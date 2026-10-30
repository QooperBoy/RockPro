"""Private pinned Hisense pipeline: copies -> geometric mates -> native tests.
Run with the integration venv in the existing IronCAD 2027 host. Never a generic MCP endpoint.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from run_t1_machining_job import run
ROOT=Path(__file__).resolve().parents[1]

def native(job,source,request):
    try:
        run(job,source,request)
    except Exception as error:
        # A known legacy AddOns.Count cleanup error can follow a completed CLR
        # invocation. Never rerun a completed CAD operation because cleanup failed.
        result=job/'result.json';clr=job/'clr_result.json'
        if not result.exists() or not clr.exists():raise
        proof=json.loads(result.read_text(encoding='utf-8-sig'))
        invocation=json.loads(clr.read_text(encoding='utf-8-sig'))
        if not proof.get('passed') or invocation.get('managed_result')!=0 or invocation.get('execute_hr')!='0x00000000':raise
        (job/'wrapper-warning.json').write_text(json.dumps({'completed_native_operation':True,'warning':repr(error)},ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('evidence',type=Path)
    args=ap.parse_args();q=json.loads(args.plan.read_text(encoding='utf-8-sig'))
    if q['contract']!='rockpro-tv-mount-count-plan-v2':raise ValueError('Unsupported private plan')
    os.environ['ROCKPRO_IRONCAD_YEAR']='2027'
    evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
    original=q['source'];original_sha=q['sha256'];output=q['output']
    construct=dict(q,contract='rockpro-tv-counts-construct-v1',output=str(evidence/'construct/assembled.ics'))
    native(evidence/'construct',ROOT/'scripts/native/ConstructTvQuantities2027.cs',construct)
    result=json.loads((evidence/'construct/result.json').read_text(encoding='utf-8-sig'))
    if not result['passed'] or result['status']!='CONSTRUCTED_NEEDS_MATING_AND_TESTS':raise RuntimeError('Construction not complete')
    ready=Path(result['output'])
    completion=dict(q,contract='rockpro-tv-quantity-complete-v2',source=str(ready),sha256=hashlib.sha256(ready.read_bytes()).hexdigest(),original=original,original_sha256=original_sha,output=output)
    native(evidence/'complete',ROOT/'scripts/native/CompleteTvQuantityModel2027.cs',completion)
    result=json.loads((evidence/'complete/result.json').read_text(encoding='utf-8-sig'))
    if not result['passed'] or not all(c['passed'] for c in result['checks']):raise RuntimeError('Native completion failed')
    print(json.dumps({'passed':True,'output':result['output'],'native_checks':len(result['checks']),'evidence':str(evidence)},ensure_ascii=False))

if __name__=='__main__':main()
