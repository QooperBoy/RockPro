from pathlib import Path
import sys,shutil,hashlib,json
sys.path.insert(0,'Integracja')
import comtypes.client
from rockpro_cad.icapi_runtime import ICAPI as A,assert_host
from rockpro_cad.cad_lock import cad_writer_lock
source=Path("artifacts/t2-analysis-20261026/source/DiGiCo Quantum 1'12.ics").resolve()
folder=Path('artifacts/ironcad2023-compatibility/python-t2-original');folder.mkdir(exist_ok=False)
copy=(folder/'source_copy.ics').resolve();shutil.copyfile(source,copy)
with cad_writer_lock():
 b=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp);assert_host(b)
 already,d=b.OpenFile2(str(copy),False,False)
 if already:raise RuntimeError('Copy already open')
 try:
  scene=d.QueryInterface(A.IZSceneDoc);root=scene.GetTopElement();out={'api':b.ApiVersion,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'nodes':[]}
  def walk(e,path='root'):
   e=e.QueryInterface(A.IZElement)
   row={'name':e.Name,'id':e.Id,'type':e.Type,'path':path}
   try:
    se=e.QueryInterface(A.IZSceneElement);row['matrix_data']=se.GetTransformToParent().Data
    pm=se.ParameterMgr;row['parameters']=[{'name':pm.GetParameter(i).Name,'expression':pm.GetParameter(i).Expression,'value':pm.GetParameter(i).Value} for i in range(pm.Count)]
   except Exception as ex:row['error']=str(ex)
   if e.Type==A.Z_ELEMENT_PART:
    try:row['bounds_body']=e.QueryInterface(A.IZPart).GetBody(True).GetBoundingBox()
    except Exception as ex:row['bounds_error']=str(ex)
   out['nodes'].append(row)
   if e.GetChildrenCount():
    ar=e.GetChildrenZArray()
    for i in range(ar.Count()):
     c=ar.Get(i).QueryInterface(A.IZElement)
     if c.Type in (A.Z_ELEMENT_PART,A.Z_ELEMENT_ASSEMBLY):walk(c,path+'/'+str(i))
  walk(root)
  (folder/'inventory.json').write_text(json.dumps(out,ensure_ascii=True,indent=2))
  print('API',out['api'],'NODES',len(out['nodes']),flush=True)
 finally:
  if d.Modified:scene.SaveAsCopy(str((folder/'preserved.ics').resolve()),A.Z_LINKS_COPY_ALL,False)
  d.Close()
 print('ORIGINAL_UNCHANGED',hashlib.sha256(source.read_bytes()).hexdigest()==out['source_sha256'])
