import json
import subprocess
import sys
import unittest
import tempfile
import types
from pathlib import Path
from unittest.mock import patch, MagicMock
import worker
import server


class Boundaries(unittest.TestCase):
    def test_copy_failure_records_stage_even_when_com_disconnects(self):
        values = dict(RP_Length=100, RP_Depth=100, RP_BaseHeight=50,
                      RP_LidHeight=20, RP_Thickness=10, RP_DisplayGap=0)
        before = {n: {"mm": v, "expression": str(v)+" mm"} for n, v in values.items()}
        scene, legacy, app, doc = (MagicMock() for _ in range(4))
        legacy.Saved = True
        doc.QueryInterface.return_value = scene
        scene.SaveAsCopy.side_effect = RuntimeError("snapshot disconnected")
        adapter = types.SimpleNamespace(connect=lambda path: (legacy, app, doc),
                                        ICAPI=MagicMock())
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root = Path(temporary)
            source = root/"source.ics"
            source.write_bytes(b"original")
            with patch.dict(sys.modules, {"ironcad_adapter": adapter}), \
                 patch.object(worker, "ROOT", root), \
                 patch.object(worker, "source_path", return_value=source), \
                 patch.object(worker, "load_manifest", return_value={}), \
                 patch.object(worker, "measure", return_value={}), \
                 patch.object(worker, "snapshot", side_effect=[before, RuntimeError("COM unavailable")]):
                with self.assertRaisesRegex(RuntimeError, "snapshot disconnected"):
                    worker.change_dimensions_on_copy({"RP_Length": 110})
            reports = list(root.glob("rockpro_cad/revisions/*/report.json"))
            self.assertEqual(len(reports), 1)
            report = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(report["stage"], "snapshot")
            self.assertEqual(report["error"]["message"], "snapshot disconnected")
            self.assertFalse(report["passed"])
            self.assertFalse(report["source_unchanged"])
            self.assertEqual(source.read_bytes(), b"original")
            doc.Save.assert_not_called()
            app.OpenFile.assert_not_called()

    def test_changes_reject_injection_and_invalid_numbers(self):
        for changes in ({}, {"evil": 2}, {"RP_Length": True}, {"RP_Length": "1000 mm"},
                        {"RP_Length": float("nan")}, {"RP_Length": float("inf")},
                        {"RP_Thickness": 0}, {"RP_DisplayGap": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                worker.validate_changes(changes)

    def test_impossible_geometry(self):
        values = dict(RP_Length=100, RP_Depth=100, RP_BaseHeight=50, RP_LidHeight=20,
                      RP_Thickness=10, RP_DisplayGap=0)
        worker.validate_dimensions(values)
        for update in ({"RP_Length":20}, {"RP_Depth":19}, {"RP_LidHeight":10}):
            with self.assertRaises(ValueError):
                worker.validate_dimensions(values | update)

    def test_unknown_dispatch_argument_rejected_before_com(self):
        with self.assertRaises(ValueError):
            worker.dispatch("inspect_project", {"code": "anything"})

    def test_source_extension_rejected(self):
        with self.assertRaises(ValueError):
            worker.source_path(__file__)

    def test_mcp_call_errors_are_tool_errors(self):
        with patch.object(server, "dispatch", side_effect=ValueError("unsupported")):
            reply = server.handle({"id":3, "method":"tools/call",
                                   "params":{"name":"inspect_project","arguments":{}}})
        self.assertTrue(reply["result"]["isError"])

    def test_real_stdio_handshake_and_listing(self):
        requests = [{"jsonrpc":"2.0", "id":1, "method":"initialize",
                     "params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}},
                    {"jsonrpc":"2.0","method":"notifications/initialized"},
                    {"jsonrpc":"2.0","id":2,"method":"tools/list"}]
        run = subprocess.run([sys.executable, str(Path(__file__).with_name("server.py"))],
                             input="\n".join(map(json.dumps,requests))+"\n",
                             text=True, encoding="utf-8", capture_output=True, check=True)
        replies = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("get_history", {t["name"] for t in replies[1]["result"]["tools"]})


if __name__ == "__main__":
    unittest.main()
