import sys,json,comtypes.client
from pathlib import Path
from comtypes.automation import IDispatch
from python_ironcad import ICAPI
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'rockpro_cad'/'mcp'))
from worker import dispatch
pid=(root/'rockpro_cad'/'qa'/'layout_demo_id.txt').read_text()
p=dispatch('get_project',dict(project_id=pid))['project']
a=comtypes.client.GetBestInterface(comtypes.client.GetActiveObject('IronCAD.Application').QueryInterface(IDispatch))
b=a.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
b.OpenFile(p['source'],False)
print('Opened layout revision')
