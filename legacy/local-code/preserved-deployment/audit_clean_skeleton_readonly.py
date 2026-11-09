"""Independent attach-only, read-only final skeleton audit. No CAD writes."""
import hashlib
import json
import traceback
from datetime import datetime,timezone
from wholecase_common import ROOT,Path,connect,ICAPI,children,bbox,matrix,transformed_bbox
from review_skeleton_geometry import validate
from review_skeleton_global import validate_global

cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'))
folder=Path(cfg['folder'])
manifest=json.loads((folder/'skeleton_manifest.json').read_text(encoding='utf-8'))
report={'timestamp':datetime.now(timezone.utc).isoformat(),'file':manifest['file'],
        'read_only':True,'ui_edit_verified':False,'passed':False,'errors':[]}
try:
    legacy,base,doc=connect(manifest['file'])
    scene=doc.QueryInterface(ICAPI.IZSceneDoc)
    u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
    report['saved_before']=bool(legacy.Saved)
    report['parameters']={}
    for name,target in manifest['parameters_mm'].items():
        p=scene.ParameterMgr.GetParameterByName(name)
        report['parameters'][name]={'mm':p.Value*1000,'expression':p.Expression,'visible':bool(p.ParamTableVisibility)}
        if abs(p.Value*1000-target)>.002 or not p.ParamTableVisibility:
            report['errors'].append('parameter baseline/visibility '+name)
    groups=children(scene.GetTopElement())
    report['groups']=[{'id':e.Id,'name':e.Name,'count':e.GetChildrenCount()} for e in groups]
    if len(groups)!=2 or any(g['count']!=5 for g in report['groups']):
        report['errors'].append('expected two groups each with five parts')
    values={n:v['mm'] for n,v in report['parameters'].items()}
    measured={'parameters_mm':values,'halves':{}}
    report['formulas']=[]
    for half,height,closure in [('base','RP_BaseHeight','bottom'),('lid','RP_LidHeight','top')]:
        data={'length_mm':values['RP_Length'],'depth_mm':values['RP_Depth'],'height_mm':values[height],
              'thickness_mm':values['RP_Thickness'],'closure':closure,'panels':[]}
        for item in manifest['panels']:
            if item['half']!=half:continue
            part=u.GetElementById(item['id'])
            feature=u.GetElementById(item['feature_id'])
            b=bbox(part,True)
            world=transformed_bbox(b,matrix(part))
            data['panels'].append({'role':item['role'],'bbox_mm':[x*1000 for x in world]})
            se=part.QueryInterface(ICAPI.IZSceneElement)
            sb=feature.QueryInterface(ICAPI.IZSizeBox)
            formulas={'part':item['id'],'feature':item['feature_id'],
                      'position':[se.PositionTransformComponentExpression[i] for i in range(3)],
                      'size':[sb.LengthExpression,sb.WidthExpression,sb.HeightExpression]}
            if not all(formulas['size']) or not any('RP_' in (f or '') for f in formulas['size']):
                report['errors'].append('missing native size formulas '+str(item['id']))
            if not all(formulas['position']):
                report['errors'].append('missing position formulas '+str(item['id']))
            if part.QueryInterface(ICAPI.IZPartFeatureMgr).GetFeaturesCount()!=1:
                report['errors'].append('unexpected feature count '+str(item['id']))
            report['formulas'].append(formulas)
        measured['halves'][half]=data
    report['measured']=measured
    report['geometry_review']=validate(measured)
    report['global_review']=validate_global(measured)
    report['saved_after']=bool(legacy.Saved)
    if report['saved_before']!=report['saved_after']:
        report['errors'].append('saved status changed during read-only audit')
    report['file_sha256']=hashlib.sha256(Path(manifest['file']).read_bytes()).hexdigest()
    report['passed']=not report['errors'] and report['geometry_review']['passed'] and report['global_review']['passed']
except Exception:
    report['exception']=traceback.format_exc()
finally:
    output=folder/'independent_live_review.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'errors':report['errors'],'exception':report.get('exception'),'report':str(output)},ensure_ascii=True))
