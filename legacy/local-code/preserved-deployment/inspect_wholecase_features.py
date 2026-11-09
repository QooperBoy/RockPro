from wholecase_common import *
cfg,legacy,base,doc,scene=get_doc()
util=scene.QueryInterface(ICAPI.IZSceneDocUtility)
rows=[]
def visit(e,depth=0):
    row={'id':e.Id,'name':e.Name,'depth':depth,'parameters':[parameter_data(p) for p in parameters(e)]}
    try:
        s=e.QueryInterface(ICAPI.IZSizeBox)
        row['size']=[s.Length,s.Width,s.Height]
        row['expressions']=[s.LengthExpression,s.WidthExpression,s.HeightExpression]
    except Exception: pass
    try: row['feature_bbox']=list(e.QueryInterface(ICAPI.IZFeature).GetBoundingBox())
    except Exception: pass
    try:
        s=e.QueryInterface(ICAPI.IZSceneElement)
        row['position']=[s.PositionTransformComponentValue[i] for i in range(3)]
        row['position_expr']=[s.PositionTransformComponentExpression[i] for i in range(3)]
    except Exception: pass
    rows.append(row)
    if depth<4:
        for c in children(e):visit(c,depth+1)
for id in [174,198,853,9018,9034,247,9053,13345,13226,594]:
    visit(util.GetElementById(id))
out=Path(cfg['copy']).parent/'features.json'
out.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print(str(out),flush=True)
