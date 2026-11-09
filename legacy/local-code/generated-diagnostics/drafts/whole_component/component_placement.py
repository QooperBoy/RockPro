"""Whole-component bbox centers and opaque rigid poses, without native imports.

Matrices use row vectors, with translation in row 3. Case coordinates start at
the minimum XYZ corner. Existing source reflections remain opaque; resize adds
proper translation only. This contract makes no mounting or production approval.
"""
import copy
import hashlib
import itertools
import json
import math
import re

POSITION_TOLERANCE_MM = .003
ORIENTATION_TOLERANCE = 1e-6


class ComponentPlacementError(ValueError):
    """Invalid, inconsistent or unbound whole-component placement."""


def _need(condition, message):
    if not condition:
        raise ComponentPlacementError(message)


def _object(value, fields):
    _need(type(value) is dict and set(value) == set(fields), 'Exact versioned fields required')


def _number(value):
    _need(type(value) in (int, float), 'Finite numbers required; bool is not numeric')
    try:
        valid = math.isfinite(value) and abs(value) <= 1e9
    except OverflowError:
        valid = False
    _need(valid, 'Finite bounded numbers required')
    return value


def _vector(value, length=3):
    _need(type(value) is list and len(value) == length, 'Incorrect vector length')
    for item in value:
        _number(item)
    return value


def _id(value):
    _need(type(value) is int and 0 < value < 2**63, 'Positive integer source_id required')
    return value


def _source(value):
    _object(value, ('id', 'sha256'))
    _need(type(value['id']) is str and 0 < len(value['id']) <= 200 and
          value['id'].strip() == value['id'], 'Explicit source identity required')
    _need(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
          'Explicit lowercase source SHA256 required')


def _size(value):
    _vector(value)
    _need(all(0 < item <= 10000 for item in value), 'Positive case size in mm required')


def _matrix(value, proper=False):
    _need(type(value) is list and len(value) == 4, '4x4 matrix required')
    for row in value:
        _vector(row, 4)
    _need(all(abs(value[i][3]) <= 1e-9 for i in range(3)) and abs(value[3][3]-1) <= 1e-9,
          'Affine row-vector matrix required')
    for i in range(3):
        for j in range(3):
            dot = sum(value[i][k]*value[j][k] for k in range(3))
            _need(abs(dot-(1 if i == j else 0)) <= ORIENTATION_TOLERANCE,
                  'Rigid orthogonal orientation required; scale/shear forbidden')
    a,b,c = value[:3]
    det = (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+
           a[2]*(b[0]*c[1]-b[1]*c[0]))
    _need(abs(det-(1 if proper else round(det))) <= 3*ORIENTATION_TOLERANCE and
          (det > 0 if proper else abs(abs(det)-1) <= 3*ORIENTATION_TOLERANCE),
          'Proper case frame required' if proper else 'Rigid source parity required')
    return 1 if det > 0 else -1


def _bounds(value):
    _vector(value, 6)
    _need(all(value[i+3] > value[i] for i in range(3)), 'Positive local bbox extents required')
    return [(value[i]+value[i+3])/2 for i in range(3)]


def _transform(point, matrix):
    return [sum(point[k]*matrix[k][i] for k in range(3))+matrix[3][i] for i in range(3)]


def _case(point, frame):
    return [sum((point[k]-frame[3][k])*frame[i][k] for k in range(3)) for i in range(3)]


def _near(a, b, tolerance=POSITION_TOLERANCE_MM):
    return all(abs(x-y) <= tolerance for x,y in zip(a,b))


