import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import project_store as store
import worker

class ProjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.temp.name)
        self.source=self.root/'test.ics';self.source.write_bytes(b'original')
        self.dbpatch=patch.object(store,'DB_PATH',self.root/'test.sqlite3');self.dbpatch.start()
        self.pathpatch=patch.object(worker,'source_path',side_effect=lambda source=None:Path(source) if source else self.source);self.pathpatch.start()
    def tearDown(self):
        self.dbpatch.stop();self.pathpatch.stop();self.temp.cleanup()
    def create(self): return store.save_project('Test',client='Client',device='Speaker',quantity=4)['project']
    def test_persistence_and_partial_update(self):
        p=self.create();updated=store.save_project('Renamed',project_id=p['id'],expected_revision=p['revision'])['project']
        self.assertEqual(updated['quantity'],4);self.assertEqual(updated['client'],'Client')
        self.assertEqual(store.list_projects()['projects'][0]['id'],p['id'])
        self.assertEqual(len(updated['stages']),9)
    def test_manual_status_and_bad_input(self):
        p=self.create()
        result=store.set_stage(p['id'],'geometry','approved','Reviewed by constructor',expected_revision=1)['project']
        stage=next(s for s in result['stages'] if s['key']=='geometry')
        self.assertEqual(stage['validation'],'manual')
        with self.assertRaises(ValueError):store.set_stage(p['id'],'geometry','validated')
        with self.assertRaises(ValueError):store.save_project('Bad',quantity=True)
    def test_metadata_invalidates_dependent_stages(self):
        p=self.create()
        for key in ("materials","production","layout"): store.set_stage(p["id"],key,"approved",expected_revision=1)
        changed=store.save_project("Test",project_id=p["id"],quantity=5,expected_revision=1)["project"]
        states={s["key"]:s["status"] for s in changed["stages"]}
        self.assertEqual(states["materials"],"outdated");self.assertEqual(states["layout"],"approved")
        changed=store.save_project("Test",project_id=p["id"],device="Other",expected_revision=2)["project"]
        self.assertEqual(next(s for s in changed["stages"] if s["key"]=="layout")["status"],"outdated")
        with self.assertRaises(ValueError):store.save_project("Archive",source=str(self.root/"snapshot.ics"))
    def test_source_pinned(self):
        p=self.create()
        with self.assertRaises(ValueError):store.pinned_source(p['id'],str(self.root/'other.ics'))
    def test_snapshot_archive_independent_and_detects_modification(self):
        p=self.create();store.set_stage(p['id'],'documentation','approved',expected_revision=1)
        working=self.root/'revision.ics';working.write_bytes(b'validated model')
        report={'copy':str(working),'source':str(self.source),'passed':True,'source_unchanged':True,
                'after_reopen':{'measurements':{'parameters_mm':{'RP_Length':100}}}}
        result=store.register_snapshot(p['id'],report,'Revision',advance=True)
        archive=Path(result['snapshot']['path'])
        self.assertNotEqual(archive,working)
        working.write_bytes(b'manual working edit')
        self.assertEqual(store.list_snapshots(p['id'])['snapshots'][0]['integrity'],'verified')
        archive.write_bytes(b'outside edit')
        self.assertEqual(store.list_snapshots(p['id'])['snapshots'][0]['integrity'],'modified')
        self.assertEqual(result['project']['source'],str(working))
        self.assertEqual(next(s for s in result['project']['stages'] if s['key']=='documentation')['status'],'outdated')
    def test_failed_snapshot_never_registered(self):
        p=self.create()
        with self.assertRaises(ValueError):store.register_snapshot(p['id'],{'passed':False},'bad')
        self.assertEqual(store.list_snapshots(p['id'])['snapshots'],[])
        self.assertEqual(store.get_project(p['id'])['project']['source'],str(self.source))

if __name__=='__main__': unittest.main()
