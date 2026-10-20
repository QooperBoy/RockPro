"""Restricted RockPro skeleton operations. COM calls run on the calling STA thread."""
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
NAMES = ("RP_Length", "RP_Depth", "RP_BaseHeight", "RP_LidHeight",
         "RP_Thickness", "RP_DisplayGap")
LIMITS = {n: (1, 10000) for n in NAMES}
LIMITS.update(RP_Thickness=(1, 100), RP_DisplayGap=(0, 1000))


def validate_changes(changes):
    if not isinstance(changes, dict) or not changes:
        raise ValueError("changes must be a nonempty object of parameter names and millimetres")
    for name, value in changes.items():
        if name not in NAMES:
            raise ValueError("Unknown parameter: " + str(name))
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("Parameter must be a finite number in millimetres: " + name)
        lo, hi = LIMITS[name]
        if not lo <= value <= hi:
            raise ValueError(f"{name} must be between {lo} and {hi} mm")
    return dict(changes)


def validate_dimensions(values):
    validate_changes(values)
    t = values["RP_Thickness"]
    if min(values["RP_Length"], values["RP_Depth"]) <= 2*t:
        raise ValueError("Length and depth must exceed two wall thicknesses")
    if min(values["RP_BaseHeight"], values["RP_LidHeight"]) <= t:
        raise ValueError("Each half height must exceed one plate thickness")


def load_manifest():
    state = json.loads((ROOT/"skeleton_state.json").read_text(encoding="utf-8-sig"))
    path = Path(state["folder"])/"skeleton_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def source_path(source=None):
    path = Path(source or load_manifest()["file"]).resolve(strict=True)
    if not path.is_relative_to(ROOT.resolve()) or path.suffix.lower() != ".ics":
        raise ValueError("Only existing ICS files inside Integracja are permitted")
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(scene):
    return {n: {"mm": scene.ParameterMgr.GetParameterByName(n).Value*1000,
                "expression": scene.ParameterMgr.GetParameterByName(n).Expression}
            for n in NAMES}


def measure(scene, manifest):
    from wholecase_common import ICAPI, bbox, matrix, transformed_bbox, children
    from review_skeleton_geometry import validate
    from review_skeleton_global import validate_global
    values = {n: v["mm"] for n, v in snapshot(scene).items()}
    validate_dimensions(values)
    groups = children(scene.GetTopElement())
    if len(groups) != 2 or any(g.GetChildrenCount() != 5 for g in groups):
        raise ValueError("Only the verified two-half, ten-panel skeleton is supported")
    utility = scene.QueryInterface(ICAPI.IZSceneDocUtility)
    data = {"parameters_mm": values, "halves": {}}
    for half, height, closure in [("base", "RP_BaseHeight", "bottom"),
                                  ("lid", "RP_LidHeight", "top")]:
        row = dict(length_mm=values["RP_Length"], depth_mm=values["RP_Depth"],
                   height_mm=values[height], thickness_mm=values["RP_Thickness"],
                   closure=closure, panels=[])
        for panel in manifest["panels"]:
            if panel["half"] == half:
                part = utility.GetElementById(panel["id"])
                bounds = transformed_bbox(bbox(part, True), matrix(part))
                row["panels"].append({"role": panel["role"],
                                     "bbox_mm": [v*1000 for v in bounds]})
        data["halves"][half] = row
    reviews = {"geometry": validate(data), "placement": validate_global(data)}
    if not all(r["passed"] for r in reviews.values()):
        raise ValueError("Geometry validation failed: " + json.dumps(reviews))
    return {"measurements": data, "reviews": reviews}


def inspect_project(source=None):
    from ironcad_adapter import connect, ICAPI
    path = source_path(source)
    legacy, base, doc = connect(path)
    scene = doc.QueryInterface(ICAPI.IZSceneDoc)
    result = {"source": str(path), "saved": bool(legacy.Saved),
              "parameters": snapshot(scene), "scope": "plywood skeleton only"}
    result.update(measure(scene, load_manifest()))
    return result


