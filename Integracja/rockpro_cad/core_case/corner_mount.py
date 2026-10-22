"""Pure, source-bound corner 410429 translation proposals; no native imports.

Eight measured opaque source occurrences are retained, including existing mirror
transforms. Requested motions are proper translations; no mirrored seed geometry
is synthesized. Registration anchors remain candidates, never mounting approval.
"""
import copy
import hashlib
import itertools
import json
import math
import re

TOL=.003
I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]


class CornerMountError(ValueError):
    def __init__(self,code,message):
        self.code,self.message=code,message
        super().__init__(code+': '+message)


def need(condition,code,message):
    if not condition:raise CornerMountError(code,message)


def obj(value,fields):
    need(isinstance(value,dict) and set(value)==set(fields),'INVALID_FIELDS','Exact versioned fields required')


def number(value):
    need(type(value) in (int,float),'INVALID_NUMBER','Finite numeric value required; bool is not numeric')
    try:valid=math.isfinite(value)
    except OverflowError:valid=False
    need(valid,'INVALID_NUMBER','NaN/inf are forbidden')
    return value


def integer(value):
    need(type(value) is int and 0<value<2**63,'INVALID_ID','Positive CAD integer ID required')
    return value


def vector(value,n=3):
    need(isinstance(value,list) and len(value)==n,'INVALID_VECTOR','Incorrect vector length')
    for x in value:number(x)
    return value


def size(value):
    vector(value)
    need(all(0<x<=10000 for x in value),'INVALID_SIZE','Case size must be positive and bounded in mm')
    return value


def path(value):
    need(isinstance(value,list) and 1<=len(value)<=12 and all(type(v) is int and 0<=v<=10000 for v in value),
         'INVALID_PATH','Explicit occurrence path required')
    return tuple(value)


def sha(value):
    need(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),'INVALID_SHA256','Explicit lowercase SHA256 required')
    return value


def guid(value):
    need(isinstance(value,str) and 0<len(value)<=200 and value.strip()==value,'INVALID_GUID','Explicit document GUID required')
    return value


def bounded(value):
    pending=[(value,0)];count=0
    while pending:
        item,depth=pending.pop();count+=1
        need(depth<=32 and count<=100000,'INPUT_LIMIT','JSON depth/node limit exceeded')
        if isinstance(item,dict):
            need(all(isinstance(k,str) for k in item),'INVALID_JSON','String keys required')
            pending.extend((x,depth+1) for x in item.values())
        elif isinstance(item,list):pending.extend((x,depth+1) for x in item)
        elif type(item) in (int,float):number(item)
        else:need(item is None or type(item) in (str,bool),'INVALID_JSON','Only finite JSON data is supported')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def close(a,b,tol=TOL):
    if type(b) in (int,float):return type(a) in (int,float) and abs(a-b)<=tol
    if isinstance(b,list):return isinstance(a,list) and len(a)==len(b) and all(close(x,y,tol) for x,y in zip(a,b))
    if isinstance(b,dict):return isinstance(a,dict) and set(a)==set(b) and all(close(a[k],b[k],tol) for k in b)
    return type(a) is type(b) and a==b


def determinant(m):
    a,b,c=m[:3]
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])


def matrix(m,proper=False):
    need(isinstance(m,list) and len(m)==4,'INVALID_MATRIX','4x4 row-vector affine matrix required')
    for r in m:vector(r,4)
    need(all(abs(m[i][3])<=1e-6 for i in range(3)) and abs(m[3][3]-1)<=1e-6,'INVALID_MATRIX','Invalid homogeneous affine column')
    for i,j in itertools.product(range(3),repeat=2):
        need(abs(sum(m[i][k]*m[j][k] for k in range(3))-int(i==j))<=1e-6,'INVALID_MATRIX','Scaling/shear is forbidden')
    det=determinant(m)
    need(abs((det if proper else abs(det))-1)<=1e-6,'INVALID_MATRIX','Proper frame/motion or preserved opaque reflection required')
    return m


