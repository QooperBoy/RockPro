import sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.corner_native import execute_corner_case
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.cad_lock import cad_writer_lock
root=Path('artifacts/corner410429-20261022').resolve();folder=root/'native-02';folder.mkdir(exist_ok=False)
manifest=json.loads((root/'native-01/prepared_plans.json').read_text(encoding='utf-8'));assets=json.loads((root/'native-01/assets/assets_receipt.json').read_text(encoding='utf-8'))
registration=json.loads((root/'hidden-source/native_contact_registration.json').read_text(encoding='utf-8'))
try:
 with cad_writer_lock():execute_corner_case(manifest['plans'][0]['plan'],context_source=manifest['context'],assets=assets,registration=registration,output_dir=folder,operation_id='A-diagnostic')
except Exception as exc:print(type(exc).__name__+': '+str(exc),flush=True)
before=json.loads((folder/'A-diagnostic/measurement_before_save.json').read_text(encoding='utf-8'));after=json.loads((folder/'A-diagnostic/measurement_after_reopen.json').read_text(encoding='utf-8'))
diff=[]
def walk(a,b,path):
 if type(a)!=type(b):diff.append({'path':path,'before':a,'after':b,'type_changed':True});return
 if isinstance(a,dict):
  if set(a)!=set(b):diff.append({'path':path,'keys_before':list(a),'keys_after':list(b)});return
  for key in a:walk(a[key],b[key],path+[key])
 elif isinstance(a,list):
  if len(a)!=len(b):diff.append({'path':path,'length_before':len(a),'length_after':len(b)});return
  for i,(x,y) in enumerate(zip(a,b)):walk(x,y,path+[i])
 elif a!=b:
  row={'path':path,'before':a,'after':b}
  if type(a) in (int,float):row['absolute_delta']=abs(a-b)
  diff.append(row)
walk(before,after,[])
write_receipt_once(folder/'measurement_diff.json',{'differences':diff,'count':len(diff),'before_measurement':str(folder/'A-diagnostic/measurement_before_save.json'),'after_measurement':str(folder/'A-diagnostic/measurement_after_reopen.json')})
print(json.dumps({'diff_count':len(diff),'sample':diff[:15]}),flush=True)
