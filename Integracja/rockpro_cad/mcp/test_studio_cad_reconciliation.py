"""Synthetic failed-job evidence only: no CAD or real project database access."""
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rockpro_cad import studio_cad_jobs as jobs
from rockpro_cad.studio_cad import fingerprint
from rockpro_cad.mcp import project_store


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.patch = patch.object(project_store, 'DB_PATH', self.root/'projects.sqlite3')
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.operation = 'a'*32
        self.plan_id = 'b'*32
        self.folder = self.root/('studio-'+self.plan_id+'-1234abcd'); self.folder.mkdir()
        self.source = self.root/'original.ics'; self.source.write_bytes(b'source original')
        self.recovery = self.folder/'recovery.ics'; self.recovery.write_bytes(b'owned recovery')
        self.code = self.folder/'native-source.cs'; self.code.write_bytes(b'pinned executor')
        self.source_sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.code_sha = hashlib.sha256(self.code.read_bytes()).hexdigest()
        self.spec = dict(contract='roc46-native-v1', executor_sha256=self.code_sha,
                         runner_sha256='e'*64, sources=[dict(key='baseline',sha256=self.source_sha)],
                         parameters={'RP_Wysokosc':300}, panels=[dict(id='panel')])
        self.plan = dict(schema='rockpro.studio-cad-plan/1', plan_id=self.plan_id, native_spec=self.spec)
        self.plan['plan_sha256'] = fingerprint(self.plan)
        request = copy.deepcopy(self.spec)
        request.update(plan_sha256=self.plan['plan_sha256'], expected_pid=123, show_final=True)
        request['sources'][0]['path'] = str(self.source)
        self.write('request.json', request)
        self.write('compile.json', dict(returncode=0,source_sha256=self.code_sha))
        self.write('result.json', dict(passed=False, sources_unchanged=True,
            existing_documents_preserved=True, before=['preserved doc'], after_existing=['preserved doc'],
            final_visible=False, recovery_path=str(self.recovery), error='Original failure retained'))
        self.write('addon_cleanup.json', dict(removed=True,count_after=0,remaining_count=0))
        self.old_receipt = json.dumps(dict(passed=False,private_detail='historical'))
        with project_store.db() as conn:
            jobs._tables(conn)
            conn.execute('INSERT INTO studio_cad_jobs VALUES (?,?,?,?,?,?,?,?)',
                         (self.operation,self.plan_id,self.plan['plan_sha256'],json.dumps(self.plan),
                          'outcome_unknown','created','updated',self.old_receipt))
        self.lock_events = []
        @contextmanager
        def lock():
            self.lock_events.append('enter')
            try: yield
            finally: self.lock_events.append('exit')
        mutex = patch.object(jobs,'cad_writer_lock',side_effect=lock)
        mutex.start(); self.addCleanup(mutex.stop)

    def write(self, name, value):
        (self.folder/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')

    def change(self, name, **values):
        data=json.loads((self.folder/name).read_text(encoding='utf-8'));data.update(values);self.write(name,data)

    def run_reconcile(self):
        return jobs.reconcile_failed_job(self.operation,self.folder)

    def refused(self, code='CAD_RECONCILE_EVIDENCE'):
        with self.assertRaises(jobs.CadJobError) as caught:self.run_reconcile()
        self.assertEqual(caught.exception.details['code'],code)
        with project_store.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM studio_cad_job_reconciliations').fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT receipt FROM studio_cad_jobs').fetchone()[0],self.old_receipt)

    def test_reconciles_failed_history_atomically_idempotent_and_nonblocking(self):
        result=self.run_reconcile()
        self.assertEqual(result['status'],'failed_reconciled')
        self.assertFalse(result['requires_reconciliation']);self.assertFalse(result['receipt']['passed'])
        self.assertEqual(result,self.run_reconcile())
        self.assertEqual(self.lock_events,['enter','exit','enter','exit'])
        with project_store.db() as conn:
            audit=conn.execute('SELECT * FROM studio_cad_job_reconciliations').fetchone()
            self.assertEqual(audit['previous_status'],'outcome_unknown')
            self.assertEqual(audit['previous_receipt'],self.old_receipt)
            proof=json.loads(audit['evidence_payload'])
            self.assertEqual(audit['evidence_sha256'],fingerprint(proof))
            self.assertEqual(proof['recovery_sha256'],hashlib.sha256(self.recovery.read_bytes()).hexdigest())
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM studio_cad_jobs WHERE status IN ('queued','running','outcome_unknown')").fetchone()[0],0)
        with patch.object(jobs,'verify_plan'),patch.object(jobs.threading.Thread,'start'):
            plan=dict(self.plan,executable=True,blockers=[])
            service=jobs.CadJobs(lambda p:None)
            self.assertEqual(service.submit(plan,'f'*32)['status'],'queued')
            jobs._ACTIVE.discard(jobs._key('f'*32))

    def test_queued_running_success_rejected_are_never_reconciled(self):
        for status in ['queued','running','succeeded','rejected']:
            with self.subTest(status=status):
                with project_store.db() as conn:conn.execute('UPDATE studio_cad_jobs SET status=?',(status,))
                self.refused('CAD_RECONCILE_STATUS')

    def test_missing_report_and_wrong_folder(self):
        (self.folder/'result.json').unlink();self.refused()
        with self.assertRaises(jobs.CadJobError):jobs.reconcile_failed_job(self.operation,self.root)

    def test_request_plan_and_geometry_and_compiler_mismatch(self):
        for name,values in [('request.json',dict(plan_sha256='f'*64)),
                            ('request.json',dict(parameters={})),
                            ('compile.json',dict(source_sha256='f'*64)),
                            ('compile.json',dict(returncode=1))]:
            with self.subTest(values=values):
                original=(self.folder/name).read_bytes();self.change(name,**values)
                self.refused();(self.folder/name).write_bytes(original)
        self.code.write_bytes(b'other executor');self.refused()

    def test_stored_plan_hash_cannot_be_forged(self):
        bad=copy.deepcopy(self.plan);bad['native_spec']['parameters']={}
        with project_store.db() as conn:conn.execute('UPDATE studio_cad_jobs SET plan_payload=?',(json.dumps(bad),))
        self.refused()

    def test_cleanup_and_preservation_proofs_required(self):
        cases=[('result.json',dict(passed=True)),('result.json',dict(sources_unchanged=False)),
               ('result.json',dict(existing_documents_preserved=False)),('result.json',dict(after_existing=[])),
               ('result.json',dict(final_visible=True)),('result.json',dict(result_cleanup_error='failed')),
               ('result.json',dict(preservation_error='failed')),('addon_cleanup.json',dict(removed=False)),
               ('addon_cleanup.json',dict(remaining_count=1)),('addon_cleanup.json',dict(count_after=1)),
               ('addon_cleanup.json',dict(error='failed'))]
        for name,values in cases:
            with self.subTest(values=values):
                original=(self.folder/name).read_bytes();self.change(name,**values)
                self.refused();(self.folder/name).write_bytes(original)

    def test_source_mismatch_and_recovery_outside_missing_or_empty(self):
        self.source.write_bytes(b'changed');self.refused();self.source.write_bytes(b'source original')
        self.change('result.json',recovery_path=str(self.source));self.refused()
        self.change('result.json',recovery_path=str(self.recovery));self.recovery.write_bytes(b'');self.refused()
        self.recovery.unlink();self.refused()

    def test_idempotency_requires_exact_evidence(self):
        self.run_reconcile();self.change('result.json',error='different historical evidence')
        with self.assertRaises(jobs.CadJobError) as caught:self.run_reconcile()
        self.assertEqual(caught.exception.details['code'],'CAD_RECONCILE_CONFLICT')
        self.assertEqual(jobs.CadJobs().get(self.operation)['status'],'failed_reconciled')

    def test_failed_compare_and_swap_rolls_back_audit_and_receipt(self):
        with project_store.db() as conn:
            conn.execute("""CREATE TRIGGER refuse_reconciliation BEFORE UPDATE ON studio_cad_jobs
                WHEN NEW.status='failed_reconciled' BEGIN SELECT RAISE(IGNORE); END""")
        self.refused('CAD_RECONCILE_CONFLICT')
        self.assertEqual(jobs.CadJobs().get(self.operation)['status'],'outcome_unknown')

    def test_cli_does_not_create_a_missing_database(self):
        import importlib.util
        path=Path(__file__).resolve().parents[3]/'scripts/reconcile_studio_cad_job.py'
        spec=importlib.util.spec_from_file_location('reconcile_cli',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch('builtins.print'):
            self.assertEqual(module.main(['--database',str(self.root/'absent.db'),'--operation',self.operation,'--evidence',str(self.folder)]),1)
        self.assertFalse((self.root/'absent.db').exists())


if __name__ == '__main__':unittest.main()
