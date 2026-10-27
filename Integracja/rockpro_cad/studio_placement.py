"""Section-bound concept placements. No machining, native CAD or production approval."""
import math
from . import studio_parts
from . import studio_joints, studio_closures

FACE_LABELS = dict(front='Przód', rear='Tył', left='Lewa', right='Prawa', top='Góra', bottom='Dół')
OPPOSITE = dict(front='rear', rear='front', left='right', right='left', top='bottom', bottom='top')
# Reference mounting envelopes, NOT machining contours or approved motion clearances.
FOOTPRINTS = {'H7159': [161.,107.], '17251S': [127.,174.5], '27095': [102.,105.]}


def validate(draft):
    groups = draft.get('placements', [])
    if not isinstance(groups, list) or len(groups)>32:
        raise ValueError('Rozmieszczenie: maksymalnie 32 grupy okuć')
    chosen = {r['id']: r for r in studio_parts.resolve(draft['hardware'])}
    seen = set(); total = 0
    fields = {'id','part_id','revision','section_id','face','u','v','rotation_deg',
              'pattern','count_per_wall','opposite_wall','spread'}
    for g in groups:
        if not isinstance(g,dict) or not isinstance(g.get('part_id'),str) or g['part_id'] not in chosen:
            raise ValueError('Rozmieszczana część musi być wybrana w kroku 4')
        family=chosen[g['part_id']]['family_id'];handle=family=='handles'
        if g.get('pattern')=='closure_line':
            total+=studio_closures.validate(g,chosen,seen);continue
        if g.get('pattern')=='joint_line':
            if family!='hinges' or chosen[g['part_id']].get('component_only') or set(g)!={'id','part_id','revision','pattern','joint_id','hinge_count','edge_inset_mm'}:
                raise ValueError('Rząd na złączu wymaga definicji zawiasu, linii, liczby i odsunięcia')
            for key in ('id','joint_id'):
                if not isinstance(g[key],str) or not 1<=len(g[key])<=86:raise ValueError('Nieprawidłowy identyfikator rzędu zawiasów')
            if g['id'] in seen:raise ValueError('Powtórzony identyfikator grupy okuć')
            seen.add(g['id'])
            if type(g['revision']) is not int or g['revision']!=chosen[g['part_id']]['revision']:raise ValueError('Nieobsługiwana rewizja zawiasu')
            if type(g['hinge_count']) is not int or not 1<=g['hinge_count']<=16:raise ValueError('Liczba zawiasów na złączu: 1–16')
            if type(g['edge_inset_mm']) not in (int,float) or not math.isfinite(g['edge_inset_mm']) or not 0<=g['edge_inset_mm']<=5000:raise ValueError('Odsunięcie zawiasów: 0–5000 mm')
            total+=g['hinge_count'];continue
        if set(g) != fields | ({'handles_per_wall'} if handle else set()):
            raise ValueError('Nieprawidłowy opis grupy rozmieszczenia')
        for key in ('id','section_id'):
            if not isinstance(g[key],str) or not 1<=len(g[key])<=80:
                raise ValueError('Grupa i sekcja wymagają stabilnych identyfikatorów')
        if g['id'] in seen:
            raise ValueError('Powtórzony identyfikator grupy okuć')
        seen.add(g['id'])
        if type(g['revision']) is not int or g['revision']!=chosen[g['part_id']]['revision']:
            raise ValueError('Nieobsługiwana rewizja rozmieszczanej części')
        if not isinstance(g['face'],str) or g['face'] not in FACE_LABELS or g['pattern'] not in ('single','row','symmetric'):
            raise ValueError('Nieznana ścianka lub układ okuć')
        for key in ('u','v','spread'):
            if type(g[key]) not in (int,float) or not math.isfinite(g[key]) or not 0<=g[key]<=1:
                raise ValueError('Pozycje i rozstaw względny muszą należeć do zakresu 0–1')
        if type(g['rotation_deg']) is not int or g['rotation_deg'] not in (0,90,180,270):
            raise ValueError('Obrót okucia: 0, 90, 180 lub 270 stopni')
        n=g['count_per_wall']
        if type(n) is not int or not 1<=n<=16 or (g['pattern']=='single' and n!=1):
            raise ValueError('Liczba wystąpień na ściankę: 1–16; pojedyncze okucie wymaga 1')
        if type(g['opposite_wall']) is not bool:
            raise ValueError('Przeciwległa ścianka wymaga jawnego wyboru')
        if handle and (type(g['handles_per_wall']) is not int or not 1<=g['handles_per_wall']<=16 or n!=g['handles_per_wall']):
            raise ValueError('Uchwyty: jawnie 1–16 na każdą ściankę')
        total += n*(2 if g['opposite_wall'] else 1)
    if total>256:
        raise ValueError('Maksymalnie 256 wystąpień okuć w koncepcji')


