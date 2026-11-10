import pathlib,sys,time,runpy
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock,CadBusyError
deadline=time.monotonic()+3600
print('Waiting for the existing native call to return; no parallel CAD execution.',flush=True)
while True:
 try:
  with cad_writer_lock():
   print('Writer available; starting coarse-preview tessellation.',flush=True)
   runpy.run_path(str(pathlib.Path(__file__).with_name('export_kernel_fast.py')),run_name='__main__')
   break
 except CadBusyError:
  if time.monotonic()>deadline:raise TimeoutError('Existing CAD call has not returned; no parallel CAD started')
  time.sleep(3)
