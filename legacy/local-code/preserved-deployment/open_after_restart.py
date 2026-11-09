import comtypes.client,json
from pathlib import Path
from python_ironcad import ICAPI
from comtypes.automation import IDispatch
app=comtypes.client.GetBestInterface(comtypes.client.GetActiveObject('IronCAD.Application').QueryInterface(IDispatch));base=app.ZIronCADApp.QueryInterface(ICAPI.IZBaseApp);print('CONNECTED',base.ApplicationVersion)
cfg=json.loads(Path('skeleton_state.json').read_text(encoding='utf-8-sig'));doc=base.OpenFile(cfg['analysis'],False);print('OPEN')

