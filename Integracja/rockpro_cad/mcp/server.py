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
from layout import LAYOUT_PROPERTIES
layout_spec={"type":"object","additionalProperties":False,"properties":LAYOUT_PROPERTIES}
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


CORE_REQUEST = {"type":"object", "required":["spec","manifest","template_recipe"],
                "properties":{k:{"type":"object"} for k in ("spec","manifest","template_recipe","scenario")},
                "additionalProperties":False}
CORE_REV = {"type":"integer","minimum":1}
SCHEMAS += [
 schema("preview_case", "Calculate a complete prototype plan; no CAD edits or production approval",
        {"request":CORE_REQUEST}, ["request"], True),
 schema("prepare_case_request", "Prepare prototype inputs from the saved layout; unsupported variants are refused",
        {"project_id":S,"expected_layout_revision":CORE_REV}, ["project_id","expected_layout_revision"],True),
 schema("get_case_request", "Read the versioned case inputs shared by UI and AI", {"project_id":S},["project_id"],True),
 schema("save_case_request", "Save case inputs with optimistic concurrency; provenance is a caller claim",
        {"project_id":S,"request":CORE_REQUEST,"expected_revision":REV}|PROVENANCE,
        ["project_id","request","expected_revision"]),
 schema("plan_project_case", "Persist an immutable plan bound to inputs and source identity",
        {"project_id":S,"expected_revision":CORE_REV,"scenario":{"type":"object"}},["project_id","expected_revision"]),
 schema("execute_case_plan", "Execute a verified prototype plan once into a separate ICS and archive",
        {"project_id":S,"plan_id":S,"operation_id":S,"expected_revision":CORE_REV},
        ["project_id","plan_id","operation_id","expected_revision"]),
 schema("list_case_operations", "Find CAD operations after reopening the UI; unresolved operations first",
        {"project_id":S,"limit":{"type":"integer","minimum":1,"maximum":100}},["project_id"],True),
 schema("get_case_operation", "Read a CAD operation journal and its evidence",
        {"project_id":S,"operation_id":S},["project_id","operation_id"],True),
 schema("recover_case_operation", "Reconcile saved evidence after interruption; does not reinsert CAD parts",
        {"project_id":S,"operation_id":S},["project_id","operation_id"])
]


SCHEMAS += [
 schema('preview_excel_configuration','Validate a bounded XLSX staged in Integracja/imports; explicit units, no CAD edits',
        {'path':S},['path'],True),
 schema('import_excel_configuration','Import the previewed XLSX into versioned SQLite layout with CAS and duplicate protection; does not run CAD',
        {'project_id':S,'path':S,'expected_revision':REV,'expected_source_sha256':S},
        ['project_id','path','expected_revision','expected_source_sha256']),
]


SCHEMAS += [
 schema('preview_device_record','Validate a device variant with per-field units, sources and confirmation claims; preserve missing/conflicting data',{'record':{'type':'object'}},['record'],True),
 schema('save_device_record','Version source-cited device data in the shared SQLite with CAS; no product variant merging',{'record':{'type':'object'},'expected_revision':REV},['record','expected_revision']),
 schema('get_device_record','Read a current or historical device observation record',{'catalog_id':S,'revision':{'type':'integer','minimum':1}},['catalog_id'],True),
 schema('draft_device_inquiry','Draft missing/conflicting device data questions for an authorized sender; never sends messages',{'record':{'type':'object'}},['record'],True),
]


SCHEMAS += [
 schema('recommend_case_families','Filter source-bound family capabilities and rank candidates with reasons; no match routes to manual design',
        {'query':{'type':'object'},'families':{'type':'array','maxItems':200,'items':{'type':'object'}}},['query','families'],True),
 schema('benchmark_case_recommendations','Evaluate supplied closed labeled cases; never invent historical success labels',
        {'families':{'type':'array','maxItems':200,'items':{'type':'object'}},'cases':{'type':'array','minItems':1,'maxItems':500,'items':{'type':'object'}}},['families','cases'],True),
]


