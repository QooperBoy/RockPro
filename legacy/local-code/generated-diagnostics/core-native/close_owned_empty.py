import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.cad_lock import cad_writer_lock
root=Path('artifacts/core-native').resolve();request=root/'sdk/lifecycle-clean-empty-request.json'
request.write_text(json.dumps({'action':'close_owned_empty','source':str(root/'native-A-20261021-02/case_prototype.ics'),'directory':str(root/'unused')}),encoding='utf-8')
with cad_writer_lock():
 result=subprocess.run([str(root/'sdk/DocumentLifecycle.exe'),str(request),str(root/'close-owned-empty-result.json')])
raise SystemExit(result.returncode)
