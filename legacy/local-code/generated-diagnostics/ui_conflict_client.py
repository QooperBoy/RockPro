import subprocess,json
from pathlib import Path
root=Path('../Integracja').resolve()
pid=(root/'rockpro_cad/qa/layout_demo_id.txt').read_text().strip()
with subprocess.Popen([str(root/'.venv/Scripts/python.exe'),'-X','utf8',str(root/'rockpro_cad/mcp/server.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8') as p:
 def call(i,name,args):
  p.stdin.write(json.dumps(dict(jsonrpc='2.0',id=i,method='tools/call',params=dict(name=name,arguments=args)))+'\n');p.stdin.flush()
  r=json.loads(p.stdout.readline())['result'];assert not r.get('isError'),r
  return json.loads(r['content'][0]['text'])
 r=call(1,'get_layout',dict(project_id=pid));assert r['revision']==2
 saved=call(2,'save_layout',dict(project_id=pid,spec=r['spec'],expected_revision=2))
 print(json.dumps(dict(previous=2,current=saved['revision'],spec_unchanged=saved['sha256']==r['sha256'])))
 p.stdin.close();p.wait(timeout=10)
