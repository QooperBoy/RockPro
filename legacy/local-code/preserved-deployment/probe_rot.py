"""Enumerate only CAD-related Running Object Table entries; no mutations."""
import ctypes as ct
import json
import comtypes.client
from comtypes.automation import IDispatch
from python_ironcad import ICAPI
from comtypes import HRESULT

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
matches = []
total = 0
while True:
    moniker, count = enum.RemoteNext(1)
    if not count:
        break
    total += 1
    name = moniker.GetDisplayName(ctx, None)
    if any(s in name.lower() for s in ('iron', '.ics', '0002c5')):
        matches.append(name)
        obj = rot.GetObject(moniker)
        for iface in (ICAPI.IZDoc, ICAPI.IZSceneDoc):
            try:
                doc = obj.QueryInterface(iface)
                print('INTERFACE', iface.__name__, 'OK')
            except Exception as exc:
                print('INTERFACE', iface.__name__, str(exc))
        try:
            dispatch = comtypes.client.GetBestInterface(obj.QueryInterface(IDispatch))
            print('AUTOMATION', type(dispatch))
            print('MEMBERS', [n for n in dir(type(dispatch)) if not n.startswith('_')][:80])
            app = dispatch.Application
            print('APPLICATION', type(app))
            print('DOC_NAME', ascii(dispatch.Name))
            print('DOC_PATH', ascii(dispatch.FullName))
            print('DOC_SAVED', dispatch.Saved)
            shape = dispatch.Shape
            raw_shape = shape._comobj
            ti_shape = raw_shape.GetTypeInfo(0)
            attr_shape = ti_shape.GetTypeAttr()
            print('SHAPE_MEMBERS', [ti_shape.GetDocumentation(ti_shape.GetFuncDesc(i).memid)[0] for i in range(attr_shape.cFuncs)])
            for label, target in [('DOCUMENT', dispatch), ('NEW_APP', app.ZIronCADApp)]:
                raw = target._comobj if hasattr(target, '_comobj') else target
                ti = raw.GetTypeInfo(0)
                attr = ti.GetTypeAttr()
                names = [ti.GetDocumentation(ti.GetFuncDesc(i).memid)[0] for i in range(attr.cFuncs)]
                print(label, ti.GetDocumentation(-1)[0], names)
            base = app.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
            print('BASE_APP', type(base))
            active = base.ActiveDoc
            scene = active.QueryInterface(ICAPI.IZSceneDoc)
            root = scene.GetTopElement()
            print('ROOT', root.Name, 'CHILDREN', root.GetChildrenCount())
        except Exception:
            import traceback
            traceback.print_exc()
print(json.dumps({'entries': total, 'cad_entries': matches}, ensure_ascii=True, indent=2))
