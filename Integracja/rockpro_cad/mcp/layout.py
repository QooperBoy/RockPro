"""Deterministic envelope layout in millimetres; no physical/structural approval."""
import itertools
import json
import math
from project_store import db, project_exists, now

DEFAULT = dict(name="Urządzenie", x=345.4, y=241.9, z=88.2, count=2,
               orientation="XYZ", arrangement="X", gap=20, clearance=20,
               separator=0, side="none", side_width=80, side_depth=300,
               side_height=50, side_name="Kable", thickness=9, lid_height=50)

def _calculate_layout(spec):
    if not isinstance(spec, dict) or set(spec)-set(DEFAULT):
        raise ValueError("Nieznane pola układu")
    s = DEFAULT | spec
    for key in ("name", "side_name"):
        if not isinstance(s[key], str) or not s[key].strip() or len(s[key])>100:
            raise ValueError("Podaj nazwę (do 100 znaków)")
    for key, low, high in [(k, 1, 5000) for k in ("x","y","z","side_width","side_depth","side_height")] + [("gap",0,500),("clearance",0,500),("separator",0,50),("thickness",1,100),("lid_height",2,1000)]:
        v=s[key]
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not low<=v<=high:
            raise ValueError(key+": nieprawidłowa wartość w mm")
    if isinstance(s["count"],bool) or not isinstance(s["count"],int) or not 1<=s["count"]<=30:
        raise ValueError("Liczba urządzeń: 1–30")
    if s["orientation"] not in ["".join(p) for p in itertools.permutations("XYZ")] or s["arrangement"] not in ("X","Y","Z") or s["side"] not in ("none","X","Y"):
        raise ValueError("Nieznany kierunek lub orientacja")
    sizes=[s[c.lower()] for c in s["orientation"]]
    axis="XYZ".index(s["arrangement"])
    clearance=s["clearance"]
    extent=sizes.copy()
    extent[axis]=s["count"]*sizes[axis]+(s["count"]-1)*(s["gap"]+s["separator"])
    inside=[v+2*clearance for v in extent]
    boxes=[]
    for i in range(s["count"]):
        pos=[clearance]*3
        pos[axis]+=i*(sizes[axis]+s["gap"]+s["separator"])
        boxes.append(dict(kind="device", label=s["name"]+" "+str(i+1), pos=pos, size=sizes.copy()))
    # Partition spans the device compartment; gap is additional to sheet thickness.
    if s["side"]!="none":
        side_axis="XY".index(s["side"])
        other=1-side_axis
        inside[other]=max(inside[other],s["side_depth"]+2*clearance)
        inside[2]=max(inside[2],s["side_height"]+2*clearance)
    for i in range(s["count"]-1):
        if not s["separator"]: break
        pos=[0.,0.,0.]; dims=inside.copy()
        pos[axis]=clearance+(i+1)*sizes[axis]+i*(s["gap"]+s["separator"])+s["gap"]/2
        dims[axis]=s["separator"]
        boxes.append(dict(kind="divider", label="Przegroda "+str(i+1),pos=pos,size=dims))
    if s["side"]!="none":
        a="XY".index(s["side"]); old=inside[a]
        pos=[0.,0.,0.];pos[a]=old
        dims=inside.copy();dims[a]=s["thickness"]
        boxes.append(dict(kind="divider",label="Ścianka komory",pos=pos,size=dims))
        pos=[clearance]*3;pos[a]=old+s["thickness"]+clearance
        dims=[0.,0.,s["side_height"]];dims[a]=s["side_width"];dims[1-a]=s["side_depth"]
        boxes.append(dict(kind="accessory",label=s["side_name"],pos=pos,size=dims))
        inside[a]+=s["thickness"]+s["side_width"]+2*clearance
    outer=[v+2*s["thickness"] for v in inside]
    if max(outer)>10000 or s["lid_height"]<=s["thickness"] or outer[2]-s["lid_height"]<=s["thickness"]:
        raise ValueError("Gabaryt lub wysokość pokrywy poza zakresem szkieletu")
    for i,b in enumerate(boxes):
        if any(p<0 or p+d>lim+1e-6 for p,d,lim in zip(b["pos"],b["size"],inside)):
            raise ValueError("Element poza obrysem")
        for c in boxes[:i]:
            if all(min(p+d,q+e)-max(p,q)>1e-6 for p,d,q,e in zip(b["pos"],b["size"],c["pos"],c["size"])):
                raise ValueError("Kolizja elementów: "+b["label"]+" / "+c["label"])
    warnings=["Bryły uproszczone: uwzględnij wystające złącza, uchwyty i przewody.","Wyjmowanie urządzeń, pianki i wytrzymałość wymagają oceny konstruktora."]
    if s["arrangement"]=="Z" and s["count"]>1:
        warnings.append("Piętrowanie: zaprojektuj podparcie i dostęp do dolnych urządzeń; przegroda nie jest zweryfikowaną półką.")
    return dict(spec=s,boxes=boxes,internal=inside,external=outer,warnings=warnings,
                volume_l=math.prod(outer)/1_000_000,
                checks=dict(collisions=False,contained=True),
                parameters=dict(RP_Length=outer[0],RP_Depth=outer[1],RP_BaseHeight=outer[2]-s["lid_height"],RP_LidHeight=s["lid_height"],RP_Thickness=s["thickness"],RP_DisplayGap=0))

