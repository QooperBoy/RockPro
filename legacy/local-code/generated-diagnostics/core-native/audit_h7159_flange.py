import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import IronCADPrototypeDriver,write_receipt_once
from rockpro_cad.core_case.native_reader import NativePoseAdapter
from rockpro_cad.core_case.catalog_native import _signature
from rockpro_cad.cad_lock import cad_writer_lock
r=Path('artifacts/core-native').resolve()
source=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\rockpro_cad\qa\core-native-158e2ef\case_prototype.ics')
asset=r/'real-H7159-20261021-03/source_catalog_asset.ics'
with cad_writer_lock():
 d=IronCADPrototypeDriver(source)
 doc=d.base.OpenFile(str(asset),False)
 a=NativePoseAdapter(d.adapter.legacy,d.base,doc,d.api,asset)
 top=doc.QueryInterface(d.api.IZSceneDoc).GetTopElement()
 print('TOP',a.identity(top),a.child_count(top),flush=True)
 root=a.child_at(top,0)
 print('ROOT',a.identity(root),a.child_count(root),flush=True)
 sig=_signature(a,root)
 part=a.child_at(root,0).QueryInterface(d.api.IZPart)
 body=part.GetBody(True);faces=body.QueryInterface(d.api.IZBodyFace);verts=body.QueryInterface(d.api.IZBodyVertex)
 rows=[]
 for faceid in body.GetFaceIds():
  try:
   result=faces.GetPlaneData(faceid)
   typ,p,n=result
   point=[float(p.X)*1000,float(p.Y)*1000,float(p.Z)*1000]
   normal=[float(n.X),float(n.Y),float(n.Z)]
   if abs(normal[1])<.999999:continue
   ids=list(faces.GetFaceVertexIds(faceid))
   points=[[float(v)*1000 for v in verts.GetPosition(i)] for i in ids]
   rows.append({'face_id':faceid,'plane_data_type':typ,'point_mm':point,'normal':normal,'vertex_ids':ids,'vertices_mm':points,'bbox_mm':[float(v)*1000 for v in faces.GetFaceBoundingBox(faceid)]})
  except Exception:continue
 result={'asset_path':str(asset),'asset_hash':d.before_hash,'asset_signature':sig,'planar_faces_parallel_local_xz':rows,'document':a.provenance()}
 from rockpro_cad.parts.native import file_sha256
 result['asset_hash']=file_sha256(asset)
 write_receipt_once(r/'h7159-flange-faces.json',result)
 d.assert_source_unchanged()
 print(json.dumps(rows),flush=True)
