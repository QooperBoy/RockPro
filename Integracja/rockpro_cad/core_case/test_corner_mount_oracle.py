"""Independent eight-corner equations and adversarial observation checks; no CAD."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case import corner_mount as api
from rockpro_cad.core_case.test_corner_mount import make_fixture


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def point(p, m):
    return [sum(p[k] * m[k][j] for k in range(3)) + m[3][j] for j in range(3)]


def product(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def inverse(m):
    result = [[m[j][i] for j in range(3)] + [0] for i in range(3)]
    result += [[-sum(m[3][k] * m[j][k] for k in range(3)) for j in range(3)] + [1]]
    return result


def determinant(m):
    return sum(m[0][i] * (m[1][(i+1)%3] * m[2][(i+2)%3]
                          - m[1][(i+2)%3] * m[2][(i+1)%3]) for i in range(3))


def independently_observed(evidence, trusted, size):
    frame = evidence['case_frame']['matrix_world_mm']
    previous_size = evidence['case_frame']['size_mm']
    parents = {x['id']: x['matrix_world_mm'] for x in evidence['assemblies']}
    slots = {x['id']: x['slot'] for x in trusted['occurrence_bindings']}
    rows = copy.deepcopy(evidence['occurrences'])
    for row in rows:
        delta = [slots[row['id']][j] * (size[j] - previous_size[j]) for j in range(3)]
        for j in range(3):
            row['matrix_world_mm'][3][j] += sum(delta[k] * frame[k][j] for k in range(3))
        row['matrix_parent_mm'] = product(row['matrix_world_mm'], inverse(parents[row['assembly_id']]))
    planes = []
    for original in evidence['case_frame']['panel_planes']:
        plane = copy.deepcopy(original)
        axis, side = plane['axis'], plane['side']
        other = [j for j in range(3) if j != axis]
        vertices = []
        for u, v in itertools.product((0, 1), repeat=2):
            p = [0, 0, 0]
            p[axis] = size[axis] * side
            p[other[0]], p[other[1]] = size[other[0]] * u, size[other[1]] * v
            vertices.append(point(p, frame))
        plane['vertices_world_mm'] = vertices
        planes.append(plane)
    return dict(schema_version=1, units='mm', case_frame=dict(matrix_world_mm=copy.deepcopy(frame),
                size_mm=list(size), panel_planes=planes), assemblies=copy.deepcopy(evidence['assemblies']),
                occurrences=rows)


def move_source_in_case(evidence, index, delta):
    frame = evidence['case_frame']['matrix_world_mm']
    row = evidence['occurrences'][index]
    parent = next(x['matrix_world_mm'] for x in evidence['assemblies'] if x['id'] == row['assembly_id'])
    for j in range(3):
        row['matrix_world_mm'][3][j] += sum(delta[k] * frame[k][j] for k in range(3))
    row['matrix_parent_mm'] = product(row['matrix_world_mm'], inverse(parent))


class CornerMountOracleTests(unittest.TestCase):
    def fixture(self):
        e, t = make_fixture()
        return e, t, api.capture_corner_binding(e, t)

    def assert_refused_capture(self, e, t):
        t['evidence_content_sha256'] = digest(e)
        before = copy.deepcopy((e, t))
        with self.assertRaises(ValueError):
            api.capture_corner_binding(e, t)
        self.assertEqual((e, t), before)

    def test_grid_uses_independent_world_equations_and_preserves_parity(self):
        e, t, binding = self.fixture()
        original = api.plan_corner_resize(binding, [900, 600, 330])
        for size in ([901, 600, 330], [900, 601, 330], [900, 600, 331],
                     [1100, 720, 410], [850, 550, 300], [900, 600, 330]):
            with self.subTest(size=size):
                plan = api.plan_corner_resize(binding, size)
                expected = independently_observed(e, t, size)
                by_id = {r['id']: r for r in expected['occurrences']}
                self.assertEqual(len(plan['occurrences']), 8)
                self.assertEqual([r['occurrence_id'] for r in plan['occurrences']],
                                 [r['occurrence_id'] for r in original['occurrences']])
                for row in plan['occurrences']:
                    wanted = by_id[row['id']]
                    self.assertEqual(row['matrix_world_mm'], wanted['matrix_world_mm'])
                    self.assertEqual(row['matrix_parent_mm'], wanted['matrix_parent_mm'])
                    self.assertEqual(row['body_signature'], wanted['body_signature'])
                    self.assertEqual(row['local_bounds_mm'], wanted['local_bounds_mm'])
                    self.assertAlmostEqual(determinant(row['requested_motion_mm']), 1)
                    self.assertAlmostEqual(determinant(row['matrix_world_mm']), determinant(row['source_world_mm']))
                    self.assertEqual(product(row['source_world_mm'], row['requested_motion_mm']), row['matrix_world_mm'])
                self.assertTrue(api.validate_corner_observation(plan, expected))
        self.assertEqual(api.plan_corner_resize(binding, [900, 600, 330]), original)

    def test_central_symmetry_does_not_replace_three_axis_group_symmetry(self):
        e, t = make_fixture()
        # Both marginal X coordinates and center inversion remain paired, while
        # reflection across X alone no longer finds the corresponding Y/Z tuple.
        move_source_in_case(e, 0, [1, 0, 0])
        move_source_in_case(e, 7, [-1, 0, 0])
        self.assert_refused_capture(e, t)

    def test_plane_origin_separation_normals_and_unique_sides_are_evidence(self):
        for mutation in ('size', 'origin', 'normal', 'duplicate_side', 'missing', 'duplicate_face'):
            e, t = make_fixture()
            cf = e['case_frame']
            if mutation == 'size': cf['size_mm'][0] += 5
            elif mutation == 'origin': cf['matrix_world_mm'][3][0] += 5
            elif mutation == 'normal': cf['panel_planes'][0]['normal_world'] = [0, 0, 0]
            elif mutation == 'duplicate_side': cf['panel_planes'][1]['side'] = 0
            elif mutation == 'missing': cf['panel_planes'].pop()
            else:
                cf['panel_planes'][1]['node_id'] = cf['panel_planes'][0]['node_id']
                cf['panel_planes'][1]['face_id'] = cf['panel_planes'][0]['face_id']
            with self.subTest(mutation=mutation): self.assert_refused_capture(e, t)

    def test_source_root_and_occurrence_composition_is_checked_in_both_frames(self):
        for target in ('assembly', 'world', 'parent'):
            e, t = make_fixture()
            if target == 'assembly': e['assemblies'][0]['matrix_world_mm'][3][2] += 7
            else: e['occurrences'][0]['matrix_' + target + '_mm'][3][2] += 7
            with self.subTest(target=target): self.assert_refused_capture(e, t)

    def test_boolean_slot_and_duplicate_identity_are_not_coerced(self):
        for mutation in ('slot_bool', 'node_bool', 'assembly_duplicate', 'subtree_duplicate'):
            e, t = make_fixture()
            if mutation == 'slot_bool': t['occurrence_bindings'][0]['slot'][0] = False
            elif mutation == 'node_bool': e['occurrences'][0]['id'] = True
            elif mutation == 'assembly_duplicate': e['assemblies'][1]['id'] = e['assemblies'][0]['id']
            else:
                e['occurrences'][1]['occurrence_path'] = e['occurrences'][0]['occurrence_path']
                t['occurrence_bindings'][1]['occurrence_path'] = t['occurrence_bindings'][0]['occurrence_path']
            with self.subTest(mutation=mutation): self.assert_refused_capture(e, t)

    def test_body_signature_cannot_have_zero_volume_or_collapsed_bounds(self):
        for mutation in ('volume', 'faces', 'bounds'):
            e, t = make_fixture()
            if mutation == 'volume': e['occurrences'][0]['body_signature']['volume_m3'] = 0
            elif mutation == 'faces': e['occurrences'][0]['body_signature']['faces'] = True
            else: e['occurrences'][0]['local_bounds_mm'][3] = -40
            with self.subTest(mutation=mutation): self.assert_refused_capture(e, t)

    def test_observation_order_independent_but_duplicate_missing_or_moved_not_allowed(self):
        e, t, binding = self.fixture()
        plan = api.plan_corner_resize(binding, [1100, 720, 410])
        observed = independently_observed(e, t, [1100, 720, 410])
        observed['occurrences'].reverse()
        self.assertTrue(api.validate_corner_observation(plan, observed))
        for mutation in ('missing', 'duplicate', 'moved', 'new_reflection', 'changed_volume'):
            wrong = copy.deepcopy(observed)
            if mutation == 'missing': wrong['occurrences'].pop()
            elif mutation == 'duplicate': wrong['occurrences'][-1] = copy.deepcopy(wrong['occurrences'][0])
            elif mutation == 'moved': wrong['occurrences'][0]['matrix_world_mm'][3][1] += 0.01
            elif mutation == 'new_reflection':
                wrong['occurrences'][0]['matrix_world_mm'][0][:3] = [-v for v in wrong['occurrences'][0]['matrix_world_mm'][0][:3]]
            else: wrong['occurrences'][0]['body_signature']['volume_m3'] *= 1.01
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                api.validate_corner_observation(plan, wrong)

    def test_common_forged_plan_and_observation_must_not_be_their_own_oracle(self):
        e, t, binding = self.fixture()
        plan = api.plan_corner_resize(binding, [1100, 720, 410])
        observed = independently_observed(e, t, [1100, 720, 410])
        for rows in (plan['occurrences'], observed['occurrences']):
            for row in rows:
                row['matrix_world_mm'][3][0] += 50
        plan['content_sha256'] = digest({k: v for k, v in plan.items() if k != 'content_sha256'})
        with self.assertRaises(ValueError): api.validate_corner_observation(plan, observed)

    def test_api_is_detached_and_does_not_read_files(self):
        e, t = make_fixture()
        before = copy.deepcopy((e, t))
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected I/O')):
            binding = api.capture_corner_binding(e, t)
            plan = api.plan_corner_resize(binding, [1100, 720, 410])
            self.assertTrue(api.validate_corner_observation(plan, independently_observed(e, t, [1100, 720, 410])))
        self.assertEqual((e, t), before)
        plan['occurrences'][0]['body_signature']['faces'] += 1
        self.assertEqual((e, t), before)


if __name__ == '__main__': unittest.main()
