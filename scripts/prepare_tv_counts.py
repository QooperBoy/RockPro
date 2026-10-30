"""Pinned Hisense R002 quantity revision; private source geometry stays in artifacts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'artifacts/tv-counts-20261030'
OLD = ROOT / 'artifacts/tv-hisense85-20261029'
PRIMARY = ['RP_SzerokoscSkrzyni','RP_GlebokoscSkrzyni','RP_WysokoscDolu',
           'RP_WysokoscCzapki','RP_UniesienieCzapki','RP_OdsuniecieWkladow']

def main():
    snapshot=json.loads((EVIDENCE/'snapshot-01/result.json').read_text(encoding='utf-8'))
    assert snapshot['passed'] and snapshot['source_preserved']
    source=Path(snapshot['snapshot'])
    inventory=json.loads((EVIDENCE/'inspect-01/result.json').read_text(encoding='utf-8'))['rows']
    # The old inspector's GUID uniqueness assertion rejects a SaveAsCopy sharing
    # its original's GUID. The complete read is used only after explicit checks.
    assert len([r for r in inventory if r['type']=='Z_ELEMENT_PART'])==383
    rows={r['id']:r for r in inventory}
    old_plan=json.loads((OLD/'plan.json').read_text(encoding='utf-8'))
    mounts=json.loads((OLD/'mounting-04/request.json').read_text(encoding='utf-8'))
    built=json.loads((OLD/'mounting-04/result.json').read_text(encoding='utf-8'))
    assert built['passed']
    aliases={int(k):v for k,v in built['aliases'].items()}
    poses={r['id']:r for r in old_plan['poses']}
    old_rows={r['id']:r for r in mounts['inventory']}
    shifts={1:[[0.]*6 for _ in range(3)]}
    shifts.update({p['id']:p['shift'] for p in old_plan['parts']})
    def shift(i):
        if i in shifts:return shifts[i]
        r=old_rows[i]; parent=r['parent']; p=shift(parent)
        if i not in poses:
            shifts[i]=[row[:] for row in p];return shifts[i]
        pose=poses[i]; rot=old_rows[parent]['world_matrix_m']
        value=[[p[j][k]+sum(pose['coefficients'][axis][k]*rot[axis*4+j] for axis in range(3)) for k in range(6)] for j in range(3)]
        shifts[i]=value;return value
    for i in old_rows:shift(i)
    for old,new in aliases.items():shifts[new]=shifts[old]
    values={p['name']:p['value']*1000 for p in snapshot['parameters']}
    def actual_feature(op):
        part=aliases.get(op['part'],op['part'])
        if str(op['source_feature']) in built['feature_aliases']:
            fid=built['feature_aliases'][str(op['source_feature'])]
        else:fid=rows[part]['features'][op['feature_index']]['id']
        assert any(f.get('id')==fid and f['operation']=='Z_SUBTRACT' for f in rows[part]['features'])
        return part,fid
    parameters=[];configs=[]
    pl={'Lewa':'lewa','Prawa':'prawa','Korpus':'korpus','Czapka':'czapka'}
    def param(name,expression,notes,scalar=False):
        parameters.append(dict(name=name,expression=expression,notes=notes,scalar=scalar))
    for side in ['Lewa','Prawa']:
        for section,handle in [('Korpus',8838 if side=='Lewa' else 8606),('Czapka',8780 if side=='Lewa' else 8693)]:
            name=f'RP_Uchwyty{section}{side}_Liczba'
            spread=f'RP_Uchwyty{section}{side}_Rozstaw'
            center=f'RP_Uchwyt{section}{side}_Pozycja'
            height=f'RP_Uchwyt{section}{side}_Wysokosc'
            param(name,'2',f'Uchwyty H7159 — {pl[section]} — ściana {pl[side]}: liczba sztuk na tej jednej ścianie, całkowita 1–4. Równy rozstaw, przy 1 pośrodku rzędu. Wymaga aktywnego RockPro Ilość okuć; wraz z okuciem włączane są jego wycięcia.',True)
            param(spread,'RP_GlebokoscSkrzyni - 240 mm',f'Uchwyty — {pl[section]} — {pl[side]}: odległość między skrajnymi środkami w osi Y. Dla jednej sztuki nieużywana. Środek rzędu: {center}. Zostaw miejsce przy profilach i między uchwytami.')
            if section=='Korpus':
                param(height,'RP_WysokoscDolu/2',f'Uchwyty — korpus — {pl[side]}: wysokość środka nad spodem sklejki dna, bez kół. Domyślnie połowa wysokości, aby pozostawić strefę zamka przy złączu. Wycięcia są powiązane.')
            op=next(o for o in mounts['operations'] if o['mount']==handle)
            part,feature=actual_feature(op)
            configs.append(dict(kind='handle',side=side,section=section,count=name,spread=spread,center=center,height=height,
                source_mount=handle,source_parent=rows[handle]['parent'],minimum=1,
                cuts=[dict(source_part=part,source_feature=feature,target_part=part)],remove_feature=feature))
        name=f'RP_Zamki{side}_Liczba';spread=f'RP_Zamki{side}_Rozstaw';center=f'RP_Zamki{side}_Pozycja'
        param(name,'2',f'Kompletne zamki L905/915 — ściana {pl[side]}: liczba par na styku korpusu z czapką, całkowita 0–4. Każda para ma dwie połówki, otwory w sklejce i przerwy w profilach. Obsługuje RockPro Ilość okuć.',True)
        param(spread,'RP_GlebokoscSkrzyni - 240 mm',f'Zamki — {pl[side]}: odległość między skrajnymi osiami w osi Y. Jeden zamek trafia w środek rzędu; zero usuwa okucia i ich obróbki z aktywnej konstrukcji.')
        param(center,'RP_GlebokoscSkrzyni/2',f'Zamki — {pl[side]}: środek rzędu od przedniej krawędzi sklejki w osi Y. Przód to ujemne Y, niezależnie od widoku kamery.')
        targets={179:187 if side=='Lewa' else 183,200:208 if side=='Lewa' else 204,225:228 if side=='Lewa' else 231,238:241 if side=='Lewa' else 244}
        halves=[]
        for section,unit in [('Czapka',1329),('Korpus',1342)]:
            cuts=[]
            for op in mounts['operations']:
                if op['mount']!=unit:continue
                source_part,fid=actual_feature(op)
                cuts.append(dict(source_part=source_part,source_feature=fid,target_part=aliases.get(targets[op['part']],targets[op['part']])))
            halves.append(dict(section=section,source_mount=unit,source_parent=rows[unit]['parent'],cuts=cuts))
        configs.append(dict(kind='latch',side=side,count=name,spread=spread,center=center,minimum=0,halves=halves))
    q=dict(contract='rockpro-tv-mount-count-plan-v2',expected_pid=18584,source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        output=str(source.parents[1]/'03_CAD/Do_sprawdzenia/RockPro_Hisense85_r003_liczba_okuc_IC2027.ics'),
        primary=PRIMARY,base=[values[n] for n in PRIMARY],parameters=parameters,rows=configs,
        inventory=inventory,shifts={str(k):v for k,v in shifts.items()},
        controller=str(ROOT/'Integracja/rockpro_cad/addin/bin-counts-v8-2027/RockPro.MountCounts.dll'))
    (EVIDENCE/'plan.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(rows=len(configs),new_parameters=len(parameters),depth_mm=values['RP_GlebokoscSkrzyni'])))

if __name__=='__main__':main()
