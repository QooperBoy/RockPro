import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import unittest
import project_store as store
import layout
import server
import test_projects


class CardStageVersions(unittest.TestCase):
    setUp=test_projects.ProjectStoreTests.setUp
    tearDown=test_projects.ProjectStoreTests.tearDown
    create=test_projects.ProjectStoreTests.create
    def test_two_card_writers_one_wins(self):
        p=self.create();barrier=threading.Barrier(2)
        def write(name):
            barrier.wait()
            try:return store.save_project(name,project_id=p['id'],expected_revision=1,actor=name)
            except store.RevisionConflict as exc:return exc.details
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(write,['UI','AI']))
        self.assertEqual(sum('project' in r for r in results),1)
        self.assertEqual(sum(r.get('code')=='PROJECT_CONFLICT' for r in results),1)
        current=store.get_project(p['id'])['project']
        self.assertEqual(current['revision'],2)
        self.assertEqual(len(store.get_history(p['id'])['events']),2)

    def test_stage_conflict_atomic_and_independent_revisions(self):
        p=self.create();pid=p['id'];barrier=threading.Barrier(2)
        def write(note):
            barrier.wait()
            try:return store.set_stage(pid,'geometry','review',note,expected_revision=1,actor=note)
            except store.RevisionConflict as exc:return exc.details
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(write,['UI','AI']))
        self.assertEqual(sum(r.get('code')=='STAGE_CONFLICT' for r in results),1)
        before=store.get_history(pid)
        with self.assertRaises(store.RevisionConflict):store.set_stage(pid,'geometry','approved',expected_revision=1)
        self.assertEqual(store.get_history(pid),before)
        p=store.set_stage(pid,'hardware','waiting',expected_revision=1)['project']
        self.assertEqual(p['revision'],1)
        self.assertEqual(next(s for s in p['stages'] if s['key']=='hardware')['revision'],2)

    def test_invalidations_are_versioned_and_audited(self):
        p=self.create();pid=p['id']
        layout.save_layout(pid,{},0,actor='AI',change_source='mcp')
        with self.assertRaises(store.RevisionConflict):store.set_stage(pid,'geometry','approved',expected_revision=1)
        p=store.save_project('Test',project_id=pid,quantity=8,device='New',expected_revision=1,actor='UI')['project']
        stages={s['key']:s for s in p['stages']}
        self.assertEqual(stages['materials']['revision'],3) # overlapping reasons only increment once
        self.assertEqual(stages['inquiry']['revision'],1)
        events=store.get_history(pid)['events']
        stage_events=[e['payload'] for e in events if e['kind']=='stage_changed']
        self.assertTrue(any(e['reason']=='layout_saved' and e['actor']=='AI' for e in stage_events))
        self.assertTrue(all(e['after']['revision']==e['before']['revision']+1 for e in stage_events))
        self.assertTrue(all(e['identity_verified'] is False for e in stage_events))

    def test_invalid_audit_rolls_back_data(self):
        p=self.create()
        with self.assertRaises(ValueError):store.save_project('Changed',project_id=p['id'],quantity=9,expected_revision=1,actor=123)
        self.assertEqual(store.get_project(p['id'])['project'],p)
        self.assertEqual(len(store.get_history(p['id'])['events']),1)

    def test_snapshot_advancement_rejects_stale_card(self):
        p=self.create();working=self.root/'revision.ics';working.write_bytes(b'fixture')
        report=dict(copy=str(working),source=str(self.source),passed=True,source_unchanged=True,after_reopen=dict(measurements=dict(parameters_mm={})))
        result=store.register_snapshot(p['id'],report,'test',advance=True)
        self.assertEqual(result['project']['revision'],2)
        with self.assertRaises(store.RevisionConflict):store.save_project('Old',project_id=p['id'],source=p['source'],expected_revision=1)
        self.assertEqual(store.get_project(p['id'])['project']['source'],str(working))
        self.assertTrue(any(e['payload'].get('reason')=='cad_source_advanced' for e in store.get_history(p['id'])['events']))

    def test_pagination_and_mcp_conflict(self):
        p=self.create();pid=p['id']
        store.save_project('Two',project_id=pid,expected_revision=1)
        first=store.get_history(pid,limit=1);second=store.get_history(pid,limit=1,before_id=first['next_before_id'])
        self.assertGreater(first['events'][0]['id'],second['events'][0]['id'])
        self.assertIsNone(second['next_before_id'])
        request=dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='save_project',arguments=dict(project_id=pid,name='Old',expected_revision=1)))
        response=server.handle(request)['result'];self.assertTrue(response['isError'])
        details=json.loads(response['content'][0]['text'])
        self.assertEqual(details['code'],'PROJECT_CONFLICT');self.assertEqual(details['current']['name'],'Two')
        with self.assertRaises(ValueError):store.save_project('No version',project_id=pid)
        with self.assertRaises(ValueError):store.set_stage(pid,'geometry','draft')
        self.assertEqual(store.get_project(pid)['project']['revision'],2)

    def test_legacy_database_migration(self):
        # Real pre-revision schema; reopen twice, retain rows/history.
        with sqlite3.connect(store.DB_PATH) as conn:
            conn.executescript('''CREATE TABLE projects(id TEXT PRIMARY KEY,name TEXT,client TEXT,device TEXT,quantity INTEGER,notes TEXT,source TEXT,created_at TEXT,updated_at TEXT);
CREATE TABLE stages(project_id TEXT,key TEXT,label TEXT,status TEXT,note TEXT,updated_at TEXT,PRIMARY KEY(project_id,key));''')
            conn.execute('INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)',('legacy','Old','','',1,'',str(self.source),'then','then'))
            conn.executemany('INSERT INTO stages VALUES (?,?,?,?,?,?)',[('legacy',k,l,'draft','','then') for k,l in store.STAGES])
        conn.close()
        for _ in range(2):
            p=store.get_project('legacy')['project'];self.assertEqual(p['revision'],1)
            self.assertTrue(all(s['revision']==1 for s in p['stages']))
        self.assertEqual(store.save_project('New',project_id='legacy',expected_revision=1)['project']['revision'],2)

if __name__=='__main__':unittest.main()
