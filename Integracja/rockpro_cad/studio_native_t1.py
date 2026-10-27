"""Source-bound offline T1 compiler. No CAD calls or manufacturing approval."""
import copy
import hashlib
import json
import math
from . import configurator
from .part_registry import metadata
from .core_case.profile_rules import value
from .core_case.t1_mounting import SOCKET_SEAT
I=[[1,0,0],[0,1,0],[0,0,1]]
PARAMETERS=['RP_SzerokoscWnetrza','RP_GlebokoscWnetrza','RP_WysokoscWnetrza','RP_WysokoscPokrywy','RP_GruboscSklejki']
KNOWN={'H7159','17251S','270836','W0968Z','source-caster-epson','EG-0113','EG-0500/1','EG-0500/2','410429','B1930','B1121'}
FAMILIES={'H7159':'handles','17251S':'latches','270836':'hinges','W0968Z':'stacking_sockets','source-caster-epson':'wheels','410429':'corners','B1930':'braces','B1121':'braces'}
def transpose(r):return [list(x) for x in zip(*r)]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def vec(p,r):return [sum(p[k]*r[k][j] for k in range(3)) for j in range(3)]
def plus(a,b):return [a[i]+b[i] for i in range(3)]
def proper(r, allow_reflection=False):
    if len(r)!=3 or any(len(a)!=3 for a in r) or any(not math.isfinite(v) for a in r for v in a):raise ValueError('Nieprawidłowa rama montażowa')
    cross=[r[0][1]*r[1][2]-r[0][2]*r[1][1],r[0][2]*r[1][0]-r[0][0]*r[1][2],r[0][0]*r[1][1]-r[0][1]*r[1][0]]
    if abs((abs(sum(cross[k]*r[2][k] for k in range(3))) if allow_reflection else sum(cross[k]*r[2][k] for k in range(3)))-1)>1e-7 or any(abs(sum(r[i][k]*r[j][k] for k in range(3))-(i==j))>1e-7 for i in range(3) for j in range(3)):raise ValueError('Rama musi być obrotem bez odbicia i skalowania')
    return r

def frame(item):
    a=math.radians(item.get('rotation_deg',0));c,s=round(math.cos(a),12),round(math.sin(a),12)
    return proper([[c*item['u_axis'][i]+s*item['v_axis'][i] for i in range(3)],[-s*item['u_axis'][i]+c*item['v_axis'][i] for i in range(3)],list(item['normal'])])

