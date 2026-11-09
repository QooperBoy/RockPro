import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from wholecase_common import *
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));legacy,base,doc=connect(cfg['analysis'])
scene=base.QueryInterface(ICAPI.IZIronCADApp).OpenNewScene(False,True,'');print('new scene',flush=True)
cat=base.CatalogMgr.Open('C:/Program Files/IronCAD/2027/AppData/PL-PL/Catalogs/Scene/Metric/Shapes.icc')
print('catalog',cat.EntryCount,flush=True)
for i in range(cat.EntryCount):
 e=cat.Entry(i);print(i,e.Name,flush=True)
 if e.Name in ['Blok','Block']:
  part=e.InsertElement();print('insert',part.Name,part.Id,flush=True);break
scene.SaveAs(str(Path(cfg['folder'])/'Skeleton_probe.ics'),ICAPI.Z_LINKS_COPY_ALL,False);print('saved',flush=True)
print(element_data(part),flush=True)
