import hashlib,json,sys
from datetime import datetime,timezone
from wholecase_common import *
sys.stdout.reconfigure(encoding='utf-8')
source=ROOT.parent/'AI_CAD/T_1_1/Showcase_Epson_parametry.ics'
legacy,base,doc=connect(source)
folder=ROOT/'wholecase'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
folder.mkdir(parents=True,exist_ok=False)
copy=folder/'RockPro_Epson_parametric.ics'
cfg={'source':str(source),'copy':str(copy),'source_hash':hashlib.sha256(source.read_bytes()).hexdigest(),'source_saved':bool(legacy.Saved)}
doc.QueryInterface(ICAPI.IZSceneDoc).SaveAsCopy(str(copy),ICAPI.Z_LINKS_COPY_ALL,False)
copydoc=base.OpenFile(str(copy),False)
scene=copydoc.QueryInterface(ICAPI.IZSceneDoc)
top=find(scene,['góra','konstrukcja'])
top.QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName('Larg').Expression='Sizebox\\Length'
top.QueryInterface(ICAPI.IZAssembly).RegenerateParts(True)
scene.Update()
copydoc.Save()
STATE.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
data=[]
for half in children(scene.GetTopElement()):
    r=element_data(half);r['path']=[half.Name];data.append(r)
    for group in children(half):
        r=element_data(group);r['path']=[half.Name,group.Name];data.append(r)
        if group.Name in ['konstrukcja','koła','EG-0500_2','EG-0500_1','EG-0113','410429','B1930']:
            for item in children(group):
                r=element_data(item);r['path']=[half.Name,group.Name,item.Name];data.append(r)
        print(half.Name,group.Name,flush=True)
(folder/'geometry_inventory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Snapshot and audit',copy,flush=True)
