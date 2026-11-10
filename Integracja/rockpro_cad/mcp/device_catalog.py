"""ROC-23: source-cited device observations; missing/conflicting facts stay unresolved."""
import copy
import hashlib
import json
import math
import re
import project_store as store

FIELDS={'X','Y','Z','mass'}
CONFIRMATIONS={'unconfirmed','source_checked','constructor_confirmed'}


def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def _hash(value):return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _text(value,label,limit=1000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Invalid '+label)
    return value


def validate_record(record):
    payload=_json(record)
    if len(payload.encode('utf-8'))>256*1024:raise ValueError('Device record too large')
    fields={'schema_version','manufacturer','model','variant','axes','sources','observations'}
    if not isinstance(record,dict) or set(record)!=fields or type(record['schema_version']) is not int or record['schema_version']!=1:raise ValueError('Exact device schema v1 required')
    for field in ('manufacturer','model','variant'):_text(record[field],field,120)
    if record['axes']!={'X':'width','Y':'depth','Z':'height'}:raise ValueError('Explicit X width / Y depth / Z height mapping required')
    if not isinstance(record['sources'],list) or not 1<=len(record['sources'])<=32:raise ValueError('Source evidence required')
    sources={}
    for source in record['sources']:
        if not isinstance(source,dict) or set(source)!={'id','kind','reference','locator','content_sha256'}:raise ValueError('Exact source fields required')
        _text(source['id'],'source ID',80)
        if source['id'] in sources:raise ValueError('Duplicate source ID')
        if source['kind'] not in ('manufacturer_page','manufacturer_pdf','mail','measurement'):raise ValueError('Unknown source kind')
        for key in ('reference','locator'):_text(source[key],key)
        if not isinstance(source['content_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',source['content_sha256']):raise ValueError('Source content checksum required')
        sources[source['id']]=source
    observations=record['observations']
    if not isinstance(observations,list) or len(observations)>256:raise ValueError('Bounded observations required')
    ids=set()
    for row in observations:
        if not isinstance(row,dict) or set(row)!={'id','field','value','unit','source_id','confirmation'}:raise ValueError('Exact observation fields required')
        _text(row['id'],'observation ID',100)
        if row['id'] in ids:raise ValueError('Duplicate observation ID')
        ids.add(row['id'])
        if row['field'] not in FIELDS or row['source_id'] not in sources:raise ValueError('Unknown field/source')
        if row['confirmation'] not in CONFIRMATIONS:raise ValueError('Unknown confirmation status')
        units={'kg':1,'g':.001} if row['field']=='mass' else {'mm':1,'cm':10,'m':1000}
        if row['unit'] not in units:raise ValueError('Explicit compatible unit required')
        value=row['value']
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0<value*units[row['unit']]<=100000):raise ValueError('Invalid positive device measurement')
        if value is None and row['confirmation']!='unconfirmed':raise ValueError('Missing value cannot be confirmed')
    return copy.deepcopy(record)


def preview_device_record(record):
    record=validate_record(record);fields={}
    for field in ('X','Y','Z','mass'):
        rows=[]
        units={'kg':1,'g':.001} if field=='mass' else {'mm':1,'cm':10,'m':1000}
        for observation in record['observations']:
            if observation['field']==field:
                row=copy.deepcopy(observation)
                row['normalized_value']=None if row['value'] is None else row['value']*units[row['unit']]
                rows.append(row)
        known=[r for r in rows if r['normalized_value'] is not None]
        conflict=bool(known) and any(not math.isclose(r['normalized_value'],known[0]['normalized_value'],abs_tol=1e-6,rel_tol=0) for r in known)
        status='conflict' if conflict else 'missing' if not known else 'unconfirmed' if any(r['confirmation']=='unconfirmed' for r in known) else 'source_checked'
        fields[field]=dict(value=known[0]['normalized_value'] if known and not conflict else None,
            unit='kg' if field=='mass' else 'mm',status=status,observations=rows)
    missing=[k for k,v in fields.items() if v['status']=='missing']
    conflicts=[k for k,v in fields.items() if v['status']=='conflict']
    identity={k:record[k] for k in ('manufacturer','model','variant')}
    return dict(catalog_id=_hash(identity),record_sha256=_hash(record),identity=identity,axes=record['axes'],fields=fields,
        missing_fields=missing,conflicting_fields=conflicts,
        dimensions_ready=all(fields[k]['status']=='source_checked' for k in ('X','Y','Z')),
        production_approved=False,confirmation_is_caller_claim=True)


def _ensure(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS device_record_versions (
       catalog_id TEXT NOT NULL,revision INTEGER NOT NULL,record_sha256 TEXT NOT NULL,
       record_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(catalog_id,revision))''')


def save_device_record(record,expected_revision):
    if type(expected_revision) is not int or expected_revision<0:raise ValueError('Device expected_revision required')
    result=preview_device_record(record);catalog_id=result['catalog_id'];payload=_json(record)
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');_ensure(conn)
        previous=conn.execute('SELECT revision,record_sha256 FROM device_record_versions WHERE catalog_id=? ORDER BY revision DESC LIMIT 1',(catalog_id,)).fetchone()
        revision=previous['revision'] if previous else 0
        if previous and previous['record_sha256']==result['record_sha256']:
            return dict(saved=True,reused=True,revision=revision,**result)
        if revision!=expected_revision:raise ValueError('DEVICE_REVISION_CONFLICT: Device data changed; compare current source evidence')
        conn.execute('INSERT INTO device_record_versions VALUES (?,?,?,?,?)',(catalog_id,revision+1,result['record_sha256'],payload,store.now()))
        from device_layout_service import invalidate_device_layouts
        affected=invalidate_device_layouts(conn,catalog_id)
    return dict(saved=True,reused=False,revision=revision+1,invalidated_projects=affected,**result)


def list_device_records(limit=100,after_catalog_id=None):
    if type(limit) is not int or not 1<=limit<=100:raise ValueError('Device list limit 1..100 required')
    if after_catalog_id is not None and (not isinstance(after_catalog_id,str) or not re.fullmatch('[0-9a-f]{64}',after_catalog_id)):raise ValueError('Invalid device page cursor')
    with store.db() as conn:
        conn.execute('BEGIN');_ensure(conn)
        rows=conn.execute('''SELECT d.* FROM device_record_versions d WHERE d.revision=
            (SELECT MAX(v.revision) FROM device_record_versions v WHERE v.catalog_id=d.catalog_id)
            AND (? IS NULL OR d.catalog_id>?) ORDER BY d.catalog_id LIMIT ?''',(after_catalog_id,after_catalog_id,limit+1)).fetchall()
    devices=[]
    for row in rows[:limit]:
        summary=preview_device_record(json.loads(row['record_json']))
        if summary['record_sha256']!=row['record_sha256']:raise ValueError('DEVICE_RECORD_INTEGRITY_FAILED')
        devices.append(dict(catalog_id=summary['catalog_id'],revision=row['revision'],identity=summary['identity'],
                            fields={k:{f:summary['fields'][k][f] for f in ('value','unit','status')} for k in FIELDS},
                            dimensions_ready=summary['dimensions_ready'],record_sha256=summary['record_sha256']))
    return dict(devices=devices,has_more=len(rows)>limit,next_cursor=devices[-1]['catalog_id'] if len(rows)>limit else None)


def get_device_record(catalog_id,revision=None):
    if not isinstance(catalog_id,str) or not re.fullmatch('[0-9a-f]{64}',catalog_id):raise ValueError('Invalid catalog ID')
    if revision is not None and (type(revision) is not int or revision<1):raise ValueError('Invalid device revision')
    with store.db() as conn:
        _ensure(conn)
        row=conn.execute('SELECT * FROM device_record_versions WHERE catalog_id=?'+(' AND revision=?' if revision is not None else '')+' ORDER BY revision DESC LIMIT 1',
                         (catalog_id,revision) if revision is not None else (catalog_id,)).fetchone()
        if row is None:raise ValueError('Device record not found')
        record=json.loads(row['record_json'])
    return dict(record=record,revision=row['revision'],**preview_device_record(record))


def draft_device_inquiry(record):
    result=preview_device_record(record)
    requested=[k for k,v in result['fields'].items() if v['status'] in ('missing','conflict','unconfirmed')]
    identity=result['identity'];lines=[f"Prośba o potwierdzenie danych: {identity['manufacturer']} {identity['model']} ({identity['variant']})",'']
    if requested:
        lines+=['Prosimy o potwierdzenie: '+', '.join(requested)+'.',
            'Osie: X = szerokość, Y = głębokość, Z = wysokość. Prosimy podać jednostki,',
            'wariant/SKU oraz rysunek wymiarowy z wystającymi elementami i masę.']
    else:lines+=['Wymiary katalogowe są zapisane. Prosimy potwierdzić obrys transportowy z akcesoriami.']
    return dict(draft='\n'.join(lines),send_required_by_authorized_person=True,sent=False,
                missing_or_conflicting_fields=requested,production_approved=False)