SCHEMAS += [schema('preview_device_layouts','Propose up to three allowed layouts from cited device dimensions with collision and conservative vertical removal checks; constructor edits/saves separately',
    {'record':{'type':'object'},'spec':{'type':'object','additionalProperties':False,'properties':{k:v for k,v in LAYOUT_PROPERTIES.items() if k not in ('x','y','z')}},
     'allowed_orientations':{'type':'array','minItems':1,'maxItems':6,'items':{'enum':['XYZ','XZY','YXZ','YZX','ZXY','ZYX']}},
     'allowed_arrangements':{'type':'array','minItems':1,'maxItems':3,'items':{'enum':['X','Y','Z']}},
     'removal_clearance_mm':{'type':'number','minimum':0,'maximum':500},
     'max_external_mm':{'type':'array','minItems':3,'maxItems':3,'items':{'type':'number','exclusiveMinimum':0,'maximum':10000}}},
    ['record','spec','allowed_orientations','allowed_arrangements'],True)]


SCHEMAS += [
 schema('preview_bom_file','Validate staged technology cutting BOM JSON and its approval reference; no CAD or production approval',{'path':S},['path'],True),
 schema('import_bom_file','Import immutable cutting BOM into shared SQLite with source hash and optimistic concurrency; repeated revision never adds demand',
        {'project_id':S,'path':S,'expected_revision':REV,'expected_source_sha256':S},['project_id','path','expected_revision','expected_source_sha256']),
 schema('aggregate_bom_demand','Aggregate only the latest cutting BOM per project; separate material, finish, thickness, technology, grain and exact due date',
        {'project_ids':{'type':'array','minItems':1,'maxItems':100,'uniqueItems':True,'items':S}},['project_ids'],True),
]


CUT_INPUT={'demand':{'type':'object'},'sheets':{'type':'array','minItems':1,'maxItems':500,'items':{'type':'object'}},'technology':{'type':'object'}}
SCHEMAS += [
 schema('verify_cut_plan','Independently verify exact quantities, material, grain, kerf, trims and guillotine cut sequence; not machine approval',
        CUT_INPUT|{'plan':{'type':'object'}},['demand','sheets','technology','plan'],True),
 schema('solve_reference_cut_plan','Bounded deterministic first-fit guillotine proposal; no optimum claim, timeout returns no unverified result',
        CUT_INPUT|{'max_seconds':{'type':'number','exclusiveMinimum':0,'maximum':30}},['demand','sheets','technology'],True),
 schema('export_cutting_csv','Export neutral cutting columns for explicit mapping in a verified vendor profile; not machine-ready',{'demand':{'type':'object'}},['demand'],True),
]


SCHEMAS += [
 schema('inventory_command','Operator-only transactional register/reserve/issue/consume/return/cancel/delivery/receive. CAS uses lot revision; no automatic purchasing',
        {'command':{'type':'object'},'operation_id':S,'expected_revision':REV},['command','operation_id','expected_revision']),
 schema('get_inventory','Read physical, held and free stock without double subtraction; confirmed unreceived deliveries are separate',{},readonly=True),
 schema('get_inventory_history','Read bounded immutable inventory operation receipts; caller identity is unverified',{'limit':{'type':'integer','minimum':1,'maximum':500}},readonly=True),
 schema('get_inventory_operation','Read one preserved inventory receipt by operation ID without retrying; optionally verify the exact pending command and revision. Missing is only a point-in-time observation',
        {'operation_id':S,'command':{'type':'object'},'expected_revision':REV},['operation_id'],True),
 schema('prepare_inventory_command','Operator-only durable request; does not reserve or change stock. Execution rechecks pinned lot/delivery revision',
        {'command':{'type':'object'},'operation_id':S,'expected_revision':REV,'decision_reference':S,'actor':S},['command','operation_id','expected_revision','decision_reference']),
 schema('execute_inventory_intent','Operator-only execution of the exact stored request; stock and committed state change atomically and retries never duplicate effects',{'operation_id':S},['operation_id']),
 schema('cancel_inventory_intent','Operator-only cancellation of an unexecuted request; cannot undo committed stock use',{'operation_id':S,'command_sha256':S},['operation_id','command_sha256']),
 schema('get_inventory_intent','Read a durable operator request and its preserved outcome without executing it',{'operation_id':S},['operation_id'],True),
 schema('list_inventory_intents','Read durable requests after restart; prepared does not mean stock availability or approval',{'state':{'type':'string','enum':['all','prepared','committed','rejected','cancelled']},'limit':{'type':'integer','minimum':1,'maximum':100}},readonly=True),
]


SCHEMAS += [schema('preview_purchases','Draft dated piece/sheet SKU purchase options from actual free stock and outstanding deliveries; MOQ/pack/tier/shipping/tax/cash limits; never orders',
    {'requirements':{'type':'object'},'offers':{'type':'array','maxItems':200,'items':{'type':'object'}},'policy':{'type':'object'}},['requirements','offers','policy'],True)]


