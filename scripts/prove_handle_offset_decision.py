"""Native QA of a recorded H7159 offset on an owned copy; never production approval."""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Integracja'),str(ROOT/'Integracja/rockpro_cad/mcp')]
from rockpro_cad.parts.native import file_sha256,same_document_path
from rockpro_cad.core_case.native_changes import capture_selected_poses,_dimension_values
from rockpro_cad.core_case.handle_decisions import apply_bound_handle_offsets,review_handle_decision
from rockpro_cad.core_case.catalog_native import close_owned_documents
import handle_decision_service as service
import project_store as store
import worker


def execute(receipt_path,sidecar_path,output):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as api
    from rockpro_cad.cad_lock import cad_writer_lock
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'));sidecar=json.loads(sidecar_path.read_text(encoding='utf-8'))
    if receipt['passed'] is not True:raise ValueError('Verified manual-change receipt required')
    source=Path(receipt['preserved_manual_copy']).resolve(strict=True);source_sha=file_sha256(source)
    if source_sha!=receipt['preserved_manual_copy_sha256']:raise ValueError('Manual source changed')
    baseline=sidecar['snapshot'];mapping=sidecar['mapping'];per_wall=sidecar['per_wall']
    selection=[dict(id=r['logical_id'],node_id=r['id'],group_id='handles') for r in mapping]
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    working=output/'reconciled_handles.ics';shutil.copyfile(source,working)
    owned=[]
    with cad_writer_lock():
        base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(api.IZBaseApp)
        active=base.ActiveDoc;context=(str(active.Name),bool(active.Modified)) if active else None
        def open_copy():
            already,doc=base.OpenFile2(str(working),False,False)
            if already:raise ValueError('Refusing ownership of an already-open copy')
            owned.append(doc)
            if not same_document_path(doc.Name,working):raise ValueError('Wrong document opened')
            return doc
        def close(doc):close_owned_documents([doc],api,output);owned.remove(doc)
        try:
            doc=open_copy();scene=doc.QueryInterface(api.IZSceneDoc)
            current=capture_selected_poses(doc,api,selection,baseline['binding']);values=_dimension_values(current)
            evidence=dict(baseline=baseline,current=current,mapping=mapping,per_wall=per_wall,
                target_values=values,observed_source_sha256=source_sha)
            (output/'measurement.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
            proposal=service.preview_handle_reconciliation(evidence,'adopt_offset')
            if proposal['blocked'] or not any(any(abs(n)>1 for n in delta) for delta in proposal['state']['offsets_mm'].values()):
                raise ValueError('Expected a nonzero, fitting manual offset')
            # Isolated QA database; never write a constructor approval into the
            # real project database from an automated proof.
            store.DB_PATH=output/'qa-decisions.sqlite3'
            worker.ROOT=output  # Isolated QA workspace, not the deployed configuration.
            project=store.save_project('SYNTHETIC QA decision only',source=str(working))['project']['id']
            service.save_handle_reconciliation(project,evidence,'adopt_offset',0,1,proposal['review_sha256'],'AUTOMATED-QA-NOT-CONSTRUCTOR-APPROVAL')
            state=service.get_handle_reconciliation(project)['result']['state']
            apply_bound_handle_offsets(scene,api,mapping,per_wall,values,state)
            doc.Save();close(doc);doc=open_copy();scene=doc.QueryInterface(api.IZSceneDoc)
            reopened=capture_selected_poses(doc,api,selection,baseline['binding'])
            first=review_handle_decision(baseline,reopened,mapping,per_wall,values,prior_state=state)
            if first['blocked']:raise ValueError('Recorded offset did not survive first save/reopen')
            resized=dict(values,RP_Length=values['RP_Length']+20,RP_Depth=values['RP_Depth']+40,RP_BaseHeight=values['RP_BaseHeight']+10)
            for name,n in resized.items():scene.ParameterMgr.GetParameterByName(name).Expression=f'{n} mm'
            scene.GetTopElement().QueryInterface(api.IZAssembly).RegenerateParts(True);scene.Update()
            after=capture_selected_poses(doc,api,selection,baseline['binding'])
            check=review_handle_decision(baseline,after,mapping,per_wall,resized,prior_state=state)
            if check['blocked']:raise ValueError('Offset failed to follow native parameter resize')
            doc.Save();close(doc);doc=open_copy()
            final=capture_selected_poses(doc,api,selection,baseline['binding'])
            final_check=review_handle_decision(baseline,final,mapping,per_wall,resized,prior_state=state)
            if final_check['blocked']:raise ValueError('Resize/offset did not survive final save/reopen')
            close(doc)
            result=dict(passed=True,scope='H7159 group only; QA decision is not constructor approval',source_sha256=source_sha,
                state=state,first_reopen_review=first,resize_review=check,final_reopen_review=final_check,
                parameters_mm=resized,result=str(working),result_sha256=file_sha256(working),production_approved=False)
        finally:
            close_owned_documents(owned,api,output)
            if file_sha256(source)!=source_sha:raise ValueError('Manual source changed')
            active=base.ActiveDoc;after=(str(active.Name),bool(active.Modified)) if active else None
            if after!=context:raise ValueError('User context changed')
        result.update(source_unchanged=True,owned_documents_closed=True,user_context_unchanged=True)
    (output/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('PASS native offset: recorded, reopened, resized and reopened; source unchanged')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('receipt','sidecar','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native',action='store_true');a=p.parse_args()
    if a.native:execute(a.receipt,a.sidecar,a.output)
    else:print('PLAN ONLY: native offset decision proof NOT RUN')
