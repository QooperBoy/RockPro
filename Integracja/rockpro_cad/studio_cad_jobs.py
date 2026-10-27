"""Durable Studio CAD dispatch, with no implicit native adapter or crash retry.

The real executor owns the global CAD mutex. This module only serializes local
dispatch through the existing project database; HTTP threads never execute CAD.
"""
import copy
import json
import re
import threading

from .mcp import project_store

_LOCK = threading.RLock()
_ACTIVE = set()
_ID = re.compile(r'[0-9a-f]{32}\Z')
_MESSAGES = {
    'queued': ('CAD_QUEUED', 'Zlecenie oczekuje na wykonawcę CAD.'),
    'running': ('CAD_RUNNING', 'Wykonawca CAD przetwarza zlecenie.'),
    'succeeded': ('CAD_SUCCEEDED', 'Wykonawca potwierdził wykonanie tego planu.'),
    'rejected': ('CAD_PLAN_REJECTED', 'Plan przestał być aktualny przed wykonaniem. Nie uruchomiono wykonawcy CAD; przygotuj nowy plan.'),
    'outcome_unknown': ('CAD_OUTCOME_UNKNOWN', 'Wynik nie jest potwierdzony. Uzgodnij stan modelu przed kolejnym wykonaniem.'),
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
        except Exception:
            # Never expose adapter exceptions, paths, or private native details.
            pass
        finally:
            self._finish(operation_id, status, receipt)
