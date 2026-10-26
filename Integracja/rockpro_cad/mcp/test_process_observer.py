from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3
import tempfile
import unittest
from rockpro_cad.process_observer import read_trace, read_journal, read_lines, valid_elements, visible_elements, stage_state, summarize_events
from rockpro_cad.core_case.trace import PhaseTrace
from rockpro_cad.core_case.native import preflight_plan
from rockpro_cad.core_case.test_native import fixture


class ProcessObserverTests(unittest.TestCase):
    def test_actual_phase_durations_failures_and_preview_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); trace=PhaseTrace(root,preflight_plan(fixture()),'probe')
            with trace.phase('capture'):pass
            with self.assertRaisesRegex(ValueError,'intentional'):
                with trace.phase('create'):raise ValueError('intentional')
            rows,elements,notes=read_trace(trace.logger.path)
            self.assertEqual(len(elements),1);self.assertFalse(notes)
            self.assertEqual(rows[-1]['result']['status'],'failed')
            self.assertGreaterEqual(rows[-1]['duration_ms'],0)
            self.assertEqual(visible_elements(rows,elements),[])
            self.assertIsNone(rows[-1]['model']);self.assertIsNone(rows[-1]['tokens'])
            (root/'process_preview.json').write_text('{}')
            self.assertEqual(read_trace(trace.logger.path)[1],[])
            self.assertTrue(read_trace(trace.logger.path)[2])

    def test_partial_and_truncated_log_are_not_silent_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.jsonl'
            path.write_bytes(b'{"event":"logging_limit_reached"}\n{"unfinished":')
            rows,notes=read_lines(path)
            self.assertEqual(len(rows),1);self.assertEqual(len(notes),2)

    def test_readonly_database_does_not_create_migrate_or_modify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data.sqlite3'
            with self.assertRaises(FileNotFoundError):read_journal(path)
            self.assertFalse(path.exists())
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('CREATE TABLE unrelated(value TEXT)')
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(read_journal(path),[])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
            with closing(sqlite3.connect(path)) as conn:
                self.assertEqual(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('unrelated',)])

    def test_preview_only_reveals_confirmed_created_ids(self):
        elements=preflight_plan(fixture())
        rows=[{'operation':'native.create','occurrence_id':'handle/1','result':{'status':'passed'}}]
        self.assertEqual(visible_elements(rows,[{'id':'handle/1'}]),[{'id':'handle/1'}])
        with self.assertRaises(ValueError):valid_elements({'kind':'rockpro_process_preview','units':'mm','elements':[{'id':'bad','bounds':[0,0,0,float('nan'),1,1]}]})

    def test_coarse_success_does_not_hide_missing_or_failed_parts(self):
        elements=[{'id':'handle/1'},{'id':'handle/2'},{'id':'handle/3'}]
        rows=[{'operation':'case.create','result':{'status':'passed'}},
              {'operation':'native.create','occurrence_id':'handle/1','result':{'status':'passed'}},
              {'operation':'native.create','occurrence_id':'handle/2','result':{'status':'failed'}}]
        self.assertEqual(visible_elements(rows,elements),elements[:1])
        rows.append({'operation':'native.create','occurrence_id':'handle/1','result':{'status':'unknown'}})
        self.assertEqual(visible_elements(rows,elements),[])
        self.assertEqual(visible_elements(rows[:1],elements),elements)

    def test_sibling_native_log_must_match_operation_and_preview_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);trace=PhaseTrace(root,preflight_plan(fixture()),'one-operation')
            with trace.phase('create'):pass
            element=json.loads((root/'process_preview.json').read_bytes())['elements'][0]
            row={'event':'operation_finished','operation':'native.create',
                 'occurrence_id':element['id'],'result':{'status':'passed'}}
            progress=root/'native_progress.jsonl'
            def check(expected):
                progress.write_text(json.dumps(row)+'\n',encoding='utf-8')
                rows,elements,notes=read_trace(trace.logger.path)
                self.assertEqual(len(visible_elements(rows,elements)),int(expected))
                self.assertEqual(bool(notes),not expected)
            check(False)  # Same directory alone does not bind a CAD event.
            row['operation_id']='other-operation';row['refs']={'inventory_sha256':trace.digest}
            check(False)
            row['operation_id']='one-operation';check(True)
            row['refs']['inventory_sha256']='0'*64;check(False)

    def test_unrelated_coarse_success_and_null_timestamp_are_not_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);trace=PhaseTrace(root,preflight_plan(fixture()),'operation')
            with self.assertRaises(ValueError):
                with trace.phase('create'):raise ValueError('failure')
            foreign=dict(event='operation_finished',operation='case.create',run_id='foreign',
                         timestamp_utc=None,result={'status':'passed'})
            with trace.logger.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(foreign)+'\n')
            rows,elements,notes=read_trace(trace.logger.path)
            self.assertEqual(visible_elements(rows,elements),[])
            self.assertTrue(any('case.*' in note for note in notes))
            self.assertEqual(summarize_events(rows)['invalid_timestamp_count'],1)

    def test_stage_does_not_erase_failure_or_unfinished_operation(self):
        def event(status):return dict(event='operation_finished',operation='native.create',result={'status':status})
        rows=[event('failed'),event('passed')]
        self.assertEqual(stage_state(list(enumerate(rows)),1),'BŁĄD')
        rows=[event('partial'),event('passed')]
        self.assertEqual(stage_state(list(enumerate(rows)),1),'niepełny')
        rows=[dict(event='operation_started',operation='case.create'),event('passed')]
        self.assertEqual(stage_state(list(enumerate(rows)),1),'w toku')
        self.assertEqual(stage_state([(0,event('passed'))],-1),'oczekuje')
        self.assertEqual(stage_state([(0,event('passed'))],0),'OK')
        rows=[dict(event='operation_started',operation='case.create',operation_id='A'),
              dict(event='operation_finished',operation='case.create',operation_id='B',result={'status':'passed'})]
        self.assertEqual(stage_state(list(enumerate(rows)),1),'w toku')

    def test_metrics_keep_nested_durations_separate_and_authorship_unknown(self):
        rows=[dict(event='operation_started',operation='case.create',timestamp_utc='2026-10-26T10:00:00Z'),
              dict(event='operation_finished',operation='native.create',occurrence_id='handles/1',
                   timestamp_utc='2026-10-26T10:00:00.500Z',duration_ms=400,actor='script',result={'status':'passed'}),
              dict(event='operation_finished',operation='case.create',timestamp_utc='2026-10-26T10:00:01Z',
                   duration_ms=1000,actor='script',result={'status':'passed'})]
        report=summarize_events(rows)
        self.assertEqual(report['observed_window_ms'],1000)
        self.assertEqual([s['recorded_work_ms'] for s in report['stages']],[1000,400])
        self.assertEqual(report['finished_by_executor'],{'script':2})
        self.assertIsNone(report['automation_percent']);self.assertIsNone(report['agent_intervention_count'])
        self.assertIsNone(report['model_cost']);self.assertFalse(report['production_approved'])
        rows.append(dict(event='operation_finished',operation='agent.tool',actor='agent',
                         timestamp_utc='2026-10-26T11:00:00',duration_ms=float('nan')))
        report=summarize_events(rows)
        self.assertEqual(report['invalid_timestamp_count'],1)
        self.assertEqual(report['missing_or_invalid_duration_count'],1)
        self.assertEqual(report['observed_window_ms'],1000)  # Naive local times are not UTC.
        rows[-1]['duration_ms']=10**400
        self.assertEqual(summarize_events(rows)['missing_or_invalid_duration_count'],1)


