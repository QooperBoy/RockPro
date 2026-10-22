"""Versioned, pure H7159 measured candidates. No filesystem or native imports.

Report hashes pin bytes supplied by a caller; they do not authenticate the author
or prove BRep equivalence. Saved live-memory exports remain distinct from original
disk bytes. No input can grant mounting or production approval.
"""
import copy
import hashlib
import json
import math
import re

REPORTS = {'inventory', 'source_chain', 'catalog_receipt', 'face_evidence', 'poc_receipt', 'prepared_plans'}
TRUST = {'schema_version','definition_id','definition_revision','source_inventory_sha256','original_source_sha256',
         'original_source_guid','source_subtree','source_node_id','captured_source_sha256','captured_source_guid',
         'asset_sha256','asset_guid','report_sha256'}
ASSET = {'schema_version','asset_kind','definition_id','definition_revision','sku','family','units','frame',
         'geometry_policy','stage','source_binding','geometry_signature','geometry_signature_sha256','root_poses',
         'mounting_candidate','mounting_rule','proof_scope','mounting_approved','production_approved','content_sha256'}
IDENTITY = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
RULE = {'rule_version':1,'kind':'front_wall_mirrored_pair','flange_width_mm':161.,'flange_height_mm':107.,
        'flange_thickness_mm':1.2,'minimum_pair_gap_mm':25.,'minimum_vertical_margin_mm':25.}
TOP_FIELDS = {
 'inventory': {'schema_version','operation','read_only','rows','errors','partial','limit_reasons','limits','summary',
   'duration_ms','scope','feature_children_not_traversed','bbox_validation','catalog_inference','time_limit_kind',
   'time_limit_scope','cad_document','source','status','operation_log','reader_code_sha256','cad_read_status',
   'operation_log_status','logging_truncated','inventory_path'},
 'source_chain': {'original_path','original_hash_before','original_hash_after','original_live_before','original_live_after',
   'input_capture_path','input_capture_sha256','relation','native_receipt_path'},
 'catalog_receipt': {'schema_version','passed','operation_id','source','source_binding','output_path','output_sha256',
   'asset_path','asset_sha256','production_approved','geometry_scope','source_unchanged','catalog_reused','proxies',
   'physical_occurrences','source_body_signature','body_signature','target_matrix_mm','matrix_world_mm',
   'max_pose_error_mm','max_rotation_component_error','stages'},
 'face_evidence': {'asset_path','asset_hash','asset_signature','planar_faces_parallel_local_xz','document'},
 'poc_receipt': {'passed','schema_version','operation_id','plan','source_path','source_sha256_before','source_sha256_after',
   'source_document_before','source_document_after','asset_path','asset_sha256','asset_document_before',
   'fresh_native_asset_datum','asset_document_after','output_path','output_sha256','panel_stage_receipt',
   'source_body_signature','before_save','after_reopen','snapshot_path','snapshot_sha256','graphics_update_sequence',
   'production_approved','mounting_approved','limitations'},
 'prepared_plans': {'schema_version','native_requested','source','source_sha256','asset','asset_sha256',
   'face_evidence','face_evidence_sha256','catalog_receipt','catalog_receipt_sha256','code_sha256','plans'}}


class CatalogAssetError(ValueError):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(code + ': ' + message)


def need(condition, code, message):
    if not condition:
        raise CatalogAssetError(code, message)


def obj(value, allowed, required=None):
    need(isinstance(value,dict) and set(value) <= set(allowed) and set(required or ()) <= set(value),
         'INVALID_FIELDS','Unknown or missing fields')
    return value


def number(value, low=None, high=None):
    need(type(value) in (int,float), 'INVALID_NUMBER','A boolean is not a number')
    try: valid=math.isfinite(value)
    except OverflowError: valid=False
    need(valid and (low is None or value>=low) and (high is None or value<=high), 'INVALID_NUMBER','Nonfinite or out-of-range number')
    return value


def integer(value, low=1):
    need(type(value) is int and value>=low, 'INVALID_INTEGER','Expected a bounded integer')
    return value


def text(value):
    need(isinstance(value,str) and bool(value.strip()) and len(value)<=200, 'INVALID_ID','Expected bounded nonempty text')
    return value


