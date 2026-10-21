import json
import tempfile
import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parts.operation_log import OperationLogger, DEFAULT_LOG_DIR


class UnsafeObject:
    def __str__(self):
        raise AssertionError("A logging sanitizer must never stringify objects")

    __repr__ = __str__


class OperationLogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def records(self, logger):
        return [json.loads(line) for line in logger.path.read_text(encoding="utf-8").splitlines()]

    def test_schema_ids_utc_and_honest_unknown_model(self):
        logger = OperationLogger(self.folder, actor="deterministic-reader")
        before = datetime.now(timezone.utc)
        first = logger.record("operation_started", arguments={"max_nodes": 30, "read_only": True})
        logger.finish("partial", partial=True, error_count=2, duration_ms=12.5,
                      refs={"source_sha256": "a" * 64})
        records = self.records(logger)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], first)
        self.assertEqual(uuid.UUID(first["run_id"]), uuid.UUID(logger.run_id))
        self.assertNotEqual(records[0]["event_id"], records[1]["event_id"])
        self.assertIsNone(records[0]["parent_event_id"])
        self.assertEqual(records[1]["parent_event_id"], records[0]["event_id"])
        for record in records:
            uuid.UUID(record["event_id"])
            self.assertEqual(record["schema_version"], 1)
            self.assertTrue(record["logger_version"])
            self.assertEqual(record["actor"], "deterministic-reader")
            for field in ("model", "reasoning_effort", "tokens", "cost", "project_id",
                          "input_revision", "output_revision", "code_version",
                          "prompt_version", "rules_version"):
                self.assertIsNone(record[field])
            stamp = datetime.fromisoformat(record["timestamp_utc"].replace("Z", "+00:00"))
            self.assertGreaterEqual(stamp, before)
            self.assertEqual(stamp.utcoffset().total_seconds(), 0)
        self.assertEqual(records[1]["result"]["status"], "partial")
        self.assertEqual(records[1]["duration_ms"], 12.5)
        self.assertEqual(records[1]["refs"], {"source_sha256": "a" * 64})
        self.assertEqual(records[1]["document_id"], "a" * 64)

    def test_sanitizes_paths_names_geometry_and_errors_without_stringification(self):
        logger = OperationLogger(self.folder)
        private = "PRIVATE_CUSTOMER_C:\\design\\model.ics"
        hostile = UnsafeObject()
        logger.record("read_error", arguments={"path": private, "name": private,
                      "max_nodes": hostile, "max_depth": True, "max_seconds": float("nan"),
                      "node_count": 10 ** 500, "geometry": [private]},
                      result={"node_count": 3, "partial": True, "status": private,
                              "bbox_raw": private, "errors": [hostile]},
                      error=RuntimeError(private), duration_ms=float("inf"),
                      refs={"source_path": private, "inventory_sha256": "G" * 64,
                            "source_sha256": "F" * 64})
        value = self.records(logger)[0]
        self.assertEqual(value["arguments"], {})
        self.assertEqual(value["result"], {"node_count": 3, "partial": True})
        self.assertEqual(value["error"], {"type": "RuntimeError"})
        self.assertEqual(value["refs"], {"source_sha256": "f" * 64})
        self.assertIsNone(value["duration_ms"])
        self.assertNotIn("PRIVATE_CUSTOMER", logger.path.read_text())
        logger.record("read_error", arguments=hostile, result=hostile, error=hostile, refs=hostile)
        self.assertEqual(self.records(logger)[1]["error"], {"type": "ReportedError"})

    def test_event_and_byte_limits_report_truncation(self):
        for options in ({"max_events": 3}, {"max_bytes": 4096}):
            with self.subTest(options=options):
                logger = OperationLogger(self.folder, **options)
                for _ in range(100):
                    logger.record("node_read", result={"node_count": 1})
                records = self.records(logger)
                self.assertTrue(logger.truncated)
                self.assertLessEqual(len(records), logger.max_events)
                self.assertLessEqual(logger.path.stat().st_size, logger.max_bytes)
                self.assertEqual(records[-1]["event"], "logging_limit_reached")
                self.assertTrue(records[-1]["result"]["logging_truncated"])
                self.assertIsNone(logger.finish("success"))

    def test_run_id_cannot_escape_directory_or_overwrite(self):
        for bad in ("../escape", "..\\escape", "/absolute", "customer-name", UnsafeObject()):
            with self.subTest(type=type(bad).__name__), self.assertRaises(ValueError):
                OperationLogger(self.folder, run_id=bad)
        identifier = "1046d6f2-806c-4248-9775-c416295da10e"
        logger = OperationLogger(self.folder, run_id=identifier)
        logger.finish("failed")
        original = logger.path.read_bytes()
        with self.assertRaises(FileExistsError):
            OperationLogger(self.folder, run_id=identifier)
        self.assertEqual(logger.path.read_bytes(), original)

    def test_storage_errors_propagate_and_error_cannot_claim_success(self):
        logger = OperationLogger(self.folder)
        for status in ("success", "passed", "complete", "completed"):
            with self.assertRaises(ValueError):
                logger.finish(status, error=RuntimeError("synthetic error"))
            with self.assertRaises(ValueError):
                logger.finish(status, partial=True)
            with self.assertRaises(ValueError):
                logger.finish(status, error_count=1)
        with patch.object(Path, "open", side_effect=PermissionError("synthetic denial")):
            with self.assertRaises(PermissionError):
                logger.finish("failed", error=RuntimeError("synthetic error"))
        self.assertEqual(self.records(logger), [])
        logger.finish("failed", error=RuntimeError("synthetic error"))
        self.assertEqual(self.records(logger)[0]["result"]["status"], "failed")

    def test_unknown_labels_rejected_and_invalid_budgets_rejected(self):
        logger = OperationLogger(self.folder, actor="C:\\private", model=UnsafeObject())
        for kwargs in ({"event": "private-customer"}, {"event": "node_read", "operation": "private"}):
            with self.assertRaises(ValueError):
                logger.record(**kwargs)
        for options in ({"max_events": True}, {"max_events": 1}, {"max_bytes": 100},
                        {"max_bytes": 1000000000}):
            with self.assertRaises(ValueError):
                OperationLogger(self.folder, **options)
        record = logger.finish("not_run")
        self.assertIsNone(record["actor"])
        self.assertIsNone(record["model"])
        self.assertEqual(DEFAULT_LOG_DIR.parts[-2:], ("artifacts", "agent-runs"))
        for network in ("\\\\server\\logs", "\\\\?\\C:\\logs"):
            with self.assertRaises(ValueError):
                OperationLogger(network)


if __name__ == "__main__":
    unittest.main()
