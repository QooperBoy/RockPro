from pathlib import Path
import hashlib,json,sqlite3,subprocess,sys
REPO=Path(__file__).resolve().parents[1]
INSTALLED=REPO.parent/'Integracja/rockpro_cad'
DB=INSTALLED/'data/projects.sqlite3'
def legacy():
    with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as conn:
        tables={r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
        result={}
        for table in ('projects','stages','snapshots','events'):
            if table in tables:
                rows=sorted(json.dumps(row,ensure_ascii=False,default=repr) for row in conn.execute('select * from '+table))
                result[table]=dict(count=len(rows),sha256=hashlib.sha256('\n'.join(rows).encode()).hexdigest())
        project=conn.execute('select id from projects order by id limit 1').fetchone()[0]
    return result,project
before,project=legacy()
fixture=json.loads((REPO/'tests/core_design/cases.json').read_text(encoding='utf-8'))
recipe=json.loads((INSTALLED/'core_case/templates/prototype-v1.json').read_text(encoding='utf-8'))
request=dict(spec=fixture['cases'][0]['spec'],manifest=fixture['manifest'],template_recipe=recipe,scenario=dict(operation='plan'))
calls=[dict(jsonrpc='2.0',id=1,method='initialize',params=dict(protocolVersion='2025-06-18')),
       dict(jsonrpc='2.0',id=2,method='tools/list')]
for index,(tool,args) in enumerate([('list_projects',{}),('get_case_request',dict(project_id=project)),
            ('list_case_operations',dict(project_id=project)),('preview_case',dict(request=request))],3):
    calls.append(dict(jsonrpc='2.0',id=index,method='tools/call',params=dict(name=tool,arguments=args)))
run=subprocess.run([sys.executable,str(INSTALLED/'mcp/server.py')],input='\n'.join(json.dumps(c) for c in calls)+'\n',
    encoding='utf-8',capture_output=True,timeout=60,check=True)
replies=[json.loads(line) for line in run.stdout.splitlines()]
assert len(replies)==6
names={tool['name'] for tool in replies[1]['result']['tools']}
assert {'list_case_operations','preview_case','execute_case_plan','recover_case_operation'}<=names
for reply in replies[2:]:assert not reply['result']['isError'],reply
plan=json.loads(replies[-1]['result']['content'][0]['text'])
assert plan['status']=='planned' and len(plan['groups'])==37 and len(plan['occurrences'])==67
assert plan['production_approved'] is False
after,_=legacy()
assert before==after,(before,after)
sys.path[:0]=[str(INSTALLED.parent),str(INSTALLED/'mcp')]
from rockpro_cad.core_case import native,native_reader,catalog_native
report=dict(status='PASS',legacy_records_preserved=True,before=before,after=after,
    server=replies[0]['result']['serverInfo'],tool_count=len(names),groups=37,occurrences=67,
    native_modules_imported=True,native_execution='NOT RUN',project_id=project)
out=REPO/'artifacts/installed-core-smoke.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status='PASS',report=str(out),tool_count=len(names),legacy_records_preserved=True),ensure_ascii=True))
