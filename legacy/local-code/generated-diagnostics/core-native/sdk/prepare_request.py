import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import preflight_plan
p=Path('artifacts/core-native/sdk/request-A.json')
p.write_text(json.dumps({'source':r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics','output':str(Path('artifacts/core-native/sdk/case-A.ics').resolve()),'parts':preflight_plan(json.loads(Path('artifacts/core-native/plan-A.json').read_text(encoding='utf-8')))}),encoding='utf-8')