def faces(sections, panels):
    result=[]
    for s in sections:
        x,y,z=s['position_mm'];w,d,h=s['size_mm']
        definitions={
            'front':([x,y,z],[1,0,0],[0,0,1],[0,-1,0],[w,h],1,-1),
            'rear':([x+w,y+d,z],[-1,0,0],[0,0,1],[0,1,0],[w,h],1,1),
            'left':([x,y+d,z],[0,-1,0],[0,0,1],[-1,0,0],[d,h],0,-1),
            'right':([x+w,y,z],[0,1,0],[0,0,1],[1,0,0],[d,h],0,1),
            'top':([x,y,z+h],[1,0,0],[0,1,0],[0,0,1],[w,d],2,1),
            'bottom':([x,y+d,z],[1,0,0],[0,-1,0],[0,0,-1],[w,d],2,-1)}
        for face,(origin,u,v,n,size,axis,sign) in definitions.items():
            # Use actual panels. An open section face cannot receive an attachment.
            plane=s['position_mm'][axis]+(s['size_mm'][axis] if sign>0 else 0)
            matches=[i for i,p in enumerate(panels) if p['section']==s['id']
                     and abs(p['center_mm'][axis]+sign*p['size_mm'][axis]/2-plane)<1e-6
                     and p['size_mm'][axis]<=s['size_mm'][axis]/2]
            if matches:
                result.append(dict(key=s['id']+'/'+face,section_id=s['id'],face=face,
                    label=s['label']+' · '+FACE_LABELS[face],origin_mm=origin,u_axis=u,v_axis=v,
                    normal=n,size_mm=size,panel_index=matches[0]))
    return result


