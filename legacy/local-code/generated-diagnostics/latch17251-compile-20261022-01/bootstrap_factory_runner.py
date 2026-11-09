import ctypes as ct,json,sys,uuid,os
from pathlib import Path
import comtypes.client
from python_ironcad import ICAPI
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.latch_native import execute_latch_showcase,foreground
from rockpro_cad.core_case.corner_native import exclusive_copy
from rockpro_cad.core_case.native import write_receipt_once
folder=Path('artifacts/latch17251-api-factory-20261022-01').resolve();folder.mkdir(exist_ok=False)
user=ct.WinDLL('user32');user.GetWindowThreadProcessId.argtypes=[ct.c_void_p,ct.POINTER(ct.c_ulong)];user.GetWindowThreadProcessId.restype=ct.c_ulong

def pid(hwnd):
 value=ct.c_ulong();user.GetWindowThreadProcessId(ct.c_void_p(hwnd),ct.byref(value));return value.value
out={'foreground_before':foreground(),'visible_setter_used':False,'activation_used':False};app=None;base=None;owned_host=False;seed=None
try:
 original=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True);original_hwnd=int(original.HWnd);original_pid=pid(original_hwnd)
 out['original']={'hwnd':original_hwnd,'pid':original_pid,'visible':bool(original.Visible)}
 app=comtypes.client.CreateObject('IronCAD.Application',dynamic=True)
 hwnd=int(app.HWnd);app_pid=pid(hwnd);visible=bool(app.Visible);owned_host=bool(app_pid and app_pid!=original_pid and not visible)
 out['factory']={'hwnd':hwnd,'pid':app_pid,'visible':visible,'owned_hidden_host':owned_host};out['foreground_after_factory']=foreground();write_receipt_once(folder/'factory_state.json',out)
 if out['foreground_after_factory']!=out['foreground_before']:raise RuntimeError('Foreground changed by COM factory; stopping')
 base=app.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
 out['api_version']=str(base.ApiVersion);out['baseapp_passed']=True
 if owned_host:
  seed_path=folder/'context_seed.ics';exclusive_copy(Path('artifacts/corner410429-20261022/native-03/A-base/POC_410429_A-base.ics'),seed_path)
  already,seed=base.OpenFile2(str(seed_path),True,False)
  if already or str(seed.Name).lower()!=str(seed_path).lower():raise RuntimeError('Own hidden seed guard')
  context=seed_path
 else:context=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\skeleton\20261020T110925Z\Epson_source_snapshot.ics')
 if foreground()!=out['foreground_before']:raise RuntimeError('Foreground changed before native run')
 result=execute_latch_showcase(context=context,source=Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics'),corner_receipt=json.loads(Path('artifacts/corner410429-20261022/native-03/A-base/corner_native_receipt.json').read_text(encoding='utf-8')),corner_assets=json.loads(Path('artifacts/corner410429-20261022/native-03/assets/assets_receipt.json').read_text(encoding='utf-8')),output=Path('artifacts/latch17251-native-20261022-01'))
 out['native_passed']=result['passed'];out['outputs']=[r['output_path'] for r in result['cases']]
except Exception as error:
 out['error']=str(error);print(type(error).__name__,error,flush=True)
finally:
 try:
  if seed is not None:
   if seed.Modified:
    backup=folder/('preserved_seed_'+uuid.uuid4().hex+'.ics');seed.QueryInterface(ICAPI.IZSceneDoc).SaveAs(str(backup),ICAPI.Z_LINKS_COPY_ALL,False);out['seed_backup']=str(backup)
   if not seed.Modified:seed.Close();out['own_seed_closed']=True
  if owned_host:
   count=int(base.GetOpenDocsCount()) if base is not None else int(app.Pages.Count)
   out['remaining_owned_host_documents']=count
   if count==0:app.Quit();out['own_hidden_host_quit']=True
   else:out['own_hidden_host_quit']=False;out['cleanup_error']='Documents remain; preserved without forcing Quit'
 except Exception as error:out['cleanup_error']=str(error)
 out['foreground_final']=foreground();out['foreground_unchanged']=out['foreground_final']==out['foreground_before'];write_receipt_once(folder/'factory_and_native_result.json',out);print(json.dumps(out,indent=2),flush=True)
if not out.get('native_passed'):raise SystemExit(1)
