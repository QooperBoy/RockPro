"""Explicit, resumable acceptance commands using the same UI/MCP service APIs.

No mode retries CAD. Plan and execute are separate commands with pinned revisions.
Reports are new local artifacts; they are never executable recovery instructions.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Integracja'))
sys.path.insert(0, str(ROOT / 'Integracja' / 'rockpro_cad' / 'mcp'))
import core_service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('preview', 'plan', 'execute', 'status', 'recover'), required=True)
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--expected-layout-revision', type=int)
    parser.add_argument('--expected-case-revision', type=int)
    parser.add_argument('--plan-id')
    parser.add_argument('--operation-id')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.mode in ('preview', 'plan') and args.expected_layout_revision is None:
        parser.error('preview/plan requires --expected-layout-revision read from get_layout')
    if args.mode in ('plan', 'execute') and args.expected_case_revision is None:
        parser.error('plan/execute requires --expected-case-revision read from get_case_request or pinned plan')
    if args.mode == 'execute' and (not args.plan_id or not args.operation_id):
        parser.error('execute requires the saved --plan-id and a stable --operation-id')
    if args.mode == 'recover' and not args.operation_id:
        parser.error('recover requires --operation-id; use status to discover it')
    report = args.report.resolve()
    if not report.is_relative_to((ROOT / 'artifacts').resolve()):
        parser.error('report must be a new file below this checkout artifacts directory')
    report.parent.mkdir(parents=True, exist_ok=True)
    # Reserve a new result path before any database/CAD action. Never overwrite evidence.
    with report.open('x', encoding='utf-8') as stream:
        record = dict(schema_version=1, mode=args.mode, project_id=args.project_id,
                      operation_id=args.operation_id, timestamp_utc=datetime.now(timezone.utc).isoformat(),
                      production_approved=False, native_status='NOT RUN', passed=False)
        try:
            if args.mode in ('preview', 'plan'):
                prepared = core_service.prepare_case_request(args.project_id, args.expected_layout_revision)
                record['prepared'] = prepared
                record['passed'] = prepared['preview']['status'] == 'planned'
                if args.mode == 'plan' and record['passed']:
                    saved = core_service.save_case_request(args.project_id, prepared['request'],
                        args.expected_case_revision, actor='acceptance-runner', change_source='explicit-cli')
                    record['saved'] = saved
                    if saved.get('saved'):
                        result = core_service.plan_project_case(args.project_id, saved['revision'])
                        record['result'] = result
                        record['passed'] = result['status'] == 'planned'
                    else:
                        record['passed'] = False
            elif args.mode == 'execute':
                result = core_service.execute_case_plan(args.project_id, args.plan_id, args.operation_id,
                                                       args.expected_case_revision)
                record['result'] = result
                record['passed'] = result['status'] == 'registered'
                record['native_status'] = result['status']
            elif args.mode == 'recover':
                result = core_service.recover_case_operation(args.project_id, args.operation_id)
                record['result'] = result
                record['passed'] = result['status'] == 'registered'
                record['native_status'] = 'RECOVERY READ ONLY: ' + result['status']
            else:
                record['result'] = (core_service.get_case_operation(args.project_id, args.operation_id)
                                    if args.operation_id else core_service.list_case_operations(args.project_id))
                record['passed'] = True
        except Exception as exc:
            record['error'] = getattr(exc, 'details', dict(code=type(exc).__name__, message=str(exc)))
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(dict(passed=record['passed'], mode=args.mode, report=str(report),
                          native_status=record['native_status']), ensure_ascii=False))
    return 0 if record['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