def sha(value):
    need(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None, 'INVALID_SHA256','Expected lowercase SHA256')
    return value


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def content_hash(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def bounded(value):
    stack=[(value,0)];count=0
    while stack:
        item,depth=stack.pop();count+=1
        need(depth<=40 and count<=500000,'INPUT_LIMIT','JSON nesting or node budget exceeded')
        if isinstance(item,dict):
            need(all(isinstance(k,str) for k in item),'INVALID_JSON','JSON keys must be strings')
            stack.extend((v,depth+1) for v in item.values())
        elif isinstance(item,list):stack.extend((v,depth+1) for v in item)
        elif type(item) in (int,float):number(item)
        else:need(item is None or type(item) in (str,bool),'INVALID_JSON','Only finite JSON data is accepted')


def vector(value, length=3):
    need(isinstance(value,list) and len(value)==length,'INVALID_VECTOR','Incorrect vector length')
    for n in value:number(n)
    return value


def matrix(value, reflected=False):
    need(isinstance(value,list) and len(value)==4,'INVALID_MATRIX','Expected 4x4 row-vector matrix')
    for row in value:vector(row,4)
    need(all(abs(value[i][3])<=1e-6 for i in range(3)) and abs(value[3][3]-1)<=1e-6,
         'INVALID_MATRIX','Not an affine transform')
    for i in range(3):
        for j in range(3):
            need(abs(sum(value[i][k]*value[j][k] for k in range(3))-int(i==j))<=1e-6,
                 'INVALID_MATRIX','Scaling or shear is forbidden')
    a,b,c=value[:3]
    det=a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    need(abs((abs(det) if reflected else det)-1)<=1e-6 and (reflected or det>0),
         'INVALID_MATRIX','Root/requested transforms must be proper rotations')
    return value


def same(a,b,tol=.003):
    if type(b) in (int,float):return type(a) in (int,float) and abs(a-b)<=tol
    if isinstance(b,list):return isinstance(a,list) and len(a)==len(b) and all(same(x,y,tol) for x,y in zip(a,b))
    if isinstance(b,dict):return isinstance(a,dict) and set(a)==set(b) and all(same(a[k],b[k],tol) for k in b)
    return type(a) is type(b) and a==b


def path_key(value):
    need(isinstance(value,list) and len(value)<=12 and all(type(v) is int and 0<=v<=1000 for v in value),
         'INVALID_SUBTREE','Invalid occurrence path')
    return tuple(value)


def signature(rows, definition_id):
    need(isinstance(rows,list) and 1<=len(rows)<=100,'INVALID_SIGNATURE','Explicit component signature required')
    mapped={};result=[]
    for row in rows:
        obj(row, {'occurrence_path','kind','name','matrix_parent_mm','local_bounds_mm','volume_m3',
                  'volume_requested_accuracy','volume_achieved_accuracy','faces','edges','vertices','lumps'},
                 {'occurrence_path','kind','name','matrix_parent_mm'})
        key=path_key(row['occurrence_path'])
        need(key not in mapped,'DUPLICATE_COMPONENT','Duplicate component path')
        need(row['kind'] in ('part','assembly'),'INVALID_SIGNATURE','Only parts and assembly containers are accepted')
        matrix(row['matrix_parent_mm'],reflected=True)
        mapped[key]=row
    need(() in mapped and mapped[()]['kind']=='assembly' and mapped[()]['name']=='H7159',
         'INVALID_SIGNATURE','H7159 root assembly required')
    need(sum(r['kind']=='part' for r in rows)==13,'INCOMPLETE_SIGNATURE','H7159 requires all 13 physical parts')
    for key,row in sorted(mapped.items()):
        need(not key or key[:-1] in mapped and mapped[key[:-1]]['kind']=='assembly',
             'INCOMPLETE_SIGNATURE','Missing parent assembly')
        if row['kind']=='assembly':
            children=sorted(k[-1] for k in mapped if len(k)==len(key)+1 and k[:-1]==key)
            need(children and children==list(range(len(children))),'INCOMPLETE_SIGNATURE','Assembly child slots must be complete')
        clean={'component_id':definition_id+'/component/'+('/'.join(map(str,key)) or 'root'),
               'occurrence_path':list(key),'kind':row['kind']}
        if key:clean['matrix_parent_mm']=copy.deepcopy(row['matrix_parent_mm'])
        if row['kind']=='part':
            b=vector(row.get('local_bounds_mm'),6)
            need(all(b[i+3]>b[i] for i in range(3)),'INVALID_SIGNATURE','Nonpositive local body bounds')
            need(number(row.get('volume_m3'),0)>0,'INVALID_SIGNATURE','Positive measured volume required')
            for k in ('faces','edges','vertices','lumps'):integer(row.get(k))
            number(row.get('volume_requested_accuracy'),0);number(row.get('volume_achieved_accuracy'),0)
            for k in ('local_bounds_mm','volume_m3','volume_requested_accuracy','volume_achieved_accuracy','faces','edges','vertices','lumps'):
                clean[k]=copy.deepcopy(row[k])
        result.append(clean)
    return result


def compare_signatures(a,b):
    need(len(a)==len(b),'INCOMPLETE_SIGNATURE','Component coverage changed')
    for x,y in zip(a,b):
        for k in ('component_id','occurrence_path','kind','faces','edges','vertices','lumps'):
            need(x.get(k)==y.get(k),'SIGNATURE_DRIFT','Component identity/topology changed')
        if x['kind']=='part':
            need(same(x['local_bounds_mm'],y['local_bounds_mm']),'SIGNATURE_DRIFT','Local geometry bounds changed')
            need(abs(x['volume_m3']-y['volume_m3'])<=max(1e-15,abs(x['volume_m3'])*1e-8),
                 'SIGNATURE_DRIFT','Measured volume changed')
        if x['occurrence_path']:
            for i in range(4):
                need(same(x['matrix_parent_mm'][i],y['matrix_parent_mm'][i],.003 if i==3 else 1e-6),
                     'SIGNATURE_DRIFT','Opaque internal placement changed')


def derive_mount(faces, source_world, definition_id):
    need(isinstance(faces,list) and all(isinstance(f,dict) for f in faces),'INVALID_DATUM','Explicit raw face witness objects required')
    selected=[]
    for face_id,y,reverse in ((194,0.,True),(353,1.2,False)):
        choices=[f for f in faces if f.get('face_id')==face_id]
        need(len(choices)==1,'INVALID_DATUM','Missing or ambiguous flange face')
        f=choices[0]
        obj(f, {'face_id','is_reversed','plane_data_type','point_mm','normal','vertex_ids','vertices_mm','bbox_mm',
                'oriented_normal','witness_bounds_mm'}, {'face_id','point_mm','normal','vertex_ids','vertices_mm'})
        integer(f['face_id']);origin=vector(f['point_mm']);normal=vector(f['normal'])
        reversed_=f.get('is_reversed',f.get('plane_data_type'))
        need(type(reversed_) is bool and reversed_ is reverse and same(normal,[0,1,0],1e-6),
             'INVALID_DATUM','Flange underlying normal or reversal is inconsistent')
        if 'plane_data_type' in f:need(type(f['plane_data_type']) is bool and f['plane_data_type'] is reverse,'INVALID_DATUM','Contradictory face reversal')
        vertices=f['vertices_mm'];ids=f['vertex_ids']
        need(isinstance(vertices,list) and 3<=len(vertices)<=1000 and isinstance(ids,list) and len(ids)==len(vertices),
             'INVALID_DATUM','Complete raw face vertices required')
        need(all(type(i) is int and i>0 for i in ids) and len(set(ids))==len(ids),'INVALID_DATUM','Duplicate/invalid face vertex IDs')
        for v in vertices:vector(v)
        need(abs(origin[1]-y)<=.003 and all(abs(v[1]-y)<=.003 for v in vertices),
             'INVALID_DATUM','Pinned flange planes are Y0 and Y1.2')
        lo=[min(v[i] for v in vertices) for i in range(3)];hi=[max(v[i] for v in vertices) for i in range(3)]
        need(abs(hi[0]-lo[0]-161)<=.003 and abs(hi[2]-lo[2]-107)<=.003
             and abs(lo[0]+hi[0])<=.006 and abs(lo[2]+hi[2])<=.006,
             'INVALID_DATUM','Pinned 161x107 flange must be centered')
        area=max(abs((b[0]-vertices[0][0])*(c[2]-vertices[0][2])-(b[2]-vertices[0][2])*(c[0]-vertices[0][0]))
                 for b in vertices[1:] for c in vertices[1:])
        need(area>1,'INVALID_DATUM','Collinear face witnesses are insufficient')
        normalized=dict(face_id=face_id,point_mm=copy.deepcopy(origin),normal=copy.deepcopy(normal),is_reversed=reverse,
             vertex_ids=copy.deepcopy(ids),vertices_mm=copy.deepcopy(vertices),oriented_normal=[v*(-1 if reverse else 1) for v in normal],witness_bounds_mm=lo+hi)
        if 'bbox_mm' in f:
            vector(f['bbox_mm'],6)
            need(same(f['bbox_mm'],lo+hi),'INVALID_DATUM','Reported face bounds differ from raw vertices beyond POC tolerance')
            normalized['bbox_mm']=copy.deepcopy(f['bbox_mm'])
        for key in ('oriented_normal','witness_bounds_mm'):
            if key in f:need(same(f[key],normalized[key]),'INVALID_DATUM','Derived face metadata contradicts raw witnesses')
        selected.append(normalized)
    matrix(source_world)
    up=[source_world[i][2] for i in range(3)]
    need(same(up,[0,0,-1],1e-6),'INVALID_DATUM','Source world up must remain catalog -Z')
    return dict(schema_version=1,component_path=[0],component_id=definition_id+'/component/0',
                component_binding='pinned_h7159_extractor_convention',
                origin_mm=[(selected[0]['witness_bounds_mm'][i]+selected[0]['witness_bounds_mm'][i+3])/2 for i in range(3)],
                outward=[0,1,0],up=up,contact_face=selected[0],exterior_face=selected[1])


def _decode(name, raw, expected):
    need(type(raw) in (bytes,str),'INVALID_REPORT','Report must be explicit JSON bytes or UTF-8 text')
    data=raw.encode('utf-8') if isinstance(raw,str) else raw
    need(len(data)<=16*1024*1024,'INPUT_LIMIT','Report byte budget exceeded')
    need(hashlib.sha256(data).hexdigest()==sha(expected),'REPORT_HASH_MISMATCH','Report bytes differ from independently supplied binding: '+name)
    def pairs(items):
        result={}
        for k,v in items:
            need(k not in result,'DUPLICATE_JSON_KEY','Duplicate JSON object key')
            result[k]=v
        return result
    try: value=json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs)
    except (UnicodeError,json.JSONDecodeError,RecursionError) as exc:raise CatalogAssetError('INVALID_REPORT','Invalid bounded UTF-8 JSON') from exc
    bounded(value);obj(value,TOP_FIELDS[name])
    if 'schema_version' in value:need(type(value['schema_version']) is int and value['schema_version']==1,'UNSUPPORTED_SCHEMA','Unsupported report version')
    return value