def _change_dimensions_on_copy(changes, source=None):
    """Native snapshot preserves unsaved source geometry; edits apply only to new document."""
    from ironcad_adapter import connect, ICAPI
    changes = validate_changes(changes)
    path = source_path(source)
    legacy, base, doc = connect(path)
    scene = doc.QueryInterface(ICAPI.IZSceneDoc)
    manifest = load_manifest()
    before = snapshot(scene)
    measure(scene, manifest)  # refuse unrelated or already-invalid documents
    requested = {n: v["mm"] for n, v in before.items()} | changes
    validate_dimensions(requested)
    original_hash, original_saved = digest(path), bool(legacy.Saved)
    folder = ROOT/"rockpro_cad"/"revisions"/uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    target = folder/"RockPro_revision.ics"
    report = {"source": str(path), "copy": str(target), "changes_mm": changes,
              "before": before, "source_sha256_before": original_hash, "passed": False,
              "stage": "snapshot"}
    try:
        # This API is available in installed ICAPI and previously exercised by prepare_wholecase.
        # No SaveAs or original-document Save fallback is permitted.
        scene.SaveAsCopy(str(target), ICAPI.Z_LINKS_COPY_ALL, False)
        if snapshot(scene) != before or digest(path) != original_hash or bool(legacy.Saved) != original_saved:
            raise RuntimeError("Source state changed during native snapshot")
        report["stage"] = "open_copy"
        copy_doc = base.OpenFile(str(target), False)
        if Path(copy_doc.Name).resolve() != target.resolve():
            raise RuntimeError("IronCAD did not open the requested revision")
        copy_scene = copy_doc.QueryInterface(ICAPI.IZSceneDoc)
        report["stage"] = "change_parameters"
        for name, value in changes.items():
            copy_scene.ParameterMgr.GetParameterByName(name).Expression = f"{value:.12g} mm"
        copy_scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True)
        copy_scene.Update()
        report["stage"] = "validate_before_save"
        report["before_save"] = measure(copy_scene, manifest)
        report["stage"] = "save_copy"
        copy_doc.Save()
        copy_doc.Close()
        report["stage"] = "reopen_copy"
        reopened = base.OpenFile(str(target), False)
        if Path(reopened.Name).resolve() != target.resolve():
            raise RuntimeError("IronCAD reopened a different document")
        report["stage"] = "validate_after_reopen"
        report["after_reopen"] = measure(reopened.QueryInterface(ICAPI.IZSceneDoc), manifest)
        actual = report["after_reopen"]["measurements"]["parameters_mm"]
        if any(abs(actual[n]-v) > .002 for n, v in requested.items()):
            raise RuntimeError("Reopened parameter values do not match requested dimensions")
        report["passed"] = True
        report["stage"] = "completed"
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        # CAD can disconnect after a COM failure. Preserve the first error and
        # still write a failure report rather than masking it in this audit.
        try:
            report["source_unchanged"] = (digest(path) == original_hash and
                                        snapshot(scene) == before and
                                        bool(legacy.Saved) == original_saved)
        except Exception as exc:
            report["source_unchanged"] = False
            report["source_verification_error"] = str(exc)
        if not report["source_unchanged"]:
            report["passed"] = False
        (folder/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("Revision verification failed; see " + str(folder/"report.json"))
    return report


def change_dimensions_on_copy(changes, source=None, project_id=None, label=None):
    from project_store import pinned_source, register_snapshot, text
    if label is not None: text(label,"label",200)
    if project_id: source = pinned_source(project_id,source)
    if source and Path(source).name == "snapshot.ics":
        raise ValueError("Archived snapshots cannot be modified; use the project working source")
    report = _change_dimensions_on_copy(changes,source)
    if project_id:
        report.update(register_snapshot(project_id,report,label or "Zmiana wymiarów",advance=True))
    return report


def create_snapshot(project_id,label="Snapshot",note=""):
    from project_store import pinned_source,register_snapshot,text
    text(label,"label",200); text(note,"note")
    source=pinned_source(project_id)
    current=inspect_project(source)
    # Unchanged values reuse the verified native copy/save/reopen pipeline.
    report=_change_dimensions_on_copy({n:v["mm"] for n,v in current["parameters"].items()},source)
    return register_snapshot(project_id,report,label,note)


def dispatch(name, arguments):
    from project_store import list_projects, save_project, get_project, set_stage, list_snapshots
    db_tools={"list_projects":list_projects,"save_project":save_project,"get_project":get_project,
              "set_stage":set_stage,"list_snapshots":list_snapshots}
    allowed = {"inspect_project": {"source"}, "change_dimensions_on_copy": {"source", "changes","project_id","label"},
               "list_projects":set(),"save_project":{"project_id","name","client","device","quantity","notes","source"},
               "get_project":{"project_id"},"set_stage":{"project_id","stage","status","note"},
               "list_snapshots":{"project_id"},"create_snapshot":{"project_id","label","note"}}
    if name not in allowed or not isinstance(arguments, dict) or set(arguments)-allowed[name]:
        raise ValueError("Unknown tool or argument")
    if name in db_tools:
        return db_tools[name](**arguments)
    # CLI panel and MCP server must never drive the COM document concurrently.
    import msvcrt
    with (Path(__file__).parent/"cad.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("Another RockPro CAD operation is running") from exc
        try:
            return globals()[name](**arguments)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == "__main__":
    # Machine-readable CLI for native UI: one JSON request file, result on stdout.
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
        from contextlib import redirect_stdout
        with redirect_stdout(sys.stderr):
            result = dispatch(request["name"], request.get("arguments", {}))
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
