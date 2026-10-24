from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3
import tempfile
import unittest
from rockpro_cad.process_observer import read_trace, read_journal, read_lines, valid_elements, visible_elements
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
