"""One explicitly unapproved H7159 flange datum and a rigid wall-relative pair.

Standalone POC contract. It does not promote the Epson inventory, change the
frozen two-device recipe, or claim manufacturing/cutout/collision acceptance.
"""
import copy
import itertools
import math
import re

from .native_reader import validate_matrix


def _vec(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
        raise ValueError('finite 3-vector required')
    return value


def _cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def _sub(a,b):return [a[i]-b[i] for i in range(3)]
def point_at(point,matrix):return [sum(point[k]*matrix[k][j] for k in range(3))+matrix[3][j] for j in range(3)]


def candidate_datum(evidence, *, contact_face_id, exterior_face_id, expected_asset_sha256, expected_guid):
    """Pin two measured native flange faces, not a guessed assembly AABB plane.

    The plane's SDK normal is its underlying surface normal. Face reversal is
    applied separately; mounting outward opposes the contact face normal.
    """
    if evidence.get('asset_hash')!=expected_asset_sha256 or evidence.get('document',{}).get('file_guid')!=expected_guid:
        raise ValueError('asset SHA256/GUID differs from explicit evidence binding')
    if not isinstance(expected_asset_sha256,str) or not re.fullmatch('[0-9a-f]{64}',expected_asset_sha256) or evidence.get('asset_signature',[{}])[0].get('name')!='H7159':
        raise ValueError('explicit H7159 asset identity required')
    faces=[]
    for face_id in [contact_face_id,exterior_face_id]:
        matches=[x for x in evidence['planar_faces_parallel_local_xz'] if x['face_id']==face_id]
        if len(matches)!=1:raise ValueError('missing or ambiguous candidate flange face')
        f=copy.deepcopy(matches[0]);normal=_vec(f['normal']);origin=_vec(f['point_mm'])
        vertices=[_vec(v) for v in f['vertices_mm']]
        if len(vertices)<3 or len(vertices)!=len(f['vertex_ids']):raise ValueError('raw face witnesses required')
        if abs(normal[1]-1)>1e-6 or abs(normal[0])+abs(normal[2])>1e-6:raise ValueError('candidate flange is not parallel to catalog XZ')
        if any(abs(v[1]-origin[1])>.003 for v in vertices):raise ValueError('non-coplanar flange witnesses')
        if not any(sum(x*x for x in _cross(_sub(b,vertices[0]),_sub(c,vertices[0])))>1 for b,c in itertools.combinations(vertices[1:],2)):
            raise ValueError('collinear flange witnesses')
        lo=[min(v[j] for v in vertices) for j in range(3)];hi=[max(v[j] for v in vertices) for j in range(3)]
        if abs(hi[0]-lo[0]-161)>.003 or abs(hi[2]-lo[2]-107)>.003:raise ValueError('flange witness footprint differs from measured SKU')
        reversed_=f.get('is_reversed',f.get('plane_data_type'))
        if type(reversed_) is not bool:raise ValueError('SDK pvarReversed boolean required')
        f.pop('plane_data_type',None);f['is_reversed']=reversed_
        f['oriented_normal']=[x*(-1 if reversed_ else 1) for x in normal]
        f['witness_bounds_mm']=lo+hi;faces.append(f)
    back,front=faces
    if not back['is_reversed'] or front['is_reversed'] or abs(front['point_mm'][1]-back['point_mm'][1]-1.2)>.003:
        raise ValueError('contact/exterior side or flange thickness is inconsistent')
    if abs(back['point_mm'][1])>.003 or abs(front['point_mm'][1]-1.2)>.003 or any(abs(back['witness_bounds_mm'][i]+back['witness_bounds_mm'][i+3])>.006 for i in [0,2]):
        raise ValueError('this POC requires the pinned asset contact Y0 and centered 161x107 flange')
    source=validate_matrix(evidence['source_world_matrix_mm'])
    # Original source world +Z is retained as up. For this asset that is -local Z.
    up=[source[i][2] for i in range(3)]
    if max(abs(up[i]-[0,0,-1][i]) for i in range(3))>1e-6:raise ValueError('source evidence up direction differs from this POC SKU')
    return {'schema_version':1,'asset_sha256':expected_asset_sha256,'asset_guid':expected_guid,
       'sku':'H7159','mounting_approved':False,'scope':'candidate measured flange datum; no cutout or strength approval',
       'origin_mm':[(back['witness_bounds_mm'][i]+back['witness_bounds_mm'][i+3])/2 for i in range(3)],
       'outward':[0,1,0],'up':up,'source_world_matrix_mm':source,'contact_face':back,'exterior_face':front}


def validate_datum(datum):
    """Re-derive every datum field from witnesses; reject contradictory metadata."""
    if not isinstance(datum,dict):raise ValueError('candidate datum required')
    e={'asset_hash':datum.get('asset_sha256'),'document':{'file_guid':datum.get('asset_guid')},
       'asset_signature':[{'name':'H7159'}],'source_world_matrix_mm':datum.get('source_world_matrix_mm'),
       'planar_faces_parallel_local_xz':[datum.get('contact_face',{}),datum.get('exterior_face',{})]}
    try:
        derived=candidate_datum(e,contact_face_id=datum['contact_face']['face_id'],exterior_face_id=datum['exterior_face']['face_id'],
          expected_asset_sha256=datum['asset_sha256'],expected_guid=datum['asset_guid'])
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('incomplete candidate datum') from exc
    if derived!=datum:raise ValueError('datum metadata differs from measured face witnesses')
    return datum


def plan_hardware_poc(size,datum):
    """Regenerate two independent native cases from edge anchors; no native mates."""
    validate_datum(datum)
    length,depth,height=_vec(size)
    if any(x<=0 or x>5000 for x in size):raise ValueError('bounded positive case dimensions required')
    if datum.get('mounting_approved') is not False or datum.get('sku')!='H7159':raise ValueError('explicit unapproved candidate datum required')
    thickness=9.;lid=80.;base=height-lid;side_inset=100.;margin=25.;half_w=80.5;half_h=53.5
    x=length/2-side_inset-half_w;z=base/2
    if x<half_w+margin/2 or z-half_h<thickness+margin or base-z-half_h<margin:
        raise ValueError('wall too small for pair and declared flange edge/seam clearances')
    device_shape=[300,220,100];device_center=[0,0,thickness+device_shape[2]/2]
    if length-2*thickness<device_shape[0]+40 or depth-2*thickness<device_shape[1]+40 or base-thickness<device_shape[2]+40:
        raise ValueError('single product clearance is infeasible')
    occurrences=[]
    def box(id_,shape,center):
        occurrences.append({'id':id_,'family':'product_proxy' if id_=='product/1' else 'panel_proxy','definition':id_,
          'rotation':[[1,0,0],[0,1,0],[0,0,1]],'closed_xyz':center,'shape':shape,
          'local_bounds':[[-v/2 for v in shape],[v/2 for v in shape]]})
    for name,z0,h in [('base',thickness,base-thickness),('lid',base,lid-thickness)]:
        for side,y in [('front',-depth/2+thickness/2),('rear',depth/2-thickness/2)]:box(f'panels-{name}-{side}/1',[length,thickness,h],[0,y,z0+h/2])
        for side,x0 in [('left',-length/2+thickness/2),('right',length/2-thickness/2)]:box(f'panels-{name}-{side}/1',[thickness,depth-2*thickness,h],[x0,0,z0+h/2])
    box('panels-floor/1',[length,depth,thickness],[0,0,thickness/2])
    box('panels-roof/1',[length,depth,thickness],[0,0,height-thickness/2])
    box('product/1',device_shape,device_center)
    handles=[]
    for side,cx in [('left',-x),('right',x)]:
        matrix=[[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[cx,-depth/2,z,1]]
        # Translate the measured candidate datum, not the arbitrary source origin.
        rotated=point_at(datum['origin_mm'],matrix)
        for j,target in enumerate([cx,-depth/2,z]):matrix[3][j]+=target-rotated[j]
        handles.append({'id':'H7159-'+side,'matrix_mm':validate_matrix(matrix),'anchor_mm':[cx,-depth/2,z]})
    result={'schema_version':1,'status':'planned','units':'mm','size':size,'base_height':base,'lid_height':lid,'thickness':thickness,
      'handles':handles,'datum':copy.deepcopy(datum),'production_approved':False,'expected_physical_parts':37,
      'proxy_plan':{'status':'planned','units':'mm','synthetic':True,'production_approved':False,'occurrences':occurrences,'inventory':{'physical_ids':[p['id'] for p in occurrences]}},
      'device':{'shape':device_shape,'center':device_center,'rotation':[[1,0,0],[0,1,0],[0,0,1]],'anchor':'floor top, centered X/Y','minimum_side_clearance_mm':20,'minimum_hardware_aabb_separation_mm':20},
      'anchor_rule':{'front_outer_y':-depth/2,'edge_inset_to_flange_mm':side_inset,'height':'base_height/2','minimum_vertical_edge_and_seam_mm':margin},
      'scope':'10 panel proxies, 2 exact native H7159 assemblies, 1 product proxy; independent regeneration on resize; recessed wood overlap unresolved; no cutouts, mates, collision or production approval'}
    validate_pair(result,handles)
    return result


def validate_pair(plan,observed,tolerance_mm=.003):
    validate_datum(plan['datum'])
    by_id={r['id']:r for r in observed}
    if len(by_id)!=2 or len(observed)!=2 or set(by_id)!={'H7159-left','H7159-right'}:raise ValueError('missing or duplicate pair occurrence')
    for expected in plan['handles']:
        actual=validate_matrix(by_id[expected['id']]['matrix_mm'])
        if max(abs(actual[i][j]-expected['matrix_mm'][i][j]) for i in range(3) for j in range(3))>1e-6:raise ValueError('mount orientation drift')
        if max(abs(actual[3][j]-expected['matrix_mm'][3][j]) for j in range(3))>tolerance_mm:raise ValueError('wall/edge anchor drift')
        # Independent semantic oracle: never accept a forged plan as its own proof.
        anchor=point_at(plan['datum']['origin_mm'],actual)
        sign=-1 if expected['id']=='H7159-left' else 1
        semantic=[sign*(plan['size'][0]/2-100-80.5),-plan['size'][1]/2,(plan['size'][2]-80)/2]
        for declared in [expected.get('anchor_mm'),by_id[expected['id']].get('anchor_mm',semantic)]:
            if max(abs(a-b) for a,b in zip(_vec(declared),semantic))>tolerance_mm:raise ValueError('declared anchor differs from wall/edge equation')
        if max(abs(anchor[j]-semantic[j]) for j in range(3))>tolerance_mm:raise ValueError('independent wall/edge equation failed')
        for local,wanted in [(plan['datum']['outward'],[0,-1,0]),(plan['datum']['up'],[0,0,1])]:
            transformed=[sum(local[k]*actual[k][j] for k in range(3)) for j in range(3)]
            if max(abs(transformed[j]-wanted[j]) for j in range(3))>1e-6:raise ValueError('independent outward/up equation failed')
    anchors=[point_at(plan['datum']['origin_mm'],by_id[x]['matrix_mm']) for x in ['H7159-left','H7159-right']]
    if abs(anchors[0][0]+anchors[1][0])>tolerance_mm or max(abs(anchors[0][j]-anchors[1][j]) for j in [1,2])>tolerance_mm:raise ValueError('pair symmetry drift')
    return True
