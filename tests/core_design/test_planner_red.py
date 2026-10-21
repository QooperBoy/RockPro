"""Deliberate RED against a future pure production planner, not a test fake."""
import copy
import json
import unittest
from contract import FIXTURES, plan
from oracle import validate, specimen, near


def resized_case(case, axis):
    result = copy.deepcopy(case)
    patch = case['resize_expectations'][axis]
    for key, value in patch.items():
        if key in ('frames', 'groups'):
            result['expected'][key].update(copy.deepcopy(value))
        else:
            result['expected'][key] = copy.deepcopy(value)
    return result


class FutureCasePlannerTests(unittest.TestCase):
    def require(self, requirement, case, **scenario):
        spec = copy.deepcopy(case['spec'])
        before = copy.deepcopy(spec)
        try:
            result = plan(requirement, spec, **scenario)
        except NotImplementedError as exc:
            self.fail(str(exc))
        self.assertEqual(spec, before, requirement + ': caller input mutated')
        return result

    def blocked(self, requirement, case, code, **scenario):
        result = self.require(requirement, case, **scenario)
        self.assertEqual(result['status'], 'blocked', requirement)
        self.assertIn(code, [d['code'] for d in result['diagnostics']], requirement)
        self.assertEqual(result['changes'], [], 'blocked proposal must contain no executable changes')


def initial_test(case):
    def test(self):
        requirement = 'H2/full-case/' + case['id']
        result = self.require(requirement, case, operation='plan')
        validate(case, result)
    return test


def missing_group_test(case, group_id):
    def test(self):
        current = specimen(case)
        current['groups'] = [g for g in current['groups'] if g['symmetry_group_id'] != group_id]
        self.blocked('H1/group-required/' + case['id'] + '/' + group_id, case,
                     'SYMMETRY_GROUP_MISSING', operation='audit', current=current)
    return test


def resize_test(case, axis):
    def test(self):
        baseline = self.require('H2/resize-baseline/' + case['id'], case, operation='plan')
        validate(case, baseline)
        expected = resized_case(case, axis)
        actual = self.require('H2/resize-' + axis + '/' + case['id'], case,
                              operation='resize', target_plywood_external=case['resize_targets'][axis],
                              previous=baseline)
        validate(expected, actual)
        # A JSON serialize/re-read models an offline plan boundary only, never ICS.
        reopened_plan = json.loads(json.dumps(actual, allow_nan=False))
        validate(expected, reopened_plan)
        returned = self.require('H2/roundtrip-' + axis + '/' + case['id'], case,
                                operation='resize', target_plywood_external=case['expected']['plywood_external'],
                                previous=reopened_plan)
        validate(case, returned)
        self.assertEqual(returned['occurrences'], baseline['occurrences'], 'roundtrip physical observation')
    return test


def count_test(case, count):
    def test(self):
        expected = count_expected_case(case, count)
        actual = self.require(f'H2/count-{count}/' + case['id'], case,
                              operation='set_group_count', group_id='handles', count=count,
                              edge_offset=100, inner_offset=260, minimum_clearance=10)
        validate(expected, actual)
        returned = self.require('H2/count-roundtrip/' + case['id'], case,
                                operation='set_group_count', group_id='handles', count=1, previous=actual)
        validate(case, returned)
    return test


def count_expected_case(case, count):
    expected = copy.deepcopy(case)
    group = expected['expected']['groups']['handles']
    base_member = copy.deepcopy(group['members'][0])
    group['mode'] = 'mirrored_pair' if count == 2 else 'centered_pattern'
    group['members'] = []
    for i, u in enumerate(case['count_slots'][str(count)]):
        member = copy.deepcopy(base_member)
        member['id'] = 'handles/' + str(i+1)
        member['uvn'][0] = u
        group['members'].append(member)
    return expected


def manual_expected_case(case_id, axis=None):
    original = next(c for c in FIXTURES['cases'] if c['id'] == case_id)
    case = resized_case(original, axis) if axis else copy.deepcopy(original)
    width, depth, height = case['expected']['plywood_external']
    if case_id == 'A':
        members = case['expected']['groups']['braces']['members']
        members[0]['uvn'][0] = 100
        members[1]['uvn'][0] = width-100
    elif case_id == 'B':
        group = case['expected']['groups']['handles']
        first = copy.deepcopy(group['members'][0])
        first['uvn'][0] = 100
        second = copy.deepcopy(first)
        second['id'] = 'handles/2'
        second['uvn'][0] = width-100
        group.update(mode='mirrored_pair', members=[first, second])
    else:
        group = copy.deepcopy(case['expected']['groups']['interior-custom'])
        group['scope'] = 'constructor-attached-local-part'
        group['exception_approval'] = 'SYNTHETIC-C-ANCHOR-APPROVAL'
        group['members'][0].update(id='manual-attached/1',
                                  uvn=[width/2,depth/2,case['expected']['base_height']/4],
                                  shape=[20,20,20],local_bounds=[[-10,-10,-10],[10,10,10]])
        case['expected']['groups']['manual-attached'] = group
    return case


