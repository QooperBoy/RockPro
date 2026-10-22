"""Independent dimensional oracle for the narrow H7159/one-device POC.

These tests use declared wall dimensions and raw face witnesses as the oracle.
The production planner and pair validator are subjects under test, never sources
of expected coordinates. No COM, native writes, existing cases, or golden output.
"""
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.hardware_poc import candidate_datum, plan_hardware_poc, validate_pair

SHA = 'd' * 64
GUID = 'independent-h7159-oracle'
T = 9.0
LID = 80.0
FLANGE_W = 161.0
FLANGE_H = 107.0
EDGE = 100.0
TOL = .003


def raw_evidence():
    """Explicit catalog witness planes: contact Y=0, exterior Y=1.2 mm."""
    faces = []
    for face_id, y, reversed_, ids in ((194, 0., True, [1, 2, 3, 4]),
                                      (353, 1.2, False, [5, 6, 7, 8])):
        faces.append(dict(face_id=face_id, point_mm=[0., y, 0.], normal=[0., 1., 0.],
                          is_reversed=reversed_, vertex_ids=ids,
                          vertices_mm=[[-80.5, y, -53.5], [80.5, y, -53.5],
                                       [80.5, y, 53.5], [-80.5, y, 53.5]]))
    return dict(asset_hash=SHA, asset_signature=[dict(kind='assembly', name='H7159')],
                document=dict(file_guid=GUID), planar_faces_parallel_local_xz=faces,
                source_world_matrix_mm=[[0., -1., 0., 0.], [-1., 0., 0., 0.],
                                        [0., 0., -1., 0.], [558., 1350., -1377., 1.]])


def make_datum(evidence=None):
    return candidate_datum(raw_evidence() if evidence is None else evidence,
                           contact_face_id=194, exterior_face_id=353,
                           expected_asset_sha256=SHA, expected_guid=GUID)


def world_point(local, matrix):
    """Independent row-vector affine transform, without production helpers."""
    return [matrix[3][axis] + sum(local[k]*matrix[k][axis] for k in range(3))
            for axis in range(3)]


def world_direction(local, matrix):
    return [sum(local[k]*matrix[k][axis] for k in range(3)) for axis in range(3)]


