"""Revision-bound process evidence. Decision origin and executor are independent.

Only leaf operations enter the automation denominator; spans never do. Evidence
is reported by the producer, not proof of geometry or an automatic AI fallback.
"""
from collections import Counter
import hashlib
import json
import math
import re
import uuid

SCHEMA = 'rockpro.process-run/1'
ORIGINS = ('standard', 'ai', 'manual', 'unknown')
EXECUTORS = ('sdk', 'python', 'agent', 'constructor', 'unknown')
TERMINAL = {'success', 'failed', 'skipped', 'resolved'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':'))


def identity(value, label='ID'):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', value):
        raise ValueError('Nieprawidłowy ' + label)
    return value


def text(value, maximum=1000):
    if not isinstance(value, str) or len(value) > maximum or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError('Nieprawidłowy opis zdarzenia')
    return value


def validate_event(value):
    allowed = {'event_id', 'kind', 'operation_id', 'attempt', 'status', 'origin', 'executor',
               'stage', 'label', 'part_id', 'occurrence_id', 'intervention_id', 'reason',
               'duration_ms', 'evidence_sha256', 'timestamp_utc'}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError('Nieznane pola zdarzenia')
    e = dict(value)
    for key in ('event_id', 'operation_id', 'stage'):
        identity(e.get(key), key)
    if e.get('kind') not in ('operation', 'intervention', 'span'):
        raise ValueError('Nieznany rodzaj zdarzenia')
    statuses = ('requested', 'running', 'resolved', 'failed') if e['kind'] == 'intervention' else ('running', 'success', 'failed', 'skipped')
    if e.get('status') not in statuses:
        raise ValueError('Nieznany stan zdarzenia')
    e.setdefault('attempt', 1)
    if type(e['attempt']) is not int or not 1 <= e['attempt'] <= 100:
        raise ValueError('Nieprawidłowy numer próby')
    e.setdefault('origin', 'unknown'); e.setdefault('executor', 'unknown')
    if e['origin'] not in ORIGINS or e['executor'] not in EXECUTORS:
        raise ValueError('Nieznane pochodzenie lub wykonawca')
    if e['kind'] == 'operation' and e['origin'] == 'ai' and not e.get('intervention_id'):
        raise ValueError('Operacja AI wymaga powiązanej interwencji')
    for key in ('part_id', 'occurrence_id', 'intervention_id'):
        if e.get(key) is not None:
            identity(e[key], key)
    for key in ('label', 'reason', 'timestamp_utc'):
        if key in e:
            text(e[key], 1000 if key != 'timestamp_utc' else 80)
    if e['kind'] == 'intervention' and not e.get('reason', '').strip():
        raise ValueError('Interwencja wymaga powodu')
    if e['kind'] == 'intervention' and e['origin'] != 'ai':
        raise ValueError('Interwencja AI wymaga jawnego pochodzenia AI')
    duration = e.get('duration_ms')
    if duration is not None and (type(duration) not in (int, float) or not math.isfinite(duration) or not 0 <= duration <= 604800000):
        raise ValueError('Nieprawidłowy czas')
    if e.get('evidence_sha256') is not None and not re.fullmatch('[a-f0-9]{64}', e['evidence_sha256']):
        raise ValueError('Nieprawidłowy SHA dowodu')
    return e


def merge_events(existing, batch):
    if not isinstance(batch, list) or len(batch) > 500:
        raise ValueError('Jedna partia może zawierać najwyżej 500 zdarzeń')
    result = list(existing); ids = {e['event_id']: e for e in result}
    for raw in batch:
        e = validate_event(raw)
        if e['event_id'] in ids:
            if canonical(ids[e['event_id']]) != canonical(e):
                raise ValueError('ID zdarzenia już ma inną treść')
            continue
        previous = [x for x in result if x['kind'] == e['kind'] and x['operation_id'] == e['operation_id']]
        latest = previous[-1] if previous else None
        if latest:
            if e['attempt'] < latest['attempt'] or e['attempt'] > latest['attempt'] + 1:
                raise ValueError('Nieciągła kolejność prób')
            if e['attempt'] == latest['attempt'] and latest['status'] in TERMINAL:
                raise ValueError('Wynik zakończonej próby jest niezmienny')
            if e['attempt'] > latest['attempt'] and latest['status'] != 'failed':
                raise ValueError('Ponowienie wymaga nieudanej poprzedniej próby')
            for key in ('origin', 'executor', 'part_id', 'occurrence_id', 'intervention_id'):
                if e['attempt'] == latest['attempt'] and e.get(key) != latest.get(key):
                    raise ValueError('Pochodzenie operacji nie może zmienić się w trakcie próby')
        if e['kind'] == 'operation' and e.get('intervention_id'):
            if not any(x['kind'] == 'intervention' and x['operation_id'] == e['intervention_id'] for x in result):
                raise ValueError('Brak wcześniejszego zapisu interwencji')
        result.append(e); ids[e['event_id']] = e
    if len(result) > 10000 or len(canonical(result).encode()) > 8*1024*1024:
        raise ValueError('Przekroczono limit śladu')
    return result