def display_gap_test(case):
    def test(self):
        baseline = self.require('H2/display-baseline/' + case['id'], case, operation='plan')
        actual = self.require('H2/display-gap/' + case['id'], case, operation='display', display_gap=60)
        validate(case, actual)
        self.assertEqual(actual['occurrences'], baseline['occurrences'], 'display gap must not change physical geometry')
        self.assertEqual(actual['presentation']['lid_translation'], [0, 0, 60])
    return test


for _case in FIXTURES['cases']:
    setattr(FutureCasePlannerTests, 'test_H2_' + _case['id'] + '_complete_case', initial_test(_case))
    for _gid in _case['expected']['groups']:
        setattr(FutureCasePlannerTests, 'test_H1_' + _case['id'] + '_missing_group_' + _gid.replace('-', '_'), missing_group_test(_case, _gid))
    for _axis in ('X', 'Y', 'Z', 'XYZ'):
        setattr(FutureCasePlannerTests, 'test_H2_' + _case['id'] + '_resize_' + _axis + '_roundtrip', resize_test(_case, _axis))
    for _count in (2, 3, 4):
        setattr(FutureCasePlannerTests, f'test_H2_{_case["id"]}_count_{_count}_roundtrip', count_test(_case, _count))
    setattr(FutureCasePlannerTests, 'test_H2_' + _case['id'] + '_display_gap', display_gap_test(_case))


def refusal_test(name, mutate, code):
    def test(self):
        case = copy.deepcopy(FIXTURES['cases'][0])
        scenario = {'operation': 'plan'}
        mutate(case, scenario)
        self.blocked('H0-H3/' + name, case, code, **scenario)
    return test


def set_spec(key, value):
    return lambda case, scenario: case['spec'].__setitem__(key, value)


def set_layout(key, value):
    return lambda case, scenario: case['spec']['layout'].__setitem__(key, value)


NEGATIVES = [
    ('missing_units', lambda c,s: c['spec'].pop('units'), 'UNITS_REQUIRED'),
    ('metres_not_mm', set_spec('units', 'm'), 'UNITS_MISMATCH'),
    ('missing_dimension_source', lambda c,s: c['spec'].pop('dimension_source'), 'DIMENSION_SOURCE_REQUIRED'),
    ('nan', set_layout('x', float('nan')), 'NONFINITE_DIMENSION'),
    ('infinity', set_layout('y', float('inf')), 'NONFINITE_DIMENSION'),
    ('bad_orientation', set_layout('orientation', 'XXZ'), 'INVALID_ORIENTATION'),
    ('bad_thickness', set_layout('thickness', 0), 'INVALID_THICKNESS'),
    ('boolean_dimension', set_layout('x', True), 'INVALID_DIMENSION'),
    ('zero_count', set_layout('count', 0), 'INVALID_COUNT'),
    ('fractional_count', set_layout('count', 1.5), 'INVALID_COUNT'),
    ('negative_clearance', set_layout('clearance', -1), 'INVALID_CLEARANCE'),
    ('unknown_template', set_spec('template_version', 'unapproved'), 'UNSUPPORTED_TEMPLATE'),
    ('unknown_schema', set_spec('schema_version', 999), 'UNSUPPORTED_SCHEMA'),
    ('missing_case_id', lambda c,s: c['spec'].pop('case_id'), 'CASE_ID_REQUIRED'),
    ('empty_manifest', lambda c,s: s.update(manifest={}), 'MANIFEST_INVALID'),
    ('stale_revision', set_spec('expected_revision', 0), 'REVISION_CONFLICT'),
    ('too_small', lambda c,s: s.update(operation='resize', target_plywood_external=[100,100,60]), 'CASE_TOO_SMALL'),
    ('handle_no_space', lambda c,s: s.update(operation='set_group_count',group_id='handles',count=20,edge_offset=100), 'GROUP_NO_SPACE'),
    ('manual_shift_one_member', lambda c,s: s.update(operation='reconcile',manual_changes=[{'kind':'move','id':'braces/1','delta':[10,0,0]}]), 'SYMMETRY_MANUAL_CONFLICT'),
    ('manual_delete', lambda c,s: s.update(operation='reconcile',manual_changes=[{'kind':'delete','id':'hinges-lid/1'}]), 'MANUAL_DELETE_CONFLICT'),
    ('manual_add_unanchored', lambda c,s: s.update(operation='reconcile',manual_changes=[{'kind':'add','id':'manual-unanchored'}]), 'MANUAL_ANCHOR_REQUIRED'),
    ('ui_ai_conflict', lambda c,s: s.update(operation='reconcile',actor='AI',expected_revision=1,current_revision=2), 'REVISION_CONFLICT'),
    ('missing_interior_exception', lambda c,s: c['spec'].pop('interior_symmetry_approval'), 'SYMMETRY_EXCEPTION_REQUIRED'),
    ('unapproved_interior_exception', set_spec('interior_symmetry_approval','AI-APPROVED'), 'SYMMETRY_EXCEPTION_UNAPPROVED'),
]
for _name, _mutate, _code in NEGATIVES:
    setattr(FutureCasePlannerTests, 'test_refuse_' + _name, refusal_test(_name, _mutate, _code))


