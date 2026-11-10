import json, sys, shutil
from datetime import datetime
from wholecase_common import *
from skeleton_panel_labels import panel_label
sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'))
folder=Path(cfg['folder'])
manifest_path=folder/'skeleton_manifest.json'
m=json.loads(manifest_path.read_text(encoding='utf-8'))
legacy,base,doc=connect(m['file'])
scene=doc.QueryInterface(ICAPI.IZSceneDoc)
utility=scene.QueryInterface(ICAPI.IZSceneDocUtility)
stamp=datetime.now().strftime('%Y%m%dT%H%M%S')
shutil.copy2(m['file'],folder/f'RockPro_Epson_before_labels_{stamp}.ics')
shutil.copy2(manifest_path,folder/f'skeleton_manifest_before_labels_{stamp}.json')
def state():
    pm=scene.ParameterMgr
    return {
        'parameters':[(pm.GetParameter(i).Name,pm.GetParameter(i).Expression,pm.GetParameter(i).Value) for i in range(pm.Count)],
        'expressions':[
            {
                'id':r['id'],
                'size':[getattr(utility.GetElementById(r['feature_id']).QueryInterface(ICAPI.IZSizeBox),a) for a in ['LengthExpression','WidthExpression','HeightExpression']],
                'position':[utility.GetElementById(r['id']).QueryInterface(ICAPI.IZSceneElement).PositionTransformComponentExpression[i] for i in range(3)]
            } for r in m['panels']
        ]
    }
before=state()
changes=[]
for r in m['panels']:
    el=utility.GetElementById(r['id'])
    label=panel_label(r['half'],r['role'])
    changes.append({'id':r['id'],'old':el.Name,'new':label})
    el.Name=label
    assert el.Name==label
    r['name']=label
assert before==state(), 'Unexpected parameter or expression change'
doc.Save()
manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/f'panel_labels_update_{stamp}.json').write_text(json.dumps({'changes':changes,'parameters_and_expressions_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(changes,ensure_ascii=False,indent=2))
