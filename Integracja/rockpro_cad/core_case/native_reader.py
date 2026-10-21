"""Read-only pose evidence for an explicitly selected, already open source.

ICAPI matrices use row vectors: world = local * rotation + translation.
The matrix is read from ICAPI, never reconstructed from a bounding box.
This module does not promote an inventory or infer mounting approvals.
"""
import itertools
import math
import time
from pathlib import Path

from ..parts.native import NativePartsAdapter, file_sha256
from ..parts.reader import ReadLimits, normalize_bbox


def validate_matrix(matrix, tolerance=1e-6, *, allow_reflection=False):
    if (not isinstance(matrix, list) or len(matrix) != 4
            or any(not isinstance(r, list) or len(r) != 4 for r in matrix)
            or any(type(v) not in (float, int) or not math.isfinite(v)
                   for row in matrix for v in row)):
        raise ValueError("expected finite 4x4 ICAPI matrix")
    if any(abs(matrix[i][3]) > tolerance for i in range(3)) or abs(matrix[3][3]-1) > tolerance:
        raise ValueError("invalid homogeneous row-vector matrix")
    rotation = matrix[:3]
    for i in range(3):
        for j in range(3):
            dot = sum(rotation[i][k]*rotation[j][k] for k in range(3))
            if abs(dot-(1 if i == j else 0)) > tolerance:
                raise ValueError("non-rigid ICAPI transform")
    determinant = sum(rotation[0][i] * (rotation[1][(i+1)%3]*rotation[2][(i+2)%3]
        - rotation[1][(i+2)%3]*rotation[2][(i+1)%3]) for i in range(3))
    if (abs(abs(determinant)-1) if allow_reflection else abs(determinant-1)) > tolerance:
        raise ValueError("improper ICAPI rotation")
    return matrix


def transform_bbox(box, matrix):
    """World AABB from all eight local corners; both inputs are millimetres."""
    validate_matrix(matrix)
    points = [[sum(p[k]*matrix[k][j] for k in range(3))+matrix[3][j]
               for j in range(3)]
              for p in itertools.product(*zip(box[:3], box[3:]))]
    return [min(p[j] for p in points) for j in range(3)] + [max(p[j] for p in points) for j in range(3)]


class NativePoseAdapter(NativePartsAdapter):
    def matrix(self, node, global_space):
        scene_element = node.QueryInterface(self.api.IZSceneElement)
        value = (scene_element.GetTransformToGlobal() if global_space
                 else scene_element.GetTransformToParent())
        matrix = [[float(value.GetValue(i, j)) for j in range(4)] for i in range(4)]
        for j in range(3):
            matrix[3][j] *= 1000
        return matrix

    def bbox(self, node, kind):
        interface = self.api.IZAssembly if kind == "assembly" else self.api.IZPart
        return normalize_bbox(list(node.QueryInterface(interface).GetBoundingBox(True)))


def read_poses(adapter, limits=None):
    limits = limits or ReadLimits(max_seconds=180)
    start = time.monotonic()
    rows, errors = [], []

    def walk(node, occurrence, names):
        if len(rows) >= limits.max_nodes or len(occurrence) > limits.max_depth or time.monotonic()-start > limits.max_seconds:
            raise RuntimeError("pose read budget exceeded")
        identity = adapter.identity(node)
        row = {key: identity.get(key) for key in ("id", "name", "kind", "type")}
        row.update(occurrence_path=list(occurrence), path=names+[identity.get("name")], errors=[])
        rows.append(row)
        if row["kind"] != "scene":
            for global_space, field in ((True, "matrix_world_mm"), (False, "matrix_parent_mm")):
                try:
                    matrix = adapter.matrix(node, global_space)
                    row[field+"_raw"] = matrix
                    row[field] = validate_matrix(matrix)
                except Exception as exc:
                    error = {"occurrence_path": list(occurrence), "field": field, "type": type(exc).__name__, "message": str(exc)[:500]}
                    row["errors"].append(error)
                    errors.append(error)
            try:
                box = adapter.bbox(node, row["kind"])
                row["bounding_box_local"] = box
                if not box["valid"]:
                    raise ValueError("invalid local bbox: "+box.get("reason", "unknown"))
                if box["valid"] and "matrix_world_mm" in row:
                    row["bbox_world_mm"] = transform_bbox(box["minimum"]+box["maximum"], row["matrix_world_mm"])
            except Exception as exc:
                error = {"occurrence_path": list(occurrence), "field": "bounding_box_local", "type": type(exc).__name__, "message": str(exc)[:500]}
                row["errors"].append(error)
                errors.append(error)
        if row["kind"] in ("scene", "assembly"):
            row["children"] = adapter.child_count(node)
            for index in range(row["children"]):
                walk(adapter.child_at(node, index), occurrence+[index], row["path"])

    walk(adapter.root(), [], [])
    return {"schema_version": 1, "operation": "core_case.read_poses", "read_only": True,
            "matrix_convention": "row-vector; translation row 3; all translations and boxes mm",
            "mounting_approval": "not_inferred", "rows": rows, "errors": errors,
            "status": "partial" if errors else "complete"}


def inspect_source_poses(source, limits=None, *, adapter_factory=None):
    source = Path(source).resolve(strict=True)
    if not source.is_file() or source.suffix.lower() != ".ics":
        raise ValueError("source must be an existing ICS")
    before = file_sha256(source)
    adapter = (adapter_factory or NativePoseAdapter.attach)(source)
    provenance_before = adapter.provenance()
    try:
        result = read_poses(adapter, limits)
    finally:
        after = file_sha256(source)
        provenance_after = adapter.provenance()
        if after != before or provenance_after != provenance_before:
            raise RuntimeError("source identity, flags or disk bytes changed during pose audit")
    result["source"] = {"path": str(source), "sha256_before": before, "sha256_after": after, "unchanged": True}
    result["cad_document"] = {"before": provenance_before, "after": provenance_after,
                              "disk_equivalence": "not_proven" if provenance_before["modified"] else "saved_document"}
    if provenance_before["modified"]:
        result["status"] = "partial"
    return result
