"""Blocked offline wheel/dish preview; bbox centers are not contact datums."""
import copy

try:
    from .latch_placement import _need, _vector, _matrix, _center, TOL
except ImportError:
    from latch_placement import _need, _vector, _matrix, _center, TOL


def preview_wheels_sockets(wheel_rows, socket_rows, case_min, source_size, target_size):
    """Preserve known whole poses and expose missing evidence without inventing it.

    Rows contain id, matrix_world_mm (nullable for missing wheel poses), and
    local_bounds_mm. World XYZ axes match case axes; all lengths are mm. Only
    socket centers prove a complete XY grid. Wheel/socket contacts stay unproven.
    """
    for value in (case_min,source_size,target_size):
        _vector(value)
    _need(all(0 < v <= 10000 for v in source_size+target_size), 'Positive case sizes required')
    ids=set();normalized={'wheel':[],'socket':[]};missing=[]
    for role,inputs in [('wheel',wheel_rows),('socket',socket_rows)]:
        _need(type(inputs) is list and len(inputs)==4, 'Four whole '+role+' rows required')
        for original in inputs:
            _need(type(original) is dict and set(original)=={'id','matrix_world_mm','local_bounds_mm'},
                  'Exact whole-component fields required')
            node_id=original['id']
            _need(type(node_id) is int and 0 < node_id < 2**63 and node_id not in ids,'Unique source IDs required')
            ids.add(node_id);bounds=original['local_bounds_mm'];_vector(bounds,6)
            _need(all(bounds[i+3]>bounds[i] for i in range(3)), 'Positive local bbox required')
            row=copy.deepcopy(original);row['role']=role
            if row['matrix_world_mm'] is None:
                _need(role=='wheel','Socket pose cannot be missing')
                missing.append(node_id);continue
            _matrix(row['matrix_world_mm'])
            row['source_matrix_world_mm']=copy.deepcopy(row['matrix_world_mm'])
            row['bbox_center_local_mm'],row['source_bbox_center_world_mm']=_center(bounds,row['matrix_world_mm'])
            center=row['source_bbox_center_world_mm']
            _need(all(case_min[i]+TOL < center[i] < case_min[i]+source_size[i]-TOL for i in (0,1)),
                  'Candidate bbox center outside case XY')
            row['slot']=[int(center[i]>case_min[i]+source_size[i]/2) for i in (0,1)]
            normalized[role].append(row)
    sockets={tuple(r['slot']):r for r in normalized['socket']}
    _need(set(sockets)=={(0,0),(0,1),(1,0),(1,1)},'Four distinct socket XY slots required')
    for slot,row in sockets.items():
        center=row['source_bbox_center_world_mm']
        for axis in (0,1):
            opposite=list(slot);opposite[axis]=1-opposite[axis]
            expected=center[:];expected[axis]=2*case_min[axis]+source_size[axis]-center[axis]
            other=sockets[tuple(opposite)]['source_bbox_center_world_mm']
            _need(all(abs(expected[i]-other[i])<=TOL for i in range(3)), 'Full socket XY symmetry is broken')
    wheels={tuple(r['slot']):r for r in normalized['wheel']}
    _need(len(wheels)==len(normalized['wheel']),'Known wheel centers occupy duplicate candidate slots')
    pairs=[];predictions=[]
    for role in ('wheel','socket'):
        for row in sorted(normalized[role],key=lambda r:(r['slot'],r['id'])):
            delta=[row['slot'][i]*(target_size[i]-source_size[i]) for i in (0,1)]
            delta.append(target_size[2]-source_size[2] if role=='socket' else 0)
            for axis in range(3):row['matrix_world_mm'][3][axis]+=delta[axis]
            row['translation_mm']=delta
            row['bbox_center_local_mm'],row['bbox_center_world_mm']=_center(row['local_bounds_mm'],row['matrix_world_mm'])
            _need(all(case_min[i]+TOL < row['bbox_center_world_mm'][i] < case_min[i]+target_size[i]-TOL
                      for i in (0,1)),'Target XY dimensions collapse candidate slots')
            _need(all((row['bbox_center_world_mm'][i]>case_min[i]+target_size[i]/2)==bool(row['slot'][i])
                      and abs(row['bbox_center_world_mm'][i]-case_min[i]-target_size[i]/2)>TOL
                      for i in (0,1)), 'Target dimensions invert or collapse candidate slots')
            predictions.append(row)
    for slot,wheel in sorted(wheels.items()):
        socket=sockets[slot]
        pairs.append(dict(slot=list(slot),wheel_id=wheel['id'],socket_id=socket['id'],confirmed=False,
                          basis='bbox_xy_quadrant_candidate_only',
                          source_delta_xy_mm=[wheel['source_bbox_center_world_mm'][i]-socket['source_bbox_center_world_mm'][i]
                                              for i in (0,1)],
                          predicted_socket_bbox_xy_mm=socket['bbox_center_world_mm'][:2]))
    diagnostics=['WHEEL_SKU_UNRESOLVED','SOURCE_ORIENTATION_PARITY_UNVERIFIED','CONTACT_XY_ANCHORS_UNPROVEN']
    if missing:diagnostics.append('WHEEL_WORLD_MATRICES_MISSING')
    if any(abs(value)>TOL for pair in pairs for value in pair['source_delta_xy_mm']):
        diagnostics.append('BBOX_XY_CANDIDATES_DO_NOT_COINCIDE')
    return dict(status='blocked',scope='offline_bbox_candidate_preview',units='mm',production_approved=False,
                native_proof='NOT_RUN',diagnostics=diagnostics,missing_wheel_pose_ids=sorted(missing),
                predicted_occurrences=predictions,candidate_pairs=pairs,occurrences=[],
                source_size_mm=source_size[:],target_size_mm=target_size[:])
