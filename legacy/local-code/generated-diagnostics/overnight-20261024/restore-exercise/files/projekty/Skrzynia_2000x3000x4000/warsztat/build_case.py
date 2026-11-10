"""One isolated full-case prototype; persistent scene parameters, opaque hardware."""
from inspect_case import *
import hashlib, itertools, traceback

PARAMS={'RP_Length':2000.,'RP_Depth':3000.,'RP_BaseHeight':3600.,'RP_LidHeight':400.,'RP_Thickness':9.8,'RP_DisplayGap':0.}
BASE={'RP_Length':1000.,'RP_Depth':1000.,'RP_BaseHeight':895.87,'RP_LidHeight':104.13,'RP_Thickness':9.8,'RP_DisplayGap':0.}
ORIGIN=[558.0497847073995,896.4261794940822,-1503.0399167133687]
RESULT=OUT/'RockPro_skrzynia_2000x3000x4000_parametryczna.ics'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ex(s,depth=1):
 for n in sorted(PARAMS,key=len,reverse=True):s=s.replace(n,'Parent\\'*depth+'Params\\'+n)
 return s
def update(scene):
 scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True);scene.Update()
def bbox(e):
 try:b=list(e.QueryInterface(A.IZPart).GetBoundingBox(True))
 except Exception:b=list(e.QueryInterface(A.IZAssembly).GetBoundingBox(True))
 m=matrix(e);pts=[[sum(p[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)] for p in itertools.product(*zip(b[:3],b[3:]))]
 return [1000*min(p[j] for p in pts) for j in range(3)]+[1000*max(p[j] for p in pts) for j in range(3)]
def mark(e):
 e.SetDirtyFlag(A.Z_DIRTY_GRAPHICS)
 try:e.QueryInterface(A.IZAssembly)
 except comtypes.COMError:return
 for c in children(e):mark(c)
def run():
 assert not RESULT.exists(),'Refusing to overwrite delivery'
 sourcehash=sha(SOURCE);app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
 already,doc=app.OpenFile2(str(OUT/'working_input.ics'),False,False);assert not already
 scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility)
 report={'source':str(SOURCE),'source_sha256':sourcehash,'parameters_mm':PARAMS,'bindings':[],'checks':[],'production_approved':False}
 try:
  for n,v in BASE.items():
   p=scene.ParameterMgr.CreateParameter(A.Z_PARAMETER_TYPE_LENGTH,n,v/1000);p.Expression=f'{v} mm';p.ParamTableVisibility=True
   p.Notes={'RP_Length':'Dlugosc zewnetrzna plyt','RP_Depth':'Glebokosc zewnetrzna plyt','RP_BaseHeight':'Wysokosc podstawy wraz z dnem','RP_LidHeight':'Wysokosc zdejmowanego wieka','RP_Thickness':'Grubosc plyt','RP_DisplayGap':'Rozsuniecie wieka do podgladu'}[n]
  L='RP_Length';D='RP_Depth';T='RP_Thickness';B='RP_BaseHeight';H='RP_LidHeight';G='RP_DisplayGap'
  definitions=[]
  for half,ids,h,z in [('base',[3,7,11,15],B,T),('lid',[19,23,27,31],H,B+' + '+G)]:
   dims=[[L,T,h+' - '+T],[L,T,h+' - '+T],[T,D+' - 2*'+T,h+' - '+T],[T,D+' - 2*'+T,h+' - '+T]]
   pos=[['0 mm','0 mm',z],['0 mm',D+' - '+T,z],['0 mm',T,z],[L+' - '+T,T,z]]
   for id,ds,ps,role in zip(ids,dims,pos,['przod','tyl','lewa','prawa']):definitions.append((id,ds,ps,half+' - '+role))
  definitions += [(35,[L,D,T],['0 mm','0 mm','0 mm'],'dno'),(39,[L,D,T],['0 mm','0 mm',B+' + '+G+' + '+H+' - '+T],'wieko')]
  template=REPO.parent/'Integracja/skeleton/20261020T110925Z/Clean_panel_template.ics'
  assembly=scene.GetTopElement().QueryInterface(A.IZAssembly)
  newdefs=[]
  for id,ds,ps,label in definitions:
   u.GetElementById(id).Remove()
   e=assembly.AddChildFromExternalFile(str(template),False).QueryInterface(A.IZElement)
   id=e.Id
   feature=e.QueryInterface(A.IZPartFeatureMgr).GetFeatureAt(0).QueryInterface(A.IZElement)
   fs=feature.QueryInterface(A.IZSizeBox)
   for axis,s in zip(['Length','Width','Height'],ds):setattr(fs,axis+'Expression',ex(s,2))
   feature.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
   ps=[f'({ps[0]}) + ({ds[0]})/2',f'({ps[1]}) + ({ds[1]})/2',ps[2]]
   se=e.QueryInterface(A.IZSceneElement)
   for i,s in enumerate(ps):se.PositionTransformComponentExpression[i]=ex(s)
   se.ForceSetupParameterExpression();e.Name='RockPro - '+label
   report['bindings'].append(dict(id=id,feature_id=feature.Id,kind='panel',size=ds,position=ps))
   newdefs.append((id,ds,ps,label))
  definitions=newdefs
  evidence=json.loads((REPO/'artifacts/cube1000-native-20261022-01/single_1000x1000x1000_before.json').read_text())
  hardware_motion={}
  for kind in ['corners','latches','handles']:
   for row in evidence[kind]:
    id=row['native_id'];e=u.GetElementById(id);se=e.QueryInterface(A.IZSceneElement);world=row['matrix_world_mm'];local=row['matrix_parent_mm']
    # Parent rotation in row-vector convention, including preserved catalog mirrors.
    r=[[sum(local[k][i]*world[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    depth=2 if kind=='corners' else 1
    pos=world[3];motion={L:[1. if pos[0]>ORIGIN[0]+500 else 0.,0,0],D:[0,1. if pos[1]>ORIGIN[1]+500 else 0.,0]}
    if kind=='corners' and pos[2]>ORIGIN[2]+500:motion.update({B:[0,0,1],H:[0,0,1],G:[0,0,1]})
    elif kind=='latches':
     motion[B]=[0,0,1]
     if row['source_id'] in [12631,12782]:motion[G]=[0,0,1]
    elif kind=='handles':motion[B]=[0,0,.5]
    hardware_motion[id]=motion
    expressions=[]
    for i in range(3):
     value=local[3][i]-sum(ORIGIN[j]*r[i][j] for j in range(3))
     s=f'{value:.15g} mm'
     for n,vec in motion.items():
      c=sum(vec[j]*r[i][j] for j in range(3))
      if abs(c)>1e-8:s+=f' + ({c:.12g}) * ({n} - {BASE[n]} mm)'
     se.PositionTransformComponentExpression[i]=ex(s,depth);expressions.append(s)
    se.ForceSetupParameterExpression();report['bindings'].append(dict(id=id,kind=kind,position=expressions))
  def setparams(values):
   for n,v in values.items():scene.ParameterMgr.GetParameterByName(n).Expression=f'{v} mm'
   for binding in report['bindings']:
    if binding['kind']=='panel':
     fs=u.GetElementById(binding['feature_id']).QueryInterface(A.IZSizeBox)
     for axis,s in zip(['Length','Width','Height'],binding['size']):setattr(fs,axis+'Expression',ex(s,2))
     u.GetElementById(binding['feature_id']).QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
    u.GetElementById(binding['id']).QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
   update(scene);update(scene)
  def check(label,values):
   expected=[values[L],values[D],values[B]+values[H]+values[G]];boxes=[bbox(u.GetElementById(id)) for id,*_ in definitions]
   extent=[min(b[i] for b in boxes) for i in range(3)]+[max(b[i+3] for b in boxes) for i in range(3)]
   for box,(id,ds,ps,_) in zip(boxes,definitions):
    env={n:v for n,v in values.items()}
    size=[eval(s.replace(' mm',''),{'__builtins__':{}},env) for s in ds]
    assert max(abs(box[j+3]-box[j]-size[j]) for j in range(3))<.05,('Panel size',label,id,box,size)
   assert max(abs(extent[i]) for i in range(3))<.05,(label,extent)
   assert max(abs(extent[i+3]-expected[i]) for i in range(3))<.05,(label,extent,expected,boxes)
   hw={str(row['native_id']):matrix(u.GetElementById(row['native_id'])) for k in ['corners','latches','handles'] for row in evidence[k]}
   for k in ['corners','latches','handles']:
    for row in evidence[k]:
     m=hw[str(row['native_id'])];old=row['matrix_world_mm']
     assert max(abs(m[i][j]-old[i][j]) for i in range(3) for j in range(3))<1e-7,'Hardware rotation changed'
     desired=[old[3][j]-ORIGIN[j]+sum(vec[j]*(values[n]-BASE[n]) for n,vec in hardware_motion[row['native_id']].items()) for j in range(3)]
     assert max(abs(m[3][j]*1000-desired[j]) for j in range(3))<.05,('Hardware placement',row['native_id'],m[3],desired)
   report['checks'].append(dict(label=label,panel_extent_mm=extent,hardware_world_matrices_m=hw))
   print(label,extent,flush=True)
  setparams(PARAMS);check('target',PARAMS)
  alternative=dict(PARAMS,RP_Length=2200.,RP_Depth=3100.,RP_BaseHeight=3700.,RP_LidHeight=450.,RP_DisplayGap=100.,RP_Thickness=12.)
  setparams(alternative);check('resize',alternative)
  setparams(PARAMS);check('restored',PARAMS)
  mark(scene.GetTopElement());scene.Update()
  for name in ['UpdateGraphics','Redraw']:
   try:getattr(scene,name)(0) if name=='UpdateGraphics' else getattr(scene,name)()
   except Exception as error:report.setdefault('graphics_notes',[]).append(str(error))
  scene.SaveAs(str(RESULT),A.Z_LINKS_COPY_ALL,False);doc.Close();doc=None
  already,doc=app.OpenFile2(str(RESULT),False,False);assert not already
  scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility);check('reopened',PARAMS)
  assert sha(SOURCE)==sourcehash
  report.update(passed=True,result=str(RESULT),result_sha256=sha(RESULT),source_unchanged=True)
 finally:
  if doc is not None:
   if doc.Modified:scene.SaveAsCopy(str(OUT/'owned_recovery.ics'),A.Z_LINKS_COPY_ALL,False)
   doc.Close()
  (OUT/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':run()
