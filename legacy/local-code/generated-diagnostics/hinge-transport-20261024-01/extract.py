from pathlib import Path
import json,shutil,sys,hashlib
ROOT=Path(__file__).resolve().parents[2];F=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Integracja'))
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.catalog_native import close_owned_documents
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def matrix(e):
 m=e.QueryInterface(A.IZSceneElement).GetTransformToParent()
 return [[m.GetValue(i,j) for j in range(4)] for i in range(4)]
def box(e,kind):return list(e.QueryInterface(A.IZPart if kind=='part' else A.IZAssembly).GetBoundingBox(True))
def children(e):
 e=e.QueryInterface(A.IZElement);a=e.GetChildrenZArray();return [a.Get(i).QueryInterface(A.IZElement) for i in range(e.GetChildrenCount())]
def tree(e,path=None):
 e=e.QueryInterface(A.IZElement);path=[] if path is None else path
 try:e.QueryInterface(A.IZPart);kind='part'
 except comtypes.COMError:kind='assembly'
 rows=[dict(path=path,id=int(e.Id),name=e.Name,kind=kind,bounds_m=box(e,kind),parent_m=matrix(e))]
 if kind=='assembly':
  for i,c in enumerate(children(e)):rows.extend(tree(c,path+[i]))
 return rows
def run():
 source=ROOT/'artifacts/saved-source-native-20261024-02/source_snapshot.ics';digest=sha(source)
 assert digest=='e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1'
 with cad_writer_lock():
  b=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp);owned=[]
  p=F/'source_read_copy.ics'
  with source.open('rb') as s,p.open('xb') as t:shutil.copyfileobj(s,t)
  rows=[]
  try:
   opened,d=b.OpenFile2(str(p),False,False);assert not opened;owned.append(d);u=d.QueryInterface(A.IZSceneDocUtility)
   for id,alias,kind in [(12953,'hinge_lid','assembly'),(13020,'hinge_base','assembly'),(594,'wheel','assembly'),(13227,'socket','part')]:
    e=u.GetElementById(id);path=F/(alias+'.ics');e.QueryInterface(A.IZPart if kind=='part' else A.IZAssembly).SaveAs(str(path),False)
    rows.append(dict(source_id=id,name=e.Name,alias=alias,kind=kind,path=str(path),sha256=sha(path),signature=tree(e)))
   assert not d.Modified;close_owned_documents(owned,A,F)
   for row in rows:
    p=F/('inspect_'+row['alias']+'.ics');shutil.copyfile(row['path'],p)
    opened,d=b.OpenFile2(str(p),False,False);assert not opened;owned.append(d);s=d.QueryInterface(A.IZSceneDoc)
    e=s.GetFirstChild().QueryInterface(A.IZElement);row['export_signature']=tree(e)
    if row['alias']=='socket':
     body=e.QueryInterface(A.IZPart).GetBody(True);faces=body.QueryInterface(A.IZBodyFace);verts=body.QueryInterface(A.IZBodyVertex);planes=[]
     for fid in body.GetFaceIds():
      try:rev,point,normal=faces.GetPlaneData(fid)
      except comtypes.COMError:continue
      if abs(abs(normal.Z)-1)>1e-6:continue
      vs=[list(verts.GetPosition(i)) for i in faces.GetFaceVertexIds(fid)]
      if not vs:continue
      bounds=[min(v[i] for v in vs) for i in range(3)]+[max(v[i] for v in vs) for i in range(3)]
      planes.append(dict(face_id=int(fid),reversed=bool(rev),point=[point.X,point.Y,point.Z],normal=[normal.X,normal.Y,normal.Z],bounds_m=bounds))
     row['horizontal_planes']=planes;print('SOCKET PLANES',json.dumps(planes),flush=True)
    if row['alias']=='wheel':
     rubber=children(e)[3];body=rubber.QueryInterface(A.IZPart).GetBody(True);faces=body.QueryInterface(A.IZBodyFace);cyl=[]
     for fid in body.GetFaceIds():
      try:data=faces.GetCylinderData(fid)
      except comtypes.COMError:continue
      print('CYLINDER',fid,str(data),flush=True)
     row['rubber_parent_m']=matrix(rubber)
    assert not d.Modified;close_owned_documents(owned,A,F)
   (F/'assets.json').write_text(json.dumps(dict(source_sha256=digest,rows=rows),indent=2,ensure_ascii=False),encoding='utf-8')
   assert sha(source)==digest
  finally:close_owned_documents(owned,A,F)
if __name__=='__main__':run()
