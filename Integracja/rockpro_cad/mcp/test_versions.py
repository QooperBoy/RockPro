import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import project_store as store
import layout
import worker
import server

class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.temp.name)
        self.dbpatch=patch.object(store,'DB_PATH',self.root/'test.sqlite3');self.dbpatch.start()
        self.source=self.root/'source.ics';self.source.write_bytes(b'original')
        with store.db() as c:
            c.execute('INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)',('p','test','','',1,'',str(self.source),'now','now'))
            c.executemany('INSERT INTO stages VALUES (?,?,?,?,?,?)',[('p',k,l,'approved','','now') for k,l in store.STAGES])
    def tearDown(self):
        self.dbpatch.stop();self.temp.cleanup()
    def test_legacy_migration_idempotent(self):
        spec=layout.calculate_layout(dict(count=3))['spec']
        with store.db() as c:
            c.execute('CREATE TABLE layouts(project_id TEXT PRIMARY KEY,spec TEXT,updated_at TEXT)')
            c.execute('INSERT INTO layouts VALUES (?,?,?)',('p',json.dumps(spec),'yesterday'))
        for _ in range(2):
            r=layout.get_layout('p');self.assertEqual(r['revision'],1);self.assertEqual(r['spec'],spec)
        second=layout.save_layout('p',dict(count=4),1)
        self.assertEqual(second['revision'],2)
        self.assertEqual(layout.get_layout('p',1)['spec'],spec)
    def test_two_simultaneous_clients_one_wins_no_lost_update(self):
        gate=threading.Barrier(2)
        def save(count):
            gate.wait()
            try:return layout.save_layout('p',dict(count=count),0)
            except ValueError as exc:return str(exc)
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(save,[3,4]))
        self.assertEqual(sum(isinstance(r,dict) for r in results),1)
        self.assertTrue(any(isinstance(r,str) and 'LAYOUT_CONFLICT' in r for r in results))
        with store.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM layout_versions').fetchone()[0],1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM events WHERE kind='layout_saved'").fetchone()[0],1)
    def test_stale_save_never_changes_stages_or_history(self):
        first=layout.save_layout('p',{},0)
        store.set_stage('p','geometry','approved')
        with self.assertRaisesRegex(ValueError,'LAYOUT_CONFLICT'):layout.save_layout('p',dict(count=9),0)
        self.assertEqual(layout.get_layout('p')['sha256'],first['sha256'])
        self.assertEqual(next(s for s in store.get_project('p')['project']['stages'] if s['key']=='geometry')['status'],'approved')
    def test_snapshot_keeps_pinned_spec_after_later_save(self):
        first=layout.save_layout('p',dict(count=3),0)
        copy=self.root/'revision.ics';copy.write_bytes(b'CAD fixture, not native validation')
        report=dict(copy=str(copy),source=str(self.source),passed=True,source_unchanged=True,after_reopen=dict(measurements=dict(parameters_mm=first['parameters'])))
        # Simulate another editor saving during the native operation.
        def native(*args):
            layout.save_layout('p',dict(count=5),1)
            return report
        with patch.object(worker,'source_path',side_effect=lambda source=None:Path(source)),patch.object(worker,'_change_dimensions_on_copy',side_effect=native):
            result=worker.change_dimensions_on_copy(first['parameters'],project_id='p',layout_revision=1)
        binding=store.list_snapshots('p')['snapshots'][0]['layout_binding']
        self.assertEqual(binding['revision'],1);self.assertEqual(binding['sha256'],first['sha256'])
        self.assertEqual(binding['spec']['count'],3)
        self.assertEqual(layout.get_layout('p')['spec']['count'],5)
        self.assertEqual(json.loads((self.root/'report.json').read_text(encoding='utf-8'))['layout_binding'],binding)
    def test_binding_mismatch_rejected_before_cad(self):
        first=layout.save_layout('p',{},0)
        with patch.object(worker,'source_path',side_effect=lambda source=None:Path(source)),patch.object(worker,'_change_dimensions_on_copy') as native:
            with self.assertRaisesRegex(ValueError,'do not match'):
                worker.change_dimensions_on_copy({'RP_Length':123},project_id='p',layout_revision=1)
            native.assert_not_called()
    def test_mcp_version_contract(self):
        r=server.handle(dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='save_layout',arguments=dict(project_id='p',spec={},expected_revision=0))))
        self.assertFalse(r['result'].get('isError',False))
        history=worker.dispatch('get_layout',dict(project_id='p',revision=1))
        self.assertEqual(history['revision'],1)
        for revision in [True,-1,1.2]:
            with self.assertRaises(ValueError):layout.save_layout('p',{},revision)
        with self.assertRaises(TypeError):worker.dispatch('save_layout',dict(project_id='p',spec={}))
        self.assertEqual(layout.get_layout('p')['revision'],1)

if __name__=='__main__':unittest.main()

