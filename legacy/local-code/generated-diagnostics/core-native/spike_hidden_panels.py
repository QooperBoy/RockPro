import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.corner_native import produce_hidden_panels,panel_occurrences
from rockpro_cad.cad_lock import cad_writer_lock
r=json.loads(Path('artifacts/corner410429-20261022/hidden-source/normalized_evidence.json').read_text(encoding='utf-8'))
with cad_writer_lock():
 result=produce_hidden_panels(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\rockpro_cad\qa\core-native-158e2ef\case_prototype.ics',panel_occurrences([914,602,352],r['case_frame']['matrix_world_mm'])[:1],Path('artifacts/corner410429-20261022/hidden-panel-spike'))
 print(json.dumps({'passed':result['passed'],'path':result['output_path'],'sha256':result['sha256']}),flush=True)
