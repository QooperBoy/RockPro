"""Pinned full-case v3 extension: rigid hinges/casters/dishes, two support pads."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.parts.native import file_sha256,same_document_path
from rockpro_cad.core_case.profile_rules import expression,value
from rockpro_cad.core_case.transport_rules import make_rules,validate_transport_values
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.mcp.lid_policy import PLYWOOD_COLORREF,validate_lid_height

def execute(case,previous,assets,panel_template,output,expected_sha256,lid_height_mm=None):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as A
    from rockpro_cad.cad_lock import cad_writer_lock
    from rockpro_cad.core_case.catalog_native import close_owned_documents
    from rockpro_cad.core_case.native_reader import NativePoseAdapter
    from rockpro_cad.core_case.hardware_poc_native import _face
    case=Path(case).resolve(strict=True);output=Path(output).resolve();panel_template=Path(panel_template).resolve(strict=True)
    if previous.get('passed') is not True or previous.get('contract')!='full_case_profiles_v2':raise ValueError('Pinned v2 receipt required')
    if file_sha256(case)!=expected_sha256 or previous['result_sha256']!=expected_sha256:raise ValueError('Case hash/receipt mismatch')
    catalog={r['alias']:r for r in assets['rows']};rows=make_rules(catalog)
    for a in catalog.values():
        if file_sha256(Path(a['path']))!=a['sha256']:raise ValueError('Asset hash changed')
    values=dict(previous['parameters_mm'])
    if lid_height_mm is not None:
        total=values['RP_BaseHeight']+values['RP_LidHeight']
        values['RP_LidHeight']=lid_height_mm;values['RP_BaseHeight']=total-lid_height_mm
    hinge_top=catalog['hinge_lid']['export_signature'][0]['bounds_m'][5]*1000
    hinge_minimum=hinge_top+1.01+(values['RP_JointGap']-8.63)/2+values['RP_Thickness']+2
    minimum=validate_lid_height(values['RP_LidHeight'],[hinge_minimum],values['RP_BaseHeight'])
    validate_transport_values(values);template_sha=file_sha256(panel_template)
    report=dict(schema_version=3,contract='full_case_transport_v3',parameters_mm=values,
        source_case=str(case),source_case_sha256=expected_sha256,source_catalog=assets,
        panel_template_sha256=template_sha,members=rows,checks=[],production_approved=False,
        wheel_sku=None,stacking_fit_approved=False,native_graphics_review='NOT RUN',
        lid_policy=dict(minimum_mm=minimum,hinge_required_height_mm=hinge_minimum),plywood_colorref=PLYWOOD_COLORREF)
    with cad_writer_lock():
        output.mkdir(parents=True,exist_ok=False);working=output/'working_input.ics'
        with case.open('rb') as src,working.open('xb') as dst:shutil.copyfileobj(src,dst)
        base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp);owned=[]
        active=base.ActiveDoc;context=(str(active.Name),bool(active.Modified)) if active else None
        def opened(path):
            already,d=base.OpenFile2(str(path),False,False)
            if already:raise ValueError('Already open; ownership refused')
            owned.append(d)
            if not same_document_path(d.Name,path):raise ValueError('Wrong document')
            return d,d.QueryInterface(A.IZSceneDoc)
        def close(d):close_owned_documents([d],A,output);owned.remove(d)
        def children(e):
            e=e.QueryInterface(A.IZElement);n=e.GetChildrenCount()
            if not n:return []
            a=e.GetChildrenZArray();return [a.Get(i).QueryInterface(A.IZElement) for i in range(n)]
        def matrix(e,world=True):
            se=e.QueryInterface(A.IZSceneElement);m=se.GetTransformToGlobal() if world else se.GetTransformToParent()
            return [[m.GetValue(i,j) for j in range(4)] for i in range(4)]
        def bbox(e,kind='part'):return list(e.QueryInterface(A.IZPart if kind=='part' else A.IZAssembly).GetBoundingBox(True))
        def point(p,m):return [sum(p[k]*m[k][j] for k in range(3))+m[3][j]*1000 for j in range(3)]
        def dirty(e):
            try:assembly=e.QueryInterface(A.IZAssembly)
            except comtypes.COMError:assembly=None
            if assembly is not None:
                for c in children(e):dirty(c)
                assembly.Update()
            else:e.QueryInterface(A.IZPart).Update()
            e.SetDirtyFlag(A.Z_DIRTY_GRAPHICS)
        def same(a,b,tol=.003):
            if len(a)!=len(b) or max(abs(x-y) for x,y in zip(a,b))>tol:raise ValueError(('Native datum drift',a,b))
        try:
            doc,scene=opened(working);u=scene.QueryInterface(A.IZSceneDocUtility);top=scene.GetTopElement().QueryInterface(A.IZAssembly)
            if len(children(scene.GetTopElement()))!=50:raise ValueError('Expected fifty-root profile case')
            for row in rows:
                path=panel_template if row['kind']=='pad' else catalog[row['asset']]['path']
                e=top.AddChildFromExternalFile(str(path),False).QueryInterface(A.IZElement)
                row['node_id']=int(e.Id);e.Name='RockPro - '+row['id']
                se=e.QueryInterface(A.IZSceneElement);anchor=se.GetAnchorTransform()
                for i in range(4):
                    for j in range(4):anchor.SetValue(i,j,int(i==j))
                se.SetAnchorTransform(anchor);m=se.GetTransformToParent()
                for i in range(3):
                    for j in range(3):m.SetValue(i,j,row['rotation'][i][j])
                se.SetTransformToParent(m)
                if row['kind']=='pad':
                    row['feature_id']=int(e.QueryInterface(A.IZPartFeatureMgr).GetFeatureAt(0).QueryInterface(A.IZElement).Id)
                    e.QueryInterface(A.IZPart).SurfaceFinish.Color=PLYWOOD_COLORREF
                    row['position']=row['anchor']
                else:
                    p=row['local_anchor_mm'];R=row['rotation']
                    row['position']=[s+f' - ({sum(p[k]*R[k][j] for k in range(3)):.15g} mm)' for j,s in enumerate(row['anchor'])]
            # Restore dependency expressions after all imports, once only.
            for old in previous['old_bindings']:
                e=u.GetElementById(old['id']);se=e.QueryInterface(A.IZSceneElement)
                if old['kind']=='panel':
                    e.QueryInterface(A.IZPart).SurfaceFinish.Color=PLYWOOD_COLORREF
                    f=u.GetElementById(old['feature_id']);sb=f.QueryInterface(A.IZSizeBox)
                    for axis,s in zip(('Length','Width','Height'),old['size']):setattr(sb,axis+'Expression',expression(s,2))
                    f.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
                for i,s in enumerate(old['position']):se.PositionTransformComponentExpression[i]=expression(s,2 if old['kind']=='corners' else 1)
                se.ForceSetupParameterExpression()
            for old in previous['bindings']:
                e=u.GetElementById(old['node_id']);se=e.QueryInterface(A.IZSceneElement)
                if old['cut_length']:e.QueryInterface(A.IZSizeBox).HeightExpression=expression(old['cut_length'])
                for j,s in enumerate(old['position']):se.PositionTransformComponentExpression[j]=expression(s)
                se.ForceSetupParameterExpression()
            for row in rows:
                e=u.GetElementById(row['node_id']);se=e.QueryInterface(A.IZSceneElement)
                if row['kind']=='pad':
                    f=u.GetElementById(row['feature_id']);sb=f.QueryInterface(A.IZSizeBox)
                    for axis,s in zip(('Length','Width','Height'),row['dimensions']):setattr(sb,axis+'Expression',expression(s,2))
                    f.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
                for j,s in enumerate(row['position']):se.PositionTransformComponentExpression[j]=expression(s)
                se.ForceSetupParameterExpression()
            def update(v):
                validate_transport_values(v)
                for n,x in v.items():scene.ParameterMgr.GetParameterByName(n).Expression=f'{x} mm'
                scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True);scene.Update()
            def measure(label,v):
                members=[];anchors={};contacts={};physical=0
                adapter=NativePoseAdapter(None,base,doc,A,Path(doc.Name))
                for row in rows:
                    e=u.GetElementById(row['node_id']);m=matrix(e)
                    same([m[i][j] for i in range(3) for j in range(3)],[row['rotation'][i][j] for i in range(3) for j in range(3)],1e-7)
                    expected=[value(s,v) for s in row['anchor']]
                    if row['kind']=='pad':
                        b=bbox(e);same([(b[i+3]-b[i])*1000 for i in range(3)],[value(s,v) for s in row['dimensions']],.05)
                        actual=point([0,0,0],m);physical+=1
                    else:
                        actual=point(row['local_anchor_mm'],m)
                        baseline=catalog[row['asset']]['export_signature']
                        for part in baseline:
                            node=e
                            for index in part['path']:node=children(node)[index]
                            same([x*1000 for x in bbox(node,part['kind'])],[x*1000 for x in part['bounds_m']],.05)
                            if part['path']:
                                parent=matrix(node,False);wanted=part['parent_m']
                                for i in range(4):same(parent[i],wanted[i],3e-6 if i<3 else 3e-6)
                            if part['kind']=='part':physical+=1
                        if row['kind']=='wheel':
                            rubber=children(e)[3];body=rubber.QueryInterface(A.IZPart).GetBody(True)
                            rev,center,axis,radius=body.QueryInterface(A.IZBodyFace).GetCylinderData(7)
                            same([radius],[.05],1e-7);same([axis.X,axis.Y,abs(axis.Z)],[0,0,1],1e-6)
                            b=bbox(rubber);p=[center.X*1000,(center.Y-radius)*1000,(b[2]+b[5])*500]
                            contacts[row['pair']]=point(p,matrix(rubber));same([contacts[row['pair']][2]],[-150.1])
                        elif row['kind']=='socket':
                            face=_face(adapter,e,44);vs=face['vertices_world_mm']
                            middle=[(min(p[j] for p in vs)+max(p[j] for p in vs))/2 for j in range(3)]
                            same(middle,expected);same(face['oriented_normal_world'],[0,0,-1],1e-6)
                    same(actual,expected,.05);anchors[row['id']]=actual
                    members.append(dict(id=row['id'],node_id=row['node_id'],anchor_mm=actual))
                for side in ('left','right'):
                    lo=anchors['hinge/'+side+'/base'];hi=anchors['hinge/'+side+'/lid']
                    same(hi,[lo[0],lo[1],lo[2]+v['RP_DisplayGap']])
                for pair,p in contacts.items():same(p[:2],anchors['socket/'+pair][:2])
                for group in ('front','rear'):
                    a=contacts['left/'+group];b=contacts['right/'+group]
                    same([a[0]+b[0],a[1]-b[1]],[v['RP_Length'],0])
                # Retain all existing plate, hardware and edge-profile invariants.
                for old in previous['old_bindings']:
                    e=u.GetElementById(old['id']);se=e.QueryInterface(A.IZSceneElement)
                    same([se.PositionTransformComponentValue[i]*1000 for i in range(3)],[value(s,v) for s in old['position']],.05)
                    if old['kind']=='panel':
                        b=bbox(e);same([(b[i+3]-b[i])*1000 for i in range(3)],[value(s,v) for s in old['size']],.05)
                for old in previous['bindings']:
                    e=u.GetElementById(old['node_id']);b=bbox(e);spans=[(b[i+3]-b[i])*1000 for i in range(3)];wanted=list(old['section_mm'])
                    if old['cut_length']:wanted[2]=value(old['cut_length'],v)
                    same(spans,wanted,.05);center=point([(b[i]+b[i+3])*500 for i in range(3)],matrix(e))
                    same(center,[value(s,v) for s in old['center']],.05)
                if physical!=72:raise ValueError(('Added physical parts',physical))
                report['checks'].append(dict(label=label,parameters_mm=v,members=members,added_physical_parts=physical,wheel_ground_contacts_mm=contacts))
                print(label,'PASS: 2 hinges, 4 casters, 4 sockets, 2 pads; existing case PASS',flush=True)
            update(values);measure('target',values)
            alt=dict(values,RP_Length=2200.,RP_Depth=3200.,RP_BaseHeight=3700.,RP_LidHeight=450.,RP_DisplayGap=80.,RP_JointGap=10.)
            update(alt);measure('parameter_only_resize',alt);update(values);measure('restored',values)
            dirty(scene.GetTopElement());scene.Update()
            result=output/'RockPro_2000x3000x4000_zawiasy_kola_gniazda.ics'
            scene.SaveAs(str(result),A.Z_LINKS_COPY_ALL,False);close(doc)
            doc,scene=opened(result);u=scene.QueryInterface(A.IZSceneDocUtility)
            measure('saved_reopened',values);update(alt);measure('post_reopen_resize',alt)
            update(values);measure('post_reopen_restored',values);doc.Save();close(doc)
            report.update(passed=True,result=str(result),result_sha256=file_sha256(result),source_profile_report=previous)
        finally:
            try:close_owned_documents(owned,A,output)
            finally:
                if file_sha256(case)!=expected_sha256:raise ValueError('Original profile case changed')
                if file_sha256(panel_template)!=template_sha:raise ValueError('Panel template changed')
                for a in catalog.values():
                    if file_sha256(Path(a['path']))!=a['sha256']:raise ValueError('Original asset changed')
                active=base.ActiveDoc;after=(str(active.Name),bool(active.Modified)) if active else None
                if after!=context:raise ValueError('Active document context changed')
        report.update(source_case_unchanged=True,catalog_unchanged=True,owned_documents_closed=True)
        write_receipt_once(output/'transport_build_report.json',report);return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('case','profile-report','assets','panel-template','output-dir'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--expected-case-sha256',required=True);p.add_argument('--native',action='store_true')
    p.add_argument('--lid-height-mm',type=float,help='Explicit target lid height; keeps total plywood height by adjusting base')
    a=p.parse_args()
    if not a.native:print('PLAN ONLY: rigid paired hinges/casters/sockets; native execution NOT RUN');return
    r=execute(a.case,json.loads(a.profile_report.read_text(encoding='utf-8')),json.loads(a.assets.read_text(encoding='utf-8')),a.panel_template,a.output_dir,a.expected_case_sha256,a.lid_height_mm)
    print(json.dumps(dict(passed=r['passed'],result=r['result'])))
if __name__=='__main__':main()
