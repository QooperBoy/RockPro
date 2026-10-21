"""GREEN: oracle mutation sensitivity, NOT evidence of a case implementation."""
import copy
import json
from pathlib import Path
import unittest
from contract import FIXTURES
from oracle import validate, specimen, FAMILIES


class ObservationOracleTests(unittest.TestCase):
    def test_input_recipe_accounts_for_every_frozen_group_without_expected_outputs(self):
        recipe = json.loads(Path(__file__).with_name('synthetic_template.json').read_text(encoding='utf-8'))
        self.assertTrue(recipe['synthetic'])
        self.assertFalse(recipe['production_approved'])
        self.assertEqual(recipe['units'], 'mm')
        for forbidden in ('cases', 'expected', 'resize_expectations', 'legacy_boxes'):
            self.assertNotIn(forbidden, recipe)
        ids = [g['symmetry_group_id'] for g in recipe['groups']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(FIXTURES['manifest']['group_roles']))
        for case in FIXTURES['cases']:
            self.assertEqual(recipe['template_version'], case['spec']['template_version'])
            self.assertEqual(set(ids), set(case['expected']['groups']))

    def test_input_recipe_covers_count_roundtrip_resize_and_manual_scenarios(self):
        # Structural contract checks only: this deliberately does not interpret
        # the recipe or generate a plan from it.
        recipe = json.loads(Path(__file__).with_name('synthetic_template.json').read_text(encoding='utf-8'))
        scenario = recipe['scenario_contract']
        counts = scenario['set_group_count']
        self.assertEqual(counts['allowed_counts'], [1, 2, 3, 4])
        self.assertEqual(counts['mode_by_count'], {'1':'centered','2':'mirrored_pair',
                                                  '3':'centered_pattern','4':'centered_pattern'})
        for count in range(1, 5):
            self.assertEqual(len(counts['patterns'][str(count)]), count)
        self.assertEqual(counts['edge_offset_default'], 100)
        self.assertEqual(counts['inner_offset_default'], 260)
        derived = {item['name']: item['value'] for item in recipe['derived']}
        expected_internal = [{'op':'sub','args':[{'ref':axis},
                              {'op':'mul','args':[2,{'ref':'T'}]}]} for axis in ('W','D','H')]
        self.assertEqual(derived['internal'], expected_internal,
                         'resized inner dimensions must follow the new outer dimensions')
        reconcile = scenario['reconcile']
        self.assertEqual(reconcile['operation'], 'reconcile')
        self.assertEqual(set(reconcile['allowed_group_parameters']['handles']),
                         {'count','edge_offset','inner_offset'})
        self.assertIn('edge_offset', reconcile['allowed_group_parameters']['braces'])
        addition = reconcile['manual_additions']
        self.assertEqual(set(addition['required']),
                         {'id','definition','anchor','group','group_id','approval'})
        self.assertEqual(addition['allowed_anchor_frame'], 'closed')
        self.assertEqual(set(addition['anchor_rule_allowlist']), {'W/2','D/2','base_height/4'})
        self.assertEqual(addition['allowed_group_id'], 'manual-attached')
        self.assertEqual(addition['group_contract']['family'], 'interior')
        self.assertEqual(addition['group_contract']['scope'], 'constructor-attached-local-part')
        definition = addition['approved_definition_allowlist']['synthetic-20-cube']
        self.assertEqual(definition['shape'], [20,20,20])
        self.assertEqual(definition['local_bounds'], [[-10,-10,-10],[10,10,10]])
        self.assertIn('presentation_gap', recipe['expression_language']['input_selector_allowlist'])
        self.assertEqual(recipe['presentation']['lid_translation'][2]['input_selector'], 'presentation_gap')

    def test_count_patterns_have_independent_literal_slots_and_minimum_spacing(self):
        from test_planner_red import count_expected_case
        for case in FIXTURES['cases']:
            width = case['expected']['plywood_external'][0]
            for count, slots in case['count_slots'].items():
                self.assertEqual(len(slots), int(count))
                self.assertAlmostEqual(slots[0], 100)
                self.assertAlmostEqual(width-slots[-1], 100)
                for a, b in zip(slots, reversed(slots)):
                    self.assertAlmostEqual(a+b, width)
                for a, b in zip(slots, slots[1:]):
                    self.assertGreaterEqual(b-a, 150+10, 'rigid handle + synthetic clearance')
                expected = count_expected_case(case, int(count))
                validate(expected, specimen(expected))

    def test_literal_synthetic_observations_are_internally_consistent(self):
        for case in FIXTURES['cases']:
            validate(case, specimen(case))

    def test_resize_literal_observations_are_internally_consistent(self):
        from test_planner_red import resized_case
        for case in FIXTURES['cases']:
            for axis in ('X', 'Y', 'Z', 'XYZ'):
                with self.subTest(case=case['id'], axis=axis):
                    resized = resized_case(case, axis)
                    validate(resized, specimen(resized))

    def test_manual_override_expected_observations_are_consistent(self):
        from test_planner_red import manual_expected_case
        for case_id in 'ABC':
            for axis in (None, 'X'):
                with self.subTest(case=case_id, axis=axis):
                    case = manual_expected_case(case_id, axis)
                    validate(case, specimen(case))

    def test_every_family_rejects_anchor_shape_rotation_and_missing_member(self):
        for case in FIXTURES['cases']:
            original = specimen(case)
            for group in original['groups']:
                family = group['family']
                gid = group['symmetry_group_id']
                pid = next(g['members'][0] for g in original['groups'] if g['symmetry_group_id'] == gid)
                for mutation in ('anchor', 'shape', 'rotation', 'missing'):
                    with self.subTest(case=case['id'], family=family, group_id=gid, mutation=mutation):
                        observation = copy.deepcopy(original)
                        p = next(p for p in observation['occurrences'] if p['id'] == pid)
                        if mutation == 'anchor': p['uvn'][0] += 1
                        elif mutation == 'shape': p['shape'][2] += 1
                        elif mutation == 'rotation': p['rotation'][0][0] += 0.1
                        else: observation['occurrences'].remove(p)
                        with self.assertRaises(AssertionError): validate(case, observation)

    def test_nonvacuous_inventory_datum_orientation_and_pairing_checks(self):
        case = FIXTURES['cases'][0]
        def change(name, obs):
            parts = {p['id']: p for p in obs['occurrences']}
            if name == 'missing_group': obs['groups'].pop()
            elif name == 'duplicate_group': obs['groups'].append(copy.deepcopy(obs['groups'][0]))
            elif name == 'duplicate_part': obs['occurrences'].append(copy.deepcopy(obs['occurrences'][0]))
            elif name == 'duplicate_inventory': obs['inventory']['physical_ids'].append(obs['inventory']['physical_ids'][0])
            elif name == 'unresolved_inventory': obs['inventory']['unresolved_ids'] = ['unidentified-synthetic']
            elif name == 'empty_group': obs['groups'][0]['members'] = []
            elif name == 'wrong_wall': parts['handles/1']['frame'] = 'rear'
            elif name == 'wrong_datum': obs['groups'][0]['datum'] = 'rear'
            elif name == 'reflection': parts['handles/1']['rotation'] = [[-1,0,0],[0,1,0],[0,0,1]]
            elif name == 'rigid_but_wrong_rotation': parts['corners/1']['rotation'] = [[0,-1,0],[1,0,0],[0,0,1]]
            elif name == 'shift_pair_symmetrically':
                parts['braces/1']['uvn'][0] += 5
                parts['braces/2']['uvn'][0] -= 5
            elif name == 'seam_mismatch': parts['latches-lid/1']['closed_xyz'][2] += 10
            elif name == 'stack_mismatch': parts['sockets/1']['closed_xyz'][0] += 10
            elif name == 'display_gap_leak': parts['hinges-lid/1']['closed_xyz'][2] += 60
            elif name == 'missing_exception':
                next(g for g in obs['groups'] if g['family'] == 'interior')['exception_approval'] = None
            elif name == 'unapproved_exception':
                next(g for g in obs['groups'] if g['family'] == 'interior')['exception_approval'] = 'AI-APPROVED'
            elif name == 'corner_exception_missing':
                next(g for g in obs['groups'] if g['symmetry_group_id'] == 'corner-handle')['exception_approval'] = None
            elif name == 'collapsed_dimension': obs['plywood_external'][0] = 0
        names = ['missing_group','duplicate_group','duplicate_part','duplicate_inventory','unresolved_inventory',
                 'empty_group','wrong_wall','wrong_datum','reflection','rigid_but_wrong_rotation',
                 'shift_pair_symmetrically','seam_mismatch','stack_mismatch','display_gap_leak',
                 'missing_exception','unapproved_exception','corner_exception_missing','collapsed_dimension']
        for name in names:
            with self.subTest(mutation=name):
                observation = specimen(case)
                change(name, observation)
                with self.assertRaises(AssertionError): validate(case, observation)


if __name__ == '__main__':
    unittest.main()
