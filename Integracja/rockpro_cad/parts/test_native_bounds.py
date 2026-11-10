import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.parts.native import part_bounds


class PartBoundsCompatibilityTests(unittest.TestCase):
    def test_2023_uses_exact_body_without_transforming_local_coordinates(self):
        bounds = (-.01, -.02, -.03, .1, .2, .3)
        body = SimpleNamespace(GetBoundingBox=Mock(return_value=bounds))
        part = SimpleNamespace(GetBody=Mock(return_value=body))
        self.assertEqual(part_bounds(part), list(bounds))
        part.GetBody.assert_called_once_with(True)

    def test_newer_interface_failure_is_not_hidden_by_body_fallback(self):
        part = SimpleNamespace(GetBoundingBox=Mock(side_effect=RuntimeError('CAD read failed')),
                               GetBody=Mock())
        with self.assertRaisesRegex(RuntimeError, 'CAD read failed'):
            part_bounds(part)
        part.GetBody.assert_not_called()

    def test_newer_interface_preserves_existing_getter(self):
        part = SimpleNamespace(GetBoundingBox=Mock(return_value=range(6)), GetBody=Mock())
        self.assertEqual(part_bounds(part), list(range(6)))
        part.GetBoundingBox.assert_called_once_with(True)
        part.GetBody.assert_not_called()

    def test_missing_body_does_not_create_fictitious_zero_bounds(self):
        part = SimpleNamespace(GetBody=lambda exact: None)
        with self.assertRaises(AttributeError):
            part_bounds(part)


if __name__ == '__main__':
    unittest.main()
