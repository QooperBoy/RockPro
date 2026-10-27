"""Closure rows bound to actual section seams. Concept layout, not machining approval."""
import math
import json
import hashlib
from functools import lru_cache
from . import source_parts


def lines(draft,sections,faces):
    body=sections[0];by={(f['section_id'],f['face']):f for f in faces};result=[]
    normals={'top':[0,0,1],'front':[0,-1,0],'rear':[0,1,0],'left':[-1,0,0],'right':[1,0,0]}
    for cover in draft['covers']:
        section=next(s for s in sections if s['id']==cover['id']);normal=normals[cover['face']];axis=next(k for k,x in enumerate(normal) if x)
        plane=body['position_mm'][axis]+(body['size_mm'][axis] if normal[axis]>0 else 0)
        low=[max(body['position_mm'][k],section['position_mm'][k]) for k in range(3)]
        high=[min(body['position_mm'][k]+body['size_mm'][k],section['position_mm'][k]+section['size_mm'][k]) for k in range(3)]
        low[axis]=high[axis]=plane
        if any(high[k]-low[k]<=0 for k in range(3) if k!=axis):continue
        hinge_face=('rear' if cover['hinge_edge']=='high' else 'front') if axis==2 else ('right' if cover['hinge_edge']=='high' else 'left')
        for face in ('front','rear','left','right','top','bottom'):
            frame=by.get(('body',face));other=by.get((cover['id'],face))
            if not frame or not other or abs(sum((frame['origin_mm'][k]-other['origin_mm'][k])*frame['normal'][k] for k in range(3)))>1e-5:continue
            face_axis=next(k for k,x in enumerate(frame['normal']) if x)
            if face_axis==axis:continue
            a=list(low);b=list(high)
            a[face_axis]=b[face_axis]=frame['origin_mm'][face_axis];b[axis]=a[axis]=plane
            angle=round(math.degrees(math.atan2(-sum(normal[k]*frame['u_axis'][k] for k in range(3)),sum(normal[k]*frame['v_axis'][k] for k in range(3)))))%360
            along=[math.cos(math.radians(angle))*frame['u_axis'][k]+math.sin(math.radians(angle))*frame['v_axis'][k] for k in range(3)]
            if sum((b[k]-a[k])*along[k] for k in range(3))<0:a,b=b,a
            hinge=cover['kind']=='hinged' and face==hinge_face
            result.append(dict(id='seam-'+cover['id']+'-'+face,cover_id=cover['id'],face=face,frame_key=frame['key'],
                label='Korpus ↔ '+cover['label']+' · '+frame['label'].split(' · ')[-1],start_mm=a,end_mm=b,length_mm=math.dist(a,b),
                rotation_deg=angle,u_axis=frame['u_axis'],v_axis=frame['v_axis'],normal=frame['normal'],
                roles=['hinges'] if hinge else ['latches'],negative_space_mm=body['size_mm'][axis],positive_space_mm=cover['depth_mm']))
    return result


def validate(g,chosen,seen):
    fields={'id','part_id','revision','pattern','seam_id','count','edge_inset_mm','clearance_mm','avoid_handles'}
    row=chosen[g['part_id']];paired=row.get('component_only',False)
    if set(g)!=fields|({'mate_part_id','mate_revision'} if paired else set()) or row['family_id'] not in ('hinges','latches'):
        raise ValueError('Rząd złącza wymaga zatrzasku/zawiasu, linii, liczby i rezerw; komponent wymaga drugiej połówki')
    if paired:
        mate=chosen.get(g['mate_part_id']) if isinstance(g['mate_part_id'],str) else None
        if not mate or mate['id']==row['id'] or mate['family_id']!=row['family_id'] or not mate.get('component_only') or type(g['mate_revision']) is not int or g['mate_revision']!=mate['revision']:
            raise ValueError('Wybierz w kroku 4 dwie różne połówki tej samej rodziny; potwierdź ich role w rzędzie')
    if any(not isinstance(g[k],str) or not 1<=len(g[k])<=150 for k in ('id','seam_id')) or g['id'] in seen:raise ValueError('Nieprawidłowe ID grupy/złącza')
    seen.add(g['id'])
    if type(g['revision']) is not int or g['revision']!=row['revision']:raise ValueError('Nieobsługiwana rewizja okucia')
    if type(g['count']) is not int or not 1<=g['count']<=16:raise ValueError('Liczba na złączu: 1–16')
    for key in ('edge_inset_mm','clearance_mm'):
        if type(g[key]) not in (int,float) or not math.isfinite(g[key]) or not 0<=g[key]<=5000:raise ValueError('Rezerwy złącza: 0–5000 mm')
    if type(g['avoid_handles']) is not bool:raise ValueError('Omijanie uchwytów wymaga jawnego wyboru')
    return g['count']*(2 if paired else 1)


