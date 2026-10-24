"""ROC-33: immutable plans, stale-input guard and append-only actual progress.

No inventory balance, consumption or purchase is undone by changing a plan.
Produced parts are only reuse candidates until an operator accepts them.
"""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path

import project_store as store
from material_service import aggregate_bom_demand, digest, encode, token
from cutting_plan import verify_cut_plan
from inventory_service import quantity
from purchase_proposals import money, monetary_text


def ensure(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS material_plans(id TEXT PRIMARY KEY,
        payload_sha256 TEXT NOT NULL,payload_json TEXT NOT NULL,status TEXT NOT NULL,
        revision INTEGER NOT NULL,created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS material_progress(id TEXT PRIMARY KEY,
        plan_id TEXT NOT NULL REFERENCES material_plans(id),event_sha256 TEXT NOT NULL,
        event_json TEXT NOT NULL,created_at TEXT NOT NULL)''')


def file_hash(path):
    path=Path(path);before=path.stat()
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Source changed during hashing')
    return sha


def input_state(conn,project_ids):
    state=[]
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for ident in sorted(project_ids):
        card=store.project_exists(conn,ident)
        bom=conn.execute('SELECT revision,document_sha256 FROM bom_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',(ident,)).fetchone()
        if bom is None:raise ValueError('BOM_REQUIRED')
        layout=conn.execute('SELECT MAX(revision) FROM layout_versions WHERE project_id=?',(ident,)).fetchone()[0] if 'layout_versions' in tables else None
        snapshot=conn.execute('SELECT id,sha256,path FROM snapshots WHERE project_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(ident,)).fetchone()
        def fingerprint(path):
            try:return dict(sha256=file_hash(path))
            except (OSError,ValueError):return dict(error='file_missing_or_unstable')
        state.append(dict(project_id=ident,card_revision=card['revision'],quantity=card['quantity'],
            bom_revision=bom['revision'],bom_sha256=bom['document_sha256'],layout_revision=layout,
            source_file=fingerprint(card['source']),snapshot=None if snapshot is None else
            dict(id=snapshot['id'],registered_sha256=snapshot['sha256'],file=fingerprint(snapshot['path']))))
    return state


def _load(conn,plan_id):
    row=conn.execute('SELECT * FROM material_plans WHERE id=?',(plan_id,)).fetchone()
    if row is None:raise ValueError('MATERIAL_PLAN_NOT_FOUND')
    data=json.loads(row['payload_json'])
    if digest(data)!=row['payload_sha256']:raise ValueError('MATERIAL_PLAN_INTEGRITY_FAILED')
    current=input_state(conn,[b['project_id'] for b in data['demand']['bindings']])
    stale=current!=data['input_state']
    progress=[dict(id=r['id'],created_at=r['created_at'],event=json.loads(r['event_json']))
              for r in conn.execute('SELECT * FROM material_progress WHERE plan_id=? ORDER BY created_at,id',(plan_id,))]
    effective=('outdated' if row['status']=='ready' else 'changed_in_progress') if stale else row['status']
    return dict(id=plan_id,revision=row['revision'],status=row['status'],effective_status=effective,
                stale=stale,payload=data,payload_sha256=row['payload_sha256'],progress=progress,
                current_input_state=current,production_approved=False)


def save_material_plan(plan_id,project_ids,sheets,technology,cut_plan,supersedes_plan_id=None):
    token(plan_id,'plan ID')
    demand=aggregate_bom_demand(project_ids);verification=verify_cut_plan(demand,sheets,technology,cut_plan)
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');ensure(conn)
        current=input_state(conn,project_ids)
        if any(s['source_file'].get('error') or (s['snapshot'] and s['snapshot']['file'].get('error')) for s in current):
            raise ValueError('Material plan needs stable source/snapshot files')
        expected={b['project_id']:(b['revision'],b['document_sha256']) for b in demand['bindings']}
        if any(expected[s['project_id']]!=(s['bom_revision'],s['bom_sha256']) for s in current):raise ValueError('BOM_CHANGED_DURING_PLANNING')
        if supersedes_plan_id is not None:
            token(supersedes_plan_id,'previous plan ID');old=_load(conn,supersedes_plan_id)
            if {b['project_id'] for b in old['payload']['demand']['bindings']}!=set(project_ids):raise ValueError('Superseded plan project set differs')
        payload=dict(demand=demand,sheets=sheets,technology=technology,cut_plan=cut_plan,
                     verification_sha256=digest(verification),input_state=current,supersedes_plan_id=supersedes_plan_id)
        existing=conn.execute('SELECT payload_sha256 FROM material_plans WHERE id=?',(plan_id,)).fetchone()
        if existing:
            if existing['payload_sha256']!=digest(payload):raise ValueError('MATERIAL_PLAN_ID_REUSED')
            return _load(conn,plan_id)|dict(replayed=True)
        conn.execute('INSERT INTO material_plans VALUES (?,?,?,?,?,?)',(plan_id,digest(payload),encode(payload),'ready',1,store.now()))
        result=_load(conn,plan_id)
    return result|dict(replayed=False)


def get_material_plan(plan_id):
    with store.db() as conn:
        conn.execute('BEGIN');ensure(conn);return _load(conn,plan_id)


def start_material_plan(plan_id,expected_revision):
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');ensure(conn);plan=_load(conn,plan_id)
        if type(expected_revision) is not int or plan['revision']!=expected_revision:raise ValueError('MATERIAL_PLAN_REVISION_CONFLICT')
        if plan['stale']:raise ValueError('MATERIAL_PLAN_OUTDATED')
        if plan['status']!='ready':raise ValueError('Material plan already started; do not repeat physical operations')
        p=plan['payload'];verify_cut_plan(p['demand'],p['sheets'],p['technology'],p['cut_plan'])
        conn.execute("UPDATE material_plans SET status='started',revision=revision+1 WHERE id=?",(plan_id,))
        return _load(conn,plan_id)


def record_material_progress(plan_id,event_id,event,expected_revision):
    token(event_id,'progress event ID')
    if not isinstance(event,dict):raise ValueError('Progress event required')
    kind=event.get('type')
    if kind=='produced':
        if set(event)!={'type','group_index','quantity'} or type(event['group_index']) is not int or event['group_index']<0:raise ValueError('Produced group/quantity required')
        quantity(event['quantity'])
    elif kind=='committed_order':
        if set(event)!={'type','reference','item_id','quantity','total_gross','currency','arrival_date'}:raise ValueError('Exact committed order fields required')
        for k in ('reference','item_id'):token(event[k],k)
        quantity(event['quantity']);money(event['total_gross'])
        if not isinstance(event['currency'],str) or len(event['currency'])!=3 or not event['currency'].isupper():raise ValueError('Order currency required')
        if date.fromisoformat(event['arrival_date']).isoformat()!=event['arrival_date']:raise ValueError('ISO order arrival required')
    else:raise ValueError('Unknown progress event; no undo-consumption/order command')
    event_hash=digest(dict(plan_id=plan_id,event=event))
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');ensure(conn)
        previous=conn.execute('SELECT * FROM material_progress WHERE id=?',(event_id,)).fetchone()
        if previous:
            if previous['event_sha256']!=event_hash:raise ValueError('PROGRESS_EVENT_ID_REUSED')
            return _load(conn,plan_id)|dict(replayed=True)
        plan=_load(conn,plan_id)
        if type(expected_revision) is not int or expected_revision!=plan['revision']:raise ValueError('MATERIAL_PLAN_REVISION_CONFLICT')
        if plan['status']!='started':raise ValueError('Record actual progress only after explicit start')
        if kind=='produced' and event['group_index']>=len(plan['payload']['demand']['groups']):raise ValueError('Unknown produced group')
        conn.execute('INSERT INTO material_progress VALUES (?,?,?,?,?)',(event_id,plan_id,event_hash,encode(event),store.now()))
        conn.execute('UPDATE material_plans SET revision=revision+1 WHERE id=?',(plan_id,))
        return _load(conn,plan_id)|dict(replayed=False)


def compare_material_plans(old_plan_id,new_plan_id):
    with store.db() as conn:
        conn.execute('BEGIN');ensure(conn);old=_load(conn,old_plan_id);new=_load(conn,new_plan_id)
    if {s['project_id'] for s in old['payload']['input_state']}!={s['project_id'] for s in new['payload']['input_state']}:raise ValueError('Plan project sets differ')
    key_fields=('material_id','finish','technology_id','thickness_mm','grain_axis','rotation_allowed','cut_length_mm','cut_width_mm')
    def key(g):return tuple(g[k] for k in key_fields)
    produced=Counter();orders=[]
    for p in old['progress']:
        event=p['event']
        if event['type']=='produced':produced[key(old['payload']['demand']['groups'][event['group_index']])]+=event['quantity']
        else:orders.append(event)
    initial=produced.copy();changes=[]
    for g in sorted(new['payload']['demand']['groups'],key=lambda g:g['required_date']):
        match=key(g);candidate=min(g['quantity'],produced[match]);produced[match]-=candidate
        changes.append(dict(new_group=g,required_quantity=g['quantity'],reuse_candidate_quantity=candidate,
            shortage_without_reuse=g['quantity'],shortage_if_reuse_accepted=g['quantity']-candidate,
            reuse_approved=False,quality_and_term_check_required=True))
    totals={}
    for order in orders:totals[order['currency']]=totals.get(order['currency'],money(0))+money(order['total_gross'])
    return dict(old_plan_id=old_plan_id,new_plan_id=new_plan_id,old_revision=old['revision'],new_revision=new['revision'],
        old_status=old['effective_status'],new_status=new['effective_status'],changes=changes,
        produced_total=sum(initial.values()),unallocated_produced_total=sum(produced.values()),
        committed_orders_preserved=orders,committed_expense_by_currency={k:monetary_text(v) for k,v in totals.items()},
        incremental_cost=None,incremental_cost_status='requires_current_pricing_and_reuse_acceptance',
        delivery_impact='compare_new_required_dates_with_preserved_order_arrivals; no automatic expedite',
        inventory_reversed=False,orders_cancelled=False,production_approved=False)
