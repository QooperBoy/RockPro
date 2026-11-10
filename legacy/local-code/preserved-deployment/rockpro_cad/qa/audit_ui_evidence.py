"""Read-only independent follow-up to native UI smoke test."""
import hashlib
import json
from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parents[1]
log = json.loads((root / "logs/ui_live_acceptance.json").read_text(encoding="utf-8"))
conn = sqlite3.connect((root / "data/projects.sqlite3").as_uri() + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
try:
    project = dict(conn.execute("SELECT * FROM projects WHERE id=?", (log["project_id"],)).fetchone())
    snapshots = [dict(r) for r in conn.execute("SELECT * FROM snapshots WHERE project_id=?", (log["project_id"],))]
finally:
    conn.close()
snapshot = next(r for r in snapshots if r["id"] == log["snapshot"]["id"])
report = json.loads(Path(snapshot["report_path"]).read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = {
    "native UI evidence reports success": log["passed"] and all(log["checks"].values()),
    "persisted UI revision exists": snapshot["label"] == "Zmiana parametrów z panelu",
    "at least three revisions persisted": len(snapshots) >= 3,
    "archive checksum independently verified": sha(snapshot["path"]) == snapshot["sha256"],
    "UI archive length is 984 mm": json.loads(snapshot["parameters"])["RP_Length"] == 984,
    "native reopened length is 984 mm": report["after_reopen"]["measurements"]["parameters_mm"]["RP_Length"] == 984,
    "native reopened geometry and placement pass": all(r["passed"] for r in report["after_reopen"]["reviews"].values()),
    "source still has pre-operation SHA": sha(report["source"]) == report["source_sha256_before"],
    "working copy differs from archive": Path(report["copy"]) != Path(snapshot["path"]),
    "persisted project points to UI working copy": project["source"] == log["source"] == report["copy"],
}
result = {"passed": all(checks.values()), "checks": checks,
          "scope": "Independent file/DB evidence audit; native UI observations attributed to root agent"}
(root / "qa/ui_evidence_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["passed"] else 1)
