import sys,json,os,traceback
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.catalog_native import _signature,compare_body_signatures
from rockpro_cad.core_case.native_reader import NativePoseAdapter
from rockpro_cad.parts.native import file_sha256
from rockpro_cad.core_case.native import write_receipt_once
folder=Path('artifacts/core-native/real-H7159-20261021-03')
try:
 r=json.loads((folder/'native_receipt.json').read_text(encoding='utf-8'))
 source=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')
 adapter=NativePoseAdapter.attach(source);before=adapter.provenance();sha=file_sha256(source)
 scene=adapter.document.QueryInterface(adapter.api.IZSceneDoc)
 node=scene.QueryInterface(adapter.api.IZSceneDocUtility).GetElementById(11797)
 actual=_signature(adapter,node)
 compare_body_signatures(actual,r['source_body_signature'])
 compare_body_signatures(actual,r['body_signature'])
 after=adapter.provenance();shaafter=file_sha256(source)
 assert before==after and sha==shaafter
 result={'passed':True,'source':{'path':str(source),'sha256_before':sha,'sha256_after':shaafter,'before':before,'after':after,'unchanged':True},'source_node_id':11797,'source_node_name':str(node.Name),'original_body_signature':actual,'original_matrix_world_mm':adapter.matrix(node,True),'compared_to_receipt':str((folder/'native_receipt.json').resolve()),'source_capture_and_reopened_native_body_equivalence':'PASS','production_approved':False}
 write_receipt_once(folder/'original_body_comparison.json',result)
 print(json.dumps({'passed':True,'parts':len(actual)-1,'source_unchanged':True,'report':str((folder/'original_body_comparison.json').resolve())},ensure_ascii=True),flush=True)
 os._exit(0)
except BaseException:
 traceback.print_exc();sys.stderr.flush();os._exit(1)
