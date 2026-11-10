from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc();u=scene.QueryInterface(ICAPI.IZSceneDocUtility);folder=Path(cfg['copy']).parent
rp=folder/'verification.json';report=json.loads(rp.read_text(encoding='utf-8'));report['geometry_checks_passed']=report['passed'];report['passed']=False
report['ui_blockers']=['Two lower profile H Block regeneration errors on reopen','Wood cutouts not yet attached to moved hardware']
rp.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
(folder/'verification_before_cutouts.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
rows=[]
for half,construction in [(115,174),(116,198)]:
    for panel in children(u.GetElementById(construction)):
        for part in children(panel):
            for f in children(part):
                if f.Name=='Formatka':continue
                d=element_data(f);d['half']=half;d['construction']=construction;d['panel']=panel.Id;d['part']=part.Id;d['depth']=5
                d['bbox_local']=list(f.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
                d['bbox_world']=transformed_bbox(d['bbox_local'],d['matrix_global'])
                d['parent']=element_data(part)
                rows.append(d)
                print(f.Id,ascii(f.Name),flush=True)
(folder/'cutouts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('Cutouts',len(rows),flush=True)
