"""Complete T1-style concept construction. Reference datums, never production approval."""
from collections import Counter
from .part_registry import metadata
from . import studio_parts
from .core_case.t1_mounting import corner_pose,SOCKET_SEAT,support_dimensions
from .core_case.machining_rules import minimum_lid_height
from .core_case.profile_rules import rules as profile_rules, value as profile_value

REQUIRED=['EG-0113','EG-0500/1','EG-0500/2','410429','B1930','B1121']
IDENTITY=[[1,0,0],[0,1,0],[0,0,1]]


def validate(d):
    c=d.get('construction')
    if c is None:return
    if not isinstance(c,dict) or set(c)!={'enabled','wheels','stacking'} or any(type(v) is not bool for v in c.values()):
        raise ValueError('Konstrukcja wymaga trzech jawnych przełączników')
    if not c['enabled']:return
    if d['type']!='case' or len(d['covers'])!=1 or d['covers'][0]['face']!='top':
        raise ValueError('Kompletna konstrukcja jest obecnie dostępna dla skrzyni z jednym górnym wiekiem')
    if c['stacking'] and not c['wheels']:raise ValueError('Gniazda do piętrowania wymagają kół')
    needed=REQUIRED+(['source-caster-epson'] if c['wheels'] else [])+(['W0968Z'] if c['stacking'] else [])
    selected={r['part_id'] for r in d['hardware']}
    if set(needed)-selected:raise ValueError('Wybierz części konstrukcji: '+', '.join(sorted(set(needed)-selected)))
    if min(d['internal_mm'][:2])<380 or d['internal_mm'][2]<160 or d['covers'][0]['depth_mm']<minimum_lid_height():
        raise ValueError('Ten zestaw konstrukcyjny wymaga wnętrza co najmniej 380 × 380 × 160 mm i wieka 110 mm')


