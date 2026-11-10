import json,sys
from wholecase_common import *
from review_skeleton_geometry import validate
sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));folder=Path(cfg['folder']);m=json.loads((folder/'skeleton_manifest.json').read_text(encoding='utf-8'));legacy,base,doc=connect(m['file']);scene=doc.QueryInterface(ICAPI.IZSceneDoc)
def capture(scene):
 u=scene.QueryInterface(ICAPI.IZSceneDocUtility);pm=scene.ParameterMgr;v={n:pm.GetParameterByName(n).Value*1000 for n in m['parameters_mm']};data={'parameters_mm':v,'halves':{}}
 for half,h,closure in [('base','RP_BaseHeight','bottom'),('lid','RP_LidHeight','top')]:
  d={'length_mm':v['RP_Length'],'depth_mm':v['RP_Depth'],'height_mm':v[h],'thickness_mm':v['RP_Thickness'],'closure':closure,'panels':[]}
  for row in m['panels']:
   if row['half']!=half:continue
   p=u.GetElementById(row['id']);b=transformed_bbox(bbox(p,True),matrix(p));d['panels'].append({'role':row['role'],'id':p.Id,'bbox_mm':[x*1000 for x in b]})
  data['halves'][half]=d
 return data
variants=[('baseline',{}),('length',{'RP_Length':1014}),('depth',{'RP_Depth':662}),('base_height',{'RP_BaseHeight':289.24}),('lid_height',{'RP_LidHeight':144.13}),('thickness',{'RP_Thickness':12}),('combined',{'RP_Length':1040,'RP_Depth':700,'RP_BaseHeight':300,'RP_LidHeight':150,'RP_Thickness':12}),('smaller',{'RP_Length':800,'RP_Depth':500,'RP_BaseHeight':200,'RP_LidHeight':80}),('return',{})]
results=[]
try:
 for name,changes in variants:
  for n,v in (m['parameters_mm']|changes).items():scene.ParameterMgr.GetParameterByName(n).Expression=f'{v} mm'
  scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
  data=capture(scene);review=validate(data);data['review']=review
  (folder/f'measured_{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  print(name,review['passed'],review['errors'],flush=True);results.append({'variant':name,'passed':review['passed'],'errors':review['errors']})
finally:
 for n,v in m['parameters_mm'].items():scene.ParameterMgr.GetParameterByName(n).Expression=f'{v} mm'
 scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update();doc.Save()
(folder/'skeleton_tests.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
