from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc();u=scene.QueryInterface(ICAPI.IZSceneDocUtility)
folder=Path(cfg['copy']).parent
old=json.loads((folder/'geometry_inventory.json').read_text(encoding='utf-8'))
byid={r['id']:r for r in old}
groups={115:{'profiles':[852,9017],'rigid_groups':[9089,9439],'skip':[7499,174,11614]},
        116:{'profiles':[246,9052],'rigid_groups':[9077,9427,526],'skip':[198,13345]}}
manifest={'base':{'RP_Length':.914,'RP_Depth':.602,'RP_BaseHeight':.23924,'RP_LidHeight':.10413},'items':[],'excluded':[7499,11614,13345]}
for half,g in groups.items():
    for e in children(u.GetElementById(half)):
        if e.Id in g['skip']:continue
        kind='profile' if e.Id in g['profiles'] else 'rigid'
        nested=e.Id in g['profiles']+g['rigid_groups']
        elems=children(e) if nested else [e]
        for t in elems:
            row=dict(byid[t.Id]);row.update(half=half,parent=e.Id if nested else half,depth=3 if nested else 2,kind=kind)
            row['bbox_world']=transformed_bbox(row['bbox_local'],row['matrix_global'])
            if kind=='profile':
                fs=children(t);f=next(x for x in fs if x.Name=='Blok')
                row['feature']=element_data(f);row['feature']['bbox_local']=list(f.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
                row['feature']['bbox_world']=transformed_bbox(row['feature']['bbox_local'],row['feature']['matrix_global'])
                row['other_features']=[element_data(x) for x in fs if x.Id!=f.Id]
            manifest['items'].append(row)
            print(row['id'],row['kind'],flush=True)
(folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Captured',len(manifest['items']),flush=True)
