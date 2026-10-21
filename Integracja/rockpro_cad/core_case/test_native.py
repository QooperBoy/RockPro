import copy
import tempfile
import unittest
from pathlib import Path
import sys
import math
from contextlib import nullcontext
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.native import NativeExecutionError, compare_measurements, execute_plan, plan_matrix, preflight_plan
from rockpro_cad.core_case.native_reader import read_poses, transform_bbox, validate_matrix


def fixture():
    return {"status": "planned", "units": "mm", "synthetic": True, "production_approved": False,
            "inventory": {"physical_ids": ["handle/1"]},
            "occurrences": [{"id": "handle/1", "family": "handles", "closed_xyz": [100, 200, 300],
                "rotation": [[0, -1, 0], [1, 0, 0], [0, 0, 1]], "shape": [20, 40, 10],
                "local_bounds": [[-10, -20, -5], [10, 20, 5]]}]}


class FakeDriver:
    def __init__(self, source):
        self.parts = []
        self.reopened = False

    def capture(self, path):
        path.write_bytes(b"captured live memory")
        return {"snapshot_path": str(path), "captured_from": "live_memory", "disk_equivalence": "not_proven"}

    def create(self, parts):
        self.parts = copy.deepcopy(parts)

    def measure(self):
        return [{"occurrence_id": p["id"], "cad_node_id": i+10, "matrix_world_mm": p["native_matrix_mm"],
                 "bbox_world_mm": p["expected_bbox_world_mm"]} for i,p in enumerate(self.parts)]

    def save_reopen(self, path):
        path.write_bytes(b"native test output")
        self.reopened = True

    def assert_source_unchanged(self):
        pass


class NativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        # Offline fake-driver tests must never contend with a live CAD writer.
        self.lock_patch = patch("rockpro_cad.core_case.native.cad_writer_lock", side_effect=lambda: nullcontext())
        self.lock_patch.start()
        self.addCleanup(self.lock_patch.stop)

    def test_column_planner_to_row_native_and_eight_corners(self):
        matrix = plan_matrix(fixture()["occurrences"][0])
        self.assertEqual(matrix[0][:3], [0, 1, 0])
        self.assertEqual(transform_bbox([-10,-20,-5,10,20,5], matrix), [80,190,295,120,210,305])

    def test_reflection_and_scale_rejected(self):
        for bad in (-1, 2):
            matrix = [[bad,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
            with self.assertRaises(ValueError):
                validate_matrix(matrix)

    def test_duplicate_unaccounted_and_fake_approved_blocked_before_cad(self):
        for mutate in (lambda p:p["occurrences"].append(p["occurrences"][0]),
                       lambda p:p["inventory"].update(physical_ids=[]),
                       lambda p:p.update(production_approved=True),
                       lambda p:p.update(status="blocked")):
            plan = fixture()
            mutate(plan)
            with self.assertRaises(ValueError):
                preflight_plan(plan)

    def test_nonfinite_bounds_and_shape_mismatch_rejected(self):
        for value in (float("nan"), float("inf"), True, 1000000):
            plan = fixture()
            plan["occurrences"][0]["local_bounds"][1][0] = value
            with self.assertRaises(ValueError):
                preflight_plan(plan)

    def test_readback_drift_and_missing_part_fail(self):
        parts = preflight_plan(fixture())
        driver = FakeDriver(None)
        driver.create(parts)
        rows = driver.measure()
        rows[0]["bbox_world_mm"][0] += 1
        with self.assertRaises(NativeExecutionError):
            compare_measurements(parts, rows)
        with self.assertRaises(NativeExecutionError):
            compare_measurements(parts, [])

    def test_orientation_uses_dimensionless_tolerance(self):
        parts = preflight_plan(fixture())
        driver = FakeDriver(None)
        driver.create(parts)
        rows = driver.measure()
        angle = math.pi/2 + 0.0001
        rows[0]["matrix_world_mm"][:3] = [[math.cos(angle),math.sin(angle),0,0],
                                           [-math.sin(angle),math.cos(angle),0,0],[0,0,1,0]]
        with self.assertRaises(NativeExecutionError):
            compare_measurements(parts,rows)

    def test_copy_receipt_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            source = Path(folder)/"source.ics"
            source.write_bytes(b"original")
            receipt = execute_plan(fixture(), output_dir=folder, source=source,
                                   operation_id="test", _adapter_factory=FakeDriver)
            self.assertTrue(receipt["passed"])
            self.assertEqual(receipt["proxies"], ["handle/1"])
            self.assertFalse(receipt["production_approved"])
            self.assertEqual(source.read_bytes(), b"original")
            self.assertNotEqual(receipt["source"]["snapshot_path"], receipt["output_path"])
            with self.assertRaises(FileExistsError):
                execute_plan(fixture(), output_dir=folder, source=source,
                             operation_id="test", _adapter_factory=FakeDriver)

    def test_failure_does_not_issue_success_receipt(self):
        class BadDriver(FakeDriver):
            def measure(self):
                rows = super().measure()
                if self.reopened:
                    rows[0]["cad_node_id"] += 1
                return rows
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            source = Path(folder)/"source.ics"
            source.write_bytes(b"original")
            with self.assertRaises(NativeExecutionError):
                execute_plan(fixture(), output_dir=folder, source=source,
                             operation_id="bad", _adapter_factory=BadDriver)
            self.assertFalse((Path(folder)/"bad"/"native_receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
