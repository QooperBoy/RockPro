"""Durable Studio CAD dispatch, with no implicit native adapter or crash retry.

The real executor owns the global CAD mutex. This module only serializes local
dispatch through the existing project database; HTTP threads never execute CAD.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import threading

from .mcp import project_store
from .cad_lock import cad_writer_lock

_LOCK = threading.RLock()
_ACTIVE = set()
_ID = re.compile(r'[0-9a-f]{32}\Z')
_MESSAGES = {
    'queued': ('CAD_QUEUED', 'Zlecenie oczekuje na wykonawcę CAD.'),
    'running': ('CAD_RUNNING', 'Wykonawca CAD przetwarza zlecenie.'),
    'succeeded': ('CAD_SUCCEEDED', 'Wykonawca potwierdził wykonanie tego planu.'),
    'rejected': ('CAD_PLAN_REJECTED', 'Plan przestał być aktualny przed wykonaniem. Nie uruchomiono wykonawcy CAD; przygotuj nowy plan.'),
    'outcome_unknown': ('CAD_OUTCOME_UNKNOWN', 'Wynik nie jest potwierdzony. Uzgodnij stan modelu przed kolejnym wykonaniem.'),
    'failed_reconciled': ('CAD_FAILED_RECONCILED', 'Budowa nie powiodła się. Zachowano kopię odzyskiwania i potwierdzono sprzątnięcie; można przygotować nowe zlecenie.'),
    'reconciliation_required': ('CAD_RECONCILIATION_REQUIRED', 'Przerwane zlecenie wymaga uzgodnienia stanu modelu. Nie zostanie ponowione automatycznie.'),
}


class CadJobError(ValueError):
    def __init__(self, code, message):
        self.details = dict(code=code, message=message)
        super().__init__(message)


def verify_plan(plan):
    # Lazy import keeps this dispatcher independent of adapter initialization.
    from . import studio_cad
    return studio_cad.verify_plan(plan)


def _operation_id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise CadJobError('CAD_INVALID_OPERATION_ID', 'Identyfikator zlecenia musi mieć 32 małe znaki szesnastkowe.')


def _tables(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS studio_cad_jobs (
        operation_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL,
        plan_sha256 TEXT NOT NULL, plan_payload TEXT NOT NULL,
        status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        receipt TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS studio_cad_job_reconciliations (
        operation_id TEXT PRIMARY KEY REFERENCES studio_cad_jobs(operation_id),
        created_at TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
        previous_status TEXT NOT NULL, previous_receipt TEXT, evidence_payload TEXT NOT NULL)''')


def _evidence(folder, row):
    """Validate historical, pinned execution bytes; never re-analyse a newer draft."""
    from .studio_cad import fingerprint
    folder = Path(folder).resolve(strict=True)
    plan = json.loads(row['plan_payload'])
    if (plan['plan_sha256'] != row['plan_sha256'] or
            fingerprint({k:v for k,v in plan.items() if k != 'plan_sha256'}) != row['plan_sha256'] or
            plan['plan_id'] != row['plan_id'] or
            not re.fullmatch('studio-'+re.escape(plan['plan_id'])+r'-[0-9a-f]{8}', folder.name)):
        raise ValueError('Unbound plan or evidence folder')
    hashes = {}
    def file(name):
        path = (folder/name).resolve(strict=True)
        if not path.is_relative_to(folder) or not path.is_file():
            raise ValueError('Evidence outside job folder')
        return path
    def digest(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    def read(name):
        path = file(name)
        if path.stat().st_size > 64*1024*1024:
            raise ValueError('Evidence too large')
        raw = path.read_bytes(); hashes[name] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw.decode('utf-8-sig'))
    request = read('request.json'); compiled = read('compile.json')
    report = read('result.json'); cleanup = read('addon_cleanup.json')
    spec = plan['native_spec']
    if (request.get('contract') != 'roc46-native-v1' or
            request.get('plan_sha256') != row['plan_sha256'] or
            report.get('plan_sha256', row['plan_sha256']) != row['plan_sha256']):
        raise ValueError('Evidence belongs to another plan')
    # Adapter adds only private source paths and execution options to this spec.
    for key, expected in spec.items():
        actual = request.get(key)
        if key == 'sources':
            actual = [{k:v for k,v in s.items() if k != 'path'} for s in actual]
        if actual != expected:
            raise ValueError('Request differs from pinned native plan')
    hashes['native-source.cs'] = digest(file('native-source.cs'))
    if (compiled.get('returncode') != 0 or
            compiled.get('source_sha256') != spec['executor_sha256'] or
            hashes['native-source.cs'] != spec['executor_sha256']):
        raise ValueError('Executor evidence mismatch')
    if (report.get('passed') is not False or report.get('sources_unchanged') is not True or
            report.get('existing_documents_preserved') is not True or
            not isinstance(report.get('before'), list) or
            report['before'] != report.get('after_existing') or report.get('final_visible') is not False or
            any(('cleanup' in k or 'preservation' in k) and 'error' in k for k in report) or
            cleanup.get('removed') is not True or type(cleanup.get('count_after')) is not int or
            cleanup['count_after'] != 0 or type(cleanup.get('remaining_count')) is not int or
            cleanup['remaining_count'] != 0 or 'error' in cleanup):
        raise ValueError('Native cleanup or preservation not proven')
    source_hashes = {}
    if not request.get('sources'):
        raise ValueError('Missing source identities')
    for source in request['sources']:
        path = Path(source['path']).resolve(strict=True)
        actual = digest(path)
        if actual != source['sha256'] or source['key'] in source_hashes:
            raise ValueError('Source mismatch')
        source_hashes[source['key']] = actual
    recovery = Path(report['recovery_path']).resolve(strict=True)
    if not recovery.is_relative_to(folder) or recovery.suffix.lower() != '.ics' or recovery.stat().st_size == 0:
        raise ValueError('Missing owned recovery')
    recovery_sha = digest(recovery)
    proof = dict(schema='rockpro.studio-cad-reconciliation/1', operation_id=row['operation_id'],
                 plan_sha256=row['plan_sha256'], evidence_folder=str(folder), files=hashes,
                 recovery_path=str(recovery), recovery_sha256=recovery_sha, source_sha256=source_hashes)
    return proof, fingerprint(proof)


def reconcile_failed_job(operation_id, evidence_folder):
    """LOCAL maintenance only; never expose through the HTTP request dispatcher.

    A failed execution remains failed. This records evidence allowing a new job,
    without retrying CAD or pretending the failure occurred before execution.
    """
    _operation_id(operation_id)
    with cad_writer_lock(), _LOCK:
        with project_store.db() as conn:
            _tables(conn)
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM studio_cad_jobs WHERE operation_id=?', (operation_id,)).fetchone()
            if row is None:
                raise CadJobError('CAD_JOB_NOT_FOUND', 'Nie znaleziono zlecenia CAD.')
            if row['status'] not in ('outcome_unknown', 'failed_reconciled') or _key(operation_id) in _ACTIVE:
                raise CadJobError('CAD_RECONCILE_STATUS', 'Uzgodnić można tylko zakończone zlecenie o niepotwierdzonym wyniku.')
            try:
                proof, evidence_sha = _evidence(evidence_folder, row)
            except Exception:
                raise CadJobError('CAD_RECONCILE_EVIDENCE', 'Dowody są niepełne, zmienione lub nie należą do tego zlecenia. Kolejka pozostaje zablokowana.') from None
            previous = conn.execute('SELECT evidence_sha256 FROM studio_cad_job_reconciliations WHERE operation_id=?', (operation_id,)).fetchone()
            if row['status'] == 'failed_reconciled':
                if previous is None or previous['evidence_sha256'] != evidence_sha:
                    raise CadJobError('CAD_RECONCILE_CONFLICT', 'Zlecenie uzgodniono już na podstawie innych dowodów.')
                return _view(row)
            stamp = project_store.now()
            receipt = dict(passed=False, plan_sha256=row['plan_sha256'], reconciliation=dict(
                evidence_sha256=evidence_sha, recovery_sha256=proof['recovery_sha256'],
                sources_unchanged=True, existing_documents_preserved=True, cleanup_confirmed=True))
            conn.execute('INSERT INTO studio_cad_job_reconciliations VALUES (?,?,?,?,?,?)',
                         (operation_id, stamp, evidence_sha, row['status'], row['receipt'], json.dumps(proof, ensure_ascii=False)))
            changed = conn.execute("UPDATE studio_cad_jobs SET status='failed_reconciled',updated_at=?,receipt=? WHERE operation_id=? AND status='outcome_unknown' AND plan_sha256=?",
                                   (stamp, json.dumps(receipt), operation_id, row['plan_sha256']))
            if changed.rowcount != 1:
                raise CadJobError('CAD_RECONCILE_CONFLICT', 'Stan zlecenia zmienił się podczas uzgadniania.')
            return _view(conn.execute('SELECT * FROM studio_cad_jobs WHERE operation_id=?', (operation_id,)).fetchone())


def _key(operation_id):
    return (str(project_store.DB_PATH.resolve()), operation_id)


def _view(row):
    status = row['status']
    if status in ('queued', 'running') and _key(row['operation_id']) not in _ACTIVE:
        status = 'reconciliation_required'
    code, message = _MESSAGES[status]
    return dict(operation_id=row['operation_id'], plan_id=row['plan_id'],
                plan_sha256=row['plan_sha256'], status=status,
                recorded_status=row['status'], code=code, message=message,
                created_at=row['created_at'], updated_at=row['updated_at'],
                requires_reconciliation=status in ('outcome_unknown', 'reconciliation_required'),
                receipt=json.loads(row['receipt']) if row['receipt'] else None)


class CadJobs:
    def __init__(self, executor=None):
        if executor is not None and not callable(executor):
            raise CadJobError('CAD_INVALID_EXECUTOR', 'Wykonawca CAD musi być funkcją.')
        self._executor = executor

    def get(self, operation_id):
        _operation_id(operation_id)
        with _LOCK, project_store.db() as conn:
            _tables(conn)
            row = conn.execute('SELECT * FROM studio_cad_jobs WHERE operation_id=?', (operation_id,)).fetchone()
            if row is None:
                raise CadJobError('CAD_JOB_NOT_FOUND', 'Nie znaleziono zlecenia CAD.')
            return _view(row)

    def submit(self, plan, operation_id):
        _operation_id(operation_id)
        try:
            detached = copy.deepcopy(plan)
            verify_plan(detached)
            payload = json.dumps(detached, ensure_ascii=False, allow_nan=False, sort_keys=True)
        except Exception:
            raise CadJobError('CAD_INVALID_PLAN', 'Plan jest nieprawidłowy lub jego wersja nie jest już aktualna.') from None
        with _LOCK:
            with project_store.db() as conn:
                _tables(conn)
                conn.execute('BEGIN IMMEDIATE')
                row = conn.execute('SELECT * FROM studio_cad_jobs WHERE operation_id=?', (operation_id,)).fetchone()
                if row is not None:
                    if row['plan_sha256'] != detached['plan_sha256']:
                        raise CadJobError('CAD_OPERATION_CONFLICT', 'Ten identyfikator zlecenia dotyczy innego planu.')
                    return _view(row)
                if detached.get('executable') is not True or detached.get('blockers') != []:
                    raise CadJobError('CAD_PLAN_BLOCKED', 'Plan ma blokery lub nie jest wykonywalny. Uzupełnij wymagane dane przed budową.')
                if self._executor is None:
                    raise CadJobError('CAD_EXECUTOR_UNAVAILABLE', 'Wykonawca IronCAD nie jest podłączony. Model nie został utworzony.')
                if conn.execute("SELECT 1 FROM studio_cad_jobs WHERE status IN ('queued','running','outcome_unknown') LIMIT 1").fetchone():
                    raise CadJobError('CAD_JOB_BUSY', 'Inne zlecenie trwa lub wymaga uzgodnienia. Nie rozpoczęto kolejnej budowy.')
                stamp = project_store.now()
                conn.execute('INSERT INTO studio_cad_jobs VALUES (?,?,?,?,?,?,?,?)',
                             (operation_id, detached['plan_id'], detached['plan_sha256'], payload,
                              'queued', stamp, stamp, None))
            # Registration and start are atomic with respect to local get/submit.
            _ACTIVE.add(_key(operation_id))
            try:
                threading.Thread(target=self._run, args=(operation_id, detached),
                                 name='RockPro-Studio-CAD', daemon=True).start()
            except Exception:
                self._finish(operation_id, 'outcome_unknown', None)
            return self.get(operation_id)

    def _finish(self, operation_id, status, receipt):
        with _LOCK:
            try:
                with project_store.db() as conn:
                    _tables(conn)
                    conn.execute('UPDATE studio_cad_jobs SET status=?,updated_at=?,receipt=? WHERE operation_id=?',
                                 (status, project_store.now(), json.dumps(receipt) if receipt else None, operation_id))
            except Exception:
                # A durable running/queued row remains unresolved if persistence
                # fails. It blocks another job and is never silently retried.
                pass
            finally:
                _ACTIVE.discard(_key(operation_id))

    def _run(self, operation_id, plan):
        status, receipt = 'outcome_unknown', None
        try:
            with project_store.db() as conn:
                _tables(conn)
                conn.execute("UPDATE studio_cad_jobs SET status='running',updated_at=? WHERE operation_id=? AND status='queued'",
                             (project_store.now(), operation_id))
            expected_hash = plan['plan_sha256']
            try:
                verify_plan(copy.deepcopy(plan))
            except Exception:
                # This refusal precedes the executor, so there are no unknown
                # native effects and a fresh job may be submitted safely.
                status = 'rejected'
                return
            # No database connection or dispatcher lock is held during execution.
            raw = self._executor(copy.deepcopy(plan))
            if (isinstance(raw, dict) and raw.get('passed') is True
                    and raw.get('plan_sha256') == expected_hash):
                status = 'succeeded'
                receipt = dict(passed=True, plan_sha256=expected_hash)
                for key in ('output_path','output_sha256','occurrence_count','machining_count',
                            'physical_parts','source_preservation','existing_documents_preserved','native_report'):
                    if key in raw:
                        receipt[key]=raw[key]
        except Exception:
            # Never expose adapter exceptions, paths, or private native details.
            pass
        finally:
            self._finish(operation_id, status, receipt)
