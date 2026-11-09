from pathlib import Path
import json,shutil,hashlib,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Integracja'))
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.catalog_native import close_owned_documents
F=Path(__file__).resolve().parent
SOURCE=ROOT/'artifacts/saved-source-native-20261024-02/source_snapshot.ics'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mat(e):
 m=e.QueryInterface(A.IZSceneElement).GetTransformToGlobal()
 return [[m.GetValue(i,j) for j in range(4)] for i in range(4)]
def box(e):return list(e.QueryInterface(A.IZPart).GetBoundingBox(True))
def run():
 assert sha(SOURCE)=='e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1'
 with cad_writer_lock():
  base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp);owned=[]
  p=F/'source_read_copy.ics'
  with SOURCE.open('rb') as s,p.open('xb') as t:shutil.copyfileobj(s,t)
  try:
   already,doc=base.OpenFile2(str(p),False,False);assert not already;owned.append(doc)
   scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility);rows=[]
   for id,name in [(285,'EG-0500_1'),(1319,'EG-0500_2'),(9018,'EG-0113'),(9440,'B1930'),(13210,'B1121')]:
    e=u.GetElementById(id);assert e.Name==name
    path=F/(name+'.ics');e.QueryInterface(A.IZPart).SaveAs(str(path),False)
    rows.append(dict(source_id=id,name=name,asset=str(path),sha256=sha(path),source_world_m=mat(e),local_bounds_m=box(e),features=e.QueryInterface(A.IZPartFeatureMgr).GetFeaturesCount()))
   assert not doc.Modified;close_owned_documents(owned,A,F)
   p=F/'probe.ics';shutil.copyfile(F/'EG-0113.ics',p)
   already,doc=base.OpenFile2(str(p),False,False);assert not already;owned.append(doc);scene=doc.QueryInterface(A.IZSceneDoc)
   e=scene.GetFirstChild().QueryInterface(A.IZElement);sb=e.QueryInterface(A.IZSizeBox);sb.Reset(False)
   print('BEFORE',box(e),[sb.Length,sb.Width,sb.Height],flush=True)
   param=scene.ParameterMgr.CreateParameter(A.Z_PARAMETER_TYPE_LENGTH,'RP_Length',2);param.Expression='2000 mm'
   sb.ResizeAspectLock=A.Z_RESIZE_LOCK_NONE;sb.HeightResizeBehavior=A.Z_RESIZE_ABOUT_SIZEBOX_CENTER;sb.HeightExpression='Parent\\Params\\RP_Length'
   e.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression();e.QueryInterface(A.IZPart).Regenerate();scene.Update()
   print('AFTER',box(e),[sb.Length,sb.Width,sb.Height],flush=True)
   scene.SaveAs(str(F/'probe_result.ics'),A.Z_LINKS_COPY_ALL,False)
   (F/'assets.json').write_text(json.dumps(dict(source_sha256=sha(SOURCE),rows=rows),indent=2),encoding='utf-8')
  finally:close_owned_documents(owned,A,F)
if __name__=='__main__':run()
