from pathlib import Path
import json, shutil
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
ROOT=Path(__file__).resolve().parents[3]
REPO=ROOT/'Transfer_RockPro_20261024/RockPro/rockpro-cad'
OUT=Path(__file__).resolve().parent.parent
SOURCE=REPO/'artifacts/cube1000-native-20261022-01/delivery/RockPro_skrzynia_1000x1000x1000.ics'
def matrix(e,glob=True):
 s=e.QueryInterface(A.IZSceneElement);m=s.GetTransformToGlobal() if glob else s.GetTransformToParent()
 return [[m.GetValue(i,j) for j in range(4)] for i in range(4)]
def children(e):
 if not e.GetChildrenCount():return []
 arr=e.GetChildrenZArray();return [arr.Get(i).QueryInterface(A.IZElement) for i in range(arr.Count())]
def info(e):
 r=dict(id=e.Id,name=e.Name,world=matrix(e),parent=matrix(e,False))
 try:
  p=e.QueryInterface(A.IZPart);r['bbox']=list(p.GetBoundingBox(True))
  f=p.QueryInterface(A.IZPartFeatureMgr).GetFeatureAt(0).QueryInterface(A.IZElement)
  b=f.QueryInterface(A.IZSizeBox)
  r['feature']=dict(id=f.Id,world=matrix(f),parent=matrix(f,False),size=[b.Length,b.Width,b.Height],resize=[b.LengthResizeBehavior,b.WidthResizeBehavior,b.HeightResizeBehavior])
 except Exception as x:r['feature_error']=str(x)
 return r
if __name__=='__main__':
 target=OUT/'working_input.ics'
 with SOURCE.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
 app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
 opened,doc=app.OpenFile2(str(target),False,False)
 assert not opened
 try:
  scene=doc.QueryInterface(A.IZSceneDoc);roots=children(scene.GetTopElement())
  rows=[]
  for e in roots:
   r=info(e)
   if 'feature_error' in r:r['children']=[info(c) for c in children(e)]
   rows.append(r)
  (OUT/'inspection.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
  print(json.dumps([{'id':r['id'],'name':r['name'],'feature':r.get('feature'),'children':len(r.get('children',[]))} for r in rows],indent=2))
 finally:
  if doc.Modified:scene.SaveAsCopy(str(OUT/'inspection_recovery.ics'),A.Z_LINKS_COPY_ALL,False)
  doc.Close()
