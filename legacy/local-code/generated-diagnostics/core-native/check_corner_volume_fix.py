import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.corner_native import compare_corner_persistence
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import file_sha256
root=Path('artifacts/corner410429-20261022');folder=root/'native-02'
before=json.loads((folder/'A-diagnostic/measurement_before_save.json').read_text(encoding='utf-8'));after=json.loads((folder/'A-diagnostic/measurement_after_reopen.json').read_text(encoding='utf-8'))
plan=json.loads((root/'native-01/prepared_plans.json').read_text(encoding='utf-8'))['plans'][0]['plan']
result=compare_corner_persistence(before,after,source_volumes={r['id']:r['body_signature']['volume_m3'] for r in plan['occurrences']})
write_receipt_once(folder/'persistence_offline_recheck.json',{'scope':'Offline application of volume-only fix to immutable historical native02 raw observations; not a new native execution','comparison':result,'corner_native_sha256':file_sha256('Integracja/rockpro_cad/core_case/corner_native.py')})
print(json.dumps(result))
