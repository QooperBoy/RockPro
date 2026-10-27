import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from rockpro_cad import studio_cad_jobs as jobs
from rockpro_cad.mcp import project_store


def plan():
    return dict(schema='rockpro.studio-cad-plan/1', plan_id='1'*32,
                draft_id='2'*32, draft_revision=1, draft_sha256='3'*64,
                plan_sha256='4'*64, target_year=2027, executable=True,
                blockers=[], adapter_id='synthetic-test-only')


class CadJobsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_patch = patch.object(project_store, 'DB_PATH', Path(self.temp.name)/'project.sqlite3')
        self.db_patch.start(); self.addCleanup(self.db_patch.stop)
        verify_patch = patch.object(jobs, 'verify_plan')
        self.verify = verify_patch.start()
        self.addCleanup(verify_patch.stop)
        self.operation = 'a'*32

    def wait(self, service, operation=None):
        operation = operation or self.operation
        until = time.monotonic()+5
        while time.monotonic() < until:
            result = service.get(operation)
            if result['status'] not in ('queued', 'running'):
                return result
            time.sleep(.01)
        self.fail('Synthetic worker did not finish')

    def assert_code(self, code, call):
        with self.assertRaises(jobs.CadJobError) as ctx:
            call()
        self.assertEqual(ctx.exception.details['code'], code)
        return ctx.exception.details

    def test_idempotent_success_detached_plan_and_sanitized_receipt(self):
        calls=[]
        def execute(p):
            calls.append(copy.deepcopy(p)); p['blockers'].append('executor mutation')
            return dict(passed=True, plan_sha256=p['plan_sha256'], path='PRIVATE', traceback='PRIVATE')
        service=jobs.CadJobs(execute); p=plan()
        service.submit(p,self.operation)
        result=self.wait(service)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(result['receipt'],dict(passed=True,plan_sha256=p['plan_sha256']))
        self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertEqual(service.submit(p,self.operation),result)
        self.assertEqual(len(calls),1);self.assertEqual(p,plan())
        self.assertEqual(self.verify.call_count,3)
        with project_store.db() as conn:
            row=conn.execute('SELECT plan_payload FROM studio_cad_jobs').fetchone()
            self.assertEqual(json.loads(row[0]),p)

    def test_same_id_other_plan_hash_conflicts(self):
        service=jobs.CadJobs(lambda p:dict(passed=True,plan_sha256=p['plan_sha256']))
        service.submit(plan(),self.operation);self.wait(service)
        other=plan();other['plan_sha256']='b'*64
        self.assert_code('CAD_OPERATION_CONFLICT',lambda:service.submit(other,self.operation))

    def test_receipt_must_be_true_and_bound_to_this_plan(self):
        for index,raw in enumerate((None,dict(passed=True),dict(passed=True,plan_sha256='9'*64),
                                   dict(passed=1,plan_sha256='4'*64),dict(passed=False,plan_sha256='4'*64))):
            with self.subTest(raw=raw):
                # Separate isolated databases; unknown results intentionally block.
                with patch.object(project_store,'DB_PATH',Path(self.temp.name)/f'bad-{index}.sqlite3'):
                    service=jobs.CadJobs(lambda p:raw)
                    service.submit(plan(),self.operation)
                    result=self.wait(service)
                    self.assertEqual(result['status'],'outcome_unknown')
                    self.assertTrue(result['requires_reconciliation'])
                    self.assertIsNone(result['receipt'])

    def test_exception_never_retries_and_does_not_expose_private_detail(self):
        calls=[]
        def broken(p):
            calls.append(p);raise RuntimeError('secret C:/private/customer.ics')
        service=jobs.CadJobs(broken)
        service.submit(plan(),self.operation);result=self.wait(service)
        self.assertEqual(result['status'],'outcome_unknown')
        service.submit(plan(),self.operation)
        self.assertEqual(len(calls),1)
        self.assertNotIn('secret',json.dumps(result));self.assertNotIn('private',json.dumps(result))
        self.assert_code('CAD_JOB_BUSY',lambda:service.submit(plan(),'b'*32))

    def test_blocked_plan_and_missing_executor_never_execute_or_reserve(self):
        calls=[];service=jobs.CadJobs(lambda p:calls.append(p))
        for changes in (dict(executable=False),dict(executable=1),dict(blockers=['missing datum'])):
            p=plan();p.update(changes)
            self.assert_code('CAD_PLAN_BLOCKED',lambda:service.submit(p,self.operation))
        self.assert_code('CAD_EXECUTOR_UNAVAILABLE',lambda:jobs.CadJobs().submit(plan(),self.operation))
        self.assertEqual(calls,[])
        self.assert_code('CAD_JOB_NOT_FOUND',lambda:service.get(self.operation))

    def test_two_instances_share_one_dispatch_slot_and_executor_runs_outside_db(self):
        started=threading.Event();release=threading.Event();outside=[]
        def execute(p):
            # Acquiring a write transaction proves no dispatch DB lock remains.
            with project_store.db() as conn:
                conn.execute('BEGIN IMMEDIATE');outside.append(True)
            started.set();release.wait(5)
            return dict(passed=True,plan_sha256=p['plan_sha256'])
        first=jobs.CadJobs(execute);second=jobs.CadJobs(execute)
        first.submit(plan(),self.operation)
        try:
            self.assertTrue(started.wait(3))
            self.assertEqual(second.get(self.operation)['status'],'running')
            self.assert_code('CAD_JOB_BUSY',lambda:second.submit(plan(),'b'*32))
            second.submit(plan(),self.operation)
            self.assertEqual(outside,[True])
        finally:
            release.set();self.wait(first)

    def test_completed_receipt_persists_without_executor(self):
        original=jobs.CadJobs(lambda p:dict(passed=True,plan_sha256=p['plan_sha256']))
        original.submit(plan(),self.operation);expected=self.wait(original)
        restarted=jobs.CadJobs()
        self.assertEqual(restarted.get(self.operation),expected)
        self.assertEqual(restarted.submit(plan(),self.operation),expected)

    def test_abandoned_queued_or_running_requires_reconciliation_never_restarts(self):
        for index,status in enumerate(('queued','running')):
            with patch.object(project_store,'DB_PATH',Path(self.temp.name)/f'restart-{index}.sqlite3'):
                with project_store.db() as conn:
                    jobs._tables(conn)
                    conn.execute('INSERT INTO studio_cad_jobs VALUES (?,?,?,?,?,?,?,?)',
                                 (self.operation,'1'*32,'4'*64,json.dumps(plan()),status,'start','start',None))
                calls=[];service=jobs.CadJobs(lambda p:calls.append(p))
                result=service.get(self.operation)
                self.assertEqual(result['status'],'reconciliation_required')
                self.assertEqual(result['recorded_status'],status)
                self.assertEqual(service.submit(plan(),self.operation),result)
                self.assert_code('CAD_JOB_BUSY',lambda:service.submit(plan(),'b'*32))
                self.assertEqual(calls,[])

    def test_plan_verification_and_operation_validation_precede_execution(self):
        self.verify.side_effect=ValueError('C:/private/why')
        service=jobs.CadJobs(lambda p:self.fail('Must not execute'))
        details=self.assert_code('CAD_INVALID_PLAN',lambda:service.submit(plan(),self.operation))
        self.assertNotIn('private',json.dumps(details))
        self.assert_code('CAD_INVALID_OPERATION_ID',lambda:service.submit(plan(),'../bad'))
        self.assert_code('CAD_INVALID_OPERATION_ID',lambda:service.get(True))

    def test_worker_start_failure_remains_durable_and_is_not_retried(self):
        calls=[];service=jobs.CadJobs(lambda p:calls.append(p))
        with patch.object(jobs.threading.Thread,'start',side_effect=RuntimeError('private launcher detail')):
            result=service.submit(plan(),self.operation)
        self.assertEqual(result['status'],'outcome_unknown')
        self.assertEqual(service.submit(plan(),self.operation),result)
        self.assertEqual(calls,[])

    def test_plan_changed_after_submission_is_rejected_before_executor(self):
        self.verify.side_effect=[None,ValueError('draft changed: private details')]
        calls=[]
        def execute(p):
            calls.append(p)
            return dict(passed=True,plan_sha256=p['plan_sha256'])
        service=jobs.CadJobs(execute)
        service.submit(plan(),self.operation)
        result=self.wait(service)
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(result['code'],'CAD_PLAN_REJECTED')
        self.assertFalse(result['requires_reconciliation'])
        self.assertIsNone(result['receipt']);self.assertEqual(calls,[])
        self.assertNotIn('private',json.dumps(result))
        self.verify.side_effect=None
        self.assertEqual(service.submit(plan(),self.operation),result)
        service.submit(plan(),'b'*32)
        self.assertEqual(self.wait(service,'b'*32)['status'],'succeeded')
        self.assertEqual(len(calls),1)


if __name__=='__main__':
    unittest.main()
