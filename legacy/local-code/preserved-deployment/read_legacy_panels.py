exec(open('probe_document.py',encoding='utf-8').read().split("report['success']")[0])
import sys;sys.stdout.reconfigure(encoding='utf-8')
r=doc.Shape
try:
 e=r.IZElement;print('IZElement',e);print(e.QueryInterface(ICAPI.IZElement).Name)
except Exception as e:print(e)
for i in range(1,r.ChildShapes.Count+1):
 h=r.ChildShapes.Item(i);print('half',h.Name)
 for j in range(1,h.ChildShapes.Count+1):
  g=h.ChildShapes.Item(j)
  if g.Name!='konstrukcja':continue
  print('group',g.Name)
  for k in range(1,g.ChildShapes.Count+1):
   p=g.ChildShapes.Item(k);print('panel',p.Name,p.TSID)
   try:print('bbox',p.InstanceShape.BoundingBox)
   except Exception as e:print(e)
