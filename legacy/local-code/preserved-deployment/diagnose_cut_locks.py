from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc();u=scene.QueryInterface(ICAPI.IZSceneDocUtility);rows=[]
for id in [12451,12453,12459,12461,12447,12449,13202,13204,13218]:
    e=u.GetElementById(id);s=e.QueryInterface(ICAPI.IZSceneElement)
    r=element_data(e)
    r.update(anchor_behavior=s.AnchorBehavior,status_flag=s.StatusFlag,anchor_expressions=[s.AnchorTransformComponentExpression[i] for i in range(3)])
    parent=e;r['parent_chain']=[]
    for _ in range(8):
        try:parent=parent.GetParent()
        except Exception:break
        if not parent:break
        r['parent_chain'].append({'id':parent.Id,'name':parent.Name})
    try:r['keep_anchor_fixed']=e.QueryInterface(ICAPI.IZSizeBox).KeepAnchorFixedInSpace
    except Exception as exc:r['size_error']=str(exc)
    rows.append(r)
    print(json.dumps({k:r[k] for k in ['id','position_expressions','anchor_behavior','status_flag','anchor_expressions','keep_anchor_fixed','parent_chain'] if k in r},ensure_ascii=True),flush=True)
(Path(cfg['copy']).parent/'cut_locks.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
