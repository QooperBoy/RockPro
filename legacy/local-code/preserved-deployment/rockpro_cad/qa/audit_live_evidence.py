"""Read-only audit of root's real CAD evidence, SQLite and archived bytes."""
import hashlib
import json
from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parents[1]
report = json.loads((root / "logs/project_live_acceptance.json").read_text(encoding="utf-8"))
checks = []
def check(name, ok):
    checks.append({"check": name, "passed": bool(ok)})
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

check("live protocol run passed", report["passed"])
for event in report["events"]:
    check("MCP " + event["tool"], event["returncode"] == 0 and
          not event["reply"].get("result", {}).get("isError", True))
conn = sqlite3.connect((root / "data/projects.sqlite3").as_uri() + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
try:
    project = dict(conn.execute("SELECT * FROM projects WHERE id=?", (report["project_id"],)).fetchone())
    snapshots = [dict(r) for r in conn.execute("SELECT * FROM snapshots WHERE project_id=?", (report["project_id"],))]
finally:
    conn.close()
latest = max(snapshots, key=lambda row: row["created_at"])
latest_report = json.loads(Path(latest["report_path"]).read_text(encoding="utf-8"))
check("persistent source equals latest working copy", project["source"] == latest_report["copy"])
check("at least initial two snapshots persisted", len(snapshots) >= report["snapshot_count"] == 2)
for item in snapshots:
    check("archive hash " + item["id"], sha(item["path"]) == item["sha256"])
    evidence = json.loads(Path(item["report_path"]).read_text(encoding="utf-8"))
    check("native verification " + item["id"], evidence["passed"] and evidence["source_unchanged"])
    check("original still unchanged " + item["id"], sha(evidence["source"]) == evidence["source_sha256_before"])
    check("archive separate from working copy " + item["id"], Path(item["path"]) != Path(evidence["copy"]))
    for key in ("geometry", "placement"):
        check("reopened " + key + " " + item["id"], evidence["after_reopen"]["reviews"][key]["passed"])
result = {"passed": all(c["passed"] for c in checks), "checks": checks,
          "scope": "Persisted real-CAD evidence and file hashes, no COM or UI calls"}
(root / "qa/live_evidence_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"passed": result["passed"], "checks": len(checks),
                  "failures": [c["check"] for c in checks if not c["passed"]]}, indent=2))
raise SystemExit(0 if result["passed"] else 1)
