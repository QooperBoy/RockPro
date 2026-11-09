exec(open('read_legacy_panels.py',encoding='utf-8-sig').read().split('for i in range')[0])
from pathlib import Path
cfg=json.loads(Path('skeleton_state.json').read_text(encoding='utf-8-sig'));rows=[]
for i in range(1,r.ChildShapes.Count+1):
 h=r.ChildShapes.Item(i)
 for j in range(1,h.ChildShapes.Count+1):
  g=h.ChildShapes.Item(j)
  if g.Name!='konstrukcja':continue
  for k in range(1,g.ChildShapes.Count+1):
   p=g.ChildShapes.Item(k);b=p.InstanceShape.BoundingBox
   box=[getattr(b,x) for x in ['MinX','MinY','MinZ','MaxX','MaxY','MaxZ']]
   row={'half':h.Name,'name':p.Name,'legacy_id':p.TSID,'bbox_raw':box,'dimensions_raw':[box[x+3]-box[x] for x in range(3)]};rows.append(row);print(row)
Path(cfg['folder'],'legacy_panels.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
