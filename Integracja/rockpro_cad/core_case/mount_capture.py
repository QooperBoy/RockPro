"""Fresh H7159 flange witnesses and pair-only native proof on owned copies.

No production promotion, full-case substitution, or legacy receipt rewriting.
Native imports are lazy; the source export is never opened or modified.
"""
import copy
from pathlib import Path
import shutil

from ..cad_lock import cad_writer_lock
from ..parts.native import file_sha256, same_document_path
from .catalog_native import validate_source_binding, close_owned_documents
from .hardware_poc import candidate_datum, plan_hardware_poc, validate_pair
from .native import write_receipt_once


def validate_export(receipt, binding, asset_sha256):
    validate_source_binding(binding)
    if (receipt.get('passed') is not True or receipt.get('production_approved') is not False
            or receipt.get('source_unchanged') is not True
            or receipt.get('source_binding') != binding
            or receipt.get('asset_sha256') != asset_sha256
            or receipt.get('physical_occurrences') != 13):
        raise ValueError('Fresh export must match the exact source binding and asset hash')
    source=receipt.get('source',{})
    if (source.get('disk_equivalence') != 'saved_document'
            or source.get('live_document',{}).get('modified') is not False
            or source.get('live_document',{}).get('file_guid') != binding['source_guid']
            or source.get('sha256_before') != binding['source_sha256']
            or source.get('sha256_after') != binding['source_sha256']):
        raise ValueError('Export must originate in the bound saved revision')
    required=('source_capture','native_catalog_export_import','rigid_move','body_topology_volume','save_reopen')
    if any(receipt.get('stages',{}).get(k) != 'PASS' for k in required):
        raise ValueError('Export validation stages are incomplete')
    return copy.deepcopy(receipt)


def prepare_pair_plans(evidence, binding, expected_asset_sha256, expected_asset_guid):
    validate_source_binding(binding)
    measured=copy.deepcopy(evidence)
    measured['source_world_matrix_mm']=binding['expected_world_matrix_mm']
    datum=candidate_datum(measured,contact_face_id=194,exterior_face_id=353,
        expected_asset_sha256=expected_asset_sha256,expected_guid=expected_asset_guid)
    plans=[dict(id=label,plan=plan_hardware_poc(size,datum)) for label,size in (
        ('A',[900,600,330]),('B',[1100,720,410]),('C',[900,600,330]))]
    if plans[0]['plan'] != plans[2]['plan']:
        raise ValueError('Return pair plan differs')
    return datum,plans


