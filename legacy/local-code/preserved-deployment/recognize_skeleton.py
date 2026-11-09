import json,hashlib,sys
from datetime import datetime,timezone
from wholecase_common import *
sys.stdout.reconfigure(encoding='utf-8')
source=ROOT.parent/'AI_CAD/T_1_1/Epson EB-PU2216B (2).ics'
legacy,base,doc=connect(source)
scene=doc.QueryInterface(ICAPI.IZSceneDoc)
folder=ROOT/'skeleton'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');folder.mkdir(parents=True)
copy=folder/'Epson_source_snapshot.ics'
scene.SaveAsCopy(str(copy),ICAPI.Z_LINKS_COPY_ALL,False)
report={'source':str(source),'source_hash':hashlib.sha256(source.read_bytes()).hexdigest(),'source_saved':bool(legacy.Saved),'snapshot':str(copy),'groups':[]}
for half in ['góra','dół']:
 group=find(scene,[half,'konstrukcja']); row=element_data(group);row['half']=half;row['panels']=[]
 for p in children(group):
  item=element_data(p);item['features']=[]
  for f in children(p):
   d=element_data(f)
   try:d['parameters']=[parameter_data(x) for x in parameters(f)]
   except Exception:pass
   item['features'].append(d)
  row['panels'].append(item)
 report['groups'].append(row)
(folder/'recognition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'skeleton_state.json').write_text(json.dumps({'folder':str(folder)},indent=2),encoding='utf-8')
for g in report['groups']:
 print(g['half'],g['id'])
 for p in g['panels']: print(p['id'],p['name'],p.get('sizebox'),p.get('bbox_local'),[(x['id'],x['name'],x.get('sizebox')) for x in p['features']])
print(folder)
