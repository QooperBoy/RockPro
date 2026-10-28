"""Prepare a pinned local review prototype, not a general MCP executor.

Inputs are local measurement evidence; no customer files enter source control.
Mounting contours trace measured vendor mouths; prototype arc fits require native checks.
"""
from __future__ import annotations
import argparse, ast, hashlib, itertools, json, math, operator
from pathlib import Path

IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
PARAMS = dict(RP_Szerokosc_wnetrza=800, RP_Glebokosc_wnetrza=650,
              RP_Wysokosc_wnetrza=800, RP_Grubosc_sklejki=9.8,
              RP_Wysokosc_wieka_gornego=115)
ALIASES = dict(W='RP_Szerokosc_wnetrza', D='RP_Glebokosc_wnetrza',
               B='RP_Wysokosc_wnetrza', T='RP_Grubosc_sklejki',
               L='RP_Wysokosc_wieka_gornego')
E, F, S, H = '(W+2*T)', '(D+2*T)', '(B+2*T)', '(B+2*T+L)'

def number(expression, values):
    """Arithmetic only; reject calls, attributes and all non-arithmetic AST."""
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.Name): return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub): return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            op = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul, ast.Div:operator.truediv}.get(type(node.op))
            if op: return op(visit(node.left), visit(node.right))
        raise ValueError('Unsupported expression')
    return visit(ast.parse(str(expression), mode='eval').body)

def expression(x):
    import re
    return re.sub(r'\b[WDBTL]\b', lambda m: ALIASES[m[0]], str(x))

def units(x):
    def emit(n):
        if isinstance(n,ast.Constant):return str(n.value),False
        if isinstance(n,ast.Name):return n.id,True
        if isinstance(n,ast.UnaryOp):
            a,d=emit(n.operand);return '-('+a+')',d
        a,ad=emit(n.left);b,bd=emit(n.right)
        if isinstance(n.op,(ast.Add,ast.Sub)):
            if ad and not bd:b=str(number(ast.unparse(n.right),{}))+' mm'
            if bd and not ad:a=str(number(ast.unparse(n.left),{}))+' mm'
            return '('+a+('+' if isinstance(n.op,ast.Add) else '-')+b+')',ad or bd
        return '('+a+('*' if isinstance(n.op,ast.Mult) else '/')+b+')',ad or bd
    s,d=emit(ast.parse(expression(x),mode='eval').body)
    return s if d else str(number(expression(x),{}))+' mm'

def rect(w,h):
    pts=[[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]
    return [dict(type='line', start=a, end=b) for a,b in zip(pts,pts[1:]+pts[:1])]

def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def determinant(a): return dot(a[0],cross(a[1],a[2]))
def rotate(v, r): return [sum(v[k]*r[k][j] for k in range(3)) for j in range(3)]

def mouth_curves(row, half=None):
    """Trace the measured mouth, with a 0.5 mm construction clearance.

    Vendor spline corners are fitted through their measured start/mid/end.
    These are explicit prototype arc fits, NOT exact source splines or CNC approval.
    Native interference checks remain mandatory after generating these contours.
    """
    wire='outer' if half else 'inner'
    es=row['recess']['flange'][0]['wires'][wire]
    if half:
        hz=.0508 if half=='upper' else .0948;hx=.0498
        es=[e for e in es if all(abs(e[p][0])<=hx+1e-6 and abs(e[p][2])<=hz+1e-6 for p in ('start','end'))]
    else:
        es=[e for e in es if e['type']!='Z_CURVE3D_CIRCLE']
        hx=max(abs(e[p][0]) for e in es for p in ('start','end'))
        hz=max(abs(e[p][2]) for e in es for p in ('start','end'))
    sx=(hx+.0005)/hx;sz=(hz+.0005)/hz
    def xy(v):return [v[0]*sx,v[2]*sz]
    curves=[]
    for e in es:
        a,b=xy(e['start']),xy(e['end'])
        if e['type']=='Z_CURVE3D_LINE':curves.append(dict(type='line',start=a,end=b));continue
        if e['type']!='Z_CURVE3D_BSPLINE':raise ValueError('Unexpected mouth curve')
        m=xy(e['mid']);ax,ay=a;bx,by=m;cx,cy=b
        d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
        if abs(d)<1e-14:raise ValueError('Degenerate fitted corner')
        aa=ax*ax+ay*ay;bb=bx*bx+by*by;cc=cx*cx+cy*cy
        center=[(aa*(by-cy)+bb*(cy-ay)+cc*(ay-by))/d,(aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax))/d]
        angles=[math.atan2(p[1]-center[1],p[0]-center[0]) for p in (a,m,b)]
        start,mid,end=angles
        if (mid-start)%(2*math.pi)>(end-start)%(2*math.pi):start,end=end,start
        curves.append(dict(type='arc',center=center,radius=math.dist(a,center),start_angle=start,end_angle=end))
    if half:
        z=(-.0298 if half=='upper' else .0303)*sz;x=hx*sx
        curves.extend([dict(type='line',start=[-x,z],end=[-x,0]),dict(type='line',start=[-x,0],end=[x,0]),dict(type='line',start=[x,0],end=[x,z])])
    return curves

