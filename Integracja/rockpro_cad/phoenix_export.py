"""Read-only mapping of RockPro evidence to OpenInference-style trace spans.

The process registry (SQLite) and the agent tool logs stay the source of truth.
This module only reads them and builds plain span dictionaries; the CLI in
scripts/export_to_phoenix.py sends them to a local Phoenix over OTLP. Nothing
here writes to the registry, the drafts or any CAD file.

Span kinds follow OpenInference so Phoenix can filter them:
  CHAIN  - a process run or one CAD job (span event in the registry)
  TOOL   - one leaf operation (SDK/Python/constructor) or one agent tool call
  AGENT  - an AI intervention (decision with a written reason) or an agent session
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from . import process_runs

PROJECT = 'rockpro'


def _id(*parts, size=16):
    """Deterministic hex ID so a re-export never invents a second copy."""
    return hashlib.sha256('\x1f'.join(map(str, parts)).encode('utf-8')).hexdigest()[:size*2]


def _time(value, fallback):
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return fallback
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _span(trace_id, span_id, parent_id, name, kind, start, end, status, attributes):
    end = max(end, start)
    return dict(trace_id=trace_id, span_id=span_id, parent_id=parent_id, name=name, kind=kind,
                start=start.isoformat(), end=end.isoformat(), status=status,
                attributes={k: v for k, v in attributes.items() if v is not None})


def _status(value):
    if value in ('failed',):
        return 'ERROR'
    if value in ('running', 'requested'):
        return 'UNSET'
    return 'OK'


def _attempts(events):
    """Group raw registry events into attempts; the first row opens, the last closes."""
    groups = {}
    for index, e in enumerate(events):
        key = (e['kind'], e['operation_id'], e.get('attempt', 1))
        groups.setdefault(key, []).append((index, e))
    return groups


def run_spans(report):
    """All spans of one process run. `report` is process_runs.read(...) output."""
    run_id = report['id']; trace = _id('run', run_id)
    created = _time(report.get('created_at'), datetime.now(timezone.utc))
    updated = _time(report.get('updated_at'), created)
    summary = report.get('summary') or process_runs.summarize(report['events'])
    groups = _attempts(report['events'])
    jobs = {op for (kind, op, _), rows in groups.items() if kind == 'span'}
    job_origin = {}
    spans = []
    root = _id('run', run_id, 'root', size=8)
    for (kind, op, attempt), rows in groups.items():
        first, last = rows[0][1], rows[-1][1]
        end = _time(last.get('timestamp_utc'), updated)
        duration = last.get('duration_ms')
        start = end - timedelta(milliseconds=duration) if duration is not None else _time(first.get('timestamp_utc'), end)
        parent = root
        for job in jobs:
            if kind == 'operation' and op.startswith(job + '/line/'):
                parent = _id('run', run_id, 'span', job, 1, size=8)
        attributes = {
            'openinference.span.kind': {'span': 'CHAIN', 'intervention': 'AGENT', 'operation': 'TOOL'}[kind],
            'rockpro.event.kind': kind, 'rockpro.operation_id': op, 'rockpro.attempt': attempt,
            'rockpro.status': last['status'], 'rockpro.origin': last.get('origin', 'unknown'),
            'rockpro.executor': last.get('executor', 'unknown'), 'rockpro.stage': last.get('stage'),
            'rockpro.part_id': last.get('part_id'), 'rockpro.occurrence_id': last.get('occurrence_id'),
            'rockpro.intervention_id': last.get('intervention_id'), 'rockpro.evidence_sha256': last.get('evidence_sha256'),
            'rockpro.duration_ms': duration, 'rockpro.run_id': run_id,
        }
        if kind == 'intervention':
            name = 'AI decision: ' + op
            attributes['input.value'] = last.get('reason') or first.get('reason')
        elif kind == 'span':
            name = f"CAD job ({last.get('origin', 'unknown')})"
            attributes['rockpro.label'] = last.get('label')
            if last.get('reason'):
                attributes['output.value'] = last['reason']
            if attempt == 1 and op in jobs:
                job_origin[op] = last['status'], last.get('origin', 'unknown')
        else:
            name = last.get('label') or op
            attributes['tool.name'] = last.get('label') or op
        span_id = _id('run', run_id, kind, op, attempt, size=8)
        spans.append(_span(trace, span_id, parent, name, attributes['openinference.span.kind'],
                           start, end, _status(last['status']), attributes))
    job_counts = {o: sum(1 for status, origin in job_origin.values() if origin == o) for o in process_runs.ORIGINS}
    root_attributes = {
        'openinference.span.kind': 'CHAIN', 'rockpro.run_id': run_id, 'rockpro.run.state': report['state'],
        'rockpro.run.mode': report.get('mode'), 'rockpro.run.label': report.get('label'),
        'rockpro.draft_id': report['binding']['draft_id'], 'rockpro.draft_revision': report['binding']['draft_revision'],
        'rockpro.draft_sha256': report['binding'].get('draft_sha256'),
        'rockpro.ops.completed': summary['completed'], 'rockpro.ops.failed': summary['failed'],
        'rockpro.ops.running': summary['running'], 'rockpro.interventions': summary['interventions'],
        'rockpro.open_spans': summary['open_spans'], 'rockpro.retry_attempts': summary['retry_attempts'],
        'rockpro.coarse_jobs_without_details': summary['coarse_jobs_without_details'],
        'rockpro.metric_note': 'Shares count completed leaf operations, weighted by job size (audit O1).',
        'input.value': report.get('label'),
        'output.value': json.dumps(dict(by_origin=summary['by_origin'], by_executor=summary['by_executor'],
                                        percent=summary['percent'], jobs_by_origin=job_counts), ensure_ascii=False),
    }
    for origin in process_runs.ORIGINS:
        root_attributes[f'rockpro.ops.{origin}'] = summary['by_origin'][origin]
        root_attributes[f'rockpro.jobs.{origin}'] = job_counts[origin]
        if summary['percent'][origin] is not None:
            root_attributes[f'rockpro.percent.{origin}'] = summary['percent'][origin]
    for executor in process_runs.EXECUTORS:
        root_attributes[f'rockpro.executor.{executor}'] = summary['by_executor'][executor]
    # The run's own clock bounds the root; producer timestamps are not trusted to
    # stretch it (timestamp_utc is free text in the registry, audit O8).
    outside = sum(not (created <= _time(s['end'], created) <= max(updated, created)) for s in spans)
    root_attributes['rockpro.events_outside_run_window'] = outside
    status = {'failed': 'ERROR', 'running': 'UNSET'}.get(report['state'], 'OK')
    spans.insert(0, _span(trace, root, None, 'Process run: ' + report.get('label', run_id), 'CHAIN',
                          created, updated, status, root_attributes))
    return spans


def read_agent_log(path):
    rows = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def agent_spans(rows, run_id=None):
    """Spans of one agent_server session (one JSONL file)."""
    if not rows and run_id is None:
        return []
    run_id = run_id or rows[0]['run_id']; trace = _id('agent', run_id)
    root = _id('agent', run_id, 'root', size=8)
    spans = []
    now = datetime.now(timezone.utc)
    for index, row in enumerate(rows):
        end = _time(row.get('timestamp_utc'), now)
        start = end - timedelta(milliseconds=row.get('duration_ms') or 0)
        status = (row.get('result') or {}).get('status')
        attributes = {
            'openinference.span.kind': 'TOOL', 'tool.name': row.get('tool'),
            'rockpro.agent.run_id': run_id, 'rockpro.agent.call_index': row.get('tool_calls'),
            'rockpro.status': status, 'rockpro.error_code': row.get('error_code'),
            'rockpro.arguments_sha256': row.get('arguments_sha256'),
            'rockpro.duration_ms': row.get('duration_ms'), 'rockpro.client': row.get('client'),
            'rockpro.studio_run_id': row.get('studio_run_id'),
            'rockpro.tool_status': row.get('tool_status'),
            'rockpro.diagnostic_codes': ','.join(row.get('diagnostic_codes') or []) or None,
            'llm.model_name': row.get('model'),
        }
        spans.append(_span(trace, _id('agent', run_id, index, size=8), root, 'tool: ' + str(row.get('tool')),
                           'TOOL', start, end, 'ERROR' if status in ('failed', 'blocked') else ('UNSET' if status == 'limited' else 'OK'),
                           attributes))
    first = rows[0] if rows else {}
    client = next((r.get('client') for r in rows if r.get('client')), None)
    failed = sum((r.get('result') or {}).get('status') == 'failed' for r in rows)
    limited = sum((r.get('result') or {}).get('status') == 'limited' for r in rows)
    blocked = sum((r.get('result') or {}).get('status') == 'blocked' for r in rows)
    starts = [_time(s['start'], now) for s in spans] or [now]
    ends = [_time(s['end'], now) for s in spans] or [now]
    attributes = {
        'openinference.span.kind': 'AGENT', 'rockpro.agent.run_id': run_id, 'rockpro.client': client,
        'rockpro.agent.tool_calls': len(rows), 'rockpro.agent.failed_calls': failed,
        'rockpro.agent.refused_calls': limited, 'rockpro.agent.blocked_calls': blocked,
        'rockpro.agent.prompt_version': first.get('prompt_version'),
        'rockpro.agent.policy_sha256': first.get('policy_sha256'), 'rockpro.agent.toolset_sha256': first.get('toolset_sha256'),
        'rockpro.agent.usage_status': first.get('usage_status'),
        'output.value': json.dumps(dict(tools=sorted({str(r.get('tool')) for r in rows}), failed=failed, blocked=blocked, refused=limited)),
    }
    spans.insert(0, _span(trace, root, None, 'Agent session' + (f' ({client})' if client else ''), 'AGENT',
                          min(starts), max(ends), 'ERROR' if failed else 'OK', attributes))
    return spans
