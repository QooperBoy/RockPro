"""Narrow 17251S showcase: whole components, hidden documents, no BRep inspection.

Requires an existing exact ROT document. Never launches the application. Own
documents are preserved and closed in finally; unknown/user documents stay open.
"""
import ctypes
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from ..cad_lock import cad_writer_lock
from ..parts.native import NativePartsAdapter, file_sha256, same_document_path
from .native import write_receipt_once
from .native_reader import NativePoseAdapter, validate_matrix
from .corner_native import panel_occurrences, exclusive_copy, BackgroundGuard
from .corner_mount import plan_corner_resize
from .latch_placement import plan_latch_pairs

SOURCE_SHA = 'e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1'
SOURCE_GUID = '{D6ECD56D-7836-4796-B64A-C63C0699FF96}'
LATCHES = ((12631, 'lid', 'left', '17251S_1'),
           (12630, 'base', 'left', '17251S'),
           (12782, 'lid', 'right', '17251S_1'),
           (12781, 'base', 'right', '17251S'))


def foreground():
    user = ctypes.WinDLL('user32')
    user.GetForegroundWindow.restype = ctypes.c_void_p
    return int(user.GetForegroundWindow() or 0)


def state(base):
    doc = base.ActiveDoc
    return {'foreground_hwnd': foreground(), 'active_document': None if not doc else
            {'path': str(doc.Name), 'guid': str(doc.FileGUID), 'modified': bool(doc.Modified)}}


