"""Update comments only, preserving all live parameter values and expressions."""
import json, sys, shutil
from datetime import datetime
from wholecase_common import *
from skeleton_parameter_notes import PARAMETER_NOTES
sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'))
folder=Path(cfg['folder'])
target=folder/'RockPro_Epson_szkielet_MVP.ics'
legacy,base,doc=connect(target)
scene=doc.QueryInterface(ICAPI.IZSceneDoc)
mgr=scene.ParameterMgr
params={mgr.GetParameter(i).Name:mgr.GetParameter(i) for i in range(mgr.Count)}
assert set(PARAMETER_NOTES)<=set(params)
before={n:{'expression':p.Expression,'value':p.Value,'notes':p.Notes} for n,p in params.items()}
stamp=datetime.now().strftime('%Y%m%dT%H%M%S')
backup=folder/f'RockPro_Epson_szkielet_MVP_before_notes_{stamp}.ics'
shutil.copy2(target,backup)
for n,note in PARAMETER_NOTES.items(): params[n].Notes=note
after={n:{'expression':p.Expression,'value':p.Value,'notes':p.Notes} for n,p in params.items()}
assert all(before[n]['expression']==after[n]['expression'] and before[n]['value']==after[n]['value'] for n in before)
assert all(after[n]['notes']==note for n,note in PARAMETER_NOTES.items())
doc.Save()
report={'file':str(target),'disk_backup':str(backup),'before':before,'after':after,'values_and_expressions_unchanged':True}
(folder/f'parameter_notes_update_{stamp}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