def calculate_layout(spec):
    result=_calculate_layout(spec)
    s=result['spec']
    candidates=[]
    for orientation in map(''.join,itertools.permutations('XYZ')):
        for arrangement in 'XYZ':
            item=dict(orientation=orientation,arrangement=arrangement)
            try:
                variant=_calculate_layout(s|item)
                item.update(valid=True,volume_l=variant['volume_l'],external=variant['external'])
            except ValueError as exc:
                item.update(valid=False,volume_l=None,reason=str(exc))
            candidates.append(item)
    # Stable tie order; equal-volume choices receive the same colour/score.
    candidates.sort(key=lambda c:(not c['valid'],round(c['volume_l'] or 0,9),c['orientation'],c['arrangement']))
    def decorate(rows,key):
        valid=[r['volume_l'] for r in rows if r['valid']]
        lo,hi=min(valid),max(valid)
        return [dict(r,key=r[key],score=0.0 if hi-lo<1e-9 else (r['volume_l']-lo)/(hi-lo)) if r['valid'] else dict(r,key=r[key],score=None) for r in rows]
    result['ranking']=dict(
        criterion='external_volume',best=candidates[0],
        orientations=decorate([r for r in candidates if r['arrangement']==s['arrangement']],'orientation'),
        arrangements=decorate([r for r in candidates if r['orientation']==s['orientation']],'arrangement'),
        variants=candidates)
    return result

def ensure(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS layouts (project_id TEXT PRIMARY KEY REFERENCES projects(id), spec TEXT NOT NULL, updated_at TEXT NOT NULL)")

def get_layout(project_id):
    with db() as conn:
        project_exists(conn,project_id);ensure(conn)
        row=conn.execute("SELECT spec,updated_at FROM layouts WHERE project_id=?",(project_id,)).fetchone()
    return dict(saved=bool(row),updated_at=row["updated_at"] if row else None,**calculate_layout(json.loads(row["spec"]) if row else {}))

def save_layout(project_id,spec):
    result=calculate_layout(spec);stamp=now()
    payload=json.dumps(result["spec"],ensure_ascii=False)
    with db() as conn:
        project_exists(conn,project_id);ensure(conn)
        conn.execute("INSERT OR REPLACE INTO layouts VALUES (?,?,?)",(project_id,payload,stamp))
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?",(stamp,project_id))
        conn.execute("UPDATE stages SET status='outdated',updated_at=? WHERE project_id=? AND key IN ('geometry','hardware','wheels','documentation','materials','production')",(stamp,project_id))
        conn.execute("UPDATE stages SET status='review',updated_at=? WHERE project_id=? AND key='layout'",(stamp,project_id))
        conn.execute("INSERT INTO events(project_id,created_at,kind,payload) VALUES (?,?,?,?)",(project_id,stamp,"layout_saved",payload))
    return dict(saved=True,updated_at=stamp,**result)
