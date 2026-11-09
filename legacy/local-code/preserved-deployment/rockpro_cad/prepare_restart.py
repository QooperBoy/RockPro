import sys,json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from ironcad_adapter import connect,ICAPI
sys.stdout.reconfigure(encoding='utf-8')
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'))
folder=Path(cfg['folder'])
legacy,base,doc=connect(folder/'RockPro_Epson_szkielet_MVP.ics')
paths=[str(folder/n) for n in ['Epson_analysis_copy.ics','Skeleton_probe.ics','Skeleton_probe_drop.ics','RockPro_Epson_szkielet.ics','RockPro_Epson_szkielet_MVP.ics']]
print('Open count',base.GetOpenDocsCount(),flush=True)
docs=[]
for path in paths:
 d=base.GetOpenDocByName(path)
 if not d:raise RuntimeError('Cannot find '+path)
 docs.append(d)
 print(d.Name,flush=True)
assert len(docs)==base.GetOpenDocsCount(),'Unexpected open documents; abort'
unsaved=base.ActiveDoc
assert unsaved.Name in ('Scene3','Scene3*'), 'Expected unsaved Scene3 selected'
docs.append(unsaved)
if '--save' in sys.argv:
 out=ROOT/'rockpro_cad'/'session_backups'/datetime.now().strftime('%Y%m%dT%H%M%S')
 out.mkdir(parents=True)
 rows=[]
 for i,d in enumerate(docs):
  target=out/(str(i)+'_'+Path(d.Name).stem+'.ics')
  d.QueryInterface(ICAPI.IZSceneDoc).SaveAsCopy(str(target),ICAPI.Z_LINKS_COPY_ALL,False)
  assert target.exists() and target.stat().st_size>1000
  rows.append({'name':d.Name,'backup':str(target)})
 (out/'session.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Backups',out,flush=True)
 for d in docs:d.Close2(True)
 legacy.Application.Quit()
 print('Restart ready',flush=True)
