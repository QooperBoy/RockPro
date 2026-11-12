import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rockpro_cad import configurator, process_runs as runs, phoenix_export
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept
from rockpro_cad.mcp.test_process_runs import event, intervention


class PhoenixExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        p=patch.object(project_store,'DB_PATH',self.root/'projects.sqlite3');p.start();self.addCleanup(p.stop)
        self.saved=configurator.save_draft(concept())
        self.run=runs.create(self.saved['id'],1,'Eksport')

    def spans(self):
        return phoenix_export.run_spans(runs.read(self.run['id']))

    def test_run_maps_origins_jobs_and_parenting_without_touching_registry(self):
        job=dict(event('job/a',duration_ms=50),kind='span',status='running')
        events=[intervention(),job,
                dict(event('job/a/line/0',duration_ms=5)),
                dict(event('job/a/line/1',duration_ms=5),origin='ai',intervention_id='new-vent'),
                dict(job,event_id='job-a-end',status='success'),
                dict(event('loose',duration_ms=1),status='failed')]
        runs.append(self.run['id'],events)
        before=runs.read(self.run['id'])
        spans=self.spans()
        self.assertEqual(runs.read(self.run['id']),before)
        root=spans[0];self.assertIsNone(root['parent_id'])
        self.assertEqual(root['attributes']['rockpro.ops.ai'],1)
        self.assertEqual(root['attributes']['rockpro.ops.standard'],1)
        self.assertEqual(root['attributes']['rockpro.jobs.standard'],1)
        self.assertEqual(root['attributes']['rockpro.ops.failed'],1)
        by_op={s['attributes'].get('rockpro.operation_id'):s for s in spans[1:]}
        self.assertEqual(by_op['job/a']['status'],'OK')
        self.assertEqual(by_op['job/a/line/1']['parent_id'],by_op['job/a']['span_id'])
        self.assertEqual(by_op['loose']['parent_id'],root['span_id'])
        self.assertEqual(by_op['loose']['status'],'ERROR')
        self.assertEqual(by_op['new-vent']['kind'],'AGENT')
        self.assertIn('Brak mapy',by_op['new-vent']['attributes']['input.value'])
        self.assertEqual(len({s['span_id'] for s in spans}),len(spans))
        self.assertTrue(all(s['trace_id']==root['trace_id'] for s in spans))
        self.assertEqual(spans,self.spans())  # deterministic IDs: re-export is idempotent

    def test_retry_attempts_are_separate_spans_and_attributes_are_scalars(self):
        a=dict(event(),status='running');b=dict(a,event_id='finish',status='failed',duration_ms=1)
        c=dict(b,event_id='retry',attempt=2,status='success',duration_ms=3)
        runs.append(self.run['id'],[a,b,c])
        ops=[s for s in self.spans() if s['attributes'].get('rockpro.operation_id')=='op']
        self.assertEqual(sorted(s['attributes']['rockpro.attempt'] for s in ops),[1,2])
        for s in self.spans():
            for value in s['attributes'].values():
                self.assertIsInstance(value,(str,int,float,bool))
            self.assertLessEqual(s['start'],s['end'])

    def test_producer_timestamps_cannot_stretch_the_run(self):
        runs.append(self.run['id'],[dict(intervention(),timestamp_utc='2001-01-01T00:00:00+00:00'),
                                    dict(event(),timestamp_utc='not a time')])
        report=runs.read(self.run['id']);root=phoenix_export.run_spans(report)[0]
        self.assertEqual((root['start'],root['end']),(report['created_at'],report['updated_at']))
        self.assertEqual(root['attributes']['rockpro.events_outside_run_window'],1)

    def test_agent_log_becomes_session_with_tool_children(self):
        rows=[dict(run_id='r1',timestamp_utc='2026-11-10T10:00:01+00:00',tool='preview_layout',result={'status':'passed'},
                   duration_ms=10,tool_calls=1,client='claude-code/2.1.0',prompt_version='proposal-only-v2'),
              dict(run_id='r1',timestamp_utc='2026-11-10T10:00:02+00:00',tool='denied',result={'status':'limited'},
                   duration_ms=0,tool_calls=2,error_code='AGENT_TOOL_DENIED')]
        path=self.root/'r1.jsonl';path.write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf-8')
        spans=phoenix_export.agent_spans(phoenix_export.read_agent_log(path),'r1')
        self.assertEqual(spans[0]['kind'],'AGENT');self.assertEqual(spans[0]['name'],'Agent session (claude-code/2.1.0)')
        self.assertEqual(spans[0]['attributes']['rockpro.agent.refused_calls'],1)
        self.assertEqual([s['parent_id'] for s in spans[1:]],[spans[0]['span_id']]*2)
        self.assertEqual(spans[2]['attributes']['rockpro.error_code'],'AGENT_TOOL_DENIED')

    def test_blocked_tool_result_is_an_error_span_and_counted(self):
        rows=[dict(run_id='r2',timestamp_utc='2026-11-12T10:00:54+00:00',tool='preview_case',result={'status':'blocked'},
                   duration_ms=3,tool_calls=1,error_code='AGENT_TOOL_BLOCKED',tool_status='blocked',
                   diagnostic_codes=['FIELD_REQUIRED'])]
        spans=phoenix_export.agent_spans(rows,'r2')
        self.assertEqual(spans[1]['status'],'ERROR')
        self.assertEqual(spans[1]['attributes']['rockpro.diagnostic_codes'],'FIELD_REQUIRED')
        self.assertEqual(spans[0]['attributes']['rockpro.agent.blocked_calls'],1)


if __name__=='__main__':unittest.main()
