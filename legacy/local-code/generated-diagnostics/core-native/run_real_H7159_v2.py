import sys,json,traceback,os
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.parts.native import NativePartsAdapter,file_sha256
from rockpro_cad.core_case.native_reader import NativePoseAdapter
import rockpro_cad.core_case.catalog_native as catalog
from rockpro_cad.core_case.native import write_receipt_once
source=Path('artifacts/core-native/real-H7159-20261021-01/source_snapshot.ics').resolve()
original=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')
chain={}
try:
 original_adapter=NativePartsAdapter.attach(original)
 chain={'original_path':str(original),'original_hash_before':file_sha256(original),'original_live_before':original_adapter.provenance(),'input_capture_path':str(source),'input_capture_sha256':file_sha256(source),'relation':'input capture created by earlier original live-memory SaveAsCopy; original not edited'}
 adapter=NativePoseAdapter.attach(source)
 scene=adapter.document.QueryInterface(adapter.api.IZSceneDoc)
 node=scene.QueryInterface(adapter.api.IZSceneDocUtility).GetElementById(11797)
 binding={'schema_version':1,'source_path':str(source),'source_sha256':file_sha256(source),'source_guid':adapter.provenance()['file_guid'],'node_id':11797,'node_name':str(node.Name),'expected_world_matrix_mm':adapter.matrix(node,True)}
 old_signature=catalog._signature
 def signature(adapter,node):
  print('BODY_SIGNATURE',int(node.Id),str(node.Name),flush=True)
  result=old_signature(adapter,node)
  print('BODY_SIGNATURE_DONE',len(result),flush=True)
  return result
 catalog._signature=signature
 print('BEGIN_REAL_REUSE',flush=True)
 r=catalog.execute_rigid_reuse(binding,output_dir='artifacts/core-native',target_matrix_mm=[[0,1,0,0],[-1,0,0,0],[0,0,1,0],[100,200,300,1]],operation_id='real-H7159-20261021-02',source_is_captured_copy=True)
 chain.update(original_hash_after=file_sha256(original),original_live_after=original_adapter.provenance(),native_receipt_path=str(Path(r['output_path']).parent/'native_receipt.json'))
 assert chain['original_hash_before']==chain['original_hash_after']
 assert chain['original_live_before']==chain['original_live_after']
 write_receipt_once(Path(r['output_path']).parent/'source_chain.json',chain)
 print(json.dumps({k:r[k] for k in ('passed','output_path','source_unchanged','physical_occurrences','catalog_reused','geometry_scope','stages')},ensure_ascii=True),flush=True)
 os._exit(0)
except BaseException:
 traceback.print_exc();sys.stderr.flush()
 if chain:
  try:
   chain.update(original_hash_after=file_sha256(original),original_live_after=original_adapter.provenance(),status='FAILED')
   write_receipt_once(Path('artifacts/core-native/real-H7159-20261021-02-failed-source-chain.json'),chain)
  except BaseException: traceback.print_exc();sys.stderr.flush()
 os._exit(1)