def build_panel_bridge(folder):
    """Compile only; no COM, application startup or document creation."""
    folder = Path(folder)
    folder.mkdir(exist_ok=False)
    vendor = Path(r'C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll')
    compiler = Path(os.environ.get('WINDIR', r'C:\Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    bridge = Path(__file__).with_name('LatchPanelBridge.cs')
    exe = folder/'LatchPanelBridge.exe'
    run = subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:x64',
                          '/out:'+str(exe), '/reference:'+str(vendor),
                          '/reference:System.Web.Extensions.dll', '/reference:Microsoft.CSharp.dll',
                          str(bridge)], capture_output=True, text=True,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    write_receipt_once(folder/'compile.json', {'exit_code': run.returncode,
                      'stdout': run.stdout, 'stderr': run.stderr,
                      'bridge_sha256': file_sha256(bridge)})
    if run.returncode:
        raise RuntimeError('Latch panel bridge compilation failed: '+run.stdout+run.stderr)
    shutil.copyfile(vendor, folder/vendor.name)
    return exe


def _pose(context, doc, path):
    return NativePoseAdapter(context.legacy, context.base, doc, context.api, path)


def _matrix_close(a, b):
    return all(abs(a[i][j]-b[i][j]) <= (.003 if i == 3 and j < 3 else 1e-6)
               for i in range(4) for j in range(4))


def _whole(pose, node):
    node = node.QueryInterface(pose.api.IZElement)
    identity = pose.identity(node)
    if identity['kind'] not in ('assembly', 'part'):
        raise ValueError('Only complete native parts/assemblies supported')
    api_type = pose.api.IZAssembly if identity['kind'] == 'assembly' else pose.api.IZPart
    box = [float(v)*1000 for v in node.QueryInterface(api_type).GetBoundingBox(True)]
    if len(box) != 6 or any(not math.isfinite(v) for v in box) or any(box[i] >= box[i+3] for i in range(3)):
        raise ValueError('Invalid whole-component bbox')
    world = validate_matrix(pose.matrix(node, True), allow_reflection=True)
    parent = validate_matrix(pose.matrix(node, False), allow_reflection=True)
    local_center = [(box[i]+box[i+3])/2 for i in range(3)]
    center = [sum(local_center[k]*world[k][i] for k in range(3))+world[3][i] for i in range(3)]
    return {'native_id': int(node.Id), 'name': str(node.Name), 'kind': identity['kind'],
            'children_count': int(pose.child_count(node)), 'matrix_world_mm': world,
            'matrix_parent_mm': parent, 'local_bounds_mm': box,
            'bbox_center_local_mm': local_center, 'bbox_center_world_mm': center}


def _set_matrix(node, matrix, api):
    validate_matrix(matrix, allow_reflection=True)
    element = node.QueryInterface(api.IZSceneElement)
    value = element.GetTransformToParent()
    for i in range(4):
        for j in range(4):
            value.SetValue(i, j, matrix[i][j]/1000 if i == 3 and j < 3 else matrix[i][j])
    element.SetTransformToParent(value)


def _assert_row(actual, expected, *, identity=False):
    for field in ('matrix_world_mm', 'matrix_parent_mm'):
        if field in expected and not _matrix_close(actual[field], expected[field]):
            raise RuntimeError('Whole component pose changed: '+field)
    if max(abs(a-b) for a, b in zip(actual['local_bounds_mm'], expected['local_bounds_mm'])) > .003:
        raise RuntimeError('Whole component bbox changed')
    if identity and any(actual[k] != expected[k] for k in ('native_id', 'name', 'kind', 'children_count')):
        raise RuntimeError('Whole component identity/count changed after reopen')


class Session:
    def __init__(self, context, folder):
        self.context, self.folder, self.owned, self.events = context, Path(folder), [], []
        self.guard = BackgroundGuard(lambda: state(context.base),
            lambda label, phase, value: self.events.append({'label': label, 'phase': phase, 'state': value}))
        self.cleanup = []

    def open(self, path, readonly=False):
        path = Path(path).resolve()
        # Ownership is captured inside the action so a failed post-action guard
        # still leaves a document eligible for finally cleanup.
        def action():
            already, doc = self.context.base.OpenFile2(str(path), readonly, False)
            if already:
                raise RuntimeError('Refusing ownership of a pre-existing document: '+str(path))
            self.owned.append(doc)
            if not same_document_path(doc.Name, path):
                raise RuntimeError('Hidden document path mismatch')
            return doc
        return self.guard.run('open-hidden-'+path.name, action)

    def close(self, doc):
        if doc.Modified:
            raise RuntimeError('Normal close requires clean owned document')
        name = str(doc.Name)
        def action():
            doc.Close()
            self.owned.remove(doc)
            self.cleanup.append({'closed_path': name, 'backup_path': None})
        self.guard.run('close-owned-clean', action)

    def finish(self):
        failures = []
        for doc in list(reversed(self.owned)):
            before = foreground()
            row = {'closed_path': None, 'backup_path': None, 'foreground_before': before}
            try:
                row['original_path'] = str(doc.Name)
                if doc.Modified:
                    backup = self.folder/('preserved_owned_'+uuid.uuid4().hex+'.ics')
                    doc.QueryInterface(self.context.api.IZSceneDoc).SaveAs(
                        str(backup), self.context.api.Z_LINKS_COPY_ALL, False)
                    row['backup_path'] = str(backup)
                    row['backup_sha256'] = file_sha256(backup)
                if doc.Modified:
                    raise RuntimeError('Owned document still modified; preserved without closing')
                name = str(doc.Name)
                doc.Close()
                self.owned.remove(doc)
                row['closed_path'] = name
            except Exception as exc:
                row['error'] = str(exc)
                failures.append(str(exc))
            finally:
                row['foreground_after'] = foreground()
                if row['foreground_after'] != before:
                    failures.append('Foreground changed during cleanup')
                self.cleanup.append(row)
        write_receipt_once(self.folder/'cleanup.json', {'passed': not failures,
            'closed': self.cleanup, 'remaining_owned': len(self.owned), 'errors': failures,
            'unknown_or_user_documents_closed': 0})
        write_receipt_once(self.folder/'background_guards.json', self.events)
        if failures:
            raise RuntimeError('Owned-document cleanup failed: '+repr(failures))


def _measure_case(pose, corner_plan, corner_map, latch_plan, latch_map, source_latches):
    root = pose.root()
    if pose.child_count(root) != 16:  # 10 panel parts + 2 corner containers + 4 opaque latch roots
        raise RuntimeError('Unexpected top-level inventory')
    nodes = [pose.child_at(root, i).QueryInterface(pose.api.IZElement) for i in range(16)]
    if len({int(n.Id) for n in nodes}) != 16:
        raise RuntimeError('Duplicate native root IDs')
    byid = {int(n.Id): n for n in nodes}
    panels = [_whole(pose, n) for n in nodes if str(n.Name).startswith('RP:panels-')]
    expected_panels = panel_occurrences(corner_plan['target_size_mm'], corner_plan['target_case_frame']['matrix_world_mm'])
    if len(panels) != 10 or {r['name'] for r in panels} != {'RP:'+r['id'] for r in expected_panels}:
        raise RuntimeError('Ten panel proxy inventory mismatch')
    for panel in expected_panels:
        actual = next(r for r in panels if r['name'] == 'RP:'+panel['id'])
        _assert_row(actual, {'matrix_world_mm': panel['native_matrix_mm'],
                            'local_bounds_mm': panel['local_bounds'][0]+panel['local_bounds'][1]})
    corners = []
    for assembly in corner_plan['assemblies']:
        node = byid[corner_map[assembly['id']]]
        if str(node.Name) != '410429' or pose.child_count(node) != 4:
            raise RuntimeError('Four-corner container inventory changed')
        if not _matrix_close(pose.matrix(node, True), assembly['matrix_world_mm']):
            raise RuntimeError('Corner root frame changed')
        for item in (r for r in corner_plan['occurrences'] if r['assembly_id'] == assembly['id']):
            child = pose.child_at(node, item['occurrence_path'][-1]).QueryInterface(pose.api.IZElement)
            row = _whole(pose, child)
            _assert_row(row, item)
            row['source_id'] = item['id']
            corners.append(row)
    latches = []
    for item in latch_plan['occurrences']:
        row = _whole(pose, byid[latch_map[item['id']]])
        _assert_row(row, item)
        source = source_latches[item['id']]
        if any(row[k] != source[k] for k in ('name', 'kind', 'children_count')):
            raise RuntimeError('Opaque latch name/kind/direct child count changed')
        row.update(source_id=item['id'], role=item['role'], side=item['side'])
        latches.append(row)
    # Independent semantic check on observed whole bbox centers and pair origins.
    observed = [{'id': r['source_id'], 'role': r['role'], 'side': r['side'],
                 'matrix_world_mm': r['matrix_world_mm'], 'local_bounds_mm': r['local_bounds_mm']} for r in latches]
    plan_latch_pairs(observed, corner_plan['target_case_frame']['matrix_world_mm'][3][:3],
                     latch_plan['target_size_mm'], latch_plan['target_size_mm'])
    gaps = {}
    for role in ('lid', 'base'):
        pair = [next(r for r in latches if r['role'] == role and r['side'] == side) for side in ('left', 'right')]
        minimum = corner_plan['target_case_frame']['matrix_world_mm'][3][0]
        width = latch_plan['target_size_mm'][0]
        gaps[role] = {'left_center_edge_mm': pair[0]['bbox_center_world_mm'][0]-minimum,
                      'right_center_edge_mm': minimum+width-pair[1]['bbox_center_world_mm'][0]}
    return {'panels': panels, 'corners': corners, 'latches': latches,
            'whole_center_edge_gaps_mm': gaps, 'top_level_roots': 16}


def _persistence(before, after):
    if before['top_level_roots'] != after['top_level_roots']:
        raise RuntimeError('Root count changed after reopen')
    for family in ('panels', 'corners', 'latches'):
        if len(before[family]) != len(after[family]):
            raise RuntimeError('Component count changed after reopen')
        for a, b in zip(before[family], after[family]):
            _assert_row(b, a, identity=True)
            for key in ('source_id', 'role', 'side'):
                if a.get(key) != b.get(key):
                    raise RuntimeError('Source correspondence changed')


def execute_latch_showcase(*, context, source, corner_receipt, corner_assets, output):
    """Exactly two cases, basic placement checks, read-only disk-copy source."""
    # This is intentionally before mkdir: unavailable existing ROT means no new files.
    attached = NativePartsAdapter.attach(context)
    source = Path(source).resolve(strict=True)
    if file_sha256(source) != SOURCE_SHA or corner_assets['source_sha256'] != SOURCE_SHA:
        raise ValueError('Pinned Epson disk source mismatch')
    if corner_receipt.get('passed') is not True or corner_receipt['source_sha256_before'] != SOURCE_SHA:
        raise ValueError('Accepted corner A receipt required')
    for asset in corner_assets['roots']:
        if file_sha256(asset['asset_path']) != asset['asset_sha256']:
            raise ValueError('Pinned corner asset changed')
    output = Path(output).resolve()
    output.mkdir(exist_ok=False)
    session = Session(attached, output)
    context_before = attached.provenance()
    results = []
    with cad_writer_lock():
        try:
            snapshot = output/'source_disk_copy.ics'
            exclusive_copy(source, snapshot)
            doc = session.open(snapshot, readonly=True)
            pose = _pose(attached, doc, snapshot)
            if str(doc.FileGUID) != SOURCE_GUID or doc.Modified or not doc.IsReadOnly():
                raise RuntimeError('Read-only source copy identity mismatch')
            source_provenance = pose.provenance()
            utility = doc.QueryInterface(attached.api.IZSceneDocUtility)
            rows, source_rows, exports = [], {}, {}
            for node_id, role, side, name in LATCHES:
                node = utility.GetElementById(node_id).QueryInterface(attached.api.IZElement)
                row = session.guard.run('read-whole-latch-'+str(node_id), lambda: _whole(pose, node))
                if row['native_id'] != node_id or row['kind'] != 'assembly' or row['name'] != name:
                    raise RuntimeError('Pinned whole latch source identity mismatch')
                source_rows[node_id] = row
                rows.append({'id': node_id, 'role': role, 'side': side,
                    'matrix_world_mm': row['matrix_world_mm'], 'local_bounds_mm': row['local_bounds_mm']})
                asset = output/('latch_'+str(node_id)+'.ics')
                session.guard.run('export-whole-latch-'+str(node_id),
                                  lambda: node.QueryInterface(attached.api.IZAssembly).SaveAs(str(asset), False))
                exports[node_id] = {'path': str(asset), 'sha256': file_sha256(asset)}
            if pose.provenance() != source_provenance:
                raise RuntimeError('Read/export changed source copy flags or identity')
            write_receipt_once(output/'fresh_whole_latches.json', {'source': source_provenance,
                'source_sha256': SOURCE_SHA, 'source_disk_relation': 'byte-identical read-only disk copy',
                'rows': rows, 'whole_components': source_rows, 'exports': exports})
            frame = corner_receipt['plan']['binding']['case_frame']['matrix_world_mm']
            minimum = frame[3][:3]
            sizes = ([914, 602, 352], [1100, 720, 410])
            for label, size in zip(('A_914x602x352', 'B_1100x720x410'), sizes):
                print('START '+label, flush=True)
                folder = output/label
                folder.mkdir()
                latch_plan = plan_latch_pairs(rows, minimum, list(sizes[0]), list(size))
                corners = plan_corner_resize(corner_receipt['plan']['binding'], list(size))
                parts = panel_occurrences(list(size), frame)
                exe = build_panel_bridge(folder/'producer')
                request = exe.parent/'request.json'
                panel_path = exe.parent/'panel_case.ics'
                write_receipt_once(request, {'source': str(Path(context).resolve()),
                                            'output': str(panel_path), 'parts': parts})
                bridge_result = exe.parent/'result.json'
                run = session.guard.run('produce-hidden-panels', lambda: subprocess.run(
                    [str(exe), str(request), str(bridge_result)], capture_output=True, text=True,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
                write_receipt_once(exe.parent/'process.json', {'exit_code': run.returncode,
                                  'stdout': run.stdout, 'stderr': run.stderr})
                if run.returncode or not panel_path.is_file():
                    raise RuntimeError('Hidden panel producer failed: '+run.stderr[-2000:])
                cleanup = json.loads((exe.parent/'panel_cleanup.json').read_text(encoding='utf-8'))
                producer = json.loads(bridge_result.read_text(encoding='utf-8'))
                if cleanup.get('passed') is not True or producer.get('passed') is not True:
                    raise RuntimeError('Panel producer or its owned-document cleanup did not pass')
                working = folder/'working.ics'
                exclusive_copy(panel_path, working)
                case = session.open(working)
                case_pose = _pose(attached, case, working)
                top = case_pose.root().QueryInterface(attached.api.IZAssembly)
                corner_map, latch_map = {}, {}
                for expected in corners['assemblies']:
                    asset = next(a for a in corner_assets['roots'] if a['source_id'] == expected['id'])
                    node = session.guard.run('import-corners', lambda: top.AddChildFromExternalFile(
                        asset['asset_path'], False)).QueryInterface(attached.api.IZElement)
                    corner_map[expected['id']] = int(node.Id)
                    session.guard.run('place-corner-container', lambda: _set_matrix(node, expected['matrix_world_mm'], attached.api))
                    for item in (r for r in corners['occurrences'] if r['assembly_id'] == expected['id']):
                        child = case_pose.child_at(node, item['occurrence_path'][-1]).QueryInterface(attached.api.IZElement)
                        session.guard.run('place-whole-corner', lambda: _set_matrix(child, item['matrix_parent_mm'], attached.api))
                        session.guard.run('update-whole-corner', lambda: child.QueryInterface(attached.api.IZPart).Update())
                        session.guard.run('dirty-corner-graphics', lambda: child.SetDirtyFlag(attached.api.Z_DIRTY_GRAPHICS))
                    session.guard.run('update-corner-container', lambda: node.QueryInterface(attached.api.IZAssembly).Update())
                for item in latch_plan['occurrences']:
                    node = session.guard.run('import-whole-latch', lambda: top.AddChildFromExternalFile(
                        exports[item['id']]['path'], False)).QueryInterface(attached.api.IZElement)
                    latch_map[item['id']] = int(node.Id)
                    session.guard.run('place-whole-latch', lambda: _set_matrix(node, item['matrix_world_mm'], attached.api))
                    session.guard.run('update-whole-latch', lambda: node.QueryInterface(attached.api.IZAssembly).Update())
                    session.guard.run('dirty-latch-graphics', lambda: node.SetDirtyFlag(attached.api.Z_DIRTY_GRAPHICS))
                scene = case.QueryInterface(attached.api.IZSceneDoc)
                session.guard.run('update-case', lambda: scene.Update())
                before = session.guard.run('measure-whole-before', lambda: _measure_case(
                    case_pose, corners, corner_map, latch_plan, latch_map, source_rows))
                write_receipt_once(folder/'before_save.json', before)
                final = folder/('POC_zatrzaski_'+label+'.ics')
                session.guard.run('save-case', lambda: scene.SaveAs(str(final), attached.api.Z_LINKS_COPY_ALL, False))
                session.close(case)
                case = session.open(final)
                after = session.guard.run('measure-whole-reopened', lambda: _measure_case(
                    _pose(attached, case, final), corners, corner_map, latch_plan, latch_map, source_rows))
                write_receipt_once(folder/'after_reopen.json', after)
                _persistence(before, after)
                session.close(case)
                archive = folder/'snapshot.ics'
                exclusive_copy(final, archive)
                result = {'passed': True, 'output_path': str(final), 'output_sha256': file_sha256(final),
                    'snapshot_path': str(archive), 'snapshot_sha256': file_sha256(archive),
                    'latch_plan': latch_plan, 'latch_native_ids': latch_map, 'corner_native_ids': corner_map,
                    'whole_center_edge_gaps_mm': after['whole_center_edge_gaps_mm'],
                    'inventory': {'panel_proxies': 10, 'real_corner_components': 8, 'opaque_latch_assemblies': 4},
                    'visual_qa': 'NOT_RUN', 'production_approved': False,
                    'scope': 'Regular ten-panel copy with eight source corners and four complete latch halves; not the full Epson case. Regenerated A/B, no persistent native mates.'}
                write_receipt_once(folder/'receipt.json', result)
                results.append(result)
                print('PASS '+str(final), flush=True)
            if pose.provenance() != source_provenance or file_sha256(snapshot) != SOURCE_SHA:
                raise RuntimeError('Read/export modified source copy')
            session.close(doc)
            if attached.provenance() != context_before or file_sha256(source) != SOURCE_SHA:
                raise RuntimeError('Original/context changed')
        finally:
            session.finish()
    # A successful receipt is written only after own-document cleanup succeeds.
    if file_sha256(source) != SOURCE_SHA:
        raise RuntimeError('Original source hash changed at final gate')
    for path in exports.values():
        if file_sha256(path['path']) != path['sha256']:
            raise RuntimeError('Export hash changed')
    for asset in corner_assets['roots']:
        if file_sha256(asset['asset_path']) != asset['asset_sha256']:
            raise RuntimeError('Corner asset hash changed')
    result = {'passed': True, 'verification': 'whole-component placement', 'cases': results,
        'source_sha256_before': SOURCE_SHA, 'source_sha256_after': file_sha256(source),
        'source_guid': SOURCE_GUID, 'own_documents_closed': True, 'visual_qa': 'NOT_RUN',
        'production_approved': False, 'no_application_launch_or_desktop_activation': True}
    write_receipt_once(output/'acceptance.json', result)
    return result
