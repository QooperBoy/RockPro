"""Quit only if all open CAD documents are known, saved test documents."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from ironcad_adapter import connect

known = {ROOT.parent / "skeleton/20261020T110925Z/RockPro_Epson_szkielet_MVP.ics"}
def paths(value):
    if isinstance(value, dict):
        for item in value.values(): paths(item)
    elif isinstance(value, list):
        for item in value: paths(item)
    elif isinstance(value, str) and value.startswith("{"):
        try: paths(json.loads(value))
        except ValueError: pass
    elif isinstance(value, str) and value.lower().endswith(".ics"):
        p = Path(value)
        if p.is_absolute() and p.exists() and p.is_relative_to(ROOT.parent):
            known.add(p)
for name in ("mcp_live_change.json", "project_live_acceptance.json"):
    paths(json.loads((ROOT / "logs" / name).read_text(encoding="utf-8")))
for report in (ROOT / "revisions").glob("*/report.json"):
    paths(json.loads(report.read_text(encoding="utf-8")))

docs = []
app = base = None
for path in known:
    try:
        legacy, b, doc = connect(path)
    except RuntimeError:
        continue
    if not legacy.Saved:
        raise RuntimeError("Unsaved changes: " + str(path))
    app = legacy.Application
    base = b
    docs.append(str(path))
if base is None:
    raise RuntimeError("No known open documents")
count = base.GetOpenDocsCount()
active = str(base.ActiveDoc.Name)
if count != len(docs) or active.lower() not in {p.lower() for p in docs}:
    raise RuntimeError(f"Unexpected open document: count={count}, known={len(docs)}, active={active}")
print(json.dumps({"known_saved_documents": docs, "count": count}, ensure_ascii=True))
if "--quit" in sys.argv:
    app.Quit()
    print("Normal Quit completed; all known documents were saved.")
