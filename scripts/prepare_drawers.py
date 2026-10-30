"""Pinned workstation plan. Select deployed state, preserve its rotated section frames."""
import json
from pathlib import Path
from prepare_wing_compact import mm,add,scale,difference

ROOT=Path(__file__).resolve().parents[1];E=ROOT/'artifacts/szuflady-20261030'

def rot(m):return [[m[a*4+b] for b in range(3)] for a in range(3)]
def tr(m):return [[m[b][a] for b in range(3)] for a in range(3)]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def vec(v,m):return [sum(v[k]*m[k][j] for k in range(3)) for j in range(3)]
def expressions(v,m):return [add(*[scale(m[k][j],v[k]) for k in range(3)]) for j in range(3)]

def main():
    inspection=json.loads((E/'inspect-01/result.json').read_text(encoding='utf-8'));rows=inspection['rows'];by={r['id']:r for r in rows}
    details=json.loads((E/'details-01/result.json').read_text(encoding='utf-8'))['rows']+json.loads((E/'pads-01/result.json').read_text(encoding='utf-8'))['rows']
    def path(i):
        a=[]
        while i>=0:a.append(i);i=by[i]['parent']
        return a[::-1]
    active=[r for r in rows if 1788 in path(r['id'])]
    parts=[r for r in active if r['type']=='Z_ELEMENT_PART'];assert len(parts)==380
    roots={'body':1040,'table':895,'lid':1631,'legs':1702};closed={'body':148,'table':3,'lid':739}
    def phase(i):return next((k for k,v in roots.items() if v in path(i)),None)
    def world_points(i):
        r=by[i]
        if 'bounds_m' in r:
            b=r['bounds_m'];m=r['world_matrix_m'];return [[1000*(m[12+j]+sum(b[k+3*((v>>k)&1)]*m[k*4+j] for k in range(3))) for j in range(3)] for v in range(8)]
        return [p for r in rows if r['parent']==i for p in world_points(r['id'])]
    frames={k:mul(tr(rot(by[closed[k]]['world_matrix_m'])),rot(by[v]['world_matrix_m'])) for k,v in roots.items() if k!='legs'}
    def to_design(p,ph):
        if ph not in closed:return p
        o=by[roots[ph]]['world_matrix_m'];c=by[closed[ph]]['world_matrix_m']
        local=vec([p[j]-1000*o[12+j] for j in range(3)],tr(rot(o)))
        value=vec(local,rot(c));return [value[j]+1000*c[12+j] for j in range(3)]
    def bbox(i,design=True):
        ph=phase(i);points=world_points(i);points=[to_design(p,ph) for p in points] if design else points
        return [min(p[k] for p in points) for k in range(3)]+[max(p[k] for p in points) for k in range(3)]
    boxes={r['id']:bbox(r['id']) for r in active}
    def center(i):b=boxes[i];return [(b[j]+b[j+3])/2 for j in range(3)]
    base=bbox(185,False);back=bbox(188,False);roof=bbox(785,False);side=bbox(782,False);table=bbox(125,False)
    XL,YF,ZF=base[:3];W=base[3]-XL;D=base[4]-YF;H=back[5]-ZF;L=roof[5]-side[2];TL=table[5]-table[2]
    drawer_ids=[1272,1230,1209,1251];heights=[220.,205.,300.,130.];fronts=[1288,1246,1225,1267]
    pads=[1293,1296,1301,1304]
    panels=[r['id'] for r in parts if r['parent'] in (1016,1076,1673) or r['parent'] in drawer_ids and r['name']!='3453']+pads
    material=panels+[r['id'] for r in parts if r['name'].startswith('EG-')]
    assert all(by[i]['features'][0].get('extrude') for i in material)
    rebuild=[i for i in material if all(f.get('extrude') and f.get('curves') for f in by[i]['features'])]
    # Complete opaque units; the two L905 groups contain separate latch halves.
    units={1702,1309,960,973,1108,1141,986,1001}|{r['id'] for r in active if r['type']=='Z_ELEMENT_ASSEMBLY' and r['name']=='H7159'}
    for p in parts:
        i=p['id']
        if i not in material and not any(a in units for a in path(i)):units.add(i)
    units={i for i in units if not any(a in units for a in path(i)[:-1])}
    params=[]
    def parameter(n,e,note):params.append(dict(name=n,expression=mm(e) if isinstance(e,(int,float)) else e,notes=note))
    parameter('RP_Szerokosc',W,'Szerokość obrysu sklejki korpusu, oś X, mm. Bez wystających okuć. Próbna zmiana +30 mm; zmienia też szerokość szuflad i odpowiadający wymiar stołu/pokrywy.')
    parameter('RP_Glebokosc',D,'Głębokość sklejki korpusu, od frontu do tyłu, mm. Próbna zmiana +20 mm. Zmienia pudła szuflad oraz głębokość górnej klapy; metalowych okuć nie skaluje.')
    for k,h in enumerate(heights,1):parameter(f'RP_Szuflada{k}_Wysokosc',h,f'Wysokość frontu szuflady {k}, licząc od dołu, mm. Ścianki pudła mają zachowane źródłowe odsunięcia. Zmienia położenie wyższych szuflad i wynikową wysokość korpusu; zalecane na początek +10–20 mm.')
    reserve=boxes[1101][2]-boxes[1267][5]
    parameter('RP_RezerwaNadSzufladami',reserve,'Wolna wysokość nad najwyższym frontem do dolnej powierzchni półki górnej, mm. Minimum źródłowe około 14.25 mm. Zwiększenie jawnie podnosi korpus, a nie ściska szuflady.')
    parameter('RP_WysokoscKorpusu',' + '.join(f'RP_Szuflada{k}_Wysokosc' for k in range(1,5))+f' + RP_RezerwaNadSzufladami + {mm(H-sum(heights)-reserve)}','Wynikowa wysokość sklejki korpusu od spodu dna do górnej krawędzi. Suma wysokości szuflad, rezerwy i stałych źródłowych przerw konstrukcyjnych. Zachowaj równanie; ręczne skrócenie może wywołać kolizje.')
    parameter('RP_WysokoscKlapyGornej',L,'Wysokość górnej klapy w stanie złożonym, mm; źródłowo około 111.64. W stanie roboczym zachowuje źródłowe otwarcie 105 stopni. Próbna zmiana +10 mm; nie zmniejszaj bez kontroli zawiasów.')
    primary=['RP_Szerokosc','RP_Glebokosc','RP_WysokoscKorpusu','RP_WysokoscKlapyGornej']+[f'RP_Szuflada{k}_Wysokosc' for k in range(1,5)]
    baseline=[W,D,H,L]+heights;delta=[difference(n,mm(v)) for n,v in zip(primary,baseline)]
    for k in range(1,5):parameter(f'RP_Szuflada{k}_Wysuw',0,f'Poglądowe wysunięcie szuflady {k} w stronę frontu (-Y), mm. 0 = wsunięta, próby do 240 mm. Nie jest symulacją nośności ani certyfikacją zakresu prowadnic; zachowano źródłowe podkładki drewniane.')
    for a in 'XY':parameter('RP_Stol_Przesuniecie'+a,0,'Przesunięcie całego rozłożonego stołu z nogami w globalnej osi '+a+', mm. Stół jest odpinaną przednią pokrywą; parametry dotyczą jednego egzemplarza, nie kopii transportowej.')
    parameter('RP_Nogi_KorektaZ',0,'Dodatkowa korekta całego fabrycznego zespołu nóg w osi Z, mm. Nie zmienia jego długości. Źródłowy kontakt z podłogą i blatem wymaga oceny konstruktora; domyślnie 0.')
    joint_units=[1108,1141,960,973];joint_rank={i:min(range(2),key=lambda k:abs(center(i)[2]-center([1108,1141][k])[2])) for i in joint_units}
    for rank,i in enumerate((1108,1141),1):
        height=center(i)[2]-ZF
        parameter(f'RP_Zamek{rank}_Wysokosc',height if rank==1 else f'RP_WysokoscKorpusu - {mm(H-height)}',f'Wysokość osi zamka {rank} od spodu dna w stanie złożonym, mm. Połówka na stole i jej wycięcia poruszają się w ramie stołu, a połówka korpusu w ramie korpusu.')
    handles=[i for i in units if by[i]['name']=='H7159']
    for wall,code in [('lewa','Lewa'),('prawa','Prawa')]:
        ids=[i for i in handles if (center(i)[0]<XL+W/2)==(wall=='lewa')];cs=[center(i) for i in ids]
        spread=max(c[1] for c in cs)-min(c[1] for c in cs);offset=sum(c[1] for c in cs)/2-YF-D/2;height=sum(c[2] for c in cs)/2-ZF
        parameter('RP_Uchwyty'+code+'_Rozstaw',spread,'Rozstaw dwóch uchwytów na ścianie '+wall+', w osi Y, mm. Liczba pozostaje 2; zmiana liczby wymaga przebudowy. Zachowaj zapas od zamków i krawędzi.')
        parameter('RP_Uchwyty'+code+'_Pozycja',f'RP_Glebokosc/2 + {mm(offset)}','Środek pary uchwytów '+wall+' od przedniej krawędzi korpusu, mm; ich wycięcia w ścianie i podkładce podążają razem.')
        parameter('RP_Uchwyty'+code+'_Wysokosc',f'(RP_WysokoscKorpusu - {mm(H)})/2 + {mm(height)}','Wysokość środka pary uchwytów '+wall+' od spodu dna, mm. Domyślnie podąża o połowę zmiany wysokości korpusu; można jawnie wpisać inną wartość.')
    for a in 'XY':parameter('RP_Podstawa_Przesuniecie'+a,0,'Przesunięcie kompletnej źródłowej podstawy transportowej z czterema kołami w osi '+a+', mm. Jej rozstaw i geometria pozostają sztywne; domyślnie wyśrodkowana względem zmienianego korpusu.')
    def snap(v,lo,size):return 0 if v-lo<size*.22 else 1 if lo+size-v<size*.22 else .5
    def drawer(i):return next((k for k,g in enumerate(drawer_ids) if g in path(i)),None)
    def design_growth(i):
        b=boxes[i];span=[b[k+3]-b[k] for k in range(3)];ph=phase(i);dr=drawer(i);g=[[0.]*8 for _ in range(3)]
        if span[0]>W/2:g[0][0]=1
        if ph in ('body','lid') and span[1]>D/2:g[1][1]=1
        if dr is not None:
            if span[2]>heights[dr]/2:g[2][4+dr]=1
        elif ph=='body' and span[2]>H/2:g[2][2]=1
        elif ph=='table' and span[2]>TL/2:g[2][2]=g[2][3]=1
        elif ph=='lid' and span[2]>L/2:g[2][3]=1
        if i in pads:g[1]=[0.]*8
        return g
    def generic_design(c,ph,g=None):
        shift=[scale(snap(c[0],XL,W),delta[0]),'0 mm','0 mm']
        if ph=='body':shift[1]=scale(snap(c[1],YF,D),delta[1]);shift[2]=scale(snap(c[2],ZF,H),delta[2])
        elif ph=='table':shift[2]=add(scale(snap(c[2],ZF,TL),delta[2]),scale(snap(c[2],ZF,TL),delta[3]))
        elif ph=='lid':shift[1]=scale(snap(c[1],YF,D)-1,delta[1]);shift[2]=scale(snap(c[2],side[2],L),delta[3])
        if g:
            for axis in range(3):
                if any(g[axis]):
                    shift[axis]=add(*[scale(.5*g[axis][k],delta[k]) for k in range(8)])
                    if ph=='lid' and axis==1:shift[axis]=add(shift[axis],scale(-1,delta[1]))
        return shift
    def world_shift(shift,ph):
        value=expressions(shift,frames[ph])
        if ph=='lid':value[1]=add(value[1],delta[1]);value[2]=add(value[2],delta[2])
        if ph=='table':value[0]=add(value[0],'RP_Stol_PrzesuniecieX');value[1]=add(value[1],'RP_Stol_PrzesuniecieY')
        return value
    def desired(i,g=None,point=None):
        ph=phase(i);c=center(i) if point is None else point;dr=drawer(i)
        shift=generic_design(c,ph,g)
        if dr is not None:
            below=add(*delta[4:4+dr]);shift[2]=add(below,scale(.5 if g and any(g[2]) or i not in material else 0,delta[4+dr]))
            shift[1]=add(shift[1],scale(-1,f'RP_Szuflada{dr+1}_Wysuw'))
        return world_shift(shift,ph)
    dims={};local_low={};local_high={};shifts={r['id']:['0 mm']*3 for r in active}
    for r in parts:
        i=r['id']
        if i not in material and i not in units:continue
        ph=phase(i)
        if ph=='legs':continue
        if i in material:
            g=design_growth(i);fw=mul(rot(r['features'][0]['matrix_m']),rot(r['world_matrix_m']));fd=mul(fw,tr(frames[ph]));coeff=[]
            for axis in range(3):
                k=max(range(3),key=lambda j:abs(fd[axis][j]));assert abs(fd[axis][k])>.9999,(i,fd)
                coeff.append(g[k][:])
            dims[i]=coeff;fr=rot(r['features'][0]['matrix_m'])
            local_low[i]=[[sum(min(0,fr[a][j])*coeff[a][k] for a in range(3)) for k in range(8)] for j in range(3)]
            local_high[i]=[[sum(max(0,fr[a][j])*coeff[a][k] for a in range(3)) for k in range(8)] for j in range(3)]
            value=desired(i,g)
            # About-anchor resizing extends each feature axis. Subtract its
            # center drift in world coordinates, rather than guessing a world
            # dominant axis for the tilted lid/table.
            for j in range(3):value[j]=add(value[j],*[scale(-.5*fw[a][j]*coeff[a][k],delta[k]) for a in range(3) for k in range(8)])
            shifts[i]=value
        else:shifts[i]=desired(i)
    # Worktop width originates from the transport cover width, but its pegs
    # attach along the cabinet depth. Follow the cabinet peg spacing, not the
    # resized worktop's outer edge. Its factory legs define a fixed work height.
    for i in (1199,1201,1487,1489):
        value=generic_design(center(i),'body');value[2]='0 mm';shifts[i]=world_shift(value,'body')
    shifts[986]=['RP_Stol_PrzesuniecieX',add(delta[1],'RP_Stol_PrzesuniecieY'),'0 mm']
    shifts[1001]=['RP_Stol_PrzesuniecieX','RP_Stol_PrzesuniecieY','0 mm']
    for i in joint_units:
        c=center(i);rank=joint_rank[i];shift=generic_design(c,phase(i));shift[2]=difference(f'RP_Zamek{rank+1}_Wysokosc',mm(center([1108,1141][rank])[2]-ZF));shifts[i]=world_shift(shift,phase(i))
    for i in handles:
        c=center(i);code='Lewa' if c[0]<XL+W/2 else 'Prawa';rank=-.5 if c[1]<YF+D/2 else .5
        shift=generic_design(c,'body');shift[1]=difference(add(mm(YF),'RP_Uchwyty'+code+'_Pozycja',scale(rank,'RP_Uchwyty'+code+'_Rozstaw')),mm(c[1]));shift[2]=difference('RP_Uchwyty'+code+'_Wysokosc',mm(c[2]-ZF));shifts[i]=world_shift(shift,'body')
    shifts[1309]=[add(scale(.5,delta[0]),'RP_Podstawa_PrzesuniecieX'),add(scale(.5,delta[1]),'RP_Podstawa_PrzesuniecieY'),'0 mm']
    t=frames['table'];leglocal=[scale(.5,delta[0]),'0 mm',add(delta[2],delta[3])];leg=expressions(leglocal,t);leg[0]=add(leg[0],'RP_Stol_PrzesuniecieX');leg[1]=add(leg[1],'RP_Stol_PrzesuniecieY');leg[2]=add(leg[2],'RP_Nogi_KorektaZ');shifts[1702]=leg
    for r in active:
        own=next((a for a in path(r['id'])[:-1] if a in units),None)
        if own:shifts[r['id']]=shifts[own][:]
    ops=[]
    candidates={'body':handles+[1108,1141],'table':[960,973,986,1001],'lid':[]}
    for r in details:
        i=r['id']
        if i not in material:continue
        fs={f.get('id'):f for f in by[i]['features']};ph=phase(i)
        for f in r['features']:
            fid=f.get('id');c=f.get('profile_center_world_mm')
            if fid not in fs or fs[fid].get('operation')!='Z_SUBTRACT' or not c:continue
            design=to_design(c,ph);pool=candidates.get(ph,[])
            owner=min(pool,key=lambda m:sum((center(m)[k]-design[k])**2 for k in range(3))) if pool else None
            shift=shifts[owner][:] if owner is not None else desired(i,point=design)
            ops.append(dict(part=i,id=fid,shift=shift,mount=owner,depth=by[i]['depth']+1,bind=True,reserved=False))
    names=[];section_names={'body':'korpus','table':'stół / przednia pokrywa','lid':'górna klapa, otwarta 105 stopni','legs':'nogi stołu'}
    for r in active:
        i=r['id'];ph=phase(i);dr=drawer(i);src=r['name'];c=center(i);sec=section_names.get(ph,'komplet serwisu');side_name='lewa' if c[0]<XL+W/2 else 'prawa';location=('przód' if c[1]<YF+D/2 else 'tył')
        own=next((a for a in path(i)[:-1] if a in units),None)
        if i==1788:label='RockPro | Serwis 4 szuflady ze stołem — jeden egzemplarz, stan roboczy'
        elif i in roots.values():label='RockPro | '+sec
        elif i in drawer_ids:label=f'Szuflada {dr+1} od dołu — front {heights[dr]:g} mm'
        elif i in fronts:label=f'Front sklejki — szuflada {dr+1} od dołu'
        elif dr is not None and i in material:label=f'Pudło szuflady {dr+1} — '+('dno' if boxes[i][5]-boxes[i][2]<10 else side_name if boxes[i][3]-boxes[i][0]<10 else location)
        elif src=='3453':label=f'Uchwyt 3453 — szuflada {dr+1} — front'
        elif i in pads:label='Podkładka sklejki 6.8 mm — korpus — '+side_name+' — '+location
        elif src=='H7159':label='Uchwyt H7159 — korpus — '+side_name+' — '+location
        elif i in joint_units:label=f'Zamek L905/915 {joint_rank[i]+1} — połówka: '+sec
        elif i in (986,1001):label='Łącznik źródłowy stołu — '+side_name+' — SKU do potwierdzenia'
        elif i in (1199,1201,1487,1489):label='Trzpień mocowania stołu — korpus — '+side_name+' — '+location
        elif 1691 in path(i) or 1203 in path(i):label='Zawias P1980 — '+sec+' — '+side_name+' — '+src
        elif i==1309:label='Podstawa transportowa — cztery koła i płyta, geometria sztywna'
        elif own:label='Podczęść '+by[own]['name']+' — '+sec+' — ID '+str(i)+' (rola do identyfikacji)'
        elif src.startswith('EG-'):label='Profil '+src+' — '+sec+' — '+side_name+' — '+location
        elif i in panels:label='Sklejka — '+sec+' — '+side_name+' — '+location+' — ID '+str(i)
        elif src in ('B1121','C1351'):label=('Wzmocnienie ' if src=='B1121' else 'Narożnik ')+src+' — '+sec+' — '+side_name+' — '+location
        elif r['type']=='Z_ELEMENT_PART' and i in units:label='Okucie źródłowe '+src+' — '+sec+' — '+side_name+' — ID '+str(i)+' (SKU do potwierdzenia)'
        else:label='Grupa — '+sec+' — '+src+' — ID '+str(i)
        names.append(dict(id=i,name=label))
    zero=[[0.]*8 for _ in range(3)]
    q=dict(contract='rockpro-szuflady-parametric-v1',expected_pid=18584,sha256='180b57705df95eca65db4ad80133ce13d31210b373fa02a71969702a4637d9bb',source=inspection['source'],
           output=str(ROOT.parents[2]/'projekty/Serwis_szufladowy_parametryczny_20261030/03_CAD/Do_sprawdzenia/RockPro_Serwis4Szuflady_r001_IC2027.ics'),inventory=rows,parameters=params,primary=primary,primary_base=baseline,rebuild=rebuild,green_parts=panels,reveal=[1788,1040,895,1631,1702],remove_roots=[1787],
           dimensions=[dict(part=i,coefficients=v) for i,v in dims.items()],units=sorted(units),nodes=[dict(id=r['id'],parent=r['parent'],depth=r['depth'],shift=shifts[r['id']]) for r in active if not any(a in units for a in path(r['id'])[:-1])],
           parts=[dict(id=r['id'],owner=next((a for a in path(r['id']) if a in units),r['id']),growth=zero,local_min_growth=local_low.get(r['id'],zero),local_max_growth=local_high.get(r['id'],zero)) for r in parts],operations=ops,names=names,
           gaps=[dict(a=fronts[k],b=fronts[k+1],axis=2,edge_a='max',edge_b='min',minimum_mm=6.) for k in range(3)]+[dict(a=fronts[-1],b=1101,axis=2,edge_a='max',edge_b='min',minimum_param='RP_RezerwaNadSzufladami')],
           offset_pairs=[dict(a=987,b=1489,expected=['RP_Stol_PrzesuniecieX','RP_Stol_PrzesuniecieY',None]),dict(a=1002,b=1487,expected=['RP_Stol_PrzesuniecieX','RP_Stol_PrzesuniecieY',None])]+[dict(a=i,b=min((1204,1206),key=lambda b:abs(center(i)[0]-center(b)[0])),expected=[None,None,None]) for i in (1693,1700)],
           tests=[dict(name='szuflady_wysuw',values={f'RP_Szuflada{k}_Wysuw':v for k,v in enumerate([240,180,120,60],1)}),dict(name='gabaryty_i_sekcje',values=dict(RP_Szerokosc=W+30,RP_Glebokosc=D+20,RP_Szuflada2_Wysokosc=225,RP_WysokoscKlapyGornej=L+10)),dict(name='montaz',values=dict(RP_UchwytyLewa_Wysokosc=420,RP_UchwytyPrawa_Rozstaw=330,RP_Zamek1_Wysokosc=130,RP_Stol_PrzesuniecieY=10))])
    physical={r['id'] for r in parts};bound={r['id'] for r in q['nodes']}
    assert all(p['owner'] in bound for p in q['parts'])
    assert all(s['a'] in physical and s['b'] in physical for s in q['gaps']+q['offset_pairs'])
    (E/'plan.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
    print({k:len(q[k]) for k in ('parameters','parts','rebuild','dimensions','units','nodes','operations')});print('base',baseline,'reserve',reserve)

if __name__=='__main__':main()
