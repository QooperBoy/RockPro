"""Inject failures after opening owned copies; original must never be closed."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import worker


class WorkerCleanupTests(unittest.TestCase):
    def test_failure_preserves_modified_copy_and_original_for_each_phase(self):
        for failure in ('regenerate', 'measure', 'save', 'reopen_measure', 'recovery', 'silent_recovery'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); source=root/'source.ics'; source.write_bytes(b'original')
                values={n: {'mm': 10 if n=='RP_Thickness' else 300, 'expression': 'original'} for n in worker.NAMES}
                copies=[]; recovered=[]
                class Doc:
                    def __init__(self, name, original=False):
                        self.Name=str(name); self.Modified=not original; self.original=original; self.closed=False
                        self.ParameterMgr=SimpleNamespace(GetParameterByName=lambda n: SimpleNamespace(Expression='300 mm'))
                    def QueryInterface(self, api): return self
                    def SaveAsCopy(self, path, *args):
                        if not self.original:
                            if failure=='recovery': raise RuntimeError('recovery refused')
                            recovered.append(path)
                        Path(path).write_bytes(b'preserved')
                    def SaveAs(self, path, *args):
                        if failure=='silent_recovery':
                            Path(path).write_bytes(b'invalid partial output'); return
                        self.SaveAsCopy(path,*args); self.Name=path; self.Modified=False
                    def GetTopElement(self): return self
                    def RegenerateParts(self, *args):
                        if failure=='regenerate': raise RuntimeError('regenerate failed')
                    def Update(self): pass
                    def Save(self):
                        if failure=='save': raise RuntimeError('save failed')
                        self.Modified=False
                    def Close(self): self.closed=True
                original=Doc(source,True)
                def open_copy(path,*args):
                    d=Doc(path); copies.append(d); return d
                calls=[]
                def measure(scene,manifest):
                    calls.append(scene)
                    if (len(calls)==2 and failure in ('measure','recovery','silent_recovery')) or (len(calls)==3 and failure=='reopen_measure'):
                        raise RuntimeError('measurement failed')
                    return {'measurements': {'parameters_mm': {n:v['mm'] for n,v in values.items()}}}
                api=SimpleNamespace(IZSceneDoc=object(), IZAssembly=object(), Z_LINKS_COPY_ALL=0)
                adapter=SimpleNamespace(ICAPI=api, connect=lambda p:(SimpleNamespace(Saved=True),SimpleNamespace(OpenFile=open_copy),original))
                with patch.dict(sys.modules,ironcad_adapter=adapter), patch.object(worker,'ROOT',root), \
                     patch.object(worker,'load_manifest',return_value={}), patch.object(worker,'snapshot',return_value=values), \
                     patch.object(worker,'measure',side_effect=measure):
                    with self.assertRaises(RuntimeError): worker._change_dimensions_on_copy({'RP_Length':350},str(source))
                self.assertFalse(original.closed)
                self.assertEqual(source.read_bytes(),b'original')
                self.assertTrue(copies)
                if failure in ('recovery','silent_recovery'):
                    self.assertFalse(copies[-1].closed)
                else:
                    self.assertTrue(all(d.closed for d in copies))
                    self.assertTrue(recovered)
                report=json.loads(next(root.rglob('report.json')).read_text())
                self.assertFalse(report['passed'])
                self.assertTrue(report['source_unchanged'])
                self.assertIn('error',report)
