"""Bounded offline benchmark of source-bound mounting references; never invokes CAD."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'))
from rockpro_cad.core_case import working_mounts

MAX_INPUT_BYTES=64*1024*1024


def _read(path):
    with Path(path).open('rb') as stream:data=stream.read(MAX_INPUT_BYTES+1)
    if len(data)>MAX_INPUT_BYTES:raise ValueError('Benchmark input exceeds 64 MB')
    return data


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _content_digest(value):
    return _digest(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode('utf-8'))


def _stats(samples):
    return {clock:None if not samples else dict(min=min(values),median=statistics.median(values),max=max(values))
            for clock in ('wall_ms','cpu_ms')
            for values in ([sample[clock] for sample in samples],)}


def _measure(action):
    wall_start=time.perf_counter();cpu_start=time.process_time()
    result=action()
    cpu_ms=(time.process_time()-cpu_start)*1000
    wall_ms=(time.perf_counter()-wall_start)*1000
    if any(not math.isfinite(v) or v<0 for v in (wall_ms,cpu_ms)):
        raise RuntimeError('Invalid benchmark clock sample')
    return result,dict(wall_ms=wall_ms,cpu_ms=cpu_ms)


def benchmark(inventory_path,standard_path,destination,component_path,delta_world_mm,*,repeats=3,warmup=1):
    """Verify before timing; report each call separately, without mutating inputs.

    Plan timings include the planner's mandatory inventory revalidation. They
    must not be added to standalone build/validate timings as a process total.
    Hashing/checking outputs happens outside the measured function calls.
    """
    if type(repeats) is not int or not 1<=repeats<=20:raise ValueError('repeats must be an integer from 1 to 20')
    if type(warmup) is not int or not 0<=warmup<=5:raise ValueError('warmup must be an integer from 0 to 5')
    destination=Path(destination)
    if destination.exists():raise FileExistsError('Benchmark output must be a new directory')
    inventory_path=Path(inventory_path).resolve(strict=True);standard_path=Path(standard_path).resolve(strict=True)
    inventory_bytes=_read(inventory_path);standard_bytes=_read(standard_path)
    standard=json.loads(standard_bytes.decode('utf-8-sig'))
    # No clock sampling or output directory exists until both source binding
    # and the explicit component/delta have passed the production code's guards.
    verified=working_mounts.validate_working_standard(standard,inventory_bytes)
    expected_plan=working_mounts.plan_component_translation(standard,component_path,delta_world_mm,inventory_bytes=inventory_bytes)
    standard_digest=_content_digest(standard);plan_digest=_content_digest(expected_plan)
    code_paths={'benchmark':Path(__file__).resolve(),'working_mounts':Path(working_mounts.__file__).resolve()}
    code_sha={name:_digest(_read(path)) for name,path in code_paths.items()}
    calls={
        'build_working_standard':lambda:working_mounts.build_working_standard(inventory_bytes,standard['source_sha256'],standard['inventory_sha256']),
        'validate_working_standard':lambda:working_mounts.validate_working_standard(standard,inventory_bytes),
        'plan_component_translation':lambda:working_mounts.plan_component_translation(standard,component_path,delta_world_mm,inventory_bytes=inventory_bytes),
    }
    results={}
    for phase,count in (('warmup',warmup),('measured',repeats)):
        phase_samples={name:[] for name in calls}
        for _ in range(count):
            for name,action in calls.items():
                value,sample=_measure(action)
                expected=plan_digest if name=='plan_component_translation' else standard_digest
                if _content_digest(value)!=expected:raise RuntimeError('Benchmark output is not deterministic')
                if _content_digest(standard)!=standard_digest:raise RuntimeError('Benchmark modified its standard input')
                phase_samples[name].append(sample)
        results[phase]={name:dict(samples=samples,statistics=_stats(samples)) for name,samples in phase_samples.items()}
    if _read(inventory_path)!=inventory_bytes or _read(standard_path)!=standard_bytes:
        raise RuntimeError('Benchmark input changed; no report was created')
    if any(_digest(_read(path))!=code_sha[name] for name,path in code_paths.items()):
        raise RuntimeError('Benchmark code changed; no report was created')
    report=dict(schema='rockpro.offline-mount-benchmark/1',status='PASS',
        scope='offline function call timings; not CAD or complete workflow time',
        repeats=repeats,warmup_repeats=warmup,
        inputs=dict(inventory_sha256=_digest(inventory_bytes),standard_sha256=_digest(standard_bytes),
                    source_sha256_declared_by_inventory=verified['source_sha256'],
                    component_path=component_path,delta_world_mm=delta_world_mm),
        code_sha256=code_sha,
        environment=dict(python=sys.version,implementation=platform.python_implementation(),platform=platform.platform()),
        nodes=len(verified['nodes']),physical_parts=verified['physical_part_count'],
        moving_nodes=sum(target['moving'] for target in expected_plan['targets']),
        standard_content_sha256=standard_digest,plan_content_sha256=plan_digest,
        standard_unchanged=True,input_files_unchanged=True,deterministic_outputs=True,
        measurements=results,
        timing_semantics='Independent calls; plan includes inventory validation. Do not sum calls. Warmup is reported separately. Wall uses perf_counter; CPU uses process_time.',
        native_cad='NOT RUN',source_ics_read=False,production_approved=False)
    encoded=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)
    destination.mkdir(parents=True,exist_ok=False)
    with (destination/'benchmark.json').open('x',encoding='utf-8') as output:output.write(encoded)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory',type=Path);parser.add_argument('standard',type=Path);parser.add_argument('destination',type=Path)
    parser.add_argument('--component',required=True)
    parser.add_argument('--delta',type=float,nargs=3,required=True,metavar=('X_MM','Y_MM','Z_MM'))
    parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--warmup',type=int,default=1)
    args=parser.parse_args()
    report=benchmark(args.inventory,args.standard,args.destination,args.component,args.delta,repeats=args.repeats,warmup=args.warmup)
    print(json.dumps(dict(status=report['status'],nodes=report['nodes'],repeats=report['repeats'],report=str(args.destination/'benchmark.json'))))


if __name__=='__main__':main()
