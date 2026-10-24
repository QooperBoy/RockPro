"""Verify registered wheel/socket datums on a receipt-bound copy, never the source."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.part_registry import contract, metadata, legacy_export_family
from rockpro_cad.parts.native import file_sha256, same_document_path
from rockpro_cad.core_case.transport_rules import make_rules, validate_transport_values
from rockpro_cad.core_case.profile_rules import value
from rockpro_cad.cad_lock import cad_writer_lock


def execute(source,receipt,transport_receipt,output):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as A
    source=source.resolve(strict=True);output=output.resolve()
    previous=json.loads(receipt.read_text(encoding='utf-8'))
    transport=json.loads(transport_receipt.read_text(encoding='utf-8'))
    source_hash=file_sha256(source)
    if previous.get('passed') is not True or previous['result_sha256']!=source_hash:raise ValueError('Source receipt/hash mismatch')
    if transport.get('passed') is not True or transport['result_sha256']!=previous['source_sha256']:raise ValueError('Transport lineage mismatch')
    rules=make_rules({r['alias']:r for r in transport['source_catalog']['rows']})
    ids={r['id']:r['node_id'] for r in transport['members']}
    for row in rules:row['node_id']=ids[row['id']]
    checks=[];owned=[];bindings=[]
    with cad_writer_lock():
        output.mkdir(parents=True,exist_ok=False)
        working=output/'working.ics';shutil.copyfile(source,working)
        base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
        active=base.ActiveDoc;context=(str(active.Name),bool(active.Modified)) if active else None
        def opened(path):
            already,doc=base.OpenFile2(str(path),False,False)
            if already:raise ValueError('Owned copy already open')
            owned.append(doc)
            if not same_document_path(doc.Name,path):raise ValueError('Wrong opened document')
            return doc,doc.QueryInterface(A.IZSceneDoc)
        def near(a,b):
            if len(a)!=len(b) or max(abs(x-y) for x,y in zip(a,b))>.05:raise ValueError(('Datum mismatch',a,b))
        def point(p,e):
            m=e.QueryInterface(A.IZSceneElement).GetTransformToGlobal()
            return [sum(p[k]*m.GetValue(k,j) for k in range(3))+1000*m.GetValue(3,j) for j in range(3)]
        def update(values):
            validate_transport_values(values)
            for key,x in values.items():scene.ParameterMgr.GetParameterByName(key).Expression=f'{x} mm'
            scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True);scene.Update()
        def measure(label,values):
            utility=scene.QueryInterface(A.IZSceneDocUtility);points={};pairs=[]
            for row in rules:
                if row['kind'] not in ('wheel','socket'):continue
                element=utility.GetElementById(row['node_id'])
                near(point(row['local_anchor_mm'],element),[value(s,values) for s in row['anchor']])
                m=element.QueryInterface(A.IZSceneElement).GetTransformToGlobal()
                near([m.GetValue(i,j) for i in range(3) for j in range(3)],[row['rotation'][i][j] for i in range(3) for j in range(3)])
                points[row['id']]=point(row.get('contact_local_mm',row['local_anchor_mm']),element)
            for row in rules:
                if row['kind']!='wheel':continue
                wheel=points[row['id']];socket=points['socket/'+row['pair']];near(wheel[:2],socket[:2])
                pairs.append(dict(interface_id=row['stacking_interface_id'],wheel_contact_mm=wheel,socket_mount_mm=socket,xy_error_mm=max(abs(wheel[i]-socket[i]) for i in (0,1))))
            if len(pairs)!=4:raise ValueError('Four pairs required')
            checks.append(dict(label=label,parameters_mm=values,pairs=pairs,passed=True));print(label,'PASS',flush=True)
        try:
            doc,scene=opened(working)
            values=previous['parameters_mm'];alternate=dict(values,RP_Length=850.,RP_Depth=620.,RP_BaseHeight=350.,RP_LidHeight=90.)
            measure('source_copy',values);update(alternate);measure('resized',alternate);update(values);measure('restored',values)
            final=output/'RockPro_Epson_registry.ics';scene.SaveAs(str(final),A.Z_LINKS_COPY_ALL,False)
            if doc.Modified or not final.exists():raise ValueError('Save not confirmed')
            doc.Close();owned.remove(doc)
            doc,scene=opened(final);measure('saved_reopened',values)
            top=scene.GetTopElement();children=top.GetChildrenZArray();by_node={r['node_id']:r for r in rules}
            for i in range(top.GetChildrenCount()):
                e=children.Get(i).QueryInterface(A.IZElement);node=int(e.Id);r=by_node.get(node)
                family=r['family_id'] if r else legacy_export_family(str(e.Name))
                bindings.append(dict(node_id=node,occurrence_id=r['id'] if r else 'native/'+str(node),
                    stacking_interface_id=r.get('stacking_interface_id') if r else None,**metadata(family)))
            export=output/'native_export.zip';scene.ExportICWebViewerFile(str(export))
            if doc.Modified:raise ValueError('Export modified document')
            doc.Close();owned.remove(doc)
        finally:
            for d in list(owned):
                if d.Modified:
                    recovery=output/'recovery.ics'
                    d.QueryInterface(A.IZSceneDoc).SaveAs(str(recovery),A.Z_LINKS_COPY_ALL,False)
                    if d.Modified or not recovery.exists():raise ValueError('Recovery not confirmed; owned document retained')
                d.Close();owned.remove(d)
            if file_sha256(source)!=source_hash:raise ValueError('Original changed')
            active=base.ActiveDoc;after=(str(active.Name),bool(active.Modified)) if active else None
            if context!=after:raise ValueError('User context changed')
    report=dict(passed=True,registry=contract(),source_sha256=source_hash,result=str(final),result_sha256=file_sha256(final),
        source_export_sha256=file_sha256(export),bindings=bindings,checks=checks,original_unchanged=True,
        scope='Native datum XY registration after resize and reopen; not load or full stacking fit approval')
    (output/'registry_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('source','receipt','transport-receipt','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();execute(a.source,a.receipt,a.transport_receipt,a.output)
