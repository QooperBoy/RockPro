"""Build a native ten-panel skeleton from measured source dimensions; no old constraints."""
import json,sys
from skeleton_parameter_notes import PARAMETER_NOTES
from skeleton_panel_labels import panel_label
from wholecase_common import *
sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));folder=Path(cfg['folder']);values=json.loads((folder/'skeleton_parameters.json').read_text(encoding='utf-8'))
assert not (folder/'RockPro_Epson_szkielet_MVP.ics').exists(), 'Refusing to overwrite an existing model'
legacy,base,probe=connect(folder/'Skeleton_probe_drop.ics');prototype=probe.QueryInterface(ICAPI.IZSceneDoc).GetFirstChild().QueryInterface(ICAPI.IZPartFeatureMgr).GetFeatureAt(0)
if not (folder/'Clean_panel_template.ics').exists(): prototype.QueryInterface(ICAPI.IZElement).GetParent().QueryInterface(ICAPI.IZPart).SaveAs(str(folder/'Clean_panel_template.ics'),False)
scene=base.QueryInterface(ICAPI.IZIronCADApp).OpenNewScene(False,True,'')
initial={'RP_Length':values['length_mm'],'RP_Depth':values['depth_mm'],'RP_BaseHeight':values['base_height_mm'],'RP_LidHeight':values['lid_height_mm'],'RP_Thickness':values['thickness_mm'],'RP_DisplayGap':values['display_gap_mm']}
for n,v in initial.items():
 p=scene.ParameterMgr.CreateParameter(ICAPI.Z_PARAMETER_TYPE_LENGTH,n,v/1000);p.Expression=f'{v} mm';p.ParamTableVisibility=True;p.Notes=PARAMETER_NOTES[n]
manifest={'file':str(folder/'RockPro_Epson_szkielet_MVP.ics'),'parameters_mm':initial,'assemblies':{},'panels':[],'source':cfg['snapshot'],'normalizations':values['normalizations']}
def ex(s,depth):
 for n in sorted(initial,key=len,reverse=True):s=s.replace(n,'Parent\\'*depth+'Params\\'+n)
 return s
L='RP_Length';D='RP_Depth';T='RP_Thickness'
for half,h,name in [('base','RP_BaseHeight','dół — konstrukcja'),('lid','RP_LidHeight','góra — konstrukcja')]:
 a=scene.CreateAssembly();ae=a.QueryInterface(ICAPI.IZElement);ae.Name=name;manifest['assemblies'][half]=ae.Id
 if half=='lid':ae.QueryInterface(ICAPI.IZSceneElement).PositionTransformComponentExpression[2]=ex('RP_BaseHeight + RP_DisplayGap',1)
 wallz=T if half=='base' else '0 mm';closurez='0 mm' if half=='base' else h+' - '+T
 defs=[('front','przód',[L,T,h+' - '+T],[L+'/2',T+'/2',wallz]),('back','tył',[L,T,h+' - '+T],[L+'/2',D+' - '+T+'/2',wallz]),('left','lewa',[T,D+' - 2*'+T,h+' - '+T],[T+'/2',D+'/2',wallz]),('right','prawa',[T,D+' - 2*'+T,h+' - '+T],[L+' - '+T+'/2',D+'/2',wallz]),('closure','dno' if half=='base' else 'wieko',[L,D,T],[L+'/2',D+'/2',closurez])]
 for role,label,dims,pos in defs:
  label=panel_label(half,role)
  pe=a.AddChildFromExternalFile(str(folder/'Clean_panel_template.ics'),False);p=pe.QueryInterface(ICAPI.IZPart);pe.Name=label;f=p.QueryInterface(ICAPI.IZPartFeatureMgr).GetFeatureAt(0).QueryInterface(ICAPI.IZElement);f.Name='Plyta'
  sb=f.QueryInterface(ICAPI.IZSizeBox)
  for attr,expr in zip(['LengthExpression','WidthExpression','HeightExpression'],dims):setattr(sb,attr,ex(expr,3))
  se=pe.QueryInterface(ICAPI.IZSceneElement)
  for i,expr in enumerate(pos):se.PositionTransformComponentExpression[i]=ex(expr,2)
  p.Regenerate();manifest['panels'].append({'half':half,'role':role,'id':pe.Id,'feature_id':f.Id,'name':label,'size_expr':dims,'position_expr':pos});print(half,label,flush=True)
# Imports can replace dependency caches: bind every panel after all imports.
u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
for r in manifest['panels']:
 pe=u.GetElementById(r['id']);f=u.GetElementById(r['feature_id']);sb=f.QueryInterface(ICAPI.IZSizeBox)
 for attr,expr in zip(['LengthExpression','WidthExpression','HeightExpression'],r['size_expr']):setattr(sb,attr,ex(expr,3))
 for i,expr in enumerate(r['position_expr']):pe.QueryInterface(ICAPI.IZSceneElement).PositionTransformComponentExpression[i]=ex(expr,2)
 f.QueryInterface(ICAPI.IZSceneElement).ForceSetupParameterExpression()
 pe.QueryInterface(ICAPI.IZSceneElement).ForceSetupParameterExpression()
scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update();scene.SaveAs(manifest['file'],ICAPI.Z_LINKS_COPY_ALL,False)
(folder/'skeleton_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('SAVED',manifest['file'],flush=True)



