"""Native facade and CLI exercised with a synthetic, getter-only adapter."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parts import __main__ as cli
from parts import native
from parts.native import (NativePartsAdapter, SourceMismatchError, file_sha256,
                          inspect_source, same_document_path)
from test_parts_reader import FixtureAdapter, part


class NativeFixture(FixtureAdapter):
    def __init__(self, source, children=None):
        super().__init__([part()] if children is None else children)
        self.source = str(source)
        self.modified = False
        self.provenance_calls = 0

    def provenance(self):
        self.provenance_calls += 1
        return dict(document_path=self.source, modified=self.modified,
                    file_guid="fixture-guid", connection="fixture_getters_only")


class NativeFacadeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "fixture.ics"
        self.source.write_bytes(b"synthetic fixture bytes, not a CAD document")

    def run_cli(self, *extra, factory=NativeFixture):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(["--source", str(self.source), "--log-dir", str(self.folder / "logs"), *extra],
                            adapter_factory=factory)
        return code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_hash_identity_and_read_only_result_are_separate(self):
        before = self.source.read_bytes()
        adapter = NativeFixture(self.source)
        result = inspect_source(self.source, adapter_factory=lambda _: adapter)
        self.assertEqual(result["status"], "complete")
        self.assertFalse(result["partial"])
        self.assertTrue(result["source"]["unchanged"])
        self.assertEqual(result["source"]["sha256_before"], hashlib.sha256(before).hexdigest())
        self.assertEqual(result["source"]["sha256_after"], file_sha256(self.source))
        self.assertEqual(result["cad_document"]["disk_equivalence"], "not_proven")
        self.assertEqual(adapter.provenance_calls, 2)
        self.assertEqual(self.source.read_bytes(), before)

    def test_reader_code_fingerprint_is_deterministic_and_sensitive_to_runtime_code(self):
        package = self.folder / "package"
        package.mkdir()
        (package / "reader.py").write_bytes(b"fixture reader v1\n")
        (package / "operation_log.py").write_bytes(b"fixture logger v1\n")
        first = cli.reader_code_sha256(package)
        self.assertEqual(len(first), 64)
        self.assertEqual(first, cli.reader_code_sha256(package))
        (package / "test_reader.py").write_bytes(b"fixture test excluded\n")
        (package / "inventory.json").write_bytes(b"fixture local report excluded\n")
        self.assertEqual(first, cli.reader_code_sha256(package))
        (package / "reader.py").write_bytes(b"fixture reader v2\n")
        self.assertNotEqual(first, cli.reader_code_sha256(package))

    def test_full_windows_path_comparison_and_native_mismatch_guard(self):
        self.assertTrue(same_document_path(r"C:\fixture\A.ics", r"c:/fixture/a.ics"))
        self.assertFalse(same_document_path(r"C:\fixture\A.ics", r"D:\fixture\A.ics"))
        self.assertFalse(same_document_path("A.ics", r"C:\fixture\A.ics"))
        document = SimpleNamespace(Name=r"D:\other\fixture.ics", Modified=False, FileGUID="fixture")
        adapter = NativePartsAdapter(None, None, document, None, r"C:\expected\fixture.ics")
        with self.assertRaises(SourceMismatchError):
            adapter.provenance()
        result = inspect_source(self.source, adapter_factory=lambda _: adapter)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["rows"], [])
        self.assertTrue(result["source"]["unchanged"])
        self.assertEqual(result["errors"][0]["type"], "SourceMismatchError")

    def test_modified_live_document_is_partial_even_if_disk_unchanged(self):
        adapter = NativeFixture(self.source)
        adapter.modified = True
        result = inspect_source(self.source, adapter_factory=lambda _: adapter)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["source"]["unchanged"])
        self.assertEqual(result["errors"][-1]["type"], "UnsavedOrChangedDocument")
        self.assertEqual(result["summary"]["error_count"], 1)

    def test_disk_change_and_failed_attachment_are_honest(self):
        def failed_attachment(source):
            raise RuntimeError("synthetic attach failure")
        result = inspect_source(self.source, adapter_factory=failed_attachment)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["source"]["unchanged"])
        class ExternalFileChange(NativeFixture):
            def root(inner):
                # Deliberately simulate another actor changing fixture disk bytes.
                self.source.write_bytes(b"changed externally by fixture")
                return super().root()
        result = inspect_source(self.source, adapter_factory=ExternalFileChange)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["source"]["unchanged"])
        self.assertNotEqual(result["source"]["sha256_before"], result["source"]["sha256_after"])
        self.assertEqual(result["errors"][-1]["type"], "SourceChangedError")

    def test_postread_identity_or_provenance_failure_is_failed_with_rows_retained(self):
        for changed_field in ("document_path", "file_guid", "exception"):
            with self.subTest(changed_field=changed_field):
                class ChangedProvenance(NativeFixture):
                    def provenance(inner):
                        value = super().provenance()
                        if inner.provenance_calls == 2:
                            if changed_field == "exception":
                                raise RuntimeError("fixture disconnected after read")
                            value[changed_field] = "fixture-changed"
                        return value
                result = inspect_source(self.source, adapter_factory=ChangedProvenance)
                self.assertEqual(result["status"], "failed")
                self.assertTrue(result["partial"])
                self.assertEqual(len(result["rows"]), 2)
                self.assertTrue(result["source"]["unchanged"])
                self.assertTrue(result["errors"])

    def test_unavailable_after_hash_fails_even_when_rows_were_read(self):
        digest = file_sha256(self.source)
        with patch.object(native, "file_sha256", side_effect=[digest, OSError("fixture unavailable")]):
            result = inspect_source(self.source, adapter_factory=NativeFixture)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["partial"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertIsNone(result["source"]["sha256_after"])
        self.assertFalse(result["source"]["unchanged"])

    def test_cli_report_hash_and_jsonl_privacy(self):
        output = self.folder / "inventory.json"
        before = self.source.read_bytes()
        code, result, stderr = self.run_cli("--output", str(output))
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.source.read_bytes(), before)
        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(saved["rows"], result["rows"])
        self.assertEqual(saved["operation_log_status"], "pending_finalization")
        self.assertEqual(result["operation_log_status"], "finished")
        log_text = Path(result["operation_log"]).read_text()
        events = [json.loads(line) for line in log_text.splitlines()]
        self.assertNotIn("fixture.ics", log_text)
        self.assertNotIn(str(self.folder), log_text)
        self.assertNotIn("fixture plate", log_text)
        self.assertEqual(events[-1]["result"]["status"], "complete")
        self.assertEqual(events[-1]["refs"]["inventory_sha256"], file_sha256(output))
        self.assertEqual(events[-1]["refs"]["source_sha256"], file_sha256(self.source))
        self.assertEqual(events[0]["refs"]["code_sha256"], result["reader_code_sha256"])
        self.assertEqual(result["reader_code_sha256"], cli.reader_code_sha256())
        self.assertIsNone(events[-1]["model"])
        self.assertEqual(events[-1]["actor"], "deterministic-reader")

    def test_cli_rejects_collisions_and_invalid_limits_before_cad(self):
        output = self.folder / "existing.json"
        output.write_text("fixture-preserved", encoding="utf-8")
        for args in (("--output", str(self.source)), ("--output", str(output)),
                     ("--output", str(self.folder / "bad.txt")), ("--max-nodes", "0"),
                     ("--max-seconds", "nan")):
            calls = []
            with self.subTest(args=args):
                code, result, _ = self.run_cli(*args, factory=lambda source: calls.append(source))
                self.assertEqual(code, 1)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(calls, [])
        self.assertEqual(output.read_text(encoding="utf-8"), "fixture-preserved")

    def test_cli_partial_failure_and_log_io_failure_exit_codes(self):
        code, result, _ = self.run_cli("--max-nodes", "1")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "partial")
        class FailedRoot(NativeFixture):
            def root(self):
                raise RuntimeError("synthetic error with private fixture name")
        code, result, _ = self.run_cli(factory=FailedRoot)
        self.assertEqual(code, 1)
        events = [json.loads(line) for line in Path(result["operation_log"]).read_text().splitlines()]
        self.assertEqual(events[-1]["result"]["status"], "failed")
        with patch.object(cli.OperationLogger, "record", side_effect=OSError("synthetic log I/O failure")):
            code, result, _ = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(e["field"] == "operation_log" for e in result["errors"]))

    def test_saved_report_never_claims_finalized_log_when_final_log_write_fails(self):
        output = self.folder / "inventory.json"
        with patch.object(cli.OperationLogger, "finish", side_effect=OSError("fixture final log failure")):
            code, result, _ = self.run_cli("--output", str(output))
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["operation_log_status"], "failed")
        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(saved["operation_log_status"], "pending_finalization")


if __name__ == "__main__":
    unittest.main()
