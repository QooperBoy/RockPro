"""Explicit source-bound rigid reuse on new native copies.

This is an internal prototype seam, not a catalog approval or an MCP command.
It preserves real native bodies; it never turns their bounding boxes into solids.
"""
import json
import math
from pathlib import Path
import re
import uuid

from ..cad_lock import cad_writer_lock
from ..parts.native import file_sha256, same_document_path
from .native import IronCADPrototypeDriver, NativeExecutionError, write_receipt_once
from .native_reader import NativePoseAdapter, validate_matrix, transform_bbox


def native_volume(values):
    # ICAPI output order is out pdAchievedAccuracy, retval pdVolume.
    accuracy, volume = values
    if (type(volume) not in (int,float) or not math.isfinite(volume) or volume <= 0
            or type(accuracy) not in (int,float) or not math.isfinite(accuracy) or accuracy < 0):
        raise NativeExecutionError("native catalog volume or achieved accuracy unavailable")
    return accuracy, volume


def _signature(adapter, node):
    """Measured native body topology, volume, and local geometry per tree path."""
    result = []
    def walk(element, path):
        identity = adapter.identity(element)
        row = {"occurrence_path": path, "kind": identity["kind"], "name": identity["name"]}
        if identity["kind"] in ("assembly", "part"):
            # Opaque original subtrees can contain unchanged mirror transforms.
            # The source root WORLD and requested mount remain proper; internal
            # parent transforms are preserved exactly, never unmirrored.
            row["matrix_parent_mm"] = validate_matrix(adapter.matrix(element,False),allow_reflection=True)
        if identity["kind"] == "part":
            part = element.QueryInterface(adapter.api.IZPart)
            box = adapter.bbox(element, "part")
            if not box["valid"]:
                raise NativeExecutionError("invalid native catalog body box")
            body = part.GetBody(True)
            accuracy, volume = native_volume(part.QueryInterface(adapter.api.IZPartProperty).GetVolume(0.001))
            row.update(local_bounds_mm=box["minimum"]+box["maximum"], volume_m3=volume,
                       volume_requested_accuracy=0.001, volume_achieved_accuracy=accuracy,
                       faces=body.GetFacesCount(), edges=body.GetEdgesCount(), vertices=body.GetVerticesCount(),
                       lumps=body.GetLumpsCount())
        result.append(row)
        if identity["kind"] == "assembly":
            for index in range(adapter.child_count(element)):
                walk(adapter.child_at(element,index), path+[index])
    walk(node, [])
    if not any(row["kind"] == "part" for row in result):
        raise NativeExecutionError("catalog assembly contains no physical parts")
    return result


def compare_body_signatures(before, after):
    if len(before) != len(after):
        raise NativeExecutionError("catalog subtree inventory changed")
    for a,b in zip(before,after):
        for field in ("occurrence_path", "kind", "name", "faces", "edges", "vertices", "lumps"):
            if a.get(field) != b.get(field):
                raise NativeExecutionError("catalog topology or tree changed: "+field)
        if a["kind"] == "part":
            if max(abs(x-y) for x,y in zip(a["local_bounds_mm"],b["local_bounds_mm"])) > 0.003:
                raise NativeExecutionError("catalog local body geometry changed")
            if abs(a["volume_m3"]-b["volume_m3"]) > max(1e-15, abs(a["volume_m3"])*1e-8):
                raise NativeExecutionError("catalog body volume changed")
        # Keep every opaque subpart/subassembly placement as well as its shape.
        # The subtree root itself is intentionally moved rigidly.
        if a["occurrence_path"] and a["kind"] in ("part","assembly"):
            for i in range(4):
                for j in range(4):
                    tolerance = 0.003 if i==3 and j<3 else 1e-6
                    if abs(a["matrix_parent_mm"][i][j]-b["matrix_parent_mm"][i][j]) > tolerance:
                        raise NativeExecutionError("catalog subtree placement changed")


