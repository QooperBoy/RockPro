"""ROC-29: versioned approved-input BOM import and conservative demand grouping.

No dimensions are obtained from an assembly bounding box. Approval references
are preserved caller claims; this service does not grant production approval.
"""
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import project_store as store


def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(encode(value).encode('utf-8')).hexdigest()


def token(value,label):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',value):raise ValueError('Invalid '+label)
    return value


def positive(value,label,maximum=100000):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=maximum:raise ValueError('Invalid '+label)


def approval_payload_hash(document):return digest({k:v for k,v in document.items() if k!='approval'})


def validate_bom(document):
    fields={'schema_version','project_id','source_revision','model_sha256','units','case_quantity','scope','approval','rows'}
    if not isinstance(document,dict) or set(document)!=fields or type(document['schema_version']) is not int or document['schema_version']!=1:raise ValueError('Exact BOM schema v1 required')
    token(document['project_id'],'project ID');token(document['source_revision'],'source revision')
    if not isinstance(document['model_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',document['model_sha256']):raise ValueError('Model SHA256 required')
    if document['units']!='mm':raise ValueError('BOM cutting dimensions must use explicit mm')
    if document['scope'] not in ('source_input','synthetic_test'):raise ValueError('Explicit input scope required')
    if type(document['case_quantity']) is not int or not 1<=document['case_quantity']<=100000:raise ValueError('Positive case quantity required')
    approval=document['approval']
    if (not isinstance(approval,dict) or set(approval)!={'status','reference','by','content_sha256'} or
        approval['status']!='approved' or any(not isinstance(approval[k],str) or not approval[k] or len(approval[k])>500 for k in ('reference','by')) or
        approval['content_sha256']!=approval_payload_hash(document)):raise ValueError('Approval reference must bind this exact BOM content')
    rows=document['rows']
    if not isinstance(rows,list) or not 1<=len(rows)<=2000:raise ValueError('BOM requires 1..2000 rows')
    ids=set();total=0
    for row in rows:
        keys={'id','material_id','finish','technology_id','thickness_mm','cut_length_mm','cut_width_mm','per_case_quantity','grain_axis','rotation_allowed','required_date','dimension_source'}
        if not isinstance(row,dict) or set(row)!=keys:raise ValueError('Exact BOM row fields required')
        for key in ('id','material_id','finish','technology_id'):token(row[key],key)
        if row['id'] in ids:raise ValueError('Duplicate BOM row ID')
        ids.add(row['id'])
        for key in ('thickness_mm','cut_length_mm','cut_width_mm'):positive(row[key],key,10000 if key!='thickness_mm' else 100)
        if type(row['per_case_quantity']) is not int or not 1<=row['per_case_quantity']<=100000:raise ValueError('Positive integer quantity per case required')
        if row['grain_axis'] not in ('X','Y','free') or type(row['rotation_allowed']) is not bool:raise ValueError('Explicit grain/rotation policy required')
        if row['dimension_source']!='technology':raise ValueError('Cut size must come from technology; assembly bbox is not a cutting dimension')
        if not isinstance(row['required_date'],str) or date.fromisoformat(row['required_date']).isoformat()!=row['required_date']:raise ValueError('Explicit ISO required date required')
        total+=row['per_case_quantity']*document['case_quantity']
    if total>1000000:raise ValueError('Expanded demand exceeds one million parts')
    return dict(valid=True,document_sha256=digest(document),content_sha256=approval_payload_hash(document),rows=len(rows),
        cases=document['case_quantity'],total_parts=total,scope=document['scope'],approval_is_caller_claim=True,production_approved=False)


def _read(path):
    import worker
    path=Path(path).resolve(strict=True)
    if not path.is_relative_to((worker.ROOT/'imports').resolve()) or path.suffix.lower()!='.json':raise ValueError('Stage BOM JSON in Integracja/imports')
    with path.open('rb') as stream:data=stream.read(2*1024*1024+1)
    if len(data)>2*1024*1024:raise ValueError('BOM input exceeds 2 MB')
    document=json.loads(data.decode('utf-8-sig'));result=validate_bom(document)
    return document,data,dict(source_sha256=hashlib.sha256(data).hexdigest(),**result)


def preview_bom_file(path):return _read(path)[2]


def ensure(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS bom_versions (
        project_id TEXT NOT NULL REFERENCES projects(id), revision INTEGER NOT NULL,
        source_revision TEXT NOT NULL, document_sha256 TEXT NOT NULL, source_sha256 TEXT NOT NULL,
        document_json TEXT NOT NULL, source_blob BLOB NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(project_id,revision), UNIQUE(project_id,source_revision))''')


def import_bom_file(project_id,path,expected_revision,expected_source_sha256):
    document,data,preview=_read(path)
    if document['project_id']!=project_id:raise ValueError('BOM_PROJECT_MISMATCH')
    if preview['source_sha256']!=expected_source_sha256:raise ValueError('BOM_SOURCE_CHANGED')
    if type(expected_revision) is not int or expected_revision<0:raise ValueError('BOM expected revision required')
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');store.project_exists(conn,project_id);ensure(conn)
        current=conn.execute('SELECT COALESCE(MAX(revision),0) FROM bom_versions WHERE project_id=?',(project_id,)).fetchone()[0]
        previous=conn.execute('SELECT revision,document_sha256 FROM bom_versions WHERE project_id=? AND source_revision=?',(project_id,document['source_revision'])).fetchone()
        if previous:
            if previous['document_sha256']!=preview['document_sha256']:raise ValueError('BOM_REVISION_REUSED_WITH_DIFFERENT_CONTENT')
            return dict(imported=True,reused=True,revision=previous['revision'],historical=previous['revision']!=current,**preview)
        if expected_revision!=current:raise ValueError('BOM_REVISION_CONFLICT')
        stamp=store.now();revision=current+1
        conn.execute('INSERT INTO bom_versions VALUES (?,?,?,?,?,?,?,?)',(project_id,revision,document['source_revision'],preview['document_sha256'],preview['source_sha256'],encode(document),data,stamp))
        store.change_stages(conn,project_id,['materials','production'],'outdated','operator','bom_import','bom_changed',stamp)
        result=dict(imported=True,reused=False,revision=revision,historical=False,**preview)
        conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',(project_id,stamp,'bom_imported',encode(result)))
    return result


def aggregate_bom_demand(project_ids):
    if not isinstance(project_ids,list) or not 1<=len(project_ids)<=100:raise ValueError('Unique project list required')
    for project_id in project_ids:token(project_id,'project ID')
    if len(set(project_ids))!=len(project_ids):raise ValueError('Unique project list required')
    project_ids=sorted(project_ids)
    documents=[];bindings=[]
    with store.db() as conn:
        conn.execute('BEGIN');ensure(conn)
        for project_id in project_ids:
            store.project_exists(conn,project_id)
            row=conn.execute('SELECT * FROM bom_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',(project_id,)).fetchone()
            if row is None:raise ValueError('BOM_REQUIRED: '+str(project_id))
            document=json.loads(row['document_json']);validate_bom(document)
            if digest(document)!=row['document_sha256']:raise ValueError('BOM_INTEGRITY_FAILED')
            documents.append(document);bindings.append(dict(project_id=project_id,revision=row['revision'],document_sha256=row['document_sha256'],source_revision=row['source_revision'],model_sha256=document['model_sha256']))
    if len({d['scope'] for d in documents})!=1:raise ValueError('Do not mix synthetic and source material demand')
    groups={};total=0
    for document in documents:
        for row in document['rows']:
            # Dates are conservatively exact; merging into compatible windows
            # requires a separate explicit scheduling policy.
            key=tuple(row[k] for k in ('material_id','finish','technology_id','thickness_mm','required_date','grain_axis','rotation_allowed','cut_length_mm','cut_width_mm'))
            group=groups.setdefault(key,{k:row[k] for k in ('material_id','finish','technology_id','thickness_mm','required_date','grain_axis','rotation_allowed','cut_length_mm','cut_width_mm')}|dict(quantity=0,sources=[]))
            quantity=row['per_case_quantity']*document['case_quantity'];total+=quantity;group['quantity']+=quantity
            group['sources'].append(dict(project_id=document['project_id'],source_revision=document['source_revision'],row_id=row['id'],cases=document['case_quantity'],per_case_quantity=row['per_case_quantity'],quantity=quantity))
    result=dict(groups=sorted(groups.values(),key=lambda r:encode({k:r[k] for k in r if k!='sources'})),
                bindings=bindings,total_parts=total,scope=documents[0]['scope'],production_approved=False)
    result['demand_sha256']=digest(result)
    return result
