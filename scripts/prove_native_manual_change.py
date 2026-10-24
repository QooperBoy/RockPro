"""ROC-40 native proof: detect one handle move on a disposable owned copy."""
import argparse
import json
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.parts.native import file_sha256, same_document_path
from rockpro_cad.core_case.native_changes import capture_selected_poses, guard_native_changes, observed_pose_changes
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
    if len(handles)!=2 or {r['id'] for r in handles}!={682,836}:
        raise ValueError('Pinned two-handle mapping required')
    selection=[dict(id='handles/'+side,node_id=row['id'],group_id='handles')
               for side,row in zip(('left','right'),handles)]
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
            if guard_native_changes(before,before)['blocked']:raise ValueError('Baseline not clean')
            e=scene.QueryInterface(A.IZSceneDocUtility).GetElementById(682).QueryInterface(A.IZSceneElement)
            initial=e.PositionTransformComponentValue[0]*1000
            e.PositionTransformComponentExpression[0]=f'{initial+12} mm'
            e.ForceSetupParameterExpression();scene.Update()
            edited=capture_selected_poses(doc,A,selection,binding)
            delta=observed_pose_changes(before,edited)
            if len(delta['changes'])!=1 or abs(delta['changes'][0]['delta'][0]-12)>.05:
                raise ValueError('Expected exactly one 12 mm handle movement')
            def blocked(snapshot):
                try:guard_native_changes(before,snapshot)
                except ValidationError as error:
                    if error.code!='SYMMETRY_MANUAL_CONFLICT':raise
                    return error.as_dict()
                raise ValueError('Manual change was not blocked')
            conflict=blocked(edited)
            if capture_selected_poses(doc,A,selection,binding)!=edited:
                raise ValueError('Guard rewrote user evidence')
            doc.Save();close(doc)
            doc=opened();reopened=capture_selected_poses(doc,A,selection,binding)
            reopened_conflict=blocked(reopened)
            if observed_pose_changes(before,reopened)!=delta:
                raise ValueError('Manual move did not survive save/reopen')
            close(doc)
            result=dict(passed=True,scope='Two explicitly bound H7159 occurrences only',
                        baseline=before,edited=edited,reopened=reopened,observed=delta,
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
        print('PASS: 12 mm manual handle move detected and blocked; save/reopen preserves change; source unchanged',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','receipt','output-dir'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    args=parser.parse_args()
    if args.native:execute(args.source,args.receipt,args.output_dir)
    else:print('PLAN ONLY: explicit two-handle native manual-change proof; CAD NOT RUN')