def validate_source_binding(binding):
    fields = {"schema_version", "source_path", "source_sha256", "source_guid", "node_id", "node_name", "expected_world_matrix_mm"}
    if (not isinstance(binding,dict) or set(binding) != fields
            or type(binding.get("schema_version")) is not int or binding["schema_version"] != 1):
        raise ValueError("exact versioned source identity binding required")
    if type(binding["node_id"]) is not int or binding["node_id"] <= 0:
        raise ValueError("source node ID must be positive integer")
    if not isinstance(binding["node_name"],str) or not binding["node_name"]:
        raise ValueError("source node name required")
    if not isinstance(binding["source_sha256"],str) or not re.fullmatch("[0-9a-f]{64}",binding["source_sha256"]):
        raise ValueError("source SHA256 required")
    validate_matrix(binding["expected_world_matrix_mm"])
    return binding


def execute_rigid_reuse(binding, *, output_dir, target_matrix_mm, operation_id=None, source_is_captured_copy=False):
    """Copy/export/import a measured proper source node, rigidly place, reopen.

    A binding must come from explicit source evidence. Reflections are refused.
    The output preserves opaque native subparts and their native body topology.
    """
    binding = validate_source_binding(binding)
    validate_matrix(target_matrix_mm)
    operation_id = operation_id or uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",operation_id):
        raise ValueError("invalid operation ID")
    parent = Path(output_dir).resolve(strict=True)
    if type(source_is_captured_copy) is not bool:
        raise ValueError("source_is_captured_copy must be explicit boolean")
    if source_is_captured_copy:
        source = Path(binding["source_path"]).resolve(strict=True)
        artifacts = Path(__file__).resolve().parents[3]/"artifacts"
        if (source.name != "source_snapshot.ics" or not source.is_relative_to(parent)
                or not parent.is_relative_to(artifacts.resolve(strict=True))):
            raise ValueError("direct read/export requires a source_snapshot.ics captured inside the artifacts workspace")
    destination = parent / operation_id
    with cad_writer_lock():
        driver = IronCADPrototypeDriver(binding["source_path"])
        if driver.before_hash != binding["source_sha256"] or driver.before["file_guid"] != binding["source_guid"]:
            raise NativeExecutionError("source binding SHA256 or GUID mismatch")
        source_scene = driver.adapter.document.QueryInterface(driver.api.IZSceneDoc)
        source_node = source_scene.QueryInterface(driver.api.IZSceneDocUtility).GetElementById(binding["node_id"])
        if int(source_node.Id) != binding["node_id"] or str(source_node.Name) != binding["node_name"]:
            raise NativeExecutionError("source node identity mismatch")
        pose = NativePoseAdapter(driver.adapter.legacy,driver.base,driver.adapter.document,driver.api,driver.source)
        source_matrix = validate_matrix(pose.matrix(source_node,True))
        for i in range(4):
            for j in range(4):
                tolerance = 0.003 if i==3 and j<3 else 1e-6
                if abs(source_matrix[i][j]-binding["expected_world_matrix_mm"][i][j]) > tolerance:
                    raise NativeExecutionError("live source pose drifted from binding")
        destination.mkdir(exist_ok=False)
        try:
            source_evidence = driver.capture(destination/"source_snapshot.ics")
            if source_is_captured_copy:
                # The explicitly pinned input is itself an already-open capture
                # under artifacts. Native SaveAs(False) exports its subtree into
                # a new asset; no setter, close or save touches this input.
                copied_doc, copied_node, copied_pose = driver.adapter.document, source_node, pose
                source_evidence["read_export_route"] = "explicit_already_open_captured_copy"
            else:
                copied_doc = driver.base.OpenFile(source_evidence["snapshot_path"],False)
                if not same_document_path(copied_doc.Name,source_evidence["snapshot_path"]):
                    raise NativeExecutionError("wrong copied source opened")
                copied_scene = copied_doc.QueryInterface(driver.api.IZSceneDoc)
                copied_node = copied_scene.QueryInterface(driver.api.IZSceneDocUtility).GetElementById(binding["node_id"])
                copied_pose = NativePoseAdapter(driver.adapter.legacy,driver.base,copied_doc,driver.api,driver.source)
            source_signature = _signature(copied_pose,copied_node)
            source_box = copied_pose.bbox(copied_node,copied_pose.identity(copied_node)["kind"])
            if not source_box["valid"]:
                raise NativeExecutionError("source catalog assembly bounds unavailable")
            asset = destination/"source_catalog_asset.ics"
            interface = driver.api.IZAssembly if copied_pose.identity(copied_node)["kind"] == "assembly" else driver.api.IZPart
            copied_node.QueryInterface(interface).SaveAs(str(asset),False)
            # OpenNewDoc is implemented in ICAPI 2027; OpenNewScene is not.
            document = driver.base.OpenNewDoc(driver.api.Z_SCENE,False,True,"")
            scene = document.QueryInterface(driver.api.IZSceneDoc)
            assembly = scene.GetTopElement().QueryInterface(driver.api.IZAssembly)
            imported = assembly.AddChildFromExternalFile(str(asset),False)
            imported_pose = NativePoseAdapter(driver.adapter.legacy,driver.base,document,driver.api,driver.source)
            compare_body_signatures(source_signature,_signature(imported_pose,imported))
            imported_box = imported_pose.bbox(imported,imported_pose.identity(imported)["kind"])
            if (not imported_box["valid"] or max(abs(x-y) for x,y in zip(source_box["minimum"]+source_box["maximum"],
                    imported_box["minimum"]+imported_box["maximum"])) > 0.003):
                raise NativeExecutionError("catalog export/import changed local mounting frame")
            se = imported.QueryInterface(driver.api.IZSceneElement)
            matrix = se.GetTransformToParent()
            for i in range(4):
                for j in range(4):
                    matrix.SetValue(i,j,target_matrix_mm[i][j]/1000 if i==3 and j<3 else target_matrix_mm[i][j])
            se.SetTransformToParent(matrix)
            scene.Update()
            output = destination/"rigid_catalog_reuse.ics"
            scene.SaveAs(str(output),driver.api.Z_LINKS_COPY_ALL,False)
            if not same_document_path(document.Name,output) or document.Modified:
                raise NativeExecutionError("rigid output did not save cleanly")
            imported_id = int(imported.Id)
            document.Close()
            reopened = driver.base.OpenFile(str(output),False)
            if not same_document_path(reopened.Name,output):
                raise NativeExecutionError("wrong rigid output reopened")
            reopened_scene = reopened.QueryInterface(driver.api.IZSceneDoc)
            observed = reopened_scene.QueryInterface(driver.api.IZSceneDocUtility).GetElementById(imported_id)
            reopened_pose = NativePoseAdapter(driver.adapter.legacy,driver.base,reopened,driver.api,driver.source)
            final_signature = _signature(reopened_pose,observed)
            compare_body_signatures(source_signature,final_signature)
            observed_matrix = validate_matrix(reopened_pose.matrix(observed,True))
            error = max(abs(observed_matrix[3][j]-target_matrix_mm[3][j]) for j in range(3))
            rotation_error = max(abs(observed_matrix[i][j]-target_matrix_mm[i][j]) for i in range(3) for j in range(3))
            if error > 0.003 or rotation_error > 1e-6:
                raise NativeExecutionError("rigid imported pose differs from target")
            driver.assert_source_unchanged()
            receipt = {"schema_version":1,"passed":True,"operation_id":operation_id,"source":source_evidence,
                "source_binding":binding,"output_path":str(output),"output_sha256":file_sha256(output),
                "asset_path":str(asset),"asset_sha256":file_sha256(asset),"production_approved":False,
                "geometry_scope":"real_source_rigid_assembly_slice; full case mounting not approved",
                "source_unchanged":True,"catalog_reused":[binding["node_name"]],"proxies":[],
                "physical_occurrences":sum(r["kind"]=="part" for r in final_signature),
                "source_body_signature":source_signature,"body_signature":final_signature,
                "target_matrix_mm":target_matrix_mm,"matrix_world_mm":observed_matrix,"max_pose_error_mm":error,
                "max_rotation_component_error":rotation_error,
                "stages":{"source_capture":"PASS","native_catalog_export_import":"PASS","rigid_move":"PASS", "body_topology_volume":"PASS","save_reopen":"PASS"}}
            write_receipt_once(destination/"native_receipt.json",receipt)
            return receipt
        finally:
            driver.assert_source_unchanged()