def summarize(events):
    latest = {}; attempts = {}
    for e in events:
        latest[(e['kind'], e['operation_id'])] = e
        attempts[(e['kind'], e['operation_id'], e['attempt'])] = e
    operations = [e for (kind, _), e in latest.items() if kind == 'operation']
    completed = [e for e in operations if e['status'] == 'success']
    by_origin = {k: sum(e['origin'] == k for e in completed) for k in ORIGINS}
    by_executor = {k: sum(e['executor'] == k for e in completed) for k in EXECUTORS}
    denominator = len(completed)
    interventions = [e for (kind, _), e in latest.items() if kind == 'intervention']
    spans = [e for (kind, _), e in latest.items() if kind == 'span']
    return dict(completed=denominator, failed=sum(e['status'] == 'failed' for e in operations),
        running=sum(e['status'] == 'running' for e in operations), skipped=sum(e['status'] == 'skipped' for e in operations),
        by_origin=by_origin, by_executor=by_executor,
        percent={k: round(100*v/denominator, 2) if denominator else None for k, v in by_origin.items()},
        interventions=len(interventions), unresolved_interventions=sum(e['status'] not in ('resolved', 'failed') for e in interventions),
        failed_interventions=sum(e['status']=='failed' for e in interventions),
        open_spans=sum(e['status']=='running' for e in spans),
        operation_attempts=sum(kind == 'operation' for kind, _, _ in attempts),
        retry_attempts=sum(kind == 'operation' and attempt > 1 for kind, _, attempt in attempts),
        measured_leaf_ms=sum(e.get('duration_ms') or 0 for (kind, _, _), e in attempts.items() if kind == 'operation' and e['status'] in TERMINAL),
        timing_note='Suma zmierzonych prób operacji; nie czas całego przebiegu. Spany i czas interwencji są osobne.',
        attribution='reported_by_producer', coverage='recorded_operations_only',
        coarse_jobs_without_details=sum(e['status']=='success' and not any(o['operation_id'].startswith(e['operation_id']+'/line/') for o in operations) for e in spans),
        operations=operations, intervention_rows=interventions, spans=spans)