def multiply(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def inverse(m):
    out=copy.deepcopy(I)
    for i,j in itertools.product(range(3),repeat=2):out[i][j]=m[j][i]
    out[3]=[-sum(m[3][k]*m[j][k] for k in range(3)) for j in range(3)]+[1]
    return out


def point(p,m):
    return [m[3][j]+sum(p[k]*m[k][j] for k in range(3)) for j in range(3)]


def direction(p,m):
    return [sum(p[k]*m[k][j] for k in range(3)) for j in range(3)]


def _frame(frame):
    obj(frame,{'matrix_world_mm','size_mm','panel_planes'})
    m=matrix(frame['matrix_world_mm'],proper=True);dims=size(frame['size_mm']);inv=inverse(m)
    faces=frame['panel_planes'];need(isinstance(faces,list) and len(faces)==6,'PANEL_DATUM_INCOMPLETE','Six measured external panel planes required')
    seen=set();face_ids=set()
    for f in faces:
        obj(f,{'axis','side','node_id','face_id','vertices_world_mm','normal_world'})
        axis,side=f['axis'],f['side']
        need(type(axis) is int and axis in (0,1,2) and type(side) is int and side in (0,1),'INVALID_PANEL_DATUM','Invalid plane axis/side')
        need((axis,side) not in seen,'PANEL_DATUM_AMBIGUOUS','Duplicate panel plane slot');seen.add((axis,side))
        key=(integer(f['node_id']),integer(f['face_id']))
        need(key not in face_ids,'PANEL_DATUM_AMBIGUOUS','One measured face cannot stand in for different panel planes');face_ids.add(key)
        normal=vector(f['normal_world']);expected=[0,0,0];expected[axis]=1 if side else -1
        need(close(direction(normal,inv),expected,1e-6),'INVALID_PANEL_DATUM','Measured outward normal disagrees with proper case frame')
        vertices=f['vertices_world_mm'];need(isinstance(vertices,list) and 3<=len(vertices)<=10000,'INVALID_PANEL_DATUM','Raw measured plane vertices required')
        local=[point(vector(p),inv) for p in vertices]
        need(all(abs(p[axis]-dims[axis]*side)<=TOL for p in local),'INVALID_PANEL_DATUM','Plane separation/origin contradicts declared case dimensions')
        need(all(-TOL<=p[i]<=dims[i]+TOL for p in local for i in range(3)), 'INVALID_PANEL_DATUM','External panel witness lies outside the declared case frame')
        a=local[0];area=0.
        for b,c in itertools.combinations(local[1:],2):
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            area=max(area,sum(x*x for x in cross))
        need(area>1e-8,'INVALID_PANEL_DATUM','Collinear witnesses do not establish a panel plane')
    need(seen==set(itertools.product(range(3),range(2))),'PANEL_DATUM_INCOMPLETE','Every external side requires one unambiguous measured plane')
    return m,dims


def _body(row):
    bounds=vector(row['local_bounds_mm'],6)
    need(all(bounds[i+3]>bounds[i] for i in range(3)),'INVALID_BODY','Body local bounds must be positive')
    signature=row['body_signature'];obj(signature,{'volume_m3','faces','edges','vertices','lumps'})
    need(number(signature['volume_m3'])>0,'INVALID_BODY','Positive measured body volume required')
    for key in ('faces','edges','vertices','lumps'):integer(signature[key])


def _assemblies(rows):
    need(isinstance(rows,list) and len(rows)==2,'ASSEMBLY_INCOMPLETE','Exactly two preserved source corner containers required')
    result={};paths=set()
    for row in rows:
        obj(row,{'id','occurrence_path','matrix_world_mm'});id_=integer(row['id']);key=path(row['occurrence_path'])
        need(id_ not in result and key not in paths,'ASSEMBLY_DUPLICATE','Distinct source containers required')
        matrix(row['matrix_world_mm']);result[id_]=row;paths.add(key)
    return result


def _symmetry(anchors,dims):
    need(set(anchors)==set(itertools.product(range(2),repeat=3)),'CORNER_GROUP_INCOMPLETE','All eight distinct XYZ corner slots required')
    for slot,p in anchors.items():
        for axis in range(3):
            need((p[axis]<=dims[axis]/2+TOL if slot[axis]==0 else p[axis]>=dims[axis]/2-TOL),
                 'CORNER_SLOT_MISMATCH','Explicit slot places a candidate on the wrong side of its measured wall')
            opposite=list(slot);opposite[axis]=1-opposite[axis];q=anchors[tuple(opposite)]
            expected=list(p);expected[axis]=dims[axis]-p[axis]
            need(close(q,expected),'CORNER_SYMMETRY_CONFLICT','Full anchor tuples do not reflect in each declared case axis; offsets are not averaged')


def _capture(evidence,trusted):
    bounded(evidence);bounded(trusted)
    obj(evidence,{'schema_version','units','matrix_convention','source','case_frame','assemblies','occurrences'})
    obj(trusted,{'schema_version','evidence_content_sha256','source_sha256','source_guid','assembly_ids','occurrence_bindings'})
    need(type(evidence['schema_version']) is int and evidence['schema_version']==1
         and type(trusted['schema_version']) is int and trusted['schema_version']==1,'UNSUPPORTED_SCHEMA','Corner binding v1 required')
    need(evidence['units']=='mm' and evidence['matrix_convention']=='row-vector','INVALID_UNITS_FRAME','Explicit row-vector mm evidence required')
    need(sha(trusted['evidence_content_sha256'])==digest(evidence),'EVIDENCE_HASH_MISMATCH','Evidence differs from independent caller binding')
    source=evidence['source'];obj(source,{'sha256_before','sha256_after','guid'})
    need(source['sha256_before']==source['sha256_after']==sha(trusted['source_sha256'])
         and source['guid']==guid(trusted['source_guid']),'SOURCE_BINDING_MISMATCH','Source bytes or document GUID differ')
    frame,dims=_frame(evidence['case_frame']);inv=inverse(frame)
    assemblies=_assemblies(evidence['assemblies'])
    need(isinstance(trusted['assembly_ids'],list) and len(trusted['assembly_ids'])==2,'ASSEMBLY_INCOMPLETE','Explicit two-container selection required')
    for i in trusted['assembly_ids']:integer(i)
    need(set(trusted['assembly_ids'])==set(assemblies),'SOURCE_BINDING_MISMATCH','Selected source corner containers differ')
    rows=evidence['occurrences'];selections=trusted['occurrence_bindings']
    need(isinstance(rows,list) and len(rows)==8 and isinstance(selections,list) and len(selections)==8,'CORNER_GROUP_INCOMPLETE','Exactly eight opaque corner occurrences required')
    selections_by_id={};slots=set()
    for selected in selections:
        obj(selected,{'id','assembly_id','occurrence_path','slot','anchor_local_mm'})
        id_=integer(selected['id']);integer(selected['assembly_id']);path(selected['occurrence_path']);vector(selected['anchor_local_mm'])
        slot=selected['slot'];need(isinstance(slot,list) and len(slot)==3 and all(type(x) is int and x in (0,1) for x in slot),
             'INVALID_CORNER_SLOT','Explicit binary XYZ slot required')
        need(id_ not in selections_by_id and tuple(slot) not in slots,'CORNER_GROUP_DUPLICATE','Duplicate source ID or slot')
        selections_by_id[id_]=selected;slots.add(tuple(slot))
    seen=set();paths=set();enriched=[];anchors={};by_assembly={id_:[] for id_ in assemblies}
    for raw in sorted(rows,key=lambda r:r['id']):
        obj(raw,{'id','assembly_id','occurrence_path','matrix_world_mm','matrix_parent_mm','local_bounds_mm','body_signature'})
        id_=integer(raw['id']);root_id=integer(raw['assembly_id']);key=path(raw['occurrence_path'])
        need(id_ not in seen and id_ not in assemblies and key not in paths and id_ in selections_by_id,'CORNER_GROUP_DUPLICATE','Duplicate, missing or unselected source occurrence')
        seen.add(id_);paths.add(key);selected=selections_by_id[id_]
        need(root_id in assemblies and root_id==selected['assembly_id'] and raw['occurrence_path']==selected['occurrence_path'],
             'SOURCE_BINDING_MISMATCH','Source part/container/path differs from explicit selection')
        root=assemblies[root_id]
        need(key[:-1]==path(root['occurrence_path']),'SOURCE_BINDING_MISMATCH','Part is not a direct child of its preserved source corner container')
        world=matrix(raw['matrix_world_mm']);parent=matrix(raw['matrix_parent_mm'])
        composed=multiply(parent,root['matrix_world_mm'])
        need(all(close(composed[i],world[i],TOL if i==3 else 1e-6) for i in range(4)),
             'SOURCE_PARENT_FRAME_MISMATCH','Source parent/world matrices do not compose through the preserved root')
        _body(raw);anchor=selected['anchor_local_mm'];bounds=raw['local_bounds_mm']
        need(all(bounds[i]-TOL<=anchor[i]<=bounds[i+3]+TOL for i in range(3)),
             'INVALID_REGISTRATION_ANCHOR','Candidate registration point lies outside its explicitly selected body bounds')
        source_anchor=point(anchor,world);case_anchor=point(source_anchor,inv);slot=selected['slot']
        offset=[case_anchor[i]-slot[i]*dims[i] for i in range(3)]
        anchors[tuple(slot)]=case_anchor;by_assembly[root_id].append((key[-1],slot[2]))
        enriched.append(dict(id=id_,occurrence_id='410429/'+trusted['source_guid']+'/'+str(id_),assembly_id=root_id,
            occurrence_path=copy.deepcopy(raw['occurrence_path']),slot=copy.deepcopy(slot),anchor_local_mm=copy.deepcopy(anchor),
            source_world_mm=copy.deepcopy(world),source_parent_mm=copy.deepcopy(parent),source_offset_case_mm=offset,
            local_bounds_mm=copy.deepcopy(bounds),body_signature=copy.deepcopy(raw['body_signature']),
            source_parity=-1 if determinant(world)<0 else 1))
    for members in by_assembly.values():
        need(sorted(k for k,z in members)==[0,1,2,3] and len({z for k,z in members})==1,
             'ASSEMBLY_INCOMPLETE','Each preserved corner container requires four complete same-height slots')
    _symmetry(anchors,dims)
    result=dict(schema_version=1,kind='source_bound_opaque_corner_group',sku='410429',units='mm',frame='case.min_xyz',
        source=copy.deepcopy(source),source_evidence_sha256=trusted['evidence_content_sha256'],case_frame=copy.deepcopy(evidence['case_frame']),
        assemblies=copy.deepcopy(evidence['assemblies']),occurrences=enriched,evidence=copy.deepcopy(evidence),trusted_bindings=copy.deepcopy(trusted),
        anchor_scope='candidate_registration_only',mounting_approved=False,production_approved=False,
        proof_scope='Eight opaque measured source occurrences, preserved internal/root frames and reflection parity; no mounting, collision or BRep equivalence approval')
    result['content_sha256']=digest(result)
    return result


def capture_corner_binding(evidence,trusted_bindings):
    """Validate explicit source identity, measured planes and all eight anchors."""
    try:return _capture(evidence,trusted_bindings)
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError,RecursionError) as exc:
        raise CornerMountError('INVALID_SOURCE_EVIDENCE','Malformed explicit corner evidence/binding') from exc


