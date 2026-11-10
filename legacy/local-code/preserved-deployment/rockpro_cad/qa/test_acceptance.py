"""Independent DB acceptance tests; temporary files only, no CAD automation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
import project_store as store


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix="acceptance_tmp_")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.ics"
        self.source.write_bytes(b"test fixture - not a CAD document")
        self.dbpatch = patch.object(store, "DB_PATH", self.root / "projects.sqlite3")
        self.pathpatch = patch("worker.source_path", side_effect=lambda source=None: Path(source or self.source).resolve())
        self.dbpatch.start()
        self.pathpatch.start()

    def tearDown(self):
        self.pathpatch.stop()
        self.dbpatch.stop()
        self.temp.cleanup()

    def create(self, name="Alpha"):
        return store.save_project(name=name, client="RockPro", device="Epson", quantity=3,
                                  notes="wymagania", source=str(self.source))["project"]

    def test_card_persists_in_fresh_connections(self):
        p = self.create()
        reloaded = store.get_project(p["id"])["project"]
        self.assertEqual((reloaded["client"], reloaded["device"], reloaded["quantity"]),
                         ("RockPro", "Epson", 3))
        self.assertEqual(reloaded["source"], str(self.source))
        self.assertEqual(len(reloaded["stages"]), 9)

    def test_partial_metadata_update_preserves_omitted_fields(self):
        p = self.create()
        updated = store.save_project(project_id=p["id"], name="Renamed")["project"]
        self.assertEqual((updated["client"], updated["device"], updated["quantity"], updated["notes"]),
                         ("RockPro", "Epson", 3, "wymagania"))

    def test_stage_updates_are_project_scoped_and_manual(self):
        a, b = self.create("Alpha"), self.create("Beta")
        store.set_stage(a["id"], "geometry", "approved", "constructeur")
        aa = store.get_project(a["id"])["project"]["stages"]
        bb = store.get_project(b["id"])["project"]["stages"]
        self.assertEqual(next(x for x in aa if x["key"] == "geometry")["status"], "approved")
        self.assertEqual(next(x for x in bb if x["key"] == "geometry")["status"], "draft")
        self.assertTrue(all(x["validation"] == "manual" for x in aa))

    def test_failed_report_cannot_register_snapshot_or_advance_source(self):
        p = self.create()
        with self.assertRaises(ValueError):
            store.register_snapshot(p["id"], {"passed": False, "source_unchanged": True},
                                    "Failure", advance=True)
        updated = store.get_project(p["id"])["project"]
        self.assertEqual(updated["snapshots"], [])
        self.assertEqual(updated["source"], str(self.source))

    def test_mismatched_source_is_rejected(self):
        p = self.create()
        with self.assertRaises(ValueError):
            store.pinned_source(p["id"], str(self.root / "unrelated.ics"))

    def test_sql_content_is_data(self):
        p = self.create("Robert'); DROP TABLE projects; --")
        self.assertEqual(store.get_project(p["id"])["project"]["name"], p["name"])
        self.assertEqual(len(store.list_projects()["projects"]), 1)

    def test_archive_checksum_detects_later_changes_and_project_advance(self):
        p = self.create()
        working = self.root / "revision" / "working.ics"
        working.parent.mkdir()
        working.write_bytes(b"validated-worker-fixture")
        report = {"passed": True, "source_unchanged": True, "source": str(self.source),
                  "copy": str(working), "after_reopen": {"measurements": {"parameters_mm": {"RP_Length": 914}}}}
        result = store.register_snapshot(p["id"], report, "Revision A", advance=True)
        archive = Path(result["snapshot"]["path"])
        self.assertNotEqual(archive, working)
        self.assertEqual(result["project"]["source"], str(working))
        self.assertEqual(store.list_snapshots(p["id"])["snapshots"][0]["integrity"], "verified")
        working.write_bytes(b"manual edits to working copy")
        self.assertEqual(store.list_snapshots(p["id"])["snapshots"][0]["integrity"], "verified")
        archive.write_bytes(b"external archive edit")
        self.assertEqual(store.list_snapshots(p["id"])["snapshots"][0]["integrity"], "modified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
