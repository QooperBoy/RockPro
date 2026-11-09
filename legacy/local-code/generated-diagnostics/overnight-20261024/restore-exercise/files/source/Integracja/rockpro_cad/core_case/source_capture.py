"""Acquire one saved source revision without promoting catalog approvals.

The original is never opened. An exclusive byte-identical clone is opened in an
existing IronCAD host, inventoried and closed. Native dependencies are lazy.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

from ..cad_lock import cad_writer_lock
from ..parts.native import file_sha256, same_document_path
from .manifest import build_manifest, validate_manifest
from .native import write_receipt_once
from .native_reader import validate_matrix


class SavedSourceSession:
    def __init__(self):
        import comtypes.client
        from python_ironcad import ICAPI
        self.api = ICAPI
        self.app = comtypes.client.GetActiveObject('IronCAD.Application', dynamic=True)
        self.base = self.app.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
        self.document = None

    def open_owned(self, path):
        from .native_reader import NativePoseAdapter
        already_open, document = self.base.OpenFile2(str(path), True, False)
        if already_open:
            raise ValueError('Clone was already open; document ownership refused')
        if not same_document_path(document.Name, path):
            raise ValueError('IronCAD opened a different file')
        self.document = document
        self.path = path
        self.adapter = NativePoseAdapter(None, self.base, document, self.api, path)
        return self.state()

    def state(self):
        return self.adapter.provenance()

    def inspect(self):
        from ..parts.native import inspect_source
        from ..parts.reader import ReadLimits
        from .native_reader import inspect_source_poses
        limits = ReadLimits(max_seconds=180)
        inventory = inspect_source(self.path, limits, adapter_factory=lambda _: self.adapter)
        poses = inspect_source_poses(self.path, limits, adapter_factory=lambda _: self.adapter)
        return inventory, poses

    def close(self):
        if self.document is not None:
            if self.document.Modified:
                # Preserve unexpected changes to our own clone before closing it.
                scene = self.document.QueryInterface(self.api.IZSceneDoc)
                scene.SaveAsCopy(str(self.path.with_name('unexpected_modified_copy.ics')),
                                 self.api.Z_LINKS_COPY_ALL, False)
            self.document.Close()
            self.document = None


def _require_saved(report, state, digest, clone):
    source = report.get('source', {})
    document = report.get('cad_document', {})
    if (report.get('status') == 'failed'
            or source.get('sha256_before') != digest or source.get('sha256_after') != digest
            or source.get('unchanged') is not True
            or not same_document_path(source.get('path', ''), clone)
            or document.get('before') != state or document.get('after') != state):
        raise ValueError('Source identity, hash or live state changed during capture')


def select_source_binding(inventory, poses, *, node_id, occurrence_path, node_name):
    """Select exact IDs from saved evidence, preserving opaque parent mirrors.

    The world frame must remain a proper rotation. This is a source selection,
    not approval of a part, its mount or a mirrored geometry variant.
    """
    if (type(node_id) is not int or node_id <= 0 or not isinstance(node_name,str)
            or not node_name or not isinstance(occurrence_path,list) or not occurrence_path
            or len(occurrence_path)>12 or any(type(i) is not int or i<0 for i in occurrence_path)):
        raise ValueError('Explicit node ID, name and occurrence path are required')
    state = inventory['cad_document']['before']
    source = inventory['source']
    if (inventory['cad_document'].get('disk_equivalence') != 'saved_document'
            or state.get('modified') is not False or not state.get('file_guid')):
        raise ValueError('Selection requires a captured saved source revision')
    for report in (inventory, poses):
        _require_saved(report, state, source['sha256_before'], source['path'])
    rows = [r for r in inventory['rows'] if r['occurrence_path'] == occurrence_path]
    positions = [r for r in poses['rows'] if r['occurrence_path'] == occurrence_path]
    if (len(rows) != 1 or len(positions) != 1 or rows[0].get('errors')
            or any(r.get('id') != node_id or r.get('name') != node_name for r in rows+positions)
            or rows[0].get('kind') != positions[0].get('kind')):
        raise ValueError('Selected occurrence identity or pose is unresolved')
    position = positions[0]
    world = validate_matrix(position['matrix_world_mm'])
    for error in position.get('errors', []):
        if (error.get('field') != 'matrix_parent_mm' or error.get('type') != 'ValueError'
                or error.get('message') != 'improper ICAPI rotation'):
            raise ValueError('Selected occurrence has unresolved native evidence')
        parent = position['matrix_parent_mm_raw']
        validate_matrix(parent, allow_reflection=True)
        try:
            validate_matrix(parent)
        except ValueError:
            pass  # An actual unchanged parent mirror; never rewrite this matrix.
        else:
            raise ValueError('Reported reflection contradicts its raw parent matrix')
    return dict(schema_version=1, source_path=source['path'],
        source_sha256=source['sha256_before'], source_guid=state['file_guid'],
        node_id=node_id, node_name=node_name, expected_world_matrix_mm=world)


def capture_source_revision(source, output_dir, *, expected_sha256, node_id=None,
                            occurrence_path=None, node_name=None, session_factory=None):
    """Produce fresh inventory/poses/draft plus one explicitly selected binding.

    session_factory exists for synthetic tests. No old inventory IDs are silently
    reconciled: the new manifest has its own source-bound identity map.
    """
    source = Path(source).resolve(strict=True)
    output = Path(output_dir).resolve()
    if source.suffix.lower() != '.ics' or not source.is_file():
        raise ValueError('Source must be an existing ICS file')
    if (not isinstance(expected_sha256, str)
            or not re.fullmatch('[0-9a-f]{64}', expected_sha256)
            or file_sha256(source) != expected_sha256):
        raise ValueError('Source SHA256 does not match the explicit revision pin')
    select_node = any(v is not None for v in (node_id, occurrence_path, node_name))
    if select_node and (type(node_id) is not int or node_id <= 0 or not isinstance(node_name, str)
            or not node_name or not isinstance(occurrence_path, list)
            or not occurrence_path or len(occurrence_path) > 12
            or any(type(i) is not int or i < 0 for i in occurrence_path)):
        raise ValueError('Explicit node ID, name and occurrence path are required')
    # Never reuse an operation folder or overwrite its artifacts.
    output.mkdir(exist_ok=False)
    clone = output / 'source_snapshot.ics'
    receipt = dict(schema_version=1, operation='capture_saved_source_revision',
        passed=False, source=str(source), source_sha256=expected_sha256,
        captured_source=str(clone), original_opened=False, production_approved=False,
        mounting_approved=False, owned_document_closed=False)
    try:
        with cad_writer_lock():
            with source.open('rb') as incoming, clone.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            if file_sha256(clone) != expected_sha256:
                raise ValueError('Byte-identical source acquisition failed')
            session = (session_factory or SavedSourceSession)()
            try:
                state = session.open_owned(clone)
                if (state.get('modified') is not False or not state.get('file_guid')
                        or not same_document_path(state.get('document_path', ''), clone)):
                    raise ValueError('Newly opened clone is not a clean saved revision')
                inventory, poses = session.inspect()
                _require_saved(inventory, state, expected_sha256, clone)
                _require_saved(poses, state, expected_sha256, clone)
                if session.state() != state:
                    raise ValueError('Clone live state changed after the readers')
            finally:
                session.close()
                receipt['owned_document_closed'] = True
            if file_sha256(source) != expected_sha256 or file_sha256(clone) != expected_sha256:
                raise ValueError('Original or clone bytes changed during acquisition')

            # Preserve observations even when an old selected ID cannot be bound.
            # These raw reports do not assert a mounting or catalog approval.
            write_receipt_once(output/'raw_inventory.json', inventory)
            write_receipt_once(output/'poses.json', poses)
            receipt['source_capture_passed'] = True

            # Saved equivalence is justified by this operation's exclusive clone
            # acquisition, stable live state and matching source/clone hashes.
            bound = copy.deepcopy(inventory)
            bound['cad_document']['disk_equivalence'] = 'saved_document'

            # Do not guess a role or select another same-named catalog object.
            binding = None
            if select_node:
                rows = [r for r in inventory['rows'] if r['occurrence_path'] == occurrence_path]
                positions = [r for r in poses['rows'] if r['occurrence_path'] == occurrence_path]
                receipt['selected_observations'] = dict(inventory=rows, poses=positions)
                binding = select_source_binding(bound, poses, node_id=node_id,
                    occurrence_path=occurrence_path, node_name=node_name)

            # This evidence comes from our newly opened byte-identical clone, not
            # from a caller merely claiming Modified=false on an arbitrary document.
            inventory_bytes = (json.dumps(bound,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
            inventory_sha = hashlib.sha256(inventory_bytes).hexdigest()
            manifest = build_manifest(bound, inventory_sha256=inventory_sha)
            validation = validate_manifest(manifest, bound).as_dict()
            if not validation['valid']:
                raise ValueError('Captured inventory cannot produce a valid accounting draft')
            with (output/'inventory.json').open('xb') as stream:
                stream.write(inventory_bytes)
            for name, value in [('manifest.json',manifest), ('manifest_validation.json',validation)]:
                write_receipt_once(output/name, value)
            if binding is not None:
                write_receipt_once(output/'selected_binding.json', binding)
            receipt.update(passed=True, captured_source_guid=state['file_guid'],
                captured_source_sha256=expected_sha256, inventory_sha256=inventory_sha,
                accounted_nodes=len(manifest['occurrences']),
                inventory_status=inventory.get('status'), pose_status=poses.get('status'),
                selected_node_id=node_id, selected_occurrence_path=occurrence_path,
                selected_node_name=node_name, disk_equivalence='saved_document',
                runtime_template_compatible=False,
                identity_reconciliation='new_revision_map; prior maps are not silently reused')
    except Exception as exc:
        receipt['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        try:
            receipt['original_unchanged'] = file_sha256(source) == expected_sha256
            receipt['capture_unchanged'] = clone.is_file() and file_sha256(clone) == expected_sha256
        except OSError as exc:
            receipt.update(original_unchanged=False, capture_unchanged=False,
                           final_integrity_error=str(exc))
        late_failure = receipt['passed'] and not (receipt['original_unchanged']
            and receipt['capture_unchanged'] and receipt['owned_document_closed'])
        if late_failure:
            receipt['passed'] = False
        write_receipt_once(output/'capture_receipt.json', receipt)
        if late_failure:
            raise ValueError('Final source integrity or owned-document cleanup failed')
    return receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--node-id', type=int)
    parser.add_argument('--node-name')
    parser.add_argument('--occurrence-path', type=int, nargs='+')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--native', action='store_true', help='Open an owned clone in an existing host')
    args = parser.parse_args(argv)
    artifacts = Path(__file__).resolve().parents[3]/'artifacts'
    if not args.output_dir.resolve().is_relative_to(artifacts.resolve()):
        parser.error('output-dir must be a new folder inside checkout artifacts')
    if not args.native:
        print('PLAN_ONLY: no CAD, copies or output files; add --native to capture the pinned revision')
        return 0
    from contextlib import redirect_stdout
    import sys
    with redirect_stdout(sys.stderr):
        receipt = capture_source_revision(args.source,args.output_dir,
            expected_sha256=args.expected_sha256,node_id=args.node_id,
            occurrence_path=args.occurrence_path,node_name=args.node_name)
    print(json.dumps(receipt,ensure_ascii=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
