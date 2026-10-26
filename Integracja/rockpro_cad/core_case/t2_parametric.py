"""Source-pinned T2 depth/height prototype; fixed-width rack and opaque hardware.

This is an experimental recipe, never a promoted family manifest or fit approval.
The original occurrence matrices (including mirrors) are retained. Only native
positive panel/profile feature dimensions are changed, never catalog solids.
"""
import copy
import hashlib
import itertools
import json
import math
from .t2_family import draft_with_source_frames

SOURCE_SHA = 'e7dccb157f58ffec249c4634896b71b831b6228354afd688f37ba83f50cb75cb'
REFERENCE = {'RP_GlebokoscObudowy':627., 'RP_WysokoscObudowy':506.5,
             'RP_UniesienieCzapki':0., 'RP_OdsuniecieKlapy':0.,
             'RP_UniesienieRacka':0., 'RP_PrzesuniecieUchwytow':0.,
             'RP_PodniesienieUchwytow':0.}
NOTES = {
 'RP_GlebokoscObudowy':'Głębokość obrysu sklejki, oś Y. Wzorzec 627 mm. Zakres prototypu 627–827 mm; bez wystających okuć. Klapa zachowuje własną grubość.',
 'RP_WysokoscObudowy':'Wysokość obrysu sklejki zamkniętej obudowy, oś Z. Wzorzec 506,5 mm; zakres 506,5–706,5 mm. Zmiana zwiększa wysokość czapki i klapy, spód pozostaje bez zmian.',
 'RP_UniesienieCzapki':'Prezentacyjne uniesienie zdejmowanej czapki w osi Z. Rack nie podnosi się z czapką. 0 mm oznacza położenie zamknięte. To nie symulacja toru demontażu.',
 'RP_OdsuniecieKlapy':'Prezentacyjne odsunięcie przedniej klapy w kierunku −Y. 0 mm oznacza położenie zamknięte. Nie zmienia wymiarów cięcia ani szczelin montażowych.',
 'RP_UniesienieRacka':'Niezależne prezentacyjne podniesienie racka w osi Z. Zachowuje szerokość i geometrię modułu. Dodatnia wartość nie jest potwierdzeniem bezkolizyjnego wyjmowania.',
 'RP_PrzesuniecieUchwytow':'Przesunięcie uchwytów bocznych wraz z otworami i podfrezowaniami podpór w osi Y. Zakres prototypu −10…10 mm. Uchwyt przedniej klapy pozostaje wyśrodkowany.',
 'RP_PodniesienieUchwytow':'Podniesienie trzech uchwytów razem z powiązanymi wycięciami w osi Z. Zakres prototypu −10…10 mm. Zachowano liczbę uchwytów wzorca T2.',
}


def validate_parameters(parameters):
    if set(parameters)!=set(REFERENCE):raise ValueError('T2: wymagany dokładny zestaw parametrów prototypu')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in parameters.values()):raise ValueError('T2: parametry muszą być skończonymi liczbami')
    for n in ('RP_GlebokoscObudowy','RP_WysokoscObudowy'):
        if not REFERENCE[n]<=parameters[n]<=REFERENCE[n]+200:raise ValueError('T2: wymiar poza zakresem prototypu')
    for n in ('RP_UniesienieCzapki','RP_OdsuniecieKlapy','RP_UniesienieRacka'):
        if not 0<=parameters[n]<=600:raise ValueError('T2: rozsunięcie poza zakresem prototypu')
    for n in ('RP_PrzesuniecieUchwytow','RP_PodniesienieUchwytow'):
        if abs(parameters[n])>10:raise ValueError('T2: przesunięcie uchwytu poza zakresem prototypu')
    return dict(parameters)


def point(p,m):return [m[3][j]+sum(p[k]*m[k][j] for k in range(3)) for j in range(3)]
def bbox_world(row):
    b=[x*1000 for x in row['bounds_local_m']];m=row['world_mm']
    corners=[point([b[j+3*q[j]] for j in range(3)],m) for q in itertools.product((0,1),repeat=3)]
    return [min(p[j] for p in corners) for j in range(3)]+[max(p[j] for p in corners) for j in range(3)]
def expression(initial,coefficients):
    terms=[f'{initial:.15g} mm']
    for name,c in coefficients.items():
        if abs(c)>1e-9:terms.append(f'({c:.15g})*({name}-({REFERENCE[name]:.15g} mm))')
    return ' + '.join(terms)
def evaluate(initial,coefficients,parameters):return initial+sum(c*(parameters[n]-REFERENCE[n]) for n,c in coefficients.items())
def zero():return {n:[0.,0.,0.] for n in REFERENCE}
def coeff_for_axis(motion,axis):return {n:v[axis] for n,v in motion.items()}
def combine_local(motion,parent_motion,parent_matrix):
    return {n:[sum((motion[n][j]-parent_motion[n][j])*parent_matrix[i][j] for j in range(3)) for i in range(3)] for n in REFERENCE}