def uniform_positions(length,count,inset,min_pitch,forbidden):
    """Largest uniform pitch, then closest-to-centre shift; exact interval subtraction."""
    if length<2*inset:return None
    merged=[]
    for lo,hi in sorted((max(inset,a),min(length-inset,b)) for a,b in forbidden if b>=inset and a<=length-inset):
        if merged and lo<=merged[-1][1]:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
        else:merged.append((lo,hi))
    forbidden=merged
    if count==1:pitches=[0.]
    else:
        maximum=(length-2*inset)/(count-1)
        if maximum<min_pitch:return None
        # Feasibility changes when two interval boundaries meet. Enumerate those
        # pitches instead of sampling (which can miss a narrow feasible layout).
        endpoints=[inset,length-inset]+[v for a,b in forbidden for v in (a-2e-5,b+2e-5)]
        events={maximum,min_pitch}
        for a in endpoints:
            for b in endpoints:
                if a<=b:continue
                for steps in range(1,count):
                    pitch=(a-b)/steps
                    if min_pitch<=pitch<=maximum:
                        events.add(pitch)
                        if pitch-4e-5>=min_pitch:events.add(pitch-4e-5)
        pitches=sorted(events,reverse=True)
    for pitch in pitches:
        intervals=[(inset,length-inset-(count-1)*pitch)]
        for lo,hi in forbidden:
            for i in range(count):
                a,b=lo-i*pitch,hi-i*pitch;next_intervals=[]
                for start,end in intervals:
                    if b<start or a>end:next_intervals.append((start,end));continue
                    if start<a-1e-5:next_intervals.append((start,min(end,a-1e-5)))
                    if end>b+1e-5:next_intervals.append((max(start,b+1e-5),end))
                intervals=next_intervals
        if intervals:
            target=(length-(count-1)*pitch)/2
            start=min((max(a,min(b,target)) for a,b in intervals),key=lambda v:abs(v-target))
            return [start+i*pitch for i in range(count)]
    return None


