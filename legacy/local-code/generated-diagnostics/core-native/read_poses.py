import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native_reader import inspect_source_poses
r=inspect_source_poses(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')
p=Path('artifacts/core-native/source-poses.json'); p.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({'status':r['status'],'rows':len(r['rows']),'errors':len(r['errors']),'report':str(p.resolve()),'source':r['source'],'doc':r['cad_document']},ensure_ascii=True))
