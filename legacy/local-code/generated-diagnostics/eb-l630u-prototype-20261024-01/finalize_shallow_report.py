import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.profile_rules import value
out=Path(r'C:\Users\zuzan\Documents\ChatGPT\Ironcad\projekty\Epson_EB-L630U\Prototyp_02_plytka_pokrywa')
r=json.loads((out/'prototype_report.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with cad_writer_lock():
 base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
 doc=base.ActiveDoc
 assert Path(str(doc.Name)).resolve()==Path(r['result']).resolve()
 assert not doc.Modified
 scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility)
 for n,v in r['parameters_mm'].items():assert abs(float(scene.ParameterMgr.GetParameterByName(n).Expression.replace('mm','').replace(',','.').strip())-v)<1e-6
 source_receipt=Path(r'C:\Users\zuzan\Documents\ChatGPT\Ironcad\projekty\Skrzynia_2000x3000x4000\Wersja_03_zawiasy_kola_gniazda\transport_build_report.json')
 old=json.loads(source_receipt.read_text(encoding='utf-8'))
 for row in old['source_profile_report']['old_bindings']:
  if row['kind']=='panel':
   e=u.GetElementById(row['id']).QueryInterface(A.IZPart);b=list(e.GetBoundingBox(True))
   assert max(abs((b[j+3]-b[j])*1000-value(row['size'][j],r['parameters_mm'])) for j in range(3))<.05
   assert e.SurfaceFinish.Color==0x808040
 assert sha(r['source'])==r['source_sha256']
 r['pre_visual_result_sha256']=r['result_sha256'];r['result_sha256']=sha(r['result'])
 r.update(native_graphics_review='PASS: actual front/side and rear screenshots',final_parameters_and_panels_passed=True,delivery_open_for_review=True,final_document_modified=False,verification_evidence='artifacts/verification/20261024T154630321496Z/results.json',screenshots=['podglad_przod.png','podglad_tyl.png'])
 (out/'prototype_report.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
 print(json.dumps(dict(passed=True,result_sha256=r['result_sha256'],original_unchanged=True,checks=len(r['checks']))))


