import sys,json,traceback,os
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.catalog_native import execute_rigid_reuse
report=json.loads(Path('artifacts/core-native/source-poses.json').read_text(encoding='utf-8'))
row=next(r for r in report['rows'] if r['id']==11797)
binding={'schema_version':1,'source_path':report['source']['path'],'source_sha256':report['source']['sha256_before'],'source_guid':report['cad_document']['before']['file_guid'],'node_id':row['id'],'node_name':row['name'],'expected_world_matrix_mm':row['matrix_world_mm']}
try:
 r=execute_rigid_reuse(binding,output_dir='artifacts/core-native',target_matrix_mm=[[0,1,0,0],[-1,0,0,0],[0,0,1,0],[100,200,300,1]],operation_id='real-H7159-20261021-01')
 print(json.dumps({k:r[k] for k in ('passed','output_path','source_unchanged','physical_occurrences','catalog_reused','geometry_scope','stages')},ensure_ascii=True),flush=True)
 os._exit(0)
except BaseException:
 traceback.print_exc();sys.stderr.flush();os._exit(1)
