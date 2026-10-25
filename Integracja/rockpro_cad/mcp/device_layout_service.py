"""Source-bound layout drafts with atomic device/layout concurrency checks."""
import json
import math
import re

import device_catalog as catalog
import layout
from layout_variants import preview_device_layouts, _removal_check
import project_store as store


def _constraints(value):
    keys={'allowed_orientations','allowed_arrangements','removal_clearance_mm','max_external_mm'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('Exact device layout constraints required')
    # The common proposal validator owns validation of list contents and limits.
    return value


def _record(conn,binding,current=True):
    if not isinstance(binding,dict) or set(binding)!={'catalog_id','device_revision','record_sha256','constraints'}:raise ValueError('Exact device binding required')
    for key in ('catalog_id','record_sha256'):
        if not isinstance(binding[key],str) or not re.fullmatch('[0-9a-f]{64}',binding[key]):raise ValueError('Device identity/checksum required')
    if type(binding['device_revision']) is not int or binding['device_revision']<1:raise ValueError('Device revision required')
    _constraints(binding['constraints']);catalog._ensure(conn)
    row=conn.execute('SELECT * FROM device_record_versions WHERE catalog_id=? ORDER BY revision DESC LIMIT 1',(binding['catalog_id'],)).fetchone()
    if row is None:raise ValueError('DEVICE_RECORD_NOT_FOUND')
    if current and (row['revision']!=binding['device_revision'] or row['record_sha256']!=binding['record_sha256']):raise ValueError('DEVICE_REVISION_CONFLICT: source data changed; compare the record before choosing again')
    if not current:row=conn.execute('SELECT * FROM device_record_versions WHERE catalog_id=? AND revision=?',(binding['catalog_id'],binding['device_revision'])).fetchone()
    if row is None:raise ValueError('DEVICE_RECORD_NOT_FOUND')
    record=json.loads(row['record_json']);summary=catalog.preview_device_record(record)
    if summary['record_sha256']!=binding['record_sha256'] or summary['catalog_id']!=binding['catalog_id']:raise ValueError('DEVICE_RECORD_INTEGRITY_FAILED')
    return record,summary


def _checked(record,summary,spec,constraints):
    if not isinstance(spec,dict):raise ValueError('Layout spec required')
    dimensions={axis.lower():summary['fields'][axis]['value'] for axis in 'XYZ'}
    for key,value in dimensions.items():
        if value is None:raise ValueError('DEVICE_DIMENSIONS_MISSING_OR_CONFLICTING')
        if key in spec and (type(spec[key]) not in (int,float) or not math.isclose(spec[key],value,abs_tol=1e-6,rel_tol=0)):
            raise ValueError('DEVICE_DIMENSION_OVERRIDE: explicitly unlink the source before entering manual dimensions')
    source_spec={k:v for k,v in spec.items() if k not in ('x','y','z')}
    proposals=preview_device_layouts(record,source_spec,**constraints)
    orientations=constraints['allowed_orientations'];arrangements=constraints['allowed_arrangements']
    if spec.get('orientation') not in orientations or spec.get('arrangement') not in arrangements:raise ValueError('DEVICE_LAYOUT_CHOICE_NOT_ALLOWED')
    # Validate the selected/edited variant independently of the top-three slice.
    selected=preview_device_layouts(record,source_spec,**(constraints|dict(allowed_orientations=[spec['orientation']],allowed_arrangements=[spec['arrangement']])))
    if not selected['variants']:raise ValueError('DEVICE_LAYOUT_REJECTED: '+str(selected['rejected']))
    result=selected['variants'][0]['layout']
    candidates=[]
    for orientation in orientations:
        for arrangement in arrangements:
            item=dict(orientation=orientation,arrangement=arrangement)
            try:
                candidate=layout._calculate_layout(result['spec']|item)
                maximum=constraints['max_external_mm']
                if maximum is not None and any(n>limit+1e-6 for n,limit in zip(candidate['external'],maximum)):raise ValueError('External limit exceeded')
                removal=_removal_check(candidate,constraints['removal_clearance_mm'])
                if not removal['passed']:raise ValueError('; '.join(removal['failures']))
                item.update(valid=True,volume_l=candidate['volume_l'],external=candidate['external'])
            except ValueError as error:item.update(valid=False,volume_l=None,reason=str(error))
            candidates.append(item)
    candidates.sort(key=lambda c:(not c['valid'],round(c['volume_l'] or 0,9),c['orientation'],c['arrangement']))
    def decorate(rows,key):
        valid=[r['volume_l'] for r in rows if r['valid']];lo,hi=min(valid),max(valid)
        return [dict(r,key=r[key],score=0.0 if hi-lo<1e-9 else (r['volume_l']-lo)/(hi-lo)) if r['valid'] else dict(r,key=r[key],score=None) for r in rows]
    result['ranking']=dict(criterion='allowed_feasible_external_volume',best=candidates[0],variants=candidates,
        orientations=decorate([r for r in candidates if r['arrangement']==spec['arrangement']],'orientation'),
        arrangements=decorate([r for r in candidates if r['orientation']==spec['orientation']],'arrangement'))
    result.update(removal_check=selected['variants'][0]['removal_check'],release_blockers=proposals['release_blockers'],production_approved=False)
    return result


def _ensure(conn):
    layout.ensure(conn)
    conn.execute('''CREATE TABLE IF NOT EXISTS layout_device_bindings(
        project_id TEXT NOT NULL,layout_revision INTEGER NOT NULL,binding_json TEXT NOT NULL,
        PRIMARY KEY(project_id,layout_revision),
        FOREIGN KEY(project_id,layout_revision) REFERENCES layout_versions(project_id,revision))''')


def binding_for_layout(conn,project_id,revision):
    if 'layout_device_bindings' not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}:return None
    row=conn.execute('SELECT binding_json FROM layout_device_bindings WHERE project_id=? AND layout_revision=?',(project_id,revision)).fetchone()
    return None if row is None else json.loads(row[0])


