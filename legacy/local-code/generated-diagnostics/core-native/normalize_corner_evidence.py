import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import file_sha256
root=Path('artifacts/corner410429-20261022/hidden-source').resolve()
raw=json.loads((root/'fresh_corner_panel_evidence.json').read_text(encoding='utf-8'));panels=json.loads((root/'fresh_panels.json').read_text(encoding='utf-8'))
byid={r['id']:r for r in panels['rows']}
selected=[(0,0,208,3),(0,1,204,1),(1,0,200,1),(1,1,212,3),(2,0,216,3),(2,1,195,3)]
planes=[];bounds=[[None,None] for _ in range(3)]
for axis,side,nid,fid in selected:
 f=next(f for f in byid[nid]['planar_faces'] if f['face_id']==fid)
 vs=f['vertices_world_mm'];coordinate=sum(v[axis] for v in vs)/len(vs)
 assert max(abs(v[axis]-coordinate) for v in vs)<1e-6
 assert max(abs(f['oriented_normal_world'][j]-((2*side-1) if j==axis else 0)) for j in range(3))<1e-6
 bounds[axis][side]=coordinate
 planes.append({'axis':axis,'side':side,'node_id':nid,'face_id':fid,'vertices_world_mm':vs,'normal_world':f['oriented_normal_world']})
frame=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[b[0] for b in bounds]+[1]]
size=[b[1]-b[0] for b in bounds]
assemblies=[{'id':r['id'],'occurrence_path':r['occurrence_path'],'matrix_world_mm':r['matrix_world_mm']} for r in raw['rows'] if r.get('name')=='410429' and r['kind']=='assembly']
occ=[];trusted=[];contacts=[]
for r in raw['rows']:
 if r.get('name')!='410429' or r['kind']!='part':continue
 signature=r['body_signature'][0]
 occ.append({'id':r['id'],'assembly_id':9089 if r['occurrence_path'][0]==0 else 9077,'occurrence_path':r['occurrence_path'],
   'matrix_world_mm':r['matrix_world_mm'],'matrix_parent_mm':r['matrix_parent_mm'],'local_bounds_mm':r['bbox_local']['minimum']+r['bbox_local']['maximum'],
   'body_signature':{k:signature[k] for k in ['volume_m3','faces','edges','vertices','lumps']}})
 local=[];faces=[]
 for axis in range(3):
  candidates=[]
  for f in r['planar_faces']:
   vs=f['vertices_local_mm'];coord=sum(v[axis] for v in vs)/len(vs)
   if abs(coord-16.5)<1e-6 and max(abs(v[axis]-coord) for v in vs)<1e-6 and abs(f['oriented_normal_local'][axis]+1)<1e-6:candidates.append(f)
  assert len(candidates)==1,(r['id'],axis,len(candidates))
  local.append(sum(v[axis] for v in candidates[0]['vertices_local_mm'])/len(candidates[0]['vertices_local_mm']));faces.append(candidates[0])
 m=r['matrix_world_mm'];world=[sum(local[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)]
 slots=[]
 for axis in range(3):
  matches=[side for side in range(2) if abs(world[axis]-bounds[axis][side])<.003]
  assert len(matches)==1,(r['id'],axis,world,bounds)
  slots.append(matches[0])
 # The intersection of three native local plane witnesses is a measured
 # candidate registration point; it is never inferred from a cubic AABB.
 trusted.append({'id':r['id'],'assembly_id':occ[-1]['assembly_id'],'occurrence_path':r['occurrence_path'],'slot':slots,'anchor_local_mm':local})
 contacts.append({'id':r['id'],'slot':slots,'anchor_local_mm':local,'anchor_world_mm':world,'local_contact_faces':faces,
  'approval':'candidate POC registration; original lid has manual panel inconsistencies, no production mounting approval'})
e={'schema_version':1,'units':'mm','matrix_convention':'row-vector','source':{'sha256_before':raw['snapshot_sha256'],'sha256_after':file_sha256(raw['snapshot_path']),'guid':raw['snapshot_provenance_before']['file_guid']},
 'case_frame':{'matrix_world_mm':frame,'size_mm':size,'panel_planes':planes},'assemblies':assemblies,'occurrences':occ}
encoded=json.dumps(e,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
t={'schema_version':1,'evidence_content_sha256':hashlib.sha256(encoded).hexdigest(),'source_sha256':raw['snapshot_sha256'],'source_guid':e['source']['guid'],
 'assembly_ids':[a['id'] for a in assemblies],'occurrence_bindings':trusted}
write_receipt_once(root/'normalized_evidence.json',e);write_receipt_once(root/'trusted_registration.json',t)
write_receipt_once(root/'native_contact_registration.json',{'contacts':contacts,'size_mm':size,'frame_world_mm':frame,'raw_corner_evidence_sha256':file_sha256(root/'fresh_corner_panel_evidence.json'),
 'raw_panel_evidence_sha256':file_sha256(root/'fresh_panels.json'),'reference_planes':selected,'limitations':['Source lid BL outer X is18.5mm inward versus base reference; source lid WG extends31.5mm outside base Xmin.','New POC uses ten rectangular panels on coherent reference planes, not an approval or correction of original Epson model.']})
print(json.dumps({'size_mm':size,'origin_mm':frame[3][:3],'bindings':trusted,'evidence_content_sha256':t['evidence_content_sha256']}))
