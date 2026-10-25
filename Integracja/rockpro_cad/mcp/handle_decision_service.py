"""Durable operator decisions for the explicitly bound H7159 group only."""
import json
import re
import project_store as store
from pathlib import Path
import hashlib
import uuid
from material_service import digest, encode
from rockpro_cad.core_case.handle_decisions import review_handle_decision
from rockpro_cad.core_case.handle_measurement import capture_handle_measurement
from rockpro_cad.core_case.native_changes import _dimension_values


def ensure(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS handle_decision_versions(
        project_id TEXT NOT NULL REFERENCES projects(id),revision INTEGER NOT NULL,
        evidence_json TEXT NOT NULL,result_json TEXT NOT NULL,decision_reference TEXT NOT NULL,
        project_revision INTEGER NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(project_id,revision))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS handle_measurements(
        id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),
        project_revision INTEGER NOT NULL,decision_revision INTEGER NOT NULL,
        evidence_json TEXT NOT NULL,prior_state_json TEXT, snapshot_sha256 TEXT NOT NULL,
        provenance_json TEXT NOT NULL,created_at TEXT NOT NULL)''')


def measure_handle_reconciliation(project_id,expected_revision,expected_project_revision,target_values=None):
    """Observe the saved baseline's bound handles; never create a baseline by guess."""
    import worker
    with store.db() as conn:
        conn.execute('BEGIN');card=store.project_exists(conn,project_id);ensure(conn)
        store.check_revision(expected_project_revision,card,'PROJECT_CONFLICT')
        row=conn.execute('SELECT * FROM handle_decision_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',(project_id,)).fetchone()
        if row is None:raise ValueError('HANDLE_BASELINE_REQUIRED: najpierw wczytaj przypięty pomiar bazowy i zapisz decyzję')
        if type(expected_revision) is not int or row['revision']!=expected_revision:raise ValueError('HANDLE_DECISION_REVISION_CONFLICT')
        previous=json.loads(row['evidence_json']);prior_state=json.loads(row['result_json']).get('state')
    source=worker.source_path(card['source'])
    measured=capture_handle_measurement(source,previous['baseline'],previous['mapping'])
    evidence=dict(baseline=previous['baseline'],current=measured['snapshot'],mapping=previous['mapping'],
        per_wall=previous['per_wall'],target_values=_dimension_values(measured['snapshot']) if target_values is None else target_values,
        observed_source_sha256=measured['source_sha256'])
    preview=preview_handle_reconciliation(evidence,prior_state=prior_state)
    ident=uuid.uuid4().hex;stamp=store.now()
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');store.check_revision(expected_project_revision,store.project_exists(conn,project_id),'PROJECT_CONFLICT')
        current=conn.execute('SELECT MAX(revision) FROM handle_decision_versions WHERE project_id=?',(project_id,)).fetchone()[0]
        if current!=expected_revision:raise ValueError('HANDLE_DECISION_REVISION_CONFLICT')
        conn.execute('INSERT INTO handle_measurements VALUES (?,?,?,?,?,?,?,?,?)',
            (ident,project_id,expected_project_revision,expected_revision,encode(evidence),None if prior_state is None else encode(prior_state),
             measured['snapshot_sha256'],encode(measured['provenance']),stamp))
    return dict(measurement_id=ident,evidence=evidence,prior_state=prior_state,preview=preview,
        project_revision=expected_project_revision,revision=expected_revision,native_read_only=True,
        document_modified=measured['provenance']['modified'],captured_at=stamp,cad_changed=False,production_approved=False)


def preview_handle_reconciliation(evidence,choice=None,prior_state=None):
    fields={'baseline','current','mapping','per_wall','target_values','observed_source_sha256'}
    if not isinstance(evidence,dict) or set(evidence)!=fields:raise ValueError('Exact bound handle evidence required')
    sha=evidence['observed_source_sha256']
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Observed saved-source SHA256 required')
    result=review_handle_decision(**{k:v for k,v in evidence.items() if k!='observed_source_sha256'},choice=choice,prior_state=prior_state)
    result['observed_source_sha256']=sha
    result['review_sha256']=digest(result)
    result['native_capture_verified_by_service']=False
    return result


def get_handle_reconciliation(project_id):
    with store.db() as conn:
        conn.execute('BEGIN');store.project_exists(conn,project_id);ensure(conn)
        row=conn.execute('SELECT * FROM handle_decision_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',(project_id,)).fetchone()
    if row is None:return dict(project_id=project_id,revision=0,saved=False)
    return dict(project_id=project_id,revision=row['revision'],saved=True,evidence=json.loads(row['evidence_json']),
        result=json.loads(row['result_json']),decision_reference=row['decision_reference'],project_revision=row['project_revision'],
        created_at=row['created_at'],cad_changed=False,production_approved=False)


def save_handle_reconciliation(project_id,evidence,choice,expected_revision,expected_project_revision,review_sha256,decision_reference,prior_state=None,measurement_id=None):
    if choice is None:raise ValueError('A constructor choice is required before recording a decision')
    result=preview_handle_reconciliation(evidence,choice,prior_state)
    if result['review_sha256']!=review_sha256:raise ValueError('HANDLE_REVIEW_CHANGED')
    if not isinstance(decision_reference,str) or not decision_reference.strip() or len(decision_reference)>500:raise ValueError('Decision reference required')
    if type(expected_revision) is not int or expected_revision<0:raise ValueError('Handle decision revision required')
    if measurement_id is not None:
        with store.db() as conn:
            ensure(conn);ticket=conn.execute('SELECT * FROM handle_measurements WHERE id=?',(measurement_id,)).fetchone()
        if ticket is None or ticket['project_id']!=project_id:raise ValueError('HANDLE_MEASUREMENT_NOT_FOUND')
        if (ticket['project_revision']!=expected_project_revision or ticket['decision_revision']!=expected_revision or
            json.loads(ticket['evidence_json'])!=evidence or
            (None if ticket['prior_state_json'] is None else json.loads(ticket['prior_state_json']))!=prior_state):
            raise ValueError('HANDLE_MEASUREMENT_BINDING_CONFLICT')
        with store.db() as conn:card=store.project_exists(conn,project_id)
        import worker
        # Fresh observation before recording the decision. Application still
        # needs another preflight; this does not lock out a human editing CAD.
        verified_measurement=capture_handle_measurement(worker.source_path(card['source']),evidence['baseline'],evidence['mapping'])
        if (verified_measurement['snapshot_sha256']!=ticket['snapshot_sha256'] or
            verified_measurement['source_sha256']!=evidence['observed_source_sha256']):
            raise ValueError('HANDLE_MEASUREMENT_STALE')
        result['native_capture_verified_by_service']=True
        result['measurement_id']=measurement_id
        result['native_capture_provenance']=verified_measurement['provenance']
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');card=store.project_exists(conn,project_id);ensure(conn)
        store.check_revision(expected_project_revision,card,'PROJECT_CONFLICT')
        with Path(card['source']).open('rb') as stream:source_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        if source_sha!=evidence['observed_source_sha256']:raise ValueError('HANDLE_SOURCE_CHANGED')
        current=conn.execute('SELECT COALESCE(MAX(revision),0) FROM handle_decision_versions WHERE project_id=?',(project_id,)).fetchone()[0]
        if current!=expected_revision:raise ValueError('HANDLE_DECISION_REVISION_CONFLICT')
        revision=current+1;stamp=store.now()
        conn.execute('INSERT INTO handle_decision_versions VALUES (?,?,?,?,?,?,?)',
            (project_id,revision,encode(evidence),encode(result),decision_reference,card['revision'],stamp))
        event=dict(revision=revision,choice=choice,blocked=result['blocked'],review_sha256=review_sha256,
                   decision_reference=decision_reference,identity_verified=False,cad_changed=False)
        conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',(project_id,stamp,'handle_decision_recorded',encode(event)))
    return dict(project_id=project_id,revision=revision,saved=True,result=result,cad_changed=False,production_approved=False)
