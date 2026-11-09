import json,math
from pathlib import Path
p=Path('artifacts/corner410429-20261022/hidden-source/fresh_corner_panel_evidence.json');r=json.loads(p.read_text(encoding='utf-8'))
for n in r['rows']:
 if n.get('kind')!='part' or n.get('name')!='410429':continue
 rows=[]
 for f in n['planar_faces']:
  norm=f['oriented_normal_local'];axis=max(range(3),key=lambda j:abs(norm[j]));vs=f['vertices_local_mm'];lo=[min(v[j] for v in vs) for j in range(3)];hi=[max(v[j] for v in vs) for j in range(3)]
  area=math.prod(hi[j]-lo[j] for j in range(3) if j!=axis)
  rows.append({'face_id':f['face_id'],'normal':norm,'local_axis':axis,'coord':sum(v[axis] for v in vs)/len(vs),'span':[lo,hi],'area_candidate':area})
 rows.sort(key=lambda f:-f['area_candidate'])
 print(json.dumps({'id':n['id'],'faces':rows[:8]}))
