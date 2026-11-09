exec(open('read_legacy_panels.py',encoding='utf-8-sig').read().split('for i in range')[0])
h=r.ChildShapes.Item(1);g=h.ChildShapes.Item(2);p=g.ChildShapes.Item(1)
for label,o in [('part',p.InstanceShape),('bbox',p.InstanceShape.BoundingBox)]:
 print(label)
 try:
  ti=o._comobj.GetTypeInfo(0);a=ti.GetTypeAttr();print(ti.GetDocumentation(-1));print([ti.GetDocumentation(ti.GetFuncDesc(i).memid)[0] for i in range(a.cFuncs)])
 except Exception as e:print(e)
 for n in ['MinX','X','Length','Value','Count','MinPoint','Item']:
  try:print(n,getattr(o,n))
  except:pass
