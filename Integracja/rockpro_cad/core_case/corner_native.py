"""Source-bound corner POC, using only documented hidden/background ICAPI.

No UI, activation, foreground setters, visibility setters, or Redraw calls.
Opaque source reflections are retained; requested resize motions are proper.
"""
import copy
import ctypes
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

from ..cad_lock import cad_writer_lock
from ..parts.native import NativePartsAdapter,file_sha256,same_document_path
from .native import write_receipt_once,NativeExecutionError
from .native_reader import NativePoseAdapter,validate_matrix,transform_bbox
from .catalog_native import _signature,compare_body_signatures
from .corner_mount import plan_corner_resize,validate_corner_observation


class BackgroundGuard:
    def __init__(self,state_reader,event_sink):
        self.state_reader=state_reader;self.event_sink=event_sink

    def run(self,label,action):
        before=self.state_reader();self.event_sink(label,'before',before)
        try:return action()
        finally:
            after=self.state_reader();self.event_sink(label,'after',after)
            if before!=after:raise RuntimeError('background active-document/foreground guard changed: '+label)


def panel_occurrences(size,frame,thickness=9.8,lid_height=104.13):
    validate_matrix(frame)
    if any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in (thickness,lid_height)):
        raise ValueError('finite positive numeric panel thickness and lid height required')
    if (not isinstance(size,list) or len(size)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) or v<150 or v>50000 for v in size)):
        raise ValueError('bounded positive case dimensions >=150mm required')
    w,d,h=size;t=thickness;b=h-lid_height
    if b<=2*t or lid_height<=2*t or min(w,d)<=2*t:raise ValueError('case too small for panels')
    shapes=[('base-front',[w,t,b-t],[0,0,t]),('base-rear',[w,t,b-t],[0,d-t,t]),
      ('base-left',[t,d-2*t,b-t],[0,t,t]),('base-right',[t,d-2*t,b-t],[w-t,t,t]),
      ('lid-front',[w,t,lid_height-t],[0,0,b]),('lid-rear',[w,t,lid_height-t],[0,d-t,b]),
      ('lid-left',[t,d-2*t,lid_height-t],[0,t,b]),('lid-right',[t,d-2*t,lid_height-t],[w-t,t,b]),
      ('floor',[w,d,t],[0,0,0]),('roof',[w,d,t],[0,0,h-t])]
    rows=[]
    for name,shape,position in shapes:
        matrix=copy.deepcopy(frame)
        matrix[3]=[frame[3][j]+sum(position[k]*frame[k][j] for k in range(3)) for j in range(3)]+[1]
        rows.append({'id':'panels-'+name+'/1','local_bounds':[[0,0,0],shape],'native_matrix_mm':matrix,'family':'rectangular_panel_proxy'})
    return rows


def native_background_state(base):
    user=ctypes.WinDLL('user32');user.GetForegroundWindow.restype=ctypes.c_void_p
    doc=base.ActiveDoc
    return {'foreground_hwnd':int(user.GetForegroundWindow() or 0),'active_path':str(doc.Name),'active_guid':str(doc.FileGUID),'active_modified':bool(doc.Modified)}


def background_guard(base,folder):
    count=[0]
    def event(label,phase,state):
        if phase=='before':count[0]+=1
        write_receipt_once(Path(folder)/('background-%04d-%s.%s.json'%(count[0],label,phase)),state)
    return BackgroundGuard(lambda:native_background_state(base),event)


def exclusive_copy(source,target):
    with Path(source).open('rb') as src,Path(target).open('xb') as dst:
        shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
    if file_sha256(source)!=file_sha256(target):raise NativeExecutionError('exclusive byte copy differs')


