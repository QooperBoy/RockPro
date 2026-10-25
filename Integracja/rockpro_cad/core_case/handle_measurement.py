"""Read bound handles from an already-open document; no launch/open/save/focus."""
import hashlib
import json
from pathlib import Path

from ..cad_lock import cad_writer_lock
from ..parts.native import NativePartsAdapter, file_sha256, same_document_path
from .native_changes import capture_selected_poses


def snapshot_fingerprint(snapshot):
    """Ignore sub-micron COM noise, not a constructor's displacement.

    This is a stale-observation token, not a geometry or production signature.
    Translation precision is 0.001 mm; rotation precision is 1e-9.
    """
    rows=[]
    for row in sorted(snapshot['members'],key=lambda r:r['id']):
        matrix=[[round(float(n),3 if i==3 and j<3 else 9)+0.0
                 for j,n in enumerate(line)] for i,line in enumerate(row['matrix_world_mm'])]
        rows.append(dict(id=row['id'],node_id=row['node_id'],group_id=row['group_id'],matrix=matrix))
    data=dict(binding=snapshot['binding'],file_guid=snapshot['file_guid'],parameters=snapshot['parameters'],members=rows)
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def capture_handle_measurement(source,baseline,mapping,*,adapter_factory=None):
    source=Path(source).resolve(strict=True)
    factory=adapter_factory or NativePartsAdapter.attach
    with cad_writer_lock():
        source_hash=file_sha256(source)
        try:adapter=factory(source)
        except RuntimeError as error:
            if 'not already open in the running object table' in str(error):
                raise ValueError('HANDLE_DOCUMENT_NOT_OPEN: otwórz przypięty plik projektu w IronCAD i ponów pomiar') from error
            raise
        provenance_before=adapter.provenance()
        if not same_document_path(provenance_before['document_path'],source):raise ValueError('HANDLE_DOCUMENT_PATH_MISMATCH')
        if provenance_before['file_guid']!=baseline['file_guid']:raise ValueError('HANDLE_DOCUMENT_GUID_MISMATCH')
        active=adapter.base.ActiveDoc
        context=(str(active.Name),bool(active.Modified)) if active else None
        selection=[dict(id=r['logical_id'],node_id=r['id'],group_id='handles') for r in mapping]
        try:
            first=capture_selected_poses(adapter.document,adapter.api,selection,baseline['binding'])
            second=capture_selected_poses(adapter.document,adapter.api,selection,baseline['binding'])
            provenance_after=adapter.provenance()
            if provenance_before!=provenance_after or snapshot_fingerprint(first)!=snapshot_fingerprint(second):
                raise ValueError('HANDLE_CAD_CHANGED_DURING_MEASUREMENT')
            if file_sha256(source)!=source_hash:raise ValueError('HANDLE_SOURCE_CHANGED_DURING_MEASUREMENT')
            return dict(snapshot=second,source_sha256=source_hash,provenance=provenance_after,
                        snapshot_sha256=snapshot_fingerprint(second),native_read_only=True)
        finally:
            active=adapter.base.ActiveDoc
            after=(str(active.Name),bool(active.Modified)) if active else None
            if after!=context:raise ValueError('HANDLE_ACTIVE_CONTEXT_CHANGED')