def resolve(group,line,frame,envelopes,definitions,obstacles):
    paired='mate_part_id' in group;size=envelopes.get(group['part_id'],[64.,44.]);mate=envelopes.get(group.get('mate_part_id'),size)
    width=max(size[0],mate[0]);body_height=size[1] if paired else size[1]/2;lid_height=mate[1] if paired else size[1]/2
    clearance=group['clearance_mm'];inset=max(group['edge_inset_mm'],width/2+clearance);forbidden=[];angle=math.radians(line['rotation_deg'])
    along=[math.cos(angle)*line['u_axis'][k]+math.sin(angle)*line['v_axis'][k] for k in range(3)]
    across=[-math.sin(angle)*line['u_axis'][k]+math.cos(angle)*line['v_axis'][k] for k in range(3)]
    for item in obstacles:
        if (definitions[item['part_id']]['family_id']!='handles' and not item.get('seam_id') and not item.get('joint_id')) or item['face']!=line['face'] or item['section_id'] not in ('body',line['cover_id']):continue
        delta=[item['position_mm'][k]-line['start_mm'][k] for k in range(3)];d=sum(delta[k]*along[k] for k in range(3));v=sum(delta[k]*across[k] for k in range(3))
        # Project handle's wall-aligned envelope onto the seam's along/across axes.
        half=[item['footprint_mm'][j]/2 for j in range(2)]
        extent_along=sum(abs(sum(along[k]*a[k] for k in range(3)))*half[j] for j,a in enumerate((item['u_axis'],item['v_axis'])))
        extent_across=sum(abs(sum(across[k]*a[k] for k in range(3)))*half[j] for j,a in enumerate((item['u_axis'],item['v_axis'])))
        if v+extent_across+clearance>=-body_height and v-extent_across-clearance<=lid_height:forbidden.append((d-extent_along-width/2-clearance,d+extent_along+width/2+clearance))
    positions=uniform_positions(line['length_mm'],group['count'],inset,width+clearance,forbidden if group['avoid_handles'] else [])
    if positions is None:return [],[dict(group_id=group['id'],code='closure_no_space',message='Brak miejsca na równy rząd z rezerwą i bez kolizji z uchwytami. Zmniejsz liczbę lub zmień linię/położenie uchwytów.')]
    warnings=[];items=[]
    if group['part_id'] not in envelopes or (paired and group['mate_part_id'] not in envelopes):
        warnings.append(dict(group_id=group['id'],code='closure_unknown_envelope',message='Brak zmierzonego obrysu okucia. Rozstaw korzysta z umownego obrysu; potwierdź gabaryty przed montażem.'))
    if any(definitions[o['part_id']]['family_id']=='handles' and o['part_id'] not in envelopes for o in obstacles):
        warnings.append(dict(group_id=group['id'],code='closure_unknown_handle',message='Co najmniej jeden uchwyt nie ma zmierzonego obrysu. Omijanie używa obrysu umownego; brak pełnego potwierdzenia kolizji.'))
    if not group['avoid_handles'] and any(a<=p<=b for p in positions for a,b in forbidden):warnings.append(dict(group_id=group['id'],code='closure_handle_overlap',message='Rząd koliduje z uchwytami; włącz omijanie lub zmień układ.'))
    if body_height+clearance>line['negative_space_mm'] or lid_height+clearance>line['positive_space_mm']:warnings.append(dict(group_id=group['id'],code='closure_mount_space',message='Za mało miejsca na okucie po jednej stronie złącza. Sprawdź wysokość/głębokość wieka; wymiary nie zostały powiększone.'))
    for i,distance in enumerate(positions):
        pos=[line['start_mm'][k]+distance*along[k] for k in range(3)];delta=[pos[k]-frame['origin_mm'][k] for k in range(3)]
        uv=[sum(delta[k]*a[k] for k in range(3))/frame['size_mm'][j] for j,a in enumerate((frame['u_axis'],frame['v_axis']))]
        halves=[]
        for section,sign,height,part in [('body',-1,body_height,group['part_id']),(line['cover_id'],1,lid_height,group.get('mate_part_id',group['part_id']))]:
            halves.append(dict(section_id=section,position_mm=[pos[k]+sign*height/2*across[k] for k in range(3)],part_id=part,
                mesh_region=None if paired else ('body' if sign<0 else 'cover'),paired_component=paired,mesh_local_offset_y_mm=0 if paired else -sign*height/2,uv_range=[0,.5] if sign<0 else [.5,1]))
        footprint=[width,body_height+lid_height];
        if line['rotation_deg']%180:footprint.reverse()
        items.append(dict(id=group['id']+':seam:'+str(i),group_id=group['id'],part_id=group['part_id'],revision=group['revision'],section_id='body',face=line['face'],face_key=frame['key'],u=uv[0],v=uv[1],position_mm=pos,
            rotation_deg=line['rotation_deg'],footprint_mm=footprint,footprint_known=False,u_axis=line['u_axis'],v_axis=line['v_axis'],normal=line['normal'],seam_id=line['id'],distance_along_joint_mm=distance,visual_halves=halves))
    warnings.append(dict(group_id=group['id'],code='closure_reference',message='Rząd koncepcyjny: rezerwy według obrysów podglądu. Parowanie, osie montażu, wycięcia i przestrzeń ruchu wymagają odbioru.'))
    return items,warnings


@lru_cache(maxsize=4)
def _source_envelopes(path,stamp):
    from pathlib import Path
    index_path=Path(path);data=json.loads(index_path.read_text(encoding='utf-8'));result={}
    rows={r['id']:r for r in source_parts.catalog()['items']}
    for key,image in data['images'].items():
        if key not in rows or not image.get('mesh'):continue
        file=(index_path.parent/image['mesh']['file']).resolve()
        if not file.is_relative_to(index_path.parent.resolve()):raise ValueError('Mesh path outside source package')
        raw=file.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=image['mesh']['sha256']:raise ValueError('Source envelope checksum mismatch')
        mesh=json.loads(raw)
        if mesh.get('source_binding')!=rows[key]['source_binding']:raise ValueError('Mixed envelope source')
        bounds=mesh['bounds_m']
        if len(bounds)!=6 or not all(type(x) in (float,int) and math.isfinite(x) for x in bounds) or any(bounds[k+3]<=bounds[k] for k in (0,1)):
            raise ValueError('Invalid source envelope dimensions')
        result[key]=[(bounds[k+3]-bounds[k])*1000 for k in (0,1)]
    return result


def envelopes():
    path=source_parts.configured_path().parent/'images/index.json'
    return dict(_source_envelopes(str(path),path.stat().st_mtime_ns)) if path.exists() else {}
