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


if __name__=='__main__':unittest.main()
