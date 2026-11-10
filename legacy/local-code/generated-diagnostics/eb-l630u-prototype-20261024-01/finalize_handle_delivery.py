import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.profile_rules import value
out=Path(sys.argv[1]).resolve(strict=True)
r=json.loads((out/'prototype_report.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with cad_writer_lock():
 base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
 doc=base.ActiveDoc;assert Path(str(doc.Name)).resolve()==Path(r['result']).resolve()
 scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility)
 for name,wanted in r['parameters_mm'].items():
  assert abs(float(scene.ParameterMgr.GetParameterByName(name).Expression.replace('mm','').replace(',','.').strip())-wanted)<1e-6
 for row in r['small_case_binding_changes']:
  e=u.GetElementById(row['id']);se=e.QueryInterface(A.IZSceneElement);m=se.GetTransformToGlobal()
  assert e.GetChildrenCount()==13
  assert max(abs(m.GetValue(3,j)*1000-value(row['position'][j],r['parameters_mm'])) for j in range(3))<.05
  assert max(abs(m.GetValue(i,j)-row['rotation'][i][j]) for i in range(3) for j in range(3))<1e-7
 doc.Save()
 assert not doc.Modified
 assert sha(r['source'])==r['source_sha256']
 assert sha(r['handle_asset'])==r['handle_asset_sha256']
 r['pre_visual_result_sha256']=r['result_sha256'];r['result_sha256']=sha(r['result'])
 r.update(post_visual_handle_geometry_passed=True,delivery_open_for_review=True)
 images=[p.name for p in out.glob('podglad_*.png')]
 if images:r.update(native_graphics_review='PASS: actual IronCAD view',screenshots=images)
 (out/'prototype_report.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
 print('PASS: final handle poses and original hashes; delivery saved',flush=True)