def _import(bundle,t):
    bounded(t);obj(t,TRUST,TRUST);obj(bundle,REPORTS,REPORTS)
    need(type(t['schema_version']) is int and t['schema_version']==1,'UNSUPPORTED_SCHEMA','Only v1 bindings are accepted')
    text(t['definition_id']);integer(t['definition_revision']);integer(t['source_node_id']);path_key(t['source_subtree'])
    obj(t['report_sha256'],REPORTS,REPORTS)
    for k in ('source_inventory_sha256','original_source_sha256','captured_source_sha256','asset_sha256'):sha(t[k])
    for k in ('original_source_guid','captured_source_guid','asset_guid'):text(t[k])
    need(t['source_inventory_sha256']==t['report_sha256']['inventory'],'SOURCE_BINDING_MISMATCH','Inventory byte bindings differ')
    r={k:_decode(k,bundle[k],t['report_sha256'][k]) for k in REPORTS}
    inv,chain,cat,face,poc,prepared=(r[k] for k in ('inventory','source_chain','catalog_receipt','face_evidence','poc_receipt','prepared_plans'))
    need(inv['scope']=='assembly_part_hierarchy','SOURCE_BINDING_MISMATCH','Expected source hierarchy inventory')
    src=inv['source'];doc=inv['cad_document']
    need(src['sha256_before']==src['sha256_after']==t['original_source_sha256'] and src['unchanged'] is True,
         'SOURCE_BINDING_MISMATCH','Original inventory source changed')
    need(doc['before']['file_guid']==doc['after']['file_guid']==t['original_source_guid']
         and doc['before']==doc['after'],'SOURCE_BINDING_MISMATCH','Inventory document identity changed')
    need(chain['original_hash_before']==chain['original_hash_after']==t['original_source_sha256']
         and chain['original_live_before']==chain['original_live_after']
         and chain['original_live_before']['file_guid']==t['original_source_guid']
         and chain['input_capture_sha256']==t['captured_source_sha256'],
         'EXPORT_LINEAGE_MISMATCH','Original/capture lineage does not match trusted binding')
    need(cat['passed'] is True and cat['production_approved'] is False and cat['source_unchanged'] is True,
         'APPROVAL_SCOPE_INVALID','Catalog export evidence must be passed but unapproved')
    stage_keys={'source_capture','native_catalog_export_import','rigid_move','body_topology_volume','save_reopen'}
    obj(cat['stages'],stage_keys,stage_keys)
    need(all(cat['stages'].get(k)=='PASS' for k in ('source_capture','native_catalog_export_import','rigid_move','body_topology_volume','save_reopen')),
         'EXPORT_LINEAGE_MISMATCH','Catalog export stages are incomplete')
    binding=cat['source_binding'];source=cat['source']
    need(binding['source_sha256']==source['sha256_before']==source['sha256_after']==t['captured_source_sha256']
         and binding['source_guid']==source['live_document']['file_guid']==t['captured_source_guid']
         and source['unchanged'] is True and binding['node_id']==t['source_node_id'] and binding['node_name']=='H7159',
         'EXPORT_LINEAGE_MISMATCH','Captured subtree identity changed')
    need(cat['asset_sha256']==face['asset_hash']==poc['asset_sha256']==prepared['asset_sha256']==t['asset_sha256'],
         'ASSET_BINDING_MISMATCH','Exported asset hashes differ')
    need(face['document']['file_guid']==poc['asset_document_before']['file_guid']==poc['asset_document_after']['file_guid']==t['asset_guid']
         and poc['asset_document_before']==poc['asset_document_after'], 'ASSET_BINDING_MISMATCH','Exported asset document identity changed')
    need(face['document'].get('modified') is False and poc['asset_document_before'].get('modified') is False,
         'ASSET_BINDING_MISMATCH','Dirty asset memory cannot be equated to the pinned exported file')
    need(prepared['face_evidence_sha256']==t['report_sha256']['face_evidence']
         and prepared['catalog_receipt_sha256']==t['report_sha256']['catalog_receipt'],
         'EXPORT_LINEAGE_MISMATCH','Prepared report references different evidence bytes')
    need(poc['passed'] is True and poc['production_approved'] is False and poc['mounting_approved'] is False,
         'APPROVAL_SCOPE_INVALID','POC evidence cannot grant mounting/production approval')
    need(poc['source_sha256_before']==poc['source_sha256_after']==prepared['source_sha256'],
         'SOURCE_BINDING_MISMATCH','POC case source changed')
    for stage in ('before_save','after_reopen'):
        check=poc[stage]
        need(check['passed'] is True and check['physical_parts']==37 and check['real_catalog_parts']==26
             and check['proxy_parts']==11 and check['catalog_assemblies']==2,
             'INCOMPLETE_SIGNATURE','POC part/assembly accounting differs')
    sig=signature(face['asset_signature'],t['definition_id'])
    for rows in (cat['source_body_signature'],cat['body_signature'],poc['source_body_signature']):
        compare_signatures(sig,signature(rows,t['definition_id']))
    subtree=path_key(t['source_subtree']);tree={}
    for row in inv['rows']:
        key=path_key(row['occurrence_path']);need(key not in tree,'DUPLICATE_COMPONENT','Duplicate inventory path');tree[key]=row
    need(subtree in tree and tree[subtree]['id']==t['source_node_id'] and tree[subtree]['kind']=='assembly'
         and tree[subtree]['name']=='H7159','SOURCE_BINDING_MISMATCH','Exact bound source root not found')
    selected={k[len(subtree):]:v for k,v in tree.items() if k[:len(subtree)]==subtree}
    need(set(selected)=={path_key(x['occurrence_path']) for x in sig},'INCOMPLETE_SIGNATURE','Inventory subtree coverage differs')
    for component in sig:
        key=path_key(component['occurrence_path']);row=selected[key]
        need(row['kind']==component['kind'] and not row.get('errors'),'INCOMPLETE_SIGNATURE','Source subtree has unresolved rows')
        children=sum(len(k)==len(key)+1 and k[:-1]==key for k in selected)
        if component['kind']=='assembly':
            need(type(row['children']) is int and row['children']==children,'INCOMPLETE_SIGNATURE','Assembly occurrence coverage differs')
        else:
            need(children==0 and (type(row['children']) is int and row['children']==0
                 or row['children'] is None and row.get('children_scope')=='not_traversed_modeling_features'),
                 'INCOMPLETE_SIGNATURE','Physical part must be a leaf of the assembly occurrence hierarchy')
        if component['kind']=='part':
            box=row['bounding_box']
            need(box['valid'] is True and box['unit']=='mm' and box['frame']=='part_local'
                 and same(box['minimum']+box['maximum'],component['local_bounds_mm']),
                 'SIGNATURE_DRIFT','Inventory local bounds do not match exported component')
    world=matrix(binding['expected_world_matrix_mm']);asset_world=matrix(face['asset_signature'][0]['matrix_parent_mm'])
    mount=derive_mount(face['planar_faces_parallel_local_xz'],world,t['definition_id'])
    stored=poc['plan']['datum']
    for key in ('schema_version','origin_mm','outward','up','contact_face','exterior_face'):
        need(same(stored[key],mount[key]),'INVALID_DATUM','POC datum contradicts raw measured flange witnesses')
    need(stored['sku']=='H7159' and stored['asset_sha256']==t['asset_sha256'] and stored['asset_guid']==t['asset_guid']
         and stored['mounting_approved'] is False and same(stored['source_world_matrix_mm'],world),
         'INVALID_DATUM','POC datum belongs to a different source or asset')
    matches=[x for x in prepared['plans'] if x['id']==poc['operation_id']]
    need(len(matches)==1 and matches[0]['plan']['datum']==stored,'INVALID_DATUM','Prepared and executed datum differ')
    modified=chain['original_live_before']['modified']
    need(type(modified) is bool,'SOURCE_BINDING_MISMATCH','Explicit source modified flag required')
    capture_modified=source['live_document']['modified']
    need(type(capture_modified) is bool,'SOURCE_BINDING_MISMATCH','Explicit captured-source modified flag required')
    relation=('saved_source_bound' if modified is False and capture_modified is False and doc.get('disk_equivalence')=='saved_document'
              and doc['before']==chain['original_live_before'] else 'unproven_live_memory')
    source_binding=dict(inventory_sha256=t['source_inventory_sha256'],inventory_content_sha256=content_hash(inv),
        original_sha256=t['original_source_sha256'],original_guid=t['original_source_guid'],subtree=copy.deepcopy(t['source_subtree']),
        node_id=t['source_node_id'],capture_sha256=t['captured_source_sha256'],capture_guid=t['captured_source_guid'],
        asset_sha256=t['asset_sha256'],asset_guid=t['asset_guid'],report_sha256=copy.deepcopy(t['report_sha256']),
        original_document_modified=modified,captured_document_modified=capture_modified,
        inventory_disk_equivalence=doc.get('disk_equivalence'),inventory_relation_status=relation)
    asset=dict(schema_version=1,asset_kind='source_bound_catalog_candidate',definition_id=t['definition_id'],
        definition_revision=t['definition_revision'],sku='H7159',family='handles',units='mm',frame='catalog.local',
        geometry_policy='rigid',stage='measured_candidate',source_binding=source_binding,geometry_signature=sig,
        geometry_signature_sha256=content_hash(sig),root_poses=dict(captured_source_world_mm=copy.deepcopy(world),
        asset_world_mm=copy.deepcopy(asset_world)),mounting_candidate=mount,mounting_rule=copy.deepcopy(RULE),
        proof_scope='Saved report bytes and measured topology/volume/bounds/internal poses; not a complete BRep fingerprint or authenticated approval',
        mounting_approved=False,production_approved=False)
    asset['content_sha256']=content_hash(asset)
    return asset


