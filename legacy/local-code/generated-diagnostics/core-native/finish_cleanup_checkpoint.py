import sys,json,datetime
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import file_sha256
repo=Path('.').resolve();folder=repo/'artifacts/prototype-cleanup-20261022-urgent-02'
history_path=repo/'artifacts/core-native/source-poses.json';history=json.loads(history_path.read_text(encoding='utf-8'))
ids={12631,12782,12630,12781};rows=[r for r in history['rows'] if r['id'] in ids]
assert len(rows)==4
latch={'scope':'Historical filesystem-only source-pose evidence; NOT fresh native data; original source had Modified=true when read, disk-equivalence not proven',
 'historical_report':str(history_path),'historical_report_sha256':file_sha256(history_path),'source':history['source'],'cad_document':history['cad_document'],'rows':rows}
latch_path=folder/'historical_latch_roots.json';write_receipt_once(latch_path,latch)
source=json.loads((folder/'source-shared-read.json').read_text(encoding='utf-8-sig'))
files=[]
for rel in ['artifacts/corner410429-20261022/native-03/A-base/POC_410429_A-base.ics','artifacts/corner410429-20261022/native-03/A-base/snapshot.ics','artifacts/h7159-poc-native-20261022-04/delivery/POC_H7159_bazowy_900x600x330.ics','artifacts/h7159-poc-native-20261022-04/delivery/POC_H7159_powiekszony_1100x720x410.ics','artifacts/h7159-poc-native-20261022-04/delivery/POC_H7159_wnetrze_900x600x330.ics']:
 p=repo/rel;files.append({'path':str(p),'bytes':p.stat().st_size,'sha256':file_sha256(p)})
r={'status':'CLEANUP_NOT_PERFORMED_HOST_UNAVAILABLE','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'agent_closed_documents':0,'agent_saved_documents':0,'new_memory_backups':[],
 'before_open_document_count':None,'after_open_document_count':None,'ironcad_process_count_after':0,'global_native_lock_released':True,
 'sequence':['03 A-base geometry/save/reopen PASS; B stopped at foreground guard; C NOT_RUN','Read-only Python GetAllOpenDocs returned RPC_E_SERVERFAULT before any cleanup Save/Close','Subsequent official SDK ROT attachment found no existing explicit context','Elevated OS process enumeration confirmed no IRONCAD process; no host restart/kill attempted'],
 'windows_application_error':{'local_timestamp':'2026-10-22 20:17:31','event_id':1000,'process':'IRONCAD.exe','version':'29.0.20.20605','exception':'0xc0000005','offset':'0x2','module':'unknown','pid_hex':'0x7768'},
 'windows_wer':{'local_timestamps':['2026-10-22 20:17:36','2026-10-22 20:17:40'],'event_id':1001,'event_name':'BEX64','stack_hash':'StackHash_1d29','module_hint':'PCH_73_FROM_ntdll'},
 'causation':'Not established; server exception and Windows crash report are observed facts, not proof of which operation caused the crash.',
 'original_source_shared_read':source,'existing_saved_files':files,'historical_latch_roots':str(latch_path),
 'unsaved_prototype_state':'Requested new memory backup/clean close did not occur; current live unsaved state cannot be recovered through a stopped host. Existing saved ICS/archive files remain available.',
 'no_more_cad_calls':True,'no_ui_or_foreground_activation':True}
write_receipt_once(folder/'cleanup_checkpoint.json',r)
print(json.dumps({'checkpoint':str(folder/'cleanup_checkpoint.json'),'source_shared_read':source,'latch_rows':[{'id':row['id'],'name':row['name'],'path':row['occurrence_path'],'has_world_matrix':'matrix_world_mm' in row} for row in rows],'files':files},ensure_ascii=True),flush=True)
