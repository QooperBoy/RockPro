import sys,json,subprocess,os,shutil
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.cad_lock import cad_writer_lock
repo=Path('.').resolve();folder=repo/'artifacts/prototype-cleanup-20261022-urgent-02';folder.mkdir(exist_ok=False) if sys.argv[1]=='inventory' else None
qa=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\rockpro_cad\qa\core-native-158e2ef')
context=qa/'case_prototype.ics';contexts=[context,repo/'artifacts/h7159-poc-native-20261022-04/delivery/POC_H7159_wnetrze_900x600x330.ics',Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')]
whitelist=[]
for p in (repo/'artifacts').rglob('*.ics'):
 rel=p.relative_to(repo/'artifacts');first=rel.parts[0].lower()
 if 'epson' in p.name.lower() or 'showcase' in p.name.lower():continue
 if first.startswith(('h7159-poc-','corner410429-','runtime-ui-')):whitelist.append(str(p.resolve()))
 elif first=='core-native' and len(rel.parts)>2 and rel.parts[1].startswith(('native-','real-H7159-','core-service-native')) and p.name.lower() in ('case_prototype.ics','source_snapshot.ics','source_catalog_asset.ics','h7159_native.ics'):whitelist.append(str(p.resolve()))
whitelist.extend(str(p.resolve()) for p in qa.glob('*.ics') if p.name in ('case_prototype.ics','H7159_native.ics'))
request=folder/(sys.argv[1]+'-request.json');write_receipt_once(request,{'action':sys.argv[1],'directory':str(folder),'contexts':[str(p) for p in contexts],'primary_context':str(context),'whitelist':sorted(set(whitelist))})
exe=folder/'PrototypeCleanup.exe';vendor=Path(r'C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll')
if sys.argv[1]=='inventory':
 build=subprocess.run([r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','/nologo','/target:exe','/platform:x64','/out:'+str(exe),'/reference:'+str(vendor),'/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',str(repo/'artifacts/core-native/PrototypeCleanup.cs')],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if build.returncode:raise RuntimeError(build.stdout+build.stderr)
 shutil.copyfile(vendor,folder/vendor.name)
with cad_writer_lock():
 result=subprocess.run([str(exe),str(request)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 print(result.stdout,flush=True);print(result.stderr,file=sys.stderr,flush=True)
 raise SystemExit(result.returncode)
