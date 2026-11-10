import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rockpro_cad import configurator,part_preferences as prefs
from rockpro_cad.mcp import project_store
from rockpro_cad.mcp.test_configurator import concept


class PartPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.patch=patch.object(project_store,'DB_PATH',Path(self.temp.name)/'isolated.sqlite3');self.patch.start();self.addCleanup(self.patch.stop)
        self.known={'H7159','company-'+'a'*24}
    def test_favorite_persists_and_repeated_request_is_idempotent(self):
        command=dict(part_id='H7159',favorite=True)
        a=prefs.set_favorite(command,self.known);b=prefs.set_favorite(command,self.known)
        self.assertEqual(a,b);self.assertTrue(prefs.read(self.known)['items']['H7159']['favorite'])
        prefs.set_favorite(dict(command,favorite=False),self.known)
        self.assertFalse(prefs.read(self.known)['items']['H7159']['favorite'])
    def test_counts_projects_not_revisions_or_reads_and_retains_history(self):
        d=concept();d['hardware']=[dict(part_id='H7159',revision=1)]
        a=configurator.save_draft(d)
        for _ in range(3):a=configurator.save_draft(d,a['id'],a['revision'])
        removed=copy.deepcopy(d);removed['hardware']=[]
        configurator.save_draft(removed,a['id'],a['revision'])
        for _ in range(3):self.assertEqual(prefs.read(self.known)['items']['H7159']['project_count'],1)
        configurator.save_draft(d)
        self.assertEqual(prefs.read(self.known)['items']['H7159']['project_count'],2)
        stat=prefs.set_favorite(dict(part_id='H7159',favorite=True),self.known)['items']['H7159']
        self.assertEqual(stat['project_count'],2)
    def test_company_preference_does_not_create_project_usage_or_alias(self):
        company='company-'+'a'*24
        r=prefs.set_favorite(dict(part_id=company,favorite=True),self.known)
        self.assertEqual(r['items'][company]['project_count'],0)
        self.assertNotIn('H7159',r['items'])
    def test_invalid_writes_are_refused_and_catalogue_removal_keeps_preference(self):
        for command in [dict(part_id='unknown',favorite=True),dict(part_id='H7159',favorite=1),dict(part_id='H7159',favorite=True,extra=1)]:
            with self.assertRaises(ValueError):prefs.set_favorite(command,self.known)
        prefs.set_favorite(dict(part_id='H7159',favorite=True),self.known)
        self.assertEqual(prefs.read(set())['items'],{})
        self.assertTrue(prefs.read(self.known)['items']['H7159']['favorite'])
    def test_preferences_do_not_modify_project_or_stock_tables(self):
        saved=configurator.save_draft(concept())
        with project_store.db() as conn:before=[tuple(r) for r in conn.execute('SELECT * FROM configurator_draft_versions')]
        prefs.set_favorite(dict(part_id='H7159',favorite=True),self.known)
        self.assertEqual(configurator.read_draft(saved['id']),saved)
        with project_store.db() as conn:
            self.assertEqual([tuple(r) for r in conn.execute('SELECT * FROM configurator_draft_versions')],before)
            self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='inventory_journal'").fetchone())


if __name__=='__main__':unittest.main()
