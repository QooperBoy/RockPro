from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc();u=scene.QueryInterface(ICAPI.IZSceneDocUtility);rows=[]
def walk(e,depth=0):
    d=element_data(e);d['depth']=depth
    try:d['feature_box']=list(e.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
    except Exception:pass
    rows.append(d)
    if depth<3:
        try:cs=children(e)
        except Exception as exc:
            d['enumeration_warning']=str(exc);cs=[]
        for c in cs:walk(c,depth+1)
for id in [695,698,13346,13345]:walk(u.GetElementById(id))
(Path(cfg['copy']).parent/'auxiliary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print([(r['id'],r['depth'],ascii(r['name']),r.get('sizebox')) for r in rows],flush=True)
