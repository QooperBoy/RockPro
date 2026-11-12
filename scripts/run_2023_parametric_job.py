"""End-to-end IronCAD 2023 parametrization job on an owned diagnostic part.

What it does (every step on new files in a new folder, never on a user model):
  1. builds the local ICAPI interop from the installed 2023 type library,
  2. job "create":  IronCad2023Probe.exe creates a 100 x 50 x 20 mm part with
     the scene parameter RP_ProbeThickness, saves and reopens it,
  3. job "resize":  binds the part height natively to RP_ProbeThickness, sets
     it to --target-mm, measures, saves, reopens, re-checks 60 mm and 20 mm.

Both jobs are always recorded in the Studio process registry (one span per
job, one operation per measured CAD step), so they appear in Phoenix:
  - without --run-id the script opens its own run on the newest saved draft
    revision (or --draft-id/--draft-revision) and closes it at the end;
  - with --run-id it records into that run and leaves it open for its owner;
  - --no-record runs without any logging.
--origin ai needs the AI decision: either --decision-reason (recorded now, in
this run) or --intervention-id of a decision already recorded in --run-id.
See docs/PHOENIX_DASHBOARD.md.

This is a compatibility/observability proof, not a case-family adapter: the
parametrized family models in the 2026-11-03 package are saved in IronCAD 2027
and cannot be opened by 2023.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Integracja'))
sys.path.insert(0, str(ROOT / 'scripts'))
from rockpro_cad.auto_run import studio_database  # noqa: E402

PROBE_STEPS = (('bounds_before', 'native.create'), ('bounds_changed', 'native.regenerate'),
               ('bounds_changed', 'native.measure'), ('saved', 'native.save'),
               ('bounds_reopened', 'native.reopen'), ('bounds_reopened', 'native.measure'),
               ('bounds_restored', 'native.regenerate'), ('bounds_restored', 'native.measure'))
BINDING_STEPS = {'input': ('native.measure',), 'native_expression_resize': ('native.regenerate', 'native.measure'),
                 'reopened': ('native.save', 'native.reopen', 'native.measure'),
                 'post_reopen_parameter_only_resize': ('native.regenerate', 'native.measure'),
                 'return_to_input_dimensions': ('native.regenerate', 'native.measure')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_progress(folder, rows):
    """Translate the job's own measured checks into the registry's native trace format."""
    stamp = datetime.now(timezone.utc).isoformat()
    with (Path(folder) / 'native_progress.jsonl').open('w', encoding='utf-8', newline='\n') as f:
        for operation, label in rows:
            f.write(json.dumps(dict(event='operation_finished', operation=operation, result={'status': 'passed'},
                                    occurrence_id='probe:' + label.replace('_', '-'), timestamp_utc=stamp)) + '\n')


def create_job(folder):
    from run_t1_machining_job import current_interop
    from rockpro_cad.cad_lock import cad_writer_lock
    folder.mkdir(parents=True)
    interop = current_interop(folder)
    exe = folder / 'IronCad2023Probe.exe'
    built = subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe', '/nologo', '/platform:x64',
                            '/out:' + str(exe), '/reference:' + str(interop), '/reference:System.Web.Extensions.dll',
                            '/reference:Microsoft.CSharp.dll', str(ROOT / 'scripts/native/IronCad2023Probe.cs')],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
    if built.returncode:
        raise RuntimeError('Probe build failed: ' + built.stdout + built.stderr)
    with cad_writer_lock():
        done = subprocess.run([str(exe), str(folder / 'model')], cwd=folder, capture_output=True, text=True, timeout=600)
    result = json.loads((folder / 'model/result.json').read_text(encoding='utf-8-sig'))
    if done.returncode or not result.get('passed'):
        raise RuntimeError('Native create job failed: ' + str(result.get('error', done.returncode))[:500])
    write_progress(folder, [(op, key) for key, op in PROBE_STEPS if key in result])
    return folder / 'model/diagnostic_restored.ics'


def resize_job(folder, source, target_mm):
    import probe_2023_legacy_binding
    folder.mkdir(parents=True)
    result = probe_2023_legacy_binding.run(source, sha(source), folder / 'model', target_mm)
    if not result.get('passed'):
        raise RuntimeError('Native resize job failed: ' + str(result.get('error'))[:500])
    write_progress(folder, [(op, c['name']) for c in result['checks'] for op in BINDING_STEPS.get(c['name'], ())])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, help='new folder (default artifacts/jobs/2023-parametric-<time>)')
    parser.add_argument('--target-mm', type=float, default=40)
    parser.add_argument('--run-id', help='record into this open run and leave it open (default: own run, closed at the end)')
    parser.add_argument('--database', type=Path, default=studio_database(),
                        help='Studio SQLite (default: ROCKPRO_STUDIO_DATABASE or artifacts/studio.sqlite)')
    parser.add_argument('--draft-id', help='draft for the own run (default: newest saved draft revision)')
    parser.add_argument('--draft-revision', type=int, default=1)
    parser.add_argument('--label', help='label of the own run')
    parser.add_argument('--no-record', action='store_true', help='run without recording anything')
    parser.add_argument('--origin', choices=('standard', 'ai', 'manual'), default='standard',
                        help='who decided the resize value (the create job is always standard)')
    parser.add_argument('--decision-reason', help="with --origin ai: the AI decision's reason, recorded before the job")
    parser.add_argument('--intervention-id', help='AI decision ID (default with --decision-reason: ai/resize-<mm>mm)')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('ROCKPRO_IRONCAD_YEAR', '2023')
    from rockpro_cad import process_runs
    from rockpro_cad.auto_run import NoDraft, decision_event, recorded_run
    from rockpro_cad.icapi_runtime import selected_year
    from rockpro_cad.mcp import project_store
    from rockpro_cad.process_capture import capture
    if selected_year() != 2023:
        raise SystemExit('This job targets IronCAD 2023 (ROCKPRO_IRONCAD_YEAR=2023).')
    project_store.DB_PATH = args.database.resolve()
    if args.origin == 'ai' and args.no_record:
        raise SystemExit('--origin ai is about recording who decided; it cannot be combined with --no-record')
    if args.origin == 'ai' and not (args.decision_reason or args.intervention_id):
        raise SystemExit('--origin ai needs --decision-reason "<why>" (or --intervention-id of a decision recorded in --run-id)')
    if args.decision_reason and args.origin != 'ai':
        raise SystemExit('--decision-reason records an AI decision; add --origin ai')
    if args.decision_reason and not args.intervention_id:
        args.intervention_id = f'ai/resize-{args.target_mm:g}mm'
    folder = (args.output or ROOT / 'artifacts/jobs' / ('2023-parametric-' + datetime.now().strftime('%Y%m%dT%H%M%S'))).resolve()
    if args.no_record:
        print('not recording (--no-record): this job will not appear in Phoenix', flush=True)
        return run_jobs(args, folder, lambda **extra: None, capture)
    label = args.label or f'2023 parametric job: {args.target_mm:g} mm ({args.origin})'
    draft = (args.draft_id, args.draft_revision) if args.draft_id else None
    try:
        with recorded_run(project_store.DB_PATH, label, args.run_id, draft) as run_id:
            if args.decision_reason:
                process_runs.append(run_id, [decision_event(args.intervention_id, args.decision_reason)])
            return run_jobs(args, folder, lambda **extra: dict(run_id=run_id, stage='native', **extra), capture)
    except NoDraft as exc:
        raise SystemExit(str(exc))


def run_jobs(args, folder, trace, capture):
    folder.mkdir(parents=True, exist_ok=False)
    print('1/2 create job ->', folder / 'create', flush=True)
    with capture(trace(origin='standard'), folder / 'create'):
        source = create_job(folder / 'create')
    print('2/2 resize job ->', folder / 'resize', f'(target {args.target_mm:g} mm, decided by {args.origin})', flush=True)
    extra = dict(origin=args.origin)
    if args.intervention_id:
        extra['intervention_id'] = args.intervention_id
    with capture(trace(**extra), folder / 'resize'):
        result = resize_job(folder / 'resize', source, args.target_mm)
    print(json.dumps(dict(passed=True, folder=str(folder), api_version=result.get('api_version'),
                          checks=[(c['name'], [round(v, 3) for v in c['dimensions_mm']]) for c in result['checks']]),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
