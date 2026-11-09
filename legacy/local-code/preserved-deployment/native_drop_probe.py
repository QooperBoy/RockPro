import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from wholecase_common import *
cfg=json.loads((ROOT/'skeleton_state.json').read_text(encoding='utf-8-sig'));legacy,base,doc=connect(cfg['analysis']);scene=base.QueryInterface(ICAPI.IZIronCADApp).OpenNewScene(False,True,'')
cat=next(base.CatalogMgr.Catalog(i) for i in range(base.CatalogMgr.Count) if base.CatalogMgr.Catalog(i).Name=='Starter');cat.Entry(0).DropObject(900,450)
print('dropped',flush=True)
p=scene.GetFirstChild();print('first',p.Name,p.Id,flush=True);print(element_data(p),flush=True)
scene.SaveAs(str(Path(cfg['folder'])/'Skeleton_probe_drop.ics'),ICAPI.Z_LINKS_COPY_ALL,False)
