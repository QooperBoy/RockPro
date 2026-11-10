import copy
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
import http.client
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from rockpro_cad import configurator, process_runs as runs
from rockpro_cad.process_capture import capture, import_native_progress
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept
from rockpro_cad.reference_studio import make_handler


def event(identifier='op', **kw):
    return dict(event_id=identifier, operation_id=identifier, kind='operation', stage='hardware',
                origin='standard', executor='sdk', status='success', **kw)


def intervention():
    return dict(event_id='ai-reason',operation_id='new-vent',kind='intervention',stage='hardware',
                origin='ai',executor='agent',status='resolved',reason='Brak mapy otworu nowej kratki',part_id='VENT-NEW')


class ProcessRunTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        p=patch.object(project_store,'DB_PATH',self.root/'projects.sqlite3');p.start();self.addCleanup(p.stop)
        self.saved=configurator.save_draft(concept())
        self.run=runs.create(self.saved['id'],1,'Próba')

    def test_300_operations_30_ai_sdk_not_double_counted(self):
        events=[intervention()]
        for i in range(300):
            e=event(str(i),duration_ms=2)
            if i>=270:e.update(origin='ai',intervention_id='new-vent',part_id='VENT-NEW')
            events.append(e)
        events.append(dict(event('parent',duration_ms=99999),kind='span'))
        r=runs.append(self.run['id'],events,state='completed');s=r['summary']
        self.assertEqual((s['completed'],s['by_origin']['standard'],s['by_origin']['ai']),(300,270,30))
        self.assertEqual(s['by_executor']['sdk'],300);self.assertEqual(s['percent']['ai'],10)
        self.assertEqual(s['interventions'],1);self.assertEqual(s['measured_leaf_ms'],600)

    def test_retry_and_running_event_count_once(self):
        a=dict(event(),status='running');b=dict(a,event_id='finish',status='failed',duration_ms=1)
        c=dict(b,event_id='retry',attempt=2,status='success',duration_ms=3)
        r=runs.append(self.run['id'],[a,b,c]);s=r['summary']
        self.assertEqual((s['completed'],s['operation_attempts'],s['retry_attempts']),(1,2,1))
        self.assertEqual(s['measured_leaf_ms'],4)
        self.assertEqual(runs.append(self.run['id'],[c])['summary'],s)
        with self.assertRaises(ValueError):runs.append(self.run['id'],[dict(c,label='changed')])

    def test_unknown_is_not_standard_and_empty_percent_missing(self):
        self.assertIsNone(runs.read(self.run['id'])['summary']['percent']['standard'])
        e=event();e.pop('origin');e.pop('executor')
        s=runs.append(self.run['id'],[e])['summary']
        self.assertEqual(s['by_origin']['unknown'],1);self.assertEqual(s['by_origin']['standard'],0)

    def test_ai_requires_prior_reason_and_failure_cannot_complete(self):
        e=dict(event(),origin='ai',intervention_id='new-vent')
        with self.assertRaises(ValueError):runs.append(self.run['id'],[e])
        runs.append(self.run['id'],[intervention(),dict(e,status='failed')])
        with self.assertRaises(ValueError):runs.append(self.run['id'],state='completed')
        runs.append(self.run['id'],state='failed')
        with self.assertRaises(ValueError):runs.append(self.run['id'],[event('another')])

    def test_revision_binding_import_and_idempotence(self):
        r=runs.append(self.run['id'],[event()],state='completed')
        self.assertEqual(runs.import_report(r,self.saved['id'],1)['id'],r['id'])
        d=concept();d['internal_mm'][0]+=100;configurator.save_draft(d,self.saved['id'],1)
        with self.assertRaises(ValueError):runs.import_report(r,self.saved['id'],2)
        with self.assertRaises(ValueError):runs.import_report(dict(r,label='forged'),self.saved['id'],1)
        self.assertEqual(len(runs.list_runs(self.saved['id'])),1)
        self.assertEqual(runs.read(r['id'])['binding']['draft_revision'],1)

    def test_invalid_batch_is_atomic_and_rejects_nonfinite(self):
        with self.assertRaises(ValueError):runs.append(self.run['id'],[event(),event('bad',duration_ms=float('nan'))])
        self.assertEqual(runs.read(self.run['id'])['events'],[])
        with self.assertRaises(ValueError):runs.append(self.run['id'],[dict(event(),secret='no')])
        with self.assertRaises(ValueError):runs.append(self.run['id'],[dict(event(),attempt=True)])

    def test_native_parent_is_span_no_inferred_parts_and_failed_partial_trace(self):
        with capture(dict(run_id=self.run['id'],origin='standard'),self.root):pass
        s=runs.read(self.run['id'])['summary'];self.assertEqual(s['completed'],0)
        self.assertEqual(s['coarse_jobs_without_details'],1)
        raw=dict(event='operation_finished',operation='native.create',result={'status':'passed'},occurrence_id='handle/1',duration_ms=9)
        (self.root/'native_progress.jsonl').write_text(json.dumps(raw)+'\n',encoding='utf-8')
        with self.assertRaises(RuntimeError):
            with capture(dict(run_id=self.run['id'],origin='unknown'),self.root):raise RuntimeError('CAD failed')
        s=runs.read(self.run['id'])['summary'];self.assertEqual(s['completed'],1)
        self.assertEqual(s['by_origin']['unknown'],1);self.assertEqual(s['operations'][0]['occurrence_id'],'handle/1')

    def test_trace_problems_never_change_the_job_outcome(self):
        p=self.root/'native_progress.jsonl'
        raw=json.dumps(dict(event='operation_finished',operation='native.create',result={'status':'passed'}))
        p.write_text(raw,encoding='utf-8')  # missing final newline
        with redirect_stderr(io.StringIO()):
            with capture(dict(run_id=self.run['id'],origin='standard'),self.root):done=True
        self.assertTrue(done)
        spans=runs.read(self.run['id'])['summary']['spans']
        self.assertEqual(sorted(s['status'] for s in spans),['failed','success'])
        self.assertIn('Niepełny ślad natywny',[s for s in spans if s['status']=='failed'][0]['reason'])
        p.write_text('not json\n',encoding='utf-8')
        with redirect_stderr(io.StringIO()),self.assertRaises(RuntimeError) as caught:
            with capture(dict(run_id=self.run['id'],origin='standard'),self.root):raise RuntimeError('Native job failed')
        self.assertEqual(str(caught.exception),'Native job failed')
        self.assertIn('JSONDecodeError',caught.exception.__notes__[0])
        other=runs.create(self.saved['id'],1,'Zamknięty w trakcie')
        with redirect_stderr(io.StringIO()):
            with capture(dict(run_id=other['id'],origin='standard'),self.root/'missing'):
                runs.append(other['id'],state='partial')
        self.assertEqual(runs.read(other['id'])['state'],'partial')

    def test_native_trace_reimport_deduplicates_and_truncation_rejected(self):
        raw=dict(event='operation_finished',operation='native.create',result={'status':'passed'})
        p=self.root/'native_progress.jsonl';p.write_text(json.dumps(raw)+'\n',encoding='utf-8')
        import_native_progress(self.run['id'],self.root,{},'job/x')
        import_native_progress(self.run['id'],self.root,{},'job/x')
        self.assertEqual(runs.read(self.run['id'])['summary']['completed'],1)
        p.write_text(json.dumps(raw),encoding='utf-8')
        with self.assertRaises(ValueError):import_native_progress(self.run['id'],self.root,{},'job/y')

    def test_occurrence_mapping_is_explicit(self):
        raw=dict(event='operation_finished',operation='native.create',result={'status':'passed'},occurrence_id='cad/123')
        (self.root/'native_progress.jsonl').write_text(json.dumps(raw)+'\n',encoding='utf-8')
        import_native_progress(self.run['id'],self.root,{'occurrence_map':{'cad/123':'carry:left:0'}},'job/map')
        self.assertEqual(runs.read(self.run['id'])['summary']['operations'][0]['occurrence_id'],'carry:left:0')

    def test_simulation_explicit_and_draft_unchanged(self):
        before=configurator.read_draft(self.saved['id'])
        demo=runs.create(self.saved['id'],1,'Przykład','simulation')
        self.assertEqual(demo['mode'],'simulation')
        self.assertEqual(configurator.read_draft(self.saved['id']),before)

    def test_unfinished_span_and_failed_intervention_block_completion(self):
        runs.append(self.run['id'],[dict(event(),kind='span',status='running')])
        with self.assertRaises(ValueError):runs.append(self.run['id'],state='completed')
        other=runs.create(self.saved['id'],1,'Błąd interwencji')
        runs.append(other['id'],[dict(intervention(),status='failed')])
        with self.assertRaises(ValueError):runs.append(other['id'],state='completed')

    def test_http_read_and_origin_guard(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler({}, {}, 'process-test'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
            conn.request('GET','/process-test/process/run/'+self.run['id'])
            response=conn.getresponse();self.assertEqual(response.status,200)
            self.assertEqual(json.loads(response.read())['binding']['draft_id'],self.saved['id'])
            payload=json.dumps(dict(action='append',run_id=self.run['id'],events=[event()]))
            conn.request('POST','/process-test/process',payload,{'Origin':'https://other.example','X-RockPro-Session':'process-test'})
            response=conn.getresponse();self.assertEqual(response.status,403);response.read()
            headers={'Origin':f'http://127.0.0.1:{server.server_port}','X-RockPro-Session':'process-test'}
            conn.request('POST','/process-test/process',payload,headers)
            response=conn.getresponse();self.assertEqual(response.status,200)
            self.assertEqual(json.loads(response.read())['summary']['completed'],1)
            for body in ('[]','"append"'):
                conn.request('POST','/process-test/process',body,headers)
                response=conn.getresponse();self.assertEqual(response.status,400);response.read()
            conn.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
