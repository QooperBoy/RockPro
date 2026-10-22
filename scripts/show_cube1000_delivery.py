"""Show the accepted 1000 mm cube through legacy Pages.Add; no UI automation.
This is a separately authorized visible delivery phase, after helper cleanup.
"""
import argparse,ctypes,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.parts.native import file_sha256,same_document_path
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.core_case.corner_native import exclusive_copy
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.core_case.latch_native import foreground

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--expected-pid',type=int,required=True);a=p.parse_args()
    receipt=a.receipt.resolve(strict=True);data=json.loads(receipt.read_text(encoding='utf-8'));cases=data.get('cases',[])
    if data.get('passed') is not True or len(cases)!=1 or cases[0].get('size_mm')!=[1000,1000,1000] or cases[0].get('real_handle_assemblies')!=2:raise RuntimeError('Accepted cube with the expected corner, latch and handle inventory required')
    source=Path(cases[0]['output_path']);expected=cases[0]['sha256']
    for path in (source,Path(cases[0]['archive_path'])):
        if file_sha256(path)!=expected:raise RuntimeError('Accepted cube/archive hash changed')
    for phase in ('source','execute'):
        raw=json.loads((receipt.parent/(phase+'_receipt.json')).read_text(encoding='utf-8'))
        if raw.get('passed') is not True or raw.get('remaining_owned')!=0:raise RuntimeError('Helpers not proven closed')
    delivery=receipt.parent/'delivery';delivery.mkdir(exist_ok=False);output=delivery/'RockPro_skrzynia_1000x1000x1000.ics';exclusive_copy(source,output)
    write_receipt_once(delivery/'copy_receipt.json',{'passed':True,'source_path':str(source),'delivery_path':str(output),'sha256':file_sha256(output),'byte_identical':True,'acceptance_receipt':str(receipt)})
    import comtypes.client
    from comtypes.automation import IDispatch
    app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True);draft=app.ActivePage
    user=ctypes.WinDLL('user32');user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    def state():
        pid=ctypes.c_ulong();h=int(app.HWnd);user.GetWindowThreadProcessId(ctypes.c_void_p(h),ctypes.byref(pid));page=app.ActivePage
        return {'pid':pid.value,'hwnd':h,'foreground':foreground(),'active_path':str(page.FullName),'saved':bool(page.Saved)}
    result={'passed':False,'operation':'explicitly authorized visible delivery open; expected active-document change','delivery_path':str(output),'sha256':expected}
    with cad_writer_lock():
        before=state();result['before']=before
        if before['pid']!=a.expected_pid:raise RuntimeError('Existing hostPID changed')
        try:
            pages=app.Pages;dispatch=pages._comobj if hasattr(pages,'_comobj') else pages.QueryInterface(IDispatch)
            # Official legacy Pages.Add DISP3(filename VARIANT,ForTemplate VARIANT).
            opened=dispatch._invoke(3,1,0,str(output),False)
            result['after']=state();result['passed']=same_document_path(result['after']['active_path'],output) and result['after']['pid']==a.expected_pid and file_sha256(output)==expected
            try:result['prior_context_after']={'path':str(draft.FullName),'saved':bool(draft.Saved)}
            except Exception as e:result['prior_context_after_error']=repr(e)
            result.update(final_result_left_open=True,helper_documents_remaining=0,source_or_unknown_documents_explicitly_closed=0,no_computer_use_or_keyboard=True)
        except Exception as e:result['error']=repr(e);raise
        finally:write_receipt_once(delivery/'visible_open_receipt.json',result)
    if not result['passed']:raise RuntimeError('Visible delivery file identity not confirmed')
    print('OPENED '+str(output),flush=True)
if __name__=='__main__':main()
