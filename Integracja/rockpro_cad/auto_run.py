"""Record CAD jobs in the Studio process registry by default.

A job script that is not given a run opens its own run, bound to a saved draft
revision, and closes it when the job ends:

    completed  every step finished and nothing is open
    partial    the job finished but the registry refuses `completed`
               (e.g. the native trace could not be imported)
    failed     the job raised

A run that was passed in (`--run-id`) is never closed here; its owner closes it.
The registry rules are unchanged: an AI operation still needs a recorded
decision with a reason (see `decision_event`).
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys

from . import process_runs

REPO = Path(__file__).resolve().parents[2]


def studio_database():
    """The registry the observability tools share: ROCKPRO_STUDIO_DATABASE, else artifacts/studio.sqlite.

    Studio must be started with the same file (reference_studio --database ...).
    """
    return Path(os.environ.get('ROCKPRO_STUDIO_DATABASE') or REPO / 'artifacts' / 'studio.sqlite')


def decision_event(decision_id, reason, stage='native', label='AI decision'):
    """The registry event for an AI decision (intervention) with its reason, now."""
    return dict(event_id='decision/' + decision_id, kind='intervention', operation_id=decision_id,
                stage=stage, origin='ai', executor='agent', status='resolved', label=label,
                reason=reason, timestamp_utc=datetime.now(timezone.utc).isoformat())


def latest_draft(database):
    """(draft id, revision) of the newest saved draft revision, or None.

    Opens the database read-only, so a mistyped path never creates an empty one.
    """
    path = Path(database)
    if not path.exists():
        return None
    conn = sqlite3.connect(f'file:{path.resolve().as_posix()}?mode=ro', uri=True)
    try:
        row = conn.execute('SELECT id, revision FROM configurator_draft_versions '
                           'ORDER BY created_at DESC, revision DESC LIMIT 1').fetchone()
    except sqlite3.OperationalError:
        return None  # Studio never saved a draft into this file.
    finally:
        conn.close()
    return (row[0], int(row[1])) if row else None


class NoDraft(RuntimeError):
    pass


def _close(run_id, state, out):
    try:
        return process_runs.append(run_id, state=state)['state']
    except ValueError as exc:
        if state != 'completed':
            raise
        print(f'run {run_id}: cannot close as completed ({exc}); closing as partial', file=out)
        return process_runs.append(run_id, state='partial')['state']


@contextmanager
def recorded_run(database, label, run_id=None, draft=None, out=sys.stdout):
    """Yield the run ID to record into; open and close one if none was given.

    `database` must already be the active registry (project_store.DB_PATH).
    `draft` is (id, revision); default: the newest saved draft revision.
    """
    if run_id:
        yield run_id
        return
    draft = draft or latest_draft(database)
    if draft is None:
        raise NoDraft(f'No saved Studio draft in {database}. Save a draft in Studio first '
                      '(docs/PHOENIX_DASHBOARD.md), pass --draft-id, or --no-record to run without logging.')
    report = process_runs.create(draft[0], draft[1], label)
    run_id = report['id']
    print(f'recording into new run {run_id} (draft {draft[0]} rev {draft[1]}); it is closed automatically', file=out, flush=True)
    try:
        yield run_id
    except BaseException:
        try:
            print(f'run {run_id} closed as {_close(run_id, "failed", out)}', file=out, flush=True)
        except Exception as exc:  # Never hide the job's own error behind bookkeeping.
            print(f'run {run_id} could not be closed: {exc}', file=out, flush=True)
        raise
    print(f'run {run_id} closed as {_close(run_id, "completed", out)}', file=out, flush=True)
