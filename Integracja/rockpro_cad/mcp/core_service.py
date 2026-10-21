"""Shared SQLite case proposals and a durable, copy-only execution journal.

UI and MCP use this same service. A receipt proves a synthetic prototype only;
it never promotes source inventory, changes the project's source, or grants CAD
production approval. External I/O is confined to the configured Integracja root.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

import project_store as store
import worker
from rockpro_cad.core_case import plan_case


class CoreServiceError(ValueError):
    def __init__(self, code, message, **details):
        self.details = dict(code=code, message=message, **details)
        super().__init__(json.dumps(self.details, ensure_ascii=False))


def _require(condition, code, message, **details):
    if not condition:
        raise CoreServiceError(code, message, **details)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash_text(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _id(value, name):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value),
             'INVALID_ID', name + ' must be a bounded identifier')
    return value


def _revision(expected, current):
    _require(type(expected) is int and expected >= 0 and expected == current,
             'CASE_REVISION_CONFLICT', 'Case request changed; read and compare before saving or executing',
             expected_revision=expected, current_revision=current)


def _ensure(conn):
    # Additive tables in project_store.db, never a second project database.
    conn.execute('''CREATE TABLE IF NOT EXISTS case_requests (
        project_id TEXT PRIMARY KEY REFERENCES projects(id), revision INTEGER NOT NULL,
        request_json TEXT NOT NULL, request_sha TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS case_request_versions (
        project_id TEXT NOT NULL REFERENCES projects(id), revision INTEGER NOT NULL,
        request_json TEXT NOT NULL, request_sha TEXT NOT NULL, created_at TEXT NOT NULL,
        actor TEXT NOT NULL, change_source TEXT NOT NULL, PRIMARY KEY(project_id,revision))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS case_plans (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
        request_revision INTEGER NOT NULL, saved_request_sha TEXT NOT NULL,
        request_json TEXT NOT NULL, request_sha TEXT NOT NULL, spec_sha TEXT NOT NULL,
        recipe_sha TEXT NOT NULL, plan_json TEXT NOT NULL, plan_sha TEXT NOT NULL,
        binding_json TEXT NOT NULL, created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS case_operations (
        project_id TEXT NOT NULL REFERENCES projects(id), operation_id TEXT NOT NULL,
        plan_id TEXT NOT NULL REFERENCES case_plans(id), request_revision INTEGER NOT NULL,
        state TEXT NOT NULL, directory TEXT NOT NULL, receipt_json TEXT, result_json TEXT,
        diagnostic_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(project_id,operation_id))''')


def _event(conn, project_id, kind, payload):
    conn.execute('INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)',
                 (project_id, store.now(), kind, _json(payload)))


def preview_case(request):
    """Pure: accepts data and returns a proposal without touching SQLite or CAD."""
    return plan_case(request)


def _request_row(conn, project_id):
    return conn.execute('SELECT * FROM case_requests WHERE project_id=?', (project_id,)).fetchone()


def _request_result(row):
    if row is None:
        return dict(saved=False, revision=0, request=None, sha256=None)
    _require(_hash_text(row['request_json']) == row['request_sha'], 'CASE_REQUEST_INTEGRITY', 'Saved request hash differs')
    return dict(saved=True, revision=row['revision'], request=json.loads(row['request_json']),
                sha256=row['request_sha'], updated_at=row['updated_at'])


def get_case_request(project_id):
    with store.db() as conn:
        _ensure(conn)
        store.project_exists(conn, project_id)
        return _request_result(_request_row(conn, project_id))


def _layout_binding(conn, project_id, request):
    reference = request['spec']['dimension_source']['reference']
    if not reference.startswith('prototype-layout:'):
        return None
    import layout
    layout.ensure(conn)
    row = conn.execute('SELECT * FROM layout_versions WHERE project_id=? ORDER BY revision DESC LIMIT 1',
                       (project_id,)).fetchone()
    expected = f"prototype-layout:{project_id}:{row['revision']}:{row['sha256']}" if row else None
    _require(reference == expected and json.loads(row['spec']) == request['spec']['layout'],
             'LAYOUT_CONFLICT', 'Prepared request no longer matches the saved layout')
    return dict(project_id=project_id, revision=row['revision'], sha256=row['sha256'])


def save_case_request(project_id, request, expected_revision, actor='unspecified', change_source='unspecified'):
    actor, change_source = store.text(actor, 'actor', 200), store.text(change_source, 'change_source', 200)
    preview = preview_case(request)
    if preview['status'] != 'planned':
        return dict(saved=False, status='blocked', diagnostics=preview['diagnostics'], preview=preview)
    payload, stamp = _json(request), store.now()
    digest = _hash_text(payload)
    with store.db() as conn:
        _ensure(conn)
        conn.execute('BEGIN IMMEDIATE')
        store.project_exists(conn, project_id)
        row = _request_row(conn, project_id)
        _revision(expected_revision, row['revision'] if row else 0)
        _layout_binding(conn, project_id, request)
        revision = expected_revision + 1
        conn.execute('INSERT INTO case_request_versions VALUES (?,?,?,?,?,?,?)',
                     (project_id, revision, payload, digest, stamp, actor, change_source))
        conn.execute('INSERT OR REPLACE INTO case_requests VALUES (?,?,?,?,?)',
                     (project_id, revision, payload, digest, stamp))
        _event(conn, project_id, 'case_request_saved', dict(revision=revision, sha256=digest,
                    actor=actor, source=change_source, identity_verified=False, production_approved=False))
        result = _request_result(_request_row(conn, project_id))
    return dict(result, preview=preview)


def prepare_case_request(project_id, expected_layout_revision):
    import layout
    saved = layout.get_layout(project_id)
    _require(saved['saved'] and type(expected_layout_revision) is int and expected_layout_revision == saved['revision'],
             'LAYOUT_CONFLICT', 'Read the current saved layout before preparing a case request')
    spec = copy.deepcopy(saved['spec'])
    _require(spec['count'] == 2 and spec['side'] in ('X', 'Y') and spec['separator'] > 0,
             'PROTOTYPE_LAYOUT_UNSUPPORTED', 'Prototype recipe requires two devices, an X/Y accessory compartment and a positive divider thickness')
    recipe_path = Path(__file__).resolve().parents[1] / 'core_case' / 'templates' / 'prototype-v1.json'
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    with store.db() as conn:
        project = store.project_exists(conn, project_id)
    approval = 'SYNTHETIC-CONSTRUCTOR-APPROVAL-1'
    case_spec = dict(case_id='prototype-' + project_id, schema_version=1, revision=saved['revision'],
                     expected_revision=saved['revision'], template_version=recipe['template_version'],
                     units='mm', axes='right-handed-XYZ', layout=spec, display_gap=0,
                     dimension_source=dict(kind='synthetic', confirmation='test-only',
                         reference=f"prototype-layout:{project_id}:{saved['revision']}:{saved['sha256']}"),
                     interior_symmetry_approval=approval, order_quantity=project['quantity'])
    manifest = dict(version=recipe['template_version'], synthetic=True, production_approved=False,
                    source_template='synthetic-prototype-input-only',
                    required_families=list(dict.fromkeys(g['family'] for g in recipe['groups'])),
                    empty_assembly_ids=copy.deepcopy(recipe['inventory']['empty_assembly_ids']), unresolved_ids=[],
                    interior_exception_approval=approval, group_roles=[g['symmetry_group_id'] for g in recipe['groups']])
    request = dict(spec=case_spec, manifest=manifest, template_recipe=recipe, scenario={'operation': 'plan'})
    return dict(request=request, layout_revision=saved['revision'], layout_sha256=saved['sha256'],
                production_approved=False, preview=preview_case(request))


def _source(project):
    source = worker.source_path(project['source'])
    _require(source.name.lower() != 'snapshot.ics', 'SOURCE_INVALID', 'An archive cannot be the working source')
    return source, _hash_file(source)


def plan_project_case(project_id, expected_revision, scenario=None):
    with store.db() as conn:
        _ensure(conn)
        conn.execute('BEGIN IMMEDIATE')
        project = store.project_exists(conn, project_id)
        row = _request_row(conn, project_id)
        _revision(expected_revision, row['revision'] if row else 0)
        _require(row is not None, 'CASE_REQUEST_REQUIRED', 'Save an explicit case request first')
        request = _request_result(row)['request']
        saved_sha = row['request_sha']
        if scenario is not None:
            request['scenario'] = copy.deepcopy(scenario)
        layout_binding = _layout_binding(conn, project_id, request)
        plan = preview_case(request)
        if plan['status'] != 'planned':
            return dict(status='blocked', revision=row['revision'], diagnostics=plan['diagnostics'], plan=plan)
        source, source_sha = _source(project)
        binding = dict(project_id=project_id, project_revision=project['revision'], source=str(source),
                        source_sha256=source_sha, request_revision=row['revision'], layout_binding=layout_binding)
        plan_id, stamp = uuid.uuid4().hex, store.now()
        payload, plan_payload = _json(request), _json(plan)
        request_sha, plan_sha = _hash_text(payload), _hash_text(plan_payload)
        conn.execute('INSERT INTO case_plans VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                     (plan_id, project_id, row['revision'], saved_sha, payload, request_sha,
                      _hash_text(_json(request['spec'])), _hash_text(_json(request['template_recipe'])),
                      plan_payload, plan_sha, _json(binding), stamp))
        _event(conn, project_id, 'case_plan_created', dict(plan_id=plan_id, revision=row['revision'],
                     plan_sha256=plan_sha, binding=binding, production_approved=False))
    return dict(status='planned', plan_id=plan_id, revision=expected_revision, plan=plan,
                sha256=plan_sha, request_sha256=request_sha, binding=binding)


def _load_plan(conn, project_id, plan_id):
    row = conn.execute('SELECT * FROM case_plans WHERE id=? AND project_id=?', (plan_id, project_id)).fetchone()
    _require(row is not None, 'CASE_PLAN_NOT_FOUND', 'Plan does not belong to this project')
    request, plan, binding = (json.loads(row[k]) for k in ('request_json', 'plan_json', 'binding_json'))
    _require(_hash_text(row['request_json']) == row['request_sha']
             and _hash_text(row['plan_json']) == row['plan_sha']
             and _hash_text(_json(request['spec'])) == row['spec_sha']
             and _hash_text(_json(request['template_recipe'])) == row['recipe_sha'],
             'CASE_PLAN_INTEGRITY', 'Stored immutable plan or request hash differs')
    _require(_json(preview_case(request)) == row['plan_json'], 'CASE_PLAN_INTEGRITY', 'Stored plan does not replay from its pinned input')
    return row, request, plan, binding


def _current_binding(conn, project_id, row, request, binding):
    project = store.project_exists(conn, project_id)
    current = _request_row(conn, project_id)
    _revision(row['request_revision'], current['revision'] if current else 0)
    _request_result(current)
    _require(current['request_sha'] == row['saved_request_sha'], 'CASE_REQUEST_INTEGRITY', 'Saved request differs from the pinned plan')
    _require(project['revision'] == binding['project_revision'], 'PROJECT_CONFLICT', 'Project card changed after planning')
    source, digest = _source(project)
    _require(str(source) == binding['source'] and digest == binding['source_sha256'],
             'SOURCE_CHANGED', 'Pinned source changed after planning')
    _layout_binding(conn, project_id, request)
    return source


def _operation_dir(project_id, operation_id):
    root = Path(worker.ROOT).resolve(strict=True)
    parent = root / 'case_runs' / _id(project_id, 'project_id')
    target = parent / _id(operation_id, 'operation_id')
    _require(parent.resolve().is_relative_to(root) and target.resolve().is_relative_to(root),
             'OUTPUT_PATH_INVALID', 'Operation directory escaped the configured integration root')
    return parent, target


def _operation_result(row):
    if row['result_json']:
        result = json.loads(row['result_json'])
        if row['state'] == 'registered':
            _, target = _operation_dir(row['project_id'], row['operation_id'])
            archive = target / 'snapshot.ics'
            report = target / 'service_receipt.json'
            receipt = json.loads(row['receipt_json'])
            _require(result.get('receipt') == receipt and result.get('snapshot_path') == str(archive)
                     and result.get('report_path') == str(report) and archive.is_file()
                     and _hash_file(archive) == receipt['output_sha256'] and report.is_file(),
                     'OUTPUT_INTEGRITY', 'Registered archive or receipt is missing or changed')
            evidence = json.loads(report.read_text(encoding='utf-8'))
            _require(evidence.get('receipt') == receipt and evidence.get('plan_id') == row['plan_id']
                     and evidence.get('operation_id') == row['operation_id']
                     and evidence.get('snapshot_sha256') == receipt['output_sha256'],
                     'OUTPUT_INTEGRITY', 'Registered recovery evidence differs')
        return result
    return dict(status=row['state'], operation_id=row['operation_id'], plan_id=row['plan_id'],
                revision=row['request_revision'], diagnostic=json.loads(row['diagnostic_json']) if row['diagnostic_json'] else None)


def get_case_operation(project_id, operation_id):
    with store.db() as conn:
        _ensure(conn)
        store.project_exists(conn, project_id)
        row = conn.execute('SELECT * FROM case_operations WHERE project_id=? AND operation_id=?',
                           (project_id, operation_id)).fetchone()
        _require(row is not None, 'CASE_OPERATION_NOT_FOUND', 'Operation does not exist in this project')
        if row['state'] == 'registered':
            _load_plan(conn, project_id, row['plan_id'])
        return _operation_result(row)


def list_case_operations(project_id, limit=50):
    _require(type(limit) is int and 1 <= limit <= 100, 'INVALID_LIMIT', 'Operation limit must be an integer 1..100')
    with store.db() as conn:
        _ensure(conn)
        store.project_exists(conn, project_id)
        rows = conn.execute('''SELECT operation_id,plan_id,request_revision,state,created_at,updated_at
            FROM case_operations WHERE project_id=? ORDER BY
            CASE WHEN state NOT IN ('registered','failed') THEN 0 ELSE 1 END, created_at DESC LIMIT ?''',
            (project_id, limit)).fetchall()
    return dict(operations=[dict(row) for row in rows])


def _stage(project_id, operation_id, state, diagnostic=None):
    with store.db() as conn:
        _ensure(conn)
        conn.execute('BEGIN IMMEDIATE')
        updated = conn.execute("UPDATE case_operations SET state=?,diagnostic_json=?,updated_at=? WHERE project_id=? AND operation_id=? AND state!='registered'",
                     (state, _json(diagnostic) if diagnostic else None, store.now(), project_id, operation_id))
        if updated.rowcount:
            _event(conn, project_id, 'case_operation_stage', dict(operation_id=operation_id, state=state, diagnostic=diagnostic))


def _native_execute(plan, **kwargs):
    from rockpro_cad.core_case.native import execute_plan
    return execute_plan(plan, **kwargs)


def _write_once(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(_json(value))
        stream.flush()
        os.fsync(stream.fileno())


def _verify_receipt(receipt, plan, binding, target, operation_id):
    _require(isinstance(receipt, dict) and receipt.get('passed') is True
             and receipt.get('source_unchanged') is True and receipt.get('production_approved') is False
             and receipt.get('operation_id') == operation_id
             and receipt.get('geometry_scope') == 'synthetic_native_block_prototype',
             'NATIVE_RECEIPT_INVALID', 'Receipt must explicitly prove an unapproved synthetic copy')
    _require(all(receipt.get('stages', {}).get(key) == 'PASS' for key in
                 ('read', 'copy', 'change_on_copy', 'measurement', 'save_reopen')),
             'NATIVE_RECEIPT_INVALID', 'Native read, measurement, save and reopen stages must pass')
    output = Path(receipt['output_path']).resolve(strict=True)
    _require(target.resolve().is_relative_to(Path(worker.ROOT).resolve())
             and output.parent == target.resolve() and output.suffix.lower() == '.ics'
             and output.name.lower() not in ('snapshot.ics', 'source_snapshot.ics')
             and output != Path(binding['source']).resolve(),
             'OUTPUT_PATH_INVALID', 'Native output must be a new working file in this operation directory')
    _require(_hash_file(output) == receipt.get('output_sha256'), 'OUTPUT_INTEGRITY', 'Native working file hash differs')
    source = receipt.get('source', {})
    _require(Path(source['path']).resolve() == Path(binding['source']).resolve()
             and source.get('sha256_before') == source.get('sha256_after') == binding['source_sha256']
             and source.get('unchanged') is True
             and _hash_file(binding['source']) == binding['source_sha256'],
             'SOURCE_CHANGED', 'Native receipt does not match the unchanged pinned source')
    capture = Path(source['snapshot_path']).resolve(strict=True)
    _require(capture.parent == target.resolve() and capture.name == 'source_snapshot.ics'
             and _hash_file(capture) == source['snapshot_sha256'],
             'OUTPUT_INTEGRITY', 'Source capture is missing or changed')
    from rockpro_cad.core_case.native import compare_measurements, preflight_plan
    compare_measurements(preflight_plan(plan), receipt['measurements'])
    return output


def _register(project_id, operation_id, receipt):
    with store.db() as conn:
        _ensure(conn)
        operation = conn.execute('SELECT * FROM case_operations WHERE project_id=? AND operation_id=?',
                                 (project_id, operation_id)).fetchone()
        if operation['state'] == 'registered':
            _load_plan(conn, project_id, operation['plan_id'])
            return _operation_result(operation)
        row, request, plan, binding = _load_plan(conn, project_id, operation['plan_id'])
        _current_binding(conn, project_id, row, request, binding)
    _, target = _operation_dir(project_id, operation_id)
    _require(str(target) == operation['directory'], 'OUTPUT_PATH_INVALID', 'Journal output directory differs')
    output = _verify_receipt(receipt, plan, binding, target, operation_id)
    _stage(project_id, operation_id, 'saved')
    archive = target / 'snapshot.ics'
    if archive.exists():
        _require(_hash_file(archive) == receipt['output_sha256'], 'OUTPUT_INTEGRITY', 'Existing archive differs; never overwrite it')
    else:
        with output.open('rb') as src, archive.open('xb') as dst:
            for block in iter(lambda: src.read(1024*1024), b''):
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
    _require(_hash_file(archive) == receipt['output_sha256'], 'OUTPUT_INTEGRITY', 'Archive copy hash differs')
    evidence = dict(schema_version=1, project_id=project_id, operation_id=operation_id, plan_id=row['id'],
                    request_revision=row['request_revision'], request_sha256=row['request_sha'], plan_sha256=row['plan_sha'],
                    binding=binding, receipt=receipt, snapshot_path=str(archive), snapshot_sha256=_hash_file(archive))
    report = target / 'service_receipt.json'
    if report.exists():
        _require(json.loads(report.read_text(encoding='utf-8')) == evidence, 'OUTPUT_INTEGRITY', 'Stored recovery evidence differs')
    else:
        _write_once(report, evidence)
    _stage(project_id, operation_id, 'reopened_verified')
    snapshot_id = 'case-' + row['id'] + '-' + operation_id
    result = dict(status='registered', operation_id=operation_id, plan_id=row['id'], revision=row['request_revision'],
                   receipt=receipt, snapshot_id=snapshot_id, snapshot_path=str(archive), report_path=str(report),
                   production_approved=False, validation='prototype', source_advanced=False)
    with store.db() as conn:
        _ensure(conn)
        conn.execute('BEGIN IMMEDIATE')
        # Repeat all CAS/source checks at registration, after the external call.
        current_row, current_request, _, current_binding = _load_plan(conn, project_id, row['id'])
        _current_binding(conn, project_id, current_row, current_request, current_binding)
        current_operation = conn.execute('SELECT * FROM case_operations WHERE project_id=? AND operation_id=?',
                                         (project_id, operation_id)).fetchone()
        if current_operation['state'] == 'registered':
            return _operation_result(current_operation)
        _require(_hash_file(output) == _hash_file(archive) == receipt['output_sha256'],
                 'OUTPUT_INTEGRITY', 'Artifact changed before registration')
        conn.execute('''INSERT OR IGNORE INTO snapshots
            (id,project_id,created_at,label,note,path,source,sha256,parameters,validation,report_path,layout_binding)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (snapshot_id, project_id, store.now(), 'Prototyp syntetyczny skrzyni',
             'Bryły zastępcze; bez zatwierdzenia katalogu, montażu i produkcji', str(archive), binding['source'],
             receipt['output_sha256'], _json(dict(plan_id=row['id'], request_revision=row['request_revision'],
                 plywood_external=plan['plywood_external'], production_approved=False)), 'prototype', str(report),
             _json(binding['layout_binding']) if binding.get('layout_binding') else None))
        conn.execute('UPDATE case_operations SET state=?,receipt_json=?,result_json=?,diagnostic_json=NULL,updated_at=? WHERE project_id=? AND operation_id=?',
                     ('registered', _json(receipt), _json(result), store.now(), project_id, operation_id))
        _event(conn, project_id, 'case_prototype_registered', dict(operation_id=operation_id, snapshot_id=snapshot_id,
                     plan_id=row['id'], production_approved=False, source_advanced=False))
    return result


def execute_case_plan(project_id, plan_id, operation_id, expected_revision):
    _id(operation_id, 'operation_id')
    parent, target = _operation_dir(project_id, operation_id)
    with store.db() as conn:
        _ensure(conn)
        conn.execute('BEGIN IMMEDIATE')
        previous = conn.execute('SELECT * FROM case_operations WHERE project_id=? AND operation_id=?',
                                (project_id, operation_id)).fetchone()
        if previous:
            _require(previous['plan_id'] == plan_id and type(expected_revision) is int
                     and previous['request_revision'] == expected_revision,
                     'OPERATION_ID_CONFLICT', 'An operation ID cannot be rebound to another plan or revision')
            _load_plan(conn, project_id, previous['plan_id'])
            return _operation_result(previous)
        row, request, plan, binding = _load_plan(conn, project_id, plan_id)
        _revision(expected_revision, row['request_revision'])
        source = _current_binding(conn, project_id, row, request, binding)
        unknown = conn.execute("SELECT operation_id FROM case_operations WHERE project_id=? AND state NOT IN ('registered','failed')", (project_id,)).fetchone()
        _require(unknown is None, 'CASE_OPERATION_UNRESOLVED', 'Recover the outstanding operation before starting another',
                 operation_id=unknown['operation_id'] if unknown else None)
        _require(not target.exists(), 'OUTPUT_EXISTS', 'Operation output already exists; explicit recovery is required')
        stamp = store.now()
        conn.execute('INSERT INTO case_operations VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                     (project_id, operation_id, plan_id, expected_revision, 'planned', str(target), None, None, None, stamp, stamp))
        _event(conn, project_id, 'case_operation_stage', dict(operation_id=operation_id, state='planned', plan_id=plan_id))
    parent.mkdir(parents=True, exist_ok=True)
    _stage(project_id, operation_id, 'applying')
    try:
        receipt = _native_execute(copy.deepcopy(plan), output_dir=parent, source=source, operation_id=operation_id)
        if not isinstance(receipt, dict) or receipt.get('passed') is not True:
            _stage(project_id, operation_id, 'failed', dict(code='NATIVE_EXECUTION_FAILED', message='Native executor returned a failed receipt'))
            return get_case_operation(project_id, operation_id)
        return _register(project_id, operation_id, receipt)
    except Exception as exc:
        diagnostic = getattr(exc, 'details', dict(code='NATIVE_OUTCOME_UNKNOWN', message=str(exc)))
        _stage(project_id, operation_id, 'outcome_unknown', diagnostic)
        return get_case_operation(project_id, operation_id)


def recover_case_operation(project_id, operation_id):
    """Read and verify durable evidence only. Never repeat a CAD insertion."""
    _id(operation_id, 'operation_id')
    with store.db() as conn:
        _ensure(conn)
        operation = conn.execute('SELECT * FROM case_operations WHERE project_id=? AND operation_id=?',
                                 (project_id, operation_id)).fetchone()
        _require(operation is not None, 'CASE_OPERATION_NOT_FOUND', 'Unknown operation')
        _load_plan(conn, project_id, operation['plan_id'])
        if operation['state'] in ('registered', 'failed'):
            return _operation_result(operation)
    _, target = _operation_dir(project_id, operation_id)
    _require(str(target) == operation['directory'], 'OUTPUT_PATH_INVALID', 'Journal directory differs')
    receipt_path = target / 'native_receipt.json'
    _require(receipt_path.is_file(), 'RECOVERY_EVIDENCE_REQUIRED', 'Native outcome remains unknown; no complete receipt exists')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    return _register(project_id, operation_id, receipt)
