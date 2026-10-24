"""Extend a pinned full-case prototype on a NEW copy; no skeleton API changes."""
import argparse
from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.profile_rules import rules,expression,value,validate_values,PARAMETERS
from rockpro_cad.parts.native import file_sha256,same_document_path
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.mcp.lid_policy import PLYWOOD_COLORREF

def execute(case,case_report,assets,output,expected_case_sha256):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as A
    from rockpro_cad.cad_lock import cad_writer_lock
    from rockpro_cad.core_case.catalog_native import close_owned_documents
    original=Path(case).resolve(strict=True);output=Path(output).resolve()
    if file_sha256(original)!=expected_case_sha256 or case_report['result_sha256']!=expected_case_sha256:
        raise ValueError('Full-case file/receipt hash mismatch')
    catalog={r['name']:r for r in assets['rows']}
    if set(catalog)!={'EG-0500_1','EG-0500_2','EG-0113','B1930','B1121'}:
        raise ValueError('Exact five-family catalog selection required')
    for name,row in catalog.items():
        if file_sha256(Path(row['asset']))!=row['sha256']:raise ValueError('Catalog asset hash drift')
        if name.startswith('EG-') and row['features']!=1:raise ValueError('Clean single-feature cut profile required')
    values=dict(case_report['parameters_mm'],RP_JointGap=8.63);validate_values(values)
    definitions=rules();owned=[]
    with cad_writer_lock():
        output.mkdir(parents=True,exist_ok=False)
        working=output/'working_input.ics'
        with original.open('rb') as src,working.open('xb') as dst:shutil.copyfileobj(src,dst)
        base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
        active=base.ActiveDoc;context=(str(active.Name),bool(active.Modified)) if active else None
        def open_owned(path):
            already,d=base.OpenFile2(str(path),False,False)
            if already:raise ValueError('Already open; ownership refused')
            owned.append(d)
            if not same_document_path(d.Name,path):raise ValueError('Wrong CAD document')
            return d,d.QueryInterface(A.IZSceneDoc)
        def close(d):close_owned_documents([d],A,output);owned.remove(d)
        def matrix(e):
            m=e.QueryInterface(A.IZSceneElement).GetTransformToGlobal()
            return [[m.GetValue(i,j) for j in range(4)] for i in range(4)]
        def children(e):
            n=e.GetChildrenCount()
            if not n:return []
            arr=e.GetChildrenZArray();return [arr.Get(i).QueryInterface(A.IZElement) for i in range(n)]
        def graphics(e):
            e.SetDirtyFlag(A.Z_DIRTY_GRAPHICS)
            try:e.QueryInterface(A.IZAssembly)
            except comtypes.COMError:return
            for c in children(e):graphics(c)
        report=dict(schema_version=2,contract='full_case_profiles_v2',production_approved=False,
            source_case=str(original),source_case_sha256=expected_case_sha256,parameters_mm=values,
            source_catalog=assets,bindings=[],checks=[],native_graphics_review='NOT RUN')
        try:
            doc,scene=open_owned(working);u=scene.QueryInterface(A.IZSceneDocUtility)
            if len(children(scene.GetTopElement()))!=18:raise ValueError('Expected the pinned eighteen-root case')
            p=scene.ParameterMgr.CreateParameter(A.Z_PARAMETER_TYPE_LENGTH,'RP_JointGap',.00863)
            p.Expression='8.63 mm';p.ParamTableVisibility=True
            p.Notes='Szczelina konstrukcyjna zlacza EG-0500; niezalezna od rozsuwania widoku. Pelna skrzynia v2.'
            old=case_report['bindings']
            for row in old:
                if row['kind']=='panel' and ' - lid - ' in str(u.GetElementById(row['id']).Name):
                    row['size'][2]+=' - RP_JointGap'
                    row['position'][2]+=' + RP_JointGap'
                if row['kind']=='panel':u.GetElementById(row['id']).QueryInterface(A.IZPart).SurfaceFinish.Color=PLYWOOD_COLORREF
            top=scene.GetTopElement().QueryInterface(A.IZAssembly)
            for row in definitions:
                e=top.AddChildFromExternalFile(catalog[row['sku']]['asset'],False).QueryInterface(A.IZElement)
                e.Name='RockPro - '+row['sku']+' - '+row['id']
                sb=e.QueryInterface(A.IZSizeBox);sb.Reset(False)
                b=list(e.QueryInterface(A.IZPart).GetBoundingBox(True))
                row['node_id']=int(e.Id);row['section_mm']=[(b[i+3]-b[i])*1000 for i in range(3)]
                row['local_center_mm']=[(b[i]+b[i+3])*500 for i in range(3)]
                se=e.QueryInterface(A.IZSceneElement)
                anchor=se.GetAnchorTransform()
                for i in range(4):
                    for j in range(4):anchor.SetValue(i,j,1 if i==j else 0)
                se.SetAnchorTransform(anchor)
                m=se.GetTransformToParent()
                for i in range(3):
                    for j in range(3):m.SetValue(i,j,row['rotation'][i][j])
                se.SetTransformToParent(m)
                center=[f'{c:.15g} mm' for c in row['local_center_mm']]
                if row['cut_length']:center[2]='('+row['cut_length']+')/2'
                row['position']=[row['center'][j]+''.join(f' - ({row["rotation"][i][j]}) * ({center[i]})'
                    for i in range(3) if row['rotation'][i][j]) for j in range(3)]
                e.QueryInterface(A.IZPart).SurfaceFinish.Color=0xC8C8C8
                report['bindings'].append(row)
            # Imports can invalidate dependency caches. Bind once, after ALL imports.
            for row in old:
                e=u.GetElementById(row['id']);se=e.QueryInterface(A.IZSceneElement)
                if row['kind']=='panel':
                    f=u.GetElementById(row['feature_id']);sb=f.QueryInterface(A.IZSizeBox)
                    for axis,s in zip(('Length','Width','Height'),row['size']):setattr(sb,axis+'Expression',expression(s,2))
                    f.QueryInterface(A.IZSceneElement).ForceSetupParameterExpression()
                for i,s in enumerate(row['position']):
                    depth=2 if row['kind']=='corners' else 1
                    se.PositionTransformComponentExpression[i]=expression(s,depth)
                se.ForceSetupParameterExpression()
            for row in report['bindings']:
                e=u.GetElementById(row['node_id']);se=e.QueryInterface(A.IZSceneElement)
                if row['cut_length']:
                    sb=e.QueryInterface(A.IZSizeBox);sb.ResizeAspectLock=A.Z_RESIZE_LOCK_NONE
                    sb.HeightResizeBehavior=A.Z_RESIZE_ABOUT_SIZEBOX_CENTER
                    sb.HeightExpression=expression(row['cut_length'])
                for j,s in enumerate(row['position']):se.PositionTransformComponentExpression[j]=expression(s)
                se.ForceSetupParameterExpression()
            def setparams(v):
                validate_values(v)
                for n,x in v.items():scene.ParameterMgr.GetParameterByName(n).Expression=f'{x} mm'
                scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True);scene.Update()
            def measure(label,v):
                measured=[]
                for row in report['bindings']:
                    e=u.GetElementById(row['node_id']);b=list(e.QueryInterface(A.IZPart).GetBoundingBox(True))
                    spans=[(b[i+3]-b[i])*1000 for i in range(3)];wanted=list(row['section_mm'])
                    if row['cut_length']:wanted[2]=value(row['cut_length'],v)
                    if max(abs(x-y) for x,y in zip(spans,wanted))>.05:raise ValueError(('Profile section/length',label,row['id'],spans,wanted))
                    m=matrix(e);c=[(b[i]+b[i+3])/2 for i in range(3)]
                    center=[1000*(sum(c[k]*m[k][j] for k in range(3))+m[3][j]) for j in range(3)]
                    expected=[value(s,v) for s in row['center']]
                    if max(abs(x-y) for x,y in zip(center,expected))>.05:raise ValueError(('Profile center',label,row['id'],center,expected))
                    if max(abs(m[i][j]-row['rotation'][i][j]) for i in range(3) for j in range(3))>1e-7:raise ValueError('Profile rotation drift')
                    measured.append(dict(id=row['id'],node_id=row['node_id'],spans_mm=spans,center_mm=center))
                panels=[]
                for row in old:
                    e=u.GetElementById(row['id'])
                    if row['kind']=='panel':
                        b=list(e.QueryInterface(A.IZPart).GetBoundingBox(True));dims=[(b[i+3]-b[i])*1000 for i in range(3)]
                        expected=[value(s,v) for s in row['size']]
                        if max(abs(x-y) for x,y in zip(dims,expected))>.05:raise ValueError(('Panel dimensions',label,row['id'],dims,expected))
                        m=matrix(e);panels.append([1000*(m[3][i]+b[i]) for i in range(3)]+[1000*(m[3][i]+b[i+3]) for i in range(3)])
                    se=e.QueryInterface(A.IZSceneElement)
                    if max(abs(se.PositionTransformComponentValue[i]*1000-value(s,v)) for i,s in enumerate(row['position']))>.05:
                        raise ValueError(('Existing panel/hardware anchor',row['id']))
                extent=[min(b[i] for b in panels) for i in range(3)]+[max(b[i+3] for b in panels) for i in range(3)]
                target=[0,0,0,v['RP_Length'],v['RP_Depth'],v['RP_BaseHeight']+v['RP_LidHeight']+v['RP_DisplayGap']]
                if max(abs(x-y) for x,y in zip(extent,target))>.05:raise ValueError(('Case extent',extent,target))
                report['checks'].append(dict(label=label,parameters_mm=v,panel_extent_mm=extent,profile_measurements=measured))
                print(label,'PASS',len(measured),'new members',flush=True)
            setparams(values);measure('target',values)
            alt=dict(values,RP_Length=2200.,RP_Depth=3200.,RP_BaseHeight=3700.,RP_LidHeight=450.,RP_DisplayGap=80.,RP_JointGap=10.)
            setparams(alt);measure('parameter_only_resize',alt)
            setparams(values);measure('restored',values)
            graphics(scene.GetTopElement());scene.Update()
            result=output/'RockPro_2000x3000x4000_profile_i_wzmocnienia.ics'
            scene.SaveAs(str(result),A.Z_LINKS_COPY_ALL,False);close(doc)
            doc,scene=open_owned(result);u=scene.QueryInterface(A.IZSceneDocUtility)
            measure('saved_reopened',values);close(doc)
            report.update(passed=True,result=str(result),result_sha256=file_sha256(result),
                added_profiles=24,added_rigid_braces=8,old_bindings=old)
        finally:
            try:close_owned_documents(owned,A,output)
            finally:
                if file_sha256(original)!=expected_case_sha256:raise ValueError('Original case changed')
                for row in catalog.values():
                    if file_sha256(Path(row['asset']))!=row['sha256']:raise ValueError('Original catalog asset changed')
                active=base.ActiveDoc
                after=(str(active.Name),bool(active.Modified)) if active else None
                if after!=context:raise ValueError('Active document context changed')
        report.update(source_case_unchanged=True,catalog_unchanged=True,owned_documents_closed=True)
        write_receipt_once(output/'profile_build_report.json',report)
        return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('case','case-report','assets','output-dir'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--expected-case-sha256',required=True);p.add_argument('--native',action='store_true')
    a=p.parse_args()
    if not a.native:print('PLAN ONLY: 24 profiles, 8 braces; native execution NOT RUN');return
    result=execute(a.case,json.loads(a.case_report.read_text(encoding='utf-8')),
        json.loads(a.assets.read_text(encoding='utf-8')),a.output_dir,a.expected_case_sha256)
    print(json.dumps(dict(passed=result['passed'],result=result['result'])))
if __name__=='__main__':main()
