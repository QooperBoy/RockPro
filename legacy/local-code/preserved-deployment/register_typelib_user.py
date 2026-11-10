"""Register installed IronCAD type library for current user, no DLL installation."""
import ctypes
from pathlib import Path
from comtypes import HRESULT, typeinfo
from python_ironcad.core import install_dir

register = ctypes.OleDLL('oleaut32').RegisterTypeLibForUser
register.argtypes = [ctypes.POINTER(typeinfo.ITypeLib), ctypes.c_wchar_p, ctypes.c_wchar_p]
register.restype = HRESULT
for filename in ['ICApiIronCAD.tlb', 'ICApiFoundation.tlb', '3iICApiIronCADApp.dll', '3iICApiDrawing.dll', '3iICApiCore.dll', '3iICApiBase.dll']:
    path = str(Path(install_dir) / 'bin' / filename)
    lib = typeinfo.LoadTypeLibEx(path, 0)
    print(filename, lib.GetDocumentation(-1), flush=True)
    register(lib, path, str(Path(path).parent))
    print('Registered for current user:', path, flush=True)
