import json,sys,os,traceback
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.planner import plan_case
from rockpro_cad.core_case.native import execute_plan, IronCADPrototypeDriver
fixtures=json.loads(Path('tests/core_design/cases.json').read_text(encoding='utf-8'))
recipe=json.loads(Path('tests/core_design/synthetic_template.json').read_text(encoding='utf-8'))
plan=plan_case({'spec':fixtures['cases'][0]['spec'],'manifest':fixtures['manifest'],'scenario':{'operation':'plan'},'template_recipe':recipe})
Path('artifacts/core-native/plan-A.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
class ProgressDriver(IronCADPrototypeDriver):
 def capture(self,p):
  print('CAPTURE',flush=True);return super().capture(p)
 def create(self,p):
  print('CREATE',len(p),flush=True);return super().create(p)
 def measure(self):
  print('MEASURE',flush=True);return super().measure()
 def save_reopen(self,p):
  print('SAVE_REOPEN',flush=True);return super().save_reopen(p)
try:
 r=execute_plan(plan,output_dir='artifacts/core-native',source=r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics',operation_id='native-A-20261021-02',_adapter_factory=ProgressDriver)
 print(json.dumps({k:r[k] for k in ('passed','output_path','source_unchanged','physical_occurrences','geometry_scope','stages')},ensure_ascii=True),flush=True)
 os._exit(0)
except BaseException:
 traceback.print_exc();sys.stderr.flush();os._exit(1)

