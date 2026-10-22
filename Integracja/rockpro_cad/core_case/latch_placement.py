"""Whole 17251S latch pairs; axis-aligned case, mm, row-vector matrices."""
import copy
import itertools
import math

TOL = .003


def _need(valid, message):
    if not valid:
        raise ValueError(message)


def _vector(value, count=3):
    _need(type(value) is list and len(value) == count and
          all(type(v) in (int,float) and abs(v) <= 1e9 and math.isfinite(v) for v in value),
          'Finite numeric vector in mm required')


def _matrix(value):
    _need(type(value) is list and len(value) == 4, '4x4 row-vector matrix required')
    for row in value:
        _vector(row,4)
    _need(all(abs(value[i][3]) <= 1e-9 for i in range(3)) and abs(value[3][3]-1) <= 1e-9,
          'Affine row-vector matrix required')
    for i in range(3):
        for j in range(3):
            _need(abs(sum(value[i][k]*value[j][k] for k in range(3))-(i == j)) <= 1e-6,
                  'Opaque rigid orientation required; scale/shear forbidden')


def _center(bounds, matrix):
    local = [(bounds[i]+bounds[i+3])/2 for i in range(3)]
    world = [sum(local[k]*matrix[k][i] for k in range(3))+matrix[3][i] for i in range(3)]
    return local, world


def _symmetric(rows, case_min, size):
    for role in ('lid','base'):
        left = rows[('left',role)]['bbox_center_world_mm']
        right = rows[('right',role)]['bbox_center_world_mm']
        _need(abs(left[0]+right[0]-2*case_min[0]-size[0]) <= TOL and
              all(abs(left[i]-right[i]) <= TOL for i in (1,2)),
              'Whole latch centers must be left/right symmetric')


def _fits(rows, case_min, size):
    x_limits = {'left':[],'right':[]}
    for (side,role),row in rows.items():
        bounds,matrix = row['local_bounds_mm'],row['matrix_world_mm']
        for point in itertools.product(*[(bounds[i],bounds[i+3]) for i in range(3)]):
            world = [sum(point[k]*matrix[k][i] for k in range(3))+matrix[3][i] for i in range(3)]
            _need(all(case_min[i]-TOL <= world[i] <= case_min[i]+size[i]+TOL for i in (0,2)),
                  'Whole latch bbox does not fit case width/height')
            x_limits[side].append(world[0])
    _need(max(x_limits['left'])+TOL < min(x_limits['right']), 'Left/right latch groups overlap')


def plan_latch_pairs(source_rows, case_min, source_size, target_size, source_lid_height=104.13):
    """Keep each complete lid/base pair intact, with fixed 150mm root edge gaps.

    Front placement is unchanged; both halves receive exactly the same XYZ
    translation. Lid height stays fixed, so height resize moves both halves by
    total height change. Existing opaque source orientation/parity is preserved.
    """
    for vector in (case_min,source_size,target_size):
        _vector(vector)
    _vector([source_lid_height],1)
    _need(0 < source_lid_height < min(source_size[2],target_size[2]) and
          all(0 < v <= 10000 for v in source_size+target_size) and
          min(source_size[0],target_size[0]) > 300, 'Infeasible case or fixed lid height')
    _need(type(source_rows) is list and len(source_rows) == 4, 'Four whole latch assemblies required')
    rows,ids = {},set()
    for original in source_rows:
        _need(type(original) is dict and set(original) ==
              {'id','role','side','matrix_world_mm','local_bounds_mm'}, 'Exact whole-assembly fields required')
        node_id = original['id']
        _need(type(node_id) is int and 0 < node_id < 2**63 and node_id not in ids, 'Unique positive source ID required')
        ids.add(node_id)
        _need(type(original['role']) is str and type(original['side']) is str, 'Explicit role/side required')
        key = (original['side'],original['role'])
        _need(key in {('left','lid'),('left','base'),('right','lid'),('right','base')} and key not in rows,
              'Exactly one lid/base assembly on each side required')
        _matrix(original['matrix_world_mm'])
        bounds = original['local_bounds_mm']
        _vector(bounds,6)
        _need(all(bounds[i+3] > bounds[i] for i in range(3)), 'Positive local bbox required')
        row = copy.deepcopy(original)
        row['bbox_center_local_mm'],row['bbox_center_world_mm'] = _center(bounds,row['matrix_world_mm'])
        rows[key] = row
    for side in ('left','right'):
        lid,base = [rows[(side,role)]['matrix_world_mm'][3][:3] for role in ('lid','base')]
        _need(all(abs(lid[i]-base[i]) <= TOL for i in range(3)), 'Pair halves must share source origin')
        expected_x = case_min[0]+(150 if side == 'left' else source_size[0]-150)
        _need(abs(lid[0]-expected_x) <= TOL, 'Source latch root must retain 150mm edge offset')
    left,right = [rows[(side,'lid')]['matrix_world_mm'][3] for side in ('left','right')]
    _need(all(abs(left[i]-right[i]) <= TOL for i in (1,2)) and
          case_min[1]-TOL <= left[1] < case_min[1]+source_size[1]/2, 'Shared front-wall placement required')
    _symmetric(rows,case_min,source_size)
    for (side,role),row in rows.items():
        delta = [target_size[0]-source_size[0] if side == 'right' else 0,0,target_size[2]-source_size[2]]
        for axis in range(3):
            row['matrix_world_mm'][3][axis] += delta[axis]
        row['translation_mm'] = delta
        row['bbox_center_local_mm'],row['bbox_center_world_mm'] = _center(row['local_bounds_mm'],row['matrix_world_mm'])
    _symmetric(rows,case_min,target_size)
    _need(left[1] < case_min[1]+target_size[1]/2, 'Target depth cannot contain front placement')
    _fits(rows,case_min,target_size)
    return dict(status='planned',production_approved=False,units='mm',source_size_mm=source_size[:],
                target_size_mm=target_size[:],lid_height_mm=source_lid_height,
                occurrences=[rows[(side,role)] for side in ('left','right') for role in ('lid','base')])
