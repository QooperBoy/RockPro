import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.parts.native import NativePartsAdapter,file_sha256
from rockpro_cad.core_case.native_reader import NativePoseAdapter,validate_matrix
source=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')
history_path=Path('artifacts/core-native/source-poses.json')
history=json.loads(history_path.read_text(encoding='utf-8'))
out=Path('artifacts/corner410429-20261022');out.mkdir(exist_ok=False)
result={'read_only':True,'source_path':str(source),'source_sha256_before':file_sha256(source),'historical_report':str(history_path.resolve()),'historical_report_sha256':file_sha256(history_path),'historical_source':history.get('source'),'historical_document':history.get('cad_document'), 'historical_rows':[r for r in history['rows'] if r.get('name')=='410429'],'desktop_actions':[],'open_or_activate_calls':[]}
try:
 a=NativePartsAdapter.attach(source);result['already_open']=True;result['source_before']=a.provenance()
 pose=NativePoseAdapter(a.legacy,a.base,a.document,a.api,source)
 rows=[]
 def walk(raw,path):
  n=raw.QueryInterface(a.api.IZElement);ident=pose.identity(n)
  if str(n.Name)=='410429' or len(path)<=1:
   row={'id':int(n.Id),'name':str(n.Name),'kind':ident['kind'],'occurrence_path':path}
   if path:
    for key,world in [('matrix_world_mm',True),('matrix_parent_mm',False)]:
     row[key]=validate_matrix(pose.matrix(n,world),allow_reflection=True)
    row['bbox_local']=pose.bbox(n,ident['kind'])
   rows.append(row)
  if ident['kind'] in ('assembly','scene'):
   for i in range(pose.child_count(n)):walk(pose.child_at(n,i),path+[i])
 walk(pose.root(),[]);result['fresh_rows']=rows;result['source_after']=a.provenance()
 assert result['source_before']==result['source_after']
except RuntimeError as e:result['already_open']=False;result['attachment_error']=str(e)
result['source_sha256_after']=file_sha256(source)
assert result['source_sha256_before']==result['source_sha256_after']
write_receipt_once(out/'readonly_audit.json',result)
print(json.dumps({'already_open':result['already_open'],'historical_corner_nodes':len(result['historical_rows']),'sha_unchanged':True,'report':str((out/'readonly_audit.json').resolve())}))
