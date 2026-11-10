"""End-to-end project workflow using a fresh MCP subprocess per operation."""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
events = []

def call(name, arguments):
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "RockPro-project-acceptance", "version": "0.2"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": name, "arguments": arguments}},
    ]
    result = subprocess.run(
        [sys.executable, str(ROOT / "mcp/server.py")],
        input="\n".join(json.dumps(r) for r in requests) + "\n",
        capture_output=True, text=True, encoding="utf-8", timeout=180)
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    reply = next(r for r in replies if r.get("id") == 2)
    events.append({"tool": name, "arguments": arguments, "reply": reply,
                   "stderr": result.stderr, "returncode": result.returncode})
    assert result.returncode == 0, result.stderr
    assert "error" not in reply, reply
    assert not reply["result"].get("isError"), reply
    return json.loads(reply["result"]["content"][0]["text"])

def main():
    manifest = json.loads((ROOT.parent / "skeleton/20261020T110925Z/skeleton_manifest.json")
                          .read_text(encoding="utf-8"))
    project = call("save_project", {
        "name": "Epson — test integracji 0.2 " + datetime.now().strftime("%H:%M"),
        "client": "RockPro / test wewnętrzny", "device": "Epson — szkielet MVP",
        "quantity": 1, "source": manifest["file"],
        "notes": "Rzeczywisty test MCP + SQLite. Dziesięć płyt; bez okuć. Nie jest zleceniem produkcyjnym."
    })["project"]
    ident = project["id"]
    retrieved = call("get_project", {"project_id": ident})["project"]
    assert retrieved["name"] == project["name"]
    stages = retrieved["stages"]
    call("set_stage", {"project_id": ident, "stage": stages[0]["key"],
                      "status": "review", "note": "Test zapisu ręcznego statusu — bez zatwierdzenia technicznego."})
    call("create_snapshot", {"project_id": ident, "label": "Stan początkowy testu",
                             "note": "Kopia natywna zweryfikowana przez backend."})
    call("change_dimensions_on_copy", {"project_id": ident,
                                       "changes": {"RP_Length": 964, "RP_Depth": 632},
                                       "label": "Wariant testowy 964 × 632"})
    final = call("get_project", {"project_id": ident})["project"]
    history = call("list_snapshots", {"project_id": ident})["snapshots"]
    assert len(history) == 2, history
    actual = call("inspect_project", {"source": final["source"]})
    assert abs(actual["parameters"]["RP_Length"]["mm"] - 964) < .002
    assert abs(actual["parameters"]["RP_Depth"]["mm"] - 632) < .002
    assert final["source"] != manifest["file"]
    return {"project_id": ident, "source": final["source"], "snapshot_count": len(history)}

if __name__ == "__main__":
    report = {"time": datetime.now().isoformat(), "passed": False, "events": events}
    try:
        report.update(main(), passed=True)
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        (ROOT / "logs/project_live_acceptance.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "events"},
                         ensure_ascii=True))
