import sys,json
from pathlib import Path
import comtypes.client
from comtypes.automation import IDispatch
from python_ironcad import ICAPI
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'rockpro_cad'/'mcp'))
from worker import dispatch
app=comtypes.client.GetBestInterface(comtypes.client.GetActiveObject('IronCAD.Application').QueryInterface(IDispatch))
base=app.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp)
source=str(root/'skeleton'/'20261020T110925Z'/'RockPro_Epson_szkielet_MVP.ics')
base.OpenFile(source,False)
r=dispatch('save_project',dict(name='DEMO — układ dwóch urządzeń',device='Prostopadłościan CQ18T',source=source))
pid=r['project']['id']
(root/'rockpro_cad'/'qa'/'layout_demo_id.txt').write_text(pid)
print(json.dumps(dict(project_id=pid,source=source)))
