import unittest
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.machining_rules import local_cut_pose, machining_step, validate_layout, validate_steps, minimum_lid_height, lid_threshold
from rockpro_cad.core_case.profile_rules import value
from rockpro_cad.core_case.machining_rules import build_operation_graph, validate_operation_graph


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


def dependency_fixture():
    """Synthetic placement dependencies; not source mapping or a native recipe."""
    mounts = [dict(id='hinge', family_id='hinges', prerequisites=[]),
              dict(id='profile', family_id='profiles', prerequisites=['hinge']),
              dict(id='handle', family_id='handles', prerequisites=['profile'])]
    cuts = [dict(id='handle-opening', type='cutout', owner_mount='handle', target_part='panel', prerequisites=[]),
            dict(id='profile-end', type='profile_trim', owner_mount='hinge', target_part='edge', prerequisites=['profile'])]
    targets = [dict(id='panel', family_id='panels'), dict(id='edge', family_id='profiles')]
    return mounts, cuts, targets


class MachiningDependencyTests(unittest.TestCase):
    def test_topology_is_independent_of_display_stage_order(self):
        mounts, cuts, targets = dependency_fixture()
        original = copy.deepcopy((mounts, cuts, targets))
        graph = build_operation_graph(mounts, cuts, targets)
        self.assertEqual((mounts, cuts, targets), original)
        self.assertLess(graph['topological_order'].index('hinge'), graph['topological_order'].index('profile'))
        self.assertEqual([g['stage_id'] for g in graph['presentation_groups']], ['profiles', 'closures', 'handles'])
        nodes = {n['id']:n for n in graph['operations']}
        self.assertIn('handle', nodes['handle-opening']['prerequisites'])
        self.assertEqual(nodes['handle-opening']['stage_id'], nodes['handle']['stage_id'])
        self.assertEqual(nodes['profile-end']['stage_id'], 'closures')  # Owner, not target material.
        self.assertFalse(graph['executable_template']); self.assertFalse(graph['production_approved'])
        self.assertEqual(graph['native_execution'], 'NOT RUN')
        self.assertEqual(validate_operation_graph(graph), graph)

    def test_wheel_socket_pad_and_owned_cut_share_stage_six(self):
        mounts = [dict(id='pad', family_id='wheel_pads', prerequisites=[]),
                  dict(id='wheel', family_id='wheels', prerequisites=['pad']),
                  dict(id='socket', family_id='stacking_sockets', prerequisites=['wheel'])]
        cuts = [dict(id='socket-pocket', type='pocket', owner_mount='socket', target_part='roof', prerequisites=[])]
        graph = build_operation_graph(mounts, cuts, [dict(id='roof', family_id='panels')])
        self.assertEqual(graph['topological_order'], ['pad','wheel','socket','socket-pocket'])
        self.assertEqual(len(graph['presentation_groups']), 1)
        self.assertEqual(graph['presentation_groups'][0]['order'], 6)
        self.assertTrue(all(n['stage_id'] == 'wheels' for n in graph['operations']))

    def test_cycles_duplicates_and_orphans_are_rejected(self):
        changes = [lambda m,c,t: m[0].update(prerequisites=['handle-opening']),
                   lambda m,c,t: m.append(copy.deepcopy(m[0])),
                   lambda m,c,t: c.append(copy.deepcopy(c[0])),
                   lambda m,c,t: m[0].update(prerequisites=['absent']),
                   lambda m,c,t: c[0].update(owner_mount='absent'),
                   lambda m,c,t: c[0].update(target_part='absent'),
                   lambda m,c,t: m[1].update(prerequisites=['hinge','hinge'])]
        for change in changes:
            args = dependency_fixture(); change(*args)
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_operation_graph(*args)

    def test_unknown_type_family_and_catalog_machining_target_are_rejected(self):
        changes = [lambda m,c,t: c[0].update(type='execute_python'),
                   lambda m,c,t: m[0].update(family_id='unknown'),
                   lambda m,c,t: m[0].update(family_id='hinge/legacy-guess'),
                   lambda m,c,t: t[0].update(family_id='handles'),
                   lambda m,c,t: c[1].update(target_part='panel')]
        for change in changes:
            args = dependency_fixture(); change(*args)
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_operation_graph(*args)

    def test_tampering_with_stage_owner_edge_or_approval_fails_validation(self):
        changes = [lambda g: g['operations'][3].update(stage_id='corners'),
                   lambda g: g['operations'][3].update(prerequisites=[]),
                   lambda g: g['operations'][3].update(owner_mount='profile-end'),
                   lambda g: g.update(production_approved=True),
                   lambda g: g.update(native_execution='PASS'),
                   lambda g: g.update(topological_order=list(reversed(g['topological_order']))),
                   lambda g: g['operations'][0].update(registry_version=True)]
        for change in changes:
            graph = build_operation_graph(*dependency_fixture()); change(graph)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_operation_graph(graph)

    def test_order_is_stable_and_validation_returns_detached_data(self):
        mounts,cuts,targets = dependency_fixture()
        graph = build_operation_graph(mounts,cuts,targets)
        reordered = build_operation_graph(list(reversed(mounts)),list(reversed(cuts)),targets)
        self.assertEqual(graph['topological_order'], reordered['topological_order'])
        self.assertEqual(graph['presentation_groups'], reordered['presentation_groups'])
        checked = validate_operation_graph(graph)
        checked['operations'][0]['prerequisites'].append('changed')
        self.assertEqual(graph['operations'][0]['prerequisites'], [])


if __name__ == '__main__':
    unittest.main()
