import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cutting_plan
import inventory_service
import material_revisions as revisions
import material_service as materials
import project_store as store
from test_material_service import fixture
import worker


class MaterialRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(store,'DB_PATH',self.root/'db.sqlite3'),patch.object(worker,'ROOT',self.root)]
        for p in self.patches:p.start()
        self.source=self.root/'source.ics';self.source.write_bytes(b'synthetic only')
        self.project=store.save_project('Test',source=str(self.source))['project']['id']
        (self.root/'imports').mkdir();self.bom('R1',2,0)

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def bom(self,label,count,expected):
        path=self.root/'imports/bom.json';path.write_text(json.dumps(fixture(self.project,label,per_case_quantity=count)),encoding='utf-8')
        preview=materials.preview_bom_file(path)
        materials.import_bom_file(self.project,path,expected,preview['source_sha256'])

    def plan(self,ident='plan-1',supersedes=None):
        demand=materials.aggregate_bom_demand([self.project])
        sheets=[dict(id='synthetic-board',material_id='plywood-test',finish='green',technology_id='test-saw',
            thickness_mm=9,length_mm=4000,width_mm=400,grain_axis='X',available_date='2026-10-01')]
        technology=dict(id='test-saw',profile_revision='TEST-ONLY',kerf_mm=3,trim_mm=[0,0,0,0],cut_type='guillotine')
        plan=cutting_plan.solve_reference(demand,sheets,technology)['plan']
        return worker.dispatch('save_material_plan',dict(plan_id=ident,project_ids=[self.project],sheets=sheets,technology=technology,cut_plan=plan,supersedes_plan_id=supersedes))

    def test_new_bom_invalidates_unstarted_plan_without_rewriting_old(self):
        old=self.plan();self.bom('R2',1,1)
        stale=revisions.get_material_plan('plan-1');self.assertEqual(stale['effective_status'],'outdated')
        self.assertEqual(old['payload_sha256'],stale['payload_sha256'])
        with self.assertRaisesRegex(ValueError,'OUTDATED'):revisions.start_material_plan('plan-1',1)
        new=self.plan('plan-2','plan-1');self.assertEqual(new['payload']['supersedes_plan_id'],'plan-1')

    def test_started_revision_preserves_production_orders_and_stock(self):
        self.plan();revisions.start_material_plan('plan-1',1)
        produced=dict(type='produced',group_index=0,quantity=4)
        revisions.record_material_progress('plan-1','actual-1',produced,2)
        order=dict(type='committed_order',reference='PO-TEST',item_id='plywood-test',quantity=1,total_gross='123.00',currency='PLN',arrival_date='2026-11-02')
        revisions.record_material_progress('plan-1','actual-2',order,3)
        self.bom('R2',1,1);self.plan('plan-2','plan-1');stock_before=inventory_service.get_inventory()
        report=revisions.compare_material_plans('plan-1','plan-2')
        self.assertEqual(report['old_status'],'changed_in_progress');self.assertEqual(report['produced_total'],4)
        self.assertEqual(report['changes'][0]['reuse_candidate_quantity'],3);self.assertEqual(report['unallocated_produced_total'],1)
        self.assertFalse(report['changes'][0]['reuse_approved']);self.assertEqual(report['committed_expense_by_currency'],{'PLN':'123.00'})
        self.assertEqual(report['committed_orders_preserved'],[order]);self.assertIsNone(report['incremental_cost'])
        self.assertEqual(inventory_service.get_inventory(),stock_before)

    def test_direct_saved_file_edit_and_card_revision_are_stale(self):
        self.plan();self.source.write_bytes(b'changed saved model')
        self.assertTrue(revisions.get_material_plan('plan-1')['stale'])
        self.plan('plan-2');card=store.get_project(self.project)['project']
        store.save_project(card['name'],project_id=self.project,quantity=2,expected_revision=card['revision'])
        self.assertTrue(revisions.get_material_plan('plan-2')['stale'])

    def test_progress_cas_replay_and_event_identity(self):
        self.plan();revisions.start_material_plan('plan-1',1)
        with self.assertRaisesRegex(ValueError,'already started'):revisions.start_material_plan('plan-1',2)
        event=dict(type='produced',group_index=0,quantity=1)
        with self.assertRaisesRegex(ValueError,'CONFLICT'):revisions.record_material_progress('plan-1','e',event,1)
        revisions.record_material_progress('plan-1','e',event,2)
        self.assertTrue(revisions.record_material_progress('plan-1','e',event,2)['replayed'])
        self.assertEqual(len(revisions.get_material_plan('plan-1')['progress']),1)
        with self.assertRaisesRegex(ValueError,'ID_REUSED'):revisions.record_material_progress('plan-1','e',event|dict(quantity=2),3)

    def test_changed_geometry_never_reuses_wrong_sized_parts(self):
        self.plan();revisions.start_material_plan('plan-1',1)
        revisions.record_material_progress('plan-1','e',dict(type='produced',group_index=0,quantity=6),2)
        path=self.root/'imports/bom.json';path.write_text(json.dumps(fixture(self.project,'R2',cut_length_mm=601)),encoding='utf-8')
        materials.import_bom_file(self.project,path,1,materials.preview_bom_file(path)['source_sha256'])
        self.plan('plan-2','plan-1');report=revisions.compare_material_plans('plan-1','plan-2')
        self.assertEqual(report['changes'][0]['reuse_candidate_quantity'],0)
        self.assertEqual(report['unallocated_produced_total'],6)

    def test_changed_progress_is_not_used_for_reuse_or_expense(self):
        self.plan();revisions.start_material_plan('plan-1',1)
        event=dict(type='produced',group_index=0,quantity=1)
        revisions.record_material_progress('plan-1','actual',event,2)
        self.plan('plan-2','plan-1')
        with store.db() as conn:conn.execute('UPDATE material_progress SET event_json=? WHERE id=?',
                                           (json.dumps(event|dict(quantity=999)),'actual'))
        with self.assertRaisesRegex(ValueError,'PROGRESS_INTEGRITY'):revisions.get_material_plan('plan-1')
        with self.assertRaisesRegex(ValueError,'PROGRESS_INTEGRITY'):revisions.compare_material_plans('plan-1','plan-2')
        with self.assertRaisesRegex(ValueError,'PROGRESS_INTEGRITY'):revisions.record_material_progress('plan-1','actual',event,2)

    def test_registered_snapshot_mismatch_is_stale_and_blocks_new_plan(self):
        archive=self.root/'snapshot.ics';archive.write_bytes(b'synthetic snapshot only')
        # An isolated schema fixture; this is not a native CAD validation receipt.
        with store.db() as conn:
            conn.execute('INSERT INTO snapshots(id,project_id,created_at,label,note,path,source,sha256,parameters,validation,report_path) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                ('qa-snapshot',self.project,store.now(),'Synthetic fixture','not native',str(archive),str(self.source),revisions.file_hash(archive),'{}','synthetic_test','not-native'))
        original=self.plan();archive.write_bytes(b'changed snapshot')
        read=revisions.get_material_plan('plan-1');self.assertTrue(read['stale'])
        self.assertEqual(read['payload_sha256'],original['payload_sha256'])
        self.assertIn('SNAPSHOT_INTEGRITY_MISMATCH',{d['code'] for d in read['input_diagnostics']})
        with self.assertRaisesRegex(ValueError,'INPUT_INTEGRITY'):self.plan('plan-2')
        with self.assertRaisesRegex(ValueError,'OUTDATED'):revisions.start_material_plan('plan-1',1)

    def test_metadata_pages_do_not_claim_file_freshness_or_rehash_models(self):
        self.plan('plan-a');self.plan('plan-b','plan-a')
        with patch.object(revisions,'file_hash',side_effect=AssertionError('Metadata must not hash CAD files')):
            first=worker.dispatch('list_material_plans',dict(limit=1))
            second=revisions.list_material_plans(limit=1,after_plan_id=first['next_cursor'])
        self.assertTrue(first['has_more']);self.assertFalse(second['has_more'])
        self.assertEqual([p['id'] for p in first['plans']+second['plans']],['plan-a','plan-b'])
        self.assertTrue(all(p['freshness_checked'] is False for p in first['plans']+second['plans']))
        self.assertEqual(second['plans'][0]['supersedes_plan_id'],'plan-a')

    def test_synthetic_production_cannot_be_reused_by_a_source_input_plan(self):
        self.plan();revisions.start_material_plan('plan-1',1)
        revisions.record_material_progress('plan-1','test-output',dict(type='produced',group_index=0,quantity=2),2)
        document=fixture(self.project,'R2',per_case_quantity=1)
        # Isolated domain-boundary test; this does not approve any client BOM.
        document['scope']='source_input';document['approval']['content_sha256']=materials.approval_payload_hash(document)
        path=self.root/'imports/bom.json';path.write_text(json.dumps(document),encoding='utf-8')
        materials.import_bom_file(self.project,path,1,materials.preview_bom_file(path)['source_sha256'])
        self.plan('plan-2','plan-1')
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):revisions.compare_material_plans('plan-1','plan-2')


if __name__=='__main__':unittest.main()