class StageGroupingTests(unittest.TestCase):
    def test_nested_durations_are_preserved_not_summed(self):
        from rockpro_cad.process_observer import grouped_events
        rows=[{'operation':'case.create','duration_ms':100},
              {'operation':'native.create','occurrence_id':'plates-base/1','duration_ms':20},
              {'operation':'native.create','occurrence_id':'handles/1','duration_ms':30},
              {'operation':'unrecognized','duration_ms':10}]
        groups=grouped_events(rows)
        self.assertEqual([g[0] for g in groups],['sdk','plywood','handles','other'])
        self.assertEqual(sorted(i for *_,events in groups for i,r in events),list(range(4)))
        self.assertEqual(groups[0][3][0][1]['duration_ms'],100)

    def test_layer_server_only_serves_allowlisted_files(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        from urllib.error import HTTPError
        from rockpro_cad.layer_viewer import make_handler
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'geometry.bin').write_bytes(b'geometry')
            (root/'model.json').write_text(json.dumps({'kind':'ironcad_native_mesh','geometry_sha256':hashlib.sha256(b'geometry').hexdigest()}),encoding='utf-8')
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(root,'test'))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}'
                with urlopen(url+'/test/geometry.bin') as response:self.assertEqual(response.read(),b'geometry')
                for path in ['/model.json','/test/../model.json','/test/private.db']:
                    with self.assertRaises(HTTPError):urlopen(url+path)
            finally:server.shutdown();server.server_close();thread.join()
            (root/'geometry.bin').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):make_handler(root,'test')