def node_label(row,semantic,minimum,maximum):
    owner={'base':'spód','hood':'czapka','front_cap':'klapa przednia'}.get(semantic['owner'],'')
    names={'structural_base':'Spód','removable_hood':'Zdejmowana czapka',
           'removable_front_cap':'Zdejmowana klapa przednia','removable_rack':'Rack',
           'profile_group':'Profile','carry_handle':'Uchwyt','latch_half':'Zamek',
           'corner_or_brace':'Narożnik lub wzmocnienie','corner_wheel':'Koło narożne',
           'trolley_handle':'Uchwyt teleskopowy','rack_support_left':'Lewa podpora racka',
           'rack_support_right':'Prawa podpora racka','foam':'Piana','interior':'Wnętrze',
           'mixer_spacers':'Dystanse urządzenia','device_reference':'Urządzenie referencyjne'}
    role=semantic['role']
    if role=='outer_panel':
        b=bbox_world(row);axis=min(range(3),key=lambda j:b[j+3]-b[j])
        high=(b[axis]+b[axis+3])>(minimum[axis]+maximum[axis])
        face=[('lewa ściana','prawa ściana'),('przednia ściana','tylna ściana'),('dno','górna płyta')][axis][high]
        return f'RockPro T2 | Sklejka | {owner} | {face}'
    return ' | '.join(x for x in ('RockPro T2',names.get(role,role),owner,row['name'].strip()) if x)


