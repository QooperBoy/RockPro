import ctypes as c,json
from ctypes import wintypes as w
from pathlib import Path
from comtypes import typeinfo
bin=Path(r'C:\Program Files\IronCAD\2027\bin');out=Path('artifacts/latch17251-compile-20261022-01/resources');out.mkdir(exist_ok=False)
k=c.WinDLL('kernel32',use_last_error=True)
k.LoadLibraryExW.argtypes=[w.LPCWSTR,w.HANDLE,w.DWORD];k.LoadLibraryExW.restype=w.HMODULE;k.FreeLibrary.argtypes=[w.HMODULE]
CB=c.WINFUNCTYPE(w.BOOL,w.HMODULE,c.c_void_p,c.c_void_p,c.c_ssize_t)
k.EnumResourceNamesW.argtypes=[w.HMODULE,c.c_void_p,CB,c.c_ssize_t];k.EnumResourceNamesW.restype=w.BOOL
k.FindResourceW.argtypes=[w.HMODULE,c.c_void_p,c.c_void_p];k.FindResourceW.restype=w.HANDLE
k.SizeofResource.argtypes=[w.HMODULE,w.HANDLE];k.SizeofResource.restype=w.DWORD;k.LoadResource.argtypes=[w.HMODULE,w.HANDLE];k.LoadResource.restype=w.HANDLE;k.LockResource.argtypes=[w.HANDLE];k.LockResource.restype=c.c_void_p
rows=[]
for filename in ['3iICApiBase.dll','3iICApiIronCADApp.dll','3iICApiCore.dll','3iICApiDrawing.dll']:
 h=k.LoadLibraryExW(str(bin/filename),None,0x22)
 if not h:raise c.WinError(c.get_last_error())
 typebuf=c.create_unicode_buffer('TYPELIB');typeptr=c.cast(typebuf,c.c_void_p)
 @CB
 def callback(module,typ,name,param):
  label=str(name) if name<=0xffff else c.wstring_at(name)
  res=k.FindResourceW(module,name,typ);size=k.SizeofResource(module,res);ptr=k.LockResource(k.LoadResource(module,res));path=out/(filename+'_'+label+'.tlb');path.write_bytes(c.string_at(ptr,size));r={'dll':filename,'resource':label,'bytes':size,'path':str(path)}
  try:
   lib=typeinfo.LoadTypeLibEx(str(path.resolve()),typeinfo.REGKIND_NONE);a=lib.GetLibAttr();r.update(guid=str(a.guid),major=int(a.wMajorVerNum),minor=int(a.wMinorVerNum),syskind=int(a.syskind))
  except Exception as e:r['metadata_error']=str(e)
  rows.append(r);return True
 ok=k.EnumResourceNamesW(h,typeptr,callback,0)
 if not ok:rows.append({'dll':filename,'enum_error':c.get_last_error()})
 k.FreeLibrary(h)
for path in bin.glob('ICAPI*.tlb'):
 try:
  a=typeinfo.LoadTypeLibEx(str(path),typeinfo.REGKIND_NONE).GetLibAttr();rows.append({'file':str(path),'guid':str(a.guid),'major':int(a.wMajorVerNum),'minor':int(a.wMinorVerNum),'syskind':int(a.syskind)})
 except Exception as e:rows.append({'file':str(path),'error':str(e)})
(out/'resource_typelibs.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