def numeric(d,m):
    d=configurator.validate(d)
    if d['type']!='case' or len(d['covers'])!=1 or d['covers'][0]['face']!='top' or d['covers'][0]['kind']!='hinged' or not d.get('construction',{}).get('enabled'):raise ValueError('ROC-46 wymaga kompletnego T1 z jednym górnym wiekiem na zawiasach')
    if abs(d['thickness_mm']-9.8)>1e-9:raise ValueError('Przypięte pasowanie wymaga sklejki 9,8 mm')
    unknown={h['part_id'] for h in d['hardware']}-KNOWN
    if unknown:raise ValueError('Brak natywnego kontraktu źródła i wycięcia: '+', '.join(sorted(unknown)))
    if any('mate_part_id' in p for p in d['placements']):raise ValueError('Wybierz kompletny zamek/zawias, nie dowolne połówki')
    model=configurator.preview(d)
    blocked=[n for n in model['placement']['warnings'] if n['code']!='closure_reference']
    if blocked or model['placement']['unresolved_groups']:raise ValueError('Nie można zbudować układu: '+'; '.join(n['message'] for n in blocked))
    assets={(a['sku'],a['half']):a for a in m['assets']}
    if len(assets)!=len(m['assets']):raise ValueError('Powtórzone części w manifeście')
    for key in ('baseline','templates'):
        s=m['sources'][key]
        if not isinstance(s['path'],str) or not s['path'] or len(s['sha256'])!=64 or any(c not in '0123456789abcdef' for c in s['sha256'].lower()):raise ValueError('Źródło wymaga ścieżki i SHA256')
    panels=[];parts=[];cuts=[];nodes={};targets={};profiles={}
    sections={s['id']:s for s in model['sections']};lid=d['covers'][0]['id'];W,D,B=sections['body']['size_mm'];H=d['covers'][0]['depth_mm']
    params=dict(RP_Length=W,RP_Depth=D,RP_BaseHeight=B,RP_LidHeight=H,RP_Thickness=9.8,RP_DisplayGap=0,RP_JointGap=8.63,RP_HandleOffset=0,RP_HandleHeightOffset=0,RP_LatchInset=150,RP_HingeInset=150)
    def add(n,collection):
        if n['id'] in nodes:raise ValueError('Powtórzona instancja '+n['id'])
        proper(n['rotation'])
        for field in ('position_mm','size_mm'):
            if field in n and (len(n[field])!=3 or any(not math.isfinite(x) for x in n[field])):raise ValueError('Nieprawidłowa geometria '+n['id'])
        if 'size_mm'in n and min(n['size_mm'])<=0:raise ValueError('Niedodatni rozmiar '+n['id'])
        collection.append(n);nodes[n['id']]=n;return n
    def part(id,sku,half,r,p,**extra):
        a=assets[(sku,half)]
        if a['source'] not in m['sources']:raise ValueError('Nieznane źródło części')
        return add(dict(id=id,label='RockPro | '+sku+' | '+id,part_id=sku,half=half,source_key=a['source'],source_id=a['source_id'],rotation=r,position_mm=p,**metadata(FAMILIES.get(sku,'profiles')),**extra),parts)
    for p in model['panels']:
        sec=sections[p['section']];axis=min(range(3),key=lambda k:p['size_mm'][k]);high=p['center_mm'][axis]>sec['position_mm'][axis]+sec['size_mm'][axis]/2
        face=[('left','right'),('front','rear'),('bottom','top')][axis][high];id='panel/'+p['section']+'/'+face
        add(dict(id=id,label='RockPro | Sklejka | '+p['section']+' | '+face,section_id=p['section'],face=face,rotation=copy.deepcopy(I),size_mm=list(p['size_mm']),position_mm=[p['center_mm'][k]-p['size_mm'][k]/2 for k in range(3)],colorref=0x808040,**metadata('panels')),panels);targets[(p['section'],face)]=id
    # Use validated native profile/brace datums. Joint segmentation is replaced
    # by continuous profiles with actual negative features owned by closures.
    old_to_new={};mounts={x['id']:x for x in m['corrected_plan']['mounts']};mapping=[]
    for b in m['profile_all_bindings']:
        sku=b['sku'].replace('_','/') if b['sku'].startswith('EG-0500') else b['sku'];id='structure/'+b['id'];pose=mounts.get(b['node_id'],b)
        extra=dict(profile_axis=2,profile_length_mm=value(b['cut_length'],params)) if b['cut_length'] else {}
        part(id,sku,'complete',pose.get('rotation',b['rotation']),[value(s,params) for s in pose['position']],**extra);old_to_new[b['node_id']]=id
        if sku.startswith('EG-0500'):
            wall=b['id'].rsplit('/',1)[1];profiles[('body' if sku.endswith('/1') else lid,wall)]=id
            studio=[x['id'] for x in model['construction']['items'] if x['part_id']==sku and x['id'].startswith('joint/') and '/'+wall+'/'in x['id']]
            mapping.append(dict(studio_ids=studio,native_id=id,reason='Ciągły profil z rzeczywistymi wycięciami zamiast segmentów podglądu'))
    wheels={}
    for item in model['construction']['items']:
        sku,family=item['part_id'],item['family_id'];id='structure/'+item['id']
        if family in ('profiles','braces'):continue
        if family=='wheel_pads':add(dict(id=id,label='RockPro | Podpora kół',position_mm=list(item['position_mm']),size_mm=list(item['size_mm']),rotation=copy.deepcopy(I),colorref=0x808040,**metadata('wheel_pads')),panels)
        elif family=='wheels':
            right=item['position_mm'][0]>W/2;r=[[1 if right else -1,0,0],[0,0,1],[0,-1 if right else 1,0]]
            wheels[item['stacking_pair']]=part(id,sku,'complete',r,list(item['position_mm']),stacking_pair=item['stacking_pair'])
        elif family=='stacking_sockets':
            wheel=wheels[item['stacking_pair']];contact=plus(vec([-36.,-132.1,0.],wheel['rotation']),wheel['position_mm']);seat=[contact[0],contact[1],B+H]
            part(id,sku,'complete',copy.deepcopy(I),[seat[k]-SOCKET_SEAT[k] for k in range(3)],stacking_pair=item['stacking_pair'],seat_world_mm=seat)
        else:part(id,sku,'complete',copy.deepcopy(item['rotation']),list(item['position_mm']))
    relatives={r['key']:r for r in m['cut_transforms_relative_owner']};originals=m['corrected_plan']['cuts'];templates={r['feature']['id'] for r in m['template_features']}
    if len([c for c in originals if c['key'].startswith(('edge_rebate/','lid_seating/'))]) != 20:raise ValueError('Brak kompletu obróbek pasowania profili')
    placed={x['part_id'] for x in model['placement']['items']}
    if {'H7159','17251S','270836'}-placed:raise ValueError('Kompletny T1 wymaga uchwytów, zamków i zawiasów w układzie')
    def add_cut(original,owner,target,wr,wp,suffix):
        t=nodes[target];inv=transpose(t['rotation'])
        if original['template_id'] not in templates:raise ValueError('Brak przypiętego szablonu wycięcia')
        c=dict(id=owner+'/cut/'+suffix,owner_id=owner,target_id=target,source_key='templates',feature_id=original['template_id'],rotation=proper(mul(wr,inv),allow_reflection=True),position_mm=vec([wp[k]-t['position_mm'][k] for k in range(3)],inv),through_target=original['through_target'],stage_id=nodes[owner]['stage_id'])
        if 'size'in original:c['size_mm']=[value(x,params) for x in original['size']]
        cuts.append(c)
    def owned_cut(original,owner,target,suffix):
        r=relatives[original['key']];wr=mul(r['native_owner_rotation'],owner['rotation']);wp=plus(vec(r['native_owner_translation_mm'],owner['rotation']),owner['position_mm']);add_cut(original,owner['id'],target,wr,wp,suffix)
    for item in model['placement']['items']:
        sku=item['part_id']
        if sku not in ('H7159','17251S','270836'):raise ValueError('Brak wykonawcy okucia '+sku)
        if sku!='H7159' and not item.get('seam_id'):raise ValueError('Zamki i zawiasy muszą być związane ze złączem')
        f=frame(item)
        for half in (['complete'] if sku=='H7159' else ['base','lid']):
            a=assets[(sku,half)]['native_to_mount_uvn'];r=proper(mul(a['rotation'],f));pos=plus(vec(a['translation_mm'],f),item['position_mm']);section=item['section_id'] if sku=='H7159' else ('body' if half=='base' else lid)
            owner=part('placement/'+item['id']+'/'+half,sku,half,r,pos,studio_instance_id=item['id'],section_id=section,face=item['face'])
            prefix='handles/left/1/' if sku=='H7159' else ('latches' if sku=='17251S' else 'hinges')+'/1/'+half+'/'
            for original in originals:
                if original['key'].startswith(prefix):
                    suffix=original['key'][len(prefix):];target=profiles[(section,item['face'])] if suffix=='profile' else targets[(section,item['face'])];owned_cut(original,owner,target,suffix)
    for owner in parts:
        if owner['part_id']=='W0968Z':owned_cut(next(c for c in originals if c['key']=='stacking_sockets/left/front/opening'),owner,targets[(lid,'top')],'opening')
    oldpanels={990:('body','front'),996:('body','rear'),1002:('body','left'),1008:('body','right'),1014:(lid,'front'),1020:(lid,'rear'),1026:(lid,'left'),1032:(lid,'right')}
    for original in originals:
        if original['key'].startswith(('edge_rebate/','lid_seating/')):
            owner=old_to_new[int(original['mount_key'].rsplit('/',1)[1])]
            add_cut(original,owner,targets[oldpanels[original['target_id']]],original['world_rotation'],[value(s,params) for s in original['world_position']],original['key'])
    selected={h['part_id'] for h in d['hardware']}
    built={p['part_id'] for p in parts}
    if selected!=built:raise ValueError('Wybór części nie jest w pełni rozliczony; bez montażu: '+', '.join(sorted(selected-built))+'; niewybrane: '+', '.join(sorted(built-selected)))
    if len({c['id'] for c in cuts})!=len(cuts):raise ValueError('Powtórzone operacje')
    for owner in [p for p in parts if p['part_id'] in ('H7159','17251S','270836','W0968Z')]:
        if sum(c['owner_id']==owner['id'] for c in cuts)!=(1 if owner['part_id']=='W0968Z' else 2):raise ValueError('Niekompletne wycięcia dla '+owner['id'])
    for panel in panels:
        low=[0.,0.,0.]
        if panel.get('section_id')==lid and panel.get('face') in ('front','rear','left','right'):
            low[2]=.1  # Source-bound lid_seating trims the entire lower edge.
        panel['expected_body_bounds_local_mm']=low+list(panel['size_mm'])
        panel['expected_body_size_mm']=[panel['size_mm'][k]-low[k] for k in range(3)]
    return dict(panels=panels,parts=parts,cuts=cuts,structure_mapping=mapping,deviations=['Profile ciągłe z obróbkami; wzmocnienia i profile według przypiętych baz natywnych.','Gniazda nad punktem kontaktu koła, nie nad kotwą zespołu.'])

