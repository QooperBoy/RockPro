"""Register installed ICAPI COM metadata for this user only. Run before host restart."""
import ctypes as ct
import winreg
from pathlib import Path
from comtypes import HRESULT, typeinfo

def repair():
    key=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\IronCAD\IRONCAD\29.0")
    install=Path(winreg.QueryValueEx(key,"InstallDir")[0]);key.Close()
    folder=install/"bin"
    files=["3iICApiIronCADApp.dll","3iICApiDrawing.dll","3iICApiCore.dll","3iICApiBase.dll"]
    for f in files+["ICApiFoundation.tlb","ICApiIronCAD.tlb"]:
        if not (folder/f).is_file():raise FileNotFoundError(folder/f)
    import os
    with os.add_dll_directory(str(folder)):
        adv=ct.WinDLL("advapi32")
        adv.RegOverridePredefKey.argtypes=[ct.c_void_p,ct.c_void_p]
        adv.RegOverridePredefKey.restype=ct.c_long
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r"Software\Classes") as classes:
            code=adv.RegOverridePredefKey(ct.c_void_p(-2147483648),ct.c_void_p(int(classes)))
            if code:raise OSError(code,"RegOverridePredefKey")
            try:
                for filename in files:
                    dll=ct.WinDLL(str(folder/filename));dll.DllRegisterServer.restype=ct.c_long
                    result=dll.DllRegisterServer()
                    if result<0:raise RuntimeError(filename+": "+hex(result & 0xffffffff))
            finally:
                code=adv.RegOverridePredefKey(ct.c_void_p(-2147483648),None)
                if code:raise OSError(code,"Restore HKCR mapping")
    register=ct.OleDLL("oleaut32").RegisterTypeLibForUser
    register.argtypes=[ct.POINTER(typeinfo.ITypeLib),ct.c_wchar_p,ct.c_wchar_p]
    register.restype=HRESULT
    for filename in files+["ICApiFoundation.tlb","ICApiIronCAD.tlb"]:
        path=str(folder/filename)
        # Loading must not attempt machine registration before the explicit
        # per-user registration below.
        register(typeinfo.LoadTypeLibEx(path,typeinfo.REGKIND_NONE),path,str(folder))
    print("ICAPI COM metadata registered for current user. Restart IronCAD.")

if __name__=="__main__":repair()