def make_recipe(reference,inventory_bytes):
    draft_with_source_frames(reference,inventory_bytes)  # exact provenance/identity gate
    if reference['source_sha256']!=SOURCE_SHA:raise ValueError('T2: nieobsługiwana rewizja źródła')
    inv=json.loads(inventory_bytes.decode('utf-8-sig'));rows=inv['rows'];by={r['id']:r for r in rows}
    roles={r['source_id']:r for r in reference['parts']}
    hardware={h['source_id'] for h in reference['hardware_roots']}
    paths={r['path']:r for r in rows};root=rows[0]
    rack_path=by[6366]['path']
    panels=[r for r in rows if roles[r['id']]['role']=='outer_panel']
    boxes=[bbox_world(r) for r in panels]
    minimum=[min(b[j] for b in boxes) for j in range(3)];maximum=[max(b[j+3] for b in boxes) for j in range(3)]
    size=[maximum[j]-minimum[j] for j in range(3)]
    if max(abs(a-b) for a,b in zip(size,[548,627,506.5]))>.005:raise ValueError('T2: zmienione bazy obrysu sklejki')
    def rigid_root(row):
        ancestors=[int(x) for x in row['path'].split('/')[1:]]
        return next((i for i in ancestors if i in hardware),None)
    def world_box(row):
        leaves=[r for r in rows if r.get('bounds_local_m') and (r['path']==row['path'] or r['path'].startswith(row['path']+'/'))]
        bs=[bbox_world(r) for r in leaves]
        if not bs:raise ValueError('T2: brak geometrii do bazy montażowej')
        return [min(b[j] for b in bs) for j in range(3)]+[max(b[j+3] for b in bs) for j in range(3)]
    def depth_weight(y,owner,role):
        if owner=='front_cap':return 0.
        if role=='trolley_handle':return 0.  # source grip/slot is on the front edge
        if role in ('removable_rack','rack_support_left','rack_support_right','device_reference','mixer_spacers'):return .5
        if y<minimum[1]+250:return 0.
        if y>maximum[1]-250:return 1.
        return .5
    def height_weight(z,owner,role):
        if owner=='base' or role in ('removable_rack','rack_support_left','rack_support_right'):return 0.
        if z<minimum[2]+130:return 0.
        if z>maximum[2]-80:return 1.
        return .5
    handle_cut_owner={}
    for candidate in reference['handle_cutout_candidates']:
        handle_cut_owner[candidate['feature_id']]=candidate['hardware_source_id']
        for target in candidate['additional_targets']:handle_cut_owner[target['feature_id']]=candidate['hardware_source_id']
    motions={root['id']:zero()};nodes=[];features=[];measurements=[]
    def motion_at(row,position):
        semantic=roles[row['id']];owner=semantic['owner'];role=semantic['role'];motion=zero()
        motion['RP_GlebokoscObudowy'][1]=depth_weight(position[1],owner,role)
        motion['RP_WysokoscObudowy'][2]=height_weight(position[2],owner,role)
        in_rack=row['path']==rack_path or row['path'].startswith(rack_path+'/')
        if owner=='hood' and not in_rack:motion['RP_UniesienieCzapki'][2]=1
        if owner=='front_cap':motion['RP_OdsuniecieKlapy'][1]=-1
        if in_rack:motion['RP_UniesienieRacka'][2]=1
        if role=='carry_handle':
            if owner!='front_cap':motion['RP_PrzesuniecieUchwytow'][1]=1
            motion['RP_PodniesienieUchwytow'][2]=1
        return motion
    for row in rows[1:]:
        semantic=roles[row['id']];opaque=rigid_root(row)
        if opaque is not None and opaque!=row['id']:
            motions[row['id']]=copy.deepcopy(motions[opaque]);continue
        box=world_box(row);centre=[(box[j]+box[j+3])/2 for j in range(3)]
        motion=motion_at(row,centre)
        if row['type']=='Z_ELEMENT_ASSEMBLY' and opaque is None:
            # Organizational origins are not mounting datums; move only for presentation.
            for name in ('RP_GlebokoscObudowy','RP_WysokoscObudowy'):motion[name]=[0,0,0]
            if row['path']==rack_path:motion['RP_GlebokoscObudowy'][1]=.5
        motions[row['id']]=motion
        parent=paths[row['path'].rsplit('/',1)[0]];local=combine_local(motion,motions[parent['id']],parent['world_mm'])
        nodes.append(dict(id=row['id'],name=row['name'],label=node_label(row,semantic,minimum,maximum),type=row['type'],path=row['path'],parent_matrix=row['parent_mm'],world_matrix=row['world_mm'],motion=motion,
                          position=[expression(row['parent_mm'][3][j],coeff_for_axis(local,j)) for j in range(3)],
                          role=semantic['role'],owner=semantic['owner'],opaque=opaque is not None))
        if row['type']!='Z_ELEMENT_PART' or opaque is not None:continue
        for f in row.get('features',[]):
            if 'parent_mm' not in f or 'bbox_m' not in f:continue
            fm=f['world_mm'];fb=[x*1000 for x in f['bbox_m']];fc=point([(fb[j]+fb[j+3])/2 for j in range(3)],fm)
            fmotion=motion_at(row,fc) if semantic['role'] in ('outer_panel','profile_group') else copy.deepcopy(motion)
            if f['id'] in handle_cut_owner:fmotion=copy.deepcopy(motions[handle_cut_owner[f['id']]]) if handle_cut_owner[f['id']] in motions else motion_at(by[handle_cut_owner[f['id']]],[(x+y)/2 for x,y in zip(world_box(by[handle_cut_owner[f['id']]])[:3],world_box(by[handle_cut_owner[f['id']]])[3:])])
            sizes=[fb[j+3]-fb[j] for j in range(3)];size_coeff=[{} for j in range(3)]
            scalable=semantic['role'] in ('outer_panel','profile_group') and f['operation']=='Z_UNITE'
            if scalable:
                for axis in range(3):
                    if sizes[axis]<200:continue
                    if abs(fm[axis][1])>.999 and semantic['owner']!='front_cap':
                        size_coeff[axis]['RP_GlebokoscObudowy']=1
                        fmotion['RP_GlebokoscObudowy'][1]=1 if fm[3][1]>(minimum[1]+maximum[1])/2 else 0
                    if abs(fm[axis][2])>.999 and semantic['owner'] in ('hood','front_cap'):
                        size_coeff[axis]['RP_WysokoscObudowy']=1
                        fmotion['RP_WysokoscObudowy'][2]=1 if fm[3][2]>(minimum[2]+maximum[2])/2 else 0
            elif f['operation']=='Z_UNITE':fmotion=copy.deepcopy(motion)
            # Fixed interiors move as whole parts. Rebinding their historical
            # feature anchors can change cached geometry even at zero delta.
            if not scalable and semantic['role'] not in ('outer_panel','profile_group') and f['id'] not in handle_cut_owner:
                continue
            local=combine_local(fmotion,motion,row['world_mm'])
            features.append(dict(id=f['id'],part_id=row['id'],name=f['name'],operation=f['operation'],parent_matrix=f['parent_mm'],world_matrix=fm,
                 position=[expression(f['parent_mm'][3][j],coeff_for_axis(local,j)) for j in range(3)],motion=fmotion,
                 dimensions=[expression(sizes[j],size_coeff[j]) for j in range(3)] if scalable else None,
                 size_coeff=size_coeff,bounds_mm=fb,scalable=scalable,handle_owner=handle_cut_owner.get(f['id'])))
    for row in rows:
        if row['type']=='Z_ELEMENT_PART':measurements.append(dict(id=row['id'],name=row['name'],bounds_local_m=row['bounds_local_m'],world_matrix=row['world_mm'],motion=motions[row['id']],opaque_root=rigid_root(row)))
    return dict(contract='rockpro-t2-parametric-prototype-v1',source_sha256=SOURCE_SHA,inventory_sha256=hashlib.sha256(inventory_bytes).hexdigest(),
        parameters=copy.deepcopy(REFERENCE),notes=NOTES,nodes=nodes,features=features,measurements=measurements,
        fixed_width_mm=size[0],plywood_bounds_mm=minimum+maximum,latch_pairs=reference['latch_pairs'],handle_cutouts=reference['handle_cutout_candidates'],
        component_ids={'base':4499,'hood':7036,'front_cap':4601,'rack':6366},
        production_approved=False,device_fit_confirmed=False,width_resize_supported=False,
        limitations=['fixed_width_rack_variant','device_fit_unconfirmed','joint_clearances_inherited_unapproved','trolley_travel_not_parameterized','no_continuous_native_collision_guard'])
