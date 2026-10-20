"""Acceptance test using actual MCP stdio messages, not direct worker calls."""
import json, subprocess, sys
from pathlib import Path
from datetime import datetime
here=Path(__file__).parent
requests=[
 {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"RockPro-live-acceptance","version":"1"}}},
 {"jsonrpc":"2.0","method":"notifications/initialized"},
 {"jsonrpc":"2.0","id":2,"method":"tools/list"},
 {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"inspect_project","arguments":{}}},
]
if '--change' in sys.argv:
 requests.append({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"change_dimensions_on_copy","arguments":{"changes":{"RP_Length":1014,"RP_Depth":662}}}})
run=subprocess.run([sys.executable,str(here/'server.py')],input='\n'.join(json.dumps(r) for r in requests)+'\n',text=True,encoding='utf-8',capture_output=True,timeout=180)
folder=here.parent/'logs';folder.mkdir(exist_ok=True)
result={'time':datetime.now().isoformat(),'requests':requests,'stderr':run.stderr,'returncode':run.returncode}
try:
 replies=[json.loads(line) for line in run.stdout.splitlines()]
 result['replies']=replies
 result['passed']=len(replies)==len([r for r in requests if 'id'in r]) and all('error' not in r and not r.get('result',{}).get('isError',False) for r in replies)
except Exception as e:result.update(passed=False,error=str(e),stdout=run.stdout)
out=folder/('mcp_live_change.json' if '--change'in sys.argv else 'mcp_live_inspect.json')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('passed',result['passed'])
for r in result.get('replies',[]):
 if r.get('id') in (3,4):
  payload=r.get('result',{})
  if payload.get('isError'):print(payload)
  else:
   v=json.loads(payload['content'][0]['text'])
   print(json.dumps({k:v[k] for k in ['source','copy','passed','source_unchanged','parameters'] if k in v},ensure_ascii=True))
sys.exit(0 if result['passed'] else 1)
