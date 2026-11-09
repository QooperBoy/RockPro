"""Local attach-only adapter. No automatic application launch."""
import ctypes as ct
from pathlib import Path
import comtypes.client
from comtypes import HRESULT
from comtypes.automation import IDispatch
from python_ironcad import ICAPI
WALK_WARNINGS = []

def connect(source):
    source = Path(source).resolve()
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
        if name.lower() == str(source).lower():
            legacy = comtypes.client.GetBestInterface(rot.GetObject(moniker).QueryInterface(IDispatch))
            base = legacy.Application.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
            doc = base.GetOpenDocByName(str(source))
            if Path(doc.Name).name.lower() != source.name.lower():
                raise RuntimeError('Requested source must be active; refusing another document')
            return legacy, base, doc
    raise RuntimeError(f'Source not open in COM ROT: {source}')

def walk(element, path=()):
    element = element.QueryInterface(ICAPI.IZElement)
    current = path + ((element.Name,) if element.Name else ())
    yield current, element
    try:
        count = element.GetChildrenCount()
    except Exception as exc:
        WALK_WARNINGS.append({'path': list(current), 'error': str(exc)})
        return
    if count == 0:
        return
    children = element.GetChildrenZArray()
    for i in range(children.Count()):
        yield from walk(children.Get(i), current)

def parameters(element):
    manager = element.QueryInterface(ICAPI.IZSceneElement).ParameterMgr
    return [manager.GetParameter(i) for i in range(manager.Count)]

def parameter_data(p):
    return dict(id=p.Id, name=p.Name, type=p.Type, expression=p.Expression, value=p.Value)

def find(scene, target):
    current = scene.GetTopElement()
    for name in target:
        children = current.GetChildrenZArray()
        matches = []
        for i in range(children.Count()):
            element = children.Get(i).QueryInterface(ICAPI.IZElement)
            if element.Name == name:
                matches.append(element)
        if len(matches) != 1:
            raise ValueError(f'Expected unique child {name}, found {len(matches)}')
        current = matches[0]
    return current
