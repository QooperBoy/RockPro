"""ROC-26: proposal-only MCP entry point with cooperative run budgets.

The local constructor UI retains server.py. This entry point never offers
approval, persistence, execution, recovery or arbitrary code tools to a model.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
from contextlib import redirect_stdout
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import uuid
import server

ALLOWLIST=frozenset((
    'preview_layout','preview_case','preview_device_record','draft_device_inquiry',
    'recommend_case_families','benchmark_case_recommendations','preview_device_layouts',
    'get_device_record','get_layout','get_project','get_history','get_case_request',
    'get_case_operation','list_case_operations','list_projects','list_snapshots',
    'list_device_records','preview_catalog_layouts','preview_bound_device_layout',
))


@dataclass(frozen=True)
class Policy:
    max_tool_calls:int=30
    max_seconds:float=120
    max_retries:int=2
    schema_version:int=1
    prompt_version:str='proposal-only-v2'

    def __post_init__(self):
        if type(self.max_tool_calls) is not int or not 1<=self.max_tool_calls<=100:raise ValueError('Invalid call budget')
        if type(self.max_seconds) not in (int,float) or not math.isfinite(self.max_seconds) or not 0<self.max_seconds<=3600:raise ValueError('Invalid time budget')
        if type(self.max_retries) is not int or not 0<=self.max_retries<=5:raise ValueError('Invalid retry budget')


def validate(value,schema,path='$',depth=0):
    if depth>12:raise ValueError('Arguments too deep')
    kind=schema.get('type')
    types={'object':dict,'array':list,'string':str,'boolean':bool}
    if kind in types and type(value) is not types[kind]:raise ValueError(path+': invalid type')
    if kind=='integer' and type(value) is not int:raise ValueError(path+': integer required')
    if kind=='number' and (type(value) not in (int,float) or not math.isfinite(value)):raise ValueError(path+': finite number required')
    if 'enum' in schema and value not in schema['enum']:raise ValueError(path+': value outside enum')
    if kind in ('number','integer'):
        if value<schema.get('minimum',-math.inf) or value>schema.get('maximum',math.inf) or value<=schema.get('exclusiveMinimum',-math.inf):raise ValueError(path+': number outside bounds')
    if isinstance(value,str) and len(value)>10000:raise ValueError(path+': text too long')
    if isinstance(value,list):
        if not schema.get('minItems',0)<=len(value)<=schema.get('maxItems',1000):raise ValueError(path+': list outside bounds')
        for i,item in enumerate(value):validate(item,schema.get('items',{}),path+f'[{i}]',depth+1)
    if isinstance(value,dict):
        if not set(schema.get('required',[]))<=set(value):raise ValueError(path+': required argument missing')
        properties=schema.get('properties',{})
        if schema.get('additionalProperties') is False and set(value)-set(properties):raise ValueError(path+': unknown argument')
        if len(value)>1000:raise ValueError(path+': object too large')
        for key,item in value.items():validate(item,properties.get(key,{}),path+'.'+str(key),depth+1)


def client_label(params):
    """Name/version the MCP client reports about itself; metadata, not identity proof."""
    info=params.get('clientInfo') if isinstance(params,dict) else None
    if not isinstance(info,dict):return None
    parts=[str(info.get(k)) for k in ('name','version') if isinstance(info.get(k),(str,int,float))]
    label='/'.join(parts)
    return label if re.fullmatch(r'[A-Za-z0-9 ._@+/-]{1,80}',label or '') else None


class AgentSession:
    def __init__(self,policy=None,log_dir=None,clock=time.perf_counter,dispatcher=None):
        # The time budget starts at the first tool call. Interactive clients (Claude Code,
        # Codex) start this process when the window opens, long before the agent acts.
        self.policy=policy or Policy();self.clock=clock;self.started=None;self.calls=0;self.failures={}
        self.client=None  # MCP clientInfo from initialize, e.g. claude-code/2.x or codex-mcp-client/0.x
        self.schemas={r['name']:r for r in server.SCHEMAS if r['name'] in ALLOWLIST}
        self.dispatcher=dispatcher or server.dispatch
        self.run_id=uuid.uuid4().hex;self.log_dir=Path(log_dir if log_dir is not None else os.environ.get('ROCKPRO_AGENT_LOG_DIR') or Path(__file__).resolve().parents[3]/'artifacts/agent-runs')
        self.log_dir.mkdir(parents=True,exist_ok=True);self.log_path=self.log_dir/(self.run_id+'.jsonl')
        self.log_path.touch(exist_ok=False);self.stop_path=self.log_dir/(self.run_id+'.stop')
        # Bind the run to the actual exposed contracts, not only numeric budgets.
        self.toolset_sha=hashlib.sha256(json.dumps(self.schemas,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.policy_sha=hashlib.sha256(json.dumps(dict(policy=self.policy.__dict__,toolset_sha256=self.toolset_sha),sort_keys=True).encode()).hexdigest()

    def _log(self,tool,argument_sha,status,duration,code=None):
        row=dict(schema_version=1,run_id=self.run_id,timestamp_utc=datetime.now(timezone.utc).isoformat(),
            event='operation_finished',operation='agent.tool',actor='agent',
            tool=tool if tool in self.schemas else 'denied',arguments_sha256=argument_sha,
            policy_sha256=self.policy_sha,toolset_sha256=self.toolset_sha,prompt_version=self.policy.prompt_version,
            result={'status':status},duration_ms=duration,tool_calls=self.calls,error_code=code,
            client=self.client,
            model=None,reasoning_effort=None,tokens=None,cost=None,usage_status='unavailable',
            provenance='local tool execution; not model decision authorship')
        if self.log_path.stat().st_size>1024*1024:raise RuntimeError('Agent metadata log exhausted')
        with self.log_path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,separators=(',',':'))+'\n')

    def _error(self,code,message):
        return {'content':[{'type':'text','text':json.dumps(dict(code=code,message=message,run_id=self.run_id))}],'isError':True}

    def call(self,name,arguments):
        start=self.clock();self.calls+=1
        if self.started is None:self.started=start
        payload=json.dumps(arguments,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        argument_sha=hashlib.sha256(payload.encode()).hexdigest();fingerprint=(name,argument_sha)
        if self.calls>self.policy.max_tool_calls:code='AGENT_CALL_LIMIT'
        elif self.stop_path.exists():code='AGENT_STOP_REQUESTED'
        elif start-self.started>=self.policy.max_seconds:code='AGENT_TIME_LIMIT'
        elif name not in self.schemas:code='AGENT_TOOL_DENIED'
        elif self.failures.get(fingerprint,0)>self.policy.max_retries:code='AGENT_RETRY_LIMIT'
        elif len(payload.encode('utf-8'))>256*1024:code='AGENT_ARGUMENT_LIMIT'
        else:code=None
        if code:
            # At most the bounded budget plus one final refusal is retained.
            if self.calls<=self.policy.max_tool_calls+1:self._log(name,argument_sha,'limited',0,code)
            return self._error(code,'Run policy refused the next call; no tool was executed')
        try:
            validate(arguments,self.schemas[name]['inputSchema'])
            with redirect_stdout(sys.stderr):result=self.dispatcher(name,arguments)
            if len(json.dumps(result,ensure_ascii=False,allow_nan=False).encode('utf-8'))>2*1024*1024:raise ValueError('Tool output exceeds response budget')
        except Exception as exc:
            self.failures[fingerprint]=self.failures.get(fingerprint,0)+1
            self._log(name,argument_sha,'failed',(self.clock()-start)*1000,'AGENT_TOOL_FAILED')
            return self._error('AGENT_TOOL_FAILED',str(exc))
        duration=(self.clock()-start)*1000
        self._log(name,argument_sha,'passed',duration)
        # A completed call is returned even if its duration passed the budget.
        # Subsequent calls are refused; no worker or host is killed mid-operation.
        data=dict(tool_result=result,agent_run=dict(run_id=self.run_id,tool_calls=self.calls,
            elapsed_ms=(self.clock()-self.started)*1000,budget_exceeded_after_call=self.clock()-self.started>=self.policy.max_seconds,
            model_usage=None,model_cost=None,production_approved=False))
        return {'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'isError':False}

    def handle(self,request):
        ident=request.get('id')
        if ident is None:return None
        method=request.get('method')
        if method=='tools/list':result={'tools':list(self.schemas.values())}
        elif method=='tools/call':
            params=request.get('params',{})
            result=self.call(params.get('name'),params.get('arguments',{}))
        elif method=='initialize':
            self.client=client_label(request.get('params'))
            reply=server.handle(request)
            reply['result']['serverInfo']={'name':'rockpro-cad-proposals','version':'1.0.0'}
            return reply
        elif method=='ping':return server.handle(request)
        else:return {'jsonrpc':'2.0','id':ident,'error':{'code':-32601,'message':'Method not found'}}
        return {'jsonrpc':'2.0','id':ident,'result':result}


if __name__=='__main__':
    sys.stdin.reconfigure(encoding='utf-8');sys.stdout.reconfigure(encoding='utf-8')
    session=AgentSession()
    while True:
        line=sys.stdin.readline(512*1024+1)
        if not line:break
        if len(line)>512*1024:
            print(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Request exceeds limit'}}),flush=True)
            break
        try:
            reply=session.handle(json.loads(line))
        except Exception:
            reply={'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid bounded agent request'}}
        if reply is not None:print(json.dumps(reply,ensure_ascii=False),flush=True)
