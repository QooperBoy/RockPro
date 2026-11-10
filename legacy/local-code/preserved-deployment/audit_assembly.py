"""Bounded read-only structural audit of the source case."""
import json
from pathlib import Path
from ironcad_adapter import connect, parameters, parameter_data, ICAPI
source = Path(__file__).resolve().parent.parent / 'AI_CAD/T_1_1/Showcase_Epson_parametry.ics'
legacy, base, doc = connect(source)
scene = doc.QueryInterface(ICAPI.IZSceneDoc)
rows=[]
def visit(elem, path=(), depth=0):
    elem=elem.QueryInterface(ICAPI.IZElement)
    current=path+((elem.Name,) if elem.Name else ())
    row={'path':list(current),'id':elem.Id}
    rows.append(row)
    try:
        row['parameters']=[parameter_data(p) for p in parameters(elem)] if depth<=2 else []
        se=elem.QueryInterface(ICAPI.IZSceneElement)
        row['position_m']=[se.PositionTransformComponentValue[i] for i in range(3)]
        row['position_expressions']=[se.PositionTransformComponentExpression[i] for i in range(3)]
    except Exception as exc:
        row['scene_element_error']=str(exc)
    try:
        box=elem.QueryInterface(ICAPI.IZSizeBox)
        row['sizebox_m']=[box.Length,box.Width,box.Height]
        row['size_expressions']=[box.LengthExpression,box.WidthExpression,box.HeightExpression]
    except Exception:
        pass
    print(json.dumps({'path':row['path'],'id':row['id']},ensure_ascii=True),flush=True)
    if depth>=3:
        return
    try:
        count=elem.GetChildrenCount()
        row['children_count']=count
        if count:
            children=elem.GetChildrenZArray()
            for i in range(children.Count()):
                visit(children.Get(i),current,depth+1)
    except Exception as exc:
        row['children_error']=str(exc)
visit(scene.GetTopElement())
result={'source':str(source),'maximum_depth':3,'rows':rows}
Path(__file__).with_name('assembly_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('Audited nodes:',len(rows))
for row in rows:
    if len(row['path'])<=3:
        print(json.dumps(row,ensure_ascii=True))
