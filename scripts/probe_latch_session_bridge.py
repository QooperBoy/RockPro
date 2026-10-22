"""Historical diagnostic: publish BaseApp as a private session-only ROT object.
Reuses only the explicitly owned marked probe AddOn; no collection removal.
External typed access failed in the observed host. This is not an installed bridge.
"""
import argparse, ctypes, json, sys
from pathlib import Path
from probe_latch_inprocess import build, ROOT
from rockpro_cad.parts.native import file_sha256
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.core_case.latch_native import foreground, SOURCE_SHA

BRIDGE = '{6BCBAB61-4399-4FD1-86D1-5361B8395C52}'
OWNER = 'RockProProbe_6ec608b840324bc799c957c7abfa5c00'
OLD_DLL = ROOT/'artifacts/latch17251-inprocess-probe-20261022-04/LatchApiProbe.dll'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--expected-pid',type=int,required=True)
    a=p.parse_args(); folder=a.output.resolve()
    if folder.exists() or not folder.is_relative_to(ROOT/'artifacts'):p.error('New artifact folder required')
    import comtypes.client
    from comtypes import GUID
    from comtypes.automation import IDispatch
    from python_ironcad import ICAPI
    app=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True)
    user=ctypes.WinDLL('user32');user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    def state():
        pid=ctypes.c_ulong(); hwnd=int(app.HWnd);user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd),ctypes.byref(pid))
        return {'pid':pid.value,'hwnd':hwnd,'foreground':foreground(),'page':str(app.ActivePage.FullName),'saved':bool(app.ActivePage.Saved),'source_sha':file_sha256(a.source)}
    before=state()
    if before['pid']!=a.expected_pid or not before['saved'] or before['source_sha']!=SOURCE_SHA:raise RuntimeError('Existing saved context/source identity mismatch')
    def disp(v):return v._comobj if hasattr(v,'_comobj') else v.QueryInterface(IDispatch)
    collection=app.AddOns; matches=[]
    for i in range(int(collection.Count)):
        addon=disp(disp(collection)._invoke(5,1,0,i))
        if addon._invoke(3,2,0)==OWNER:matches.append(addon)
    if len(matches)!=1:raise RuntimeError('Unique exact owned AddOn missing; no new AddOn will be created')
    addon=matches[0]
    old={'dll':str(addon._invoke(13,2,0)),'function':str(addon._invoke(12,2,0))}
    if old['dll'].casefold()!=str(OLD_DLL).casefold() or old['function']!='RockProLatchProbe':raise RuntimeError('Owned AddOn configuration mismatch')
    folder.mkdir(); dll=build(folder); expected=file_sha256(dll); outcome={'before':before,'owner':OWNER,'previous':old}
    cookie=0
    try:
        addon._invoke(13,4,0,str(dll));addon._invoke(12,4,0,'RockProLatchPublish')
        if file_sha256(dll)!=expected or str(addon._invoke(13,2,0)).casefold()!=str(dll).casefold() or addon._invoke(12,2,0)!='RockProLatchPublish':raise RuntimeError('Pinned fixed export readback differs')
        outcome['execute_result']=int(addon._invoke(11,1,0))
        report=json.loads((folder/'inprocess_probe.json').read_text(encoding='utf-8'));outcome['inner']=report
        cookie=int(report.get('rot_cookie',0))
        if report['process_id']!=a.expected_pid or report['legacy_app_pid']!=a.expected_pid or report['foreground_before']!=before['foreground'] or report['foreground_after']!=before['foreground']:raise RuntimeError('Inner PID/foreground mismatch')
        if report['register_hr']!='0x00000000' or not cookie:raise RuntimeError('Session publication failed')
        # Explicit requested interface skips GetBestInterface/GetTypeInfo.
        base=comtypes.client.GetActiveObject(GUID(BRIDGE),interface=ICAPI.IZBaseApp)
        outcome['typed_api_version']=str(base.ApiVersion)
        outcome['typed_active_path']=str(base.ActiveDoc.Name)
        if outcome['typed_active_path'].casefold()!=before['page'].casefold():raise RuntimeError('Typed active context differs')
        outcome['passed']=True
    except Exception as error:
        outcome['passed']=False;outcome['error']=repr(error)
    finally:
        try:
            if cookie:
                ole=ctypes.OleDLL('oleaut32');ole.RevokeActiveObject.argtypes=[ctypes.c_ulong,ctypes.c_void_p];ole.RevokeActiveObject.restype=ctypes.c_long
                outcome['revoke_hr']=hex(ole.RevokeActiveObject(cookie,None)&0xffffffff)
                if outcome['revoke_hr'] != '0x0':
                    outcome['passed']=False
                    outcome['cleanup_error']='Session ROT registration was not revoked; see recorded cookie and owner host'
        finally:
            try:
                if addon._invoke(3,2,0)!=OWNER:raise RuntimeError('Owned UUID changed')
                addon._invoke(13,4,0,old['dll']);addon._invoke(12,4,0,old['function']);outcome['own_configuration_restored']=True
            finally:
                outcome['after']=state();outcome['guards_unchanged']=outcome['after']==before
                write_receipt_once(folder/'session_bridge_receipt.json',outcome)
    print(json.dumps(outcome,ensure_ascii=False),flush=True)
    if not outcome.get('passed') or not outcome['guards_unchanged']:raise SystemExit(1)

if __name__=='__main__':main()