def _values(d):return list(d['internal_mm'])+[d['covers'][0]['depth_mm'],d['thickness_mm']]
def _changed(d,index,amount):
    out=copy.deepcopy(d)
    if index<3:out['internal_mm'][index]+=amount
    else:out['covers'][0]['depth_mm']+=amount
    return out

def _probe(d,manifest,index,base):
    """Use an admissible signed step; never manufacture a constructor override."""
    for step in (.1,-.1):
        try:
            sample=numeric(_changed(d,index,step),manifest)
        except ValueError:
            continue
        return d,base,step,sample
    # At the intersection of minimum lid height and its ratio ceiling, neither
    # lid-only step is legal. Move the numerical reference into the domain,
    # without changing the requested model; later reconstruct both references.
    if index==3:
        reference=_changed(d,2,1.)
        try:
            reference_model=numeric(reference,manifest)
            sample=numeric(_changed(reference,index,.1),manifest)
        except ValueError:
            pass
        else:
            return reference,reference_model,.1,sample
    raise ValueError('Brak dopuszczalnej próby parametru '+PARAMETERS[index]+
                     '; nie zmieniono wymiarów ani odstępstwa konstruktora')

def _check_sample(d,manifest,probes):
    directions=[1 if p[2]>0 else -1 for p in probes]
    candidates=[[17.,23.,31.,3.],
                [a*b for a,b in zip((17.,23.,31.,3.),directions)],
                [a*b for a,b in zip((17.,23.,31.,6.),directions)]]
    for amounts in candidates:
        changed=d
        for i,amount in enumerate(amounts):changed=_changed(changed,i,amount)
        try:
            sample=numeric(changed,manifest)
        except ValueError:
            continue
        return changed,sample
    raise ValueError('Brak dopuszczalnej próby zmiany wymiarów; przelicz projekt w Studio')

