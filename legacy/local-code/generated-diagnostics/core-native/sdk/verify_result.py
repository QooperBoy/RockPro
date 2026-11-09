import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import preflight_plan, compare_measurements
plan=json.loads(Path('artifacts/core-native/plan-A.json').read_text(encoding='utf-8'))
r=json.loads(Path('artifacts/core-native/sdk/result-A.json').read_text())
try:
 checks=compare_measurements(preflight_plan(plan),r['reopened'])
 print('PASS',len(checks),max(c['max_error_mm'] for c in checks))
except Exception as e:
 print(type(e).__name__,e)
 p=preflight_plan(plan)[0];obs=r['reopened'][0]
 print('expected',p);print('observed',obs)