def audit_test(name, mutate, code):
    def test(self):
        case = FIXTURES['cases'][0]
        current = specimen(case)  # Explicit supplied observation, never actual output.
        mutate(current)
        self.blocked('H1-H3/audit-' + name, case, code, operation='audit', current=current)
    return test


AUDITS = [
    ('missing_group', lambda o:o['groups'].pop(), 'SYMMETRY_GROUP_MISSING'),
    ('duplicate_group', lambda o:o['groups'].append(copy.deepcopy(o['groups'][0])), 'SYMMETRY_GROUP_DUPLICATE'),
    ('missing_part', lambda o:o['occurrences'].pop(), 'INVENTORY_INCOMPLETE'),
    ('duplicate_id', lambda o:o['occurrences'].append(copy.deepcopy(o['occurrences'][0])), 'OCCURRENCE_ID_DUPLICATE'),
    ('unresolved_role', lambda o:o['inventory']['unresolved_ids'].append('unknown-synthetic'), 'INVENTORY_UNRESOLVED'),
    ('reflection', lambda o:o['occurrences'][0].__setitem__('rotation',[[-1,0,0],[0,1,0],[0,0,1]]), 'INVALID_RIGID_ROTATION'),
    ('wrong_frame', lambda o:o['occurrences'][0].__setitem__('frame','rear'), 'ANCHOR_FRAME_MISMATCH'),
    ('corner_exception_missing', lambda o:next(g for g in o['groups'] if g['symmetry_group_id']=='corner-handle').__setitem__('exception_approval',None), 'SYMMETRY_EXCEPTION_REQUIRED'),
]
for _name, _mutate, _code in AUDITS:
    setattr(FutureCasePlannerTests, 'test_audit_' + _name, audit_test(_name, _mutate, _code))


def manual_group_preserved(self):
    case = manual_expected_case('A')
    actual = self.require('H3/manual-approved-group-offset', case, operation='reconcile',
                          manual_overrides=[{'group_id':'braces','edge_offset':100,
                                             'approval':'SYNTHETIC-CONSTRUCTOR-MANUAL-1'}])
    validate(case, actual)
    self.assertIn('SYNTHETIC-CONSTRUCTOR-MANUAL-1', actual['preserved_manual_approvals'])
    resized = manual_expected_case('A', 'X')
    second = self.require('H3/manual-approved-offset-after-resize', case, operation='resize',
                          target_plywood_external=case['resize_targets']['X'], previous=actual)
    validate(resized, second)


setattr(FutureCasePlannerTests, 'test_H3_manual_group_override_survives_resize', manual_group_preserved)


def manual_b_handles_preserved(self):
    case = manual_expected_case('B')
    actual = self.require('H3/B/approved-handle-group', case, operation='reconcile',
                          manual_overrides=[{'group_id':'handles','count':2,'edge_offset':100,
                                             'approval':'SYNTHETIC-B-HANDLE-APPROVAL'}])
    validate(case, actual)
    self.assertIn('SYNTHETIC-B-HANDLE-APPROVAL', actual['preserved_manual_approvals'])
    resized = manual_expected_case('B', 'X')
    changed = self.require('H3/B/handle-decision-after-resize', case, operation='resize',
                           target_plywood_external=case['resize_targets']['X'], previous=actual)
    validate(resized, changed)
    self.assertIn('SYNTHETIC-B-HANDLE-APPROVAL', changed['preserved_manual_approvals'])


def manual_c_anchored_addition(self):
    case = manual_expected_case('C')
    group = case['expected']['groups']['manual-attached']
    actual = self.require('H3/C/attached-manual-addition', case, operation='reconcile',
                          manual_changes=[{'kind':'add','id':'manual-attached/1','definition':'synthetic-20-cube',
                                           'anchor':{'frame':'closed','uvn':[378.5,229,224.25],
                                                     'rules':['W/2','D/2','base_height/4']},
                                           'group':group,'group_id':'manual-attached',
                                           'approval':'SYNTHETIC-C-ANCHOR-APPROVAL'}])
    validate(case, actual)
    self.assertIn('SYNTHETIC-C-ANCHOR-APPROVAL', actual['preserved_manual_approvals'])
    resized = manual_expected_case('C', 'X')
    changed = self.require('H3/C/manual-addition-after-resize', case, operation='resize',
                           target_plywood_external=case['resize_targets']['X'], previous=actual)
    validate(resized, changed)
    self.assertIn('SYNTHETIC-C-ANCHOR-APPROVAL', changed['preserved_manual_approvals'])
    self.blocked('H3/C/unanchored-addition', FIXTURES['cases'][2], 'MANUAL_ANCHOR_REQUIRED',
                 operation='reconcile',manual_changes=[{'kind':'add','id':'manual-unanchored'}])


setattr(FutureCasePlannerTests, 'test_H3_B_manual_handles_survive_resize', manual_b_handles_preserved)
setattr(FutureCasePlannerTests, 'test_H3_C_manual_anchored_addition_survives_resize', manual_c_anchored_addition)


if __name__ == '__main__':
    unittest.main()
