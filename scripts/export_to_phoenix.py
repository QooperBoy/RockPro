"""Copy finished RockPro process runs and agent sessions to a local Phoenix.

Read-only for RockPro: it reads the Studio SQLite registry and the agent tool
logs, and remembers what it already sent in artifacts/phoenix/export-state.json.
Run it with the Phoenix venv (tools/phoenix/.venv), which has OpenTelemetry.

    tools/phoenix/.venv/Scripts/python.exe scripts/export_to_phoenix.py --once
    tools/phoenix/.venv/Scripts/python.exe scripts/export_to_phoenix.py --watch 15
    ... --dry-run   prints the spans instead of sending them

Running process runs are sent once they are closed (completed/partial/failed).
Agent sessions are sent after the log has been idle for --agent-idle seconds.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Integracja'))
from rockpro_cad import phoenix_export, process_runs  # noqa: E402
from rockpro_cad.mcp import project_store  # noqa: E402

DEFAULT_ENDPOINT = 'http://127.0.0.1:6006/v1/traces'


def load_state(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return dict(runs={}, agent={})


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2), encoding='utf-8')
    tmp.replace(path)


def closed_runs(database):
    if not Path(database).exists():
        return []
    conn = sqlite3.connect(f'file:{Path(database).as_posix()}?mode=ro', uri=True)
    try:
        rows = conn.execute('SELECT payload FROM studio_process_runs ORDER BY updated_at').fetchall()
    except sqlite3.OperationalError:
        return []  # Registry table not created yet: nothing recorded.
    finally:
        conn.close()
    reports = []
    for (payload,) in rows:
        report = json.loads(payload)
        report['summary'] = process_runs.summarize(report['events'])
        reports.append(report)
    return reports


def collect(database, agent_dir, state, agent_idle, flush):
    batches = []; pending = []
    for report in closed_runs(database):
        if state['runs'].get(report['id']) == report['updated_at']:
            continue
        if report['state'] == 'running' and not flush:
            failed = sum(1 for e in report['events'] if e.get('status') == 'failed')
            pending.append(f"run {report['id']} '{report.get('label', '')}' is still open "
                           f"(started {report['created_at'][:19]}Z, {len(report['events'])} events, "
                           f"{failed} failed). It is sent when closed with "
                           f"studio_process_run.py finish {report['id']} completed|partial|failed")
            continue
        batches.append((('runs', report['id'], report['updated_at']), phoenix_export.run_spans(report)))
    for log in sorted(Path(agent_dir).glob('*.jsonl')) if Path(agent_dir).exists() else []:
        stat = log.stat()
        if state['agent'].get(log.name) == stat.st_size or stat.st_size == 0:
            continue
        if time.time() - stat.st_mtime < agent_idle and not flush:
            pending.append('agent session ' + log.stem + ' (still active)')
            continue
        batches.append((('agent', log.name, stat.st_size), phoenix_export.agent_spans(phoenix_export.read_agent_log(log), log.stem)))
    return batches, pending


def to_otel(spans):
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.util.instrumentation import InstrumentationScope
    from opentelemetry.trace import SpanContext, SpanKind, TraceFlags
    from opentelemetry.trace.status import Status, StatusCode
    resource = Resource.create({'service.name': 'rockpro', 'openinference.project.name': phoenix_export.PROJECT})
    scope = InstrumentationScope('rockpro.phoenix_export', '1')
    result = []
    for s in spans:
        context = SpanContext(int(s['trace_id'], 16), int(s['span_id'], 16), False, TraceFlags(1))
        parent = SpanContext(int(s['trace_id'], 16), int(s['parent_id'], 16), False, TraceFlags(1)) if s['parent_id'] else None
        ns = lambda value: int(datetime.fromisoformat(value).timestamp() * 1e9)
        status = Status({'OK': StatusCode.OK, 'ERROR': StatusCode.ERROR}.get(s['status'], StatusCode.UNSET))
        result.append(ReadableSpan(name=s['name'], context=context, parent=parent, resource=resource,
                                   attributes=s['attributes'], kind=SpanKind.INTERNAL, status=status,
                                   start_time=ns(s['start']), end_time=ns(s['end']), instrumentation_scope=scope))
    return result


def send(spans, endpoint):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import SpanExportResult
    exporter = OTLPSpanExporter(endpoint=endpoint, timeout=10)
    try:
        if exporter.export(to_otel(spans)) != SpanExportResult.SUCCESS:
            raise RuntimeError('Phoenix did not accept the spans; is it running at ' + endpoint + '?')
    finally:
        exporter.shutdown()


def once(args, state_path):
    state = load_state(state_path)
    batches, pending = collect(args.database, args.agent_dir, state, args.agent_idle, args.flush)
    for (bucket, key, marker), spans in batches:
        if args.dry_run:
            print(json.dumps(spans, ensure_ascii=False, indent=2))
            continue
        send(spans, args.endpoint)
        state[bucket][key] = marker
        save_state(state_path, state)
        print(f'sent {bucket[:-1] if bucket == "runs" else bucket} {key}: {len(spans)} spans')
    for item in pending:
        print('waiting:', item)
    if not batches and not pending:
        print('nothing new')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--database', type=Path, default=project_store.DB_PATH,
                        help='Studio SQLite (same file as reference_studio --database)')
    parser.add_argument('--agent-dir', type=Path, default=ROOT / 'artifacts/agent-runs')
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--state', type=Path, default=ROOT / 'artifacts/phoenix/export-state.json')
    parser.add_argument('--agent-idle', type=float, default=300, help='seconds without new tool calls before a session is sent')
    parser.add_argument('--flush', action='store_true', help='also send running runs and active sessions (snapshot)')
    parser.add_argument('--dry-run', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--once', action='store_true', help='default: export once and exit')
    mode.add_argument('--watch', type=float, metavar='SECONDS', help='repeat every SECONDS until Ctrl+C')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    if args.flush and not args.dry_run:
        # A snapshot of an open run must not mark it as exported for good.
        args.state = args.state.with_name('flush-' + args.state.name)
    if args.watch:
        while True:
            try:
                once(args, args.state)
            except Exception as exc:  # Keep watching; Phoenix may be restarting.
                print('export failed:', exc, file=sys.stderr)
            time.sleep(args.watch)
    once(args, args.state)


if __name__ == '__main__':
    main()
