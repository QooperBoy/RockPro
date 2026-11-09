exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
app=doc.Application
for label,o in [('app',app),('new',app.ZIronCADApp)]:
 print(label,type(o),repr(o))
 raw=o._comobj
 try:
  ti=raw.GetTypeInfo(0);print(ti.GetDocumentation(-1));a=ti.GetTypeAttr();print('GUID',a.guid);print([ti.GetDocumentation(ti.GetFuncDesc(i).memid)[0] for i in range(a.cFuncs)])
 except Exception as e: print(e)
 for iface in [ICAPI.IZBaseApp,ICAPI.IZIronCADApp]:
  try:print(iface.__name__,raw.QueryInterface(iface))
  except Exception as e: print(iface.__name__,e)
