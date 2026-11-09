import sys,json,shutil,hashlib
from pathlib import Path
sys.path.insert(0,'Integracja')
import comtypes.client
from rockpro_cad.icapi_runtime import ICAPI as A,assert_host
from rockpro_cad.cad_lock import cad_writer_lock
from ironcad_adapter import connect
m=comtypes.client.GetModule(r'C:\Program Files\IronCAD\2023\bin\IronCad.tlb')
folder=Path('artifacts/ironcad2023-compatibility/legacy-expression-01').resolve();folder.mkdir(exist_ok=False)
source=Path('artifacts/ironcad2023-compatibility/native-probe-04/diagnostic_restored.ics').resolve();copy=folder/'input.ics';shutil.copyfile(source,copy)
result={'passed':False,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()};doc=None
with cad_writer_lock():
 try:
  base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp);assert_host(base)
  already,doc=base.OpenFile2(str(copy),False,False)
  if already:raise RuntimeError('ownership refused')
  legacy,base,doc=connect(copy)
  scene=doc.QueryInterface(A.IZSceneDoc);part=scene.GetTopElement().GetChildrenZArray().Get(0).QueryInterface(A.IZPart)
  part.QueryInterface(A.IZSizeBox).Reset(False)
  shape=legacy.Shape.Components(m.triGroup).Item(1).Shapes.Item(1)
  sb=shape.Components(m.triSizeBox).Item(1)
  v=sb._comobj._invoke(65540,2,0,m.triHeight,0)
  result['before_variable']={'value':v.Value,'expression':v.Expression};result['before_bounds']=list(part.GetBody(True).GetBoundingBox())
  v.Expression=r'Parent\Params\RP_ProbeThickness'
  scene.ParameterMgr.GetParameterByName('RP_ProbeThickness').Expression='40 mm'
  scene.RegenerateParts(True);scene.Update()
  result['after_variable']={'value':v.Value,'expression':v.Expression};result['after_bounds']=list(part.GetBody(True).GetBoundingBox())
  result['passed']=abs(result['after_bounds'][5]-result['after_bounds'][2]-.04)<1e-7
  scene.SaveAs(str(folder/'expression_result.ics'),A.Z_LINKS_COPY_ALL,False)
 except Exception as ex:result['error']=repr(ex)
 finally:
  if doc is not None:
   if doc.Modified:doc.QueryInterface(A.IZSceneDoc).SaveAsCopy(str(folder/'recovery.ics'),A.Z_LINKS_COPY_ALL,False)
   doc.Close()
  result['source_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==result['source_sha256']
  (folder/'result.json').write_text(json.dumps(result,ensure_ascii=True,indent=2))
  print(json.dumps(result,ensure_ascii=True))
