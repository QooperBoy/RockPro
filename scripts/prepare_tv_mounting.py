"""Explicit mounting controls for the verified, private Hisense r001 snapshot."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'artifacts/tv-hisense85-20261029'
PROJECT=ROOT.parents[2]/'projekty/Telewizor_Hisense85_parametryczny_20261029'
PANELS={179:('Czapka','Przod'),183:('Czapka','Prawa'),187:('Czapka','Lewa'),
        191:('Czapka','Tyl'),195:('Czapka','Gora'),200:('Korpus','Przod'),
        204:('Korpus','Prawa'),208:('Korpus','Lewa'),212:('Korpus','Tyl'),216:('Korpus','Dno')}
PL={'Czapka':'czapka','Korpus':'korpus','Przod':'przód','Tyl':'tył','Lewa':'lewa','Prawa':'prawa','Gora':'góra','Dno':'dno','Lewy':'lewy','Prawy':'prawy','Srodkowy':'środkowy'}

def main():
    inventory=json.loads((EVIDENCE/'inspect-04/result.json').read_text(encoding='utf-8'))['rows']
    details=json.loads((EVIDENCE/'details-01/result.json').read_text(encoding='utf-8'))['rows']
    plan=json.loads((EVIDENCE/'plan.json').read_text(encoding='utf-8'))
    built=json.loads((EVIDENCE/'build-07/result.json').read_text(encoding='utf-8'))
    rows={x['id']:x for x in inventory};parts={x['id']:x for x in plan['parts']}
    def path(i):
        result=[]
        while i>=0:result.append(i);i=rows[i]['parent']
        return result[::-1]
    def box(i):
        if i in parts:return parts[i]['world_bounds_mm']
        children=[box(x['id']) for x in inventory if x['parent']==i];children=[x for x in children if x]
        return [min(b[k] for b in children) for k in range(3)]+[max(b[k+3] for b in children) for k in range(3)] if children else None
    def center(i):
        b=box(i);return [(b[k]+b[k+3])/2 for k in range(3)]
    params=[]
    def param(name,expression,note):
        if isinstance(expression,(int,float)):expression=f'{expression:.12g} mm'
        params.append(dict(name=name,expression=expression,notes=note))
        return name
    def wall(i):
        x,y,z=center(i)
        return min([(abs(x+2032),'Lewa'),(abs(x+9),'Prawa'),(abs(y+1011.5),'Przod'),(abs(y+639.5),'Tyl')])[1]
    for side in ('Przod','Tyl'):
        label=PL[side]
        param(f'RP_Zamki{side}_Rozstaw','(RP_SzerokoscSkrzyni - 499.2 mm)/2',f'Zamki, {label}: odległość między sąsiednimi środkami trzech kompletnych zamków. Dwie połówki i obróbki przesuwają się razem. Zalecane 120 mm do połowy szerokości minus 85 mm. Nie zmienia liczby zamków.')
        param(f'RP_Zamki{side}_Przesuniecie',0,f'Zamki, {label}: przesunięcie całego rzędu w osi X projektu; plus w prawo, patrząc od przodu. Zachowaj min. 85 mm od krawędzi do skrajnego środka.')
        param(f'RP_Zamki{side}_Pion',0,f'Zamki, {label}: pionowe odsunięcie obu połówek i ich obróbek od źródłowego położenia na złączu; plus w górę. Zalecany zakres -3 do +3 mm; większe zmiany wymagają kontroli montażu.')
        param(f'RP_Uchwyty{side}_Rozstaw','RP_SzerokoscSkrzyni - 497.3 mm',f'Uchwyty korpusu, {label}: odległość między środkiem lewego i prawego uchwytu. Zalecane min. 180 mm, skrajny środek min. 116 mm od bocznej krawędzi.')
        param(f'RP_Uchwyty{side}_Przesuniecie',0,f'Uchwyty korpusu, {label}: przesunięcie obu uchwytów w osi X projektu. Plus w prawo, niezależnie od obrotu kamery.')
        param(f'RP_Uchwyty{side}_Wysokosc','192.3 mm + (RP_WysokoscDolu - 488.99 mm)/2',f'Uchwyty korpusu, {label}: wysokość środków nad spodem sklejki dna; bez kół. Zalecane 90 mm do wysokości korpusu minus 74 mm. Parametry pojedynczych uchwytów domyślnie korzystają z tej wartości.')
    mounts=[]
    for cut in plan['cut_replacements']:
        flange=cut['tool_part'];unit=rows[flange]['parent'];side=wall(flange);c=center(flange)
        rank=min(range(3),key=lambda k:abs(c[0]-[-1782.4,-1020.5625,-258.6][k]))-1
        dx=f'(-2032 mm + RP_SzerokoscSkrzyni/2 + ({rank})*RP_Zamki{side}_Rozstaw + RP_Zamki{side}_Przesuniecie) - ({c[0]:.13g} mm + {(rank+1)/2:g}*(RP_SzerokoscSkrzyni-2023 mm))'
        mounts.append(dict(id=unit,kind='latch',side=side,rank=rank,section='Czapka' if 115 in path(unit) else 'Korpus',delta=[dx,'0 mm',f'RP_Zamki{side}_Pion']))
    assert len({x['id'] for x in mounts})==12
    for row in inventory:
        if row['name']!='H7159':continue
        i=row['id'];side=wall(i);section='Czapka' if 115 in path(i) else 'Korpus';c=center(i)
        axis=0 if side in ('Przod','Tyl') else 1
        origin=-2032 if axis==0 else -1011.5
        u=c[axis]-origin;h=c[2]-(-748.40346002624 if section=='Czapka' else -1246.04328408674)
        shift=next(x['shift'] for x in plan['parts'] if i in path(x['id']))
        position='Lewy' if c[0]<-1020.5 else 'Prawy'
        key=f'{section}{side}'+(position if axis==0 else '')
        up=f'RP_Uchwyt{key}_Pozycja';hp=f'RP_Uchwyt{key}_Wysokosc'
        if axis==0:
            sign=-1 if position=='Lewy' else 1
            ue=f'RP_SzerokoscSkrzyni/2 + ({sign})*RP_Uchwyty{side}_Rozstaw/2 + 0.45 mm + RP_Uchwyty{side}_Przesuniecie'
            he=f'RP_Uchwyty{side}_Wysokosc'
        else:
            ue='RP_GlebokoscSkrzyni/2'
            coeff=shift[2][3] if section=='Czapka' else shift[2][2]
            he=f'{h:.13g} mm + {coeff:g}*(RP_Wysokosc'+('Czapki - 662.99 mm)' if section=='Czapka' else 'Dolu - 488.99 mm)')
        label=f'{PL[section]}, {PL[side]}'+(', '+('lewy' if position=='Lewy' else 'prawy') if axis==0 else '')
        param(up,ue,f'Uchwyt H7159 — {label}: położenie środka '+('od lewego boku w osi X projektu' if axis==0 else 'od przedniej krawędzi sklejki w osi Y')+'. Zalecany środek min. 116 mm od krawędzi. Otwór przesuwa się razem. Wpisanie liczby zastępuje domyślne powiązanie z rozstawem.')
        param(hp,he,f'Uchwyt H7159 — {label}: wysokość środka od '+('dolnej krawędzi sklejki czapki' if section=='Czapka' else 'spodu sklejki dna, bez kół')+'. Zalecane min. 90 mm, od górnej krawędzi min. 74 mm. Otwór podąża za uchwytem; nie skaluje się.')
        primary='RP_SzerokoscSkrzyni' if axis==0 else 'RP_GlebokoscSkrzyni';base=2023 if axis==0 else 372
        du=f'{up} - ({u:.13g} mm + {shift[axis][axis]:g}*({primary}-{base} mm))'
        height_coeff=shift[2][3] if section=='Czapka' else shift[2][2]
        height_primary='RP_WysokoscCzapki' if section=='Czapka' else 'RP_WysokoscDolu';height_base=662.99 if section=='Czapka' else 488.99
        dh=f'{hp} - ({h:.13g} mm + {height_coeff:g}*({height_primary}-{height_base} mm))'
        delta=['0 mm','0 mm',dh];delta[axis]=du
        mounts.append(dict(id=i,kind='handle',side=side,section=section,position=position if axis==0 else 'Srodkowy',delta=delta))
    mount_by={x['id']:x for x in mounts}
    def nearest(c,kind,side=None):
        candidates=[m for m in mounts if m['kind']==kind and (side is None or m['side']==side)]
        return min(candidates,key=lambda m:sum((center(m['id'])[k]-c[k])**2 for k in range(3)))['id']
    operations=[];latch_cuts={x['cut_id']:rows[x['tool_part']]['parent'] for x in plan['cut_replacements']}
    for row in details:
        i=row['id']
        if i not in PANELS and not rows[i]['name'].startswith('EG-'):continue
        original={f['id']:f for f in rows[i]['features'] if 'id' in f}
        for index,f in enumerate(row['features']):
            fid=f.get('id');c=f.get('profile_center_world_mm')
            if not c or index==0 or original[fid]['operation']!='Z_SUBTRACT':continue
            if fid in latch_cuts:owner=latch_cuts[fid]
            elif i in PANELS:owner=nearest(c,'handle',PANELS[i][1])
            else:owner=nearest(c,'latch','Przod' if c[1]<-825.5 else 'Tyl')
            operations.append(dict(part=i,feature_index=index,source_feature=fid,mount=owner,depth=rows[i]['depth']+1))
    assert len([x for x in operations if mount_by[x['mount']]['kind']=='handle'])==8
    assert len(operations)==56
    def label(i):
        row=rows[i];ancestry=path(i);b=box(i)
        section='czapka' if 115 in ancestry or 247 in ancestry else 'korpus'
        if i in (115,116):return 'RockPro | '+('Czapka zdejmowana' if i==115 else 'Korpus dolny')
        if i in mount_by:
            m=mount_by[i];pos=['lewy','środkowy','prawy'][m['rank']+1] if m['kind']=='latch' else PL.get(m.get('position'),m.get('position','')).lower()
            return ('Zamek L905/915' if m['kind']=='latch' else 'Uchwyt H7159')+' — '+PL[m['section']]+' — '+PL[m['side']]+' — '+pos
        owner=next((x for x in ancestry if x in mount_by),None)
        if owner:
            m=mount_by[owner];siblings=[x['id'] for x in inventory if x['type']=='Z_ELEMENT_PART' and owner in path(x['id'])]
            return label(owner)+' — podczęść '+str(siblings.index(i)+1).zfill(2)+' (rola do identyfikacji)' if row['type']=='Z_ELEMENT_PART' else label(owner)+' — element montażowy'
        if i in PANELS:return 'Sklejka — '+PL[PANELS[i][0]]+' — '+PL[PANELS[i][1]]
        if row['name']=='konstrukcja':return 'Płyty sklejki — '+section
        if i in (247,263):return 'Wkłady pomocnicze — '+section+' — położenie odsunięte'
        if i==774:return 'Koła i podpory — korpus — spód'
        wheel=next((a for a in ancestry if a in (775,842,859,926)),None)
        if wheel:
            wc=center(wheel);position=('przód' if wc[1]<-825.5 else 'tył')+'/'+('lewa' if wc[0]<-1020.5 else 'prawa')
            if i==wheel:return 'Koło jezdne — korpus — spód — '+position+' (SKU do potwierdzenia)'
            return 'Element koła — korpus — spód — '+position+' — ID '+str(i)+' (rola podczęści do identyfikacji)'
        if i in (943,946):return 'Podpora kół — korpus — spód — '+('przód' if center(i)[1]<-825.5 else 'tył')
        if i in (10933,10936):return 'Wkład podpierający — korpus — '+('lewa' if center(i)[0]<-1020.5 else 'prawa')+' (typ do potwierdzenia)'
        if i==10907:return 'Pianka — korpus — dno'
        if not b:return 'Grupa pomocnicza — '+section+' — '+row['name']+' (pusta)'
        c=center(i);sx='lewa' if c[0]<-1020.5 else 'prawa';sy='przód' if c[1]<-825.5 else 'tył'
        side=PL[wall(i)]
        size=[b[k+3]-b[k] for k in range(3)]
        source=row['name']
        if source.startswith('EG-'):
            role='Profile łączenia' if source.startswith('EG-0500') else 'Profile krawędziowe'
            if row['type']!='Z_ELEMENT_PART':return role+' '+source+' — '+section
            midpoint=-416.90846002624 if section=='czapka' else -1001.54828408674
            orientation='pionowy' if size[2]>max(size[:2]) else ('górny' if c[2]>midpoint else 'dolny')
            return ('Profil łączenia ' if source.startswith('EG-0500') else 'Profil krawędziowy ')+source+' — '+section+' — '+side+' — '+orientation+' / '+sx+' / '+sy
        if source=='C1341-30-33':return 'Narożnik kulowy C1341-30-33 — '+section+(' — '+sy+'/'+sx+' — '+('góra' if section=='czapka' else 'dół') if row['type']=='Z_ELEMENT_PART' else ' — komplet')
        if source=='40404':return 'Okucie wzmacniające 40404 — '+section+' — '+sy+'/'+sx+' — '+('góra' if c[2]>(-416.908 if section=='czapka' else -1001.548) else 'dół')
        if source=='L905-915':return 'Zamki L905/915 — '+section+' — przód i tył'
        if 'Inżynieria' in source:return 'Logo klienta — '+section+' — '+side
        if any('Inżynieria' in rows[a]['name'] for a in ancestry):return 'Element logo — '+section+' — '+side+' — ID '+str(i)
        if source.lower().startswith(('pian','piana','pianka')):return 'Wkłady piankowe — '+section+' — '+side
        if i in (174,198):return 'Płyty sklejki — '+section
        if row['type']=='Z_ELEMENT_ASSEMBLY' and source in ('przód','tył','lewa','prawa','góra','dół'):return 'Ściana — '+section+' — '+source
        role='Wkład/docisk' if i in {x['id'] for x in plan['parts'] if x['structural']} else 'Element'
        return role+' — '+section+' — '+side+' / '+sx+' — ID '+str(i)+' ('+source+'; rola do potwierdzenia)'
    names=[dict(id=x['id'],name=label(x['id'])) for x in inventory if x['id']!=1]
    source=PROJECT/'04_Snapshoty/RockPro_Hisense85_r001_sprawdzone_IC2027.ics'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!='bc4394ab6a0907b83d28d26b45fdde896b842b3542a8f2b1f69a079419a7a82a':raise ValueError('Verified snapshot changed')
    q=dict(contract='rockpro-tv-mounting-v2',expected_pid=18584,source=str(source),sha256=digest,
           output=str(PROJECT/'03_CAD/Do_sprawdzenia/RockPro_Hisense85_parametryczny_r002_montaz_IC2027.ics'),
           aliases=built['part_id_map'],parameters=params,mounts=mounts,operations=operations,names=names,
           inventory=inventory,parts=plan['parts'],rebuild_profiles=[222,225,235,238],
           tests=[dict(name='zamki_i_uchwyty_niezaleznie',values={'RP_ZamkiPrzod_Rozstaw':690,'RP_ZamkiPrzod_Przesuniecie':22,'RP_ZamkiTyl_Rozstaw':720,'RP_ZamkiTyl_Przesuniecie':-18,'RP_UchwytyPrzod_Rozstaw':1400,'RP_UchwytyTyl_Przesuniecie':17,'RP_UchwytKorpusPrzodLewy_Wysokosc':220,'RP_UchwytCzapkaPrawa_Pozycja':210,'RP_UchwytKorpusLewa_Wysokosc':390}),
                  dict(name='zamki_pion_i_drugi_uchwyt',values={'RP_ZamkiPrzod_Pion':2,'RP_ZamkiTyl_Pion':-2,'RP_UchwytKorpusPrzodPrawy_Pozycja':1740,'RP_UchwytCzapkaLewa_Wysokosc':325}),
                  dict(name='gabaryty_i_montaz',values={'RP_SzerokoscSkrzyni':2123,'RP_GlebokoscSkrzyni':402,'RP_WysokoscDolu':518.99,'RP_WysokoscCzapki':712.99,'RP_ZamkiPrzod_Rozstaw':780,'RP_UchwytyTyl_Rozstaw':1550})])
    (EVIDENCE/'mounting-plan.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(new_parameters=len(params),mounts=len(mounts),operations=len(operations),labels=len(names))))

if __name__=='__main__':main()
