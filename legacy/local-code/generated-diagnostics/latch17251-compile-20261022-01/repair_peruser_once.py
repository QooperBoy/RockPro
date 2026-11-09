import winreg,json,os,subprocess,sys,hashlib
from pathlib import Path
folder=Path('artifacts/latch17251-api-repair-20261022-03').resolve();folder.mkdir(exist_ok=False)
def write(name,x):
 with (folder/name).open('x',encoding='utf-8') as f:json.dump(x,f,indent=2);f.flush();os.fsync(f.fileno())
def snapshot():
 out={}
 def walk(path):
  try:k=winreg.OpenKey(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
  except OSError:return
  with k:
   children,values,_=winreg.QueryInfoKey(k);row={}
   for i in range(values):
    try:n,v,t=winreg.EnumValue(k,i);row[n]={'type':t,'value':v.hex() if isinstance(v,bytes) else v}
    except OSError:continue
   out[path]=row
   names=[winreg.EnumKey(k,i) for i in range(children)]
  for n in names:walk(path+'\\'+n)
 walk('Software\\Classes');return out
before=snapshot();write('hkcu_classes_before.json',before);print('Backup keys',len(before),flush=True)
repair=Path('Integracja/rockpro_cad/addin/Repair-IcApi.py').resolve()
run=subprocess.run([sys.executable,str(repair)],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
write('repair_process.json',{'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'script_sha256':hashlib.sha256(repair.read_bytes()).hexdigest()})
after=snapshot();write('hkcu_classes_after.json',after)
diff=[{'key':p,'before':before.get(p),'after':after.get(p)} for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
write('registry_diff.json',diff);print('Repair exit',run.returncode,'changedkeys',len(diff));print(run.stdout,run.stderr)
print('Changed paths:')
for r in diff[:25]:print(r['key'])
