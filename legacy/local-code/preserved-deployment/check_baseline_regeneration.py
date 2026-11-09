from wholecase_common import *
cfg=json.loads(STATE.read_text(encoding='utf-8'));folder=Path(cfg['copy']).parent
legacy,base,source=connect(cfg['source']);source_scene=source.QueryInterface(ICAPI.IZSceneDoc)
def source_state():
    u=source_scene.QueryInterface(ICAPI.IZSceneDocUtility)
    return {'saved':bool(legacy.Saved),'front_bbox':list(u.GetElementById(180).QueryInterface(ICAPI.IZFeature).GetBoundingBox()),
            'larg':u.GetElementById(174).QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName('Larg').Value}
r={'source_before':source_state()}
path=folder/'Baseline_regeneration_control.ics'
assert not path.exists()
source_scene.SaveAsCopy(str(path),ICAPI.Z_LINKS_COPY_ALL,False)
doc=base.OpenFile(str(path),False);scene=doc.QueryInterface(ICAPI.IZSceneDoc);u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
construction=u.GetElementById(174)
construction.QueryInterface(ICAPI.IZSceneElement).ParameterMgr.GetParameterByName('Larg').Expression='Sizebox\\Length'
construction.QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
ids=[12631,12782,174,198]
r['before']={str(id):element_data(u.GetElementById(id)) for id in ids}
scene.GetTopElement().QueryInterface(ICAPI.IZAssembly).RegenerateParts(True);scene.Update()
r['after']={str(id):element_data(u.GetElementById(id)) for id in ids}
doc.Save();doc.Close();r['source_after']=source_state()
base.ActiveDoc=base.GetOpenDocByName(cfg['copy'])
(folder/'baseline_regeneration.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('Source unchanged',r['source_before']==r['source_after'],flush=True)
for id in ids:print(id,'before',r['before'][str(id)].get('bbox_local'),'after',r['after'][str(id)].get('bbox_local'),flush=True)
