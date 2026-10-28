"""Parametrisation migration for an identified, measured Studio T1 copy.

No CAD calls, file writes, inferred cut contours or catalogue scaling here.
The saved request and a native inventory must describe the exact source bytes.
"""
import ast
import copy
import itertools
import math
import re


def number(expression, values):
    """Evaluate only arithmetic emitted by our compiler, in millimetres."""
    tree = ast.parse(re.sub(r'\bmm\b', '', expression), mode='eval')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (float, int):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
        raise ValueError('Niedozwolone wyrażenie parametrów')
    result = visit(tree.body)
    if not math.isfinite(result): raise ValueError('Nieskończony parametr')
    return result


def envelope(spec, inventory):
    roots = [n for n in inventory['rows'] if n['name'] == spec['label']+' | '+spec['id']]
    if len(roots) != 1: raise ValueError('Niejednoznaczne wystąpienie '+spec['id'])
    root = roots[0]
    points = []
    for row in inventory['rows']:
        if (row['path'] == root['path'] or row['path'].startswith(root['path']+'/')) and 'bounds_local_m' in row:
            b, m = row['bounds_local_m'], row['world_mm']
            for p in itertools.product(*[(b[k]*1000, b[k+3]*1000) for k in range(3)]):
                points.append([sum(p[k]*m[k][j] for k in range(3))+m[3][j] for j in range(3)])
    if not points: raise ValueError('Brak zmierzonego obrysu '+spec['id'])
    # Orthogonal T1 transforms make these union bounds exact, not a rotated AABB approximation.
    for row in inventory['rows']:
        if row['path'] == root['path'] or row['path'].startswith(root['path']+'/'):
            if any(sum(abs(x)>1e-7 for x in axis[:3]) != 1 for axis in row['world_mm'][:3]):
                raise ValueError('Obrócony obrys wymaga osobnego pomiaru '+spec['id'])
    return root, [min(p[k] for p in points) for k in range(3)]+[max(p[k] for p in points) for k in range(3)]


def section(spec, height):
    key = spec['id']
    if 'pad/' in key or spec.get('part_id') == 'source-caster-epson' or key == 'panel/body/bottom' or key.startswith('structure/bottom/'):
        return 'foundation'
    if spec.get('section_id') == 'top' or spec.get('part_id') == 'W0968Z' or key.startswith(('structure/top/', 'structure/lid/', 'structure/EG-0500_2/')):
        return 'lid'
    if spec.get('part_id') == '410429' and spec['position_mm'][2] > height:
        return 'lid'
    return 'foundation'


def evaluate(spec, overrides=None):
    result = copy.deepcopy(spec)
    values = dict(spec['parameters'])
    derived = spec['derived_parameters']
    if overrides:
        if set(overrides)-set(values) or set(overrides)&set(derived):
            raise ValueError('Zmiana nieznanego lub wyliczanego parametru')
        values.update(overrides)
    for name in spec['scalar_parameters']:
        if values[name] not in (0, 1): raise ValueError('Tryb wymaga 0 albo 1: '+name)
    for name, expr in derived.items(): values[name] = number(expr, values)
    result['parameters'] = values
    for collection in ('panels', 'parts', 'cuts'):
        for row in result[collection]:
            row['position_mm'] = [number(x, values) for x in row['position_expressions']]
            if 'size_expressions' in row:
                row['size_mm'] = [number(x, values) for x in row['size_expressions']]
            if 'profile_length_expression' in row:
                row['profile_length_mm'] = number(row['profile_length_expression'], values)
            if collection == 'panels':
                low = row['expected_body_bounds_local_mm'][:3]
                row['expected_body_bounds_local_mm'] = low+row['size_mm']
                row['expected_body_size_mm'] = [row['size_mm'][k]-low[k] for k in range(3)]
    validate(result)
    return result


