"""Bounded read-only inventory over an injectable CAD adapter.

The adapter supplies root(), identity(node), child_count(node),
child_at(node, index), part_properties(node), and material_name(node).
identity returns id/name/type/kind (scene/assembly/part/feature/unknown).
part_properties returns native BOM fields and bbox_raw in metres, min XYZ,
max XYZ, in part-local coordinates. Neither names nor material imply a
catalog item, stock material, complete product, or purchase quantity.

Time limits are cooperative between adapter calls. A blocked COM call cannot
be interrupted safely; this is not a hard wall-clock timeout for IronCAD.
"""

from dataclasses import asdict, dataclass
import math
import time


@dataclass(frozen=True)
class ReadLimits:
    max_depth: int = 12
    max_nodes: int = 10000
    max_seconds: float = 30.0

    def __post_init__(self):
        for name, maximum in (("max_depth", 128), ("max_nodes", 100000)):
            value = getattr(self, name)
            minimum = 0 if name == "max_depth" else 1
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
        if (isinstance(self.max_seconds, bool)
                or not isinstance(self.max_seconds, (int, float))
                or not math.isfinite(self.max_seconds)
                or not 0 < self.max_seconds <= 3600):
            raise ValueError("max_seconds must be finite and in (0, 3600]")


def normalize_bbox(raw):
    """Validate six metre min/max coordinates; never expose invalid dimensions."""
    result = {"valid": False, "unit": "mm", "frame": "part_local",
              "minimum": None, "maximum": None, "size": None}
    if not isinstance(raw, (list, tuple)) or len(raw) != 6:
        result["reason"] = "expected_six_coordinates"
        return result
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) for v in raw):
        result["reason"] = "nonfinite_or_nonnumeric"
        return result
    # IronCAD uses +/-1e30 for an unavailable wire/import bounding box.
    if any(abs(v) >= 1e29 for v in raw):
        result["reason"] = "unavailable_sentinel"
        return result
    size = [(raw[i + 3] - raw[i]) * 1000 for i in range(3)]
    if any(not math.isfinite(v) or v <= 0 for v in size):
        result["reason"] = "nonpositive_extent"
        return result
    result.update(valid=True, minimum=[v * 1000 for v in raw[:3]],
                  maximum=[v * 1000 for v in raw[3:]], size=size)
    return result


class _BudgetExpired(Exception):
    pass


