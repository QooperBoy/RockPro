import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import material_service as materials
import project_store as store
import server
import worker


def approved(document):
    document['approval']={'status':'approved','reference':'TEST-ONLY','by':'test-fixture',
                          'content_sha256':materials.approval_payload_hash(document)}
    return document


def fixture(project_id, revision='R1', **row_changes):
    row=dict(id='floor',material_id='plywood-test',finish='green',technology_id='test-saw',
             thickness_mm=9,cut_length_mm=600,cut_width_mm=400,per_case_quantity=2,
             grain_axis='X',rotation_allowed=False,required_date='2026-11-01',dimension_source='technology')
    row.update(row_changes)
    return approved(dict(schema_version=1,project_id=project_id,source_revision=revision,
                         model_sha256='a'*64,units='mm',case_quantity=3,scope='synthetic_test',rows=[row]))


class MaterialImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(store,'DB_PATH',self.root/'db.sqlite3'),patch.object(worker,'ROOT',self.root)]
        for p in self.patches:p.start()
        source=self.root/'source.ics';source.write_bytes(b'test only')
        self.projects=[store.save_project('Synthetic '+str(n),source=str(source))['project']['id'] for n in range(3)]
        (self.root/'imports').mkdir();self.path=self.root/'imports/bom.json'

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def save(self,document,revision=0):
        self.path.write_text(json.dumps(document),encoding='utf-8')
        preview=worker.dispatch('preview_bom_file',{'path':str(self.path)})
        return worker.dispatch('import_bom_file',dict(project_id=document['project_id'],path=str(self.path),
            expected_revision=revision,expected_source_sha256=preview['source_sha256']))

    def test_replay_never_adds_demand_and_source_is_preserved(self):
        doc=fixture(self.projects[0]);first=self.save(doc);data=self.path.read_bytes()
        repeated=self.save(doc);self.assertTrue(repeated['reused']);self.assertEqual(repeated['revision'],1)
        demand=materials.aggregate_bom_demand([self.projects[0]])
        self.assertEqual(demand['total_parts'],6);self.assertEqual(demand['groups'][0]['sources'][0]['quantity'],6)
        with store.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM bom_versions').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT source_blob FROM bom_versions').fetchone()[0],data)
        self.assertFalse(first['production_approved'])

    def test_new_revision_replaces_demand_and_old_replay_is_historical(self):
        old=fixture(self.projects[0]);self.save(old)
        self.save(fixture(self.projects[0],'R2',per_case_quantity=4),1)
        self.assertTrue(self.save(old)['historical'])
        self.assertEqual(materials.aggregate_bom_demand([self.projects[0]])['total_parts'],12)
        with self.assertRaisesRegex(ValueError,'REVISION_REUSED'):
            self.save(fixture(self.projects[0],'R1',per_case_quantity=10),2)

    def test_aggregation_keeps_technology_dimensions_dates_and_materials_separate(self):
        doc=fixture(self.projects[0]);base=doc['rows'][0]
        for i,change in enumerate([{'thickness_mm':12},{'finish':'black'},{'technology_id':'other'},
                                   {'required_date':'2026-11-02'},{'material_id':'other'},
                                   {'grain_axis':'Y'},{'rotation_allowed':True},{'cut_width_mm':399}]):
            doc['rows'].append(base|change|{'id':'row'+str(i)})
        self.save(approved(doc));self.save(fixture(self.projects[1]))
        demand=materials.aggregate_bom_demand(self.projects[:2])
        self.assertEqual(len(demand['groups']),9);self.assertEqual(demand['total_parts'],60)
        self.assertIn(12,[g['quantity'] for g in demand['groups']])
        self.assertEqual(demand['demand_sha256'],materials.aggregate_bom_demand(self.projects[1::-1])['demand_sha256'])

    def test_conflict_and_changed_file_do_not_write(self):
        doc=fixture(self.projects[0]);self.save(doc)
        with self.assertRaisesRegex(ValueError,'REVISION_CONFLICT'):self.save(fixture(self.projects[0],'R2'),0)
        preview=materials.preview_bom_file(self.path)
        self.path.write_text(json.dumps(fixture(self.projects[0],'R3')),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):
            materials.import_bom_file(self.projects[0],self.path,1,preview['source_sha256'])
        with store.db() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM bom_versions').fetchone()[0],1)

    def test_assembly_bbox_unknown_policy_and_stale_approval_are_refused(self):
        for change in [{'dimension_source':'assembly_bbox'},{'grain_axis':None},{'cut_width_mm':float('nan')},
                       {'per_case_quantity':True},{'required_date':'20261101'}]:
            doc=fixture(self.projects[0]);doc['rows'][0].update(change)
            with self.assertRaises(ValueError):materials.validate_bom(approved(doc))
        doc=fixture(self.projects[0]);doc['case_quantity']=4
        with self.assertRaisesRegex(ValueError,'Approval'):materials.validate_bom(doc)
        doc=fixture(self.projects[0]);doc['units']='m'
        with self.assertRaisesRegex(ValueError,'mm'):materials.validate_bom(approved(doc))

    def test_synthetic_and_source_inputs_are_not_mixed(self):
        self.save(fixture(self.projects[0]));doc=fixture(self.projects[1]);doc['scope']='source_input';self.save(approved(doc))
        with self.assertRaisesRegex(ValueError,'mix'):materials.aggregate_bom_demand(self.projects[:2])

    def test_mcp_contract_exposes_only_explicit_arguments(self):
        schemas={s['name']:s for s in server.SCHEMAS}
        self.assertTrue(schemas['aggregate_bom_demand']['annotations']['readOnlyHint'])
        with self.assertRaisesRegex(ValueError,'Invalid material'):
            worker.dispatch('aggregate_bom_demand',{'project_ids':self.projects[:1],'exec':'anything'})


if __name__=='__main__':unittest.main()