def validate(spec):
    """Preflight for the mapped configuration, not a live arbitrary-edit add-in."""
    p = spec['parameters']
    if p['RP_GruboscSklejki'] != 9.8: raise ValueError('Stałe pasowanie 9,8 mm')
    if min(p[n] for n in ('RP_SzerokoscWnetrza','RP_GlebokoscWnetrza','RP_WysokoscWnetrza','RP_WysokoscPokrywy')) <= 0:
        raise ValueError('Niedodatni gabaryt')
    rows = {s['id']:s for k in ('panels','parts') for s in spec[k]}
    W = p['RP_SzerokoscWnetrza']+2*p['RP_GruboscSklejki']
    D = p['RP_GlebokoscWnetrza']+2*p['RP_GruboscSklejki']
    for prefix in ('Zawiasy','Uchwyty','KolaX','KolaY'):
        if p['RP_'+prefix+'_RozstawRzeczywisty'] <= 0: raise ValueError('Odwrócona kolejność '+prefix)
        if p['RP_'+prefix+'_RozstawRzeczywisty'] < spec['accessory_row_envelopes'][prefix]['minimum_pitch_mm']-1e-5:
            raise ValueError('Kolizja sąsiednich okuć '+prefix)
        if min(p['RP_'+prefix+'_MarginesRzeczywistyLewy'],p['RP_'+prefix+'_MarginesRzeczywistyPrawy']) < 37-1e-5:
            raise ValueError('Okucie wchodzi w strefę profili/narożników '+prefix)
    handle = p['RP_Uchwyty_WysokoscRzeczywista']
    low,high=spec['handle_vertical_envelope_mm']
    if handle+low < 37 or handle+high > p['RP_WysokoscWnetrza']-37:
        raise ValueError('Uchwyt zbyt blisko profilu lub strefy zawiasu')
    for row in spec['panels']:
        if min(row['size_mm']) <= 0: raise ValueError('Niedodatnia płyta/podpora')
        if 'pad/' in row['id']:
            x,y,_ = row['position_mm'];sx,sy,_=row['size_mm']
            if min(x,y,W-x-sx,D-y-sy) < 35-1e-5:
                raise ValueError('Podpora wchodzi w profil obwodowy')
    sockets = [r for r in spec['parts'] if r.get('part_id') == 'W0968Z']
    seats = []
    for s in sockets:
        wheel = rows[s['paired_wheel_id']]
        contact = [sum(v*wheel['rotation'][k][j] for k,v in enumerate((-36.,-132.1,0.)))+wheel['position_mm'][j] for j in range(3)]
        seat = [s['position_mm'][0], s['position_mm'][1]+58.21088152752006]
        if max(abs(seat[k]-contact[k]) for k in (0,1)) > 1e-5:
            raise ValueError('Rozłączone koło i gniazdo')
        if min(seat[0]-68,W-seat[0]-68,seat[1]-45,D-seat[1]-45) < 37-1e-5:
            # Original Y margin 55 mm; the original configuration is legal.
            raise ValueError('Gniazdo w strefie profilu/narożnika')
        seats.append(seat)
    for a,b in itertools.combinations(seats,2):
        if abs(a[0]-b[0]) < 138-1e-5 and abs(a[1]-b[1]) < 92-1e-5:
            raise ValueError('Kolizja gniazd pod koła')


