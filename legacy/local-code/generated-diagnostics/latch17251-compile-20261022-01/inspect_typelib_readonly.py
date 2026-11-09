import ctypes,json,winreg,hashlib
from pathlib import Path
from comtypes import typeinfo
root=Path('artifacts/latch17251-compile-20261022-01')
path=Path(r'C:\Program Files\IronCAD\2027\bin\ICApiIronCAD.tlb')
tlib=typeinfo.LoadTypeLibEx(str(path),typeinfo.REGKIND_NONE)
def attrs(lib):
 a=lib.GetLibAttr();return {'guid':str(a.guid),'lcid':int(a.lcid),'syskind':int(a.syskind),'major':int(a.wMajorVerNum),'minor':int(a.wMinorVerNum),'flags':int(a.wLibFlags)}
a=attrs(tlib);interfaces=[]
for i in range(tlib.GetTypeInfoCount()):
 ti=tlib.GetTypeInfo(i);name=ti.GetDocumentation(-1)[0]
 if name=='IZBaseApp':
  ta=ti.GetTypeAttr();interfaces.append({'name':name,'guid':str(ta.guid),'major':int(ta.wMajorVerNum),'minor':int(ta.wMinorVerNum),'typekind':int(ta.typekind)})
def readtree(hive,keypath,view):
 try:k=winreg.OpenKey(hive,keypath,0,winreg.KEY_READ|view)
 except OSError as e:return {'missing':True,'error':str(e)}
 out={'values':{},'children':{}}
 with k:
  i=0
  while True:
   try:n,v,t=winreg.EnumValue(k,i);i+=1
   except OSError:break
   out['values'][n]={'value':v.hex() if isinstance(v,bytes) else v,'type':t}
  i=0
  while True:
   try:n=winreg.EnumKey(k,i);i+=1
   except OSError:break
   out['children'][n]=readtree(hive,keypath+'\\'+n,view)
 return out
reg={}
for label,hive,prefix in [('HKCR',winreg.HKEY_CLASSES_ROOT,''),('HKCU',winreg.HKEY_CURRENT_USER,'Software\\Classes\\'),('HKLM',winreg.HKEY_LOCAL_MACHINE,'Software\\Classes\\')]:
 for bit,view in [('64',winreg.KEY_WOW64_64KEY),('32',winreg.KEY_WOW64_32KEY)]:
  reg[label+bit]={branch:readtree(hive,prefix+branch,view) for branch in ['TypeLib\\'+a['guid'],'Interface\\{A5B9AF7D-228B-4ED1-BA42-D51318F7EA20}']}
loads={}
for major in [a['major'],29,21,14]:
 try:
  lib=typeinfo.LoadRegTypeLib(a['guid'],major,a['minor'],a['lcid']);loads[str(major)]={'loaded':True,'attributes':attrs(lib),'query_path':str(typeinfo.QueryPathOfRegTypeLib(a['guid'],major,a['minor'],a['lcid']))}
 except Exception as e:loads[str(major)]={'loaded':False,'error':str(e)}
result={'official_tlb':str(path),'tlb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'LoadTypeLibEx_REGKIND_NONE':a,'IZBaseApp':interfaces,'LoadRegTypeLib':loads,'registry':reg}
(root/'typelib_readonly_evidence.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='registry'},indent=2));print('registry evidence saved')
