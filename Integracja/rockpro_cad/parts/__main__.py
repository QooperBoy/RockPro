"""python -m rockpro_cad.parts --source OPEN_FILE.ics [--output NEW.json]."""

import argparse
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import sys
import time

from .native import inspect_source, same_document_path
from .operation_log import OperationLogger
from .reader import ReadLimits


def reader_code_sha256(package_dir=None):
    """Fingerprint sorted package source names and bytes, excluding tests."""
    folder = Path(package_dir) if package_dir is not None else Path(__file__).parent
    digest = hashlib.sha256()
    for source in sorted(folder.glob("*.py"), key=lambda path: path.name):
        if source.name.startswith("test"):
            continue
        content = source.read_bytes()
        digest.update(source.name.encode("utf-8") + b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def main(argv=None, *, adapter_factory=None):
    parser = argparse.ArgumentParser(description="Read-only inventory of an already open IronCAD ICS")
    parser.add_argument("--source", required=True)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--max-nodes", type=int, default=10000)
    parser.add_argument("--max-seconds", type=float, default=30)
    parser.add_argument("--output", help="Optional new JSON report (exclusive creation; no overwrite)")
    parser.add_argument("--log-dir", help="Local operation JSONL directory; default artifacts/agent-runs")
    args = parser.parse_args(argv)
    started = time.monotonic()
    logger = None
    result = {"schema_version": 1, "operation": "parts.inspect", "read_only": True,
              "status": "failed", "partial": True, "rows": [], "errors": []}
    output = None
    try:
        limits = ReadLimits(args.max_depth, args.max_nodes, args.max_seconds)
        source = Path(args.source).resolve(strict=True)
        if args.output:
            output = Path(args.output).resolve()
            if same_document_path(output, source) or output.suffix.lower() != ".json":
                raise ValueError("output must be a new JSON report, separate from the ICS source")
            if output.exists():
                raise FileExistsError("output report already exists; choose a new filename")
        code_digest = reader_code_sha256()
        logger = OperationLogger(log_dir=args.log_dir, actor="deterministic-reader", model=None)
        logger.record("operation_started", arguments={"max_depth": limits.max_depth,
                      "max_nodes": limits.max_nodes, "max_seconds": limits.max_seconds},
                      refs={"code_sha256": code_digest})
        with redirect_stdout(sys.stderr):
            result = inspect_source(source, limits,
                       lambda event, **summary: logger.record(event, result=summary),
                       adapter_factory=adapter_factory)
        logger.record("source_checked", result={"source_unchanged": result["source"]["unchanged"]},
                      refs={"source_sha256": result["source"]["sha256_after"]})
        result["operation_log"] = str(logger.path)
        result["reader_code_sha256"] = code_digest
        result["cad_read_status"] = result["status"]
        # The inventory and JSONL are separate files, not an atomic transaction.
        # Persisted inventories explicitly await log finalization; stdout reports
        # the final operation outcome after both writes have been attempted.
        result["operation_log_status"] = "pending_finalization"
        result["logging_truncated"] = logger.truncated
        inventory_digest = None
        if output is not None:
            result["inventory_path"] = str(output)
            payload = (json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
            # x prevents races and preserves both previous reports and customer data.
            with output.open("xb") as stream:
                stream.write(payload)
            inventory_digest = hashlib.sha256(payload).hexdigest()
            logger.record("inventory_written", result={"row_count": len(result["rows"])},
                          refs={"inventory_sha256": inventory_digest})
        logger.finish(result["status"], partial=result["partial"],
                      duration_ms=round((time.monotonic() - started) * 1000, 3),
                      refs={"source_sha256": result["source"]["sha256_after"],
                            "inventory_sha256": inventory_digest}, **result.get("summary", {}))
        result["logging_truncated"] = logger.truncated
        result["operation_log_status"] = "truncated" if logger.truncated else "finished"
    except Exception as exc:
        result["status"] = "failed"
        result["partial"] = True
        result["operation_log_status"] = "failed"
        result["errors"].append({"field": "cli", "type": type(exc).__name__, "message": str(exc)[:1000]})
        if logger is not None:
            result["operation_log"] = str(logger.path)
            try:
                logger.record("read_error", error=exc)
                logger.finish("failed", partial=True)
            except Exception as log_exc:
                result["errors"].append({"field": "operation_log", "type": type(log_exc).__name__,
                                         "message": str(log_exc)[:1000]})
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "complete" else 2 if result["status"] == "partial" else 1


if __name__ == "__main__":
    raise SystemExit(main())
