"""Copy-only native execution of explicitly synthetic case plans.

The solids are declared proxies, including hardware. A successful receipt proves
native persistence/poses of the proposal, never a catalog or mounting approval.
No caller-supplied code, attribute names or file overwrite is accepted.
"""
import copy
import json
import math
import os
from pathlib import Path
import re
import uuid

from ..cad_lock import cad_writer_lock
from ..parts.native import NativePartsAdapter, file_sha256, same_document_path
from .native_reader import NativePoseAdapter, validate_matrix, transform_bbox


class NativeExecutionError(RuntimeError):
    pass


def write_receipt_once(path, receipt):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False))
        stream.flush()
        os.fsync(stream.fileno())


def plan_matrix(part, presentation=None):
    rotation = part["rotation"]
    position = part["closed_xyz"]
    if (not isinstance(rotation, list) or len(rotation) != 3
            or any(not isinstance(r, list) or len(r) != 3 for r in rotation)
            or not isinstance(position, list) or len(position) != 3):
        raise ValueError("invalid occurrence pose")
    if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v)>100000
           for v in position):
        raise ValueError("invalid bounded occurrence position")
    # Planner rotations multiply column vectors; ICAPI uses row vectors.
    matrix = [[rotation[j][i] for j in range(3)]+[0.0] for i in range(3)]
    matrix.append([position[i]+(presentation or [0, 0, 0])[i] for i in range(3)]+[1.0])
    return validate_matrix(matrix)


def preflight_plan(plan):
    if not isinstance(plan, dict) or plan.get("status") != "planned" or plan.get("units") != "mm":
        raise ValueError("only a successful millimetre plan can execute")
    if plan.get("synthetic") is not True or plan.get("production_approved") is not False:
        raise ValueError("this executor accepts explicitly unapproved synthetic prototypes only")
    parts = copy.deepcopy(plan.get("occurrences"))
    if not isinstance(parts, list) or not 1 <= len(parts) <= 1000:
        raise ValueError("bounded occurrence list required")
    ids = [p.get("id") for p in parts]
    if any(not isinstance(i, str) or not i or len(i)>160 or any(ord(c)<32 for c in i) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique occurrence IDs required")
    inventory = plan.get("inventory", {}).get("physical_ids")
    if not isinstance(inventory, list) or len(inventory) != len(ids) or set(inventory) != set(ids):
        raise ValueError("plan physical inventory mismatch")
    # The planner marks lid occurrences through presentation positions. The
    # closed model remains the native physical artifact; view offset is separate.
    for part in parts:
        part["native_matrix_mm"] = plan_matrix(part)
        bounds = part.get("local_bounds")
        if (not isinstance(bounds, list) or len(bounds) != 2
                or any(not isinstance(row, list) or len(row) != 3 for row in bounds)
                or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v)>100000
                       for row in bounds for v in row)
                or any(bounds[1][i] <= bounds[0][i] for i in range(3))):
            raise ValueError("valid bounded local geometry required")
        shape = part.get("shape")
        if (not isinstance(shape, list) or len(shape) != 3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in shape)
                or any(abs(shape[i]-(bounds[1][i]-bounds[0][i]))>1e-6 for i in range(3))):
            raise ValueError("shape must match local geometry")
        part["expected_bbox_world_mm"] = transform_bbox(bounds[0]+bounds[1], part["native_matrix_mm"])
    return parts


def compare_measurements(expected, observed, tolerance_mm=0.003, rotation_tolerance=1e-6):
    by_id = {row["occurrence_id"]: row for row in observed}
    if len(by_id) != len(observed) or set(by_id) != {part["id"] for part in expected}:
        raise NativeExecutionError("native inventory differs from planned stable IDs")
    checks = []
    for part in expected:
        row = by_id[part["id"]]
        matrix = validate_matrix(row["matrix_world_mm"])
        bbox = row.get("bbox_world_mm")
        if (not isinstance(bbox, list) or len(bbox) != 6
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in bbox)):
            raise NativeExecutionError("invalid native bounding box: "+part["id"])
        rotation_error = max(abs(matrix[i][j]-part["native_matrix_mm"][i][j]) for i in range(3) for j in range(3))
        position_errors = [abs(matrix[3][j]-part["native_matrix_mm"][3][j]) for j in range(3)]
        bbox_errors = [abs(a-b) for a,b in zip(row["bbox_world_mm"], part["expected_bbox_world_mm"])]
        if rotation_error > rotation_tolerance or max(position_errors+bbox_errors) > tolerance_mm:
            raise NativeExecutionError("native pose or geometry mismatch: "+part["id"])
        checks.append({"occurrence_id": part["id"], "max_error_mm": max(position_errors+bbox_errors),
                       "max_rotation_component_error": rotation_error,
                       "cad_node_id": row["cad_node_id"]})
    return checks


