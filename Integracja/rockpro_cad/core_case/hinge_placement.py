"""Offline candidate for four whole 270836 lid/base assemblies, in mm.

B1930 is a brace, never a hinge. Source roots remain opaque; bbox centers, not
root origins, define group symmetry. Row-vector world axes match the case axes.
"""
import copy

try:
    from .latch_placement import _need, _vector, _matrix, _center, TOL
except ImportError:
    from latch_placement import _need, _vector, _matrix, _center, TOL


def _symmetry(rows, case_min, size):
    for role in ('lid','base'):
        left,right = [rows[(side,role)]['bbox_center_world_mm'] for side in ('left','right')]
        _need(abs(left[0]+right[0]-2*case_min[0]-size[0]) <= TOL and
              all(abs(left[i]-right[i]) <= TOL for i in (1,2)), 'Whole hinge centers are asymmetric')
        _need(left[0] < case_min[0]+size[0]/2-TOL < right[0], 'Left/right hinge groups are degenerate')


def plan_hinge_pairs(source_rows, case_min, source_size, target_size, source_lid_height=104.13,
                     *, source_pose_verified=False):
    """Preserve two complete back-wall pairs, without normalizing source offsets.

    A caller must independently prove original orientation/parity before setting
    source_pose_verified. Without that proof, predicted rows are for inspection
    only; executable occurrences remain empty. This never grants production use.
    """
    for value in (case_min,source_size,target_size):
        _vector(value)
    _vector([source_lid_height],1)
    _need(type(source_pose_verified) is bool, 'Explicit pose evidence state required')
    _need(all(0 < n <= 10000 for n in source_size+target_size) and
          0 < source_lid_height < min(source_size[2],target_size[2]), 'Infeasible size or fixed lid height')
    _need(type(source_rows) is list and len(source_rows) == 4, 'Four whole hinge assemblies required')
    rows,ids = {},set()
    for original in source_rows:
        _need(type(original) is dict and set(original) ==
              {'id','role','side','matrix_world_mm','local_bounds_mm'}, 'Exact whole-assembly fields required')
        node_id = original['id']
        _need(type(node_id) is int and 0 < node_id < 2**63 and node_id not in ids, 'Unique positive source ID required')
        ids.add(node_id)
        _need(type(original['side']) is str and type(original['role']) is str, 'Explicit side/role required')
        key = (original['side'],original['role'])
        _need(key in {('left','lid'),('left','base'),('right','lid'),('right','base')} and key not in rows,
              'One lid and base on each side required')
        _matrix(original['matrix_world_mm'])
        bounds = original['local_bounds_mm']
        _vector(bounds,6)
        _need(all(bounds[i+3] > bounds[i] for i in range(3)), 'Positive local bbox required')
        row = copy.deepcopy(original)
        row['source_matrix_world_mm'] = copy.deepcopy(original['matrix_world_mm'])
        row['bbox_center_local_mm'],row['bbox_center_world_mm'] = _center(bounds,row['matrix_world_mm'])
        row['root_to_bbox_center_world_mm'] = [row['bbox_center_world_mm'][i]-row['matrix_world_mm'][3][i]
                                               for i in range(3)]
        rows[key] = row
    for side in ('left','right'):
        lid,base = [rows[(side,role)]['matrix_world_mm'][3][:3] for role in ('lid','base')]
        _need(all(abs(lid[i]-base[i]) <= TOL for i in range(3)), 'Hinge halves must share source joint origin')
        _need(lid[1] > case_min[1]+source_size[1]/2, 'Back-wall hinge placement required')
    _symmetry(rows,case_min,source_size)
    for (side,role),row in rows.items():
        delta = [target_size[0]-source_size[0] if side == 'right' else 0,
                 target_size[1]-source_size[1],target_size[2]-source_size[2]]
        for axis in range(3):
            row['matrix_world_mm'][3][axis] += delta[axis]
        row['translation_mm'] = delta
        row['bbox_center_local_mm'],row['bbox_center_world_mm'] = _center(row['local_bounds_mm'],row['matrix_world_mm'])
    _symmetry(rows,case_min,target_size)
    predicted = [rows[(side,role)] for side in ('left','right') for role in ('lid','base')]
    return dict(status='planned' if source_pose_verified else 'blocked',scope='offline_hinge_candidate',
                units='mm',production_approved=False,native_proof='NOT_RUN',
                diagnostics=[] if source_pose_verified else ['SOURCE_ORIENTATION_PARITY_UNVERIFIED'],
                source_size_mm=source_size[:],target_size_mm=target_size[:],lid_height_mm=source_lid_height,
                predicted_occurrences=predicted,occurrences=copy.deepcopy(predicted) if source_pose_verified else [])