def produce_hidden_panels(context_source,parts,folder):
    """Create measured rectangles at supplied dimensions; never opens visibly."""
    folder=Path(folder).resolve();folder.mkdir(exist_ok=False)
    adapter=NativePartsAdapter.attach(context_source);guard=background_guard(adapter.base,folder)
    before=adapter.provenance();source_hash=file_sha256(context_source)
    from python_ironcad.core import install_dir
    vendor=Path(install_dir)/'ICAPI'/'Samples'/'C#'/'References'/'interop.ICApiIronCAD.dll'
    compiler=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET'/'Framework64'/'v4.0.30319'/'csc.exe'
    bridge=Path(__file__).with_name('CornerSceneBridge.cs');exe=folder/'CornerSceneBridge.exe'
    build=subprocess.run([str(compiler),'/nologo','/target:exe','/platform:x64','/out:'+str(exe),'/reference:'+str(vendor),'/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',str(bridge)],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if build.returncode:raise NativeExecutionError('hidden bridge compile failed: '+build.stdout+build.stderr)
    shutil.copyfile(vendor,folder/vendor.name)
    output=folder/'panel_case.ics';request=folder/'request.json';result=folder/'result.json'
    write_receipt_once(request,{'source':str(Path(context_source).resolve()),'output':str(output),'parts':parts})
    run=guard.run('hidden-panel-producer',lambda:subprocess.run([str(exe),str(request),str(result)],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
    write_receipt_once(folder/'process.json',{'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'bridge_sha256':file_sha256(bridge)})
    if run.returncode or not result.is_file():raise NativeExecutionError('hidden panel bridge failed: '+run.stderr[-2000:])
    receipt=json.loads(result.read_text(encoding='utf-8'))
    if receipt.get('passed') is not True or receipt.get('background_guard') is not True:raise NativeExecutionError('hidden panel bridge did not pass')
    for stage in ('before','after_reopen'):
        rows=receipt[stage]
        if len(rows)!=len(parts) or {r['name'] for r in rows}!={'RP:'+p['id'] for p in parts}:raise NativeExecutionError('panel inventory differs')
        byname={r['name']:r for r in rows}
        for p in parts:
            row=byname['RP:'+p['id']]
            if max(abs(a-b) for a,b in zip(row['local_bounds_mm'],p['local_bounds'][0]+p['local_bounds'][1]))>.003:raise NativeExecutionError('panel geometry mismatch')
            if max(abs(row['matrix_world_mm'][i][j]-p['native_matrix_mm'][i][j]) for i in range(4) for j in range(4))>1e-6:raise NativeExecutionError('panel pose mismatch')
    if adapter.provenance()!=before or file_sha256(context_source)!=source_hash:raise NativeExecutionError('context source changed')
    return {'passed':True,'output_path':str(output),'sha256':file_sha256(output),'bridge_result':receipt}


def _point(v,m):return [sum(v[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)]


def _opaque_box(box,m):
    validate_matrix(m,allow_reflection=True)
    points=[_point(v,m) for v in itertools.product(*zip(box[:3],box[3:]))]
    return [min(v[j] for v in points) for j in range(3)]+[max(v[j] for v in points) for j in range(3)]


def _matrix_close(a,b):
    return all(abs(a[i][j]-b[i][j])<(.003 if i==3 and j<3 else 1e-6) for i in range(4) for j in range(4))


def compare_corner_persistence(before,after,*,source_volumes,semantic_occurrences=False):
    """Every field/type exact except the explicitly located native volume retval.

    The volume gate is the same pinned-source tolerance as body preservation.
    Same-model measurements include all actual IDs/paths. Independent-scene
    return comparison supplies only source-semantic occurrence rows.
    """
    deltas=[]
    def walk(a,b,path):
        allowed=(len(path)==5 and path[:2]==('observation','occurrences') and type(path[2]) is int and path[3:]==('body_signature','volume_m3')) if not semantic_occurrences else (len(path)==3 and type(path[0]) is int and path[1:]==('body_signature','volume_m3'))
        if allowed:
            index=path[0] if semantic_occurrences else path[2]
            rows=before if semantic_occurrences else before['observation']['occurrences']
            source_id=rows[index]['id'];reference=source_volumes[source_id]
            if any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in (a,b,reference)):raise NativeExecutionError('invalid native volume at '+str(path))
            tolerance=max(1e-15,abs(reference)*1e-8);delta=abs(a-b)
            if max(delta,abs(a-reference),abs(b-reference))>tolerance:raise NativeExecutionError('native volume drift at '+str(path))
            if delta:deltas.append({'source_id':source_id,'path':list(path),'before_m3':a,'after_m3':b,'absolute_delta_m3':delta,'source_volume_m3':reference,'tolerance_m3':tolerance})
            return
        if type(a)!=type(b):raise NativeExecutionError('persisted field type changed at '+str(path))
        if isinstance(a,dict):
            if set(a)!=set(b):raise NativeExecutionError('persisted field keys changed at '+str(path))
            for key in a:walk(a[key],b[key],path+(key,))
        elif isinstance(a,list):
            if len(a)!=len(b):raise NativeExecutionError('persisted inventory length changed at '+str(path))
            for index,(left,right) in enumerate(zip(a,b)):walk(left,right,path+(index,))
        elif a!=b:raise NativeExecutionError('persisted non-volume field changed at '+str(path))
    walk(before,after,())
    return {'passed':True,'volume_changes':deltas,'max_volume_delta_m3':max((r['absolute_delta_m3'] for r in deltas),default=0),
      'volume_tolerance':'max(1e-15 m3, abs(pinned source volume)*1e-8)','all_other_fields_and_types_exact':True,'semantic_occurrences_only':semantic_occurrences}


def _vertices(node,api):
    body=node.QueryInterface(api.IZPart).GetBody(True);verts=body.QueryInterface(api.IZBodyVertex)
    ids=sorted(int(i) for i in body.GetVertexIds())
    return {'vertex_ids':ids,'positions_local_mm':[[float(v)*1000 for v in verts.GetPosition(i)] for i in ids]}


def _compare_vertices(before,after):
    if before['vertex_ids']!=after['vertex_ids'] or len(before['positions_local_mm'])!=len(after['positions_local_mm']):raise NativeExecutionError('native body vertex topology changed')
    if max(abs(a-b) for v,w in zip(before['positions_local_mm'],after['positions_local_mm']) for a,b in zip(v,w))>.003:raise NativeExecutionError('native body vertices changed')


def _face(pose,node,fid):
    body=node.QueryInterface(pose.api.IZPart).GetBody(True);faces=body.QueryInterface(pose.api.IZBodyFace);vertices=body.QueryInterface(pose.api.IZBodyVertex)
    rev,p,n=faces.GetPlaneData(fid);ids=[int(i) for i in faces.GetFaceVertexIds(fid)]
    vs=[[float(v)*1000 for v in vertices.GetPosition(i)] for i in ids];m=validate_matrix(pose.matrix(node,True),allow_reflection=True)
    raw=[float(n.X),float(n.Y),float(n.Z)];normal=[v*(-1 if rev else 1) for v in raw]
    return {'face_id':int(fid),'is_reversed':bool(rev),'vertex_ids':ids,'vertices_local_mm':vs,'vertices_world_mm':[_point(v,m) for v in vs],
      'underlying_normal_local':raw,'oriented_normal_local':normal,'oriented_normal_world':[sum(normal[k]*m[k][j] for k in range(3)) for j in range(3)]}


def _set_matrix(node,m,api):
    validate_matrix(m,allow_reflection=True);se=node.QueryInterface(api.IZSceneElement);value=se.GetTransformToParent()
    for i in range(4):
        for j in range(4):value.SetValue(i,j,m[i][j]/1000 if i==3 and j<3 else m[i][j])
    se.SetTransformToParent(value)


def _element_at(pose,path):
    n=pose.root()
    for index in path:n=pose.child_at(n,index)
    return n.QueryInterface(pose.api.IZElement)


def export_corner_assets(*,context_source,source_path,evidence,raw_evidence,contact_registration,folder):
    """Export both exact four-corner source containers without activating them."""
    folder=Path(folder).resolve();folder.mkdir(exist_ok=False)
    context=NativePartsAdapter.attach(context_source);guard=background_guard(context.base,folder)
    source=Path(source_path).resolve(strict=True)
    if file_sha256(source)!=evidence['source']['sha256_before']:raise ValueError('source disk SHA drift')
    doc=guard.run('source-get-existing',lambda:context.base.GetOpenDocByName(str(source)))
    if not same_document_path(doc.Name,source) or str(doc.FileGUID)!=evidence['source']['guid']:raise ValueError('hidden source identity mismatch')
    pose=NativePoseAdapter(context.legacy,context.base,doc,context.api,source);before=pose.provenance()
    raw_byid={r['id']:r for r in raw_evidence['rows'] if r.get('name')=='410429'};contacts={r['id']:r for r in contact_registration['contacts']}
    roots=[];bodies={}
    with cad_writer_lock():
        if before['modified']:raise NativeExecutionError('fresh disk-copy source must be clean')
        utility=doc.QueryInterface(pose.api.IZSceneDocUtility)
        for plane in evidence['case_frame']['panel_planes']:
            node=utility.GetElementById(plane['node_id']).QueryInterface(pose.api.IZElement)
            actual=guard.run('source-panel-face-'+str(plane['node_id']),lambda:_face(pose,node,plane['face_id']))
            if len(actual['vertices_world_mm'])!=len(plane['vertices_world_mm']) or max(abs(a-b) for v,w in zip(actual['vertices_world_mm'],plane['vertices_world_mm']) for a,b in zip(v,w))>1e-6 or max(abs(a-b) for a,b in zip(actual['oriented_normal_world'],plane['normal_world']))>1e-6:
                raise NativeExecutionError('fresh source panel witnesses differ from pinned reference envelope')
        for expected in evidence['assemblies']:
            root=_element_at(pose,expected['occurrence_path'])
            if int(root.Id)!=expected['id'] or str(root.Name)!='410429' or not _matrix_close(pose.matrix(root,True),expected['matrix_world_mm']):raise NativeExecutionError('source corner container drift')
            baseline=guard.run('source-signature-'+str(root.Id),lambda:_signature(pose,root))
            if len(baseline)!=5:raise NativeExecutionError('exactly four source corners per container required')
            for item in (r for r in evidence['occurrences'] if r['assembly_id']==expected['id']):
                n=_element_at(pose,item['occurrence_path']);wanted=raw_byid[item['id']]
                if int(n.Id)!=item['id'] or not _matrix_close(pose.matrix(n,True),item['matrix_world_mm']) or not _matrix_close(pose.matrix(n,False),item['matrix_parent_mm']):raise NativeExecutionError('source raw corner pose drift')
                measured=guard.run('source-body-'+str(n.Id),lambda:_signature(pose,n))
                compare_body_signatures(wanted['body_signature'],measured)
                for face in contacts[item['id']]['local_contact_faces']:
                    actual=guard.run('source-contact-'+str(n.Id)+'-'+str(face['face_id']),lambda:_face(pose,n,face['face_id']))
                    if actual['is_reversed']!=face['is_reversed'] or actual['vertex_ids']!=face['vertex_ids'] or max(abs(a-b) for v,w in zip(actual['vertices_local_mm'],face['vertices_local_mm']) for a,b in zip(v,w))>1e-6:raise NativeExecutionError('fresh native registration face differs')
                bodies[str(item['id'])]={'signature':measured,'vertices':guard.run('source-vertices-'+str(n.Id),lambda:_vertices(n,pose.api))}
            asset=folder/('410429_container_'+str(expected['id'])+'.ics')
            guard.run('export-'+str(root.Id),lambda:root.QueryInterface(pose.api.IZAssembly).SaveAs(str(asset),False))
            roots.append({'source_id':expected['id'],'source_occurrence_path':expected['occurrence_path'],'asset_path':str(asset),'asset_sha256':file_sha256(asset),'signature':baseline})
        if pose.provenance()!=before or file_sha256(source)!=evidence['source']['sha256_before']:raise NativeExecutionError('read/export changed source')
        receipt={'passed':True,'source_path':str(source),'source_sha256':file_sha256(source),'source_guid':str(doc.FileGUID),'source_before':before,'source_after':pose.provenance(),'roots':roots,'bodies':bodies,'visual_qa':'NOT_RUN','background_guard':True}
        write_receipt_once(folder/'assets_receipt.json',receipt)
        return receipt


def _measure_corner_case(pose,plan,root_map,asset_receipt,registration):
    parts=panel_occurrences(plan['target_size_mm'],plan['target_case_frame']['matrix_world_mm']);root=pose.root()
    if pose.child_count(root)!=12:raise NativeExecutionError('expected ten panels plus two exact corner containers')
    top=[pose.child_at(root,i).QueryInterface(pose.api.IZElement) for i in range(pose.child_count(root))]
    panels={str(n.Name)[3:]:n for n in top if str(n.Name).startswith('RP:')}
    if len(panels)!=10 or set(panels)!={p['id'] for p in parts}:raise NativeExecutionError('exact ten-panel inventory failed')
    panel_rows=[]
    for p in parts:
        n=panels[p['id']];m=validate_matrix(pose.matrix(n,True));box=pose.bbox(n,'part')
        if not box['valid'] or not _matrix_close(m,p['native_matrix_mm']) or max(abs(a-b) for a,b in zip(box['minimum']+box['maximum'],p['local_bounds'][0]+p['local_bounds'][1]))>.003:raise NativeExecutionError('actual panel dimensions/pose mismatch')
        panel_rows.append({'native_id':int(n.Id),'native_occurrence_path':[top.index(n)],'name':str(n.Name),'matrix_world_mm':m,'local_bounds_mm':box['minimum']+box['maximum'],'bbox_world_mm':transform_bbox(box['minimum']+box['maximum'],m)})
    w,d,h=plan['target_size_mm'];frame=plan['target_case_frame']['matrix_world_mm']
    plane_specs=[(0,0,'panels-base-left/1'),(0,1,'panels-base-right/1'),(1,0,'panels-base-front/1'),(1,1,'panels-base-rear/1'),(2,0,'panels-floor/1'),(2,1,'panels-roof/1')]
    planes=[]
    for axis,side,name in plane_specs:
        n=panels[name];body=n.QueryInterface(pose.api.IZPart).GetBody(True);matches=[]
        for fid in body.GetFaceIds():
            f=_face(pose,n,fid)
            # This source-bound native POC is measured in an axis-aligned frame.
            coordinate=frame[3][axis]+plan['target_size_mm'][axis]*side
            normal=[(side*2-1)*frame[axis][j] for j in range(3)]
            if max(abs(v[axis]-coordinate) for v in f['vertices_world_mm'])<.003 and max(abs(f['oriented_normal_world'][j]-normal[j]) for j in range(3))<1e-6:matches.append(f)
        if len(matches)!=1:raise NativeExecutionError('actual outer panel reference plane absent/ambiguous')
        f=matches[0];planes.append({'axis':axis,'side':side,'node_id':int(n.Id),'face_id':f['face_id'],'vertices_world_mm':f['vertices_world_mm'],'normal_world':f['oriented_normal_world']})
    observed={'schema_version':1,'units':'mm','case_frame':{'matrix_world_mm':frame,'size_mm':[abs(sum((planes[j*2+1]['vertices_world_mm'][0][k]-planes[j*2]['vertices_world_mm'][0][k])*frame[j][k] for k in range(3))) for j in range(3)],'panel_planes':planes},'assemblies':[],'occurrences':[]}
    native_map=[];contact_rows=[];vertices_rows=[];by_root={r['source_id']:r for r in asset_receipt['roots']};reg={r['id']:r for r in registration['contacts']}
    for expected in plan['assemblies']:
        mapping=root_map[expected['id']];n=_element_at(pose,mapping['native_occurrence_path'])
        if int(n.Id)!=mapping['native_id'] or str(n.Name)!='410429' or pose.child_count(n)!=4:raise NativeExecutionError('copied native container identity changed')
        m=validate_matrix(pose.matrix(n,True),allow_reflection=True)
        observed['assemblies'].append({'id':expected['id'],'occurrence_path':expected['occurrence_path'],'matrix_world_mm':m})
        for item in (r for r in plan['occurrences'] if r['assembly_id']==expected['id']):
            index=item['occurrence_path'][-1];part=pose.child_at(n,index).QueryInterface(pose.api.IZElement)
            actual_world=validate_matrix(pose.matrix(part,True),allow_reflection=True);actual_parent=validate_matrix(pose.matrix(part,False),allow_reflection=True)
            signature=_signature(pose,part);reference=asset_receipt['bodies'][str(item['id'])]
            compare_body_signatures(reference['signature'],signature);vertices=_vertices(part,pose.api);_compare_vertices(reference['vertices'],vertices)
            data=signature[0]
            observed['occurrences'].append({'id':item['id'],'assembly_id':expected['id'],'occurrence_path':item['occurrence_path'],
              'matrix_world_mm':actual_world,'matrix_parent_mm':actual_parent,'local_bounds_mm':data['local_bounds_mm'],'body_signature':{k:data[k] for k in ['volume_m3','faces','edges','vertices','lumps']}})
            raw_parent=[float(v)*1000 for v in part.QueryInterface(pose.api.IZPart).GetBoundingBox(False)]
            bbox=_opaque_box(raw_parent,m);composed=_opaque_box(data['local_bounds_mm'],actual_world)
            if max(abs(a-b) for a,b in zip(bbox,composed))>.003:raise NativeExecutionError('native parent bbox composition drift')
            native_map.append({'source_id':item['id'],'source_occurrence_path':item['occurrence_path'],'source_assembly_id':expected['id'],'native_id':int(part.Id),
              'native_assembly_id':int(n.Id),'native_occurrence_path':mapping['native_occurrence_path']+[index],'name':str(part.Name),'bbox_parent_raw_mm':raw_parent,'bbox_parent_world_matrix_mm':m,'bbox_world_mm':bbox})
            vertices_rows.append({'source_id':item['id'],'native_id':int(part.Id),'vertices':vertices})
            for witness in reg[item['id']]['local_contact_faces']:
                f=_face(pose,part,witness['face_id']);normal=f['oriented_normal_world'];axis=max(range(3),key=lambda j:abs(normal[j]));side=item['slot'][axis]
                outer=next(p for p in planes if p['axis']==axis and p['side']==side)
                residual=max(abs(sum((v[j]-outer['vertices_world_mm'][0][j])*outer['normal_world'][j] for j in range(3))) for v in f['vertices_world_mm'])
                if residual>.003 or abs(sum(normal[j]*outer['normal_world'][j] for j in range(3))+1)>1e-6:raise NativeExecutionError('native corner contact face is off/against wrong panel')
                contact_rows.append({'source_id':item['id'],'native_id':int(part.Id),'axis':axis,'side':side,'panel_native_id':outer['node_id'],'panel_face_id':outer['face_id'],'plane_residual_mm':residual,'face':f})
    observed['occurrences'].sort(key=lambda x:next(i for i,r in enumerate(plan['occurrences']) if r['id']==x['id']))
    validate_corner_observation(plan,observed)
    if len(native_map)!=8 or len({r['native_id'] for r in native_map})!=8 or len(contact_rows)!=24:raise NativeExecutionError('exact native eight-corner/contact inventory failed')
    return {'passed':True,'physical_parts':18,'real_corner_parts':8,'proxy_panel_parts':10,'observation':observed,'panels':panel_rows,'native_source_mapping':native_map,'contact_witnesses':contact_rows,'native_vertices':vertices_rows}


def execute_corner_case(plan,*,context_source,assets,registration,output_dir,operation_id):
    if plan!=plan_corner_resize(plan['binding'],plan['target_size_mm']):raise ValueError('corner plan drift')
    if not isinstance(operation_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}',operation_id):raise ValueError('bounded operation ID required')
    frame=plan['target_case_frame']['matrix_world_mm']
    if any(abs(frame[i][j]-(1 if i==j else 0))>1e-6 for i in range(3) for j in range(3)):raise ValueError('native POC restricted to measured axis-aligned Epson reference frame')
    source=Path(assets['source_path']).resolve(strict=True)
    if file_sha256(source)!=assets['source_sha256'] or plan['binding']['source']['sha256_before']!=assets['source_sha256']:raise ValueError('corner source SHA drift')
    folder=Path(output_dir).resolve()/operation_id;folder.mkdir(exist_ok=False)
    context=NativePartsAdapter.attach(context_source);guard=background_guard(context.base,folder)
    source_doc=guard.run('source-get-existing',lambda:context.base.GetOpenDocByName(str(source)));source_adapter=NativePartsAdapter(context.legacy,context.base,source_doc,context.api,source)
    before_source=source_adapter.provenance()
    if before_source['file_guid']!=assets['source_guid']:raise ValueError('source GUID drift')
    with cad_writer_lock():
        try:
            panels=produce_hidden_panels(context_source,panel_occurrences(plan['target_size_mm'],plan['target_case_frame']['matrix_world_mm']),folder/'panels')
            working=folder/'corner_working.ics'
            exclusive_copy(panels['output_path'],working)
            already,doc=guard.run('open-owned-working-hidden',lambda:context.base.OpenFile2(str(working),False,False))
            if already or not same_document_path(doc.Name,working):raise NativeExecutionError('new hidden working ownership mismatch')
            scene=doc.QueryInterface(context.api.IZSceneDoc);pose=NativePoseAdapter(context.legacy,context.base,doc,context.api,working)
            top=pose.root().QueryInterface(context.api.IZAssembly);root_map={}
            for expected in plan['assemblies']:
                asset=next(r for r in assets['roots'] if r['source_id']==expected['id'])
                if file_sha256(asset['asset_path'])!=asset['asset_sha256']:raise NativeExecutionError('corner asset changed')
                n=guard.run('import-'+str(expected['id']),lambda:top.AddChildFromExternalFile(asset['asset_path'],False)).QueryInterface(context.api.IZElement)
                compare_body_signatures(asset['signature'],_signature(pose,n))
                path=[pose.child_count(pose.root())-1];root_map[expected['id']]={'native_id':int(n.Id),'native_occurrence_path':path}
                guard.run('source-container-frame-'+str(expected['id']),lambda:_set_matrix(n,expected['matrix_world_mm'],context.api))
                for item in (r for r in plan['occurrences'] if r['assembly_id']==expected['id']):
                    part=pose.child_at(n,item['occurrence_path'][-1]).QueryInterface(context.api.IZElement)
                    guard.run('corner-parent-frame-'+str(item['id']),lambda:_set_matrix(part,item['matrix_parent_mm'],context.api))
                    guard.run('corner-update-'+str(item['id']),lambda:part.QueryInterface(context.api.IZPart).Update())
                    guard.run('corner-graphics-dirty-'+str(item['id']),lambda:part.SetDirtyFlag(context.api.Z_DIRTY_GRAPHICS))
                guard.run('container-update-'+str(expected['id']),lambda:n.QueryInterface(context.api.IZAssembly).Update())
                guard.run('container-graphics-dirty-'+str(expected['id']),lambda:n.SetDirtyFlag(context.api.Z_DIRTY_GRAPHICS))
            guard.run('scene-graphics-dirty',lambda:pose.root().QueryInterface(context.api.IZElement).SetDirtyFlag(context.api.Z_DIRTY_GRAPHICS))
            guard.run('scene-update',lambda:scene.Update())
            before=guard.run('measure-before-save',lambda:_measure_corner_case(pose,plan,root_map,assets,registration))
            write_receipt_once(folder/'measurement_before_save.json',before)
            output=folder/('POC_410429_'+operation_id+'.ics')
            guard.run('save-output',lambda:scene.SaveAs(str(output),context.api.Z_LINKS_COPY_ALL,False))
            if doc.Modified or not same_document_path(doc.Name,output):raise NativeExecutionError('corner output save not clean')
            guard.run('close-owned-clean',lambda:doc.Close())
            already,doc=guard.run('reopen-output-hidden',lambda:context.base.OpenFile2(str(output),False,False))
            if already or not same_document_path(doc.Name,output):raise NativeExecutionError('corner output reopen ownership mismatch')
            pose=NativePoseAdapter(context.legacy,context.base,doc,context.api,output)
            after=guard.run('measure-after-reopen',lambda:_measure_corner_case(pose,plan,root_map,assets,registration))
            write_receipt_once(folder/'measurement_after_reopen.json',after)
            persistence=compare_corner_persistence(before,after,source_volumes={r['id']:r['body_signature']['volume_m3'] for r in plan['occurrences']})
            write_receipt_once(folder/'persistence_comparison.json',persistence)
            snapshot=folder/'snapshot.ics';exclusive_copy(output,snapshot)
            if before_source!=source_adapter.provenance() or file_sha256(source)!=assets['source_sha256']:raise NativeExecutionError('corner source changed')
            receipt={'passed':True,'operation_id':operation_id,'plan':plan,'source_path':str(source),'source_sha256_before':assets['source_sha256'],'source_sha256_after':file_sha256(source),
              'source_before':before_source,'source_after':source_adapter.provenance(),'output_path':str(output),'output_sha256':file_sha256(output),'snapshot_path':str(snapshot),'snapshot_sha256':file_sha256(snapshot),
              'assets':assets,'panel_producer':panels,'before_save':before,'after_reopen':after,'persistence_comparison':persistence,'background_guard_unchanged':True,'visual_qa':'NOT_RUN',
              'mounting_approved':False,'production_approved':False,'limitations':['Eight exact source corner variants; opaque source reflections retained, requested motions translation-only.','Ten newly generated rectangular panel proxies, not original plywood geometry.','Candidate registration; no fasteners, collision, manufacturing or strength approval.','No UI/activation/Redraw or visual review; hidden scene UpdateGraphics unsupported.','Resize regenerates a new scene from dimensions and anchor equations; no persistent native mates.']}
            write_receipt_once(folder/'corner_native_receipt.json',receipt);return receipt
        finally:
            if before_source!=source_adapter.provenance() or file_sha256(source)!=assets['source_sha256']:raise NativeExecutionError('corner source identity/hash/Modified changed')
