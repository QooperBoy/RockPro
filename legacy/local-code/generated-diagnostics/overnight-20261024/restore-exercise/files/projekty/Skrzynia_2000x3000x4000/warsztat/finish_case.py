from build_case import *
import re
report=json.loads((OUT/'build_report.json').read_text())
assert len(report['checks'])==3
app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
already,doc=app.OpenFile2(str(OUT/'owned_recovery.ics'),False,False);assert not already
scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility)
def number(s,values):
 # Only trusted formulas authored in build_case.py; no external input evaluation.
 for name,val in values.items():s=s.replace(name,str(val))
 s=s.replace(' mm','')
 assert re.fullmatch(r'[0-9eE .()+*/-]+',s)
 return eval(s,{'__builtins__':{}},{})
def verify(label,values):
 for r in report['bindings']:
  e=u.GetElementById(r['id'])
  if r['kind']=='panel':
   box=bbox(e);dims=[box[i+3]-box[i] for i in range(3)]
   expected=[number(s,values) for s in r['size']]
   assert max(abs(dims[i]-expected[i]) for i in range(3))<.05,(label,r['id'],dims,expected)
  se=e.QueryInterface(A.IZSceneElement)
  for i,s in enumerate(r['position']):assert abs(se.PositionTransformComponentValue[i]*1000-number(s,values))<.05,(label,r['id'],'position')
 print(label,'PASS',flush=True)
 report.setdefault('persistent_expression_checks',[]).append({'label':label,'passed':True})
def setvalues(values):
 for n,v in values.items():scene.ParameterMgr.GetParameterByName(n).Expression=f'{v} mm'
 update(scene)
try:
 verify('recovery_target',PARAMS)
 alt=dict(PARAMS,RP_Length=2100.,RP_Depth=3200.,RP_BaseHeight=3650.,RP_LidHeight=420.,RP_Thickness=11.,RP_DisplayGap=80.)
 setvalues(alt);verify('parameter_only_resize',alt)
 setvalues(PARAMS);verify('parameter_only_restore',PARAMS)
 mark(scene.GetTopElement());scene.Update()
 for action in ['UpdateGraphics','Redraw']:
  try:getattr(scene,action)(0) if action=='UpdateGraphics' else getattr(scene,action)()
  except Exception as error:report.setdefault('graphics_notes',[]).append(str(error))
 assert not RESULT.exists()
 scene.SaveAs(str(RESULT),A.Z_LINKS_COPY_ALL,False);doc.Close();doc=None
 _,doc=app.OpenFile2(str(RESULT),False,False);scene=doc.QueryInterface(A.IZSceneDoc);u=scene.QueryInterface(A.IZSceneDocUtility)
 verify('saved_reopened',PARAMS)
 assert sha(SOURCE)==report['source_sha256']
 report.update(passed=True,result=str(RESULT),result_sha256=sha(RESULT),source_unchanged=True)
finally:
 if doc is not None:
  if doc.Modified:scene.SaveAsCopy(str(OUT/'final_recovery.ics'),A.Z_LINKS_COPY_ALL,False)
  doc.Close()
 (OUT/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if report.get('passed'):
 app.OpenFile2(str(RESULT),False,True)
 print('Delivery opened for review',flush=True)

