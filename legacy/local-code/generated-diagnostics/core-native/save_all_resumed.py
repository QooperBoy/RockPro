import sys,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.cad_lock import cad_writer_lock
root=Path('artifacts/core-native').resolve();request=root/'sdk/lifecycle-save-resumed-request.json';report=root/'save-all-result-resumed.json'
request.write_text(json.dumps({'action':'save_all','source':str(root/'native-A-20261021-02/case_prototype.ics'),'directory':str(root/'user-save-all-20261022-resumed')}),encoding='utf-8')
with cad_writer_lock():
 result=subprocess.run([str(root/'sdk/DocumentLifecycle.exe'),str(request),str(report)])
print('LIFECYCLE_EXIT',result.returncode,flush=True)
raise SystemExit(0 if result.returncode==0 else 1)
