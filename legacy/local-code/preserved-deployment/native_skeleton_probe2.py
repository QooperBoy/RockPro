import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from wholecase_common import *
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));legacy,base,doc=connect(cfg['analysis'])
scene=base.ActiveDoc.QueryInterface(ICAPI.IZSceneDoc)
cat=next(base.CatalogMgr.Catalog(i) for i in range(base.CatalogMgr.Count) if base.CatalogMgr.Catalog(i).Name=='Starter')
print('catalog',cat.EntryCount,flush=True)
e=cat.Entry(0);print(e.Name,flush=True);part=e.InsertElement();print('insert',part.Name,part.Id,flush=True)
scene.SaveAs(str(Path(cfg['folder'])/'Skeleton_probe.ics'),ICAPI.Z_LINKS_COPY_ALL,False);print('saved',flush=True)
print(element_data(part),flush=True)
