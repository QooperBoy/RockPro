"""Pinned 9U rack: fixed 19-inch mounting width, two independently removable lids."""
import json
from pathlib import Path
from prepare_tv_parametric import compose_rotation
from prepare_wing_compact import mm,add,scale,difference

ROOT=Path(__file__).resolve().parents[1];E=ROOT/'artifacts/rack-20261030'
PRIMARY=['RP_GlebokoscKorpusu','RP_WysokoscObudowy','RP_GlebokoscPokrywyPrzod','RP_GlebokoscPokrywyTyl','RP_KorektaPokrywyPrzod']
BASE=[577.,430.,88.,88.,0.]

def main():
    inspection=json.loads((E/'inspect-01/result.json').read_text(encoding='utf-8'));rows=inspection['rows'];by={r['id']:r for r in rows}
    details=json.loads((E/'details-01/result.json').read_text(encoding='utf-8'))['rows']
    def path(i):
        a=[]
        while i>=0:a.append(i);i=by[i]['parent']
        return a[::-1]
    def box(i):
        r=by[i]
        if 'bounds_m' in r:
            b=r['bounds_m'];m=r['world_matrix_m'];p=[[1000*(m[12+j]+sum(b[k+3*((v>>k)&1)]*m[k*4+j] for k in range(3))) for j in range(3)] for v in range(8)]
            return [min(t[k] for t in p) for k in range(3)]+[max(t[k] for t in p) for k in range(3)]
        c=[box(r['id']) for r in rows if r['parent']==i];c=[v for v in c if v]
        return [min(v[k] for v in c) for k in range(3)]+[max(v[k+3] for v in c) for k in range(3)] if c else None
    boxes={i:box(i) for i in by}
    def center(i):return [(boxes[i][k]+boxes[i][k+3])/2 for k in range(3)]
    XL,YF,ZF=boxes[719][:3];YB=YF+577;XR=XL+538
    def section(i):return 'przód' if 2646 in path(i) else 'tył' if 817 in path(i) else 'korpus'
    def wall(i):return 'lewa' if center(i)[0]<XL+269 else 'prawa'
    panels=[711,715,719,723,666,670,674,678,682,2649,2653,2657,2661,2665]
    pads=[193,204,215,226];rails=[189,200,211,222]
    material=panels+pads+[r['id'] for r in rows if r['type']=='Z_ELEMENT_PART' and r['name'].startswith('EG-')]+[1636]
    parts=[r for r in rows if r['type']=='Z_ELEMENT_PART'];assert len(parts)==451
    rebuild=[i for i in material if all(f.get('extrude') and f.get('curves') for f in by[i]['features'])]
    units=set(rails)|{r['id'] for r in rows if r['type']=='Z_ELEMENT_ASSEMBLY' and r['name'] in ('H7159','17251S','17251S_2','37033','37034','41046','B1121')}|{3215,3219,3221,3223}
    units={i for i in units if not any(a in units for a in path(i)[:-1])}
    params=[]
    def parameter(n,e,note):params.append(dict(name=n,expression=mm(e) if isinstance(e,(int,float)) else e,notes=note))
    for n,v,note in zip(PRIMARY,[577.,430.,88.,88.,7.],[
        'Długość otwartego korpusu w osi Y, między przednią i tylną krawędzią sklejki. Bez pokryw. Wzorzec 577 mm; próba 617 mm. Szerokość pozostaje zgodna z montażem 19 cali.',
        'Wysokość obrysu sklejki w osi Z, bez kół i wystających okuć. Wzorzec 430 mm; próba 460 mm. Szyny zachowują 9U i długość 410 mm; większa wysokość dodaje wolną przestrzeń u góry, nie jednostki U.',
        'Głębokość przedniej zdejmowanej pokrywy od jej złącza do zewnętrznej sklejki; mm. Wzorzec 88, próba 108. Wydłuża się na zewnątrz; złącze pozostaje na korpusie.',
        'Głębokość tylnej zdejmowanej pokrywy; mm. Wzorzec 88, próba 98. Zachowuje źródłowe pasowanie profili i szerokość racka.',
        'Naprawa źródła: sklejka przedniej pokrywy była 7 mm niższa od ramy, a połówki jej zamków o 3.5 mm za nisko. Domyślnie 7 mm wyrównuje sklejkę i zamki; 0 pokazuje geometrię źródłową. Wycięcia źródła były już na prawidłowej wysokości.']):parameter(n,v,note)
    for code in ('Przod','Tyl'):
        parameter('RP_Wysuniecie'+code,0,'Rozsunięcie pokrywy '+code+' wzdłuż osi Y; dodatnie na zewnątrz, mm. 0 = zamknięta, próba 160. Nie zmienia rozmiaru pokrywy.')
        parameter('RP_Zamki'+code+'_Wysokosc','RP_WysokoscObudowy/2','Wysokość wspólnej osi pary zamków '+code+' od spodu sklejki dna, mm. Obie połówki oraz wycięcia ścian/profili/podkładek podążają razem. Zachowaj min. 90 mm od góry i dołu.')
    for code in ('Lewa','Prawa'):
        ids=[i for i in units if by[i]['name']=='H7159' and wall(i)==('lewa' if code=='Lewa' else 'prawa')];c=[center(i) for i in ids]
        spread=max(x[1] for x in c)-min(x[1] for x in c);offset=sum(x[1] for x in c)/len(c)-YF-288.5
        parameter('RP_Uchwyty'+code+'_Rozstaw',spread,'Rozstaw dwóch uchwytów na ścianie '+code+' wzdłuż głębokości, mm. Źródłowa liczba 2 pozostaje stała; zachowaj zapas od zamków i profili.')
        parameter('RP_Uchwyty'+code+'_Pozycja',f'RP_GlebokoscKorpusu/2 + {mm(offset)}','Pozycja środka pary od przedniej krawędzi korpusu, mm. Przesuwa kompletne uchwyty i ich wycięcia.')
        parameter('RP_Uchwyty'+code+'_Wysokosc','RP_WysokoscObudowy/2','Wysokość środka pary uchwytów od spodu dna, mm. Nie zmienia rozmiaru uchwytów.')
    parameter('RP_SzynyPrzod_Odsuniecie',0,'Przesunięcie przedniej pary szyn 9U wraz z podkładkami w osi Y, mm; dodatnie w głąb korpusu. Rozstaw 19 cali i perforacja pozostają stałe; próbna korekta 5 mm.')
    parameter('RP_SzynyTyl_Odsuniecie',0,'Przesunięcie tylnej pary szyn 9U w osi Y, mm. Uwaga: wycięcia pod zamki pozostają przy zamkach, a podkładki przesuwają się z szynami.')
    parameter('RP_Kola_PrzesuniecieX',0,'Symetryczna korekta kół i gniazd w osi X, mm: dodatnia przesuwa lewą parę do środka, prawą do środka. Próba 5 mm; zachowaj montaż do deski.')
    parameter('RP_Kola_PrzesuniecieY',0,'Symetryczna korekta kół i gniazd w osi Y, mm: dodatnia zbliża przednią/tylną parę do środka. Próba 5 mm. Rozmiary katalogowe pozostają stałe.')
    d=[difference(n,mm(v)) for n,v in zip(PRIMARY,BASE)]
    def fraction(v,lo,size,margin):return 0 if v-lo<margin else 1 if lo+size-v<margin else .5
    shifts={1:['0 mm']*3};growth={};dims={}
    for r in rows[1:]:
        i=r['id'];b=boxes[i]
        if not b:shifts[i]=['0 mm']*3;continue
        own=next((a for a in path(i)[:-1] if a in units),None)
        if own:shifts[i]=shifts[own][:];continue
        c=center(i);sec=section(i);sz=[b[k+3]-b[k] for k in range(3)]
        y=scale(fraction(c[1],YF,577,100),d[0]) if sec=='korpus' else '0 mm'
        if sec=='przód':y=add(scale(-fraction(-c[1],-YF+7,88,20),d[2]),scale(-1,'RP_WysunieciePrzod'))
        elif sec=='tył':y=add(d[0],scale(fraction(c[1],YB+7,88,20),d[3]),'RP_WysuniecieTyl')
        shift=['0 mm',y,scale(fraction(c[2],ZF,430,70),d[1])]
        if i in material:
            g=[[0.]*5 for _ in range(3)]
            if sec=='korpus' and sz[1]>280:g[1][0]=1
            if sec!='korpus' and sz[1]>44:g[1][2 if sec=='przód' else 3]=1
            if sz[2]>200 and i not in pads:g[2][1]=1
            if i in (2649,2661,2665):g[2][4]=1
            growth[i]=g;rot=compose_rotation(r['features'][0]['matrix_m'],r['world_matrix_m'])
            dims[i]=[g[max(range(3),key=lambda k:abs(rot[a*4+k]))] for a in range(3)]
            for j in range(3):
                if any(g[j]):
                    if j==1:shift[j]='0 mm' if sec=='korpus' else add(scale(-1,d[2]),scale(-1,'RP_WysunieciePrzod')) if sec=='przód' else add(d[0],'RP_WysuniecieTyl')
                    else:shift[j]='0 mm'
            if i==2653:shift[2]=add(d[1],d[4])
            for a in range(3):
                j=max(range(3),key=lambda k:abs(rot[a*4+k]))
                if rot[a*4+j]<-.9:shift[j]=add(shift[j],*[scale(g[j][k],d[k]) for k in range(5)])
            if i in pads:shift[2]='0 mm'
        shifts[i]=shift
    mounts=[]
    for i in units:
        c=center(i);sec=section(i);name=by[i]['name'];shift=shifts[i]
        if name.startswith('17251'):
            code='Przod' if c[1]<YF+288.5 else 'Tyl'
            shift[1]='0 mm' if code=='Przod' else d[0]
            if sec!='korpus':shift[1]=add(shift[1],scale(-1 if code=='Przod' else 1,'RP_Wysuniecie'+code))
            shift[2]=difference('RP_Zamki'+code+'_Wysokosc',mm(215))
            if sec=='przód':shift[2]=add(shift[2],scale(.5,d[4]))
            mounts.append(dict(id=i,kind='joint',end=code,wall=wall(i)))
        elif name=='H7159':
            code='Lewa' if wall(i)=='lewa' else 'Prawa';rank=-.5 if c[1]<YF+288.5 else .5
            shift[1]=difference(add(mm(YF),'RP_Uchwyty'+code+'_Pozycja',scale(rank,'RP_Uchwyty'+code+'_Rozstaw')),mm(c[1]));shift[2]=difference('RP_Uchwyty'+code+'_Wysokosc',mm(215))
            mounts.append(dict(id=i,kind='handle',wall=wall(i)))
        elif i in (3215,3219,3221,3223) or name in ('37033','37034'):
            left=c[0]<XL+269;front=c[1]<YF+288.5
            shift[0]=scale(1 if left else -1,'RP_Kola_PrzesuniecieX');shift[1]=add(scale(0 if front else 1,d[0]),scale(1 if front else -1,'RP_Kola_PrzesuniecieY'))
            if i in (3215,3219,3221,3223):mounts.append(dict(id=i,kind='socket',wall='dach'))
        elif i in rails:
            front=c[1]<YF+288.5;shift[1]=add(scale(0 if front else 1,d[0]),'RP_Szyny'+('Przod' if front else 'Tyl')+'_Odsuniecie');shift[2]='0 mm'
    for i in pads:
        c=center(i);front=c[1]<YF+288.5;shifts[i][1]=add(scale(0 if front else 1,d[0]),'RP_Szyny'+('Przod' if front else 'Tyl')+'_Odsuniecie')
    for r in rows[1:]:
        own=next((a for a in path(r['id'])[:-1] if a in units),None)
        if own:shifts[r['id']]=shifts[own][:]
    ops=[]
    for r in details:
        i=r['id'];fs={f.get('id'):f for f in by[i]['features']}
        for f in r['features']:
            fid=f.get('id');c=f.get('profile_center_world_mm')
            if fid not in fs or fs[fid].get('operation')!='Z_SUBTRACT' or not c:continue
            sec=section(i);name=fs[fid]['name'];kind='socket' if i==715 else 'handle' if 'uchwyt' in name.lower() or 'H7165' in name else 'joint'
            candidates=[m for m in mounts if m['kind']==kind and (kind=='socket' or m['wall']==wall(i))]
            owner=min(candidates,key=lambda m:sum((center(m['id'])[k]-c[k])**2 for k in range(3)))['id'];shift=shifts[owner][:]
            if kind=='joint':
                code='Przod' if c[1]<YF+288.5 else 'Tyl';shift[1]=add(scale(0 if code=='Przod' else 1,d[0]),scale(-1,'RP_WysunieciePrzod') if sec=='przód' else 'RP_WysuniecieTyl' if sec=='tył' else '0 mm');shift[2]=difference('RP_Zamki'+code+'_Wysokosc',mm(215))
            if fid in (3240,3242):
                # Same 130x78 contour as the opposite side, but source placement
                # was offset. Keep the contour and its 0.2-mm template Z datum.
                shift[1]=add(shift[1],mm(center(owner)[1]-c[1]));shift[2]=add(shift[2],mm(center(owner)[2]+.2-c[2]))
            ops.append(dict(part=i,id=fid,shift=shift,mount=owner,depth=by[i]['depth']+1,bind=True,reserved=False))
    names=[]
    groupnames={'Base':'Korpus racka 9U','Back':'Pokrywa zdejmowana','Base Block':'Płyty korpusu','Back Block':'Płyty pokrywy','Frame':'Rama','Profiles':'Profile','Strips':'Profile złącza','Braces':'Wzmocnienia','Braces-Back':'Wzmocnienia pokrywy','Interior':'Szyny rackowe i podkładki','Wheels':'Koła i deski montażowe','Locks':'Zamki','Corners':'Narożniki','Miski':'Gniazda piętrowania'}
    for r in rows[1:]:
        i=r['id'];b=boxes[i];sec=section(i);w=wall(i) if b else 'brak geometrii';c=center(i) if b else [0]*3;pos=('przód' if c[1]<YF+288.5 else 'tył')+'/'+('dół' if c[2]<ZF+215 else 'góra');src=r['name'];own=next((a for a in path(i)[:-1] if a in units),None)
        if i in (819,817,2646):label='RockPro | '+('Korpus racka 9U' if sec=='korpus' else 'Pokrywa zdejmowana — '+sec)
        elif i in panels:label='Sklejka 9.8 mm — '+sec+' — '+('dach' if i in (715,670,2653) else 'dno' if i in (719,674,2657) else 'ściana zamykająca' if i in (682,2665) else w)
        elif i in rails:label='Szyna rackowa 6162 — stałe 9U — '+w+' — '+pos
        elif i in pads:label='Podkładka szyny 9 mm — korpus — '+w+' — '+pos
        elif src=='H7159':label='Uchwyt H7159 — korpus — '+w+' — '+pos
        elif src.startswith('17251'):label='Zamek 17251S — '+sec+' — '+w+' — '+pos
        elif i in (3215,3219,3221,3223):label='Gniazdo piętrowania W0964 — dach — '+w+' — '+pos
        elif src in ('37033','37034') and i in units:label='Koło '+src+' — spód — '+w+' — '+pos
        elif own:label='Podczęść '+by[own]['name']+' — '+sec+' — '+w+' — '+pos+' — ID '+str(i)+' (rola do identyfikacji)'
        elif src.startswith('EG-'):
            location=('złącze przód' if c[1]<YF+288.5 else 'złącze tył') if b[3]-b[0]>269 else w
            label='Profil '+src+' — '+sec+' — '+location+' — '+pos
        elif src in ('41046','B1121'):label=('Narożnik ' if src=='41046' else 'Wzmocnienie ')+src+' — '+sec+' — '+w+' — '+pos
        elif src in groupnames:label=groupnames[src]+' — '+sec+' — ID '+str(i)
        else:label='Element '+src+' (rola do identyfikacji) — '+sec+' — '+w+' — '+pos+' — ID '+str(i)
        names.append(dict(id=i,name=label))
    q=dict(contract='rockpro-rack-parametric-v1',expected_pid=18584,sha256='11e7004b61054dbc4796c1f254c288f6b6fe5ba3f3dd3933f2539181d51d68c3',source=inspection['source'],
           output=str(ROOT.parents[2]/'projekty/Rack9U_parametryczny_20261030/03_CAD/Do_sprawdzenia/RockPro_Rack9U_r001_IC2027.ics'),inventory=rows,parameters=params,primary=PRIMARY,primary_base=BASE,rebuild=rebuild,green_parts=panels+pads,reveal=[819,817,2646],
           dimensions=[dict(part=i,coefficients=c) for i,c in dims.items()],nodes=[dict(id=r['id'],parent=r['parent'],depth=r['depth'],shift=shifts[r['id']]) for r in rows[1:] if not any(a in units for a in path(r['id'])[:-1])],units=sorted(units),
           parts=[dict(id=r['id'],owner=next((a for a in path(r['id']) if a in units),r['id']),growth=growth.get(r['id'],[[0]*5 for _ in range(3)])) for r in parts],operations=ops,names=names,
           alignment=[dict(a=2653,b=715,axis=2,edge='max'),dict(a=2665,b=682,axis=2,edge='max')],
           center_alignment=[dict(a=2737,b=2460,axis=2),dict(a=2795,b=2553,axis=2),dict(a=1768,b=1826,axis=2),dict(a=1919,b=1977,axis=2)],
           tests=[dict(name='gabaryty',values=dict(RP_GlebokoscKorpusu=617,RP_WysokoscObudowy=460,RP_GlebokoscPokrywyPrzod=108,RP_GlebokoscPokrywyTyl=98)),dict(name='montaz',values=dict(RP_ZamkiPrzod_Wysokosc=230,RP_UchwytyLewa_Rozstaw=190,RP_UchwytyPrawa_Wysokosc=225,RP_Kola_PrzesuniecieX=5,RP_Kola_PrzesuniecieY=5)),dict(name='pokrywy_i_szyny',values=dict(RP_WysunieciePrzod=160,RP_WysuniecieTyl=140,RP_SzynyPrzod_Odsuniecie=5,RP_SzynyTyl_Odsuniecie=-5))])
    (E/'plan.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
    print({k:len(q[k]) for k in ('parameters','parts','rebuild','dimensions','units','nodes','operations')})

if __name__=='__main__':main()