def migrate(request, inventory):
    """Preserve topology and baseline, add explicit spacing/margin modes."""
    if request.get('contract') != 'roc46-native-v1' or inventory.get('errors'):
        raise ValueError('Wymagany zmierzony model Studio T1 bez błędów')
    out = copy.deepcopy(request)
    for key in ('changed_expected','check_cases','changed_parameters','plan_sha256'):
        out.pop(key, None)
    out['mode'] = 'accessory-update'
    out['sources'] = [dict(key='model',path=inventory['source'],sha256=inventory['source_sha256'])]
    out['physical_groups'] = [dict(id='lid',label='Wieko 1'),dict(id='foundation',label='Podstawa')]
    out['derived_parameters'] = {}
    out['scalar_parameters'] = []
    out['accessory_counts'] = dict(hinges=2,handles_per_wall=2,wheels=4,sockets=4)
    out['accessory_row_envelopes'] = {}
    parts = {r['id']:r for k in ('panels','parts') for r in out[k]}
    originals = copy.deepcopy(parts)
    bounds = {}
    for row in parts.values():
        source, bound = envelope(row, inventory)
        matrix=source['world_mm']
        if any(abs(matrix[3][j]-row['position_mm'][j])>1e-5 for j in range(3)) or any(abs(matrix[k][j]-row['rotation'][k][j])>1e-6 for k in range(3) for j in range(3)):
            raise ValueError('Plan nie opisuje zmierzonej sceny '+row['id'])
        row['source_native_id'] = source['id']; row['source_name'] = source['name']
        row['physical_group'] = section(row, out['parameters']['RP_WysokoscWnetrza'])
        bounds[row['id']] = bound
        face = dict(left='lewa',right='prawa',front='przód',rear='tył',top='góra',bottom='dno')
        name = row['id'].split('/')[-1]
        row['label'] = ('Sklejka — '+face.get(row.get('face'),name) if row in out['panels'] else
                        {'H7159':'Uchwyt wpuszczany','270836':'Zawias','17251S':'Zamek','source-caster-epson':'Koło skrętne','W0968Z':'Gniazdo pod koło'}.get(row.get('part_id'),'Profil / wzmocnienie')+' — '+row.get('part_id','')+' — '+name)
    if len(parts) != 72 or any(len([r for r in out['parts'] if r.get('part_id')==sku]) != count for sku,count in [('H7159',4),('270836',4),('source-caster-epson',4),('W0968Z',4)]):
        raise ValueError('Inna topologia: migracja dotyczy 2 zawiasów, 2 uchwytów na bok i 4 kół')
    def param(name,value,note,expr=None,scalar=False):
        out['parameters'][name] = value
        out['parameter_notes'][name] = note
        if expr is not None: out['derived_parameters'][name] = expr
        if scalar: out['scalar_parameters'].append(name)
        return name
    def mm(x): return f'({x:.12g} mm)'
    # A row's envelope extremes refer to its own native mounting datum. The
    # mirrored wheel orientation has different extremes; keep them separate.
    def row_controls(prefix,low,high,axis,length):
        a,b = low['position_mm'][axis],high['position_mm'][axis]
        umin = bounds[low['id']][axis]-a
        umax = bounds[high['id']][axis+3]-b
        size = number(length,out['parameters'])
        out['accessory_row_envelopes'][prefix]=dict(minimum_pitch_mm=bounds[low['id']][axis+3]-a-(bounds[high['id']][axis]-b)+2)
        stem = 'RP_'+prefix+'_'
        mode = param(stem+'TrybOdBrzegow',1,'Tryb: 1 = sterują marginesy od skrajów okucia do brzegów ścianki; 0 = steruje zadany rozstaw i środek. Bez jednostki; tylko 0/1.',scalar=True)
        left = param(stem+'MarginesLewy',a+umin,'mm. Steruje tylko w trybie 1: od pierwszego brzegu gotowej ścianki do zewnętrznego skraju całego okucia.')
        right = param(stem+'MarginesPrawy',size-b-umax,'mm. Steruje tylko w trybie 1: od drugiego brzegu gotowej ścianki do zewnętrznego skraju całego okucia.')
        pitch = param(stem+'RozstawZadany',b-a,'mm. Steruje tylko w trybie 0; odległość odpowiadających kotew montażowych. Liczba elementów pozostaje stała.')
        center = param(stem+'PrzesuniecieSrodka',0,'mm. Steruje tylko w trybie 0; przesunięcie środka grupy od połowy gotowej ścianki, dodatnie wzdłuż osi.')
        # Keep the original native-datum asymmetry when centring the envelope.
        datum_center_offset = (a+b-size)/2
        first = f'{mode} * ({left} - {mm(umin)}) + (1 - {mode}) * (({length})/2 + {mm(datum_center_offset)} + {center} - {pitch}/2)'
        last = f'{mode} * (({length}) - {right} - {mm(umax)}) + (1 - {mode}) * (({length})/2 + {mm(datum_center_offset)} + {center} + {pitch}/2)'
        param(stem+'RozstawRzeczywisty',b-a,'WYLICZONY, mm. Aktywny rozstaw wynikający z wybranego trybu; nie nadpisywać.',f'({last}) - ({first})')
        param(stem+'MarginesRzeczywistyLewy',a+umin,'WYLICZONY, mm. Rzeczywisty prześwit od pierwszego brzegu do zewnętrznego skraju okucia.',f'({first}) + {mm(umin)}')
        param(stem+'MarginesRzeczywistyPrawy',size-b-umax,'WYLICZONY, mm. Rzeczywisty prześwit od drugiego brzegu do zewnętrznego skraju okucia.',f'({length}) - ({last}) - {mm(umax)}')
        return first,last
    W='RP_SzerokoscWnetrza + 2*RP_GruboscSklejki'
    D='RP_GlebokoscWnetrza + 2*RP_GruboscSklejki'
    hinges=sorted([r for r in out['parts'] if r.get('part_id')=='270836' and r['half']=='base'],key=lambda r:r['position_mm'][0])
    for h,expr in zip(hinges,row_controls('Zawiasy',*hinges,0,W)):
        for half in ('base','lid'): parts[h['id'].rsplit('/',1)[0]+'/'+half]['position_expressions'][0]=expr
    handles=sorted([r for r in out['parts'] if r.get('part_id')=='H7159' and r['face']=='left'],key=lambda r:r['position_mm'][1])
    expressions=row_controls('Uchwyty',*handles,1,D)
    height = handles[0]['position_mm'][2]-out['parameters']['RP_GruboscSklejki']
    out['handle_vertical_envelope_mm']=[bounds[handles[0]['id']][j]-handles[0]['position_mm'][2] for j in (2,5)]
    param('RP_Uchwyty_WysokoscOdDolu',height,'mm. Wysokość kotwy uchwytu od dolnego brzegu bocznej płyty korpusu. Steruje w trybie wysokości 0.')
    param('RP_Uchwyty_UdzialWysokosci',height/out['parameters']['RP_WysokoscWnetrza'],'Bez jednostki: udział wysokości bocznej płyty; steruje w trybie wysokości 1.')
    out.setdefault('dimensionless_parameters',[]).append('RP_Uchwyty_UdzialWysokosci')
    param('RP_Uchwyty_TrybWysokosci',0,'Bez jednostki. 0 = wysokość od dołu w mm; 1 = udział wysokości bocznej płyty.',scalar=True)
    param('RP_Uchwyty_WysokoscRzeczywista',height,'WYLICZONA, mm. Wysokość montażowej kotwy uchwytu nad dolnym brzegiem płyty.', '(1 - RP_Uchwyty_TrybWysokosci)*RP_Uchwyty_WysokoscOdDolu + RP_Uchwyty_TrybWysokosci*RP_Uchwyty_UdzialWysokosci*RP_WysokoscWnetrza')
    for face in ('left','right'):
        row=sorted([r for r in out['parts'] if r.get('part_id')=='H7159' and r['face']==face],key=lambda r:r['position_mm'][1])
        for h,expr in zip(row,expressions):
            h['position_expressions'][1]=expr
            h['position_expressions'][2]='RP_GruboscSklejki + RP_Uchwyty_WysokoscRzeczywista'
    wheels={r['id']:r for r in out['parts'] if r.get('part_id')=='source-caster-epson'}
    xexpr=row_controls('KolaX',wheels['structure/wheel-00'],wheels['structure/wheel-10'],0,W)
    yexpr=row_controls('KolaY',wheels['structure/wheel-00'],wheels['structure/wheel-01'],1,D)
    for key,wheel in wheels.items():
        ix,iy = map(int,key[-2:])
        wheel['position_expressions'][:2]=[xexpr[ix],yexpr[iy]]
        socket=parts['structure/socket/'+key.split('/')[-1]]
        socket['paired_wheel_id']=key
        for axis in (0,1): socket['position_expressions'][axis]=f'({wheel["position_expressions"][axis]}) + {mm(socket["position_mm"][axis]-wheel["position_mm"][axis])}'
    for ix in (0,1):
        pad=parts['structure/pad/'+str(ix)]
        pad['position_expressions'][:2]=[f'({xexpr[ix]}) - 60 mm',f'({yexpr[0]}) - 65 mm']
        pad['size_expressions'][1]=f'({yexpr[1]}) - ({yexpr[0]}) + 130 mm'
    # The same rigid world-space displacement is expressed in the target's
    # local frame. The actual saved contour is never replaced with an AABB.
    for cut in out['cuts']:
        owner,target=parts[cut['owner_id']],parts[cut['target_id']]
        oldowner,oldtarget=originals[cut['owner_id']],originals[cut['target_id']]
        deltas=[f'(({owner["position_expressions"][j]}) - ({oldowner["position_expressions"][j]})) - (({target["position_expressions"][j]}) - ({oldtarget["position_expressions"][j]}))' for j in range(3)]
        cut['position_expressions']=[f'({old})'+''.join(f' + ({target["rotation"][axis][j]})*({deltas[j]})' for j in range(3) if target['rotation'][axis][j]) for axis,old in enumerate(cut['position_expressions'])]
    out['dimensionless_parameters']=out.get('dimensionless_parameters',[])+out['scalar_parameters']
    result=evaluate(out)
    for collection in ('panels','parts','cuts'):
        for before,after in zip(request[collection],result[collection]):
            if any(abs(a-b)>1e-5 for a,b in zip(before['position_mm'],after['position_mm'])):
                raise ValueError('Migracja zmieniłaby położenie początkowe '+before['id'])
    return result


