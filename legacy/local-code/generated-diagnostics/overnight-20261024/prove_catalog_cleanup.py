from pathlib import Path
import hashlib,json,shutil,sys,re
repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo/'Integracja'))
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.catalog_native import close_owned_documents
from rockpro_cad.parts.native import file_sha256,same_document_path
source=repo/'Integracja/skeleton/demo/RockPro_Epson_szkielet_MVP.ics'
folder=Path(__file__).with_name('catalog-cleanup-native');folder.mkdir(exist_ok=False)
original_hash=file_sha256(source);owned=[]
with cad_writer_lock():
    working=folder/'working.ics';shutil.copyfile(source,working)
    base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
    active=base.ActiveDoc;before=(str(active.Name),bool(active.Modified)) if active else None
    def opened(path):
        already,doc=base.OpenFile2(str(path.resolve()),False,False)
        if already:raise ValueError('Already open')
        if not same_document_path(doc.Name,path):raise ValueError('Wrong document')
        owned.append(doc);return doc,doc.QueryInterface(A.IZSceneDoc)
    try:
        doc,scene=opened(working)
        scene.ParameterMgr.GetParameterByName('RP_Length').Expression='935 mm'
        scene.GetTopElement().QueryInterface(A.IZAssembly).RegenerateParts(True);scene.Update()
        if not doc.Modified:raise RuntimeError('Expected dirty copy')
        body_error=None
        try:raise RuntimeError('intentional body failure')
        except RuntimeError as exc:body_error=str(exc)
        finally:close_owned_documents(owned,A,folder)
        recovery=list(folder.glob('owned_recovery_*.ics'))
        if len(recovery)!=1:raise RuntimeError('Expected one recovery')
        doc,scene=opened(recovery[0])
        expression=str(scene.ParameterMgr.GetParameterByName('RP_Length').Expression)
        if abs(float(re.match(r'\s*([0-9.,]+)',expression)[1].replace(',','.'))-935)>.003:raise RuntimeError('Recovery parameter differs')
        close_owned_documents(owned,A,folder)
    finally:
        close_owned_documents(owned,A,folder)
        if file_sha256(source)!=original_hash:raise RuntimeError('Source changed')
        active=base.ActiveDoc;after=(str(active.Name),bool(active.Modified)) if active else None
        if before!=after:raise RuntimeError('User context changed')
report=dict(passed=True,primary_body_error=body_error,recovery=str(recovery[0]),recovery_sha256=file_sha256(recovery[0]),reopened_length_expression=expression,source_unchanged=True,owned_documents_closed=not owned,user_context_unchanged=True)
(folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
