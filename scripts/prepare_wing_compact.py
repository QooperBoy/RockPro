"""Pinned Wing Compact prototype: rigid device, fixed catalog sections, shared cut anchors."""
import json
from pathlib import Path
from prepare_tv_parametric import compose_rotation

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'artifacts/wing-compact-20261029'
PROJECT=ROOT.parents[2]/'projekty/Mikser_WingCompact_parametryczny_20261029'
BASE=[623.,504.,231.8]
PRIMARY=['RP_SzerokoscSkrzyni','RP_GlebokoscSkrzyni','RP_WysokoscCzapki']
XL,YF,ZLOW=192.09567182448434,-806.8450362806534,66.3751875812056
XR,YB,ZTOP=XL+623,YF+504,ZLOW+231.8
PANELS={1459:'prawa',1463:'przód',1471:'tył',1479:'lewa',1483:'dach',1648:'dno'}
def mm(x):return f'{x:.14g} mm'
def add(*terms):return ' + '.join('('+t+')' for t in terms if t not in ('0 mm','0')) or '0 mm'
def scale(c,x):return '0 mm' if abs(c)<1e-9 else x if abs(c-1)<1e-9 else f'({c:.14g})*({x})'
def difference(a,b):return f'({a}) - ({b})'

def main():
    inspection=json.loads((E/'inspect-02/result.json').read_text(encoding='utf-8'))
    rows=inspection['rows'];by={r['id']:r for r in rows}
    detail=json.loads((E/'details-01/result.json').read_text(encoding='utf-8'))['rows']
    parts=[r for r in rows if r['type']=='Z_ELEMENT_PART']
    if len(parts)!=162:raise ValueError('Expected the reviewed 162-part source revision')
    def path(i):
        out=[]
        while i>=0:out.append(i);i=by[i]['parent']
        return out[::-1]
    def box(i):
        r=by[i]
        if 'bounds_m' in r:
            b=r['bounds_m'];m=r['world_matrix_m'];points=[[1000*(m[12+j]+sum(b[k+3*((v>>k)&1)]*m[k*4+j] for k in range(3))) for j in range(3)] for v in range(8)]
            return [min(p[k] for p in points) for k in range(3)]+[max(p[k] for p in points) for k in range(3)]
        children=[box(x['id']) for x in rows if x['parent']==i];children=[b for b in children if b]
        return [min(b[k] for b in children) for k in range(3)]+[max(b[k+3] for b in children) for k in range(3)] if children else None
    boxes={r['id']:box(r['id']) for r in rows}
    def center(i):
        b=boxes[i];return [(b[k]+b[k+3])/2 for k in range(3)]
    def lid(i):return 1456 in path(i)
    def wall(i):
        c=center(i)
        return min([(abs(c[0]-XL),'lewa'),(abs(c[0]-XR),'prawa'),(abs(c[1]-YF),'przód'),(abs(c[1]-YB),'tył')])[1]
    rebuild=[]
    for r in parts:
        fs=r['features']
        if r['id'] not in {x['id'] for x in detail}:continue
        if all(f.get('extrude') and f.get('curves') for f in fs):rebuild.append(r['id'])
    if len(rebuild)!=30:raise ValueError(('Unexpected reconstructable materials',rebuild))
    dimensions={};world_growth={}
    for i in rebuild:
        if i in (3100,3240):continue # compound device-shaped foam stays rigid
        size=[boxes[i][j+3]-boxes[i][j] for j in range(3)]
        growth=[[0.,0.,0.] for _ in range(3)]
        if size[0]>BASE[0]/2:growth[0][0]=1
        if size[1]>BASE[1]/2:growth[1][1]=1
        if lid(i) and size[2]>BASE[2]/2:growth[2][2]=1
        rotation=compose_rotation(by[i]['features'][0]['matrix_m'],by[i]['world_matrix_m'])
        local=[growth[max(range(3),key=lambda k:abs(rotation[a*4+k]))] for a in range(3)]
        dimensions[i]=local;world_growth[i]=growth
    explicit_units={r['id'] for r in rows if r['name'] in ('H7159','L905-915_1','L905-915_2')}|{3118,3117}
    units=set()
    for r in rows:
        i=r['id'];b=boxes[i]
        if r['type']!='Z_ELEMENT_ASSEMBLY' or not b:continue
        if any(i in path(p) for p in rebuild):continue
        if i in explicit_units or max(b[k+3]-b[k] for k in range(3))<150:
            if not any(a in units for a in path(i)[:-1]):units.add(i)
    params=[]
    def parameter(n,expr,note):
        if isinstance(expr,(float,int)):expr=mm(expr)
        params.append(dict(name=n,expression=expr,notes=note))
    for n,v,note in zip(PRIMARY,BASE,[
        'Szerokość zewnętrznego obrysu sklejki czapki w osi X, bez wystających okuć. Sprawdzone wartości 623 i 663 mm. Nie jest wymiarem miksera.',
        'Głębokość zewnętrznego obrysu sklejki czapki w osi Y, bez okuć. Sprawdzone wartości 504 i 534 mm. Przekroje profili pozostają stałe.',
        'Wysokość zdejmowanej czapki od dolnej krawędzi jej sklejki do dachu. Sprawdzone wartości 231.8 i 251.8 mm. To wysoka osłona nad płaską podstawą.']):parameter(n,v,note)
    parameter('RP_UniesienieCzapki',0,'Poglądowe uniesienie kompletnej czapki z okuciami i piankami; 0 = zamknięcie, test 200 mm. Mikser i dolna podstawa pozostają nieruchome.')
    for a in 'XYZ':parameter('RP_Mikser_Przesuniecie'+a,0,'Dodatkowe przesunięcie rzeczywistego modelu miksera w osi '+a+' projektu. Urządzenie nie jest skalowane; kieszenie w piance dna podążają za nim. Próba: X +2 mm, Y -2 mm, Z +1 mm; sprawdź prześwit.')
    for w in ('Przod','Tyl'):
        parameter('RP_Zamki'+w+'_Rozstaw','RP_SzerokoscSkrzyni - 250 mm','Odległość między środkami dwóch kompletnych zamków na ścianie '+w+'. Obie połówki i wycięcia sklejki/profili/pianki podążają razem. Zalecane 120 mm do szerokości minus 170 mm; liczba pozostaje jak we wzorcu.')
        parameter('RP_Zamki'+w+'_Przesuniecie',0,'Przesunięcie rzędu zamków '+w+' w osi X projektu; dodatnie w prawo, patrząc od przodu. Zachowaj zapas przy narożnikach.')
        parameter('RP_Zamki'+w+'_Pion',0,'Pionowe odsunięcie par połówek zamków '+w+' od źródłowego złącza. Zalecane -2 do +2 mm. Nie zmienia geometrii katalogowego okucia.')
    for w in ('Przod','Tyl','Lewa'):
        parameter('RP_Uchwyt'+w+'_Pozycja','RP_'+('Glebokosc' if w=='Lewa' else 'Szerokosc')+'Skrzyni/2','Pozycja środka uchwytu czapki '+w+': '+('od przodu, w osi Y' if w=='Lewa' else 'od lewego boku, w osi X projektu')+'. Otwory w sklejce i piance podążają razem. Zalecane min. 116 mm od skraju.')
        parameter('RP_Uchwyt'+w+'_Wysokosc','(RP_WysokoscCzapki - 6.8 mm)/2','Wysokość środka uchwytu czapki '+w+' od dolnej krawędzi jej sklejki. Zalecane 80 mm do wysokości czapki minus 87 mm. Wartość liczbowa zastępuje domyślne centrowanie.')
    for a in 'XY':parameter('RP_Nozki_Odsuniecie'+a,76.5,'Odległość środka gumowych nóżek od odpowiednich bocznych krawędzi obrysu sklejki w osi '+a+'. Steruje parami symetrycznie. Zalecane min. 63 mm; stopki pozostają sztywne. Wzorzec nie zawiera osobnych otworów pod śruby w dnie.')
    for a in 'XY':parameter('RP_Podpory_Przesuniecie'+a,0,'Przesunięcie dwóch dolnych podpór w osi '+a+' względem źródłowego położenia przy ramie. Przekrój sklejki 18 mm i kształt podpór nie zmieniają się. Przeznaczone do małych korekt; montaż wymaga kontroli.')
    for a in 'XYZ':parameter('RP_PiankiProfilowane_Przesuniecie'+a,0,'Dodatkowe przesunięcie kształtowych wkładów piankowych w osi '+a+'. Zachowano ich kontur pod mikser. Podążają też za korektą urządzenia i uniesieniem czapki; nie jest to generator nowych konturów CNC.')
    delta=[f'({n} - {mm(b)})' for n,b in zip(PRIMARY,BASE)]
    def snap(v,lo,hi,margin):return 0 if v-lo<margin else 1 if hi-v<margin else .5
    shifts={1:['0 mm']*3}
    for r in rows[1:]:
        i=r['id'];b=boxes[i]
        owner=next((a for a in path(i)[:-1] if a in units),None)
        if owner:shifts[i]=shifts[owner][:];continue
        if not b:shifts[i]=shifts[r['parent']][:];continue
        c=center(i)
        shift=[scale(snap(c[0],XL,XR,100),delta[0]),scale(snap(c[1],YF,YB,90),delta[1]),add(scale(snap(c[2],ZLOW,ZTOP,55),delta[2]),'RP_UniesienieCzapki') if lid(i) else '0 mm']
        if i==3118:shift=[add(scale(.5,delta[0]),'RP_Mikser_PrzesuniecieX'),add(scale(.5,delta[1]),'RP_Mikser_PrzesuniecieY'),'RP_Mikser_PrzesuniecieZ']
        if i==3117:shift=[scale(.5,delta[0]),scale(.5,delta[1]),add(delta[2],'RP_UniesienieCzapki')]
        if i in (3100,3240):shift=[add(scale(.5,delta[0]),'RP_Mikser_PrzesuniecieX','RP_PiankiProfilowane_PrzesuniecieX'),add(scale(.5,delta[1]),'RP_Mikser_PrzesuniecieY','RP_PiankiProfilowane_PrzesuniecieY'),add('RP_Mikser_PrzesuniecieZ','RP_PiankiProfilowane_PrzesuniecieZ','RP_UniesienieCzapki')]
        if i in (3160,3168):shift=[add(shift[0],'RP_Podpory_PrzesuniecieX'),add(shift[1],'RP_Podpory_PrzesuniecieY'),shift[2]]
        if i in world_growth:
            g=world_growth[i]
            for j in range(3):
                if any(g[j]):shift[j]='RP_UniesienieCzapki' if j==2 and lid(i) else '0 mm'
            rot=compose_rotation(r['features'][0]['matrix_m'],r['world_matrix_m'])
            for a in range(3):
                j=max(range(3),key=lambda k:abs(rot[a*4+k]))
                if rot[a*4+j]<-.9:shift[j]=add(shift[j],*[scale(g[j][k],delta[k]) for k in range(3)])
        shifts[i]=shift
    mounts=[]
    for i in units:
        r=by[i];w=wall(i);c=center(i)
        if r['name'].startswith('L905'):
            code='Przod' if w=='przód' else 'Tyl';rank=-.5 if c[0]<(XL+XR)/2 else .5
            shifts[i]=[difference(add(mm((XL+XR)/2),scale(.5,delta[0]),scale(rank,'RP_Zamki'+code+'_Rozstaw'),'RP_Zamki'+code+'_Przesuniecie'),mm(c[0])),scale(0 if w=='przód' else 1,delta[1]),add('RP_Zamki'+code+'_Pion','RP_UniesienieCzapki' if lid(i) else '0 mm')]
            mounts.append(dict(id=i,kind='latch',wall=w,rank=rank))
        elif r['name']=='H7159':
            code={'przód':'Przod','tył':'Tyl','lewa':'Lewa'}[w];axis=1 if w=='lewa' else 0;origin=YF if axis else XL
            shifts[i][axis]=difference('RP_Uchwyt'+code+'_Pozycja',mm(c[axis]-origin))
            shifts[i][2]=add(difference('RP_Uchwyt'+code+'_Wysokosc',mm(c[2]-ZLOW)),'RP_UniesienieCzapki')
            mounts.append(dict(id=i,kind='handle',wall=w))
        elif r['name']=='F1692':
            shifts[i][0]=difference('RP_Nozki_OdsuniecieX' if c[0]<(XL+XR)/2 else 'RP_SzerokoscSkrzyni - RP_Nozki_OdsuniecieX',mm(c[0]-XL))
            shifts[i][1]=difference('RP_Nozki_OdsuniecieY' if c[1]<(YF+YB)/2 else 'RP_GlebokoscSkrzyni - RP_Nozki_OdsuniecieY',mm(c[1]-YF))
            mounts.append(dict(id=i,kind='foot',wall='dno'))
    # Descendants of rigid units inherit the updated complete-unit movement.
    for r in rows[1:]:
        owner=next((a for a in path(r['id'])[:-1] if a in units),None)
        if owner:shifts[r['id']]=shifts[owner][:]
    operations=[]
    for row in detail:
        i=row['id'];fs={f.get('id'):f for f in by[i]['features'] if 'id' in f}
        for f in row['features']:
            fid=f.get('id');c=f.get('profile_center_world_mm')
            if fid not in fs or fs[fid]['operation']!='Z_SUBTRACT' or not c:continue
            name=fs[fid]['name'];owner=None;shift=shifts[i][:]
            if name.startswith('L/H_'):
                candidates=[m for m in mounts if m['kind']=='latch' and m['wall']==('przód' if c[1]<(YF+YB)/2 else 'tył')]
                owner=min(candidates,key=lambda m:sum((center(m['id'])[k]-c[k])**2 for k in range(3)))['id']
                shift=shifts[owner][:]
                shift[2]=add('RP_Zamki'+('Przod' if wall(owner)=='przód' else 'Tyl')+'_Pion','RP_UniesienieCzapki' if lid(i) else '0 mm')
            elif 'H7159' in name:
                # The source has an unused right-side foam opening but no
                # right-side handle or plywood opening. Never bind it to an
                # unrelated nearest handle on another wall.
                cutwall=min([(abs(c[0]-XL),'lewa'),(abs(c[0]-XR),'prawa'),(abs(c[1]-YF),'przód'),(abs(c[1]-YB),'tył')])[1]
                candidates=[m for m in mounts if m['kind']=='handle' and m['wall']==cutwall]
                if candidates:
                    owner=candidates[0]['id'];shift=shifts[owner][:]
                else:
                    shift=[scale(snap(c[0],XL,XR,100),delta[0]),scale(snap(c[1],YF,YB,90),delta[1]),add(scale(.5,delta[2]),'RP_UniesienieCzapki')]
            elif i==1911 and fid in (3152,3154,3156,3158,3219):owner=3118;shift=shifts[3118][:]
            operations.append(dict(part=i,id=fid,shift=shift,mount=owner,depth=by[i]['depth']+1,reconstructed=i in rebuild,
                                   bind=not any(a in units for a in path(i)[:-1]),reserved=fid==3093))
    bound=[]
    for r in rows[1:]:
        if any(a in units for a in path(r['id'])[:-1]):continue
        bound.append(dict(id=r['id'],parent=r['parent'],depth=r['depth'],shift=shifts[r['id']],matrix_m=r['local_matrix_m']))
    def label(i):
        r=by[i];section='czapka' if lid(i) else 'podstawa';source=r['name'];b=boxes[i]
        if i==3249:return 'RockPro | Mikser Wing Compact — kompletna skrzynia'
        if i==1456:return 'RockPro | Czapka zdejmowana'
        if i==1646:return 'RockPro | Podstawa dolna'
        if i in (3118,2):return 'Urządzenie referencyjne — Behringer Wing Compact — geometria sztywna'
        if i in (3117,3111,3199):return 'Oznaczenia klienta i modelu — czapka — dach'+(' — element '+str(i) if i!=3117 else '')
        if i in PANELS:return 'Sklejka 6.8 mm — '+section+' — '+PANELS[i]
        if not b:return 'Grupa — '+section+' — '+source+' — pusta'
        c=center(i);position=('lewa' if c[0]<(XL+XR)/2 else 'prawa')+'/'+('przód' if c[1]<(YF+YB)/2 else 'tył')
        m=next((m for m in mounts if m['id']==i),None)
        if m:
            if m['kind']=='latch':return 'Zamek L905/915 — '+m['wall']+' — '+('lewy' if m['rank']<0 else 'prawy')+' — połówka '+section
            if m['kind']=='handle':return 'Uchwyt H7159 — czapka — '+m['wall']+' — środek'
            return 'Nóżka F1692 — podstawa — spód — '+position
        owner=next((a for a in path(i)[:-1] if any(m['id']==a for m in mounts)),None)
        if owner:return label(owner)+' — podczęść '+str(i)+' (rola do identyfikacji)'
        if source.startswith('EG-'):return ('Profil '+source+' — '+section+' — '+wall(i)+' — '+position) if r['type']=='Z_ELEMENT_PART' else 'Profile '+source+' — '+section
        if source in ('B1121','C1351','C1346') or source=='Część1':return 'Okucie narożne '+source+' — '+section+' — '+position
        if i in (3160,3161,3168,3169):return 'Podpora sklejki 18 mm — podstawa — prawa/'+('przód' if c[1]<(YF+YB)/2 else 'tył')
        if source.startswith('MG'):return 'Pianka '+source+' — '+section+' — '+wall(i)+' — ID '+str(i)
        roles={'Lid_Block':'Płyty sklejki','Frame':'Rama profili i okuć','Profiles':'Profile krawędziowe','Braces':'Wzmocnienia','Strips':'Profile złącza','Corners':'Narożniki','Locks':'Zamki','Handles':'Uchwyty','Foam':'Wkłady piankowe','Bot':'Płyta dna','Feet':'Nóżki','Right':'Ściana prawa','Left':'Ściana lewa','Front':'Ściana przednia','Back':'Ściana tylna','Top':'Dach i oznaczenia'}
        return roles.get(source,'Element '+source+' (rola do identyfikacji)')+' — '+section+' — ID '+str(i)
    q=dict(contract='rockpro-wing-parametric-v1',expected_pid=18584,source=inspection['source'],sha256='397be68fe6dec85312d1a9d538eb7a52609cfd2b3f485b8a7afb05cf69bbfd62',
           output=str(PROJECT/'03_CAD/Do_sprawdzenia/RockPro_WingCompact_r001_parametryczny_IC2027.ics'),parameters=params,
           inventory=rows,rebuild=rebuild,dimensions=[dict(part=i,coefficients=c) for i,c in dimensions.items()],primary=PRIMARY,primary_base=BASE,
           nodes=bound,units=sorted(units),parts=[dict(id=r['id'],owner=next((a for a in path(r['id']) if a in units),r['id']),shift=shifts[r['id']],bounds_m=r['bounds_m'],world_matrix_m=r['world_matrix_m'],growth=world_growth.get(r['id'],[[0,0,0] for _ in range(3)])) for r in parts],
           operations=operations,names=[dict(id=r['id'],name=label(r['id'])) for r in rows[1:]],device_id=2,
           case_origin=[XL,YF,ZLOW],floor_top=28.775278344931435,
           tests=[dict(name='wieksze_gabaryty',values={PRIMARY[0]:663,PRIMARY[1]:534,PRIMARY[2]:251.8}),
                  dict(name='okucia_i_nozki',values={'RP_ZamkiPrzod_Rozstaw':330,'RP_ZamkiTyl_Przesuniecie':8,'RP_UchwytPrzod_Wysokosc':123,'RP_UchwytLewa_Pozycja':265,'RP_Nozki_OdsuniecieX':83,'RP_Nozki_OdsuniecieY':85}),
                  dict(name='otwarta_czapka',values={'RP_UniesienieCzapki':200,'RP_ZamkiPrzod_Rozstaw':350}),
                  dict(name='mikser_i_kieszenie',values={'RP_Mikser_PrzesuniecieX':2,'RP_Mikser_PrzesuniecieY':-2,'RP_Mikser_PrzesuniecieZ':1})])
    (E/'plan.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(parts=len(parts),rebuild=len(rebuild),dimensioned=len(dimensions),units=len(units),parameters=len(params),nodes=len(bound),operations=len(operations))))

if __name__=='__main__':main()
