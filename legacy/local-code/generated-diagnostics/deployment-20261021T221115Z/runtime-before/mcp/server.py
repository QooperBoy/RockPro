"""Minimal MCP stdio server. No HTTP listener, arbitrary execution, or external dependencies."""
import json
import sys
from contextlib import redirect_stdout
from worker import dispatch, NAMES, LIMITS
from project_store import RevisionConflict

SCHEMAS = [
    {"name": "inspect_project", "description": "Read and validate the open RockPro plywood skeleton.",
     "annotations": {"readOnlyHint": True, "openWorldHint": False},
     "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}},
                     "additionalProperties": False}},
    {"name": "change_dimensions_on_copy",
     "description": "Create a native ICS snapshot, change allowed dimensions in millimetres only on that copy, validate and reopen it. Original is not saved or edited.",
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False,
                     "openWorldHint": False},
     "inputSchema": {"type": "object", "required": ["changes"],
                     "properties": {"source": {"type": "string"}, "project_id": {"type":"string"}, "label":{"type":"string"}, "layout_revision":{"type":"integer","minimum":1},
                                    "changes": {"type": "object", "minProperties": 1,
                                                "additionalProperties": False,
                                                "properties": {n: {"type": "number", "minimum": LIMITS[n][0],
                                                                   "maximum": LIMITS[n][1]} for n in NAMES}}},
                     "additionalProperties": False}}
]


def schema(name, description, properties, required=(), readonly=False):
    return {"name":name,"description":description,"annotations":{"readOnlyHint":readonly,"destructiveHint":False,"openWorldHint":False},
            "inputSchema":{"type":"object","properties":properties,"required":list(required),"additionalProperties":False}}
S={"type":"string"}
REV={"type":"integer","minimum":0}
PROVENANCE={"actor":S,"change_source":S}
from layout import DEFAULT
layout_spec={"type":"object","additionalProperties":False,"properties":{k:{"type":"string" if isinstance(v,str) else "integer" if k=="count" else "number"} for k,v in DEFAULT.items()}}
SCHEMAS += [
 schema("preview_layout","Calculate device envelopes, partitions and accessory space in mm; no CAD edits",{"spec":layout_spec},["spec"],True),
 schema("get_layout","Read current or historical immutable layout; revision 0 means unsaved",{"project_id":S,"revision":{"type":"integer","minimum":1}},["project_id"],True),
 schema("save_layout","Save layout specification and invalidate downstream stages",{"project_id":S,"spec":layout_spec,"expected_revision":REV}|PROVENANCE,["project_id","spec","expected_revision"])
]
SCHEMAS += [
 schema("list_projects","List locally persisted SQLite projects",{},readonly=True),
 schema("save_project","Create a project (revision 0/absent) or update with expected_revision from get_project; caller provenance is unverified",{k:S for k in ("project_id","name","client","device","notes","source")}|{"quantity":{"type":"integer","minimum":1,"maximum":100000},"expected_revision":REV}|PROVENANCE,["name"]),
 schema("get_project","Read project card, manually recorded stages and snapshot history",{"project_id":S},["project_id"],True),
 schema("set_stage","Record a manual workflow status; this does NOT validate CAD",{"project_id":S,"stage":{"enum":["inquiry","devices","layout","geometry","hardware","wheels","documentation","materials","production"]},"status":{"enum":["draft","waiting","review","approved","outdated"]},"note":S,"expected_revision":REV}|PROVENANCE,["project_id","stage","status","expected_revision"]),
 schema("get_history","Read paginated project audit; actor/source are caller claims, not authenticated identities",{"project_id":S,"limit":{"type":"integer","minimum":1,"maximum":200},"before_id":{"type":"integer","minimum":1}},["project_id"],True),
 schema("list_snapshots","Read validated archived snapshots and checksum integrity",{"project_id":S},["project_id"],True),
 schema("create_snapshot","Capture and validate an unchanged native skeleton copy, then archive it separately from working files",{"project_id":S,"label":S,"note":S},["project_id"])
]


def handle(request):
    ident = request.get("id")
    if ident is None:
        return None
    method = request.get("method")
    params = request.get("params", {})
    if method == "initialize":
        version = params.get("protocolVersion")
        result = {"protocolVersion": version if version in ("2024-11-05", "2025-03-26", "2025-06-18") else "2025-06-18",
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "rockpro-cad", "version": "0.2.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": SCHEMAS}
    elif method == "tools/call":
        try:
            with redirect_stdout(sys.stderr):
                data = dispatch(params["name"], params.get("arguments", {}))
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                      "isError": False}
        except RevisionConflict as exc:
            result = {"content": [{"type": "text", "text": json.dumps(exc.details, ensure_ascii=False)}], "isError": True}
        except Exception as exc:
            print(str(exc), file=sys.stderr, flush=True)
            result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": ident,
                "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        try:
            reply = handle(json.loads(line))
        except Exception:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON-RPC request"}}
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False), flush=True)
