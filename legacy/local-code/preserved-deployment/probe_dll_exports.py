import ctypes,os
os.add_dll_directory('C:/Program Files/IronCAD/2027/bin')
for name in ['3iICApiIronCADApp.dll','3iICApiCore.dll','3iICApiBase.dll']:
 dll=ctypes.WinDLL('C:/Program Files/IronCAD/2027/bin/'+name)
 for fn in ['DllInstall','DllRegisterServer']:
  print(name,fn,hasattr(dll,fn))
