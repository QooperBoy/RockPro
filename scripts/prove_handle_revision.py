"""ROC-40 four-handle proof: separate native resize from a manual member move."""
import argparse
import json
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.parts.native import file_sha256, same_document_path
from rockpro_cad.core_case.native_changes import capture_selected_poses, guard_handle_update, review_handle_update
from rockpro_cad.core_case.contracts import ValidationError


def execute(source,receipt,output):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as A
    from rockpro_cad.cad_lock import cad_writer_lock
    from rockpro_cad.core_case.catalog_native import close_owned_documents
    source=source.resolve(strict=True)
    output=output.resolve()
    report=json.loads(receipt.read_text(encoding='utf-8'))
    original_hash=file_sha256(source)
    if report.get('passed') is not True or report.get('result_sha256')!=original_hash:
        raise ValueError('Verified prototype receipt/hash required')
    handles=report['small_case_binding_changes']
    per_wall=report['handles_per_wall']
    if len(handles)!=2*per_wall or any('logical_id' not in r for r in handles):
        raise ValueError('Complete semantic handle mapping required')
    selection=[dict(id=row['logical_id'],node_id=row['id'],group_id='handles') for row in handles]
    binding=dict(case_id=source.stem,source_sha256=original_hash,
                 parameter_names=list(report['parameters_mm']))
    with cad_writer_lock():
        output.mkdir(parents=True,exist_ok=False)
        working=output/'manual_edit_preserved.ics'
        with source.open('rb') as src,working.open('xb') as dst:shutil.copyfileobj(src,dst)
        base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
        active=base.ActiveDoc;context=(str(active.Name),bool(active.Modified)) if active else None
        owned=[]
        def opened():
            already,doc=base.OpenFile2(str(working),False,False)
            if already:raise ValueError('Ownership refused for an already-open document')
            owned.append(doc)
            if not same_document_path(doc.Name,working):raise ValueError('Wrong document')
            return doc
        def close(doc):
            close_owned_documents([doc],A,output);owned.remove(doc)
        try:
            doc=opened();scene=doc.QueryInterface(A.IZSceneDoc)
            before=capture_selected_poses(doc,A,selection,binding)
            original_values=report['parameters_mm']
            guard_handle_update(before,before,handles,per_wall,original_values)
            with (output/'baseline_sidecar.json').open('x',encoding='utf-8') as stream:
                json.dump(dict(schema_version=1,source_sha256=original_hash,mapping=handles,
                               per_wall=per_wall,snapshot=before,approved_for_production=False),stream,indent=2)
            resized_values=dict(original_values,RP_Length=original_values['RP_Length']+50,
                                RP_Depth=original_values['RP_Depth']+50,
                                RP_BaseHeight=original_values['RP_BaseHeight']+30)
            for name,number in resized_values.items():scene.ParameterMgr.GetParameterByName(name).Expression=f'{number} mm'
            scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True);scene.Update()
            resized=capture_selected_poses(doc,A,selection,binding)
            target_values=dict(resized_values,RP_Length=resized_values['RP_Length']+25)
            legal_resize=guard_handle_update(before,resized,handles,per_wall,target_values)
            if legal_resize['blocked'] or not legal_resize['parameter_resize_observed']:
                raise ValueError('Legal native resize was incorrectly classified')
            print('PASS: all bound handles followed native resize without manual conflict',flush=True)
            e=scene.QueryInterface(A.IZSceneDocUtility).GetElementById(handles[-1]['id']).QueryInterface(A.IZSceneElement)
            initial=e.PositionTransformComponentValue[1]*1000
            e.PositionTransformComponentExpression[1]=f'{initial+12} mm'
            e.ForceSetupParameterExpression();scene.Update()
            edited=capture_selected_poses(doc,A,selection,binding)
            delta=review_handle_update(before,edited,handles,per_wall,target_values)
            if (len(delta['manual_changes'])!=1
                    or delta['manual_changes'][0]['id']!=handles[-1]['logical_id']
                    or abs(delta['manual_changes'][0]['delta'][1]-12)>.05):
                raise ValueError('Expected exactly one 12 mm move of the last handle')
            def blocked(snapshot):
                try:guard_handle_update(before,snapshot,handles,per_wall,target_values)
                except ValidationError as error:
                    if error.code!='SYMMETRY_MANUAL_CONFLICT':raise
                    return error.as_dict()
                raise ValueError('Manual change was not blocked')
            conflict=blocked(edited)
            if capture_selected_poses(doc,A,selection,binding)!=edited:
                raise ValueError('Guard rewrote user evidence')
            with (output/'pre_save_review.json').open('x',encoding='utf-8') as stream:json.dump(delta,stream,indent=2)
            doc.Save();close(doc)
            doc=opened();reopened=capture_selected_poses(doc,A,selection,binding)
            reopened_conflict=blocked(reopened)
            reopened_review=review_handle_update(before,reopened,handles,per_wall,target_values)
            if (not reopened_review['blocked'] or len(reopened_review['manual_changes'])!=1
                    or reopened_review['manual_changes'][0]['id']!=delta['manual_changes'][0]['id']
                    or max(abs(a-b) for a,b in zip(reopened_review['manual_changes'][0]['delta'],delta['manual_changes'][0]['delta']))>.003):
                raise ValueError('Manual move did not survive save/reopen')
            close(doc)
            result=dict(passed=True,scope=f'All {2*per_wall} explicitly bound H7159 occurrences; handles only',
                        baseline=before,resized=resized,legal_resize=legal_resize,edited=edited,reopened=reopened,reopened_review=reopened_review,observed=delta,
                        conflict=conflict,reopened_conflict=reopened_conflict,
                        source=str(source),source_sha256=original_hash,
                        preserved_manual_copy=str(working),preserved_manual_copy_sha256=file_sha256(working),
                        automatic_changes_applied=False,integrated_into_live_ui=False)
        finally:
            close_owned_documents(owned,A,output)
            if file_sha256(source)!=original_hash:raise ValueError('Original prototype changed')
            active=base.ActiveDoc;after=(str(active.Name),bool(active.Modified)) if active else None
            if after!=context:raise ValueError('User context changed')
        result.update(source_unchanged=True,owned_documents_closed=True,user_context_unchanged=True)
        with (output/'manual_change_receipt.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
        print('PASS: native resize separated from 12 mm manual move; all handles watched; save/reopen and source preservation PASS',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','receipt','output-dir'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    args=parser.parse_args()
    if args.native:execute(args.source,args.receipt,args.output_dir)
    else:print('PLAN ONLY: all-handle resize/manual-change proof; CAD NOT RUN')
