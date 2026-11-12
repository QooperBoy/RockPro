import contextlib
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch
from rockpro_cad import auto_run, configurator, process_runs as runs
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept
from rockpro_cad.mcp.test_process_runs import event

REPO = Path(__file__).resolve().parents[3]


class AutoRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'studio.sqlite'
        p = patch.object(project_store, 'DB_PATH', self.db); p.start(); self.addCleanup(p.stop)
        self.out = io.StringIO()

    def draft(self):
        return configurator.save_draft(concept())

    def run_with(self, body, **kwargs):
        with auto_run.recorded_run(self.db, 'Auto test', out=self.out, **kwargs) as run_id:
            body(run_id)
        return run_id

    def test_latest_draft_is_read_only_and_picks_the_newest_revision(self):
        self.assertIsNone(auto_run.latest_draft(self.db))
        self.assertFalse(self.db.exists())  # a missing database is never created
        sqlite3.connect(self.db).close()
        self.assertIsNone(auto_run.latest_draft(self.db))  # Studio never saved a draft here
        first = self.draft(); second = self.draft()
        self.assertEqual(auto_run.latest_draft(self.db), (second['id'], 1))
        self.assertNotEqual(first['id'], second['id'])

    def test_own_run_is_opened_and_closed_completed(self):
        self.draft()
        run_id = self.run_with(lambda r: runs.append(r, [event()]))
        report = runs.read(run_id)
        self.assertEqual((report['state'], report['label'], report['summary']['completed']), ('completed', 'Auto test', 1))
        self.assertIn('closed as completed', self.out.getvalue())

    def test_job_error_closes_the_run_failed_and_is_not_hidden(self):
        self.draft(); seen = []
        def boom(r):
            seen.append(r); runs.append(r, [dict(event(), status='running')]); raise RuntimeError('CAD job failed')
        with self.assertRaisesRegex(RuntimeError, 'CAD job failed'):
            self.run_with(boom)
        self.assertEqual(runs.read(seen[0])['state'], 'failed')

    def test_refused_completed_falls_back_to_partial(self):
        self.draft()
        run_id = self.run_with(lambda r: runs.append(r, [dict(event(), status='failed')]))
        self.assertEqual(runs.read(run_id)['state'], 'partial')
        self.assertIn('closing as partial', self.out.getvalue())

    def test_given_run_is_used_and_left_open(self):
        saved = self.draft(); run = runs.create(saved['id'], 1, 'Owned elsewhere')
        self.assertEqual(self.run_with(lambda r: runs.append(r, [event()]), run_id=run['id']), run['id'])
        self.assertEqual(runs.read(run['id'])['state'], 'running')
        self.assertEqual(len(runs.list_runs(saved['id'])), 1)  # no second run was opened

    def test_no_draft_is_a_clear_error_and_opens_nothing(self):
        with self.assertRaisesRegex(auto_run.NoDraft, '--no-record'):
            self.run_with(lambda r: None)

    def test_explicit_draft_revision_is_bound(self):
        a = self.draft(); self.draft()
        run_id = self.run_with(lambda r: None, draft=(a['id'], 1))
        self.assertEqual(runs.read(run_id)['binding']['draft_id'], a['id'])

    def test_recorded_decision_allows_an_ai_job_in_the_own_run(self):
        from rockpro_cad.process_capture import capture
        self.draft(); folder = Path(self.temp.name) / 'job'; folder.mkdir()
        def body(r):
            runs.append(r, [auto_run.decision_event('ai/resize-9mm', 'agent_session=x: preview_layout says 9')])
            with capture(dict(run_id=r, origin='ai', intervention_id='ai/resize-9mm'), folder):
                pass
        report = runs.read(self.run_with(body))
        self.assertEqual(report['state'], 'completed')
        self.assertEqual(report['summary']['interventions'], 1)
        self.assertEqual([e['origin'] for e in report['events'] if e['kind'] == 'span'], ['ai', 'ai'])

    def test_studio_database_default_and_override(self):
        with patch.dict('os.environ', {'ROCKPRO_STUDIO_DATABASE': ''}):
            self.assertEqual(auto_run.studio_database(), REPO / 'artifacts' / 'studio.sqlite')
        with patch.dict('os.environ', {'ROCKPRO_STUDIO_DATABASE': str(self.db)}):
            self.assertEqual(auto_run.studio_database(), self.db)


class ExporterWatchTests(unittest.TestCase):
    """scripts/export_to_phoenix.py in watch mode, without Phoenix (dry run)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name); self.db = root / 'studio.sqlite'
        p = patch.object(project_store, 'DB_PATH', self.db); p.start(); self.addCleanup(p.stop)
        spec = importlib.util.spec_from_file_location('export_to_phoenix', REPO / 'scripts' / 'export_to_phoenix.py')
        self.exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.exporter)
        self.args = types.SimpleNamespace(database=self.db, agent_dir=root / 'agent-runs', agent_idle=300,
                                          flush=False, dry_run=True, endpoint='unused')
        self.state = root / 'state.json'
        saved = configurator.save_draft(concept())
        self.run = runs.create(saved['id'], 1, 'Forgotten run')

    def once(self, seen=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.exporter.once(self.args, self.state, seen)
        return out.getvalue()

    def test_watch_mode_reports_a_waiting_run_once(self):
        seen = set()
        self.assertIn('waiting: run ' + self.run['id'], self.once(seen))
        self.assertEqual(self.once(seen), '')  # not repeated every 30 s, no 'nothing new'
        self.assertIn('waiting: run ' + self.run['id'], self.once())  # a one-off export still lists it every time
        runs.append(self.run['id'], state='failed')
        self.assertIn('"name": "Process run: Forgotten run"', self.once(seen))  # closed -> exported (dry run prints spans)

    def test_old_open_run_is_called_probably_abandoned(self):
        self.assertNotIn('probably abandoned', self.once())
        with patch.object(self.exporter, '_age_hours', return_value=30):
            self.assertIn(f'probably abandoned, close it with studio_process_run.py finish {self.run["id"]} failed', self.once())


if __name__ == '__main__':
    unittest.main()