def make_plan(evidence_dir:Path, output:Path, expected_pid:int):
    survey=json.loads((evidence_dir/'mount-survey-02/result.json').read_text(encoding='utf-8'))
    if not survey['passed']: raise ValueError('Mount survey must pass')
    source={o['key']:o for o in survey['outputs']}
    mouths=json.loads((evidence_dir/'flange-survey-03/result.json').read_text(encoding='utf-8'))
    if not mouths['passed']:raise ValueError('Mouth measurement required')
    mouth_rows={o['key']:o['rows'] for o in mouths['outputs']}
    upper=mouth_curves(mouth_rows['L944-537-10MOL3'][0],'upper')
    lower=mouth_curves(mouth_rows['L944-537-10MOL3'][1],'lower')
    vent_mouth=mouth_curves(mouth_rows['D0536-07'][0])
    parts=[]; hardware=[]; cuts=[]; assets={}
    values={k:PARAMS[v] for k,v in ALIASES.items()}
    def pose(key,stage,name,pos,rotation=IDENTITY):
        if abs(determinant(rotation)-1)>1e-7: raise ValueError(f'Reflected frame {key}')
        return dict(key=key,stage=stage,name=name,position=[units(x) for x in pos],position_numeric=[expression(x) for x in pos],
                    initial=[number(x,values) for x in pos],rotation=rotation)
    def asset(file):
        file=file.resolve(); assets[str(file)]=dict(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest());return str(file)
    def box(key,name,dims,pos):
        p=pose(key,'plywood',name,pos); d=[number(x,values) for x in dims]
        # Local origin at one corner, preserved by the native anchor bindings.
        p.update(curves=[dict(type='line',start=a,end=b) for a,b in zip([[0,0],[d[0]/1000,0],[d[0]/1000,d[1]/1000],[0,d[1]/1000]],[[d[0]/1000,0],[d[0]/1000,d[1]/1000],[0,d[1]/1000],[0,0]])],
                 depth_m=d[2]/1000,size=[units(x) for x in dims],color=0x808040,
                 description='Prototyp montażowy. Wymiary i wycięcia sterowane parametrami sceny; odbiór konstruktora wymagany.')
        parts.append(p); return p
    # Butt joints: front/rear and horizontal panels fit between the side panels.
    # A 0.5 mm plywood seam is a prototype assembly clearance, NOT a selected joint profile.
    panels={}
    for lid in (False,True):
        prefix='lid' if lid else 'body'; label='Wieko zdejmowane' if lid else 'Korpus'
        z=f'{S}+0.25' if lid else '0'; height='L-0.25' if lid else f'{S}-0.25'
        for side,x in [('left','0'),('right',f'{E}-T')]:
            key=f'{prefix}/{side}';panels[key]=box(key,f'RockPro | {label} | '+('Lewa' if side=='left' else 'Prawa'),['T',F,height],[x,'0',z])
        for side,y in [('front','0'),('rear',f'{F}-T')]:
            key=f'{prefix}/{side}';panels[key]=box(key,f'RockPro | {label} | '+('Przód' if side=='front' else 'Tył'),['W','T',height],['T',y,z])
    panels['floor']=box('floor','RockPro | Korpus | Dno',['W','D','T'],['T','T','0'])
    panels['roof']=box('roof','RockPro | Wieko | Płyta górna',['W','D','T'],['T','T',f'{H}-T'])
    cornerfile=asset(evidence_dir/'vendor-import-01/C1339-30.ics')
    latchfile=asset(evidence_dir/'vendor-import-01/L944-537-10MOL3.ics')
    ventfile=asset(evidence_dir/'vendor-import-01/D0536-07.ics')
    handlefile=asset(evidence_dir/'handle-02/H2026_complete_source.ics')
    for ix,iy,iz in itertools.product((0,1),repeat=3):
        wanted=[1-2*ix,1-2*iy,1-2*iz]; r=None
        for perm in itertools.permutations(range(3)):
            for signs in itertools.product((-1,1),repeat=3):
                trial=[[int(j==perm[i])*signs[i] for j in range(3)] for i in range(3)]
                if determinant(trial)==1 and rotate([1,-1,-1],trial)==wanted:r=trial;break
            if r:break
        p=pose(f'corner/{ix}{iy}{iz}','corners','RockPro | C1339/30Z | Narożnik '+f'{ix}{iy}{iz}',[E if ix else '0',F if iy else '0',H if iz else '0'],r)
        p['file']=cornerfile;hardware.append(p)
    # use world-space positions then target origin subtraction with short names
    def cut(owner,target,name,curves,rot,world,depth):
        origins=[x for x in panels[target]['position_numeric']]
        back={v:k for k,v in ALIASES.items()}
        import re
        origins=[re.sub(r'RP_[A-Za-z_]+',lambda m:back[m[0]],x) for x in origins]
        p=pose(f'cut/{len(cuts)}','',name,[f'({world[i]})-({origins[i]})' for i in range(3)],rot)
        p.update(owner=owner,target=target,curves=curves,depth_m=depth);cuts.append(p)
    # Wall frames: native +Y points outside; native +Z points down.
    for rear in (False,True):
        u=[-1,0,0] if rear else [1,0,0]; n=[0,1,0] if rear else [0,-1,0]
        rot=[u,n,[0,0,-1]];side='rear' if rear else 'front'
        for i,xx in enumerate((f'{E}*0.25+0.1',f'{E}*0.75-0.1')):
            key=f'latch/{side}/{i}';y=F if rear else '0'
            p=pose(key,'closures',f'RockPro | MOL3 | '+('Tył' if rear else 'Przód')+f' | {i+1}',[xx,f'({y})+({n[1]}*0.05)',S],rot)
            p.update(file=latchfile,color=0x252525);hardware.append(p)
            # Keep each half at the seam; the measured mouth supersedes nominal dish sizes.
            for lid,h,cz in [(True,49,f'{S}+24.5'),(False,96,f'{S}-48')]:
                world=[xx,f'({y})+({n[1]}*12)',S]
                cut(key,('lid' if lid else 'body')+'/'+side,f'Wycięcie MOL3 | {side} {i+1} | '+('wieko' if lid else 'korpus'),upper if lid else lower,[u,[0,0,-1],[-v for v in n]],world,.04)
    for right in (False,True):
        side='right' if right else 'left';u=[0,1 if right else -1,0];n=[1 if right else -1,0,0];rot=[u,n,[0,0,-1]];x=E if right else '0'
        key='vent/'+side;p=pose(key,'closures','RockPro | D0536/07K | Wentylacja '+side,[f'({x})+({n[0]}*0.05)',f'{F}/2',f'{S}*0.48'],rot);p.update(file=ventfile,color=0x202020);hardware.append(p)
        cut(key,'body/'+side,'Wycięcie wentylacji | '+side,vent_mouth,[u,[0,0,-1],[-v for v in n]],[f'({x})+({n[0]}*12)',f'{F}/2',f'{S}*0.48'],.04)
    # Actual EG-0100 section from constructor. Canonical axes point inward from outer corner.
    section=source['M01']['rows'][0]['features'][0]['curves']
    def profile(key,name,a,b,pos,length):
        axial=cross(a,b); rot=[[-v for v in a],[-v for v in b],axial]
        # Normalize the measured section explicitly to a positive 30 x 30 box.
        # SizeBox.Reset normalizes its anchor; match it before binding length.
        # Original outer corner (0,.00675) becomes (30,30) mm.
        offset=[-30*rot[0][i]-30*rot[1][i] for i in range(3)]
        p=pose(key,'profiles',name,[f'({pos[i]})+({offset[i]})' for i in range(3)],rot)
        curves=[]
        for c in section:
            d={k:v for k,v in c.items() if k!='id'};d['type']='arc' if 'ARC' in c['type'] else 'line'
            for key2 in ('start','end','center'):
                if key2 in d:d[key2]=[d[key2][0]+.03,d[key2][1]+.02325]
            curves.append(d)
        p.update(curves=curves,depth_m=number(length,values)/1000,size=[units(length)],color=0xC0C0C0,description='EG-0100: rzeczywisty przekrój z modelu konstruktora, zmienna tylko długość wyciągnięcia. Dobór złącza wieka niezatwierdzony.')
        parts.append(p);return p
    profile_map={}
    # Horizontal edges. Start direction is the cross product of inward axes.
    for top in (False,True):
        sz=-1 if top else 1;z=f'{H}+1.45' if top else '-1.45'
        for rear in (False,True):
            sy=-1 if rear else 1;axis=cross([0,sy,0],[0,0,sz])[0]
            profile(f'profile/x/{top}/{rear}','RockPro | EG-0100 | Krawędź pozioma X', [0,sy,0],[0,0,sz],['70' if axis>0 else f'{E}-70',f'{F}+1.45' if rear else '-1.45',z],f'{E}-140')
        for right in (False,True):
            sx=-1 if right else 1;axis=cross([sx,0,0],[0,0,sz])[1]
            p=profile(f'profile/y/{top}/{right}','RockPro | EG-0100 | Krawędź pozioma Y',[sx,0,0],[0,0,sz],[f'{E}+1.45' if right else '-1.45','70' if axis>0 else f'{F}-70',z],f'{F}-140')
            if top:profile_map['right' if right else 'left']=p
    for right,rear in itertools.product((False,True),repeat=2):
        a=[-1 if right else 1,0,0];b=[0,-1 if rear else 1,0];up=cross(a,b)[2]>0
        for lid in (False,True):
            low=f'{S}+0.25' if lid else '70';high=f'{H}-70' if lid else f'{S}-0.25'
            profile(f'profile/z/{right}/{rear}/{lid}','RockPro | EG-0100 | Krawędź pionowa',[*a],[*b],[f'{E}+1.45' if right else '-1.45',f'{F}+1.45' if rear else '-1.45',low if up else high],f'({high})-({low})')
    # H2026 and its source-linked machining: common rigid mapping from constructor edge.
    m03={r['id']:r for r in source['M03']['rows']};root=m03[3886]['matrix_m'];source_edge=[root[12],.2624438130828361,1.0821166596935014]
    for right in (False,True):
        side='right' if right else 'left';u=[0,1 if right else -1,0];inward=[-1 if right else 1,0,0];mapping=[u,inward,[0,0,1]]
        for i,fraction in enumerate((.3,.7)):
            edge=[E if right else '0',f'{F}*{fraction}',H];key=f'handle/{side}/{i}'
            rot=[rotate(root[j*4:j*4+3],mapping) for j in range(3)]
            off=rotate([(root[12+k]-source_edge[k])*1000 for k in range(3)],mapping)
            p=pose(key,'handles',f'RockPro | H2026 | {side} | {i+1}',[f'({edge[k]})+({off[k]})' for k in range(3)],rot);p['file']=handlefile;hardware.append(p)
            for source_id,target in [(1023,'lid/'+side),(1035,'roof'),(1062,profile_map[side]['key'])]:
                feature=m03[source_id]['features'][0];matrix=feature['profile_matrix_m'];rotcut=[rotate(matrix[j*4:j*4+3],mapping) for j in range(3)]
                off=rotate([(matrix[12+k]-source_edge[k])*1000 for k in range(3)],mapping)
                world=[f'({edge[k]})+({off[k]})' for k in range(3)]
                curves=[dict(type='line',start=c['start'],end=c['end']) for c in feature['curves']]
                if determinant(rotcut)<0:
                    rotcut[0]=[-v for v in rotcut[0]]
                    curves=[dict(type='line',start=[-c['start'][0],c['start'][1]],end=[-c['end'][0],c['end'][1]]) for c in curves]
                if target.startswith('profile/'):
                    # Convert the common world cutter into the rotated profile's local frame.
                    pr=profile_map[side];rotp=pr['rotation'];delta=[f'({world[k]})-({pr["position_numeric"][k]})' for k in range(3)]
                    back={v:k for k,v in ALIASES.items()};import re
                    delta=[re.sub(r'RP_[A-Za-z_]+',lambda m:back[m[0]],d) for d in delta]
                    local=[ '+'.join(f'({delta[k]})*({rotp[j][k]})' for k in range(3)) for j in range(3)]
                    rc=[[dot(row,axis) for axis in rotp] for row in rotcut]
                    c=pose(f'cut/{len(cuts)}','',f'Wycięcie H2026 w profilu | {side} {i+1}',local,rc);c.update(owner=key,target=target,curves=curves,depth_m=feature['forward']);cuts.append(c)
                else:
                    legacy_name=f'Wycięcie H2026 | {target} | {i+1}'
                    cut(key,target,legacy_name+' | '+side,curves,rotcut,world,feature['forward'])
                    cuts[-1]['legacy_name']=legacy_name
    # AH 4903M8AH: no manufacturer CAD available. Nominal native solid and mounting hole.
    feet=[('70','70'),('70',f'{F}-70'),(f'{E}/2','70'),(f'{E}/2',f'{F}-70'),(f'{E}-70','70'),(f'{E}-70',f'{F}-70'),(f'{E}/2',f'{F}/3'),(f'{E}/2',f'{F}*2/3')]
    for i,(x,y) in enumerate(feet):
        key=f'foot/{i}';p=pose(key,'wheels',f'RockPro | 4903M8AH | Nóżka {i+1} | model nominalny',[x,y,'-9']);p.update(curves=[dict(type='circle',center=[0,0],radius=.01),dict(type='circle',center=[0,0],radius=.0022)],depth_m=.009,color=0x202020,description='Geometria nominalna Ø20 × 9 mm, otwór Ø4,4 mm. Odtworzenie z wymiarów Adam Hall; NIE jest plikiem CAD producenta. 8 sztuk = 1 opakowanie.');parts.append(p)
    # Evaluate expanded expressions for the native resize checks.
    changed=dict(PARAMS);changed.update(RP_Szerokosc_wnetrza=837,RP_Glebokosc_wnetrza=698,RP_Wysokosc_wnetrza=859,RP_Wysokosc_wieka_gornego=128)
    changed_checks=[dict(key=p['key'],initial=[number(x,changed) for x in p['position_numeric']]) for p in parts+hardware]
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Integracja'))
    from rockpro_cad.part_registry import STAGES
    groups=[dict(key=s['id'],name=f"{s['order']:02} | {s['label']}") for s in STAGES]
    notes={ALIASES[k]:v for k,v in dict(W='Szerokość wymaganej przestrzeni wewnętrznej korpusu w osi X; sklejka na zewnątrz tego wymiaru.',D='Głębokość wymaganej przestrzeni wewnętrznej korpusu w osi Y.',B='Wysokość bazowej przestrzeni wewnętrznej. Wieko jest dodatkową sekcją, nie zabiera tej przestrzeni.',T='Grubość sklejki 9,8 mm. Zmiana wymaga ponownego doboru profili i obróbek; nie jest rozmiarem okucia.',L='Całkowita wysokość dodatkowego wieka zdejmowanego; H2026 związane z jego górną krawędzią. Minimum musi pomieścić górną połówkę zamka 65 mm i profil 30 mm z luzem.').items()}
    return dict(contract='rockpro-requested-case-2027-v1',expected_pid=expected_pid,parameters=PARAMS,notes=notes,groups=groups,parts=parts,hardware=hardware,cuts=cuts,assets=list(assets.values()),changed_parameters=changed,changed_checks=changed_checks,output=str(output.resolve()),production_approved=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('evidence',type=Path);p.add_argument('output_ics',type=Path);p.add_argument('request',type=Path);p.add_argument('--pid',type=int,required=True);a=p.parse_args()
    plan=make_plan(a.evidence,a.output_ics,a.pid);a.request.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(parts=len(plan['parts']),hardware=len(plan['hardware']),cuts=len(plan['cuts']),assets=len(plan['assets']))))
if __name__=='__main__':main()
