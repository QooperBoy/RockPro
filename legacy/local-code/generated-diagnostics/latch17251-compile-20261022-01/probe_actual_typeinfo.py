import ctypes as c,json
from pathlib import Path
import comtypes,comtypes.client
from comtypes import IUnknown,GUID,HRESULT,COMMETHOD,typeinfo
from comtypes.automation import IDispatch
from python_ironcad import ICAPI
class IProvideClassInfo(IUnknown):
 _iid_=GUID('{B196B283-BAB4-101A-B69C-00AA00341D07}')
 _methods_=[COMMETHOD([],HRESULT,'GetClassInfo',(['out'],c.POINTER(c.POINTER(typeinfo.ITypeInfo)),'ppTI'))]
ole=c.OleDLL('ole32');r=c.POINTER(ICAPI.IRunningObjectTable)();ctx=c.POINTER(ICAPI.IBindCtx)();ole.GetRunningObjectTable.argtypes=[c.c_ulong,c.POINTER(type(r))];ole.GetRunningObjectTable.restype=HRESULT;ole.CreateBindCtx.argtypes=[c.c_ulong,c.POINTER(type(ctx))];ole.CreateBindCtx.restype=HRESULT;ole.GetRunningObjectTable(0,c.byref(r));ole.CreateBindCtx(0,c.byref(ctx));en=r.EnumRunning()
expected=r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\skeleton\20261020T110925Z\Epson_source_snapshot.ics'
while True:
 m,n=en.RemoteNext(1)
 if not n:raise RuntimeError('Context absent')
 try:name=m.GetDisplayName(ctx,None)
 except Exception:continue
 if str(name).lower()==expected.lower():break
legacy=comtypes.client.GetBestInterface(r.GetObject(m).QueryInterface(IDispatch));raw=legacy.Application.ZIronCADApp;ptr=raw._comobj if hasattr(raw,'_comobj') else raw.QueryInterface(IDispatch);out={}
for label,action in [('GetTypeInfoCount',lambda:ptr.GetTypeInfoCount()),('GetTypeInfo0',lambda:ptr.GetTypeInfo(0,0).GetDocumentation(-1)),('GetTypeInfo1033',lambda:ptr.GetTypeInfo(0,1033).GetDocumentation(-1)),('GetIDsOfNames_ActiveDoc',lambda:ptr.GetIDsOfNames('ActiveDoc')),('IProvideClassInfo',lambda:ptr.QueryInterface(IProvideClassInfo).GetClassInfo().GetDocumentation(-1)),('IZIronCADApp',lambda:ptr.QueryInterface(ICAPI.IZIronCADApp).ApplicationVersion)]:
 try:out[label]={'success':True,'result':str(action())}
 except Exception as e:out[label]={'success':False,'error':str(e)}
Path('artifacts/latch17251-compile-20261022-01/actual_zapp_typeinfo.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
