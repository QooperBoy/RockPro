"""Native A/B/C + resize acceptance through the real shared case service.

Run only after IronCAD has finished any earlier operation. --source must already
be open, and live inside the explicit artifacts --workspace. This runner never
opens its source, starts/restarts IronCAD, registers an add-in or uses user SQLite.
Every hardware solid in this acceptance recipe is an unapproved synthetic proxy.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'Integracja'), str(ROOT/'Integracja/rockpro_cad/mcp'),
                str(ROOT/'tests/core_design')]


def write_once(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def resolve_inputs(source, workspace):
    artifacts = (ROOT/'artifacts').resolve(strict=True)
    workspace = Path(workspace).resolve(strict=True)
    source = Path(source).resolve(strict=True)
    if not workspace.is_dir() or not workspace.is_relative_to(artifacts):
        raise ValueError('--workspace must be an existing directory inside this checkout artifacts/')
    if not source.is_file() or source.suffix.lower() != '.ics' or not source.is_relative_to(workspace):
        raise ValueError('--source must be an existing ICS inside --workspace')
    if source.name.lower() == 'snapshot.ics':
        raise ValueError('An immutable snapshot archive cannot be the working source')
    return source, workspace


def fixture_requests():
    fixtures = json.loads((ROOT/'tests/core_design/cases.json').read_text(encoding='utf-8'))
    recipe = json.loads((ROOT/'tests/core_design/synthetic_template.json').read_text(encoding='utf-8'))
    cases = {case['id']: case for case in fixtures['cases']}
    requests = {key: dict(spec=copy.deepcopy(cases[key]['spec']),
                         manifest=copy.deepcopy(fixtures['manifest']),
                         template_recipe=copy.deepcopy(recipe), scenario={'operation':'plan'})
                for key in ('A','B','C')}
    return cases, requests


def resized_expectation(case):
    expected = copy.deepcopy(case)
    for key,value in case['resize_expectations']['XYZ'].items():
        if key in ('frames','groups'):
            expected['expected'][key].update(copy.deepcopy(value))
        else:
            expected['expected'][key] = copy.deepcopy(value)
    return expected


def require(value, message):
    if not value:
        raise RuntimeError(message)


def run(source, workspace, run_id):
    # Imports do not initialize COM or write a database. The first CAD operation
    # below is strict existing-open-only attachment to the selected full path.
    from rockpro_cad.core_case import plan_case
    from rockpro_cad.parts.native import NativePartsAdapter, file_sha256
    from rockpro_cad.core_case.native import compare_measurements, preflight_plan
    import core_service as service
    import project_store as store
    import worker
    from oracle import validate

    cases, requests = fixture_requests()
    for key in ('A','B','C'):
        validate(cases[key], plan_case(requests[key]))
    adapter = NativePartsAdapter.attach(source)
    original = adapter.provenance()
    source_sha = file_sha256(source)
    # All generated service output and the sole isolated SQLite remain under
    # the user's explicit artifacts workspace. Production DB_PATH is untouched.
    folder = workspace/'native_acceptance'/run_id
    folder.mkdir(parents=True, exist_ok=False)
    worker.ROOT = workspace
    store.DB_PATH = folder/'projects.sqlite3'
    report = dict(schema_version=1, run_id=run_id, status='RUNNING', production_approved=False,
        geometry_scope='synthetic_native_block_prototype; no catalog or mounting approval',
        source=dict(path=str(source), sha256_before=source_sha, live_document_before=original,
                    identity='the explicit CLI source; never substituted with an Epson identity',
                    disk_equivalence='not_proven' if original['modified'] else 'saved_document'),
        isolated_database=str(store.DB_PATH), workspace=str(workspace), stages=[])
    tracked = ['Integracja/rockpro_cad/core_case/NativeSceneBridge.cs',
               'Integracja/rockpro_cad/core_case/native.py',
               'Integracja/rockpro_cad/core_case/native_reader.py',
               'Integracja/rockpro_cad/core_case/contracts.py',
               'Integracja/rockpro_cad/core_case/expressions.py',
               'Integracja/rockpro_cad/cad_lock.py',
               'Integracja/rockpro_cad/core_case/planner.py',
               'Integracja/rockpro_cad/mcp/core_service.py',
               'scripts/accept_core_native.py',
               'tests/core_design/cases.json', 'tests/core_design/synthetic_template.json']
    report['code_sha256'] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in tracked}
    write_once(folder/'started.json', report)
    print('Acceptance evidence: '+str(folder),flush=True)
    baselines = {}

    def source_guard():
        require(file_sha256(source)==source_sha,'Explicit source disk bytes changed')
        require(adapter.provenance()==original,'Explicit source path/GUID/Modified flag changed')

    def execute(label, project_id, planned, expected):
        require(planned['status']=='planned',label+': service did not produce executable plan')
        validate(expected,planned['plan'])
        operation_id = 'accept-'+label
        stage = dict(label=label, status='APPLYING', project_id=project_id,
                     plan_id=planned['plan_id'], operation_id=operation_id,
                     revision=planned['revision'])
        report['stages'].append(stage)
        write_once(folder/(label+'-started.json'),stage)
        print(label+': native service execute',flush=True)
        result = service.execute_case_plan(project_id,planned['plan_id'],operation_id,planned['revision'])
        stage['result'] = result
        if result.get('status') != 'registered':
            stage['status'] = result.get('status','UNKNOWN')
            write_once(folder/(label+'-stopped.json'),stage)
            raise RuntimeError(label+': native outcome '+str(result.get('status'))+'; stop without retry or insertion')
        receipt = result['receipt']
        compare_measurements(preflight_plan(planned['plan']),receipt['measurements'])
        require(receipt['source']['path']==str(source),label+': receipt substituted the explicit source')
        require(receipt['source']['sha256_before']==source_sha,label+': receipt source identity differs')
        require(receipt['production_approved'] is False,label+': unexpected production claim')
        require(Path(result['snapshot_path'])!=Path(receipt['output_path']),label+': archive and working file coincide')
        require(file_sha256(result['snapshot_path'])==file_sha256(receipt['output_path'])==receipt['output_sha256'],
                label+': saved/archive checksum mismatch')
        # The same durable operation must replay without a second CAD insertion.
        replay = service.execute_case_plan(project_id,planned['plan_id'],operation_id,planned['revision'])
        require(replay==result,label+': idempotent operation replay differs')
        snapshots = store.list_snapshots(project_id)['snapshots']
        require(any(s['id']==result['snapshot_id'] and s['integrity']=='verified' for s in snapshots),
                label+': SQLite snapshot missing or checksum not verified')
        source_guard()
        stage.update(status='PASS', physical_occurrences=len(receipt['measurements']),
                     native_receipt=str(Path(receipt['output_path']).parent/'native_receipt.json'),
                     replay='PASS', archive_integrity='PASS')
        write_once(folder/(label+'-passed.json'),stage)
        print(label+': PASS (save/reopen, measurements, SQLite, archive, replay)',flush=True)

    try:
        for key in ('A','B','C'):
            source_guard()
            project = store.save_project('Native acceptance '+run_id+' '+key,source=str(source),quantity=1)['project']
            project_id = project['id']
            saved = service.save_case_request(project_id,requests[key],0,actor='native-acceptance',change_source='explicit-cli')
            require(saved.get('saved') is True,key+': request was not saved')
            planned = service.plan_project_case(project_id,saved['revision'])
            execute(key,project_id,planned,cases[key])
            baselines[key] = (project_id,planned)
        project_id, previous = baselines['A']
        resize = service.plan_project_case(project_id,previous['revision'],scenario=dict(
            operation='resize',target_plywood_external=cases['A']['resize_targets']['XYZ'],previous=previous['plan']))
        execute('A-resize-XYZ',project_id,resize,resized_expectation(cases['A']))
        source_guard()
        report.update(status='PASS', source_unchanged=True)
        report['source'].update(sha256_after=file_sha256(source),live_document_after=adapter.provenance())
        report['project_operations'] = {key:service.list_case_operations(value[0]) for key,value in baselines.items()}
    except BaseException as exc:
        report.update(status='STOPPED',error=dict(type=type(exc).__name__,message=str(exc)))
        # Do not query a potentially unresponsive host after an unknown native
        # outcome. Existing source guards and the operation journal remain evidence.
        if report['stages'] and report['stages'][-1]['status']=='APPLYING':
            report['stages'][-1]['status']='UNKNOWN'
        traceback.print_exc()
    write_once(folder/'acceptance.json',report)
    print(json.dumps(dict(status=report['status'],report=str(folder/'acceptance.json'),
                         source=str(source),production_approved=False)),flush=True)
    return 0 if report['status']=='PASS' else 1


def main(argv=None):
    if not __debug__:
        raise ValueError('Run without -O: independent oracle assertions must remain enabled')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path,help='Explicit already-open working ICS inside --workspace')
    parser.add_argument('--workspace',required=True,type=Path,help='Existing directory inside this checkout artifacts/')
    parser.add_argument('--run-id',default=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    parser.add_argument('--validate-inputs-only',action='store_true',help='Validate paths and offline cases; no COM, SQLite or CAD writes')
    args=parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.run_id):
        parser.error('run-id must contain 1..80 ASCII letters, digits, underscores or hyphens')
    source,workspace=resolve_inputs(args.source,args.workspace)
    if args.validate_inputs_only:
        from rockpro_cad.core_case import plan_case
        from oracle import validate
        cases,requests=fixture_requests()
        for key in ('A','B','C'): validate(cases[key],plan_case(requests[key]))
        print('PASS: paths and A/B/C input plans; native CAD/SQLite NOT RUN')
        return 0
    return run(source,workspace,args.run_id)


if __name__=='__main__':
    try:
        exit_code=main()
    except BaseException:
        traceback.print_exc()
        exit_code=1
    # Completed STA COM clients can retain vendor foreground helper threads.
    # Exit only after durable final evidence or a completed failure handler.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
