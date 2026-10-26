import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad import icapi_runtime as runtime


class HostSelectionTests(unittest.TestCase):
    def test_default_and_explicit_host(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(runtime.selected_year(), 2023)
        with patch.dict(os.environ, {"ROCKPRO_IRONCAD_YEAR": "2027"}):
            self.assertEqual(runtime.selected_year(), 2027)

    def test_unsupported_or_malformed_version_rejected(self):
        for value in ("2024", "", "25", "2023 "):
            with patch.dict(os.environ, {"ROCKPRO_IRONCAD_YEAR": value}):
                with self.assertRaises(ValueError):
                    runtime.selected_year()

    def test_wrong_live_host_rejected(self):
        with patch.dict(os.environ, {"ROCKPRO_IRONCAD_YEAR": "2023"}):
            runtime.assert_host(SimpleNamespace(ApiVersion="25.0.0"))
            for version in ("29.0.0", "250.0", "unknown"):
                with self.assertRaises(RuntimeError):
                    runtime.assert_host(SimpleNamespace(ApiVersion=version))

    def test_missing_selected_installation_does_not_try_another(self):
        registry = MagicMock()
        registry.OpenKey.side_effect = FileNotFoundError("not installed")
        with patch.dict(sys.modules, {"winreg": registry}):
            with self.assertRaises(FileNotFoundError):
                runtime.installation_dir(2023)
        registry.OpenKey.assert_called_once_with(
            registry.HKEY_LOCAL_MACHINE, r"SOFTWARE\IronCAD\IRONCAD\25.0")

    def test_process_cannot_switch_loaded_type_library(self):
        with patch.object(runtime, "_runtime", (2023, object(), "2023")):
            with patch.dict(os.environ, {"ROCKPRO_IRONCAD_YEAR": "2027"}):
                with self.assertRaises(RuntimeError):
                    runtime.load_runtime()


if __name__ == "__main__":
    unittest.main()
