import sys,json
from pathlib import Path
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
doc=base.ActiveDoc;scene=doc.QueryInterface(A.IZSceneDoc)
def kids(e):
 e=e.QueryInterface(A.IZElement)
 try:e.QueryInterface(A.IZAssembly)
 except:return []
 if not e.GetChildrenCount():return []
 a=e.GetChildrenZArray();return [a.Get(i).QueryInterface(A.IZElement) for i in range(e.GetChildrenCount())]
def row(e):
 se=e.QueryInterface(A.IZSceneElement);m=se.GetTransformToGlobal()
 r=dict(id=e.Id,name=e.Name,world=[[m.GetValue(i,j) for j in range(4)] for i in range(4)])
 for cls in (A.IZPart,A.IZAssembly):
  try:r['bounds_local_m']=list(e.QueryInterface(cls).GetBoundingBox(True));break
  except:pass
 return r
roots=kids(scene.GetTopElement());rows=[]
def walk(e,path):
 r=row(e);r['path']=path;rows.append(r)
 for i,c in enumerate(kids(e)):walk(c,path+[i])
for i,e in enumerate(roots):walk(e,[i])
r=dict(document=str(doc.Name),modified=bool(doc.Modified),rows=rows)
Path(sys.argv[1]).write_text(json.dumps(r,indent=2),encoding='utf-8')
print('Document',doc.Name,'roots',len(roots))
print(json.dumps([r for r in rows if len(r['path'])==1 or r['name']=='H2026'],indent=2))