def preview(d,sections,placement):
    if not d.get('construction',{}).get('enabled'):return dict(items=[],counts={},panel_count=0,total_count=0)
    body,cover=sections;t=d['thickness_mm'];w,depth,h=body['size_mm'];lid=cover['size_mm'][2];height=h+lid
    rows=[]
    def add(key,part,family,section,position,rotation=IDENTITY,**extra):
        rows.append(dict(id=key,part_id=part,section_id=section,position_mm=position,
                         rotation=rotation,**metadata(family),**extra))
    def profile(key,part,section,rotation,position,length,seed):
        if length<=0:raise ValueError('Brak miejsca na profil: '+key)
        add(key,part,'profiles',section,position,rotation,length_mm=length,seed_length_mm=seed)
    parameters=dict(RP_Length=w,RP_Depth=depth,RP_BaseHeight=h,RP_LidHeight=lid,
                    RP_Thickness=t,RP_DisplayGap=0,RP_JointGap=8.63)
    rules={r['id']:r for r in profile_rules()}
    # Measured native local centres, not centres of the mounted world bounds.
    # Joint corrections reproduce the pinned T1 profile_seating mount revisions.
    cross_centres={'EG-0113':[17.5,17.5],
                   'EG-0500_1':[13.3961848981016,6.15058825963358],
                   'EG-0500_2':[10.5578504046396,6.15]}
    def profile_pose(rule):
        length=profile_value(rule['cut_length'],parameters)
        local=cross_centres[rule['sku']]+[length/2]
        rot=rule['rotation']
        pos=[profile_value(rule['center'][j],parameters)-sum(local[k]*rot[k][j] for k in range(3)) for j in range(3)]
        if rule['sku']=='EG-0500_1':
            wall=rule['id'].rsplit('/',1)[1]
            pos[1 if wall in ('front','rear') else 0]+=1 if wall in ('front','left') else -1
        elif rule['sku']=='EG-0500_2':
            pos[2]+=.05
        return rot,pos,length
    for rule in rules.values():
        if rule['sku']!='EG-0113':continue
        half,edge=rule['id'].split('/')
        section='body' if half in ('base','bottom') else cover['id']
        key=('edge/'+rule['id'] if half in ('bottom','top') else
             'upright/'+section+'/'+str(int('right' in edge))+str(int('rear' in edge)))
        rot,pos,length=profile_pose(rule)
        profile(key,'EG-0113',section,rot,pos,length,590)
    # Paired tongue/groove profiles. Interrupt all rows at complete closure envelopes.
    for face in ['front','rear','left','right']:
        axis=0 if face in ['front','rear'] else 1
        forbidden=[]
        for item in placement['items']:
            if not (item.get('seam_id') or item.get('joint_id')) or item['face']!=face:continue
            a=item['position_mm'][axis];half=item['footprint_mm'][0]/2+5
            forbidden.append((a-half,a+half))
        for sku,section in [('EG-0500_1','body'),('EG-0500_2',cover['id'])]:
            part=sku.replace('_','/');rot,origin,length=profile_pose(rules[sku+'/'+face])
            direction=rot[2][axis]
            low,high=sorted([origin[axis],origin[axis]+direction*length])
            segments=[(low,high)]
            for lo,hi in sorted(forbidden):
                segments=[piece for a,b in segments for piece in [(a,min(b,lo)),(max(a,hi),b)] if piece[1]-piece[0]>2]
            for i,(a,b) in enumerate(segments):
                # Source local Z grows from zero. Negative world directions
                # therefore start at the segment's high endpoint.
                pos=list(origin);pos[axis]=a if direction>0 else b
                profile('joint/'+part+'/'+face+'/'+str(i),part,section,rot,pos,b-a,650)
    for top in (False,True):
        for right in (False,True):
            for rear in (False,True):
                rot,pos=corner_pose(top,right,rear,[w,depth,height]);add('corner/'+str(int(top))+str(int(right))+str(int(rear)),'410429','corners',cover['id'] if top else 'body',pos,rot)
    # The shared rules specify world centres; source meshes keep native local
    # coordinates. Convert the measured local centre into the placement origin.
    # Lid braces use the same catalogue orientation as body braces, not a flip.
    brace_centres={'B1930':[20.,18.25,18.25],'B1121':[15.5,20.,15.5]}
    for rule in rules.values():
        if rule['sku'] not in brace_centres:continue
        section='body' if rule['id'].startswith('base/') else cover['id']
        right='right' in rule['id'];rear='rear' in rule['id']
        rot=rule['rotation'];local=brace_centres[rule['sku']]
        position=[profile_value(rule['center'][j],parameters)-sum(local[k]*rot[k][j] for k in range(3)) for j in range(3)]
        add('brace/'+section+'/'+str(int(right))+str(int(rear)),rule['sku'],'braces',section,position,rot)
    if d['construction']['wheels']:
        inset,pad_length=support_dimensions(depth)
        x_inset=min(150,w*.25);y_inset=100
        for right in (False,True):
            x=w-x_inset if right else x_inset
            add('pad/'+str(int(right)),None,'wheel_pads','body',[x-60,inset,-18],size_mm=[120,pad_length,18])
            for rear in (False,True):
                y=depth-y_inset if rear else y_inset;pair='wheel-'+str(int(right))+str(int(rear))
                rotation=[[1 if right else -1,0,0],[0,0,1],[0,-1 if right else 1,0]]
                position=[x,y,-18]
                add(pair,'source-caster-epson','wheels','body',position,rotation,stacking_pair=pair)
                if d['construction']['stacking']:
                    # Match the native wheel contact point, not the caster's
                    # mounting origin. Both sockets use the measured seat datum.
                    contact_local=[-36.,-132.1,0.]
                    contact=[position[j]+sum(contact_local[k]*rotation[k][j] for k in range(3)) for j in range(3)]
                    seat=[contact[0],contact[1],height]
                    add('socket/'+pair,'W0968Z','stacking_sockets',cover['id'],
                        [seat[k]-SOCKET_SEAT[k] for k in range(3)],stacking_pair=pair,seat_world_mm=seat)
    # Source 38083/W0968Z flange is 136 x 90 mm about its measured seat.
    # Test the actual seats after the caster contact offset, not wheel origins.
    sockets=[r for r in rows if r['family_id']=='stacking_sockets']
    for i,a in enumerate(sockets):
        for b in sockets[i+1:]:
            gaps=[abs(a['seat_world_mm'][k]-b['seat_world_mm'][k])-size
                  for k,size in enumerate((136.,90.))]
            if all(gap < 2.-1e-7 for gap in gaps):
                raise ValueError('Gniazda kół 136 × 90 mm wymagają co najmniej 2 mm odstępu: '
                                 +a['id']+' / '+b['id']+'. Zmień układ lub wymiary skrzyni.')
    counts=dict(Counter(r['part_id'] or 'plywood-wheel-pad' for r in rows))
    return dict(items=rows,counts=counts,status='reference_construction_not_manufacturing',
                notes=['Geometria katalogowa z zapisanej referencji. Wycięcia i pasowanie produkcyjne wymagają osobnego potwierdzenia.'])


def summarize(d,panels,placement,construction):
    """One physical part count for Studio, exports and subsequent CAD adapters."""
    definitions={r['id']:r for r in studio_parts.resolve(d['hardware'])}
    counts=Counter(placement['counts']);counts.update(construction['counts'])
    rows=[dict(part_id='plywood-panels',name='Panele ze sklejki',quantity=len(panels),
               unit='szt.',material_thickness_mm=d['thickness_mm'],**metadata('panels'))]
    for key,quantity in sorted(counts.items()):
        if key=='plywood-wheel-pad':
            rows.append(dict(part_id=key,name='Podpora ze sklejki',quantity=quantity,unit='szt.',
                             material_thickness_mm=18,**metadata('wheel_pads')))
        else:
            definition=definitions[key]
            rows.append(dict(part_id=key,name=definition['name'],quantity=quantity,unit='szt.',**metadata(definition['family_id'])))
    return dict(rows=rows,total_count=sum(r['quantity'] for r in rows),
                definition_count=len(rows),unplaced_selection=sorted(set(definitions)-set(counts)),
                production_approved=False,purchase_bom_ready=False)
