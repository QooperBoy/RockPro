"""Independent non-golden probes for the inert production planner boundary."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Integracja'))
from rockpro_cad.core_case import plan_case
from rockpro_cad.core_case.contracts import ValidationError, validate_case_spec


def request():
    # Only the recipe is a test input. No frozen case, expected result, or oracle.
    recipe = json.loads((ROOT / 'tests/core_design/synthetic_template.json').read_text(encoding='utf-8'))
    spec = dict(case_id='independent-rotated-envelope', schema_version=1, revision=3, expected_revision=3,
                template_version=recipe['template_version'], units='mm', axes='right-handed-XYZ',
                dimension_source=dict(kind='synthetic', reference='independent-probe', confirmation='test-only'),
                layout=dict(name='Independent probe', x=410, y=230, z=170, count=2, orientation='YZX',
                            arrangement='Y', gap=14, clearance=17, separator=8, side='Y',
                            side_width=95, side_depth=190, side_height=160, side_name='Accessory',
                            thickness=12, lid_height=70), display_gap=23,
                interior_symmetry_approval='SYNTHETIC-CONSTRUCTOR-APPROVAL-1')
    manifest = dict(version=recipe['template_version'], synthetic=True, production_approved=False,
                    source_template='independent-synthetic-input',
                    required_families=list(dict.fromkeys(g['family'] for g in recipe['groups'])),
                    empty_assembly_ids=['synthetic-empty'], unresolved_ids=[],
                    interior_exception_approval=spec['interior_symmetry_approval'],
                    group_roles=[g['symmetry_group_id'] for g in recipe['groups']])
    return dict(spec=spec, manifest=manifest, template_recipe=recipe, scenario={'operation': 'plan'})


class PlannerTests(unittest.TestCase):
    def blocked(self, data, code=None):
        result = plan_case(data)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertEqual(result['changes'], [])
        if code:
            self.assertIn(code, [d['code'] for d in result['diagnostics']])
        return result

    def test_non_golden_geometry_and_determinism(self):
        data = request()
        before = copy.deepcopy(data)
        first = plan_case(data)
        self.assertEqual(first['status'], 'planned', first)
        self.assertEqual(first['plywood_external'], [288, 561, 468])
        self.assertEqual(first['internal'], [264, 537, 444])
        self.assertEqual(first['base_height'], 398)
        self.assertEqual(first['transport_bounds'], [[-15, -30, -60], [318, 576, 483]])
        self.assertEqual(first['presentation']['lid_translation'], [0, 0, 23])
        self.assertEqual(len(first['occurrences']), 67)
        self.assertFalse(first['production_approved'])
        self.assertEqual(data, before)
        self.assertEqual(first, plan_case(data))

    def test_case_name_cannot_select_geometry(self):
        data = request()
        before = plan_case(data)
        data['spec']['case_id'] = 'arbitrary-unrelated-identity'
        after = plan_case(data)
        self.assertEqual(before['occurrences'], after['occurrences'])

    def test_unselected_unknown_operation_is_denied(self):
        data = request()
        data['template_recipe']['groups'][0]['slots'][0][0] = {
            'op': 'select', 'args': [True, 144, {'op': '__import__', 'args': ['os']}]}
        self.blocked(data, 'RECIPE_OPERATION_UNSUPPORTED')

    def test_unknown_group_selector_and_invalid_presentation_vector_are_denied(self):
        data = request()
        group = next(g for g in data['template_recipe']['groups'] if g['symmetry_group_id'] == 'braces')
        group['slots'][0][0]['group_id'] = 'unmapped-group'
        self.blocked(data, 'RECIPE_SELECTOR_INVALID')
        data = request()
        data['template_recipe']['presentation']['lid_translation'] = ['invalid-mm', 0, 0]
        self.blocked(data, 'RECIPE_INVALID_NUMBER')

    def test_unknown_version_forward_reference_duplicate_and_arity(self):
        for mutation in ('version', 'forward', 'duplicate', 'arity'):
            with self.subTest(mutation=mutation):
                data = request()
                r = data['template_recipe']
                if mutation == 'version':
                    r['expression_language']['version'] = 2
                elif mutation == 'forward':
                    r['derived'][0]['value'] = {'ref': 'H'}
                elif mutation == 'duplicate':
                    r['derived'].append(copy.deepcopy(r['derived'][0]))
                else:
                    r['derived'][0]['value'] = {'op': 'sub', 'args': [1]}
                self.blocked(data)

    def test_invalid_numeric_and_resource_expressions(self):
        for expr in (True, {'op': 'div', 'args': [1, 0]}, {'op': 'add', 'args': [True, 1]}):
            with self.subTest(expr=expr):
                data = request()
                data['template_recipe']['groups'][0]['shape'][0] = expr
                self.blocked(data)
        data = request()
        expr = 1
        for _ in range(55):
            expr = [expr]
        data['template_recipe']['groups'][0]['shape'][0] = expr
        self.blocked(data, 'RECIPE_LIMIT')

    def test_rigid_catalog_policy_bounds_and_mounting_point(self):
        for field, value in (('geometry_policy', 'panel'), ('local_bounds', [[1, 1, 1], [0, 0, 0]]),
                             ('mounting_point', [1, 0, 0])):
            with self.subTest(field=field):
                data = request()
                data['template_recipe']['catalog']['corner'][field] = value
                self.blocked(data)

    def test_reflections_and_manifest_accounting_are_denied(self):
        data = request()
        data['template_recipe']['rotations']['identity'][0][0] = -1
        self.blocked(data, 'INVALID_RIGID_ROTATION')
        data = request()
        data['manifest']['group_roles'].pop()
        self.blocked(data, 'SYMMETRY_GROUP_MISSING')

    def test_symmetry_checks_full_points_not_only_axis_projections(self):
        data = request()
        group = next(g for g in data['template_recipe']['groups'] if g['symmetry_group_id'] == 'corners')
        group['slots'] = [[0, 0, 0], [288, 561, 0], [0, 187, 0], [288, 374, 0]]
        self.blocked(data, 'SYMMETRY_INVALID')

    def test_audit_checks_every_physical_observation_and_identity(self):
        baseline = plan_case(request())
        for key, value in (('uvn', [1, 2, 3]), ('closed_xyz', [1, 2, 3]), ('shape', [1, 2, 3]),
                           ('local_bounds', [[-1, -1, -1], [1, 1, 1]]), ('definition', 'wrong')):
            with self.subTest(key=key):
                data = request()
                current = copy.deepcopy(baseline)
                current['occurrences'][0][key] = value
                data['scenario'] = dict(operation='audit', current=current)
                self.blocked(data)
        data = request()
        current = copy.deepcopy(baseline)
        current['occurrences'][0].pop('definition')
        data['scenario'] = dict(operation='audit', current=current)
        self.blocked(data, 'INVENTORY_UNRESOLVED')

    def test_previous_binding_and_unilateral_change_are_refused(self):
        baseline = plan_case(request())
        for mutation in ('source', 'recipe', 'part'):
            with self.subTest(mutation=mutation):
                data = request()
                previous = copy.deepcopy(baseline)
                if mutation == 'source':
                    data['spec']['dimension_source']['reference'] = 'changed-source'
                elif mutation == 'recipe':
                    data['template_recipe']['constants']['brace_edge_offset'] += 1
                else:
                    previous['occurrences'][0]['uvn'][0] += 1
                data['scenario'] = dict(operation='resize', target_plywood_external=[388, 661, 568], previous=previous)
                self.blocked(data)

    def test_constructor_decision_survives_json_boundary_and_resize(self):
        data = request()
        data['scenario'] = dict(operation='reconcile', manual_overrides=[dict(group_id='braces', edge_offset=90,
                               approval='SYNTHETIC-CONSTRUCTOR-MANUAL-1')])
        first = plan_case(data)
        self.assertEqual(first['status'], 'planned', first)
        data['scenario'] = dict(operation='resize', target_plywood_external=[388, 661, 568],
                                previous=json.loads(json.dumps(first)))
        second = plan_case(data)
        self.assertEqual(second['status'], 'planned', second)
        parts = {p['id']: p for p in second['occurrences']}
        self.assertEqual([parts['braces/1']['uvn'][0], parts['braces/2']['uvn'][0]], [90, 298])
        self.assertIn('SYNTHETIC-CONSTRUCTOR-MANUAL-1', second['preserved_manual_approvals'])

    def test_explicit_unapproved_interior_token_has_distinct_diagnostic(self):
        spec = request()['spec']
        spec['interior_symmetry_approval'] = 'AI-APPROVED'
        with self.assertRaises(ValidationError) as caught:
            validate_case_spec(spec)
        self.assertEqual(caught.exception.code, 'SYMMETRY_EXCEPTION_UNAPPROVED')
        spec.pop('interior_symmetry_approval')
        with self.assertRaises(ValidationError) as caught:
            validate_case_spec(spec)
        self.assertEqual(caught.exception.code, 'SYMMETRY_EXCEPTION_REQUIRED')


if __name__ == '__main__':
    unittest.main()