def with_checks(spec):
    out=copy.deepcopy(spec)
    updates=[('margines_zawiasow',{'RP_Zawiasy_MarginesLewy':spec['parameters']['RP_Zawiasy_MarginesLewy']+8}),
             ('rozstaw_zawiasow',{'RP_Zawiasy_TrybOdBrzegow':0,'RP_Zawiasy_RozstawZadany':spec['parameters']['RP_Zawiasy_RozstawZadany']-20}),
             ('uchwyty_rozstaw_i_wysokosc',{'RP_Uchwyty_TrybOdBrzegow':0,'RP_Uchwyty_RozstawZadany':spec['parameters']['RP_Uchwyty_RozstawZadany']-12,'RP_Uchwyty_WysokoscOdDolu':spec['parameters']['RP_Uchwyty_WysokoscOdDolu']+15}),
             ('kola_os_X',{'RP_KolaX_MarginesLewy':spec['parameters']['RP_KolaX_MarginesLewy']+8,'RP_KolaX_MarginesPrawy':spec['parameters']['RP_KolaX_MarginesPrawy']+8}),
             ('kola_os_Y',{'RP_KolaY_TrybOdBrzegow':0,'RP_KolaY_RozstawZadany':spec['parameters']['RP_KolaY_RozstawZadany']-10}),
             ('gabaryty_i_uchwyty_proporcjonalne',{'RP_SzerokoscWnetrza':617,'RP_GlebokoscWnetrza':523,'RP_WysokoscWnetrza':831,'RP_Uchwyty_TrybWysokosci':1})]
    out['check_cases']=[]
    for name,changes in updates:
        expected=evaluate(spec,changes)
        out['check_cases'].append(dict(name=name,parameters=expected['parameters'],expectedposes=expected['panels']+expected['parts'],expectedpanels=expected['panels'],expectedcuts=expected['cuts']))
    return out


