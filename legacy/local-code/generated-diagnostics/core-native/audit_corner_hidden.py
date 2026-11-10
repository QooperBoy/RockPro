import sys,json,os,shutil,ctypes,math
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import NativePartsAdapter,file_sha256,same_document_path
from rockpro_cad.core_case.native_reader import NativePoseAdapter,validate_matrix
from rockpro_cad.core_case.catalog_native import _signature
from rockpro_cad.cad_lock import cad_writer_lock
source=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')
attach=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\rockpro_cad\qa\core-native-158e2ef\case_prototype.ics')
out=Path('artifacts/corner410429-20261022/hidden-source').resolve();out.mkdir(exist_ok=False)
user32=ctypes.WinDLL('user32');user32.GetForegroundWindow.restype=ctypes.c_void_p
a=NativePartsAdapter.attach(attach);base=a.base;source_hash=file_sha256(source)
def state():
 d=base.ActiveDoc
 return {'foreground_hwnd':int(user32.GetForegroundWindow() or 0),'active_doc':{'path':str(d.Name),'guid':str(d.FileGUID),'modified':bool(d.Modified)}}
def guarded(label,fn):
 before=state();write_receipt_once(out/(label+'.before.json'),before)
 value=fn();after=state();write_receipt_once(out/(label+'.after.json'),after)
 if before!=after:raise RuntimeError('background guard changed at '+label)
 return value
def point(v,m):return [sum(v[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)]
def det(m):return sum(m[0][i]*(m[1][(i+1)%3]*m[2][(i+2)%3]-m[1][(i+2)%3]*m[2][(i+1)%3]) for i in range(3))
with cad_writer_lock():
 snapshot=out/'source_snapshot.ics'
 with source.open('rb') as src,snapshot.open('xb') as dst:shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
 assert file_sha256(snapshot)==source_hash
 already,doc=guarded('01-open-hidden',lambda:base.OpenFile2(str(snapshot),True,False))
 if already:raise RuntimeError('unique hidden copy unexpectedly already open; not owned')
 assert same_document_path(doc.Name,snapshot)
 pose=NativePoseAdapter(a.legacy,base,doc,a.api,snapshot);before_provenance=pose.provenance();rows=[];face_errors=[]
 def faces_of(node,m):
  body=node.QueryInterface(a.api.IZPart).GetBody(True);f=body.QueryInterface(a.api.IZBodyFace);verts=body.QueryInterface(a.api.IZBodyVertex);found=[]
  for fid in body.GetFaceIds():
   try:rev,p,n=f.GetPlaneData(fid)
   except Exception:continue
   ids=list(f.GetFaceVertexIds(fid));vs=[[float(x)*1000 for x in verts.GetPosition(i)] for i in ids]
   raw=[float(n.X),float(n.Y),float(n.Z)];oriented=[x*(-1 if rev else 1) for x in raw]
   found.append({'face_id':int(fid),'is_reversed':bool(rev),'plane_origin_local_mm':[float(p.X)*1000,float(p.Y)*1000,float(p.Z)*1000],
    'underlying_normal_local':raw,'oriented_normal_local':oriented,'oriented_normal_world':[sum(oriented[k]*m[k][j] for k in range(3)) for j in range(3)],
    'vertex_ids':[int(x) for x in ids],'vertices_local_mm':vs,'vertices_world_mm':[point(v,m) for v in vs]})
  return found
 def read_all():
  def walk(raw,path):
   n=raw.QueryInterface(a.api.IZElement);ident=pose.identity(n);name=str(n.Name);kind=ident['kind'];r={'id':int(n.Id),'name':name,'kind':kind,'occurrence_path':path}
   if path:
    for key,world in [('matrix_world_mm',True),('matrix_parent_mm',False)]:r[key]=validate_matrix(pose.matrix(n,world),allow_reflection=True)
    r['determinant_world']=det(r['matrix_world_mm']);r['bbox_local']=pose.bbox(n,kind)
   panel=kind=='part' and r.get('bbox_local',{}).get('valid') and sorted(r['bbox_local']['size'])[0]<20 and sorted(r['bbox_local']['size'])[1]>200
   r['panel_candidate']=panel
   if kind=='part' and (name=='410429' or panel):
    r['body_signature']=_signature(pose,n);r['planar_faces']=faces_of(n,r['matrix_world_mm'])
    r['bbox_parent_raw_mm']=[float(x)*1000 for x in n.QueryInterface(a.api.IZPart).GetBoundingBox(False)]
    print('READ '+str(r['id'])+' '+name+' faces='+str(len(r['planar_faces'])),flush=True)
   rows.append(r)
   if kind in ('assembly','scene') and (len(path)<2 or name=='410429'):
    for i in range(pose.child_count(n)):walk(pose.child_at(n,i),path+[i])
  walk(pose.root(),[])
 guarded('02-read-geometry',read_all)
 assert before_provenance==pose.provenance() and file_sha256(snapshot)==source_hash and file_sha256(source)==source_hash
 corners=[r for r in rows if r['name']=='410429' and r['kind']=='part']
 assert len(corners)==8
 result={'passed_read':True,'read_only':True,'source_relation':'byte-identical disk copy; original not open in ROT; historical unsaved memory is a different evidence scope',
  'original_path':str(source),'original_sha256_before':source_hash,'original_sha256_after':file_sha256(source),'snapshot_path':str(snapshot),'snapshot_sha256':file_sha256(snapshot),
  'snapshot_provenance_before':before_provenance,'snapshot_provenance_after':pose.provenance(),'background_api':'IZBaseApp.OpenFile2(snapshot,True,False)','no_activate_setvisible_redraw':True,'rows':rows}
 write_receipt_once(out/'fresh_corner_panel_evidence.json',result)
 print(json.dumps({'report':str(out/'fresh_corner_panel_evidence.json'),'nodes':len(rows),'corner_parts':len(corners),'panel_candidates':sum(r['panel_candidate'] for r in rows),'world_determinants':{str(r['id']):r['determinant_world'] for r in corners}}),flush=True)
