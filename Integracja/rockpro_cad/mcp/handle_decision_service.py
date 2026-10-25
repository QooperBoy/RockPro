"""Durable operator decisions for the explicitly bound H7159 group only."""
import json
import re
import project_store as store
from pathlib import Path
import hashlib
from material_service import digest, encode
from rockpro_cad.core_case.handle_decisions import review_handle_decision


def ensure(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS handle_decision_versions(
        project_id TEXT NOT NULL REFERENCES projects(id),revision INTEGER NOT NULL,
        evidence_json TEXT NOT NULL,result_json TEXT NOT NULL,decision_reference TEXT NOT NULL,
        project_revision INTEGER NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(project_id,revision))''')


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


def save_handle_reconciliation(project_id,evidence,choice,expected_revision,expected_project_revision,review_sha256,decision_reference,prior_state=None):
    if choice is None:raise ValueError('A constructor choice is required before recording a decision')
    result=preview_handle_reconciliation(evidence,choice,prior_state)
    if result['review_sha256']!=review_sha256:raise ValueError('HANDLE_REVIEW_CHANGED')
    if not isinstance(decision_reference,str) or not decision_reference.strip() or len(decision_reference)>500:raise ValueError('Decision reference required')
    if type(expected_revision) is not int or expected_revision<0:raise ValueError('Handle decision revision required')
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
