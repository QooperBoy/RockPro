import sys,json,ctypes
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import NativePartsAdapter,file_sha256,same_document_path
from rockpro_cad.core_case.native_reader import NativePoseAdapter,validate_matrix
from rockpro_cad.core_case.catalog_native import _signature
folder=Path('artifacts/corner410429-20261022/hidden-source').resolve()
prior=json.loads((folder/'fresh_corner_panel_evidence.json').read_text(encoding='utf-8'))
history=json.loads(Path('artifacts/core-native/source-poses.json').read_text(encoding='utf-8'))
source=Path(prior['snapshot_path']);a=NativePartsAdapter.attach(Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\rockpro_cad\qa\core-native-158e2ef\case_prototype.ics'))
doc=a.base.GetOpenDocByName(str(source));assert same_document_path(doc.Name,source)
pose=NativePoseAdapter(a.legacy,a.base,doc,a.api,source)
user32=ctypes.WinDLL('user32');user32.GetForegroundWindow.restype=ctypes.c_void_p
def state():
 d=a.base.ActiveDoc
 return {'foreground_hwnd':int(user32.GetForegroundWindow() or 0),'active_doc':{'path':str(d.Name),'guid':str(d.FileGUID),'modified':bool(d.Modified)}}
before=state();source_before=pose.provenance();write_receipt_once(folder/'03-panels.before.json',before)
utility=doc.QueryInterface(a.api.IZSceneDocUtility);rows=[]
for h in history['rows']:
 if h.get('name') not in ('WG','WD','BP','BL','PL'):continue
 node=utility.GetElementById(h['id']).QueryInterface(a.api.IZElement)
 assert int(node.Id)==h['id'] and str(node.Name)==h['name']
 actual=pose.root()
 for index in h['occurrence_path']:actual=pose.child_at(actual,index)
 assert int(actual.QueryInterface(a.api.IZElement).Id)==h['id']
 m=validate_matrix(pose.matrix(node,True),allow_reflection=True)
 body=node.QueryInterface(a.api.IZPart).GetBody(True);f=body.QueryInterface(a.api.IZBodyFace);v=body.QueryInterface(a.api.IZBodyVertex);faces=[]
 for fid in body.GetFaceIds():
  try:rev,p,n=f.GetPlaneData(fid)
  except Exception:continue
  ids=list(f.GetFaceVertexIds(fid));points=[[float(x)*1000 for x in v.GetPosition(i)] for i in ids]
  normal=[float(n.X),float(n.Y),float(n.Z)];oriented=[x*(-1 if rev else 1) for x in normal]
  world=[[sum(q[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)] for q in points]
  faces.append({'face_id':int(fid),'is_reversed':bool(rev),'plane_origin_local_mm':[float(p.X)*1000,float(p.Y)*1000,float(p.Z)*1000],
   'underlying_normal_local':normal,'oriented_normal_local':oriented,'oriented_normal_world':[sum(oriented[k]*m[k][j] for k in range(3)) for j in range(3)],
   'vertex_ids':[int(x) for x in ids],'vertices_local_mm':points,'vertices_world_mm':world})
 rows.append({'id':int(node.Id),'name':str(node.Name),'occurrence_path':h['occurrence_path'],'kind':'part','matrix_world_mm':m,
  'matrix_parent_mm':validate_matrix(pose.matrix(node,False),allow_reflection=True),'bbox_local':pose.bbox(node,'part'),'body_signature':_signature(pose,node),'planar_faces':faces})
 print('PANEL '+str(node.Id)+' '+str(node.Name)+' '+str(len(faces)),flush=True)
assert len(rows)==10
after=state();write_receipt_once(folder/'03-panels.after.json',after)
assert before==after and source_before==pose.provenance() and file_sha256(source)==prior['snapshot_sha256']
write_receipt_once(folder/'fresh_panels.json',{'passed_read':True,'source_path':str(source),'source_sha256':file_sha256(source),'source_guid':str(doc.FileGUID),'rows':rows,'background_guard_unchanged':True})
