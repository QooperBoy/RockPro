exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
new=doc.Application.ZIronCADApp
for n in ['ActiveDoc','Name','Version','Application']:
 try: print(n,getattr(new,n))
 except Exception as e:print(n,str(e))
from comtypes import typeinfo
import winreg
for f in ['ICApiIronCAD.tlb','3iICApiIronCADApp.dll','3iICApiBase.dll','3iICApiCore.dll']:
 l=typeinfo.LoadTypeLibEx('C:/Program Files/IronCAD/2027/bin/'+f,0);a=l.GetLibAttr();print(f,a.guid,a.wMajorVerNum,a.wMinorVerNum)
 try: print('REG',typeinfo.QueryPathOfRegTypeLib(a.guid,a.wMajorVerNum,a.wMinorVerNum,0))
 except Exception as e:print(e)
