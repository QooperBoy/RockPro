"""Complete T1-style concept construction. Reference datums, never production approval."""
from collections import Counter
from .part_registry import metadata
from . import studio_parts
from .core_case.t1_mounting import corner_pose,SOCKET_SEAT,support_dimensions
from .core_case.machining_rules import minimum_lid_height

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
    body,cover=sections;w,depth,h=body['size_mm'];lid=cover['size_mm'][2];height=h+lid
    rows=[]
    def add(key,part,family,section,position,rotation=IDENTITY,**extra):
        rows.append(dict(id=key,part_id=part,section_id=section,position_mm=position,
                         rotation=[list(r) for r in rotation],**metadata(family),**extra))
    def profile(key,part,section,rotation,position,length,seed):
        if length<=0:raise ValueError('Brak miejsca na profil: '+key)
        add(key,part,'profiles',section,position,rotation,length_mm=length,seed_length_mm=seed)
    # Same 35 mm angle and 33 mm inner edge as the corrected native T1.
    for top,z,section in [(False,0,'body'),(True,height,cover['id'])]:
        for face,rot,pos,length in [
            ('front',[[0,-1,0],[0,0,-1 if not top else 1],[1 if not top else -1,0,0]],[30 if not top else w-30,33,33 if not top else z-33],w-60),
            ('rear',[[0,1,0],[0,0,-1 if not top else 1],[-1 if not top else 1,0,0]],[w-30 if not top else 30,depth-33,33 if not top else z-33],w-60),
            ('left',[[-1,0,0],[0,0,-1 if not top else 1],[0,-1 if not top else 1,0]],[33,depth-30 if not top else 30,33 if not top else z-33],depth-60),
            ('right',[[1,0,0],[0,0,-1 if not top else 1],[0,1 if not top else -1,0]],[w-33,30 if not top else depth-30,33 if not top else z-33],depth-60)]:
            profile('edge/'+('top' if top else 'bottom')+'/'+face,'EG-0113',section,rot,pos,length,590)
    for section,z,high in [('body',0,h),(cover['id'],h,lid)]:
        for right,rear,rot in [(False,False,[[-1,0,0],[0,-1,0],[0,0,1]]),(True,False,[[0,-1,0],[1,0,0],[0,0,1]]),(False,True,[[0,1,0],[-1,0,0],[0,0,1]]),(True,True,[[1,0,0],[0,1,0],[0,0,1]])]:
            profile('upright/'+section+'/'+str(int(right))+str(int(rear)),'EG-0113',section,rot,[w-33 if right else 33,depth-33 if rear else 33,z+30],high-60,590)
    # Paired tongue/groove profiles. Interrupt all rows at complete closure envelopes.
    for face in ['front','rear','left','right']:
        axis=0 if face in ['front','rear'] else 1;length=[w,depth][axis]
        forbidden=[]
        for item in placement['items']:
            if not item.get('seam_id') or item['face']!=face:continue
            a=item['position_mm'][axis];half=item['footprint_mm'][0]/2+5
            forbidden.append((a-half,a+half))
        segments=[(0,length)]
        for lo,hi in sorted(forbidden):
            segments=[piece for a,b in segments for piece in [(a,min(b,lo)),(max(a,hi),b)] if piece[1]-piece[0]>2]
        for part,section,zz in [('EG-0500/1','body',h-19.497),('EG-0500/2',cover['id'],h+23.709)]:
            for i,(a,b) in enumerate(segments):
                # Rotate native profile Z into the perimeter direction.
                if face=='front':rot=[[0,0,1],[0,-1,0],[1,0,0]];pos=[a,10.0506 if section=='body' else -1.25,zz]
                elif face=='rear':rot=[[0,0,-1],[0,1,0],[1,0,0]];pos=[a,depth-10.0506 if section=='body' else depth+1.25,zz]
                elif face=='left':rot=[[0,0,-1],[-1,0,0],[0,1,0]];pos=[10.0506 if section=='body' else -1.25,a,zz]
                else:rot=[[0,0,1],[1,0,0],[0,1,0]];pos=[w-10.0506 if section=='body' else w+1.25,a,zz]
                if section!='body':rot=[[-v for v in row] if k<2 else row for k,row in enumerate(rot)]
                profile('joint/'+part+'/'+face+'/'+str(i),part,section,rot,pos,b-a,650)
    for top in (False,True):
        for right in (False,True):
            for rear in (False,True):
                rot,pos=corner_pose(top,right,rear,[w,depth,height]);add('corner/'+str(int(top))+str(int(right))+str(int(rear)),'410429','corners',cover['id'] if top else 'body',pos,rot)
    # Opaque, whole corner braces; no modification of catalogue hardware.
    for section,z,flip in [('body',h-40,False),(cover['id'],h+40,True)]:
        for right in (False,True):
            for rear in (False,True):
                part='B1121' if rear else 'B1930'
                rotations={
                    (False,False,False):[[0,0,1],[1,0,0],[0,1,0]],
                    (False,True,False):[[0,0,1],[0,1,0],[-1,0,0]],
                    (False,False,True):[[1,0,0],[0,0,1],[0,-1,0]],
                    (False,True,True):[[0,-1,0],[0,0,1],[-1,0,0]],
                    (True,False,False):[[0,0,-1],[0,1,0],[1,0,0]],
                    (True,True,False):[[0,0,-1],[-1,0,0],[0,1,0]],
                    (True,False,True):[[0,-1,0],[0,0,-1],[1,0,0]],
                    (True,True,True):[[-1,0,0],[0,0,-1],[0,-1,0]],
                }
                rot=rotations[(flip,right,rear)]
                add('brace/'+section+'/'+str(int(right))+str(int(rear)),part,'braces',section,[w+4.7 if right else -4.7,depth+4.7 if rear else -4.7,z],rot)
    if d['construction']['wheels']:
        inset,pad_length=support_dimensions(depth)
        x_inset=min(150,w*.25);y_inset=100
        for right in (False,True):
            x=w-x_inset if right else x_inset
            add('pad/'+str(int(right)),None,'wheel_pads','body',[x-60,inset,-18],size_mm=[120,pad_length,18])
            for rear in (False,True):
                y=depth-y_inset if rear else y_inset;pair='wheel-'+str(int(right))+str(int(rear))
                add(pair,'source-caster-epson','wheels','body',[x,y,-18],[[1,0,0],[0,-1,0],[0,0,-1]],stacking_pair=pair)
                if d['construction']['stacking']:
                    # This source socket's seat is not its bbox top or bottom.
                    add('socket/'+pair,'W0968Z','stacking_sockets',cover['id'],
                        [x-SOCKET_SEAT[0],y-SOCKET_SEAT[1],height-SOCKET_SEAT[2]],stacking_pair=pair,seat_world_mm=[x,y,height])
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
