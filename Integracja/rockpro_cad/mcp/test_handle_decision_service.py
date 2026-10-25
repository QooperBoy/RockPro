import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import project_store as store
import worker
import handle_decision_service as service
from rockpro_cad.core_case.test_native_changes import four_handles
from rockpro_cad.core_case.handle_measurement import snapshot_fingerprint


class HandleDecisionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patch=patch.object(store,'DB_PATH',self.root/'db.sqlite3');self.patch.start()
        self.rootpatch=patch.object(worker,'ROOT',self.root);self.rootpatch.start()
        source=self.root/'source.ics';source.write_bytes(b'test only')
        self.project=store.save_project('Handle test',source=str(source))['project']['id']
        b,m,v=four_handles();c=copy.deepcopy(b);c['members'][-1]['matrix_world_mm'][3][1]+=5
        self.evidence=dict(baseline=b,current=c,mapping=m,per_wall=2,target_values=v,observed_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())

    def tearDown(self):self.rootpatch.stop();self.patch.stop();self.temp.cleanup()

    def save(self,expected=0,project_revision=1):
        preview=worker.dispatch('preview_handle_reconciliation',dict(evidence=self.evidence,choice='adopt_offset'))
        return worker.dispatch('save_handle_reconciliation',dict(project_id=self.project,evidence=self.evidence,
            choice='adopt_offset',expected_revision=expected,expected_project_revision=project_revision,
            review_sha256=preview['review_sha256'],decision_reference='SYNTHETIC-QA-ONLY'))

    def test_offset_and_evidence_survive_database_reopen(self):
        saved=self.save();read=service.get_handle_reconciliation(self.project)
        self.assertEqual(read['revision'],1);self.assertEqual(read['evidence'],self.evidence)
        self.assertEqual(read['result']['state']['offsets_mm']['handles/right/2'],[0,5,0])
        self.assertFalse(saved['cad_changed']);self.assertFalse(saved['production_approved'])

    def test_independent_project_and_decision_cas_are_not_refreshed(self):
        self.save()
        with self.assertRaisesRegex(ValueError,'DECISION_REVISION_CONFLICT'):self.save()
        store.save_project('Changed',project_id=self.project,expected_revision=1)
        with self.assertRaisesRegex(ValueError,'PROJECT_CONFLICT'):self.save(1,1)
        self.assertEqual(service.get_handle_reconciliation(self.project)['revision'],1)

    def test_changed_review_hash_cannot_save_and_ai_has_no_write_tool(self):
        preview=service.preview_handle_reconciliation(self.evidence,'adopt_offset')
        changed=copy.deepcopy(self.evidence);changed['target_values']['RP_Depth']=550
        with self.assertRaisesRegex(ValueError,'REVIEW_CHANGED'):
            service.save_handle_reconciliation(self.project,changed,'adopt_offset',0,1,preview['review_sha256'],'TEST')
        import agent_server
        self.assertNotIn('save_handle_reconciliation',agent_server.ALLOWLIST)

    def test_source_changed_since_preview_cannot_record_decision(self):
        (self.root/'source.ics').write_bytes(b'concurrent saved edit')
        with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):self.save()
        self.assertEqual(service.get_handle_reconciliation(self.project)['revision'],0)

    def measurement(self):
        return dict(snapshot=self.evidence['current'],source_sha256=self.evidence['observed_source_sha256'],
            snapshot_sha256=snapshot_fingerprint(self.evidence['current']),
            provenance=dict(modified=True,file_guid=self.evidence['current']['file_guid']),native_read_only=True)

    def test_native_measurement_token_is_bound_and_rechecked_before_save(self):
        self.save()
        with patch.object(service,'capture_handle_measurement',return_value=self.measurement()) as reader:
            measured=service.measure_handle_reconciliation(self.project,1,1)
            args=dict(project_id=self.project,evidence=measured['evidence'],choice='adopt_offset',expected_revision=1,
                expected_project_revision=1,decision_reference='QA-ONLY',prior_state=measured['prior_state'],measurement_id=measured['measurement_id'])
            preview=service.preview_handle_reconciliation(args['evidence'],args['choice'],args['prior_state'])
            saved=service.save_handle_reconciliation(**args,review_sha256=preview['review_sha256'])
        self.assertEqual(reader.call_count,2);self.assertTrue(saved['result']['native_capture_verified_by_service'])
        self.assertEqual(saved['revision'],2);self.assertTrue(measured['document_modified']);self.assertFalse(saved['cad_changed'])

    def test_stale_native_measurement_and_changed_ticket_data_do_not_save(self):
        self.save()
        with patch.object(service,'capture_handle_measurement',return_value=self.measurement()):
            measured=service.measure_handle_reconciliation(self.project,1,1)
        args=dict(project_id=self.project,evidence=measured['evidence'],choice='adopt_offset',expected_revision=1,
            expected_project_revision=1,decision_reference='QA-ONLY',prior_state=measured['prior_state'],measurement_id=measured['measurement_id'])
        preview=service.preview_handle_reconciliation(args['evidence'],args['choice'],args['prior_state'])
        changed=self.measurement();changed['snapshot_sha256']='f'*64
        with patch.object(service,'capture_handle_measurement',return_value=changed):
            with self.assertRaisesRegex(ValueError,'MEASUREMENT_STALE'):
                service.save_handle_reconciliation(**args,review_sha256=preview['review_sha256'])
        evidence=copy.deepcopy(args['evidence']);evidence['target_values']['RP_Depth']=550
        preview=service.preview_handle_reconciliation(evidence,args['choice'],args['prior_state'])
        with self.assertRaisesRegex(ValueError,'MEASUREMENT_BINDING_CONFLICT'):
            service.save_handle_reconciliation(**(args|dict(evidence=evidence)),review_sha256=preview['review_sha256'])
        self.assertEqual(service.get_handle_reconciliation(self.project)['revision'],1)

    def test_native_measurement_does_not_invent_a_baseline_or_refresh_cas(self):
        with patch.object(service,'capture_handle_measurement') as reader:
            with self.assertRaisesRegex(ValueError,'BASELINE_REQUIRED'):service.measure_handle_reconciliation(self.project,0,1)
            reader.assert_not_called()
        self.save()
        with patch.object(service,'capture_handle_measurement') as reader:
            with self.assertRaisesRegex(ValueError,'REVISION_CONFLICT'):service.measure_handle_reconciliation(self.project,0,1)
            reader.assert_not_called()


if __name__=='__main__':unittest.main()
