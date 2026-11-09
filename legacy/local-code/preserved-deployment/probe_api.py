"""Read-only IronCAD connectivity probe; never opens or saves project files."""
import json
import traceback
from pathlib import Path

report = {}
try:
    from python_ironcad import IronCAD
    import comtypes.client
    from comtypes.automation import IDispatch
    from python_ironcad.core import install_dir
    comtypes.client.GetModule(str(Path(install_dir) / 'bin' / 'IronCad.tlb'))
    report['import'] = 'ok'
    cad = IronCAD()
    cad.attach()
    report['connection'] = 'attached'
    report['automation_interface'] = str(type(cad.comobject))
    if not hasattr(cad.comobject, 'ZIronCADApp'):
        cad.comobject = comtypes.client.GetBestInterface(cad.comobject.QueryInterface(IDispatch))
    app = cad.GetIZBaseApp()
    report['base_app'] = str(type(app))
    doc = app.ActiveDoc
    report['active_document_present'] = bool(doc)
    report['active_document_interface'] = str(type(doc))
    report['success'] = True
except Exception:
    report['success'] = False
    report['error'] = traceback.format_exc()
finally:
    output = Path(__file__).with_name('probe_result.json')
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=True), flush=True)
