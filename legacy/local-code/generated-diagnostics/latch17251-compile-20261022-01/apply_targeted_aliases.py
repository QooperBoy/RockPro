import ctypes,json,winreg,hashlib,subprocess,os
from pathlib import Path
from comtypes import typeinfo
folder=Path('artifacts/latch17251-api-repair-20261022-01').resolve();folder.mkdir(exist_ok=False)
def save(name,value):
 with (folder/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
items=[('{6EE9ED93-0C2B-4808-B138-F294D9A71B0A}','3iICApiBase.dll'),('{D8E3895D-8CA1-46CF-85F9-800B9A649F82}','3iICApiIronCADApp.dll')]
bin=Path(r'C:\Program Files\IronCAD\2027\bin');records=[]
for guid,name in items:
 path='Software\\Classes\\TypeLib\\'+guid+'\\c.0'
 try:
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY):raise RuntimeError('Alias already exists; refusing overwrite '+path)
 except FileNotFoundError:pass
 dll=bin/name;lib=typeinfo.LoadTypeLibEx(str(dll),typeinfo.REGKIND_NONE);a=lib.GetLibAttr()
 if str(a.guid).lower()!=guid.lower() or a.wMajorVerNum!=29 or a.wMinorVerNum!=0 or int(a.syskind)!=3:raise RuntimeError('Pinned DLL metadata mismatch')
 records.append({'key':path,'existed':False,'guid':guid,'file':str(dll),'sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'internal_version':[29,0],'requested_alias':[12,0],'values':{'':lib.GetDocumentation(-1)[0],'0\\win64':str(dll),'FLAGS':'0','HELPDIR':str(bin)}})
save('before_backup.json',{'scope':'Only two new HKCU TypeLib c.0 keys; no Interface/HKLM changes','records':records})
created=[]
def delete_tree(path):
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_READ|winreg.KEY_WRITE|winreg.KEY_WOW64_64KEY) as key:
  children=[winreg.EnumKey(key,i) for i in range(winreg.QueryInfoKey(key)[0])]
 for child in children:delete_tree(path+'\\'+child)
 winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER,path,winreg.KEY_WOW64_64KEY,0)
try:
 for r in records:
  with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,r['key'],0,winreg.KEY_WRITE|winreg.KEY_WOW64_64KEY) as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,r['values'][''])
  created.append(r)
  for suffix in ['0\\win64','FLAGS','HELPDIR']:
   with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,r['key']+'\\'+suffix,0,winreg.KEY_WRITE|winreg.KEY_WOW64_64KEY) as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,r['values'][suffix])
 loaded=[]
 for r in records:
  lib=typeinfo.LoadRegTypeLib(r['guid'],12,0,0);a=lib.GetLibAttr();loaded.append({'guid':r['guid'],'loaded_major':int(a.wMajorVerNum),'loaded_minor':int(a.wMinorVerNum),'path':str(typeinfo.QueryPathOfRegTypeLib(r['guid'],12,0,0))})
 save('loadreg12_after.json',loaded)
 exe=Path('artifacts/latch17251-compile-20261022-01/AttachProbe.exe').resolve()
 run=subprocess.run([str(exe),r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\skeleton\20261020T110925Z\Epson_source_snapshot.ics'],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 save('attach_after.json',{'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr});print(run.stdout);print(run.stderr)
 if run.returncode:raise RuntimeError('SDK getter attach still fails; rollback aliases')
 save('repair_receipt.json',{'passed':True,'kept_aliases':records,'host_restarted':False,'registry_machine_or_interface_changes':False,'scope':'SDK29 DLLs include ATL12 type-info holders; aliases satisfy that exact LoadRegTypeLib request','native_model_calls':0})
 print('REPAIR GETTER ATTACH PASS')
except Exception as e:
 for r in reversed(created):delete_tree(r['key'])
 save('rollback.json',{'passed':True,'removed_only_created_aliases':[r['key'] for r in created],'error':str(e)})
 raise