def read_parts(adapter, limits=None, event_sink=None, *, clock=time.monotonic):
    """Read occurrence rows, retaining per-field failures and partial status.

    event_sink(event, **summary) may record summarized local diagnostics.
    Its failures propagate: a failed audit must not masquerade as success.
    occurrence_path is an index path, independent of duplicate/blank names;
    pair it with the document/source hash for identity outside this result.
    """
    limits = limits or ReadLimits()
    if not isinstance(limits, ReadLimits):
        raise TypeError("limits must be ReadLimits")
    start = clock()
    rows, errors, reasons = [], [], []

    def emit(event, **summary):
        if event_sink:
            event_sink(event, **summary)

    def limit(reason):
        if reason not in reasons:
            reasons.append(reason)
            emit("limit_reached", node_count=len(rows))

    def check_time():
        if clock() - start >= limits.max_seconds:
            limit("max_seconds")
            raise _BudgetExpired

    def failure(row, field, exc):
        entry = {"occurrence_path": row["occurrence_path"] if row else [],
                 "field": field, "type": type(exc).__name__,
                 "message": str(exc)[:1000]}
        errors.append(entry)
        if row is not None:
            row["errors"].append(entry)
        emit("read_error", error_count=len(errors), node_count=len(rows))

    def call(row, field, fn):
        check_time()
        try:
            value = fn()
        except Exception as exc:
            failure(row, field, exc)
            return None
        check_time()
        return value

    def inspect(node, parent_path, occurrence, depth):
        row = {"id": None, "name": None, "type": None, "kind": "unknown",
               "path": list(parent_path), "occurrence_path": list(occurrence),
               "depth": depth, "children": None, "material_cad_raw": None,
               "errors": []}
        rows.append(row)
        ident = call(row, "identity", lambda: adapter.identity(node))
        if ident is not None:
            for key in ("id", "name", "type", "kind"):
                if key in ident:
                    row[key] = ident[key]
            for error in ident.get("_read_errors", []):
                failure(row, error["field"], RuntimeError(error["message"]))
        row["path"] = list(parent_path) + [row["name"]]
        # Parts own modeling features, not further BOM occurrences. Querying
        # feature child counts also fails for many valid imported wire parts.
        traverse = row["kind"] in ("scene", "assembly")
        row["children_scope"] = "occurrences" if traverse else "not_traversed_modeling_features"
        error_count = len(errors)
        count = call(row, "children", lambda: adapter.child_count(node)) if traverse else None
        if traverse and count is None and len(errors) == error_count:
            failure(row, "children", ValueError("adapter returned no child count"))
        if count is not None:
            if type(count) is int and count >= 0:
                row["children"] = count
            else:
                failure(row, "children", ValueError("invalid child count"))
        if row["kind"] == "unknown":
            failure(row, "kind", ValueError("unsupported element kind; children not traversed"))
        row["material_cad_raw"] = call(row, "material", lambda: adapter.material_name(node))
        if row["kind"] == "part":
            error_count = len(errors)
            props = call(row, "part_properties", lambda: adapter.part_properties(node))
            if props is None and len(errors) == error_count:
                failure(row, "part_properties", ValueError("adapter returned no part properties"))
            if props is not None:
                for key in ("bom_number", "bom_description", "included", "hidden"):
                    row[key] = props.get(key)
                for error in props.get("_read_errors", []):
                    failure(row, error["field"], RuntimeError(error["message"]))
                raw = props.get("bbox_raw")
                # JSON cannot carry NaN/Infinity; null retains an explicit missing value.
                row["bbox_raw"] = [v if isinstance(v, (int, float)) and math.isfinite(v)
                                   else None for v in raw] if isinstance(raw, (list, tuple)) else None
                row["bbox_raw_unit"] = "m"
                row["bounding_box"] = normalize_bbox(raw)
                if not row["bounding_box"]["valid"]:
                    failure(row, "bounding_box", ValueError(row["bounding_box"]["reason"]))
        emit("node_read", node_count=len(rows))
        return row

    # Stack holds one frame per depth, never a list of all unvisited children.
    stack = []
    child_attempts = 0
    try:
        root = call(None, "root", adapter.root)
        if root is None and not errors:
            failure(None, "root", ValueError("adapter returned no root"))
        if root is not None:
            row = inspect(root, (), (), 0)
            stack.append([root, row, 0])
        while stack:
            check_time()
            node, row, index = stack[-1]
            count = row["children"]
            if count is None or index >= count:
                stack.pop()
                continue
            if row["depth"] >= limits.max_depth:
                limit("max_depth")
                stack.pop()
                continue
            if len(rows) >= limits.max_nodes:
                limit("max_nodes")
                break
            if child_attempts >= limits.max_nodes:
                limit("max_child_attempts")
                break
            stack[-1][2] += 1
            child_attempts += 1
            error_count = len(errors)
            child = call(row, f"child[{index}]", lambda: adapter.child_at(node, index))
            if child is None:
                if len(errors) == error_count:
                    failure(row, f"child[{index}]", ValueError("adapter returned no child"))
                continue
            child_row = inspect(child, row["path"], row["occurrence_path"] + [index], row["depth"] + 1)
            stack.append([child, child_row, 0])
    except _BudgetExpired:
        pass
    parts = [r for r in rows if r["kind"] == "part"]
    summary = {"node_count": len(rows), "part_count": len(parts),
               "assembly_count": sum(r["kind"] == "assembly" for r in rows),
               "empty_assembly_count": sum(r["kind"] == "assembly" and r["children"] == 0 for r in rows),
               "geometry_valid_part_count": sum(bool(r.get("bounding_box", {}).get("valid")) for r in parts),
               "error_count": len(errors)}
    return {"schema_version": 1, "operation": "parts.inspect", "read_only": True,
            "rows": rows, "errors": errors, "partial": bool(errors or reasons),
            "limit_reasons": reasons, "limits": asdict(limits), "summary": summary,
            "duration_ms": round((clock() - start) * 1000, 3),
            "scope": "assembly_part_hierarchy", "feature_children_not_traversed": True,
            "bbox_validation": "numeric_local_aabb_only_not_geometry_validation",
            "catalog_inference": "none", "time_limit_kind": "cooperative_between_adapter_calls",
            "time_limit_scope": "traversal_only_excludes_attach_and_file_hashing"}
