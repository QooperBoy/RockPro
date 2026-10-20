from pathlib import Path
import json
from ironcad_adapter import ICAPI, connect, find, parameters, parameter_data

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'wholecase_state.json'

def children(elem):
    try:
        if not elem.GetChildrenCount(): return []
        arr=elem.GetChildrenZArray()
        return [arr.Get(i).QueryInterface(ICAPI.IZElement) for i in range(arr.Count())]
    except Exception as exc:
        raise RuntimeError(f'Cannot enumerate element {elem.Id}') from exc

def transformed_bbox(box,m):
    import itertools
    pts=[[sum(p[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)]
         for p in itertools.product(*[(box[i],box[i+3]) for i in range(3)])]
    return [min(p[j] for p in pts) for j in range(3)]+[max(p[j] for p in pts) for j in range(3)]

def matrix(elem, global_space=True):
    se=elem.QueryInterface(ICAPI.IZSceneElement)
    m=se.GetTransformToGlobal() if global_space else se.GetTransformToParent()
    data=m.Data
    if len(data)==16 and not isinstance(data[0],(tuple,list)):
        result=[[data[i*4+j] for j in range(4)] for i in range(4)]
        if all(abs(result[3][j]-m.GetValue(3,j))<1e-10 for j in range(3)):
            return result
    return [[m.GetValue(i,j) for j in range(4)] for i in range(4)]

def bbox(elem, local=False):
    errors=[]
    for iface in [ICAPI.IZAssembly,ICAPI.IZPart]:
        try: return list(elem.QueryInterface(iface).GetBoundingBox(local))
        except Exception as exc: errors.append(str(exc))
    raise RuntimeError('No bbox: '+repr(errors))

def get_doc():
    cfg=json.loads(STATE.read_text(encoding='utf-8'))
    legacy,base,doc=connect(cfg['copy'])
    return cfg,legacy,base,doc,doc.QueryInterface(ICAPI.IZSceneDoc)

def element_data(elem):
    row={'id':elem.Id,'name':elem.Name,'system_name':elem.SystemName}
    try:
        se=elem.QueryInterface(ICAPI.IZSceneElement)
        row['position']=[se.PositionTransformComponentValue[i] for i in range(3)]
        row['position_expressions']=[se.PositionTransformComponentExpression[i] for i in range(3)]
        row['matrix_global']=matrix(elem)
        row['matrix_parent']=matrix(elem,False)
    except Exception as exc: row['transform_error']=str(exc)
    for local,key in [(False,'bbox_parent'),(True,'bbox_local')]:
        try: row[key]=bbox(elem,local)
        except Exception as exc: row[key+'_error']=str(exc)
    if 'bbox_local' in row and 'matrix_global' in row:
        row['bbox_world']=transformed_bbox(row['bbox_local'],row['matrix_global'])
    try:
        sb=elem.QueryInterface(ICAPI.IZSizeBox)
        row['sizebox']=[sb.Length,sb.Width,sb.Height]
    except Exception: pass
    return row
