"""Pinned Hisense prototype plan from native evidence; never a generic ICS mapper."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'artifacts/tv-hisense85-20261029'
PROJECT=ROOT.parents[2]/'projekty/Telewizor_Hisense85_parametryczny_20261029'
NAMES=['RP_SzerokoscSkrzyni','RP_GlebokoscSkrzyni','RP_WysokoscDolu','RP_WysokoscCzapki','RP_UniesienieCzapki','RP_OdsuniecieWkladow']
BASE=[2023.,372.,488.99,662.99,0.,1165.016452740681]
NOTES=[
 'Szerokość zewnętrzna obrysu sklejki w osi X, bez wystających okuć. Wkłady i profile pomniejszają światło użytkowe. Zakres testowy 1923–2143 mm.',
 'Głębokość zewnętrzna obrysu sklejki w osi Y, bez uchwytów i zamków. Zakres testowy 352–412 mm.',
 'Wysokość dolnego zespołu sklejki, od spodu dna do krawędzi złącza. Bez kół i szczeliny profili. Zakres testowy 458.99–528.99 mm.',
 'Wysokość zdejmowanej czapki, od jej dolnej krawędzi sklejki do dachu. To wysoka osłona ze wzorca, a nie płytkie wieko zawiasowe. Zakres testowy 632.99–742.99 mm.',
 'Poglądowe uniesienie całej czapki w osi Z; nie jest animacją zawiasu. Do rozdzielenia modelu wpisz 200–400 mm; w stanie transportowym 0 mm.',
 'Odsunięcie pomocniczych wkładów w osi Y. Wzorzec ma 1165.01645 mm; 0 pokazuje je w obrysie skrzyni. Nie zmienia formatek. Ich montaż wymaga osobnego potwierdzenia.'
]

def compose_rotation(local, world):
    """Row-vector feature frame composed with its owning part frame."""
    return [sum(local[i*4+k]*world[k*4+j] for k in range(3))
            if i<3 and j<3 else 0 for i in range(4) for j in range(4)]

def axis_growth(rotation, growth):
    return [growth[max(range(3), key=lambda j:abs(rotation[a*4+j]))]
            for a in range(3)]

def main():
    r=json.loads((EVIDENCE/'inspect-04/result.json').read_text(encoding='utf-8-sig'))
    details=json.loads((EVIDENCE/'details-01/result.json').read_text(encoding='utf-8-sig'))
    rows=r['rows'];by={x['id']:x for x in rows};children={}
    if sum(x['type']=='Z_ELEMENT_PART' for x in rows)!=383:
        raise ValueError('This prototype requires the inspected 383-part revision')
    for x in rows:children.setdefault(x['parent'],[]).append(x)
    detail={x['id']:x for x in details['rows']};struct=set(detail)
    def path(x):
        result=[]
        while x['parent']>=0:result.append(x['id']);x=by[x['parent']]
        return list(reversed(result))
    def bounds(x):
        if 'bounds_m' in x:
            b=x['bounds_m'];m=x['world_matrix_m'];ps=[[1000*(m[12+j]+sum(b[k+3*((mask>>k)&1)]*m[k*4+j] for k in range(3))) for j in range(3)] for mask in range(8)]
            return [min(p[k] for p in ps) for k in range(3)]+[max(p[k] for p in ps) for k in range(3)]
        bs=[bounds(c) for c in children.get(x['id'],[])];bs=[b for b in bs if b]
        return [min(b[k] for b in bs) for k in range(3)]+[max(b[k+3] for b in bs) for k in range(3)] if bs else None
    boxes={x['id']:bounds(x) for x in rows}
    def descendants(x):return [y for y in rows if x['id'] in path(y)]
    # Whole small hardware assemblies, not their nuts/rivets/internal features.
    units=set()
    for x in rows:
        if x['type']!='Z_ELEMENT_ASSEMBLY' or not boxes[x['id']]:continue
        desc=descendants(x)
        if any(y['id'] in struct for y in desc):continue
        size=[boxes[x['id']][k+3]-boxes[x['id']][k] for k in range(3)]
        if 'Inżynieria' in x['name'] or all(v<400 for v in size):
            if not any(i in units for i in path(x)[:-1]):units.add(x['id'])
    def coefficients(point,ancestry):
        x,y,z=point;root=ancestry[0] if ancestry else 1
        # Small units preserve edge offsets; central rows remain centred.
        snap=lambda t,lo,hi,margin:0. if t-lo<margin else 1. if hi-t<margin else .5
        cx=snap(x,-2032,-9,300)
        yy=y-(BASE[5] if root in (247,263) else 0)
        cy=snap(yy,-1011.5,-639.5,125)
        cz=snap(z,-748.40346002624,-85.41346002624,150) if root in (115,247) else snap(z,-1246.04328408674,-757.05328408674,150)
        out=[[0.]*6 for _ in range(3)];out[0][0]=cx;out[1][1]=cy
        if root in (115,247):out[2][2]=1;out[2][3]=cz;out[2][4]=1
        else:out[2][2]=cz
        if root in (247,263):out[1][5]=1
        return out
    shifts={1:[[0.]*6 for _ in range(3)]};dimension_coeff={};features=[]
    for x in rows[1:]:
        ancestry=path(x);b=boxes[x['id']]
        owner=next((i for i in ancestry[:-1] if i in units),None)
        if owner:shift=shifts[owner]
        elif not b:shift=shifts[x['parent']]
        else:
            shift=coefficients([(b[k]+b[k+3])/2 for k in range(3)],ancestry)
            if x['id'] in struct:
                size=[b[k+3]-b[k] for k in range(3)];growth=[[0.]*6 for _ in range(3)]
                if size[0]>1000:growth[0][0]=1;shift[0][0]=0
                if size[1]>300:growth[1][1]=1;shift[1][1]=0
                if size[2]>250:
                    if ancestry[0] in (115,247):growth[2][3]=1;shift[2][3]=0
                    elif size[2]>800:growth[2][2]=1;growth[2][3]=1;shift[2][2]=0
                    else:growth[2][2]=1;shift[2][2]=0
                dimension_coeff[x['id']]=growth
        shifts[x['id']]=shift
    lower_shifts={i:[row[:] for row in value] for i,value in shifts.items()}
    def feature_world(x):
        a=x["features"][0]["matrix_m"];b=x["world_matrix_m"]
        return compose_rotation(a,b)
    # Desired part-min shift is not necessarily the shift of its local origin.
    # Extrudes are resized about their unchanged local feature origin (minimum).
    # Convert global lower-end displacement through the part's axis directions.
    for x in rows:
        if x['id'] not in struct:continue
        growth=dimension_coeff[x['id']];w=feature_world(x);shift=shifts[x['id']]
        for local in range(3):
            axis=max(range(3),key=lambda j:abs(w[local*4+j]));sign=w[local*4+axis]
            if sign<-.9:
                for k in range(6):shift[axis][k]+=growth[axis][k]
    poses=[];parts=[];mapping=[]
    for x in rows[1:]:
        shift=shifts[x['id']];parent=by[x['parent']];pm=parent['world_matrix_m'];relative=[[sum((shift[j][k]-shifts[x['parent']][j][k])*pm[a*4+j] for j in range(3)) for k in range(6)] for a in range(3)]
        if x["id"] in struct or any(x["id"] in path(by[i]) for i in struct) or any(abs(v)>1e-9 for row in relative for v in row):poses.append(dict(id=x['id'],depth=x['depth'],matrix_m=x['local_matrix_m'],coefficients=relative))
        if x['type']!='Z_ELEMENT_PART':continue
        growth=dimension_coeff.get(x['id'],[[0.]*6 for _ in range(3)])
        if x['id'] in struct:
            first=x['features'][0];wm=feature_world(x);local_growth=[]
            local_growth=axis_growth(wm,growth)
            features.append(dict(part_id=x['id'],id=first['id'],depth=x['depth']+1,matrix_m=first['matrix_m'],dimension_coefficients=local_growth))
            fs={f['id']:f for f in detail[x['id']]['features'] if 'id' in f}
            for f in x['features'][1:]:
                if f.get('id') not in fs:continue
                fd=fs[f['id']];center=fd.get('profile_center_world_mm')
                if not center:continue
                desired=coefficients(center,path(x))
                # Docisk spans the whole case, so upper-end dependent holes
                # need combined base/hood displacement.
                if boxes[x['id']][5]-boxes[x['id']][2]>800:
                    desired[2][2]=1 if center[2]>-750 else desired[2][2]
                    desired[2][3]=1 if center[2]>-250 else 0
                coeff=[[sum((desired[j][k]-shift[j][k])*wm[a*4+j] for j in range(3)) for k in range(6)] for a in range(3)]
                if any(abs(v)>1e-9 for row in coeff for v in row):features.append(dict(part_id=x['id'],id=f['id'],depth=x['depth']+1,matrix_m=f['matrix_m'],coefficients=coeff,cut=True))
        b=x['bounds_m'];wm=x['world_matrix_m'];local_growth=[]
        for a in range(3):local_growth.append(growth[max(range(3),key=lambda j:abs(wm[a*4+j]))])
        # Baseline part local minima follow the positive feature origin when a
        # local axis points toward the decreasing world coordinate.
        parts.append(dict(id=x['id'],name=x['name'],world_matrix_m=wm,bounds_m=b,
            shift=shift,world_bounds_mm=boxes[x["id"]],lower_shift=lower_shifts[x["id"]],world_growth=growth,local_growth=local_growth,structural=x['id'] in struct))
        ancestry=path(x);unit=next((i for i in ancestry if i in units),None)
        owner=by[unit]['name'] if unit else x['name'];role='profil' if x['name'].startswith('EG-') else 'sklejka' if x['name'] in ['WG','BP','BL','WD','PL'] else 'wkład/docisk' if x['id'] in struct else 'logo/podczęść' if any('Inżynieria' in by[i]['name'] for i in ancestry) else 'okucie/podczęść'
        mapping.append(dict(id=x['id'],name=x['name'],unit_id=unit,unit_name=owner,role=role,
            supplier_sku_status='kod ze źródła, do potwierdzenia' if role=='okucie/podczęść' else 'nie dotyczy',
            source_path='/'.join(map(str,ancestry)),parametric_scope='wymiary i położenie' if x['id'] in struct else 'sztywny element; powiązane położenie'))
    replacements=[]
    cutdetails=json.loads((EVIDENCE/"cut-details-01/result.json").read_text(encoding="utf-8-sig"))
    flanges=[x for x in rows if sum(f.get("name")=="HWDrill" for f in x.get("features",[]))==2 and x["parent"] in units]
    for target in cutdetails["rows"]:
        for fd in target["features"][1:4]:
            point=fd["profile_center_world_mm"]
            candidates=[x for x in flanges if (x["parent"] in [1587,1634,1540,1376,1329,1235])==(target["id"] in [179,191])]
            flange=min(candidates,key=lambda x:sum((((boxes[x["id"]][j]+boxes[x["id"]][j+3])/2)-point[j])**2 for j in range(3)))
            replacements.append(dict(target_part=target["id"],cut_id=fd["id"],tool_part=flange["id"],tool_feature=next(f["id"] for f in flange["features"] if f.get("name")=="HWDrill"),depth=by[target["id"]]["depth"]+1,world_shift=shifts[flange["id"]],part_shift=shifts[target["id"]]))
    source=PROJECT/'01_Kopia_zrodla/HISENSE_85U8Q_ORYGINAL.ics'
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if source_sha!='23bed383abf6738bc784feb0e870e80b80c1503aa3c05bb60a26321ba54dab38':
        raise ValueError('Source revision changed; capture and review a new mapping')
    if len(replacements)!=12 or len({x['cut_id'] for x in replacements})!=12:
        raise ValueError('Expected twelve distinct upper/lower mounting cutouts')
    plan=dict(contract='rockpro-tv-parametric-v1',expected_pid=18584,source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        output=str(PROJECT/'03_CAD/Do_sprawdzenia/RockPro_Hisense85_parametryczny_r001_IC2027.ics'),
        parameters=[dict(name=n,value=v,notes=t) for n,v,t in zip(NAMES,BASE,NOTES)],poses=poses,features=features,parts=parts,
        tests=[dict(name='szersza_glebsza_wyzsza',values=[2143,412,528.99,742.99,0,BASE[5]]),dict(name='mniejsza',values=[1923,352,458.99,632.99,0,BASE[5]]),dict(name='uniesiona_czapka',values=[*BASE[:4],250,BASE[5]])],
        cut_replacements=replacements,rigid_units=sorted(units),mapping=mapping,production_approved=False)
    (EVIDENCE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    (PROJECT/'00_Karta_zlecenia/PLAN_PARAMETRYZACJI.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    with (PROJECT/'00_Karta_zlecenia/MAPOWANIE_CZESCI.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(mapping[0]),delimiter=';');writer.writeheader();writer.writerows(mapping)
    print(json.dumps(dict(parts=len(parts),dimensioned=len(struct),poses=len(poses),features=len(features),rigid_units=len(units))))

if __name__=='__main__':main()
