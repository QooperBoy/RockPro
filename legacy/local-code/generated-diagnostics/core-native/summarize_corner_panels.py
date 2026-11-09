import json,math
from pathlib import Path
p=Path('artifacts/corner410429-20261022/hidden-source/fresh_panels.json');r=json.loads(p.read_text(encoding='utf-8'))
rows=[]
for n in r['rows']:
 planes=[]
 for f in n['planar_faces']:
  normal=f['oriented_normal_world'];axis=max(range(3),key=lambda j:abs(normal[j]))
  vs=f['vertices_world_mm'];lo=[min(v[j] for v in vs) for j in range(3)];hi=[max(v[j] for v in vs) for j in range(3)]
  area=math.prod(hi[j]-lo[j] for j in range(3) if j!=axis)
  if area>10000:planes.append({'face_id':f['face_id'],'normal':normal,'axis':axis,'coord':sum(v[axis] for v in vs)/len(vs),'span':[lo,hi],'area_candidate':area})
 rows.append({'id':n['id'],'name':n['name'],'path':n['occurrence_path'],'matrix':n['matrix_world_mm'],'large_planes':planes})
Path('artifacts/corner410429-20261022/hidden-source/panel_plane_summary.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for row in rows:print(json.dumps(row))