def regroup_saved_copy(spec, receipt):
    """Migrate the identified saved parameterised copy, keeping its expressions.

    The constructor corrected the physical meaning: the permanent body belongs
    to Podstawa. Only an actual cover gets a numbered Wieko assembly.
    """
    if receipt.get('passed') is not True or receipt.get('sources_unchanged') is not True:
        raise ValueError('Wymagany udany kwit wcześniejszej kopii')
    final=receipt.get('final_file_reopened',{})
    if final.get('passed') is not True or receipt.get('parameters') != spec.get('parameters'):
        raise ValueError('Brak zgodnego pomiaru końcowego pliku')
    measured={r['id']:r['native_id'] for r in final['occurrences']}
    out=copy.deepcopy(spec)
    out['sources']=[dict(key='model',path=receipt['output_path'],sha256=receipt['output_sha256'])]
    out['input_groups']=[g['label'] for g in spec['physical_groups']]
    out['physical_groups']=[dict(id='lid',label='Wieko 1'),dict(id='foundation',label='Podstawa')]
    for row in out['panels']+out['parts']:
        row['source_native_id']=measured[row['id']]
        row['source_name']=row['label']+' | '+row['id']
        if row['physical_group']=='body':row['physical_group']='foundation'
    for case in out.get('check_cases',[]):
        for row in case['expectedposes']+case['expectedpanels']:
            if row['physical_group']=='body':row['physical_group']='foundation'
    return out
