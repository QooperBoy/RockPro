"""ROC-15 contracts are offline data validation, never a geometry planner."""
import copy
import json
from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Integracja'))
try:
    from rockpro_cad.core_case import contracts as c
except ImportError:
    c = None
FIXTURES = json.loads((ROOT / 'tests/core_design/cases.json').read_text(encoding='utf-8'))


def case():
    return copy.deepcopy(FIXTURES['cases'][0]['spec'])


def source():
    return dict(kind='synthetic', reference='ROC-15/test', confirmation='test-only')


def frame():
    return dict(origin=[0, 0, 0], u=[1, 0, 0], v=[0, 1, 0], n=[0, 0, 1])


def anchor():
    return dict(schema_version=1, anchor_id='base/front/handle', wall_id='base/front',
                datum='panel', frame=frame(), edge='left',
                offsets=dict(u=dict(mode='fixed', value=100), v=dict(mode='centered'),
                             n=dict(mode='fixed', value=0)),
                orientation=[[1,0,0],[0,1,0],[0,0,1]])


def definition():
    return dict(schema_version=1, definition_id='handle/type-A', family='handles',
                units='mm', geometry_policy='rigid', dimensions=[150,80,25],
                dimension_source=source())


class ContractsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(c, 'ROC-15: production core_case.contracts validation is missing')

    def rejected(self, action, code, path=None):
        with self.assertRaises(c.ValidationError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        if path is not None:
            self.assertEqual(caught.exception.path, path)
        self.assertEqual(set(caught.exception.as_dict()), {'code','path','message'})

    def test_three_frozen_cases_remain_valid_and_detached(self):
        for item in FIXTURES['cases']:
            original=copy.deepcopy(item['spec'])
            normalized=c.validate_case_spec(original)
            self.assertEqual(normalized, original)
            normalized['layout']['x']=123
            self.assertEqual(original, item['spec'])

    def test_order_quantity_is_independent_of_devices_per_case_and_can_be_unknown(self):
        spec=case()
        self.assertNotIn('order_quantity',c.validate_case_spec(spec))
        spec['order_quantity']=7
        normalized=c.validate_case_spec(spec)
        self.assertEqual(normalized['order_quantity'],7)
        self.assertEqual(normalized['layout']['count'],2)
        spec['layout']['count']=3
        self.assertEqual(c.validate_case_spec(spec)['order_quantity'],7)

    def test_order_quantity_is_a_bounded_positive_integer(self):
        for quantity in (True,False,1.0,0,-1,100001,float('nan'),float('inf'),None,'7'):
            with self.subTest(quantity=quantity):
                spec=case(); spec['order_quantity']=quantity
                self.rejected(lambda:c.validate_case_spec(spec),'INVALID_ORDER_QUANTITY','$.order_quantity')
        for quantity in (1,100000):
            spec=case(); spec['order_quantity']=quantity
            self.assertEqual(c.validate_case_spec(spec)['order_quantity'],quantity)
        spec=case(); spec['ordered_cases']=7
        self.rejected(lambda:c.validate_case_spec(spec),'UNKNOWN_FIELD','$.ordered_cases')

    def test_required_version_units_axes_ids_and_provenance(self):
        mutations=[('units', None,'UNITS_REQUIRED'),('units','m','UNITS_MISMATCH'),
                   ('schema_version',999,'UNSUPPORTED_SCHEMA'),('schema_version',True,'UNSUPPORTED_SCHEMA'),
                   ('axes','left-handed-XYZ','AXES_MISMATCH'),('case_id','','CASE_ID_REQUIRED'),
                   ('dimension_source',None,'DIMENSION_SOURCE_REQUIRED'),
                   ('template_version','unapproved','UNSUPPORTED_TEMPLATE')]
        for key,value,code in mutations:
            with self.subTest(key=key,value=value):
                spec=case()
                if value is None: spec.pop(key)
                else: spec[key]=value
                self.rejected(lambda:c.validate_case_spec(spec),code)

    def test_numeric_and_existing_layout_bounds_are_strict(self):
        for key,value,code in [('x',True,'INVALID_DIMENSION'),('x',float('nan'),'NONFINITE_DIMENSION'),
                               ('y',float('inf'),'NONFINITE_DIMENSION'),('z',5001,'INVALID_DIMENSION'),
                               ('count',False,'INVALID_COUNT'),('count',1.5,'INVALID_COUNT'),
                               ('count',31,'INVALID_COUNT'),('gap',501,'INVALID_CLEARANCE'),
                               ('clearance',-1,'INVALID_CLEARANCE'),('thickness',0,'INVALID_THICKNESS'),
                               ('separator',51,'INVALID_DIMENSION'),('lid_height',1001,'INVALID_DIMENSION'),
                               ('orientation','XXZ','INVALID_ORIENTATION'),('arrangement','A','INVALID_ARRANGEMENT')]:
            with self.subTest(key=key,value=value):
                spec=case(); spec['layout'][key]=value
                self.rejected(lambda:c.validate_case_spec(spec),code,'$.layout.'+key)

    def test_outer_envelope_and_base_lid_limits_not_relaxed(self):
        spec=case(); spec['layout'].update(x=5000,count=3)
        self.rejected(lambda:c.validate_case_spec(spec),'CASE_TOO_LARGE')
        spec=case(); spec['layout']['lid_height']=155
        self.rejected(lambda:c.validate_case_spec(spec),'CASE_TOO_SMALL')

    def test_revision_conflict_and_bool_rejected(self):
        for rev in (0,False,2):
            spec=case(); spec['expected_revision']=rev
            self.rejected(lambda:c.validate_case_spec(spec),'REVISION_CONFLICT')

    def test_unknown_fields_and_forged_synthetic_confirmation_rejected(self):
        spec=case(); spec['layout']['exec']='raise SystemExit'
        self.rejected(lambda:c.validate_case_spec(spec),'UNKNOWN_FIELD','$.layout.exec')
        spec=case(); spec['dimension_source']['confirmation']='confirmed'
        self.rejected(lambda:c.validate_case_spec(spec),'SOURCE_SCOPE_INVALID')
        spec=case(); spec['dimension_source']['query']='__import__("os")'
        self.rejected(lambda:c.validate_case_spec(spec),'UNKNOWN_FIELD','$.dimension_source.query')

    def test_dimension_envelopes_have_distinct_meanings_no_derived_transport(self):
        spec=case(); spec['dimension_envelopes']={name:dict(value=values,units='mm',source=source())
            for name,values in [('device',[300,220,100]),('internal',[808,340,140]),
                                ('plywood_external',[826,358,158]),('transport_external',[871,403,233])]}
        normalized=c.validate_case_spec(spec)
        self.assertEqual(normalized['dimension_envelopes'],spec['dimension_envelopes'])
        spec['dimension_envelopes']['external']=spec['dimension_envelopes'].pop('transport_external')
        self.rejected(lambda:c.validate_case_spec(spec),'UNKNOWN_FIELD')

    def test_inconsistent_declared_envelopes_rejected(self):
        spec=case(); spec['dimension_envelopes']={name:dict(value=values,units='mm',source=source())
            for name,values in [('internal',[900,340,140]),('plywood_external',[826,358,158])]}
        self.rejected(lambda:c.validate_case_spec(spec),'DIMENSION_ENVELOPE_MISMATCH')

    def test_source_approval_scopes_are_exact(self):
        src=dict(kind='manufacturer',reference='catalog:123',confirmation='confirmed',
                 approval=dict(scope='dimensions',reference='approval:1',approved_by='constructor'))
        self.assertEqual(c.validate_dimension_source(src),src)
        src['approval']['scope']='all'
        self.rejected(lambda:c.validate_dimension_source(src),'SOURCE_SCOPE_INVALID')

    def test_anchor_fixed_proportional_centered_and_no_input_mutation(self):
        a=anchor(); a['offsets']['u']=dict(mode='proportional',value=0.25)
        self.assertEqual(c.validate_anchor(a),a)
        normalized=c.validate_anchor(a); normalized['frame']['origin'][0]=5
        self.assertEqual(a['frame']['origin'][0],0)

    def test_anchor_rejects_non_right_frames_and_mixed_offset_meanings(self):
        for mutate,code in [(lambda a:a['frame'].update(n=[0,0,-1]),'INVALID_FRAME'),
                            (lambda a:a['frame'].update(u=[2,0,0]),'INVALID_FRAME'),
                            (lambda a:a['offsets']['u'].update(mode='proportional',value=1.1),'INVALID_OFFSET'),
                            (lambda a:a['offsets']['v'].update(value=2),'INVALID_OFFSET'),
                            (lambda a:a['orientation'].__setitem__(0,[float('nan'),0,0]),'INVALID_ROTATION')]:
            a=anchor(); mutate(a); self.rejected(lambda:c.validate_anchor(a),code)

    def test_definition_and_occurrence_identities_are_separate(self):
        d=definition(); self.assertEqual(c.validate_part_definition(d),d)
        occurrence=dict(schema_version=1,occurrence_id='base/front/handle/1',definition_id=d['definition_id'],
                        semantic_role='base/front/handle/left',anchor=anchor(),
                        cad_reference=dict(document_id='copy:1',node_id='native:42'))
        self.assertEqual(c.validate_part_occurrence(occurrence),occurrence)
        occurrence['occurrence_id']=''
        self.rejected(lambda:c.validate_part_occurrence(occurrence),'IDENTITY_REQUIRED')
        d['geometry_policy']='scale-anything'
        self.rejected(lambda:c.validate_part_definition(d),'INVALID_GEOMETRY_POLICY')

    def test_explicit_symmetry_modes_counts_and_scoped_exception(self):
        group=dict(schema_version=1,symmetry_group_id='handles',mode='centered',scope='base/front',
                   member_ids=['handle/1'],axes=['u'],datum='front')
        self.assertEqual(c.validate_symmetry_group(group),group)
        group.update(mode='mirrored_pair',member_ids=['handle/1','handle/2'])
        c.validate_symmetry_group(group)
        group['member_ids']=['handle/1','handle/1']
        self.rejected(lambda:c.validate_symmetry_group(group),'DUPLICATE_ID')
        group.update(mode='scoped_exception',member_ids=['handle/1'],exception_approval=dict(
            scope='base/front',reference='SYNTHETIC-constructor:1',approved_by='constructor',
            symmetry_group_id='handles',template_version='synthetic-v1',source_reference='ROC-15/test'),
            template_version='synthetic-v1',source_reference='ROC-15/test')
        c.validate_symmetry_group(group)
        group['exception_approval']['scope']='whole-case'
        self.rejected(lambda:c.validate_symmetry_group(group),'SYMMETRY_EXCEPTION_REQUIRED')

    def test_exception_cannot_be_replayed_for_other_group_source_or_template(self):
        group=dict(schema_version=1,symmetry_group_id='interior',mode='scoped_exception',scope='interior/device',
                   member_ids=['device/1'],axes=['u'],datum='closed',template_version='real-v1',source_reference='sha256:source',
                   exception_approval=dict(scope='interior/device',reference='constructor:1',approved_by='constructor',
                       symmetry_group_id='interior',template_version='real-v1',source_reference='sha256:source'))
        c.validate_symmetry_group(group)
        for key,value in [('symmetry_group_id','other'),('source_reference','sha256:other'),
                          ('template_version','real-v2'),('reference','SYNTHETIC-fake')]:
            changed=copy.deepcopy(group); changed['exception_approval'][key]=value
            self.rejected(lambda:c.validate_symmetry_group(changed),'SYMMETRY_EXCEPTION_REQUIRED')

    def test_synthetic_spec_cannot_be_relabelled_as_real_template(self):
        spec=case(); spec['template_version']='real-v1'
        self.rejected(lambda:c.validate_case_spec(spec,supported_templates=('real-v1',)),'SOURCE_SCOPE_INVALID')

    def test_request_rejects_unknown_commands_before_any_action(self):
        request=dict(spec=case(),manifest={},scenario=dict(operation='exec',code='print(1)'))
        self.rejected(lambda:c.validate_request(request),'UNSUPPORTED_OPERATION')
        request['scenario']=dict(operation='plan',shell='powershell')
        self.rejected(lambda:c.validate_request(request),'UNKNOWN_FIELD')

    def test_request_revisions_json_and_synthetic_manifest_are_validated(self):
        request=dict(spec=case(),manifest=copy.deepcopy(FIXTURES['manifest']),scenario=dict(operation='plan'))
        self.assertEqual(c.validate_request(request),request)
        for rev in (True,1.0,-1,float('nan'),2):
            request['scenario']=dict(operation='reconcile',expected_revision=rev,current_revision=1)
            self.rejected(lambda:c.validate_request(request),'REVISION_CONFLICT')
        request['scenario']=dict(operation='reconcile',expected_revision=1,current_revision=2)
        self.rejected(lambda:c.validate_request(request),'REVISION_CONFLICT')
        request['scenario']=dict(operation='audit',current=dict(size=float('inf')))
        self.rejected(lambda:c.validate_request(request),'INVALID_JSON_DATA')
        request['scenario']=dict(operation='plan'); request['manifest']['production_approved']=True
        self.rejected(lambda:c.validate_request(request),'MANIFEST_INVALID')

    def test_component_set_references_and_exact_symmetry_coverage(self):
        d=definition()
        occurrence=dict(schema_version=1,occurrence_id='handle/1',definition_id=d['definition_id'],
                        semantic_role='base/front/handle',anchor=anchor())
        group=dict(schema_version=1,symmetry_group_id='handles',mode='centered',scope='base/front',
                   member_ids=['handle/1'],axes=['u'],datum='panel')
        parts=dict(schema_version=1,template_version='synthetic-roc43-v1',source_reference='ROC-15/test',
                   definitions=[d],occurrences=[occurrence],symmetry_groups=[group])
        self.assertEqual(c.validate_component_set(parts),parts)
        changed=copy.deepcopy(parts); changed['definitions'].append(d)
        self.rejected(lambda:c.validate_component_set(changed),'DUPLICATE_ID')
        changed=copy.deepcopy(parts); changed['occurrences'][0]['definition_id']='unknown'
        self.rejected(lambda:c.validate_component_set(changed),'DEFINITION_NOT_FOUND')
        changed=copy.deepcopy(parts); changed['symmetry_groups']=[]
        self.rejected(lambda:c.validate_component_set(changed),'SYMMETRY_GROUP_MISSING')
        changed=copy.deepcopy(parts); changed['symmetry_groups'][0]['scope']='base/rear'
        self.rejected(lambda:c.validate_component_set(changed),'SYMMETRY_SCOPE_MISMATCH')
        changed=copy.deepcopy(parts); changed.update(definitions=[],occurrences=[],symmetry_groups=[])
        self.rejected(lambda:c.validate_component_set(changed),'COMPONENT_SET_EMPTY')
        changed=copy.deepcopy(parts); changed['template_version']='real-v1'
        self.rejected(lambda:c.validate_component_set(changed),'SOURCE_SCOPE_INVALID')

    def test_recipe_is_inert_synthetic_data_with_explicit_header(self):
        recipe=json.loads((ROOT / 'tests/core_design/synthetic_template.json').read_text(encoding='utf-8'))
        request=dict(spec=case(),manifest=copy.deepcopy(FIXTURES['manifest']),scenario=dict(operation='plan'),template_recipe=recipe)
        self.assertEqual(c.validate_request(request),request)
        request['template_recipe']['query']='__import__("os")'
        self.rejected(lambda:c.validate_request(request),'UNKNOWN_FIELD')
        request['template_recipe'].pop('query'); request['template_recipe']['template_version']='other'
        self.rejected(lambda:c.validate_request(request),'RECIPE_MISMATCH')

    def test_inventory_draft_is_not_a_ready_component_contract(self):
        from rockpro_cad.core_case.test_manifest import inventory
        from rockpro_cad.core_case.manifest import build_manifest,validate_manifest
        draft=build_manifest(inventory())
        self.assertTrue(validate_manifest(draft).valid)
        self.assertFalse(validate_manifest(draft).production_ready)
        request=dict(spec=case(),manifest=draft,scenario=dict(operation='plan'))
        self.rejected(lambda:c.validate_request(request),'MANIFEST_NOT_READY')
        self.rejected(lambda:c.validate_part_occurrence(draft['occurrences'][0]),'UNKNOWN_FIELD')

    def test_contract_validation_remains_separate_from_the_pure_planner(self):
        import rockpro_cad.core_case as package
        self.assertFalse(callable(getattr(c,'plan_case',None)))
        self.assertTrue(callable(package.plan_case))


if __name__ == '__main__':
    unittest.main()
