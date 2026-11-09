"""Isolated acceptance project via deployed stdio MCP. Never targets other projects."""
import argparse,json,subprocess,sys,sqlite3,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
LIVE=REPO.parent/'Integracja'
SERVER=LIVE/'rockpro_cad/mcp/server.py'
STATE=HERE/'live-test-project.json'
def rpc(name,args):
    request=dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name=name,arguments=args))
    proc=subprocess.run([str(LIVE/'.venv/Scripts/python.exe'),str(SERVER)],input=json.dumps(request)+'\n',text=True,encoding='utf-8',capture_output=True,check=True)
    r=json.loads(proc.stdout.strip().splitlines()[-1])['result']
    data=json.loads(r['content'][0]['text'])
    if r.get('isError'):raise RuntimeError(data)
    return data

def verify_migration():
    before=sqlite3.connect(REPO/'artifacts/roc22-predeploy/projects.sqlite3')
    after=sqlite3.connect(LIVE/'rockpro_cad/data/projects.sqlite3')
    result={}
    try:
        for (table,) in before.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            columns=[r[1] for r in before.execute('PRAGMA table_info('+table+')')]
            query='SELECT '+','.join('"'+c+'"' for c in columns)+' FROM "'+table+'"'
            old=before.execute(query).fetchall();new=after.execute(query).fetchall()
            assert all(row in new for row in old),table+' existing row changed'
            result[table]=dict(prior_rows=len(old),preserved=True)
        for table in ['projects','stages']:
            assert 'revision' in [r[1] for r in after.execute('PRAGMA table_info('+table+')')]
        (HERE/'migration-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    finally:before.close();after.close()
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['create','get','card-change','stage-change','history']);p.add_argument('--stage',default='geometry');p.add_argument('--note',default='Konkurencyjny zapis AI - test ROC-22');a=p.parse_args()
    if a.action=='create':
        rpc('list_projects',{})
        migration=verify_migration()
        if STATE.exists():raise RuntimeError('Test project already created; use get')
        manifest_state=json.loads((LIVE/'skeleton_state.json').read_text(encoding='utf-8-sig'))
        manifest=json.loads((Path(manifest_state['folder'])/'skeleton_manifest.json').read_text(encoding='utf-8'))
        target=LIVE/'rockpro_cad/revisions/roc22-acceptance-source'
        target.mkdir(exist_ok=False);source=target/'ROC22_test_source.ics';shutil.copy2(manifest['file'],source)
        result=rpc('save_project',dict(name='ROC-22 TEST odbior',client='Test techniczny',device='Fixture - bez operacji CAD',notes='Projekt testowy ROC-22. Bez zmian projektow klienta.',source=str(source),actor='test',change_source='acceptance'))
        STATE.write_text(json.dumps(dict(project_id=result['project']['id'],source=str(source)),indent=2),encoding='utf-8')
        print(json.dumps(dict(project=result['project'],migration=migration),ensure_ascii=False));return
    pid=json.loads(STATE.read_text(encoding='utf-8'))['project_id'];project=rpc('get_project',dict(project_id=pid))['project']
    assert project['name'].startswith('ROC-22 TEST'), 'Refusing non-test project'
    if a.action=='get':result=project
    elif a.action=='history':result=rpc('get_history',dict(project_id=pid,limit=200))
    elif a.action=='card-change':result=rpc('save_project',dict(project_id=pid,name=project['name'],notes=a.note,expected_revision=project['revision'],actor='AI-test',change_source='stdio-acceptance'))
    else:
        stage=next(s for s in project['stages'] if s['key']==a.stage)
        result=rpc('set_stage',dict(project_id=pid,stage=a.stage,status='review',note=a.note,expected_revision=stage['revision'],actor='AI-test',change_source='stdio-acceptance'))
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()

