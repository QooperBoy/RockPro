import sys,math,array,json
from pathlib import Path
import comtypes.client
comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')
from python_ironcad import ICAPI as A
base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
p=Path(sys.argv[1]).resolve(strict=True)
if len(sys.argv)>2 and sys.argv[2] in ('rear','opposite'):
 doc=base.ActiveDoc
 assert Path(str(doc.Name)).resolve()==p
else:
 base.OpenFile(str(p),False)
 doc=base.ActiveDoc
 assert Path(str(doc.Name)).resolve()==p
scene=doc.QueryInterface(A.IZSceneDoc)
camera=scene.CameraMgr.ActiveCamera
position=[2.,-3.,2.] if not (len(sys.argv)>2 and sys.argv[2]=='rear') else [2.,3.,2.]
if len(sys.argv)>2 and sys.argv[2]=='opposite':position=[-2.,3.,2.]
direction=[.325-position[0],.25-position[1],.2-position[2]]
norm=math.sqrt(sum(x*x for x in direction))
camera.Position=array.array('d',position)
camera.Direction=array.array('d',[x/norm for x in direction])
camera.Up=array.array('d',[0,0,1])
scene.UpdateGraphics(0);scene.Redraw()
print('Visible delivery',doc.Name,flush=True)
