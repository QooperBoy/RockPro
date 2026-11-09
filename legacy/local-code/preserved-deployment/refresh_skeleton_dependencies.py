import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from wholecase_common import *
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));folder=Path(cfg['folder']);m=json.loads((folder/'skeleton_manifest.json').read_text(encoding='utf-8'));legacy,base,doc=connect(m['file']);scene=doc.QueryInterface(ICAPI.IZSceneDoc);u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
def ex(s,depth):
 for n in sorted(m['parameters_mm'],key=len,reverse=True):s=s.replace(n,'Parent\\'*depth+'Params\\'+n)
 return s
for r in m['panels']:
 p=u.GetElementById(r['id']);part=p.QueryInterface(ICAPI.IZPart)
 print(r['id'],'linked',part.HasInternalLinks(),flush=True)
 if part.HasInternalLinks():part.Unlink()
 f=u.GetElementById(r['feature_id']);sb=f.QueryInterface(ICAPI.IZSizeBox)
 for attr,expr in zip(['LengthExpression','WidthExpression','HeightExpression'],r['size_expr']):setattr(sb,attr,ex(expr,3))
 for i,expr in enumerate(r['position_expr']):p.QueryInterface(ICAPI.IZSceneElement).PositionTransformComponentExpression[i]=ex(expr,2)
 for e in [f,p]:
  try:e.QueryInterface(ICAPI.IZSceneElement).ForceSetupParameterExpression()
  except Exception as err:print('setup',err)
scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update();doc.Save()
