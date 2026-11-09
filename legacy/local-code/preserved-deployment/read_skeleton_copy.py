import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from wholecase_common import *
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'))
legacy,base,doc=connect(cfg['analysis']);print('CONNECTED',doc.Name)
scene=doc.QueryInterface(ICAPI.IZSceneDoc)
report={'source':cfg['source'],'snapshot':cfg['snapshot'],'groups':[]}
for half in ['góra','dół']:
 group=find(scene,[half,'konstrukcja']); row=element_data(group);row['half']=half;row['panels']=[]
 for p in children(group):
  item=element_data(p);item['features']=[element_data(f) for f in children(p)];row['panels'].append(item)
 report['groups'].append(row)
Path(cfg['folder'],'recognition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for g in report['groups']:
 print(g['half'],g['id'])
 for p in g['panels']:print(p['id'],p['name'],p.get('bbox_local'),[(f['name'],f.get('sizebox')) for f in p['features']])
