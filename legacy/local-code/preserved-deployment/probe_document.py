"""Read-only connection to an already open ICS through the COM ROT."""
import ctypes as ct
import json
from pathlib import Path
from datetime import datetime, timezone
import comtypes.client
from comtypes import HRESULT
from comtypes.automation import IDispatch
from python_ironcad import ICAPI

report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'documents': []}
ole = ct.OleDLL('ole32')
rot = ct.POINTER(ICAPI.IRunningObjectTable)()
ctx = ct.POINTER(ICAPI.IBindCtx)()
ole.GetRunningObjectTable.argtypes = [ct.c_ulong, ct.POINTER(type(rot))]
ole.GetRunningObjectTable.restype = HRESULT
ole.CreateBindCtx.argtypes = [ct.c_ulong, ct.POINTER(type(ctx))]
ole.CreateBindCtx.restype = HRESULT
ole.GetRunningObjectTable(0, ct.byref(rot))
ole.CreateBindCtx(0, ct.byref(ctx))
enum = rot.EnumRunning()
while True:
    moniker, count = enum.RemoteNext(1)
    if not count:
        break
    name = moniker.GetDisplayName(ctx, None)
    if not name.lower().endswith('.ics'):
        continue
    item = {'rot_path': name}
    report['documents'].append(item)
    try:
        doc = comtypes.client.GetBestInterface(rot.GetObject(moniker).QueryInterface(IDispatch))
        item.update(name=doc.Name, path=doc.FullName, saved=bool(doc.Saved), automation_read=True)
        try:
            shape = doc.Shape
            item['root_name'] = shape.Name
            children = shape.ChildShapes
            item['root_child_count'] = children.Count
            item['root_children'] = [children.Item(i).Name for i in range(1, min(children.Count, 20)+1)]
        except Exception as exc:
            item['shape_read_error'] = str(exc)
        try:
            new_app = doc.Application.ZIronCADApp
            base = new_app.QueryInterface(ICAPI.IZBaseApp)
            item['icapi_read'] = bool(base.ActiveDoc)
        except Exception as exc:
            item['icapi_read'] = False
            item['icapi_error'] = str(exc)
    except Exception as exc:
        item['automation_read'] = False
        item['error'] = str(exc)
report['success'] = any(d.get('automation_read') for d in report['documents'])
Path(__file__).with_name('document_probe_result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True, indent=2))
