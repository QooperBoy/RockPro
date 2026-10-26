import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.machining_rules import local_cut_pose, machining_step, validate_layout, validate_steps, minimum_lid_height, lid_threshold
from rockpro_cad.core_case.profile_rules import value


class MachiningRulesTests(unittest.TestCase):
    def setUp(self):
        self.p = dict(RP_Length=650., RP_Depth=500., RP_BaseHeight=300.,
                      RP_LidHeight=115., RP_Thickness=9.8, RP_DisplayGap=0., RP_JointGap=8.63,
                      RP_HandleOffset=0., RP_HandleHeightOffset=0., RP_LatchInset=150., RP_HingeInset=150.)

    def test_cut_moves_in_rotated_target_frame(self):
        identity = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        target = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
        rotation, position = local_cut_pose(identity, ['RP_Length/4', '40 mm', '150 mm'],
                                            target, ['RP_Length/2', '10 mm', '20 mm'])
        self.assertEqual([value(e, self.p) for e in position], [30, 162.5, 130])
        self.p['RP_Length'] = 800
        self.assertEqual([value(e, self.p) for e in position], [30, 200, 130])
        self.assertEqual(rotation, [[0, -1, 0], [1, 0, 0], [0, 0, 1]])

    def test_contour_cannot_be_scaled(self):
        with self.assertRaises(ValueError):
            local_cut_pose([[2,0,0],[0,1,0],[0,0,1]], ['0']*3,
                           [[1,0,0],[0,1,0],[0,0,1]], ['0']*3)

    def test_mount_and_cut_share_assembly_stage(self):
        step = machining_step('left/opening', 'left', 'handles', 1, 2,
                              [[1,0,0],[0,1,0],[0,0,1]], ['0 mm']*3, self.p)
        self.assertEqual(step['stage_id'], 'handles')
        self.assertTrue(validate_steps([step], {'left'}))
        with self.assertRaises(ValueError):
            validate_steps([step], {'right'})
        with self.assertRaises(ValueError):
            validate_steps([step, step], {'left'})

    def test_valid_baseline_and_changed_dimensions(self):
        self.assertTrue(validate_layout(self.p))
        self.p.update(RP_Length=720., RP_Depth=560., RP_BaseHeight=320.,
                      RP_HandleOffset=10., RP_HandleHeightOffset=5., RP_LatchInset=170., RP_HingeInset=170.)
        self.assertTrue(validate_layout(self.p))

    def test_handle_flange_cannot_enter_hinge_wall_reserve(self):
        self.p['RP_HandleOffset'] = 20
        with self.assertRaisesRegex(ValueError, 'corner/hinge'):
            validate_layout(self.p)

    def test_shallow_lid_cannot_remove_hinge_mounting_space(self):
        self.p['RP_LidHeight'] = 109
        with self.assertRaisesRegex(ValueError, 'hinge'):
            validate_layout(self.p)

    def test_lid_threshold_includes_profile_and_clearance(self):
        self.assertEqual(minimum_lid_height(), 110)
        self.p['RP_LidHeight'] = 110
        self.assertTrue(validate_layout(self.p))
        self.assertEqual(minimum_lid_height(10), 115)

    def test_future_catalog_must_supply_reach_before_build(self):
        self.assertEqual(lid_threshold([100, 70], 35), 140)
        with self.assertRaises(ValueError):
            lid_threshold([], 35)
        with self.assertRaises(ValueError):
            lid_threshold([None], 35)

    def test_unmeasured_profile_fit_is_not_silently_accepted(self):
        for name, number in [('RP_Thickness', 12.), ('RP_JointGap', 1.)]:
            p = dict(self.p, **{name:number})
            with self.assertRaisesRegex(ValueError, 'measured profile'):
                validate_layout(p)

    def test_one_centered_handle_per_wall_is_supported(self):
        self.assertTrue(validate_layout(self.p, 1))
        with self.assertRaises(ValueError):
            validate_layout(self.p, 3)


if __name__ == '__main__':
    unittest.main()