def import_candidate(bundle,trusted_bindings):
    """Import six explicit saved JSON inputs; never follow paths found in them."""
    try:return validate_asset(_import(bundle,trusted_bindings))
    except (KeyError,TypeError,IndexError,OverflowError,RecursionError) as exc:
        raise CatalogAssetError('INVALID_REPORT','Incomplete or malformed pinned report bundle') from exc


def validate_asset(asset):
    try:
        bounded(asset);obj(asset,ASSET,ASSET)
        need(type(asset['schema_version']) is int and asset['schema_version']==1,'UNSUPPORTED_SCHEMA','CatalogAsset v1 required')
        text(asset['definition_id']);integer(asset['definition_revision'])
        need(asset['asset_kind']=='source_bound_catalog_candidate' and asset['sku']=='H7159' and asset['family']=='handles'
             and asset['units']=='mm' and asset['frame']=='catalog.local' and asset['geometry_policy']=='rigid'
             and asset['stage']=='measured_candidate' and asset['mounting_approved'] is False and asset['production_approved'] is False,
             'APPROVAL_SCOPE_INVALID','Only an unapproved source-bound H7159 candidate is supported')
        need(sha(asset['content_sha256'])==content_hash({k:v for k,v in asset.items() if k!='content_sha256'}),
             'ASSET_CONTENT_MISMATCH','Immutable definition content hash differs')
        sig=asset['geometry_signature'];need(isinstance(sig,list),'INVALID_SIGNATURE','Signature required')
        raw=[]
        for row in sig:
            clean=dict(row);component=clean.pop('component_id',None);key=path_key(clean['occurrence_path'])
            need(component==asset['definition_id']+'/component/'+('/'.join(map(str,key)) or 'root'),'INVALID_SIGNATURE','Component identity differs')
            clean['name']='H7159' if not key else 'component';clean.setdefault('matrix_parent_mm',copy.deepcopy(IDENTITY));raw.append(clean)
        need(signature(raw,asset['definition_id'])==sig and content_hash(sig)==asset['geometry_signature_sha256'],
             'SIGNATURE_DRIFT','Normalized component signature changed')
        roots=obj(asset['root_poses'],{'captured_source_world_mm','asset_world_mm'},{'captured_source_world_mm','asset_world_mm'})
        for m in roots.values():matrix(m)
        mount=asset['mounting_candidate']
        mount_fields={'schema_version','component_path','component_id','component_binding','origin_mm','outward','up','contact_face','exterior_face'}
        obj(mount,mount_fields,mount_fields)
        need(type(mount['schema_version']) is int and same(mount,derive_mount([mount['contact_face'],mount['exterior_face']],roots['captured_source_world_mm'],asset['definition_id'])),
             'INVALID_DATUM','Mounting metadata differs from raw witnesses')
        parts=[r for r in sig if r['component_id']==mount['component_id'] and r['occurrence_path']==[0] and r['kind']=='part']
        need(len(parts)==1,'INVALID_DATUM','Pinned extractor flange component [0] is missing')
        need(same(parts[0]['matrix_parent_mm'],IDENTITY,1e-6),'INVALID_DATUM',
             'Pinned v1 extractor requires flange part-local axes identical to catalog-root local axes')
        body_bounds=parts[0]['local_bounds_mm']
        need(all(body_bounds[i]-.003<=v[i]<=body_bounds[i+3]+.003 for f in (mount['contact_face'],mount['exterior_face'])
                 for v in f['vertices_mm'] for i in range(3)), 'INVALID_DATUM','Flange witnesses fall outside the explicitly bound part')
        need(asset['mounting_rule']==RULE,'INVALID_RULE','Only the explicit H7159 pair rule is supported')
        s=asset['source_binding']
        fields={'inventory_sha256','inventory_content_sha256','original_sha256','original_guid','subtree','node_id',
                'capture_sha256','capture_guid','asset_sha256','asset_guid','report_sha256','original_document_modified','captured_document_modified',
                'inventory_disk_equivalence','inventory_relation_status'}
        obj(s,fields,fields)
        for k in ('inventory_sha256','inventory_content_sha256','original_sha256','capture_sha256','asset_sha256'):sha(s[k])
        for k in ('original_guid','capture_guid','asset_guid'):text(s[k])
        path_key(s['subtree']);integer(s['node_id']);obj(s['report_sha256'],REPORTS,REPORTS)
        for value in s['report_sha256'].values():sha(value)
        need(s['inventory_sha256']==s['report_sha256']['inventory'],'SOURCE_BINDING_MISMATCH','Inventory report binding differs')
        need(type(s['original_document_modified']) is bool and type(s['captured_document_modified']) is bool
             and s['inventory_relation_status'] in ('saved_source_bound','unproven_live_memory'),
             'SOURCE_BINDING_MISMATCH','Explicit source relation required')
        if s['inventory_relation_status']=='saved_source_bound':
            need(s['original_document_modified'] is False and s['captured_document_modified'] is False
                 and s['inventory_disk_equivalence']=='saved_document',
                 'SOURCE_BINDING_MISMATCH','Live memory cannot be silently equated to original disk source')
        return copy.deepcopy(asset)
    except (KeyError,TypeError,IndexError,OverflowError,RecursionError) as exc:
        raise CatalogAssetError('INVALID_ASSET','Malformed versioned candidate definition') from exc