def compile_t1(record,manifest):
    """Compile a saved record with affine expressions; executor verifies source bytes."""
    if not isinstance(record,dict) or not {'id','revision','draft'}<=set(record) or not isinstance(record['id'],str) or not record['id'] or type(record['revision']) is not int or record['revision']<1:raise ValueError('Wymagany zapisany rekord Studio: id, revision, draft')
    d=copy.deepcopy(record['draft']);base=numeric(d,manifest);values=_values(d)
    probes=[_probe(d,manifest,i,base) for i in range(4)]
    derivatives=[p[3] for p in probes]
    references=[p[1] for p in probes]
    changed,alt=_check_sample(d,manifest,probes);altvalues=_values(changed)
    for collection in ('panels','parts','cuts'):
        for sample in derivatives+references+[alt]:
            if [x['id'] for x in sample[collection]]!=[x['id'] for x in base[collection]]:raise ValueError('Zmiana wymiarów zmienia topologię; przelicz projekt w Studio')
        for k,row in enumerate(base[collection]):
            if any(s[collection][k]['rotation']!=row['rotation'] for s in derivatives+references+[alt]):raise ValueError('Zmienna orientacja nie jest parametrem liniowym')
            for field,outfield in [('position_mm','position_expressions'),('size_mm','size_expressions'),('profile_length_mm','profile_length_expression')]:
                if field not in row:continue
                numbers=row[field] if isinstance(row[field],list) else [row[field]];formulas=[]
                for axis,start in enumerate(numbers):
                    at=lambda x:(x[field][axis] if isinstance(x[field],list) else x[field])
                    coefficients=[round((at(sample[collection][k])-at(ref[collection][k]))/step,8)
                                  for _,ref,step,sample in probes]+[0.]
                    const=round(start-sum(a*b for a,b in zip(coefficients,values)),8)
                    checks=[(values,row),(altvalues,alt[collection][k])]
                    checks += [(_values(refdraft),ref[collection][k]) for refdraft,ref,_,_ in probes]
                    if any(abs(const+sum(a*b for a,b in zip(coefficients,v))-at(expected))>1e-5
                           for v,expected in checks):raise ValueError('Nieliniowe rozmieszczenie '+row['id']+'; przelicz projekt w Studio')
                    formulas.append(' + '.join([f'{const:.12g} mm']+[f'({a:.12g}) * {n}' for n,a in zip(PARAMETERS,coefficients) if a]))
                row[outfield]=formulas if isinstance(row[field],list) else formulas[0]
    return dict(contract='roc46-native-v1',name=d['name'],draft_id=record['id'],draft_revision=record['revision'],draft_sha256=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),sources=[dict(key=k,**v) for k,v in manifest['sources'].items()],parameters=dict(zip(PARAMETERS,values)),fixed_parameters={'RP_GruboscSklejki':9.8},joint_gap_mm=8.63,parameter_notes=dict(zip(PARAMETERS,['Szerokość użytkowego wnętrza korpusu, oś X.','Głębokość użytkowego wnętrza korpusu, oś Y.','Wysokość użytkowego wnętrza korpusu nad dnem.','Od rantu korpusu do wierzchu pokrywy, zawiera złącze profili.','Stałe 9,8 mm dla przypiętego pasowania.'])),changed_parameters=dict(zip(PARAMETERS,altvalues)),changed_expected=alt,check_cases=[dict(name='zmiana_wymiarow',parameters=dict(zip(PARAMETERS,altvalues)),expectedposes=alt['panels']+alt['parts'],expectedpanels=alt['panels'],expectedcuts=alt['cuts'])],formula_check='PASS',native_validation='NOT RUN',production_approved=False,**base)
