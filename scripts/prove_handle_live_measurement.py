"""ROC-40 native measurement/read-again guard using a copied QA project only."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Integracja'),str(ROOT/'Integracja/rockpro_cad/mcp')]
import project_store as store
import worker
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.parts.native import file_sha256,same_document_path
from rockpro_cad.core_case.catalog_native import close_owned_documents


def execute(receipt_path,output):
    import comtypes.client
    comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
    from python_ironcad import ICAPI as api
    receipt_path=receipt_path.resolve(strict=True)
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt.get('passed') is not True:raise ValueError('Verified offset receipt required')
    source=Path(receipt['result']).resolve(strict=True);database=receipt_path.parent/'qa-decisions.sqlite3'
    original_sha=file_sha256(source);database_sha=file_sha256(database)
    if original_sha!=receipt['result_sha256']:raise ValueError('Pinned source changed')
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    working=output/'observed_copy.ics';shutil.copyfile(source,working)
    qa_db=output/'qa-projects.sqlite3'
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(qa_db) as dst:src.backup(dst)
    store.DB_PATH=qa_db;worker.ROOT=output  # Process-local isolated QA configuration.
    cards=store.list_projects()['projects']
    if len(cards)!=1:raise ValueError('Expected one isolated source QA project')
    card=cards[0]
    updated=store.save_project(card['name'],project_id=card['id'],source=str(working),expected_revision=card['revision'])['project']
    project=updated['id'];card_revision=updated['revision']
    print('QA copied; starting native read of the owned document',flush=True)
    owned=[]
    with cad_writer_lock():
        base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(api.IZBaseApp)
        active=base.ActiveDoc;context=(str(active.Name),bool(active.Modified)) if active else None
        try:
            already,doc=base.OpenFile2(str(working),False,False)
            if already:raise ValueError('Refusing ownership of already-open document')
            owned.append(doc)
            if not same_document_path(doc.Name,working):raise ValueError('Wrong document')
            saved=worker.dispatch('get_handle_reconciliation',dict(project_id=project))
            measured=worker.dispatch('measure_handle_reconciliation',dict(project_id=project,expected_revision=saved['revision'],expected_project_revision=card_revision))
            if measured['preview']['blocked']:raise ValueError('Previously accepted offset not replayed')
            print('PASS: read-only native observation from the already-open copy',flush=True)
            def arguments(observation):
                args=dict(project_id=project,evidence=observation['evidence'],choice='adopt_offset',
                    expected_revision=saved['revision'],expected_project_revision=card_revision,
                    prior_state=observation['prior_state'],measurement_id=observation['measurement_id'],
                    decision_reference='AUTOMATED-QA-NOT-CONSTRUCTOR-APPROVAL')
                preview=worker.dispatch('preview_handle_reconciliation',dict(evidence=args['evidence'],choice=args['choice'],prior_state=args['prior_state']))
                if preview['blocked']:raise ValueError('QA offset no longer fits')
                return args|dict(review_sha256=preview['review_sha256'])
            stale_args=arguments(measured)
            # Deliberate unsaved edit on the owned copy only. The native reader
            # itself has no setter, save, close, open or activation operation.
            scene=doc.QueryInterface(api.IZSceneDoc)
            mapping=measured['evidence']['mapping'];identity=mapping[-1]['id']
            element=scene.QueryInterface(api.IZSceneDocUtility).GetElementById(identity).QueryInterface(api.IZSceneElement)
            position=element.PositionTransformComponentValue[1]*1000
            element.PositionTransformComponentExpression[1]=f'{position+1} mm'
            element.ForceSetupParameterExpression();scene.Update()
            try:worker.dispatch('save_handle_reconciliation',stale_args)
            except ValueError as error:
                if 'HANDLE_MEASUREMENT_STALE' not in str(error):raise
                stale_error=str(error)
            else:raise ValueError('Stale native observation was accepted')
            if worker.dispatch('get_handle_reconciliation',dict(project_id=project))['revision']!=saved['revision']:
                raise ValueError('Rejected stale observation wrote a decision')
            print('PASS: unsaved CAD edit after preview rejected without a decision write',flush=True)
            fresh=worker.dispatch('measure_handle_reconciliation',dict(project_id=project,expected_revision=saved['revision'],expected_project_revision=card_revision))
            recorded=worker.dispatch('save_handle_reconciliation',arguments(fresh))
            if not recorded['result']['native_capture_verified_by_service'] or not fresh['document_modified']:
                raise ValueError('Fresh native evidence was not preserved')
            preserved=output/'edited_preserved.ics';scene.Update();doc.SaveAs(str(preserved))
            if not preserved.is_file() or not same_document_path(doc.Name,preserved) or bool(doc.Modified):raise ValueError('QA edit not preserved')
            result=dict(passed=True,scope='Bound H7159 native read and stale decision guard only',
                stale_error=stale_error,native_measurement=measured,fresh_measurement=fresh,recorded=recorded,
                edited_preserved=str(preserved),edited_sha256=file_sha256(preserved),production_approved=False)
        finally:
            close_owned_documents(owned,api,output)
            if file_sha256(source)!=original_sha or file_sha256(database)!=database_sha:raise ValueError('Historical input modified')
            if file_sha256(working)!=original_sha:raise ValueError('Input copy was overwritten instead of preserving edit separately')
            active=base.ActiveDoc;after=(str(active.Name),bool(active.Modified)) if active else None
            if after!=context:raise ValueError('User active context changed')
    result.update(source_unchanged=True,historical_database_unchanged=True,owned_documents_closed=True,user_context_unchanged=True)
    (output/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS: fresh measured decision saved, QA edit preserved, original model/database/context unchanged',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--native',action='store_true');a=p.parse_args()
    if a.native:execute(a.receipt,a.output)
    else:print('PLAN ONLY: no CAD operation performed')
