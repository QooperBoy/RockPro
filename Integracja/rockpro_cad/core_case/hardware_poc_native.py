"""Copy-only, source-pinned native execution for the narrow H7159 POC."""
import itertools
import math
import os
import shutil
from pathlib import Path
import re

from ..cad_lock import cad_writer_lock
from ..parts.native import file_sha256, same_document_path
from .catalog_native import _signature, compare_body_signatures
from .hardware_poc import plan_hardware_poc, point_at, validate_pair
from .native import (execute_plan, IronCADPrototypeDriver, NativeExecutionError,
                     preflight_plan, compare_measurements, write_receipt_once)
from .native_reader import NativePoseAdapter, validate_matrix, transform_bbox


def _product(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _flush_graphics(adapter,scene):
    """ICAPI placement setters leave stale serialized render nodes without this.

    Geometry is unchanged: invalidate graphics only, update descendants first,
    then redraw. Acceptance still measures every body before and after reopen.
    """
    def walk(raw):
        node=raw.QueryInterface(adapter.api.IZElement);kind=adapter.identity(node)['kind']
        if kind in ('scene','assembly'):
            for i in range(adapter.child_count(node)):walk(adapter.child_at(node,i))
            if kind=='assembly':node.QueryInterface(adapter.api.IZAssembly).Update()
        elif kind=='part':node.QueryInterface(adapter.api.IZPart).Update()
        node.SetDirtyFlag(adapter.api.Z_DIRTY_GRAPHICS)
    walk(adapter.root());scene.Update();scene.UpdateGraphics(0);scene.Redraw()


def _direct_parent_box(node,api):
    # GetBoundingBox(False) includes this part's transform, but not ancestor
    # assembly transforms. Nested parts therefore return parent-frame bounds.
    values=[float(v)*1000 for v in node.QueryInterface(api.IZPart).GetBoundingBox(False)]
    if len(values)!=6 or any(not math.isfinite(v) for v in values) or any(values[j+3]<=values[j] for j in range(3)):
        raise NativeExecutionError('invalid direct native parent bbox')
    return values


def _face(adapter,node,face_id):
    body=node.QueryInterface(adapter.api.IZPart).GetBody(True)
    faces=body.QueryInterface(adapter.api.IZBodyFace)
    vertices=body.QueryInterface(adapter.api.IZBodyVertex)
    reversed_,p,n=faces.GetPlaneData(face_id)
    ids=list(faces.GetFaceVertexIds(face_id))
    raw=[[float(v)*1000 for v in vertices.GetPosition(i)] for i in ids]
    matrix=validate_matrix(adapter.matrix(node,True))
    underlying=[float(n.X),float(n.Y),float(n.Z)]
    oriented=[v*(-1 if reversed_ else 1) for v in underlying]
    return {'face_id':face_id,'is_reversed':bool(reversed_),'plane_origin_local_mm':[float(p.X)*1000,float(p.Y)*1000,float(p.Z)*1000],
      'underlying_normal_local':underlying,'oriented_normal_local':oriented,
      'oriented_normal_world':[sum(oriented[k]*matrix[k][j] for k in range(3)) for j in range(3)],
      'vertex_ids':ids,'vertices_local_mm':raw,'vertices_world_mm':[point_at(v,matrix) for v in raw]}


def _native_plane(adapter,node,axis,coordinate):
    body=node.QueryInterface(adapter.api.IZPart).GetBody(True)
    candidates=[]
    for face_id in body.GetFaceIds():
        face=_face(adapter,node,face_id)
        if len(face['vertices_world_mm'])>=3 and max(abs(v[axis]-coordinate) for v in face['vertices_world_mm'])<.003:
            candidates.append(face)
    if len(candidates)!=1:raise NativeExecutionError('missing/ambiguous native panel reference face')
    return candidates[0]


def _measure(adapter,plan,handle_ids,baseline):
    top=adapter.root();rows=[adapter.child_at(top,i).QueryInterface(adapter.api.IZElement) for i in range(adapter.child_count(top))]
    if len(rows)!=13:raise NativeExecutionError('expected exactly 11 proxy parts and 2 catalog assemblies')
    proxies={str(n.Name)[3:]:n for n in rows if str(n.Name).startswith('RP:')}
    expected=preflight_plan(plan['proxy_plan'])
    if set(proxies)!={p['id'] for p in expected}:raise NativeExecutionError('proxy inventory mismatch')
    measurements=[]
    for id_,node in proxies.items():
        matrix=validate_matrix(adapter.matrix(node,True));box=adapter.bbox(node,'part')
        if not box['valid']:raise NativeExecutionError('invalid proxy native geometry')
        transformed=transform_bbox(box['minimum']+box['maximum'],matrix);direct=_direct_parent_box(node,adapter.api)
        if max(abs(a-b) for a,b in zip(direct,transformed))>.003:raise NativeExecutionError('proxy direct native world bbox disagrees with measured frame')
        finish=node.QueryInterface(adapter.api.IZPart).SurfaceFinish
        color=int(finish.Color)
        if color!=(0xD09024 if id_=='product/1' else 0x9CBADD):raise NativeExecutionError('proxy presentation color did not persist')
        measurements.append({'occurrence_id':id_,'cad_node_id':int(node.Id),'matrix_world_mm':matrix,'bbox_world_mm':direct,'transformed_local_bbox_world_mm':transformed,'surface_color_colorref':color,'surface_transparency_native':float(finish.Transparency)})
    proxy_checks=compare_measurements(expected,measurements)
    by_id={int(n.Id):n for n in rows}
    handles=[];all_parts=[]
    for planned in plan['handles']:
        root=by_id[handle_ids[planned['id']]]
        signature=_signature(adapter,root);compare_body_signatures(baseline,signature)
        root_matrix=validate_matrix(adapter.matrix(root,True))
        world_by_path={():root_matrix};nodes_by_path={():root};parts=[]
        for row in signature[1:]:
            path=tuple(row['occurrence_path']);parent=path[:-1]
            node=adapter.child_at(nodes_by_path[parent],path[-1]).QueryInterface(adapter.api.IZElement);nodes_by_path[path]=node
            expected_world=_product(row['matrix_parent_mm'],world_by_path[parent]);world_by_path[path]=expected_world
            actual=validate_matrix(adapter.matrix(node,True))
            position_error=max(abs(actual[3][j]-expected_world[3][j]) for j in range(3))
            rotation_error=max(abs(actual[i][j]-expected_world[i][j]) for i in range(3) for j in range(3))
            if position_error>.003 or rotation_error>1e-6:raise NativeExecutionError('catalog subpart world pose changed')
            if row['kind']=='part':
                box=adapter.bbox(node,'part')
                if not box['valid']:raise NativeExecutionError('catalog body bbox unavailable')
                observed_box=transform_bbox(box['minimum']+box['maximum'],actual)
                parent_box=_direct_parent_box(node,adapter.api)
                direct_box=transform_bbox(parent_box,world_by_path[parent])
                if max(abs(a-b) for a,b in zip(direct_box,observed_box))>.003:raise NativeExecutionError('catalog direct native world bbox disagrees with measured frame')
                wanted_box=transform_bbox(row['local_bounds_mm'],expected_world)
                bbox_error=max(abs(a-b) for a,b in zip(observed_box,wanted_box))
                if bbox_error>.003:raise NativeExecutionError('catalog body world bounds changed')
                parts.append({'occurrence_path':list(path),'node_id':int(node.Id),'matrix_world_mm':actual,'expected_matrix_world_mm':expected_world,
                    'bbox_world_mm':direct_box,'native_bbox_parent_mm':parent_box,'bbox_parent_matrix_world_mm':world_by_path[parent],
                    'transformed_local_bbox_world_mm':observed_box,'max_pose_error_mm':position_error,'max_rotation_component_error':rotation_error,'max_bbox_error_mm':bbox_error})
        if len(parts)!=13:raise NativeExecutionError('each H7159 must retain exactly 13 native parts')
        contact=_face(adapter,nodes_by_path[(0,)],plan['datum']['contact_face']['face_id'])
        exterior=_face(adapter,nodes_by_path[(0,)],plan['datum']['exterior_face']['face_id'])
        world_vertices=contact['vertices_world_mm'];front_y=-plan['size'][1]/2
        if max(abs(v[1]-front_y) for v in world_vertices)>.003:raise NativeExecutionError('flange not on actual front wall plane')
        if max(abs(v[1]-(front_y-1.2)) for v in exterior['vertices_world_mm'])>.003:raise NativeExecutionError('exterior flange side/thickness drift')
        if max(abs(contact['oriented_normal_world'][j]-[0,1,0][j]) for j in range(3))>1e-6:raise NativeExecutionError('contact face normal must oppose wall outward')
        outward=[sum(plan['datum']['outward'][k]*root_matrix[k][j] for k in range(3)) for j in range(3)]
        up=[sum(plan['datum']['up'][k]*root_matrix[k][j] for k in range(3)) for j in range(3)]
        if max(abs(outward[j]-[0,-1,0][j]) for j in range(3))>1e-6 or max(abs(up[j]-[0,0,1][j]) for j in range(3))>1e-6:
            raise NativeExecutionError('source-preserving up/outward mount signs differ')
        margins={'left':min(v[0] for v in world_vertices)+plan['size'][0]/2,'right':plan['size'][0]/2-max(v[0] for v in world_vertices),
          'bottom':min(v[2] for v in world_vertices)-plan['thickness'],'seam':plan['base_height']-max(v[2] for v in world_vertices)}
        if min(margins.values())<25-.003:raise NativeExecutionError('measured flange edge/seam margin too small')
        handles.append({'id':planned['id'],'node_id':int(root.Id),'matrix_mm':root_matrix,'body_signature':signature,'parts':parts,
            'contact_face':contact,'exterior_face':exterior,'edge_margins_mm':margins,'mount_outward_world':outward,'source_up_world':up})
        all_parts+=parts
    validate_pair(plan,handles)
    wall=_native_plane(adapter,proxies['panels-base-front/1'],1,-plan['size'][1]/2)
    if max(abs(wall['oriented_normal_world'][j]-[0,-1,0][j]) for j in range(3))>1e-6:raise NativeExecutionError('native wall outward differs from plan')
    length,depth,height=plan['size'];t=plan['thickness']
    references=[('panels-base-left/1',0,-length/2+t),('panels-base-right/1',0,length/2-t),
      ('panels-base-front/1',1,-depth/2+t),('panels-base-rear/1',1,depth/2-t),('panels-floor/1',2,t),('panels-roof/1',2,height-t)]
    inner=[{'panel':name,'axis':axis,'coordinate_mm':coordinate,'face':_native_plane(adapter,proxies[name],axis,coordinate)} for name,axis,coordinate in references]
    device=next(r for r in measurements if r['occurrence_id']=='product/1')
    corners=[point_at(list(p),device['matrix_world_mm']) for p in itertools.product(*[[-v/2,v/2] for v in plan['device']['shape']])]
    clearance={'left':min(v[0] for v in corners)-inner[0]['coordinate_mm'],'right':inner[1]['coordinate_mm']-max(v[0] for v in corners),
      'front':min(v[1] for v in corners)-inner[2]['coordinate_mm'],'rear':inner[3]['coordinate_mm']-max(v[1] for v in corners),
      'floor':min(v[2] for v in corners)-inner[4]['coordinate_mm'],'roof':inner[5]['coordinate_mm']-max(v[2] for v in corners)}
    if min(clearance[k] for k in ['left','right','front','rear'])<20-.003 or abs(clearance['floor'])>.003 or clearance['roof']<20-.003:
        raise NativeExecutionError('native single-product clearance or floor anchor failed')
    if len({r['node_id'] for r in all_parts})!=26:raise NativeExecutionError('duplicate/missing catalog native node IDs')
    hardware_clearance=[];device_box=device['bbox_world_mm']
    for row in all_parts:
        box=row['bbox_world_mm']
        gap=max(max(box[j]-device_box[j+3],device_box[j]-box[j+3]) for j in range(3))
        if gap<plan['device']['minimum_hardware_aabb_separation_mm']-.003:raise NativeExecutionError('product/real-hardware AABB separation below declared 20mm')
        hardware_clearance.append({'native_node_id':row['node_id'],'conservative_axis_separation_mm':gap})
    return {'passed':True,'physical_parts':37,'proxy_parts':11,'real_catalog_parts':26,'catalog_assemblies':2,'proxy_measurements':measurements,'proxy_checks':proxy_checks,
       'handles':handles,'front_outer_face':wall,'inner_panel_faces':inner,'device_corners_mm':corners,'device_clearance_mm':clearance,'product_hardware_separation':hardware_clearance}


def execute_hardware_poc(plan, *, source, asset_path, asset_evidence, output_dir, operation_id):
    """Create a new independently regenerated case; preserve pinned source+asset."""
    if not re.fullmatch('[A-Za-z0-9_-]{1,80}',operation_id):raise ValueError('invalid operation ID')
    if plan!=plan_hardware_poc(plan['size'],plan['datum']):raise ValueError('POC plan drifted from deterministic construction')
    asset=Path(asset_path).resolve(strict=True)
    if file_sha256(asset)!=plan['datum']['asset_sha256'] or file_sha256(asset)!=asset_evidence['asset_hash']:raise ValueError('asset disk hash drift')
    destination=Path(output_dir).resolve(strict=True)/operation_id
    with cad_writer_lock():
        guard=IronCADPrototypeDriver(source);asset_guard=IronCADPrototypeDriver(asset)
        if asset_guard.before['file_guid']!=plan['datum']['asset_guid']:raise ValueError('asset GUID drift')
        source_root=asset_guard.adapter.child_at(asset_guard.adapter.root(),0)
        source_pose=NativePoseAdapter(asset_guard.adapter.legacy,asset_guard.base,asset_guard.adapter.document,asset_guard.api,asset)
        baseline=_signature(source_pose,source_root)
        compare_body_signatures(asset_evidence['asset_signature'],baseline)
        if sum(r['kind']=='part' for r in baseline)!=13:raise ValueError('expected validated thirteen-part H7159 asset')
        source_body=source_pose.child_at(source_root,0)
        native_datum=[]
        for label in ['contact_face','exterior_face']:
            expected_face=plan['datum'][label]
            actual_face=_face(source_pose,source_body,expected_face['face_id'])
            if actual_face['is_reversed']!=expected_face['is_reversed'] or actual_face['vertex_ids']!=expected_face['vertex_ids']:
                raise ValueError('native asset flange topology differs from pinned datum')
            for left,right in [(actual_face['vertices_local_mm'],expected_face['vertices_mm']),
                  ([actual_face['plane_origin_local_mm']],[expected_face['point_mm']]),
                  ([actual_face['underlying_normal_local']],[expected_face['normal']])]:
                if len(left)!=len(right) or max(abs(a-b) for v,w in zip(left,right) for a,b in zip(v,w))>1e-6:
                    raise ValueError('fresh native flange witness differs from pinned datum')
            native_datum.append(actual_face)
        destination.mkdir(exist_ok=False)
        try:
            proxy_receipt=execute_plan(plan['proxy_plan'],output_dir=destination,source=source,operation_id='panel_stage')
            scene_doc=guard.base.GetOpenDocByName(proxy_receipt['output_path'])
            scene=scene_doc.QueryInterface(guard.api.IZSceneDoc)
            working=destination/'working.ics';scene.SaveAsCopy(str(working),guard.api.Z_LINKS_COPY_ALL,False)
            document=guard.base.OpenFile(str(working),False)
            if not same_document_path(document.Name,working):raise NativeExecutionError('wrong working copy opened')
            scene=document.QueryInterface(guard.api.IZSceneDoc);top=scene.GetTopElement().QueryInterface(guard.api.IZAssembly)
            pose=NativePoseAdapter(guard.adapter.legacy,guard.base,document,guard.api,working)
            handle_ids={}
            for member in plan['handles']:
                imported=top.AddChildFromExternalFile(str(asset),False)
                compare_body_signatures(baseline,_signature(pose,imported))
                se=imported.QueryInterface(guard.api.IZSceneElement);matrix=se.GetTransformToParent()
                for i in range(4):
                    for j in range(4):matrix.SetValue(i,j,member['matrix_mm'][i][j]/1000 if i==3 and j<3 else member['matrix_mm'][i][j])
                se.SetTransformToParent(matrix);handle_ids[member['id']]=int(imported.Id)
            # Presentation only: wood color and blue product; real hardware untouched.
            for i in range(pose.child_count(pose.root())):
                node=pose.child_at(pose.root(),i).QueryInterface(guard.api.IZElement)
                if str(node.Name).startswith('RP:'):
                    finish=node.QueryInterface(guard.api.IZPart).SurfaceFinish
                    if str(node.Name)=='RP:product/1':finish.Color=0xD09024
                    else:finish.Color=0x9CBADD
            _flush_graphics(pose,scene);before=_measure(pose,plan,handle_ids,baseline)
            output=destination/'H7159_case_poc.ics';scene.SaveAs(str(output),guard.api.Z_LINKS_COPY_ALL,False)
            if document.Modified or not same_document_path(document.Name,output):raise NativeExecutionError('POC save failed')
            document.Close();document=guard.base.OpenFile(str(output),False)
            if not same_document_path(document.Name,output):raise NativeExecutionError('POC reopen mismatch')
            pose=NativePoseAdapter(guard.adapter.legacy,guard.base,document,guard.api,output)
            after=_measure(pose,plan,handle_ids,baseline)
            if [r['cad_node_id'] for r in before['proxy_measurements']]!=[r['cad_node_id'] for r in after['proxy_measurements']]:raise NativeExecutionError('proxy stable IDs changed on reopen')
            if [[r['node_id'] for r in h['parts']] for h in before['handles']]!=[[r['node_id'] for r in h['parts']] for h in after['handles']]:raise NativeExecutionError('catalog stable IDs changed on reopen')
            snapshot=destination/'snapshot.ics'
            with output.open('rb') as original,snapshot.open('xb') as archive:
                shutil.copyfileobj(original,archive);archive.flush();os.fsync(archive.fileno())
            if file_sha256(snapshot)!=file_sha256(output):raise NativeExecutionError('exclusive archive differs from validated working output')
            receipt={'passed':True,'schema_version':1,'operation_id':operation_id,'plan':plan,'source_path':str(guard.source),'source_sha256_before':guard.before_hash,'source_sha256_after':file_sha256(guard.source),
              'source_document_before':guard.before,'source_document_after':guard.adapter.provenance(),'asset_path':str(asset),'asset_sha256':file_sha256(asset),'asset_document_before':asset_guard.before,
              'fresh_native_asset_datum':native_datum,
              'asset_document_after':asset_guard.adapter.provenance(),
              'output_path':str(output),'output_sha256':file_sha256(output),'panel_stage_receipt':proxy_receipt,'source_body_signature':baseline,'before_save':before,'after_reopen':after,
              'snapshot_path':str(snapshot),'snapshot_sha256':file_sha256(snapshot),
              'graphics_update_sequence':['recursive part.Update/assembly.Update','each element.SetDirtyFlag(Z_DIRTY_GRAPHICS)','scene.Update','scene.UpdateGraphics(0)','scene.Redraw'],
              'production_approved':False,'mounting_approved':False,'limitations':['Native export/import and rigid placement POC only.','Recessed handle dish intersects uncut plywood; cutouts/fasteners/collision/strength unresolved.','Resize regenerates independent native scene from anchors; no persistent native assembly mates.','One blue rectangular product proxy, ten rectangular panel proxies; only two handles reuse exact source geometry.']}
            guard.assert_source_unchanged();asset_guard.assert_source_unchanged()
            write_receipt_once(destination/'hardware_poc_receipt.json',receipt)
            return receipt
        finally:
            guard.assert_source_unchanged();asset_guard.assert_source_unchanged()
