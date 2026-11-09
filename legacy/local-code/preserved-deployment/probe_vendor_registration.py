import ctypes as c,winreg,os,json
os.add_dll_directory('C:/Program Files/IronCAD/2027/bin')
a=c.WinDLL('advapi32');a.RegOverridePredefKey.argtypes=[c.c_void_p,c.c_void_p]
k=winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\RockPro\RegistrationProbe')
print('override',a.RegOverridePredefKey(c.c_void_p(-2147483648),c.c_void_p(int(k))))
try:
 d=c.WinDLL('C:/Program Files/IronCAD/2027/bin/3iICApiIronCADApp.dll');d.DllRegisterServer.restype=c.c_long;print('register result',hex(d.DllRegisterServer() & 0xffffffff))
finally:a.RegOverridePredefKey(c.c_void_p(-2147483648),None)
def walk(h,path=''):
 i=0
 while True:
  try:n,v,t=winreg.EnumValue(h,i);print(path,n,str(v));i+=1
  except OSError:break
 i=0
 while True:
  try:n=winreg.EnumKey(h,i);i+=1
  except OSError:break
  with winreg.OpenKey(h,n) as sub:walk(sub,path+'\\'+n)
walk(k)