def _validated(binding):
    bounded(binding)
    need(isinstance(binding,dict),'INVALID_BINDING','Explicit source corner binding required')
    expected=capture_corner_binding(binding.get('evidence'),binding.get('trusted_bindings'))
    need(binding==expected,'BINDING_CONTENT_MISMATCH','Immutable source binding does not replay from its pinned evidence')
    return expected


def _plan(binding,target_size_mm):
    target=size(target_size_mm);original=binding['case_frame']['size_mm'];frame=binding['case_frame']['matrix_world_mm']
    roots={r['id']:r for r in binding['assemblies']};rows=[];anchors={}
    for source in binding['occurrences']:
        row=copy.deepcopy(source);slot=source['slot'];delta_case=[slot[i]*(target[i]-original[i]) for i in range(3)]
        delta_world=direction(delta_case,frame);motion=copy.deepcopy(I);motion[3]=delta_world+[1]
        world=copy.deepcopy(source['source_world_mm'])
        for i in range(3):world[3][i]+=delta_world[i]
        parent=(copy.deepcopy(source['source_parent_mm']) if target==original else multiply(world,inverse(roots[source['assembly_id']]['matrix_world_mm'])))
        anchor_world=point(source['anchor_local_mm'],world)
        anchor_case=[slot[i]*target[i]+source['source_offset_case_mm'][i] for i in range(3)]
        anchors[tuple(slot)]=anchor_case
        row.update(matrix_world_mm=world,matrix_parent_mm=parent,requested_motion_mm=motion,anchor_world_mm=anchor_world)
        matrix(motion,proper=True)
        need(world[:3]==source['source_world_mm'][:3],'ORIENTATION_DRIFT','Opaque source orientation may not be changed')
        rows.append(row)
    _symmetry(anchors,target)
    result=dict(schema_version=1,status='planned',units='mm',sku='410429',binding=copy.deepcopy(binding),
        binding_sha256=binding['content_sha256'],target_size_mm=copy.deepcopy(target),
        target_case_frame=dict(matrix_world_mm=copy.deepcopy(frame),size_mm=copy.deepcopy(target)),
        assemblies=copy.deepcopy(binding['assemblies']),occurrences=rows,physical_corner_parts=8,expected_poc_physical_parts=18,
        anchor_scope='candidate_registration_only',mounting_approved=False,production_approved=False,
        proof_scope='Translation-only candidate preview for eight preserved source corners; requested motions proper, absolute source reflections retained')
    result['content_sha256']=digest(result)
    return result


