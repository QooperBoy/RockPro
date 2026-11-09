from comtypes import typeinfo
from pathlib import Path
for f in ['3iICApiIronCADApp.dll','3iICApiCore.dll','3iICApiBase.dll','ICApiIronCAD.tlb']:
 l=typeinfo.LoadTypeLibEx('C:/Program Files/IronCAD/2027/bin/'+f,0)
 for i in range(l.GetTypeInfoCount()):
  t=l.GetTypeInfo(i);a=t.GetTypeAttr()
  for j in range(a.cImplTypes):
   try:r=t.GetRefTypeInfo(t.GetRefTypeOfImplType(j));n=r.GetDocumentation(-1)[0]
   except Exception as e:print(f,t.GetDocumentation(-1)[0],j,e)
 print('checked',f)
