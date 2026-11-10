import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
from rockpro_cad.cad_lock import cad_writer_lock
out=Path(r'C:\Users\zuzan\Documents\ChatGPT\Ironcad\projekty\Epson_EB-L630U\Prototyp_02_plytka_pokrywa')
r=json.loads((out/'prototype_report.json').read_text(encoding='utf-8'))
with cad_writer_lock():
 base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
 doc=base.ActiveDoc;assert Path(str(doc.Name)).resolve()==Path(r['result']).resolve()
 assert not doc.Modified
 scene=doc.QueryInterface(A.IZSceneDoc)
 saved=out/'RockPro_EB-L630U_650x500x381_final.ics';assert not saved.exists()
 scene.SaveAsCopy(str(saved),A.Z_LINKS_COPY_ALL,False)
 print('Safety copy saved',flush=True)
 doc.Close()
 already,check=base.OpenFile2(str(saved),False,False);assert not already
 try:
  s=check.QueryInterface(A.IZSceneDoc)
  for n,v in r['parameters_mm'].items():assert abs(float(s.ParameterMgr.GetParameterByName(n).Expression.replace('mm','').replace(',','.').strip())-v)<1e-6
 finally:check.Close()
 print('Fresh safety copy reopens PASS',flush=True)
 # Also check whether the first failure was caused by concurrent same-GUID scenes.
 copy=Path('artifacts/native-manual-change-20261024-01/manual_edit_preserved.ics').resolve()
 already,check=base.OpenFile2(str(copy),False,False);assert not already
 check.Close();print('Previously refused byte-copy reopens PASS when delivery is closed',flush=True)
 base.OpenFile(str(saved),False)
 r.update(result=str(saved),result_sha256=hashlib.sha256(saved.read_bytes()).hexdigest(),post_visual_saved_reopened=True,
          same_guid_open_conflict='byte-copy opening refused while delivery open; identical copy opened after closing delivery')
 (out/'prototype_report.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
 print('Final delivery reopened',flush=True)