def plan_corner_resize(binding,target_size_mm):
    """Propose eight proper motions; preserve opaque source world orientations."""
    try:return _plan(_validated(binding),target_size_mm)
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError,RecursionError) as exc:
        raise CornerMountError('INVALID_RESIZE','Malformed corner resize request') from exc


def validate_corner_observation(plan,observed):
    """Rebuild from source, then check measured target panels/roots/parts."""
    try:
        bounded(plan);bounded(observed)
        expected=plan_corner_resize(plan['binding'],plan['target_size_mm'])
        need(plan==expected,'PLAN_CONTENT_MISMATCH','Proposal was changed or does not replay from pinned source')
        obj(observed,{'schema_version','units','case_frame','assemblies','occurrences'})
        need(type(observed['schema_version']) is int and observed['schema_version']==1 and observed['units']=='mm',
             'INVALID_OBSERVATION','Versioned mm observation required')
        m,dims=_frame(observed['case_frame'])
        need(close(m,expected['target_case_frame']['matrix_world_mm'],1e-6) and close(dims,expected['target_size_mm']),
             'TARGET_PANEL_FRAME_MISMATCH','Measured target panel frame/size differs from the proposal')
        roots=_assemblies(observed['assemblies']);wanted_roots={r['id']:r for r in expected['assemblies']}
        need(set(roots)==set(wanted_roots),'ASSEMBLY_INCOMPLETE','Observed containers differ')
        for id_,root in roots.items():
            need(root['occurrence_path']==wanted_roots[id_]['occurrence_path'] and close(root['matrix_world_mm'],wanted_roots[id_]['matrix_world_mm'],1e-6),
                 'ROOT_FRAME_DRIFT','Opaque source root frames must remain unchanged')
        wanted={r['id']:r for r in expected['occurrences']};rows=observed['occurrences']
        need(isinstance(rows,list) and len(rows)==8,'CORNER_GROUP_INCOMPLETE','Eight measured occurrences required')
        seen=set()
        for row in rows:
            obj(row,{'id','assembly_id','occurrence_path','matrix_world_mm','matrix_parent_mm','local_bounds_mm','body_signature'})
            id_=integer(row['id']);need(id_ in wanted and id_ not in seen,'CORNER_GROUP_DUPLICATE','Unselected or duplicate observed corner');seen.add(id_)
            target=wanted[id_];matrix(row['matrix_world_mm']);matrix(row['matrix_parent_mm']);_body(row)
            need(type(row['assembly_id']) is int and row['assembly_id']==target['assembly_id'] and row['occurrence_path']==target['occurrence_path'],
                 'SOURCE_BINDING_MISMATCH','Observed source/container correspondence differs')
            for field in ('matrix_world_mm','matrix_parent_mm'):
                need(all(close(row[field][i],target[field][i],TOL if i==3 else 1e-6) for i in range(4)),
                     'CORNER_POSE_DRIFT','Measured corner differs from source-preserving motion')
            need(close(row['local_bounds_mm'],target['local_bounds_mm']),'BODY_SIGNATURE_DRIFT','Opaque local body bounds changed')
            signature=row['body_signature'];reference=target['body_signature']
            need(all(signature[k]==reference[k] for k in ('faces','edges','vertices','lumps'))
                 and abs(signature['volume_m3']-reference['volume_m3'])<=max(1e-15,abs(reference['volume_m3'])*1e-8),
                 'BODY_SIGNATURE_DRIFT','Opaque source body evidence changed')
        return True
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError,RecursionError) as exc:
        raise CornerMountError('INVALID_OBSERVATION','Malformed measured corner observation') from exc
