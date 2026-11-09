import sys,json,subprocess,os,traceback
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.cad_lock import cad_writer_lock
root=Path('artifacts/core-native').resolve();request=root/'sdk/lifecycle-save-request.json';report=root/'save-all-result.json'
request.write_text(json.dumps({'action':'save_all','source':str(root/'native-A-20261021-02/case_prototype.ics'),'directory':str(root/'user-save-all-20261021')}),encoding='utf-8')
try:
 with cad_writer_lock():
  r=subprocess.run([str(root/'sdk/DocumentLifecycle.exe'),str(request),str(report)])
 print('LIFECYCLE_EXIT',r.returncode,flush=True)
 sys.stdout.flush();os._exit(r.returncode)
except BaseException:
 traceback.print_exc();sys.stderr.flush();os._exit(1)
