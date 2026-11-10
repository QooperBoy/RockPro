import sys,json,os,shutil
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import IronCADPrototypeDriver,write_receipt_once
from rockpro_cad.core_case.hardware_poc_native import _measure,_flush_graphics
from rockpro_cad.core_case.native_reader import NativePoseAdapter
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.parts.native import file_sha256,same_document_path
root=Path('artifacts/h7159-poc-native-20261022-04').resolve()
accept=json.loads((root/'acceptance.json').read_text(encoding='utf-8'))
assert accept['passed']
stage=sys.argv[1]
folder=root/'delivery'
def copy_once(source,target):
 with Path(source).open('rb') as src,Path(target).open('xb') as dst:
  shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
 assert file_sha256(source)==file_sha256(target)
names=['POC_H7159_bazowy_900x600x330.ics','POC_H7159_powiekszony_1100x720x410.ics','POC_H7159_powrot_900x600x330.ics']
if stage=='copy':
 folder.mkdir(exist_ok=False);rows=[]
 for case,name in zip(accept['cases'],names):
  r=json.loads(Path(case['receipt']).read_text(encoding='utf-8'))
  assert file_sha256(r['output_path'])==case['sha256']==r['snapshot_sha256']==file_sha256(r['snapshot_path'])
  output=folder/name;copy_once(r['output_path'],output)
  rows.append({'case_id':case['id'],'path':str(output),'sha256':file_sha256(output),'source_receipt':case['receipt']})
  for h in r['after_reopen']['handles']:
   for p in h['parts']:
    m=p['bbox_parent_matrix_world_mm']
    assert all(sum(abs(abs(m[i][j])-1)<1e-6 for j in range(3))==1 for i in range(3))
    assert all(abs(m[i][j])<1e-6 or abs(abs(m[i][j])-1)<1e-6 for i in range(3) for j in range(3))
 write_receipt_once(folder/'delivery_receipt.json',{'passed':True,'copies':rows,'all_78_measured_hardware_parent_frames_signed_axis':True,'exact_aabb_scope':'Pinned H7159 asset only; all measured parent-world rotations are signed axis permutations. Non-axis assets are not accepted by this POC proof.','source_unchanged':True,'asset_unchanged':True})
 stage='base'
case_index={'base':0,'resized':1,'return':2,'interior':0}[stage]
r=json.loads(Path(accept['cases'][case_index]['receipt']).read_text(encoding='utf-8'))
with cad_writer_lock():
 guard=IronCADPrototypeDriver(r['output_path'])
 output=folder/names[case_index]
 if stage=='interior':
  output=folder/'POC_H7159_wnetrze_900x600x330.ics'
  copy_once(folder/names[0],output)
 doc=guard.base.OpenFile(str(output),False)
 assert same_document_path(doc.Name,output)
 scene=doc.QueryInterface(guard.api.IZSceneDoc)
 if stage=='interior':
  pose=NativePoseAdapter(guard.adapter.legacy,guard.base,doc,guard.api,output);hidden=[]
  for i in range(pose.child_count(pose.root())):
   n=pose.child_at(pose.root(),i).QueryInterface(guard.api.IZElement)
   if str(n.Name).startswith('RP:panels-lid-') or str(n.Name)=='RP:panels-roof/1':
    n.QueryInterface(guard.api.IZPart).IsHidden=True;hidden.append({'id':int(n.Id),'name':str(n.Name)})
  assert len(hidden)==5
  _flush_graphics(pose,scene);scene.SaveAs(str(output),guard.api.Z_LINKS_COPY_ALL,True)
  assert not doc.Modified
  doc.Close();doc=guard.base.OpenFile(str(output),False)
  pose=NativePoseAdapter(guard.adapter.legacy,guard.base,doc,guard.api,output)
  observation=_measure(pose,r['plan'],{h['id']:h['node_id'] for h in r['after_reopen']['handles']},r['source_body_signature'])
  assert observation==r['after_reopen']
  for row in hidden:
   n=doc.QueryInterface(guard.api.IZSceneDocUtility).GetElementById(row['id'])
   assert n.QueryInterface(guard.api.IZPart).IsHidden
  archive=folder/'POC_H7159_wnetrze_snapshot.ics';copy_once(output,archive)
  write_receipt_once(folder/'interior_receipt.json',{'passed':True,'presentation_only':True,'physical_parts':37,'hidden_panels':hidden,'output':str(output),'sha256':file_sha256(output),'snapshot':str(archive),'snapshot_sha256':file_sha256(archive),'after_reopen':observation,'geometry_identical_to_closed_case':True,'closed_case_sha256':file_sha256(folder/names[0])})
 guard.assert_source_unchanged()
 write_receipt_once(folder/('active_'+stage+'.json'),{'active_path':str(doc.Name),'sha256':file_sha256(output),'modified':bool(doc.Modified),'source_unchanged':True})
 print('DELIVERY '+stage+' PASS '+str(output),flush=True)