SCHEMAS += [
 schema('save_material_plan','Persist an immutable independently verified draft cutting plan tied to current BOM/card/layout/source/snapshot; does not reserve stock',
        {'plan_id':S,'project_ids':{'type':'array','minItems':1,'maxItems':100,'items':S},'sheets':CUT_INPUT['sheets'],'technology':{'type':'object'},'cut_plan':{'type':'object'},'supersedes_plan_id':S},['plan_id','project_ids','sheets','technology','cut_plan']),
 schema('get_material_plan','Read saved plan, append-only progress and computed staleness against saved files and database revisions',{'plan_id':S},['plan_id'],True),
 schema('list_material_plans','Page through stored plan metadata without claiming current file freshness; use get_material_plan for explicit verification',{'limit':{'type':'integer','minimum':1,'maximum':100},'after_plan_id':S},readonly=True),
 schema('start_material_plan','Record operator start once with CAS; refuses stale plan and does not execute a machine',{'plan_id':S,'expected_revision':REV},['plan_id','expected_revision']),
 schema('record_material_progress','Append actual produced quantities or committed-order claims; never undo consumption or cancel purchases',
        {'plan_id':S,'event_id':S,'event':{'type':'object'},'expected_revision':REV},['plan_id','event_id','event','expected_revision']),
 schema('compare_material_plans','Compare revisions: produced parts, unapproved reuse candidates, shortages, preserved orders/expense and explicit unknown cost delta',
        {'old_plan_id':S,'new_plan_id':S},['old_plan_id','new_plan_id'],True),
]


HANDLE_EVIDENCE={'type':'object'}
HANDLE_CHOICE={'enum':['preserve_absolute','restore_rule','adopt_offset','leave_manual']}
SCHEMAS += [
 schema('measure_handle_reconciliation','Observe bound H7159 in the already-open project source, preserving active context; persist an observation token, no CAD edits',
        {'project_id':S,'expected_revision':REV,'expected_project_revision':REV,'target_values':{'type':'object'}},['project_id','expected_revision','expected_project_revision']),
 schema('preview_handle_reconciliation','Preview explicit whole-group H7159 decisions and fit at new anchors; evidence is a caller claim until native capture verifies it',
        {'evidence':HANDLE_EVIDENCE,'choice':HANDLE_CHOICE,'prior_state':{'type':'object'}},['evidence'],True),
 schema('get_handle_reconciliation','Read the latest durable constructor decision for bound handles; not full-case approval',{'project_id':S},['project_id'],True),
 schema('save_handle_reconciliation','Record an operator decision with review hash and independent project/decision CAS; does not edit CAD',
        {'project_id':S,'evidence':HANDLE_EVIDENCE,'choice':HANDLE_CHOICE,'prior_state':{'type':'object'},'expected_revision':REV,'expected_project_revision':REV,'review_sha256':S,'decision_reference':S,'measurement_id':S},
        ['project_id','evidence','choice','expected_revision','expected_project_revision','review_sha256','decision_reference']),
]


SCHEMAS += [
 schema('list_device_records','Page through current device variants with units and confirmation statuses; variants remain distinct',
        {'limit':{'type':'integer','minimum':1,'maximum':100},'after_catalog_id':S},readonly=True),
 schema('preview_catalog_layouts','Propose up to three constrained layouts from a saved catalog revision, retaining its source binding',
        {'catalog_id':S,'spec':layout_spec,'constraints':{'type':'object'},'expected_device_revision':{'type':'integer','minimum':1}},['catalog_id','spec','constraints'],True),
 schema('preview_bound_device_layout','Recheck a constructor-edited layout against pinned current device data, allowed choices and removal access',
        {'binding':{'type':'object'},'spec':layout_spec},['binding','spec'],True),
 schema('save_bound_device_layout','Atomically save the edited layout and immutable catalog source binding with independent source/layout checks; draft only',
        {'project_id':S,'spec':layout_spec,'binding':{'type':'object'},'expected_revision':REV}|PROVENANCE,['project_id','spec','binding','expected_revision']),
 schema('unlink_layout_device','Explicitly create an unlinked layout revision before entering manual device dimensions; historical source binding is retained',
        {'project_id':S,'expected_revision':REV}|PROVENANCE,['project_id','expected_revision']),
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
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "rockpro-cad", "version": "0.3.0"}}
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
