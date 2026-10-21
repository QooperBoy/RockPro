"""Bounded local operation evidence, deliberately separate from the CAD inventory.

Only known counters, statuses and cryptographic references are retained. Names,
paths, geometry, exception messages and arbitrary object representations never
belong in this log. A successful append is evidence of an operation report, not
proof that CAD geometry is valid. Storage errors propagate to the caller.
"""
import json
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
LOGGER_VERSION = "1"
DEFAULT_LOG_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "agent-runs"
_EVENTS = frozenset(("operation_started", "node_read", "read_error", "limit_reached",
                     "operation_finished", "logging_limit_reached", "source_checked",
                     "inventory_written"))
_OPERATIONS = frozenset(("parts.inspect", "parts.inventory", "parts.native_test",
                         "parts.read", "parts.cli"))
_STATUSES = frozenset(("started", "success", "passed", "failed", "partial", "error",
                       "complete", "completed", "skipped", "not_run", "limited"))
_COUNTERS = frozenset(("max_depth", "max_nodes", "max_seconds", "node_count",
                      "part_count", "assembly_count", "error_count", "visited_count",
                      "row_count", "occurrence_count", "unique_part_count", "depth",
                      "child_count", "feature_count", "scene_count", "skipped_count",
                      "rows", "errors", "nodes", "parts", "assemblies", "occurrences",
                      "max_events", "max_bytes", "empty_assembly_count",
                      "geometry_valid_part_count"))
_FLAGS = frozenset(("partial", "source_unchanged", "hash_verified", "read_only",
                   "truncated", "logging_truncated", "passed"))
_REFERENCES = frozenset(("source_sha256", "inventory_sha256", "result_sha256",
                        "before_sha256", "after_sha256", "code_sha256"))
_TOKEN = re.compile(r"[A-Za-z0-9_.:+-]{1,100}\Z")
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")


def _number(value):
    return (type(value) in (int, float) and 0 <= value <= 1e12
            and math.isfinite(value))


def _summary(data):
    if type(data) is not dict:
        return {}
    clean = {}
    # Iterate our allowlist rather than arbitrary user dictionary keys.
    for key in _COUNTERS:
        value = data.get(key)
        if _number(value):
            clean[key] = value
    for key in _FLAGS:
        value = data.get(key)
        if type(value) is bool:
            clean[key] = value
    value = data.get("status")
    if type(value) is str and value in _STATUSES:
        clean["status"] = value
    return clean


def _identity(value):
    return value if type(value) is str and _TOKEN.fullmatch(value) else None


class OperationLogger:
    """Write one private JSONL run; limits include a final truncation marker.

    The caller supplies actor/model provenance. Unknown model, reasoning effort,
    tokens and cost remain null; this deterministic utility does not infer them.
    No CAD property is read or changed by this class.
    """

    def __init__(self, log_dir=None, *, actor="agent", model=None, run_id=None,
                 max_events=10000, max_bytes=4 * 1024 * 1024):
        if type(max_events) is not int or not 2 <= max_events <= 100000:
            raise ValueError("max_events must be between 2 and 100000")
        if type(max_bytes) is not int or not 4096 <= max_bytes <= 64 * 1024 * 1024:
            raise ValueError("max_bytes must be between 4096 and 67108864")
        if run_id is None:
            self.run_id = str(uuid.uuid4())
        else:
            if type(run_id) is not str:
                raise ValueError("run_id must be a UUID")
            try:
                self.run_id = str(uuid.UUID(run_id))
            except (ValueError, AttributeError) as exc:
                raise ValueError("run_id must be a UUID") from exc
        self.actor = _identity(actor)
        self.model = _identity(model)
        self.max_events, self.max_bytes = max_events, max_bytes
        self._count = self._bytes = 0
        self._parent_event_id = None
        self.truncated = False
        folder = Path(log_dir) if log_dir is not None else DEFAULT_LOG_DIR
        # UNC/device destinations are not local operation evidence.
        if folder.drive.startswith("\\\\") or str(folder).startswith(("//", "\\\\")):
            raise ValueError("Operation logs require a local directory")
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / (self.run_id + ".jsonl")
        # Exclusive creation preserves evidence from an existing run.
        with self.path.open("x", encoding="utf-8"):
            pass

    def _base(self, event, operation):
        return dict(schema_version=SCHEMA_VERSION, logger_version=LOGGER_VERSION,
                    run_id=self.run_id, event_id=str(uuid.uuid4()),
                    parent_event_id=self._parent_event_id,
                    timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    event=event, operation=operation, actor=self.actor, model=self.model,
                    project_id=None, document_id=None,
                    input_revision=None, output_revision=None,
                    code_version=None, prompt_version=None, rules_version=None,
                    reasoning_effort=None, tokens=None, cost=None)

    def _append(self, record):
        encoded = (json.dumps(record, ensure_ascii=True, allow_nan=False,
                              separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        if len(encoded) + self._bytes > self.max_bytes:
            raise RuntimeError("Operation log size invariant violated")
        with self.path.open("ab") as stream:
            written = stream.write(encoded)
            if written != len(encoded):
                raise OSError("Incomplete operation log write")
        self._count += 1
        self._bytes += len(encoded)
        self._parent_event_id = record["event_id"]
        return record

    def record(self, event, *, operation="parts.inspect", arguments=None,
               result=None, error=None, duration_ms=None, refs=None):
        if type(event) is not str or event not in _EVENTS:
            raise ValueError("Unknown operation event")
        if type(operation) is not str or operation not in _OPERATIONS:
            raise ValueError("Unknown operation")
        if self.truncated:
            return None
        record = self._base(event, operation)
        record["arguments"], record["result"] = _summary(arguments), _summary(result)
        record["duration_ms"] = duration_ms if _number(duration_ms) else None
        record["refs"] = {}
        if type(refs) is dict:
            for key in _REFERENCES:
                value = refs.get(key)
                if type(value) is str and _SHA256.fullmatch(value):
                    record["refs"][key] = value.lower()
        record["document_id"] = record["refs"].get("source_sha256")
        record["error"] = None
        if error is not None:
            # Never call str/repr on an exception or caller-supplied object.
            error_type = type(error).__name__ if isinstance(error, BaseException) else "ReportedError"
            record["error"] = {"type": _identity(error_type) or "Error"}
        size = len((json.dumps(record, ensure_ascii=True, allow_nan=False,
                               separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8"))
        # Reserve sufficient space for one small, truthful truncation event.
        if self._count >= self.max_events - 1 or self._bytes + size + 1024 > self.max_bytes:
            marker = self._base("logging_limit_reached", operation)
            marker["result"] = {"logging_truncated": True}
            self._append(marker)
            self.truncated = True
            return None
        return self._append(record)

    def finish(self, status, *, operation="parts.inspect", error=None,
               duration_ms=None, refs=None, **summary):
        if type(status) is not str or status not in _STATUSES:
            raise ValueError("Unknown operation status")
        if status in ("success", "passed", "complete", "completed"):
            error_count = summary.get("error_count")
            if (error is not None or summary.get("partial") is True
                    or (_number(error_count) and error_count > 0)):
                raise ValueError("An operation with errors or a partial result cannot finish successfully")
        return self.record("operation_finished", operation=operation,
                           result=dict(summary, status=status), error=error,
                           duration_ms=duration_ms, refs=refs)
