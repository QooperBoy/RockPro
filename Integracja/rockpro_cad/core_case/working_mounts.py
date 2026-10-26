"""Source-mounted parts as a provisional standard, without manufacturing inference.

This offline reference is not an executable template or a new MCP capability.
Positions are geometric frames, not native anchor/PositionTransform expressions.
"""
import copy
import hashlib
import json
import math
import re


def _sha(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError('Exact SHA256 required')
    return value


def _vector(value,length):
    if not isinstance(value,list) or len(value)!=length or any(
            type(x) not in (int,float) or not math.isfinite(x) for x in value):
        raise ValueError('Finite numeric coordinates required')
    return value


def _frame(value):
    if not isinstance(value,list) or len(value)!=4:raise ValueError('4x4 frame required')
    for row in value:_vector(row,4)
    if any(abs(value[i][3])>1e-8 for i in range(3)) or abs(value[3][3]-1)>1e-8:
        raise ValueError('Affine row-vector frame required')
    for i in range(3):
        for j in range(3):
            if abs(sum(value[i][k]*value[j][k] for k in range(3))-(i==j))>1e-6:
                raise ValueError('Rigid frame required; scaling hardware is forbidden')
    return copy.deepcopy(value)  # Reflections are preserved, not normalized away.


def build_working_standard(inventory_bytes,source_sha256,inventory_sha256):
    """Pin exact native read bytes; preserve every assembly/part and unknown field."""
    source_sha256=_sha(source_sha256);inventory_sha256=_sha(inventory_sha256)
    if hashlib.sha256(inventory_bytes).hexdigest()!=inventory_sha256:
        raise ValueError('Inventory revision changed')
    data=json.loads(inventory_bytes.decode('utf-8-sig'))
    if data.get('source_sha256')!=source_sha256:raise ValueError('Source revision mismatch')
    rows=data.get('rows')
    if not isinstance(rows,list) or not 1<=len(rows)<=20000:raise ValueError('Bounded inventory required')
    paths=set();ids=set();nodes=[]
    for row in rows:
        node_id=row['id'];path=row['path'];kind=row['type']
        if type(node_id) is not int or node_id<1 or node_id in ids:raise ValueError('Distinct positive source IDs required')
        if not isinstance(path,str) or not re.fullmatch(r'root(?:/[1-9][0-9]*)*',path) or path in paths:
            raise ValueError('Distinct explicit source paths required')
        if path!='root' and int(path.rsplit('/',1)[1])!=node_id:raise ValueError('Path and ID disagree')
        if kind not in ('Z_ELEMENT_UNKNOWN','Z_ELEMENT_ASSEMBLY','Z_ELEMENT_PART'):
            raise ValueError('Only hierarchy nodes belong in a mounting reference')
        ids.add(node_id);paths.add(path)
        bounds=row.get('bounds_local_m')
        if bounds is not None:
            _vector(bounds,6)
            if any(bounds[i]>bounds[i+3] for i in range(3)):raise ValueError('Invalid local bounds')
        nodes.append({'source_reference_key':source_sha256+':'+path,'source_node_id':node_id,
            'source_path':path,'parent_path':path.rsplit('/',1)[0] if '/' in path else None,
            'name_raw':row['name'],'type':kind,'world_frame_mm':_frame(row['world_mm']),
            'parent_frame_mm':_frame(row['parent_mm']),'body_bounds_local_m':copy.deepcopy(bounds),
            'source_feature_metadata':copy.deepcopy(row.get('features')),
            'semantic_role':'unmapped','requires_plywood_cutout':'unknown',
            'machining_owner_links':[],'mounting_basis':'source_revision'})
    if 'root' not in paths or any(n['parent_path'] not in paths for n in nodes if n['parent_path']):
        raise ValueError('Complete source hierarchy required')
    return {'schema':'rockpro.working-mount-standard/1','source_sha256':source_sha256,
            'inventory_sha256':inventory_sha256,'units':'mm (frames), m (raw body bounds)',
            'status':'provisional_source_standard','approval_basis':'user_requested_working_standard',
            'device_fit_confirmed':False,'production_approved':False,'executable_template':False,
            'native_api_version':data.get('api_version'),'read_errors':copy.deepcopy(data.get('errors',[])),
            'nodes':nodes,'physical_part_count':sum(n['type']=='Z_ELEMENT_PART' for n in nodes)}


def plan_component_translation(standard,source_path,delta_world_mm):
    """Predict a rigid subtree translation, preserving source bodies and rotations.

    Native execution must separately account for anchors, refresh and validation.
    A sketch outside the subtree needs explicit ownership before it can follow.
    """
    if standard.get('schema')!='rockpro.working-mount-standard/1' or standard.get('executable_template') is not False:
        raise ValueError('Non-executable working standard required')
    delta=_vector(delta_world_mm,3)
    by_path={n['source_path']:n for n in standard['nodes']}
    root=by_path.get(source_path)
    if root is None or root['parent_path'] is None or root['type'] not in ('Z_ELEMENT_ASSEMBLY','Z_ELEMENT_PART'):
        raise ValueError('An explicit source component is required')
    parent=by_path[root['parent_path']]['world_frame_mm']
    parent=_frame(parent)
    # For an orthogonal frame (including reflection), inverse is transpose.
    local_delta=[sum(delta[j]*parent[i][j] for j in range(3)) for i in range(3)]
    targets=[]
    for node in standard['nodes']:
        moving=node['source_path']==source_path or node['source_path'].startswith(source_path+'/')
        matrix=_frame(node['world_frame_mm'])
        if moving:
            matrix[3][:3]=_vector([matrix[3][j]+delta[j] for j in range(3)],3)
        targets.append({'source_reference_key':node['source_reference_key'],'moving':moving,
                        'world_frame_mm':matrix})
    initial=root['parent_frame_mm'][3]
    return {'schema':'rockpro.component-translation-reference/1',
            'source_sha256':standard['source_sha256'],'component_path':source_path,
            'root_geometry_parent_translation_mm':_vector([initial[i]+local_delta[i] for i in range(3)],3),
            'targets':targets,'catalog_geometry_scaled':False,'body_geometry_changed':False,
            'machining_link_mode':'inherited source hierarchy only; cross-component ownership unresolved',
            'executable_template':False,'native_execution':'NOT RUN by this offline planner'}
