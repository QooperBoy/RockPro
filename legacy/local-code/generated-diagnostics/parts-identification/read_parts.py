import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from ironcad_adapter import connect,ICAPI
source=Path('../AI_CAD/T_1_1/Showcase_Epson_parametry.ics').resolve()
_,_,doc=connect(source);scene=doc.QueryInterface(ICAPI.IZSceneDoc);out=[]
def visit(e,path=(),depth=0):
 e=e.QueryInterface(ICAPI.IZElement);path=path+(e.Name,);r=dict(id=e.Id,path=list(path),type=e.Type)
 try:r['children']=e.GetChildrenCount()
 except Exception as ex:r['children']=0;r['children_error']=str(ex)
 try:
  p=e.QueryInterface(ICAPI.IZPart);r.update(bom_number=p.BOMPartNumber,bom_description=p.BOMDescription,included=p.IncludedInBOM,hidden=p.IsHidden,bbox_raw=list(p.GetBoundingBox(True)))
 except Exception:pass
 try:r['material']=e.GetMaterialNameProperty()
 except Exception:pass
 out.append(r)
 print('read',len(out),e.Id,flush=True)
 if depth<5 and r['children']>0 and len(out)<1200:
  try:
   ch=e.GetChildrenZArray()
   for i in range(ch.Count()):visit(ch.Get(i),path,depth+1)
  except Exception as ex:r['walk_error']=str(ex)
visit(scene.GetTopElement())
p=Path('artifacts/parts-identification/native_inventory.json');p.write_text(json.dumps(dict(source=str(source),rows=out),ensure_ascii=False,indent=2),encoding='utf-8')
print('nodes',len(out),'parts with BOM',sum('bom_number'in r for r in out))
for r in out:
 if any(s in r['path'] for s in ['Część2648','2643','koła']) or r.get('bom_description'):print(json.dumps(r,ensure_ascii=True))

