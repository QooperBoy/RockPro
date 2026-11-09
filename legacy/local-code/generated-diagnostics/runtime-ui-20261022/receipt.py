from pathlib import Path
import sqlite3,json,hashlib,os
root=Path(__file__).resolve().parent
installed=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja')
db=installed/'rockpro_cad/data/projects.sqlite3'
c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
pid='75891b44be1c45db92d0143d6663baba';op='fbb8f1983d684fe9bba5fa10413125cd'
tables=[r[0] for r in c.execute("select name from sqlite_master where type='table'")]
rows={}
for table in tables:
 columns=[r['name'] for r in c.execute(f'pragma table_info("{table}")')]
 key='project_id' if 'project_id' in columns else 'id' if table=='projects' else None
 if key: rows[table]=[dict(r) for r in c.execute(f'select * from "{table}" where "{key}"=?',(pid,))]
folder=installed/'case_runs'/pid/op
service=json.loads((folder/'service_receipt.json').read_text(encoding='utf-8'))
native=json.loads((folder/'native_receipt.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert native['passed'] and native['physical_occurrences']==67
assert native['source']['unchanged'] and native['source']['sha256_before']==native['source']['sha256_after']==sha(service['binding']['source'])
assert sha(service['snapshot_path'])==service['snapshot_sha256']==native['output_sha256']
out={'passed':True,'scope':'Actual native Windows UI to deployed MCP to official IronCAD SDK to saved/reopened synthetic proxy prototype and registered archive. Full source catalog case not accepted.',
 'project_id':pid,'project_name':'QA Core native UI 20261022','layout_revision':1,'request_revision':service['request_revision'],'plan_id':service['plan_id'],'operation_id':op,
 'native_receipt':str(folder/'native_receipt.json'),'service_receipt':str(folder/'service_receipt.json'),'snapshot_path':service['snapshot_path'],'snapshot_sha256':service['snapshot_sha256'],
 'source':native['source'],'physical_occurrences':67,'groups':37,'production_approved':False,
 'max_native_error_mm':max(x['max_error_mm'] for x in native['checks']),
 'ui_steps':['Restarted official IronCAD after verified Save All and deployment PASS','InitSelf DLL path/build/SHA verified','Created separately named QA project using real panel','Assigned already-open light ICS source','Saved layout via real native UI:2 devices,9mm separator,side+X','Prepared request and saved/pinned plan','Clicked Create ICS once','Observed saved/reopened archive registered','Closed/reopened Case prototype in English and read same operation ID without creating again'],
 'dll_sha256':'b46e79de629ce44fe4c56c356d4ba2b83e9ba7a62e34d7d8b193786093e2b390',
 'screenshots':['case-success-pl.jpg','case-success-en.jpg'],'ui_limitations':['Recover button label truncated at default size in Polish and English; full label exposed in accessibility and tooltip configured. Operation ID horizontally clipped in default width; full ID is retained.','Opaque IronCAD rendering temporarily hid form pixels after COM activation; Win+Up then restore repainted form; recorded final screenshots show actual success.'],
 'database_readonly_evidence':rows}
with (root/'ui_receipt.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
print(json.dumps({k:out[k] for k in ['passed','project_id','plan_id','operation_id','snapshot_path','snapshot_sha256','max_native_error_mm']},ensure_ascii=False))