def capture_mount_pair(asset_path, receipt, binding, *, expected_asset_sha256,
                       output_dir, expected_asset_guid=None):
    """Measure only pinned flange faces; three pair-only scenes, no desktop input."""
    from .source_capture import SavedSourceSession
    from .native_reader import NativePoseAdapter, transform_bbox
    from .catalog_native import _signature, compare_body_signatures
    from .hardware_poc_native import _face
    asset=Path(asset_path).resolve(strict=True)
    checked=validate_export(receipt,binding,expected_asset_sha256)
    if file_sha256(asset) != expected_asset_sha256:
        raise ValueError('Asset disk bytes differ from the independent pin')
    output=Path(output_dir).resolve()
    output.mkdir(parents=True,exist_ok=False)
    owned=[]
    with cad_writer_lock():
        session=SavedSourceSession();api=session.api;base=session.base
        active=base.ActiveDoc
        before_context=(str(active.Name),bool(active.Modified)) if active else None
        def clone(path):
            with asset.open('rb') as src,path.open('xb') as dst:shutil.copyfileobj(src,dst)
            if file_sha256(path)!=expected_asset_sha256:raise ValueError('Asset clone hash differs')
        def open_owned(path):
            already,doc=base.OpenFile2(str(path),False,False)
            if already:raise ValueError('Document already open; ownership refused')
            owned.append(doc)
            if not same_document_path(doc.Name,path):raise ValueError('Wrong owned document')
            return doc,NativePoseAdapter(None,base,doc,api,path)
        def close(doc):
            close_owned_documents([doc],api,output);owned.remove(doc)
        def dirty(adapter,node):
            node=node.QueryInterface(api.IZElement)
            kind=adapter.identity(node)['kind']
            if kind in ('scene','assembly'):
                for i in range(adapter.child_count(node)):dirty(adapter,adapter.child_at(node,i))
            node.SetDirtyFlag(api.Z_DIRTY_GRAPHICS)
        def measure(adapter,plan,ids,baseline):
            observed=[]
            utility=adapter.document.QueryInterface(api.IZSceneDocUtility)
            for member in plan['handles']:
                node=utility.GetElementById(ids[member['id']])
                actual=adapter.matrix(node,True)
                if adapter.child_count(node)!=13:raise ValueError('Handle component count changed')
                parts=[]
                for r in baseline:
                    if r['kind']!='part':continue
                    child=node
                    for index in r['occurrence_path']:child=adapter.child_at(child,index)
                    box=adapter.bbox(child,'part')
                    if not box['valid']:raise ValueError('Invalid native component bounds')
                    bounds=box['minimum']+box['maximum']
                    if max(abs(x-y) for x,y in zip(bounds,r['local_bounds_mm']))>.003:
                        raise ValueError('Rigid component dimensions changed')
                    parent=adapter.matrix(child,False)
                    if any(abs(parent[i][j]-r['matrix_parent_mm'][i][j])>(.003 if i==3 and j<3 else 1e-6)
                           for i in range(4) for j in range(4)):
                        raise ValueError('Internal component pose changed')
                    parts.append(dict(path=r['occurrence_path'],bbox_world_mm=transform_bbox(bounds,adapter.matrix(child,True))))
                body=adapter.child_at(node,0)
                contact=_face(adapter,body,194);exterior=_face(adapter,body,353)
                y=-plan['size'][1]/2
                if max(abs(v[1]-y) for v in contact['vertices_world_mm'])>.003:
                    raise ValueError('Contact flange differs from front datum')
                if max(abs(v[1]-(y-1.2)) for v in exterior['vertices_world_mm'])>.003:
                    raise ValueError('Exterior flange sign/thickness differs')
                observed.append(dict(id=member['id'],node_id=int(node.Id),matrix_mm=actual,
                    contact_face=contact,exterior_face=exterior,parts=parts))
            validate_pair(plan,observed)
            return observed
        try:
            clone(output/'asset_input.ics')
            doc,adapter=open_owned(output/'asset_input.ics')
            # Exact byte identity binds the observed GUID to the pinned asset.
            if expected_asset_guid is None:expected_asset_guid=str(doc.FileGUID)
            if doc.Modified or doc.FileGUID!=expected_asset_guid:
                raise ValueError('Asset clone must be saved with pinned GUID')
            root=adapter.child_at(adapter.root(),0).QueryInterface(api.IZElement)
            if adapter.child_count(adapter.root())!=1 or root.Name!='H7159':
                raise ValueError('Exactly one H7159 catalog root required')
            baseline=_signature(adapter,root)
            compare_body_signatures(checked['body_signature'],baseline)
            faces=[]
            for id in (194,353):
                raw=_face(adapter,adapter.child_at(root,0),id)
                faces.append(dict(face_id=id,point_mm=raw['plane_origin_local_mm'],
                    normal=raw['underlying_normal_local'],is_reversed=raw['is_reversed'],
                    vertex_ids=raw['vertex_ids'],vertices_mm=raw['vertices_local_mm']))
            evidence=dict(asset_hash=expected_asset_sha256,asset_signature=baseline,
                document=adapter.provenance(),planar_faces_parallel_local_xz=faces)
            if doc.Modified:raise ValueError('Read-only flange measurement changed the clone')
            datum,plans=prepare_pair_plans(evidence,binding,expected_asset_sha256,expected_asset_guid)
            close(doc)
            write_receipt_once(output/'face_evidence.json',evidence)
            write_receipt_once(output/'datum.json',datum)
            results=[]
            for item in plans:
                path=output/(item['id']+'_pair.ics');clone(path)
                doc,adapter=open_owned(path);scene=doc.QueryInterface(api.IZSceneDoc)
                top=scene.GetTopElement().QueryInterface(api.IZAssembly)
                first=adapter.child_at(adapter.root(),0).QueryInterface(api.IZElement)
                second=top.AddChildFromExternalFile(str(asset),False).QueryInterface(api.IZElement)
                ids={}
                for member,node in zip(item['plan']['handles'],[first,second]):
                    se=node.QueryInterface(api.IZSceneElement);m=se.GetTransformToParent()
                    for i in range(4):
                        for j in range(4):m.SetValue(i,j,member['matrix_mm'][i][j]*(.001 if i==3 and j<3 else 1))
                    se.SetTransformToParent(m);ids[member['id']]=int(node.Id)
                dirty(adapter,adapter.root());scene.Update()
                before=measure(adapter,item['plan'],ids,baseline)
                doc.Save();close(doc)
                doc,adapter=open_owned(path)
                after=measure(adapter,item['plan'],ids,baseline)
                if before!=after:raise ValueError('Pair measurements or IDs changed on reopen')
                close(doc)
                results.append(dict(id=item['id'],size=item['plan']['size'],output_path=str(path),
                    sha256=file_sha256(path),before_save=before,after_reopen=after))
            if [h['matrix_mm'] for h in results[0]['after_reopen']] != [h['matrix_mm'] for h in results[2]['after_reopen']]:
                raise ValueError('Measured return poses differ')
            result=dict(schema_version=1,passed=True,scope='pair_only_native_mount_proof',
                source_binding=binding,export_receipt_asset_sha256=checked['asset_sha256'],
                asset_sha256=expected_asset_sha256,asset_guid=expected_asset_guid,
                physical_parts_per_pair=26,cases=results,return_equivalent=True,
                mounting_approved=False,production_approved=False,
                native_graphics_review='NOT RUN',full_case_and_legacy_sidecar='NOT RUN',
                resize_scope='Independent regeneration from wall datums; no persistent mates')
        finally:
            try:
                close_owned_documents(owned,api,output)
            finally:
                active=base.ActiveDoc
                after_context=(str(active.Name),bool(active.Modified)) if active else None
                if before_context!=after_context:raise ValueError('Active document context changed')
                if file_sha256(asset)!=expected_asset_sha256:raise ValueError('Original asset changed')
        result.update(owned_documents_closed=True,active_context_unchanged=True,asset_unchanged=True)
        write_receipt_once(output/'mount_pair_receipt.json',result)
        return result
