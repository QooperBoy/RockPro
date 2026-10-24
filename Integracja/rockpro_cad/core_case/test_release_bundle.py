import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.release_bundle import create_bundle,inspect_bundle,prototype_bom,sha
from rockpro_cad.part_registry import contract,metadata


class ReleaseBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.model=self.root/'working.ics';self.model.write_bytes(b'known model revision')
        self.bom=self.root/'bom.csv';self.bom.write_text('id,quantity\npart,1\n',encoding='utf-8')
        self.binding=dict(project_id='project',revision_id='r1',model_sha256=sha(self.model),
            input_version='input-v1',input_sha256='a'*64,rule_version='rules-v1',rules_sha256='b'*64,
            template_version='template-v1',template_sha256='c'*64)
        self.artifacts=[dict(role='bom',path=str(self.bom),model_sha256=sha(self.model),revision_id='r1')]
        self.output=self.root/'release'

    def tearDown(self):self.temp.cleanup()

    def create(self):
        return create_bundle(self.model,self.output,self.binding,self.artifacts,
                             [dict(name='native-reopen',status='PASS')],['Prepare drawings'])

    def test_complete_binding_and_missing_deliverables_remain_visible(self):
        data=self.create();result=inspect_bundle(self.output/'manifest.json',self.model)
        self.assertTrue(result['valid']);self.assertFalse(result['ready_for_review'])
        self.assertEqual(result['pending_roles'],['drawing','production'])
        self.assertEqual(data['binding'],self.binding)
        self.assertEqual((self.output/'model.ics').read_bytes(),self.model.read_bytes())
        self.assertFalse(data['production_approved'])
        with self.assertRaisesRegex(ValueError,'already exists'):self.create()

    def test_model_change_invalidates_old_export_without_modifying_history(self):
        self.create();manifest=(self.output/'manifest.json').read_bytes()
        self.model.write_bytes(b'new model revision')
        result=inspect_bundle(self.output/'manifest.json',self.model)
        self.assertEqual(result['status'],'outdated');self.assertFalse(result['valid'])
        self.assertIn('MODEL_REVISION_CHANGED',{r['code'] for r in result['errors']})
        self.assertEqual((self.output/'manifest.json').read_bytes(),manifest)
        self.assertEqual((self.output/'model.ics').read_bytes(),b'known model revision')

    def test_changed_artifact_and_path_escape_are_detected(self):
        self.create();(self.output/'bom.csv').write_bytes(b'tampered')
        self.assertEqual(inspect_bundle(self.output/'manifest.json',self.model)['errors'][0]['code'],'FILE_CHANGED')
        data=json.loads((self.output/'manifest.json').read_text(encoding='utf-8'))
        data['files'][0]['path']='../working.ics'
        (self.output/'manifest.json').write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'path'):inspect_bundle(self.output/'manifest.json',self.model)

    def test_wrong_model_revision_and_duplicate_names_refuse_before_copy(self):
        for change in ('model_sha256','revision_id'):
            artifacts=copy.deepcopy(self.artifacts);artifacts[0][change]='wrong'
            with self.assertRaisesRegex(ValueError,'another model'):create_bundle(self.model,self.output,self.binding,artifacts,[dict(name='x',status='PASS')])
            self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError,'Duplicate'):create_bundle(self.model,self.output,self.binding,self.artifacts*2,[dict(name='x',status='PASS')])
        self.assertFalse(self.output.exists())

    def test_root_inventory_does_not_invent_purchase_quantities_or_material(self):
        report=dict(passed=True,registry=contract(),result_sha256=sha(self.model),bindings=[dict(node_id=1,occurrence_id='socket/left/front',**metadata('socket'))])
        rows=list(csv.DictReader(io.StringIO(prototype_bom(report).decode('utf-8-sig'))))
        self.assertEqual(rows[0]['managed_root_occurrences'],'1')
        self.assertEqual(rows[0]['purchase_quantity'],'');self.assertEqual(rows[0]['approved_material'],'')
        self.assertEqual(rows[0]['stage_id'],'wheels')
        report['bindings'].append(report['bindings'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):prototype_bom(report)