def plan_candidate_pair(asset,request):
    """Pure preview of two rigid candidates; invalid data returns no changes."""
    try:
        asset=validate_asset(asset);bounded(request)
        keys={'schema_version','units','frame','size','thickness','lid_height','edge_inset_mm','count'}
        obj(request,keys,keys)
        need(type(request['schema_version']) is int and request['schema_version']==1 and request['units']=='mm'
             and request['frame']=='case.closed','INVALID_REQUEST','Explicit v1 closed mm case frame required')
        need(type(request['count']) is int and request['count']==2,'INVALID_COUNT','This rule supports exactly one mirrored pair')
        w,d,h=vector(request['size']);t=number(request['thickness'],1,100);lid=number(request['lid_height'],2,1000)
        edge=number(request['edge_inset_mm'],0,1000)
        need(all(0<n<=5000 for n in (w,d,h)) and min(w,d)>2*t and lid>t and h-lid>t,'CASE_TOO_SMALL','Invalid closed case dimensions')
        x=w/2-edge-80.5;base=h-lid;z=base/2
        need(2*(x-80.5)>=25 and z-53.5>=t+25 and base-z-53.5>=25,'GROUP_NO_SPACE','Flanges do not fit the declared wall and clearances')
        rows=[]
        for name,cx in (('left',-x),('right',x)):
            anchor=[cx,-d/2,z];m=[[1,0,0,0],[0,-1,0,0],[0,0,-1,0],anchor+[1]]
            origin=asset['mounting_candidate']['origin_mm']
            for j in range(3):m[3][j]-=sum(origin[k]*m[k][j] for k in range(3))
            rows.append(dict(id=asset['definition_id']+'/front-pair/'+name,definition_id=asset['definition_id'],
                 definition_revision=asset['definition_revision'],asset_content_sha256=asset['content_sha256'],
                 geometry_signature_sha256=asset['geometry_signature_sha256'],anchor_mm=anchor,matrix_mm=m))
        result=dict(schema_version=1,status='planned',units='mm',frame='case.closed',case=copy.deepcopy(request),
             group=dict(symmetry_group_id=asset['definition_id']+'/front-pair',mode='mirrored_pair',datum='front.outer',
                scope='candidate_only',members=[r['id'] for r in rows],edge_inset_mm=edge),occurrences=rows,
             mounting_approved=False,production_approved=False,diagnostics=[],changes=[],
             proof_scope='Offline rigid group preview only; no native execution, cutout, collision or mounting acceptance')
        result['content_sha256']=content_hash(result)
        return result
    except ValueError as exc:
        return dict(status='blocked',diagnostics=[dict(code=getattr(exc,'code','INVALID_REQUEST'),message=str(exc))],changes=[])
    except (KeyError,TypeError,IndexError,OverflowError,RecursionError):
        return dict(status='blocked',diagnostics=[dict(code='INVALID_REQUEST',message='Malformed candidate placement request')],changes=[])