class IronCADPrototypeDriver:
    def __init__(self, source):
        self.source = Path(source).resolve(strict=True)
        self.adapter = NativePartsAdapter.attach(self.source)
        self.api, self.base = self.adapter.api, self.adapter.base
        self.before = self.adapter.provenance()
        self.before_hash = file_sha256(self.source)
        self.scene = None
        self.output_doc = None

    def assert_source_unchanged(self):
        if self.before != self.adapter.provenance() or self.before_hash != file_sha256(self.source):
            raise NativeExecutionError("source bytes, identity or modified flag changed")

    def capture(self, path):
        self.workdir = path.parent
        self.assert_source_unchanged()
        self.adapter.document.QueryInterface(self.api.IZSceneDoc).SaveAsCopy(str(path), self.api.Z_LINKS_COPY_ALL, False)
        self.assert_source_unchanged()
        if not path.is_file():
            raise NativeExecutionError("source snapshot was not created")
        return {"path": str(self.source), "sha256_before": self.before_hash,
                "sha256_after": file_sha256(self.source), "unchanged": True,
                "live_document": self.before, "captured_from": "live_memory",
                "disk_equivalence": "not_proven" if self.before["modified"] else "saved_document",
                "snapshot_path": str(path), "snapshot_sha256": file_sha256(path)}

    def create(self, parts):
        # The SDK's primitive CreateBlockPart is E_NOTIMPL in IronCAD 2027.
        # Use the installed official .NET interop and its documented profile /
        # CreateExtrudeFeature path, rather than modifying COM registration.
        import shutil
        import subprocess
        import os
        from python_ironcad.core import install_dir
        folder = self.workdir / "sdk_bridge"
        folder.mkdir(exist_ok=False)
        vendor = Path(install_dir) / "ICAPI" / "Samples" / "C#" / "References" / "interop.ICApiIronCAD.dll"
        compiler = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
        if not vendor.is_file() or not compiler.is_file():
            raise NativeExecutionError("IronCAD 2027 official SDK interop or .NET Framework x64 compiler unavailable")
        executable = folder / "NativeSceneBridge.exe"
        bridge_source = Path(__file__).with_name("NativeSceneBridge.cs")
        build = subprocess.run([str(compiler), "/nologo", "/target:exe", "/platform:x64",
            "/out:"+str(executable), "/reference:"+str(vendor), "/reference:System.Web.Extensions.dll",
            "/reference:Microsoft.CSharp.dll", str(bridge_source)], capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if build.returncode:
            raise NativeExecutionError("Official SDK bridge compilation failed: "+(build.stdout+build.stderr)[-2000:])
        shutil.copyfile(vendor, folder / vendor.name)
        self.bridge_output = self.workdir / "case_prototype.ics"
        request = folder / "request.json"
        result = folder / "result.json"
        request.write_text(json.dumps({"source":str(self.source), "output":str(self.bridge_output),
                                       "parts":parts}, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        run = subprocess.run([str(executable),str(request),str(result)], capture_output=True, text=True,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        (folder / "bridge.log").write_text(run.stdout+run.stderr, encoding="utf-8")
        if run.returncode or not result.is_file():
            raise NativeExecutionError("Official SDK bridge failed: "+(run.stdout+run.stderr)[-2000:])
        self.bridge_result = json.loads(result.read_text(encoding="utf-8-sig"))
        if self.bridge_result.get("passed") is not True:
            raise NativeExecutionError("Official SDK bridge returned failure")
        self._reopened = False

    def measure(self):
        return self.bridge_result["reopened" if self._reopened else "before"]

    def save_reopen(self, path):
        # The fixed bridge performs save/close/reopen and separate measurements
        # inside one STA process; these observations are checked independently.
        if path != self.bridge_output or not path.is_file():
            raise NativeExecutionError("SDK output path mismatch")
        self._reopened = True


def execute_plan(plan, *, output_dir, source=None, operation_id=None, _adapter_factory=None):
    """Materialize and independently read back a new synthetic native prototype.

    The private adapter hook supports fault-injection tests; MCP cannot select it.
    Requires an explicit source to attach safely; never falls back to ActiveDoc.
    """
    parts = preflight_plan(plan)
    if source is None:
        raise ValueError("an explicit already-open source ICS is required")
    source_path = Path(source).resolve(strict=True)
    if source_path.suffix.lower() != ".ics":
        raise ValueError("source must be an ICS")
    operation_id = operation_id or uuid.uuid4().hex
    if not isinstance(operation_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", operation_id):
        raise ValueError("invalid operation ID")
    parent = Path(output_dir).resolve(strict=True)
    destination = parent / operation_id
    with cad_writer_lock():
        destination.mkdir(exist_ok=False)
        output = destination / "case_prototype.ics"
        snapshot = destination / "source_snapshot.ics"
        driver = (_adapter_factory or IronCADPrototypeDriver)(source_path)
        try:
            provenance = driver.capture(snapshot)
            driver.create(parts)
            before = driver.measure()
            compare_measurements(parts, before)
            driver.save_reopen(output)
            reopened = driver.measure()
            checks = compare_measurements(parts, reopened)
            if {p["occurrence_id"]: p["cad_node_id"] for p in before} != {p["occurrence_id"]: p["cad_node_id"] for p in reopened}:
                raise NativeExecutionError("native node IDs changed after reopening")
            driver.assert_source_unchanged()
            receipt = {"schema_version": 1, "passed": True, "operation_id": operation_id,
                       "output_path": str(output), "output_sha256": file_sha256(output),
                       "source": provenance, "source_unchanged": True,
                       "stages": {"read": "PASS", "copy": "PASS", "change_on_copy": "PASS",
                                  "measurement": "PASS", "save_reopen": "PASS"},
                       "geometry_scope": "synthetic_native_block_prototype", "production_approved": False,
                       "proxies": [p["id"] for p in parts], "catalog_reused": [],
                       "physical_occurrences": len(parts), "checks": checks,
                       "presentation": copy.deepcopy(plan.get("presentation")),
                       "measurements": reopened}
            write_receipt_once(destination / "native_receipt.json", receipt)
            return receipt
        finally:
            driver.assert_source_unchanged()