def _symmetry(rows, dimensions):
    """Reflect full XYZ tuples about each case midplane, paired by explicit slots."""
    by_slot = {tuple(row['slot']): row['bbox_center_case_mm'] for row in rows}
    _need(set(by_slot) == set(itertools.product((0,1), repeat=3)), 'Eight unique XYZ slots required')
    points = list(by_slot.values())
    _need(not any(_near(a,b) for i,a in enumerate(points) for b in points[i+1:]),
          'Eight distinct whole-component centers required')
    for slot,point in by_slot.items():
        _need(all(-POSITION_TOLERANCE_MM <= point[i] <= dimensions[i]+POSITION_TOLERANCE_MM
                  for i in range(3)), 'Whole-component center outside case frame')
        _need(all((point[i] <= dimensions[i]/2 if slot[i] == 0 else point[i] >= dimensions[i]/2)
                  for i in range(3)), 'Center contradicts explicit slot')
        for axis in range(3):
            opposite = list(slot)
            opposite[axis] = 1-opposite[axis]
            expected = point[:]
            expected[axis] = dimensions[axis]-expected[axis]
            _need(_near(expected,by_slot[tuple(opposite)]), 'Full XYZ group symmetry is broken')


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def plan_component_placement(request):
    """Return a detached deterministic eight-component translation plan.

    Source binding is explicit caller evidence, not authentication or disk I/O.
    Centers are transformed local-bbox centers, never guessed mounting contacts.
    """
    _object(request, ('schema_version','units','source','case_frame','target_size_mm','components'))
    _need(type(request['schema_version']) is int and request['schema_version'] == 1 and
          request['units'] == 'mm', 'Version 1 and mm units required')
    _source(request['source'])
    _object(request['case_frame'], ('matrix_world_mm','size_mm'))
    frame = request['case_frame']['matrix_world_mm']
    _matrix(frame, proper=True)
    dimensions = request['case_frame']['size_mm']
    target = request['target_size_mm']
    _size(dimensions)
    _size(target)
    _need(type(request['components']) is list and len(request['components']) == 8,
          'Exactly eight whole components required')
    source_rows = []
    ids = set()
    for row in request['components']:
        _object(row, ('source_id','slot','matrix_world_mm','local_bounds_mm'))
        node_id = _id(row['source_id'])
        _need(node_id not in ids, 'Duplicate source component')
        ids.add(node_id)
        slot = row['slot']
        _need(type(slot) is list and len(slot) == 3 and
              all(type(i) is int and i in (0,1) for i in slot), 'Explicit binary XYZ slot required')
        parity = _matrix(row['matrix_world_mm'])
        local_center = _bounds(row['local_bounds_mm'])
        world_center = _transform(local_center,row['matrix_world_mm'])
        source_rows.append(dict(source_id=node_id, slot=slot[:], source_parity=parity,
                                bbox_center_local_mm=local_center,
                                bbox_center_case_mm=_case(world_center,frame)))
    _symmetry(source_rows, dimensions)
    inputs = {row['source_id']: row for row in request['components']}
    rows = []
    for item in sorted(source_rows,key=lambda row:row['source_id']):
        original = inputs[item['source_id']]
        delta_case = [item['slot'][i]*(target[i]-dimensions[i]) for i in range(3)]
        delta_world = [sum(delta_case[k]*frame[k][i] for k in range(3)) for i in range(3)]
        matrix = copy.deepcopy(original['matrix_world_mm'])
        for axis in range(3):
            matrix[3][axis] += delta_world[axis]
        world_center = _transform(item['bbox_center_local_mm'],matrix)
        rows.append(dict(item, occurrence_id=request['source']['id']+'/'+str(item['source_id']),
                         matrix_world_mm=matrix, local_bounds_mm=copy.deepcopy(original['local_bounds_mm']),
                         bbox_center_world_mm=world_center, bbox_center_case_mm=_case(world_center,frame)))
    _symmetry(rows,target)
    canonical_request = copy.deepcopy(request)
    canonical_request['components'].sort(key=lambda row:row['source_id'])
    plan = dict(schema_version=1,units='mm',status='planned',production_approved=False,
                scope='whole_component_bbox_placement_only',source=copy.deepcopy(request['source']),
                request=canonical_request,components=rows)
    plan['content_sha256'] = _hash(plan)
    return plan


def validate_component_placement(plan, observed):
    """Replay intent, then compare eight measured whole poses and local bounds.

    Observation order is irrelevant. Pose translation uses .003mm tolerance;
    orientation coefficients use 1e-6. Internal geometry is outside this API.
    """
    _need(type(plan) is dict and 'request' in plan, 'Bound placement plan required')
    expected = plan_component_placement(plan['request'])
    _need(plan == expected and _hash(plan) == _hash(expected),
          'Plan differs from independently replayed request')
    _object(observed, ('schema_version','units','source','components'))
    _need(type(observed['schema_version']) is int and observed['schema_version'] == 1 and
          observed['units'] == 'mm', 'Version 1 and mm units required')
    _source(observed['source'])
    _need(observed['source'] == expected['source'], 'Observation source identity/SHA mismatch')
    _need(type(observed['components']) is list and len(observed['components']) == 8,
          'Eight observed components required')
    measured = {}
    for row in observed['components']:
        _object(row, ('occurrence_id','source_id','matrix_world_mm','local_bounds_mm'))
        node_id = _id(row['source_id'])
        _need(node_id not in measured, 'Duplicate observed component')
        _need(type(row['occurrence_id']) is str, 'Stable occurrence ID required')
        _matrix(row['matrix_world_mm'])
        _bounds(row['local_bounds_mm'])
        measured[node_id] = row
    centers = []
    for row in expected['components']:
        actual = measured.get(row['source_id'])
        _need(actual is not None and actual['occurrence_id'] == row['occurrence_id'],
              'Missing or mismatched occurrence identity')
        _need(_near(actual['local_bounds_mm'],row['local_bounds_mm']), 'Local bbox drift')
        for axis in range(4):
            _need(_near(actual['matrix_world_mm'][axis],row['matrix_world_mm'][axis],
                        POSITION_TOLERANCE_MM if axis == 3 else ORIENTATION_TOLERANCE),
                  'Measured component pose differs from expected pose')
        local = _bounds(actual['local_bounds_mm'])
        world = _transform(local,actual['matrix_world_mm'])
        case = _case(world,expected['request']['case_frame']['matrix_world_mm'])
        _need(_near(world,row['bbox_center_world_mm']) and _near(case,row['bbox_center_case_mm']),
              'Measured whole-component bbox center drift')
        centers.append(dict(slot=row['slot'],bbox_center_case_mm=case))
    _symmetry(centers,expected['request']['target_size_mm'])
    return True
