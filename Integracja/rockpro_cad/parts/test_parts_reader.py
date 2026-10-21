"""Synthetic adapter tests: no IronCAD, customer file or geometry write."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parts.reader import ReadLimits, normalize_bbox, read_parts


def part(identifier="p", name="plate", **properties):
    return dict(id=identifier, name=name, kind="part", children=[], material="fixture material",
                properties=dict(bom_number="fixture-001", bom_description="fixture plate",
                                included=True, hidden=False,
                                bbox_raw=[-.001, .002, .003, .009, .022, .033], **properties))


def assembly(children=(), name="fixture assembly"):
    return dict(id="assembly", name=name, kind="assembly", children=list(children), material=None)


class FixtureAdapter:
    def __init__(self, children=()):
        self.scene = dict(id="scene", name="fixture scene", kind="scene", children=list(children), material=None)
        self.calls = []

    def root(self):
        self.calls.append("root")
        return self.scene

    def identity(self, node):
        self.calls.append("identity")
        return {key: node[key] for key in ("id", "name", "kind")} | {"type": "fixture." + node["kind"]}

    def child_count(self, node):
        self.calls.append("child_count")
        return len(node["children"])

    def child_at(self, node, index):
        self.calls.append("child_at")
        return node["children"][index]

    def material_name(self, node):
        self.calls.append("material")
        return node["material"]

    def part_properties(self, node):
        self.calls.append("properties")
        return node["properties"]


class PartsReaderTests(unittest.TestCase):
    def test_occurrences_remain_distinct_and_fixture_is_immutable(self):
        shared = part()
        adapter = FixtureAdapter([assembly([shared, shared]), assembly()])
        snapshot = copy.deepcopy(adapter.scene)
        events = []
        result = read_parts(adapter, event_sink=lambda event, **data: events.append((event, data)))
        self.assertFalse(result["partial"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["catalog_inference"], "none")
        self.assertEqual(result["summary"], dict(node_count=5, part_count=2, assembly_count=2,
                         empty_assembly_count=1, geometry_valid_part_count=2, error_count=0))
        rows = [row for row in result["rows"] if row["kind"] == "part"]
        self.assertEqual(rows[0]["id"], rows[1]["id"])
        self.assertEqual([row["occurrence_path"] for row in rows], [[0, 0], [0, 1]])
        self.assertEqual(rows[0]["material_cad_raw"], "fixture material")
        self.assertEqual(rows[0]["bbox_raw_unit"], "m")
        for actual, expected in zip(rows[0]["bounding_box"]["size"], [10, 20, 30]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(adapter.scene, snapshot)
        self.assertEqual([e for e, _ in events].count("node_read"), 5)
        json.dumps(result, allow_nan=False)

    def test_empty_scene_and_empty_assembly_are_successful_inventory(self):
        result = read_parts(FixtureAdapter())
        self.assertFalse(result["partial"])
        self.assertEqual(result["summary"]["node_count"], 1)
        self.assertEqual(result["summary"]["part_count"], 0)
        result = read_parts(FixtureAdapter([assembly()]))
        self.assertFalse(result["partial"])
        self.assertEqual(result["summary"]["empty_assembly_count"], 1)

    def test_parts_stop_before_modeling_features(self):
        node = part()
        node["children"] = [dict(kind="feature", name="fixture feature")]
        class PartsHaveNoOccurrenceChildren(FixtureAdapter):
            def child_count(self, value):
                if value["kind"] == "part":
                    raise AssertionError("Must not inspect part feature children")
                return super().child_count(value)
        result = read_parts(PartsHaveNoOccurrenceChildren([node]))
        self.assertFalse(result["partial"])
        self.assertEqual(result["scope"], "assembly_part_hierarchy")
        self.assertTrue(result["feature_children_not_traversed"])
        self.assertEqual(result["summary"]["node_count"], 2)
        self.assertIsNone(result["rows"][1]["children"])
        self.assertEqual(result["rows"][1]["children_scope"], "not_traversed_modeling_features")

    def test_none_root_child_and_missing_properties_are_errors(self):
        class NoRoot(FixtureAdapter):
            def root(self):
                return None
        result = read_parts(NoRoot())
        self.assertTrue(result["partial"])
        self.assertEqual(result["errors"][0]["field"], "root")
        class NoChild(FixtureAdapter):
            def child_at(self, node, index):
                return None
        result = read_parts(NoChild([part()]))
        self.assertTrue(result["partial"])
        self.assertEqual(result["errors"][0]["field"], "child[0]")
        class NoProperties(FixtureAdapter):
            def part_properties(self, node):
                return None
        result = read_parts(NoProperties([part()]))
        self.assertTrue(result["partial"])
        self.assertEqual(result["errors"][0]["field"], "part_properties")
        self.assertEqual(result["summary"]["geometry_valid_part_count"], 0)

    def test_failed_child_attempts_have_separate_budget(self):
        class ManyBadChildren(FixtureAdapter):
            def child_count(self, node):
                return 1000000
            def child_at(self, node, index):
                self.calls.append("child_at")
                raise RuntimeError("fixture unavailable child")
        adapter = ManyBadChildren()
        result = read_parts(adapter, ReadLimits(max_nodes=3))
        self.assertEqual(adapter.calls.count("child_at"), 3)
        self.assertEqual(result["summary"]["node_count"], 1)
        self.assertEqual(result["limit_reasons"], ["max_child_attempts"])
        self.assertEqual(result["summary"]["error_count"], 3)

    def test_node_depth_and_cycle_budgets_bound_adapter_calls(self):
        adapter = FixtureAdapter([part(), part(), part()])
        result = read_parts(adapter, ReadLimits(max_nodes=2))
        self.assertTrue(result["partial"])
        self.assertEqual(result["summary"]["node_count"], 2)
        self.assertEqual(adapter.calls.count("child_at"), 1)
        self.assertEqual(result["limit_reasons"], ["max_nodes"])
        adapter = FixtureAdapter([assembly([part()])])
        result = read_parts(adapter, ReadLimits(max_depth=1))
        self.assertEqual(result["summary"]["node_count"], 2)
        self.assertEqual(result["limit_reasons"], ["max_depth"])
        cyclic = assembly()
        cyclic["children"] = [cyclic]
        result = read_parts(FixtureAdapter([cyclic]), ReadLimits(max_depth=4))
        self.assertEqual(result["summary"]["node_count"], 5)
        self.assertEqual(result["limit_reasons"], ["max_depth"])

    def test_time_budget_is_deterministic_and_explicitly_cooperative(self):
        adapter = FixtureAdapter([part()])
        tick = iter(range(100))
        result = read_parts(adapter, ReadLimits(max_seconds=.5), clock=lambda: next(tick))
        self.assertEqual(result["limit_reasons"], ["max_seconds"])
        self.assertTrue(result["partial"])
        self.assertEqual(adapter.calls, [])
        self.assertEqual(result["time_limit_kind"], "cooperative_between_adapter_calls")

    def test_optional_read_failure_is_per_field_and_does_not_hide_siblings(self):
        class FailingMaterial(FixtureAdapter):
            def material_name(self, node):
                if node["kind"] == "part":
                    raise RuntimeError("fixture read failure")
                return None
        result = read_parts(FailingMaterial([part(), part()]))
        self.assertTrue(result["partial"])
        self.assertEqual(result["summary"]["part_count"], 2)
        self.assertEqual(result["summary"]["geometry_valid_part_count"], 2)
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual([e["field"] for e in result["errors"]], ["material", "material"])
        self.assertIsNone(result["rows"][1]["material_cad_raw"])
        self.assertEqual(len(result["rows"][1]["errors"]), 1)

    def test_child_and_root_failures_are_reported_honestly(self):
        class BrokenChild(FixtureAdapter):
            def child_at(self, node, index):
                if index == 0:
                    raise RuntimeError("fixture missing child")
                return super().child_at(node, index)
        result = read_parts(BrokenChild([part(), part()]))
        self.assertTrue(result["partial"])
        self.assertEqual(result["summary"]["part_count"], 1)
        self.assertEqual(result["errors"][0]["field"], "child[0]")
        class BrokenRoot(FixtureAdapter):
            def root(self):
                raise RuntimeError("fixture no scene")
        result = read_parts(BrokenRoot())
        self.assertTrue(result["partial"])
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["errors"][0]["field"], "root")

    def test_invalid_bbox_leaves_raw_evidence_but_no_valid_dimensions(self):
        value = part()
        value["properties"]["bbox_raw"] = [0, 0, 0, float("nan"), 1, 1]
        result = read_parts(FixtureAdapter([value]))
        row = result["rows"][1]
        self.assertTrue(result["partial"])
        self.assertIsNone(row["bbox_raw"][3])
        self.assertFalse(row["bounding_box"]["valid"])
        self.assertIsNone(row["bounding_box"]["size"])
        self.assertEqual(result["summary"]["geometry_valid_part_count"], 0)
        json.dumps(result, allow_nan=False)

    def test_bounding_box_validation_and_native_units(self):
        valid = normalize_bbox([-1, -2, -3, 1, 2, 3])
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["minimum"], [-1000, -2000, -3000])
        self.assertEqual(valid["maximum"], [1000, 2000, 3000])
        self.assertEqual(valid["size"], [2000, 4000, 6000])
        self.assertEqual(valid["frame"], "part_local")
        for invalid in (None, [], [0] * 5, [0] * 7, [False, 0, 0, 1, 1, 1],
                        ["0", 0, 0, 1, 1, 1], [0, 0, 0, math.inf, 1, 1],
                        [0, 0, 0, -1, 1, 1], [0, 0, 0, 0, 1, 1],
                        [-1e30] * 3 + [1e30] * 3):
            with self.subTest(raw=invalid):
                box = normalize_bbox(invalid)
                self.assertFalse(box["valid"])
                for field in ("minimum", "maximum", "size"):
                    self.assertIsNone(box[field])

    def test_limits_validation_and_audit_failure_propagation(self):
        for values in ({"max_nodes": 0}, {"max_nodes": True}, {"max_depth": -1},
                       {"max_depth": 129}, {"max_seconds": 0}, {"max_seconds": True},
                       {"max_seconds": float("nan")}, {"max_seconds": float("inf")}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                ReadLimits(**values)
        with self.assertRaises(TypeError):
            read_parts(FixtureAdapter(), limits={"max_nodes": 1})
        def failed_log(*args, **kwargs):
            raise OSError("fixture log unavailable")
        with self.assertRaises(OSError):
            read_parts(FixtureAdapter([part()]), event_sink=failed_log)


if __name__ == "__main__":
    unittest.main()