class HardwarePocIndependentOracleTests(unittest.TestCase):
    def assert_vector(self, actual, expected, tolerance=TOL):
        self.assertEqual(len(actual), len(expected))
        for a, e in zip(actual, expected):
            self.assertIn(type(a), (int, float))
            self.assertTrue(math.isfinite(a))
            self.assertLessEqual(abs(a-e), tolerance, (actual, expected))

    def assert_physical_contract(self, plan, size):
        width, depth, height = size
        base = height-LID
        self.assertEqual(plan['status'], 'planned')
        self.assertEqual(plan['units'], 'mm')
        self.assertIs(plan['production_approved'], False)
        self.assertIs(plan['datum']['mounting_approved'], False)
        self.assert_vector(plan['size'], size)
        self.assertEqual(plan['thickness'], T)
        self.assertEqual(plan['lid_height'], LID)
        self.assertAlmostEqual(plan['base_height'], base)
        self.assertEqual(plan['anchor_rule']['edge_inset_to_flange_mm'], EDGE)
        self.assertAlmostEqual(plan['anchor_rule']['front_outer_y'], -depth/2)
        self.assertEqual({p['id'] for p in plan['handles']}, {'H7159-left', 'H7159-right'})
        by_id = {p['id']: p for p in plan['handles']}
        # Expected anchors follow external wall edges and the SKU flange width.
        for side, sign in (('left', -1), ('right', 1)):
            handle = by_id['H7159-' + side]
            cx = sign*(width/2-EDGE-FLANGE_W/2)
            anchor = [cx, -depth/2, base/2]
            self.assert_vector(handle['anchor_mm'], anchor)
            matrix = handle['matrix_mm']
            self.assertEqual(len(matrix), 4)
            for actual, expected in zip(matrix[:3], ([1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0])):
                self.assert_vector(actual, expected, 1e-6)
            self.assert_vector(matrix[3], anchor+[1])
            self.assert_vector(world_point([0, 0, 0], matrix), anchor)
            # Surface reversal and source up have distinct physical meanings.
            self.assert_vector(world_direction([0, -1, 0], matrix), [0, 1, 0])
            self.assert_vector(world_direction([0, 1, 0], matrix), [0, -1, 0])
            self.assert_vector(world_direction([0, 0, -1], matrix), [0, 0, 1])
            flange = [world_point(v, matrix) for v in raw_evidence()['planar_faces_parallel_local_xz'][0]['vertices_mm']]
            exterior = [world_point(v, matrix) for v in raw_evidence()['planar_faces_parallel_local_xz'][1]['vertices_mm']]
            self.assertTrue(all(abs(v[1]+depth/2) <= TOL for v in flange))
            self.assertTrue(all(abs(v[1]-(-depth/2-1.2)) <= TOL for v in exterior))
            xs = [v[0] for v in flange]
            zs = [v[2] for v in flange]
            self.assertAlmostEqual(max(xs)-min(xs), FLANGE_W)
            self.assertAlmostEqual(max(zs)-min(zs), FLANGE_H)
            edge_clearance = min(xs)+width/2 if side == 'left' else width/2-max(xs)
            self.assertAlmostEqual(edge_clearance, EDGE)
            self.assertGreaterEqual(min(zs)-T, 25-TOL)
            self.assertGreaterEqual(base-max(zs), 25-TOL)
        proxies = plan['proxy_plan']['occurrences']
        self.assertEqual(len(proxies), 11)
        self.assertEqual(len({p['id'] for p in proxies}), 11)
        self.assertEqual(plan['proxy_plan']['inventory']['physical_ids'], [p['id'] for p in proxies])
        panels = [p for p in proxies if p['family'] == 'panel_proxy']
        devices = [p for p in proxies if p['family'] == 'product_proxy']
        self.assertEqual(len(panels), 10)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]['id'], 'product/1')
        self.assertEqual(plan['expected_physical_parts'], 10+2*13+1)
        self.assert_vector(devices[0]['shape'], [300, 220, 100])
        self.assert_vector(devices[0]['closed_xyz'], [0, 0, T+50])
        self.assertEqual(devices[0]['rotation'], [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertEqual(devices[0]['local_bounds'], [[-150, -110, -50], [150, 110, 50]])
        self.assert_vector(plan['device']['shape'], [300, 220, 100])
        self.assert_vector(plan['device']['center'], devices[0]['closed_xyz'])
        self.assertGreaterEqual((width-2*T-300)/2, 20-TOL)
        self.assertGreaterEqual((depth-2*T-220)/2, 20-TOL)
        self.assertGreaterEqual(base-T-109, 20-TOL)

    def test_literal_wall_sku_and_single_device_contract(self):
        self.assert_physical_contract(plan_hardware_poc([900, 600, 330], make_datum()), [900, 600, 330])

    def test_independent_resize_each_axis_and_return(self):
        datum = make_datum()
        before = copy.deepcopy(datum)
        baseline = plan_hardware_poc([900, 600, 330], datum)
        for size in ([1100, 600, 330], [900, 720, 330], [900, 600, 410], [1100, 720, 410]):
            with self.subTest(size=size):
                plan = plan_hardware_poc(size, datum)
                self.assert_physical_contract(plan, size)
                self.assertEqual(plan['device'], baseline['device'])
                self.assertEqual(plan_hardware_poc([900, 600, 330], datum), baseline)
        self.assertEqual(datum, before)

    def test_feasible_boundary_and_clearance_refusals(self):
        self.assert_physical_contract(plan_hardware_poc([547, 278, 255], make_datum()), [547, 278, 255])
        for size in ([546.99, 600, 330], [900, 277.99, 330], [900, 600, 254.99],
                     [357.99, 600, 330], [900, 230, 330], [900, 600, 190]):
            with self.subTest(size=size), self.assertRaises(ValueError):
                plan_hardware_poc(size, make_datum())

    def test_dimensions_reject_nonfinite_boolean_and_nonpositive(self):
        for axis in range(3):
            for invalid in (float('nan'), float('inf'), -float('inf'), True, False, 0, -1, 5001, None, '900'):
                size = [900, 600, 330]
                size[axis] = invalid
                with self.subTest(axis=axis, invalid=invalid), self.assertRaises(ValueError):
                    plan_hardware_poc(size, make_datum())

    def test_candidate_pins_two_distinct_flange_sides_and_up(self):
        datum = make_datum()
        self.assert_vector(datum['origin_mm'], [0, 0, 0])
        self.assert_vector(datum['outward'], [0, 1, 0])
        self.assert_vector(datum['up'], [0, 0, -1])
        self.assertIs(datum['contact_face']['is_reversed'], True)
        self.assertIs(datum['exterior_face']['is_reversed'], False)
        self.assert_vector(datum['contact_face']['oriented_normal'], [0, -1, 0])
        self.assert_vector(datum['exterior_face']['oriented_normal'], [0, 1, 0])

    def test_candidate_rejects_shifted_planes_even_with_preserved_thickness(self):
        evidence = raw_evidence()
        for face in evidence['planar_faces_parallel_local_xz']:
            face['point_mm'][1] += 30
            for vertex in face['vertices_mm']:
                vertex[1] += 30
        with self.assertRaises(ValueError):
            make_datum(evidence)

    def test_candidate_rejects_face_flips_and_source_up(self):
        for mutation in ('contact_flip', 'exterior_flip', 'normal_flip', 'source_up'):
            evidence = raw_evidence()
            faces = evidence['planar_faces_parallel_local_xz']
            if mutation == 'contact_flip':
                faces[0]['is_reversed'] = False
            elif mutation == 'exterior_flip':
                faces[1]['is_reversed'] = True
            elif mutation == 'normal_flip':
                faces[0]['normal'] = [0, -1, 0]
            else:
                evidence['source_world_matrix_mm'] = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                make_datum(evidence)

    def test_planner_rechecks_datum_origin_against_face_witnesses(self):
        datum = make_datum()
        datum['origin_mm'][0] = 1000
        with self.assertRaises(ValueError):
            plan_hardware_poc([900, 600, 330], datum)

    def test_planner_rechecks_outward_and_up_against_faces_and_source(self):
        for field, value in (('outward', [0, -1, 0]), ('up', [0, 0, 1])):
            datum = make_datum()
            datum[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                plan_hardware_poc([900, 600, 330], datum)

    def test_planner_rejects_nonfinite_or_boolean_datum_vectors(self):
        for field in ('origin_mm', 'outward', 'up'):
            for invalid in (True, float('nan'), float('inf')):
                datum = make_datum()
                datum[field][0] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    plan_hardware_poc([900, 600, 330], datum)

    def test_validator_rejects_plan_and_measurements_shifted_off_wall_together(self):
        plan = plan_hardware_poc([900, 600, 330], make_datum())
        for handle in plan['handles']:
            handle['matrix_mm'][3][1] += 30
            handle['anchor_mm'][1] += 30
        with self.assertRaises(ValueError):
            validate_pair(plan, copy.deepcopy(plan['handles']))

    def test_validator_rejects_plan_and_measurements_with_wrong_up_together(self):
        plan = plan_hardware_poc([900, 600, 330], make_datum())
        for handle in plan['handles']:
            handle['matrix_mm'][:3] = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
        with self.assertRaises(ValueError):
            validate_pair(plan, copy.deepcopy(plan['handles']))

    def test_validator_rejects_plan_and_measurements_with_wrong_edge_offset_together(self):
        plan = plan_hardware_poc([900, 600, 330], make_datum())
        for handle in plan['handles']:
            handle['matrix_mm'][3][0] /= 2
            handle['anchor_mm'][0] /= 2
        with self.assertRaises(ValueError):
            validate_pair(plan, copy.deepcopy(plan['handles']))

    def test_validator_rejects_corrupted_anchor_declaration_even_if_pose_is_correct(self):
        plan = plan_hardware_poc([900, 600, 330], make_datum())
        plan['handles'][0]['anchor_mm'][0] += 10
        with self.assertRaises(ValueError):
            validate_pair(plan, copy.deepcopy(plan['handles']))


if __name__ == '__main__':
    unittest.main()
