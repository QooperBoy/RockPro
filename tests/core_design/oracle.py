"""Independent assertions on observations, never a planner or native CAD reader.

All expected dimensions/anchor slots come from frozen synthetic literals. Matrix
math here only checks an observed local-to-closed transform and rigid rotation.
"""
import math
import itertools

TOL = 1e-6  # mm / dimensionless test tolerance, not production tolerance
FAMILIES = {'plates', 'profiles', 'corners', 'braces', 'handles', 'latches',
            'hinges', 'wheels', 'sockets', 'interior'}


def near(actual, expected, label='value'):
    if isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected), label + ': length'
        for a, e in zip(actual, expected):
            near(a, e, label)
    else:
        assert type(actual) in (int, float) and math.isfinite(actual), label + ': finite numeric'
        assert abs(actual - expected) <= TOL, f'{label}: {actual} != {expected}'


def determinant(m):
    return (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
            -m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
            +m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))


def rigid(rotation):
    assert len(rotation) == 3 and all(len(r) == 3 for r in rotation), 'rotation shape'
    for i in range(3):
        for j in range(3):
            near(sum(rotation[k][i]*rotation[k][j] for k in range(3)),
                 1 if i == j else 0, 'orthonormal rotation')
    near(determinant(rotation), 1, 'proper rotation (no reflection)')


def closed_point(frame, uvn):
    return [frame['origin'][i] + sum(frame['rotation'][i][j]*uvn[j] for j in range(3))
            for i in range(3)]


def validate(case, observation):
    expected = case['expected']
    assert observation['status'] == 'planned', 'plan status'
    assert observation['units'] == 'mm', 'units'
    for key in ('internal', 'plywood_external', 'base_height', 'lid_height'):
        near(observation[key], expected[key], key)
    # Transport dimensions must be distinguished from the bare plywood envelope.
    near(observation['transport_external'], expected['transport_external'], 'transport envelope')
    near(observation['transport_bounds'], expected['transport_bounds'], 'transport bounds')
    frames = observation['frames']
    assert set(frames) == set(expected['frames']), 'wall frame inventory'
    for name, frame in expected['frames'].items():
        near(frames[name]['origin'], frame['origin'], name + ' origin')
        near(frames[name]['rotation'], frame['rotation'], name + ' wall axes')
        rigid(frames[name]['rotation'])
    groups = observation['groups']
    assert len({g['symmetry_group_id'] for g in groups}) == len(groups), 'duplicate symmetry group'
    by_group = {g['symmetry_group_id']: g for g in groups}
    assert set(by_group) == set(expected['groups']), 'missing or extra symmetry group'
    assert {g['family'] for g in groups} == FAMILIES, 'family completeness'
    parts = observation['occurrences']
    assert len({p['id'] for p in parts}) == len(parts), 'duplicate occurrence ID'
    by_part = {p['id']: p for p in parts}
    expected_ids = {p['id'] for g in expected['groups'].values() for p in g['members']}
    assert set(by_part) == expected_ids, 'unaccounted or missing physical occurrence'
    assert set(observation['inventory']['physical_ids']) == expected_ids, 'inventory completeness'
    assert len(observation['inventory']['physical_ids']) == len(expected_ids), 'duplicate inventory ID'
    assert observation['inventory']['unresolved_ids'] == [], 'unresolved physical role'
    assert observation['inventory']['empty_assembly_ids'] == ['synthetic-empty'], 'assembly accounting'
    assert 'synthetic-empty' not in by_part, 'empty assembly is not a purchased part'
    claimed = []
    for group_id, eg in expected['groups'].items():
        group = by_group[group_id]
        for key in ('family', 'mode', 'datum', 'axes', 'scope', 'exception_approval'):
            assert group[key] == eg[key], group_id + ': ' + key
        ids = [p['id'] for p in eg['members']]
        assert group['members'] == ids, group_id + ': member inventory/order'
        claimed += ids
        for ep in eg['members']:
            p = by_part[ep['id']]
            assert p['frame'] == ep['frame'], p['id'] + ': incorrect wall/local frame'
            near(p['uvn'], ep['uvn'], p['id'] + ': edge/height anchor')
            near(p['closed_xyz'], closed_point(expected['frames'][ep['frame']], ep['uvn']), p['id'] + ': closed position')
            near(p['rotation'], ep['rotation'], p['id'] + ': catalog orientation')
            rigid(p['rotation'])
            near(p['shape'], ep['shape'], p['id'] + ': thickness/section/rigid geometry')
            near(p['local_bounds'], ep['local_bounds'], p['id'] + ': approved synthetic local bounds')
        # Check actual symmetry in the declared local datum, in addition to exact slots.
        for axis, center in eg['centers'].items():
            k = int(axis)
            values = sorted(by_part[i]['uvn'][k] for i in ids)
            near([v + w for v, w in zip(values, reversed(values))], [2*center]*len(values), group_id + ': symmetry')
    assert len(claimed) == len(set(claimed)), 'occurrence belongs to multiple groups'
    # Paired halves and stacking must share physical closed coordinates regardless of display gap.
    for pair in expected['pairs']:
        a, b = (by_part[i] for i in pair['members'])
        for axis in pair['axes']:
            near(a['closed_xyz'][axis], b['closed_xyz'][axis], 'closed pair ' + pair['kind'])
    corners = []
    for p in parts:
        for point in itertools.product(*zip(*p['local_bounds'])):
            corners.append([p['closed_xyz'][i] + sum(p['rotation'][i][j]*point[j] for j in range(3)) for i in range(3)])
    measured = [[fn(p[i] for p in corners) for i in range(3)] for fn in (min, max)]
    near(measured, expected['transport_bounds'], 'observed synthetic full physical bounds')
    return observation


def specimen(case):
    """Create a known observation for testing the oracle itself ONLY.

    It copies literal expected data, so is never used as planner implementation or
    as the actual result in a RED test. It proves mutation detection, not geometry.
    """
    import copy
    e = copy.deepcopy(case['expected'])
    groups, occurrences = [], []
    for group_id, group in e.pop('groups').items():
        members = group.pop('members')
        group.pop('centers')
        groups.append(dict(group, symmetry_group_id=group_id, members=[p['id'] for p in members]))
        for part in members:
            frame = e['frames'][part['frame']]
            occurrences.append(dict(part, closed_xyz=closed_point(frame, part['uvn'])))
    e.pop('pairs')
    return dict(e, status='planned', units='mm', groups=groups, occurrences=occurrences,
                inventory={'physical_ids': [p['id'] for p in occurrences], 'unresolved_ids': [],
                           'empty_assembly_ids': ['synthetic-empty']})