def _tables(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS studio_process_runs (
        id TEXT PRIMARY KEY, draft_id TEXT NOT NULL, draft_revision INTEGER NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL)''')


def binding(draft_id, revision):
    from . import configurator
    from .mcp import project_store
    if not configurator.re_id(draft_id) or type(revision) is not int or revision < 1:
        raise ValueError('Najpierw zapisz draft i wybierz jego rewizję')
    with project_store.db() as conn:
        configurator._tables(conn)
        row = conn.execute('SELECT payload FROM configurator_draft_versions WHERE id=? AND revision=?', (draft_id, revision)).fetchone()
    if row is None:
        raise ValueError('Brak zapisanej rewizji draftu')
    return dict(draft_id=draft_id, draft_revision=revision,
                draft_sha256=hashlib.sha256(canonical(json.loads(row['payload'])).encode()).hexdigest())


def create(draft_id, revision, label, mode='actual'):
    from .mcp import project_store
    if mode not in ('actual', 'simulation'):
        raise ValueError('Nieznany rodzaj przebiegu')
    bound = binding(draft_id, revision); stamp = project_store.now()
    report = dict(schema=SCHEMA, id=uuid.uuid4().hex, binding=bound, label=text(label, 200),
        mode=mode, state='running', created_at=stamp, updated_at=stamp, events=[])
    with project_store.db() as conn:
        _tables(conn)
        conn.execute('INSERT INTO studio_process_runs VALUES (?,?,?,?,?,?)',
            (report['id'], draft_id, revision, stamp, stamp, canonical(report)))
    return report


def read(run_id):
    from .mcp import project_store
    identity(run_id)
    with project_store.db() as conn:
        _tables(conn); row = conn.execute('SELECT payload FROM studio_process_runs WHERE id=?', (run_id,)).fetchone()
    if row is None:
        raise ValueError('Nie znaleziono przebiegu')
    report = json.loads(row['payload']); report['summary'] = summarize(report['events'])
    return report


def list_runs(draft_id):
    from .mcp import project_store
    identity(draft_id)
    with project_store.db() as conn:
        _tables(conn)
        rows = conn.execute('SELECT payload FROM studio_process_runs WHERE draft_id=? ORDER BY updated_at DESC LIMIT 100', (draft_id,)).fetchall()
    return [dict(id=r['id'], label=r['label'], mode=r['mode'], state=r['state'], binding=r['binding'],
                 updated_at=r['updated_at'], summary={k:v for k,v in summarize(r['events']).items() if k not in ('operations','intervention_rows','spans')})
            for r in (json.loads(row['payload']) for row in rows)]


def append(run_id, events=None, state=None):
    from .mcp import project_store
    if state is not None and state not in ('completed', 'failed', 'partial'):
        raise ValueError('Nieznany wynik przebiegu')
    with project_store.db() as conn:
        _tables(conn); conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT payload FROM studio_process_runs WHERE id=?', (identity(run_id),)).fetchone()
        if row is None:
            raise ValueError('Nie znaleziono przebiegu')
        r = json.loads(row['payload']); merged = merge_events(r['events'], events or [])
        if r['state'] != 'running' and (merged != r['events'] or state not in (None, r['state'])):
            raise ValueError('Zakończony przebieg jest niezmienny')
        summary = summarize(merged)
        if state == 'completed' and (summary['failed'] or summary['running'] or summary['unresolved_interventions'] or summary['failed_interventions'] or summary['open_spans']):
            raise ValueError('Przebieg ma błędy lub niezakończone operacje/interwencje')
        r.update(events=merged, state=state or r['state'], updated_at=project_store.now())
        conn.execute('UPDATE studio_process_runs SET payload=?,updated_at=? WHERE id=?', (canonical(r), r['updated_at'], run_id))
    return read(run_id)


def validate_report(value, bound):
    """Pure portable validation, also used by the browser-storage cloud demo."""
    keys = {'schema','id','binding','label','mode','state','created_at','updated_at','events','summary'}
    if not isinstance(value, dict) or set(value)-keys or value.get('schema') != SCHEMA:
        raise ValueError('Nieznany raport przebiegu')
    r = {k:v for k,v in value.items() if k != 'summary'}
    if r.get('binding') != bound:
        raise ValueError('Raport dotyczy innego draftu lub rewizji')
    identity(r.get('id')); text(r.get('label'), 200)
    if r.get('mode') not in ('actual','simulation') or r.get('state') not in ('running','completed','partial','failed'):
        raise ValueError('Nieznany stan raportu')
    text(r.get('created_at'),80); text(r.get('updated_at'),80)
    events = r.get('events')
    if not isinstance(events,list) or len(events)>10000:
        raise ValueError('Nieprawidłowe zdarzenia raportu')
    validated=[]
    for i in range(0,len(events),500): validated=merge_events(validated,events[i:i+500])
    if len(validated)!=len(events): raise ValueError('Powtórzone zdarzenia w pliku')
    r['events']=validated; summary=summarize(validated)
    if r['state']=='completed' and (summary['failed'] or summary['running'] or summary['unresolved_interventions'] or summary['failed_interventions'] or summary['open_spans']):
        raise ValueError('Raport błędnie deklaruje zakończenie')
    return r


def import_report(value, draft_id, revision):
    from .mcp import project_store
    # Import preserves the original ID. Reimport is idempotent, not another run.
    r=validate_report(value,binding(draft_id,revision))
    with project_store.db() as conn:
        _tables(conn); conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT payload FROM studio_process_runs WHERE id=?',(r['id'],)).fetchone()
        if old:
            if canonical(json.loads(old['payload']))!=canonical(r): raise ValueError('ID przebiegu już ma inną treść')
        else:
            conn.execute('INSERT INTO studio_process_runs VALUES (?,?,?,?,?,?)',(r['id'],draft_id,revision,r['created_at'],r['updated_at'],canonical(r)))
    return read(r['id'])
