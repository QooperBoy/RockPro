exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
root=doc.Shape
for label,obj in [('doc',doc),('root',root),('pages',doc.Application.Pages),('children',root.ChildShapes)]:
 print(label)
 try:
  ti=obj._comobj.GetTypeInfo(0);a=ti.GetTypeAttr();print([(ti.GetDocumentation(ti.GetFuncDesc(i).memid)[0],ti.GetDocumentation(ti.GetFuncDesc(i).memid)[1]) for i in range(a.cFuncs)])
 except Exception as e:print(e)
try:print('rootname',root.Name,'children',root.ChildShapes.Count)
except Exception as e:print(e)