def preview(draft, sections, panels):
    mount_faces=faces(sections,panels);by_face={(f['section_id'],f['face']):f for f in mount_faces}
    definitions={r['id']:r for r in studio_parts.resolve(draft['hardware'])}
    joint_lines=studio_joints.lines(draft,sections,mount_faces);by_joint={j['id']:j for j in joint_lines}
    closure_lines=studio_closures.lines(draft,sections,mount_faces);by_seam={j['id']:j for j in closure_lines}
    envelopes={**FOOTPRINTS,**studio_closures.envelopes()}
    items=[];warnings=[];unresolved=[];counts={}
    for g in sorted(draft.get('placements',[]),key=lambda g:g['pattern']=='closure_line'):
        label=definitions[g['part_id']].get('catalog_code_raw') or definitions[g['part_id']]['sku'] or definitions[g['part_id']]['name']
        if g['pattern']=='closure_line':
            line=by_seam.get(g['seam_id'])
            if not line or definitions[g['part_id']]['family_id'] not in line['roles']:
                unresolved.append(g['id']);warnings.append(dict(group_id=g['id'],code='missing_seam',message='Wybrana linia nie pasuje do rodzaju okucia lub sposobu otwierania. Wskaż nowe złącze.'));continue
            resolved,notes=studio_closures.resolve(g,line,by_face[('body',line['face'])],envelopes,definitions,items)
            warnings.extend(notes);items.extend(resolved)
            if not resolved:unresolved.append(g['id'])
            counts[g['part_id']]=counts.get(g['part_id'],0)+len(resolved)
            if g.get('mate_part_id'):counts[g['mate_part_id']]=counts.get(g['mate_part_id'],0)+len(resolved)
            continue
        if g['pattern']=='joint_line':
            line=by_joint.get(g['joint_id']);footprint=FOOTPRINTS.get(g['part_id'])
            if not line or (g['hinge_count']>1 and 2*g['edge_inset_mm']>line['length_mm']):
                unresolved.append(g['id']);warnings.append(dict(group_id=g['id'],code='missing_joint',message='Brak otwieranej pokrywy lub za mało miejsca na zadany rząd zawiasów. Wybierz linię i odsunięcie.'));continue
            frame=by_face[('body',line['face'])]
            resolved=studio_joints.resolve(g,line,frame,footprint);items.extend(resolved);counts[g['part_id']]=counts.get(g['part_id'],0)+len(resolved)
            warnings.append(dict(group_id=g['id'],code='joint_mount_pending',message=g['part_id']+': rząd związany z linią styku; dokładne bazy zawiasu, profile, ruch i wycięcia wymagają potwierdzenia.'))
            if footprint is None:warnings.append(dict(group_id=g['id'],code='unknown_envelope',message=g['part_id']+': brak potwierdzonego obrysu zawiasu.'))
            else:
                if min(line['negative_space_mm'],line['positive_space_mm'])<footprint[1]/2+5:
                    warnings.append(dict(group_id=g['id'],code='hinge_mount_space',message='Za mało miejsca po jednej stronie styku na wstępny obrys '+g['part_id']+'. Sprawdź wysokość/głębokość pokrywy; wymiary nie zostały powiększone.'))
                if any(min(i['distance_along_joint_mm'],line['length_mm']-i['distance_along_joint_mm'])<footprint[0]/2+5 for i in resolved):
                    warnings.append(dict(group_id=g['id'],code='edge_clearance',message='Zawiasy są za blisko końca linii styku dla znanego obrysu i rezerwy 5 mm.'))
            continue
        walls=[g['face']]+([OPPOSITE[g['face']]] if g['opposite_wall'] else [])
        if any((g['section_id'],face) not in by_face for face in walls):
            unresolved.append(g['id']);warnings.append(dict(group_id=g['id'],code='missing_wall',message='Brak wybranej sekcji lub jednej ze ścian pary. Wskaż nową ściankę; grupa pozostaje zapisana.'));continue
        footprint=FOOTPRINTS.get(g['part_id'])
        if definitions[g['part_id']]['family_id'] in ('hinges','latches'):
            warnings.append(dict(group_id=g['id'],code='unbound_joint',message=g['part_id']+': pozycja na ściance jest koncepcją. Przypisanie do złącza, parowanie połówek i wycięcia wymagają następnego etapu.'))
        if footprint is None:
            warnings.append(dict(group_id=g['id'],code='unknown_envelope',message='Niepotwierdzony obrys montażowy '+label+' — kontrola kolizji korzysta z umownego obrysu 2D, niezależnie od szczegółowej geometrii podglądu.'))
        n=g['count_per_wall']
        offsets=[0] if n==1 else [(i/(n-1)-.5)*g['spread'] for i in range(n)]
        center=.5 if g['pattern']=='symmetric' else g['u']
        for face in walls:
            frame=by_face[(g['section_id'],face)];width,height=frame['size_mm']
            for i,offset in enumerate(offsets):
                u=center+offset;v=g['v'];size=list(envelopes.get(g['part_id'],[64.,44.]))
                # Opposing side-wall frames have opposite horizontal directions.
                # Reflect the frame coordinate so corresponding parts stay aligned in world space.
                if face!=g['face']:
                    if face in ('top','bottom'):v=1-v
                    else:u=1-u
                if g['rotation_deg']%180:size.reverse()
                pos=[frame['origin_mm'][k]+u*width*frame['u_axis'][k]+v*height*frame['v_axis'][k] for k in range(3)]
                item=dict(id=g['id']+':'+face+':'+str(i),group_id=g['id'],part_id=g['part_id'],revision=g['revision'],
                    section_id=g['section_id'],face=face,face_key=frame['key'],u=u,v=v,position_mm=pos,
                    rotation_deg=g['rotation_deg'],footprint_mm=size,footprint_known=footprint is not None,
                    u_axis=frame['u_axis'],v_axis=frame['v_axis'],normal=frame['normal'])
                items.append(item);counts[g['part_id']]=counts.get(g['part_id'],0)+1
                margin=5. # Preliminary placement clearance only, never a manufacturing tolerance.
                if u*width-size[0]/2<margin or (1-u)*width-size[0]/2<margin or v*height-size[1]/2<margin or (1-v)*height-size[1]/2<margin:
                    warnings.append(dict(group_id=g['id'],occurrence_id=item['id'],code='edge_clearance',message=label+' · '+frame['label']+': obrys lub rezerwa 5 mm wychodzi poza ściankę.'))
    for i,a in enumerate(items):
        for b in items[i+1:]:
            if a['face_key']!=b['face_key'] or not(a['footprint_known'] and b['footprint_known']):continue
            frame=by_face[(a['section_id'],a['face'])]
            if all(abs(a[k]-b[k])*frame['size_mm'][j] < (a['footprint_mm'][j]+b['footprint_mm'][j])/2+5 for j,k in enumerate(('u','v'))):
                warnings.append(dict(group_id=a['group_id'],other_group_id=b['group_id'],code='overlap',message=a['part_id']+' i '+b['part_id']+' · '+frame['label']+': obrysy lub rezerwy 5 mm nachodzą na siebie.'))
    return dict(schema='rockpro.concept-placement/1',faces=mount_faces,joint_lines=joint_lines,closure_lines=closure_lines,
        part_envelopes={k:list(v) for k,v in envelopes.items()},items=items,warnings=warnings,
        unresolved_groups=unresolved,instance_count=len(items),counts=counts,status='draft' if items else 'not_started',
        preliminary_clearance_mm=5,collision_scope='known_2d_envelopes_same_wall',
        cutouts_generated=False,production_approved=False)
