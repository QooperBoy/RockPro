"""Source-pinned chest plan: keep SKU geometry, bind cutouts and compartment slots."""
import json
from pathlib import Path
from prepare_tv_parametric import compose_rotation
from prepare_wing_compact import mm, add, scale, difference

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'artifacts/kufer-20261030'
PRIMARY=['RP_Szerokosc','RP_Glebokosc','RP_WysokoscKorpusu','RP_WysokoscPokrywy']
BASE=[1230.,580.,572.,100.]
XL,YF,ZF=779.7209932619194,-705.787077546102,-632.8666899099411

def main():
    inspection=json.loads((E/'inspect-01/result.json').read_text(encoding='utf-8'))
    rows=inspection['rows'];by={r['id']:r for r in rows}
    detail=json.loads((E/'details-01/result.json').read_text(encoding='utf-8'))['rows']
    def path(i):
        a=[]
        while i>=0:a.append(i);i=by[i]['parent']
        return a[::-1]
    def box(i):
        r=by[i]
        if 'bounds_m' in r:
            b=r['bounds_m'];m=r['world_matrix_m']
            pts=[[1000*(m[12+j]+sum(b[k+3*((v>>k)&1)]*m[k*4+j] for k in range(3))) for j in range(3)] for v in range(8)]
            return [min(p[k] for p in pts) for k in range(3)]+[max(p[k] for p in pts) for k in range(3)]
        c=[box(x['id']) for x in rows if x['parent']==i]
        return [min(b[k] for b in c) for k in range(3)]+[max(b[k+3] for b in c) for k in range(3)]
    boxes={i:box(i) for i in by}
    def center(i):return [(boxes[i][k]+boxes[i][k+3])/2 for k in range(3)]
    def lid(i):return 1458 in path(i)
    def wall(i):
        c=center(i)
        return min([(abs(c[0]-XL),'lewa'),(abs(c[0]-XL-1230),'prawa'),(abs(c[1]-YF),'przód'),(abs(c[1]-YF-580),'tył')])[1]
    partitions=[1143,5568,5582,5596];supports=[5470,5496,5520,5544]
    panels=[1461,1465,1473,1481,1485,1663,1671,1683,1695,1703]
    material=panels+partitions+supports+[2520,2649]+[r['id'] for r in rows if r['name'].startswith('EG-') and r['type']=='Z_ELEMENT_PART']
    parts=[r for r in rows if r['type']=='Z_ELEMENT_PART']
    assert len(parts)==356 and len(material)==44
    rebuild=[i for i in material if all(f.get('extrude') and f.get('curves') for f in by[i]['features'])]
    # All other nodes inside a catalog unit inherit that complete unit's pose.
    units={r['id'] for r in rows if r['depth']==3 and r['parent'] in (1497,1568,1581,1594,1625,1707,1778,1791,1866,1901)}|{5421,2523,2577,2652,2706}
    units.discard(5434);units.add(5434)
    params=[]
    def parameter(n,expr,note):
        params.append(dict(name=n,expression=mm(expr) if isinstance(expr,(int,float)) else expr,notes=note))
    for n,v,label in zip(PRIMARY,BASE,['Szerokość X obrysu sklejki','Głębokość Y obrysu sklejki','Wysokość korpusu od spodu dna do złącza','Wysokość pokrywy od dolnej krawędzi sklejki do dachu']):
        parameter(n,v,label+'. Jednostka mm; bez wystających okuć i kół. Wzorcowe wartości 1230/580/572/100. Nazwa pliku nie określa tych wymiarów. Zalecana na start zmiana do +40 mm; sprawdź wnętrze i montaż.')
    parameter('RP_UniesieniePokrywy',0,'Rozsunięcie poglądowe pokrywy w osi Z; 0 = zamknięta. Nie symuluje obrotu zawiasów. Próbna wartość 160 mm.')
    for code in ('Przod','Tyl'):
        parameter('RP_Okucia'+code+'_Rozstaw','RP_Szerokosc - 350 mm','Rozstaw dwóch zamków (przód) albo zawiasów 27083 (tył), między środkami. Obie połówki i wycięcia mają wspólną kotwę. Zachowaj min. 100 mm zapasu od narożników; liczba pozostaje jak we wzorcu.')
        parameter('RP_Okucia'+code+'_Przesuniecie',0,'Przesunięcie całego rzędu '+code+' w osi X; mm. Próbna korekta do 10 mm, z kontrolą narożników.')
    for w in ('Przod','Tyl','Lewa','Prawa'):
        ids=[i for i in units if by[i]['name']=='H7159' and wall(i)=={'Przod':'przód','Tyl':'tył','Lewa':'lewa','Prawa':'prawa'}[w]]
        axis=0 if w in ('Przod','Tyl') else 1;c=[center(i) for i in ids];spread=max(x[axis] for x in c)-min(x[axis] for x in c)
        parameter('RP_Uchwyty'+w+'_Rozstaw',f'{PRIMARY[axis]} - {mm(BASE[axis]-spread)}','Rozstaw dwóch uchwytów na ścianie '+w+'; mm, symetrycznie wokół środka ściany. Zachowaj min. 100 mm od skraju. Wycięcia podążają za uchwytami.')
        parameter('RP_Uchwyty'+w+'_Przesuniecie',0,'Przesunięcie środka pary uchwytów '+w+' w osi ściany; mm. Nie zmienia liczby ani wymiaru katalogowego uchwytów.')
        parameter('RP_Uchwyty'+w+'_Wysokosc',sum(x[2]-ZF for x in c)/len(c),'Wysokość środka pary uchwytów '+w+' od spodu sklejki dna; mm. Zachowaj obrys okucia poza profilami, zamkami i zawiasami.')
    parameter('RP_UchwytNarozny_Pozycja','RP_Szerokosc/2','Pozycja uchwytu H2026 od lewego skraju sklejki; mm. Wycięcia dachu, ściany przedniej i profilu podążają razem.')
    parameter('RP_OslonaEtykiety_Pozycja','RP_Szerokosc/2','Pozycja osłony etykiety 88001D na dachu od lewego skraju; mm. Związana z własnym wycięciem.')
    for k,i in enumerate(partitions,1):parameter(f'RP_Przegroda{k}_Pozycja',f'RP_Szerokosc*{(center(i)[0]-XL)/1230:.14g}',f'Pozycja środka przegrody {k} od lewej krawędzi sklejki, mm. Domyślnie proporcjonalna do szerokości. Powiązane gniazda listew podpierających podążają razem. Sprawdź odstępy między przegrodami.')
    parameter('RP_Kola_OdsuniecieX',154,'Odsunięcie środka gniazd piętrowania od bocznych krawędzi, mm. Koła i ich deski mają to samo przesunięcie co gniazda; zachowany źródłowy offset kontaktu koła. Zalecane 140–180 mm.')
    parameter('RP_Kola_OdsuniecieY',82.8,'Odsunięcie osi gniazd od przodu/tyłu, mm. Wspólna korekta czterech kół i czterech gniazd. Zalecane 75–100 mm, bez zmiany SKU.')
    delta=[difference(n,mm(b)) for n,b in zip(PRIMARY,BASE)]
    def snap(v,lo,span,margin):return 0 if v-lo<margin else 1 if lo+span-v<margin else .5
    shifts={1:['0 mm']*3};growth={};dimensions={}
    for r in rows[1:]:
        i=r['id'];c=center(i);b=boxes[i];size=[b[k+3]-b[k] for k in range(3)]
        own=next((a for a in path(i)[:-1] if a in units),None)
        if own:shifts[i]=shifts[own][:];continue
        z=add(delta[2],scale(snap(c[2],ZF+580,100,25),delta[3]),'RP_UniesieniePokrywy') if lid(i) else scale(snap(c[2],ZF,572,140),delta[2])
        shift=[scale(snap(c[0],XL,1230,220),delta[0]),scale(snap(c[1],YF,580,100),delta[1]),z]
        if i in material:
            g=[[0.]*4 for _ in range(3)]
            if size[0]>615:g[0][0]=1
            if size[1]>290:g[1][1]=1
            if size[2]>(50 if lid(i) else 286):g[2][3 if lid(i) else 2]=1
            growth[i]=g;rot=compose_rotation(r['features'][0]['matrix_m'],r['world_matrix_m'])
            dimensions[i]=[g[max(range(3),key=lambda k:abs(rot[a*4+k]))] for a in range(3)]
            for j in range(3):
                if any(g[j]):shift[j]=add(delta[2],'RP_UniesieniePokrywy') if j==2 and lid(i) else '0 mm'
            for a in range(3):
                j=max(range(3),key=lambda k:abs(rot[a*4+k]))
                if rot[a*4+j]<-.9:shift[j]=add(shift[j],*[scale(g[j][k],delta[k]) for k in range(4)])
        shifts[i]=shift
    mounts=[]
    for i in units:
        r=by[i];c=center(i);w=wall(i);shift=shifts[i]
        if r['name'].startswith(('17251S_','27083_')):
            code='Przod' if w=='przód' else 'Tyl';rank=-.5 if c[0]<XL+615 else .5
            shift[0]=difference(add(mm(XL),scale(.5,'RP_Szerokosc'),scale(rank,'RP_Okucia'+code+'_Rozstaw'),'RP_Okucia'+code+'_Przesuniecie'),mm(c[0]));shift[2]=add(delta[2],'RP_UniesieniePokrywy' if lid(i) else '0 mm')
            mounts.append(dict(id=i,kind='joint',wall=w))
        elif r['name']=='H7159':
            code={'przód':'Przod','tył':'Tyl','lewa':'Lewa','prawa':'Prawa'}[w];axis=0 if code in ('Przod','Tyl') else 1;rank=-.5 if c[axis]<(XL+615 if axis==0 else YF+290) else .5
            shift[axis]=difference(add(mm(XL if axis==0 else YF),scale(.5,PRIMARY[axis]),scale(rank,'RP_Uchwyty'+code+'_Rozstaw'),'RP_Uchwyty'+code+'_Przesuniecie'),mm(c[axis]));shift[2]=difference('RP_Uchwyty'+code+'_Wysokosc',mm(c[2]-ZF))
            mounts.append(dict(id=i,kind='handle',wall=w))
        elif i==5421:shift[0]=difference('RP_UchwytNarozny_Pozycja',mm(c[0]-XL));mounts.append(dict(id=i,kind='edgehandle',wall='przód'))
        elif i==5434:shift[0]=difference('RP_OslonaEtykiety_Pozycja',mm(c[0]-XL));mounts.append(dict(id=i,kind='label',wall='dach'))
        if r['name']=='W0968z' or i in (2523,2577,2652,2706):
            left=c[0]<XL+615;front=c[1]<YF+290
            shift[0]=difference('RP_Kola_OdsuniecieX',mm(154)) if left else add(delta[0],difference(mm(154),'RP_Kola_OdsuniecieX'))
            shift[1]=difference('RP_Kola_OdsuniecieY',mm(82.8)) if front else add(delta[1],difference(mm(82.8),'RP_Kola_OdsuniecieY'))
            if r['name']=='W0968z':mounts.append(dict(id=i,kind='socket',wall='dach'))
    for k,i in enumerate(partitions,1):shifts[i][0]=difference(f'RP_Przegroda{k}_Pozycja',mm(center(i)[0]-XL))
    for i in (2520,2649):shifts[i][0]=difference('RP_Kola_OdsuniecieX',mm(154)) if center(i)[0]<XL+615 else add(delta[0],difference(mm(154),'RP_Kola_OdsuniecieX'))
    for r in rows[1:]:
        own=next((a for a in path(r['id'])[:-1] if a in units),None)
        if own:shifts[r['id']]=shifts[own][:]
    ops=[]
    for r in detail:
        i=r['id'];fs={f.get('id'):f for f in by[i]['features']}
        for f in r['features']:
            fid=f.get('id');c=f.get('profile_center_world_mm')
            if fid not in fs or fs[fid].get('operation')!='Z_SUBTRACT' or not c:continue
            name=fs[fid]['name'];owner=None;shift=shifts[i][:]
            kind='handle' if 'H7159' in name else 'joint' if '17251S' in name else 'edgehandle' if 'H2026' in name else 'socket' if 'W0968' in name else 'label' if '88001D' in name else None
            if kind:
                candidates=[m for m in mounts if m['kind']==kind and (kind in ('edgehandle','socket','label') or m['wall']==wall(i))]
                owner=min(candidates,key=lambda m:sum((center(m['id'])[k]-c[k])**2 for k in range(3)))['id'];shift=shifts[owner][:]
                if kind=='joint':shift[2]=add(delta[2],'RP_UniesieniePokrywy' if lid(i) else '0 mm')
            elif i in partitions:
                shift=shifts[i][:];shift[1]=scale(snap(c[1],YF,580,100),delta[1]);shift[2]=scale(1 if c[2]>ZF+400 else 0,delta[2])
            elif i in supports:
                near=min(partitions,key=lambda x:abs(center(x)[0]-c[0]));shift=shifts[i][:]
                shift[0]=shifts[near][0] if abs(center(near)[0]-c[0])<12 else scale((c[0]-XL)/1230,delta[0])
            ops.append(dict(part=i,id=fid,shift=shift,mount=owner,depth=by[i]['depth']+1,bind=True,reserved=False))
    names=[]
    for r in rows[1:]:
        i=r['id'];section='pokrywa' if lid(i) else 'korpus';c=center(i);pos=('lewa' if c[0]<XL+615 else 'prawa')+'/'+('przód' if c[1]<YF+290 else 'tył');w=wall(i)
        m=next((m for m in mounts if m['id']==i),None)
        own=next((a for a in path(i)[:-1] if a in units),None)
        if i in (1458,1660):label='RockPro | '+('Pokrywa' if lid(i) else 'Korpus z przegrodami')
        elif i in partitions:label=f'Przegroda {partitions.index(i)+1} — korpus — od lewej'
        elif i in supports:label='Listwa podpierająca przegrody — korpus — '+w+' — '+('górna' if c[2]>ZF+350 else 'dolna')
        elif i in panels:label='Sklejka 9 mm — '+section+' — '+('dach' if i==1485 else 'dno' if i==1703 else w)
        elif i in (2520,2649):label='Deska mocowania kół 18 mm — spód — '+pos
        elif i in (2523,2577,2652,2706):label='Koło '+r['name']+' — spód korpusu — '+pos
        elif r['name'].startswith('2605_'):label='Zawias 2605 — '+section+' — tył — środkowy'
        elif r['name'] in ('41076','B1121'):label=('Narożnik ' if r['name']=='41076' else 'Wzmocnienie narożne ')+r['name']+' — '+section+' — '+pos
        elif m:label={'joint':'Zamek 17251S' if w=='przód' else 'Zawias 27083','handle':'Uchwyt H7159','edgehandle':'Uchwyt narożny H2026','socket':'Gniazdo piętrowania W0968z','label':'Osłona etykiety 88001D'}[m['kind']]+' — '+section+' — '+w+' — '+pos
        elif own:label='Podczęść '+by[own]['name']+' — '+section+' — '+wall(own)+' — '+pos+' — ID '+str(i)+' (rola do identyfikacji)'
        elif r['name'].startswith('EG-'):label='Profil '+r['name']+' — '+section+' — '+w+' — '+pos
        else:
            roles={'Lid_Block':'Płyty pokrywy','Bottom_Block':'Płyty korpusu','Frame':'Rama profili i okuć','Corners':'Narożniki','Profiles':'Profile','Strips':'Profile złącza','Braces':'Wzmocnienia','Dishes':'Gniazda i osłona etykiety','Locks':'Zamki','Hinges':'Zawiasy','Handles':'Uchwyty','Interior':'Przegrody i podpory','Wheels':'Koła i deski montażowe','Right':'Ściana prawa','Left':'Ściana lewa','Front':'Ściana przednia','Back':'Ściana tylna','Top':'Dach','Bot':'Dno'}
            label=roles.get(r['name'],'Element '+r['name']+' (rola do identyfikacji)')+' — '+section+' — '+pos+' — ID '+str(i)
        names.append(dict(id=i,name=label))
    q=dict(contract='rockpro-kufer-parametric-v1',expected_pid=18584,source=inspection['source'],sha256='d7cf0bc7734d8a862f44909b04b4be9bcae1dd3a9f917fab5ea1bf9288abee1d',
           output=str(ROOT.parents[2]/'projekty/Kufer_parametryczny_20261030/03_CAD/Do_sprawdzenia/RockPro_Kufer_r001_IC2027.ics'),inventory=rows,parameters=params,primary=PRIMARY,primary_base=BASE,rebuild=rebuild,green_parts=panels+partitions+supports,
           dimensions=[dict(part=i,coefficients=c) for i,c in dimensions.items()],nodes=[dict(id=r['id'],parent=r['parent'],depth=r['depth'],shift=shifts[r['id']]) for r in rows[1:] if not any(a in units for a in path(r['id'])[:-1])],units=sorted(units),
           parts=[dict(id=r['id'],owner=next((a for a in path(r['id']) if a in units),r['id']),growth=growth.get(r['id'],[[0]*4 for _ in range(3)])) for r in parts],operations=ops,names=names,
           tests=[dict(name='gabaryty',values=dict(RP_Szerokosc=1270,RP_Glebokosc=610,RP_WysokoscKorpusu=602,RP_WysokoscPokrywy=110)),dict(name='montaz',values=dict(RP_OkuciaPrzod_Rozstaw=830,RP_OkuciaTyl_Przesuniecie=8,RP_UchwytyPrzod_Wysokosc=190,RP_UchwytyLewa_Rozstaw=300,RP_Kola_OdsuniecieX=164,RP_Kola_OdsuniecieY=87.8)),dict(name='przegrody_i_pokrywa',values=dict(RP_Przegroda2_Pozycja=470,RP_UniesieniePokrywy=160))])
    (E/'plan.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
    print({k:len(q[k]) for k in ('parameters','parts','rebuild','dimensions','units','nodes','operations')})

if __name__=='__main__':main()