def source_for_layout(conn,project_id,revision):
    binding=binding_for_layout(conn,project_id,revision)
    if binding is None:return dict(device_binding=None,device_source_status='unbound',device_source_info=None)
    try:
        _,summary=_record(conn,binding,current=False)
        latest=conn.execute('SELECT revision,record_sha256 FROM device_record_versions WHERE catalog_id=? ORDER BY revision DESC LIMIT 1',(binding['catalog_id'],)).fetchone()
        status='current' if latest['revision']==binding['device_revision'] and latest['record_sha256']==binding['record_sha256'] else 'stale'
    except ValueError as error:summary=dict(error=str(error));status='unavailable'
    return dict(device_binding=binding,device_source_status=status,device_source_info=summary)


def assert_current_device_binding(conn,project_id,revision):
    binding=binding_for_layout(conn,project_id,revision)
    if binding is None:return None
    _record(conn,binding)
    return binding


def invalidate_device_layouts(conn,catalog_id):
    if 'layout_device_bindings' not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}:return []
    affected=[];stamp=store.now()
    rows=conn.execute('''SELECT b.* FROM layout_device_bindings b WHERE b.layout_revision=
        (SELECT MAX(v.revision) FROM layout_versions v WHERE v.project_id=b.project_id)''').fetchall()
    for row in rows:
        if json.loads(row['binding_json'])['catalog_id']!=catalog_id:continue
        store.change_stages(conn,row['project_id'],['devices','layout','geometry','hardware','wheels','documentation','materials','production'],
                            'outdated','device-catalog','device-record-revision','device_source_changed',stamp)
        affected.append(row['project_id'])
    return affected


def preview_bound_device_layout(binding,spec):
    with store.db() as conn:
        conn.execute('BEGIN');record,summary=_record(conn,binding)
    result=_checked(record,summary,spec,binding['constraints'])
    return result|dict(device_binding=binding,device_source_info=summary)


def preview_catalog_layouts(catalog_id,spec,constraints):
    if not isinstance(spec,dict):raise ValueError('Layout spec required')
    data=catalog.get_device_record(catalog_id)
    binding=dict(catalog_id=catalog_id,device_revision=data['revision'],record_sha256=data['record_sha256'],constraints=_constraints(constraints))
    proposals=preview_device_layouts(data['record'],{k:v for k,v in spec.items() if k not in ('x','y','z')},**constraints)
    return proposals|dict(device_binding=binding,device_source_info={k:v for k,v in data.items() if k!='record'})


def save_bound_device_layout(project_id,spec,binding,expected_revision,actor='operator',change_source='device-layout'):
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');store.project_exists(conn,project_id)
        record,summary=_record(conn,binding);result=_checked(record,summary,spec,binding['constraints']);_ensure(conn)
        saved=layout.save_layout_in_transaction(conn,project_id,result,expected_revision,actor,change_source,device_binding_update=True)
        conn.execute('INSERT INTO layout_device_bindings VALUES (?,?,?)',(project_id,saved['revision'],json.dumps(binding,ensure_ascii=False,sort_keys=True)))
        conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',
            (project_id,store.now(),'layout_device_bound',json.dumps(dict(layout_revision=saved['revision'],binding=binding,release_blockers=result['release_blockers']),ensure_ascii=False)))
    return saved|dict(device_binding=binding,device_source_info=summary)


def unlink_layout_device(project_id,expected_revision,actor='operator',change_source='explicit-device-unlink'):
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');store.project_exists(conn,project_id);layout.ensure(conn)
        row=conn.execute('SELECT * FROM layout_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',(project_id,)).fetchone()
        if row is None or binding_for_layout(conn,project_id,row['revision']) is None:raise ValueError('DEVICE_LAYOUT_NOT_BOUND')
        result=layout.calculate_layout(json.loads(row['spec']))
        saved=layout.save_layout_in_transaction(conn,project_id,result,expected_revision,actor,change_source,device_binding_update=True)
        conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',
            (project_id,store.now(),'layout_device_unlinked',json.dumps(dict(previous_revision=row['revision'],new_revision=saved['revision'],actor=actor,identity_verified=False))))
    return saved|dict(device_binding=None,production_approved=False)