def build_manifest_sidecar(manifest,asset,selected_occurrence_ids):
    """Return an independent candidate mapping for exactly the proved root."""
    asset=validate_asset(asset);bounded(manifest)
    from .manifest import validate_manifest
    need(validate_manifest(manifest).valid,'INVALID_MANIFEST','Manifest must remain a structurally valid inventory draft')
    source=asset['source_binding']
    need(source['inventory_relation_status']=='saved_source_bound','INVENTORY_RELATION_UNPROVEN',
         'Historical live-memory export is not an exact inventory binding; capture a new inventory and export from one pinned saved source revision')
    need(manifest['manifest_stage']=='inventory_draft' and manifest['runtime_template_compatible'] is False
         and manifest['production_approved'] is False,'INVALID_MANIFEST','A sidecar never promotes the source draft')
    binding=manifest['source_binding']
    need(binding['inventory_content_sha256']==source['inventory_content_sha256']
         and manifest['inventory_file_sha256']==source['inventory_sha256']
         and binding['source']['sha256_before']==binding['source']['sha256_after']==source['original_sha256']
         and binding['cad_document']['before']['file_guid']==source['original_guid'],
         'SOURCE_BINDING_MISMATCH','Manifest belongs to another inventory/source revision')
    need(isinstance(selected_occurrence_ids,list) and len(selected_occurrence_ids)==1 and isinstance(selected_occurrence_ids[0],str),
         'SOURCE_SELECTION_INVALID','Select exactly the explicitly bound root occurrence')
    matches=[r for r in manifest['occurrences'] if r['rockpro_id']==selected_occurrence_ids[0]]
    need(len(matches)==1,'SOURCE_SELECTION_INVALID','Selected occurrence is unknown or ambiguous')
    selected=matches[0];ref=selected['source_ref']
    need(ref['occurrence_path']==source['subtree'] and ref['cad_id']==source['node_id'] and ref['kind']=='assembly',
         'SOURCE_SELECTION_INVALID','Same-name siblings or component rows are not the explicitly bound source root')
    result=dict(schema_version=1,kind='catalog_candidate_sidecar',manifest_id=manifest['manifest_id'],
        manifest_content_sha256=content_hash(manifest),asset_content_sha256=asset['content_sha256'],
        links=[dict(source_occurrence_id=selected['rockpro_id'],source_subtree=copy.deepcopy(source['subtree']),
             definition_id=asset['definition_id'],definition_revision=asset['definition_revision'],status='candidate_only')],
        runtime_template_compatible=False,mounting_approved=False,production_approved=False)
    result['content_sha256']=content_hash(result)
    return result
