"""Nominal hinge lines from section topology; not approved hinge machining."""
import math


def lines(draft, sections, mount_faces):
    body=sections[0];x,y,z=body['position_mm'];w,d,h=body['size_mm']
    by_face={(f['section_id'],f['face']):f for f in mount_faces};result=[]
    for cover in draft['covers']:
        if cover['kind']!='hinged':continue
        high=cover['hinge_edge']=='high'
        if cover['face']=='top':
            face='rear' if high else 'front';start=[x,y+(d if high else 0),z+h];end=[x+w,start[1],z+h]
            rotation=0;negative=h
        else:
            face='right' if high else 'left';start=[x+(w if high else 0),y,z];end=[start[0],y,z+h]
            rotation=90 if high else 270;negative=d
        if ('body',face) not in by_face or (cover['id'],face) not in by_face:continue
        frame=by_face[('body',face)]
        result.append(dict(id='joint-'+cover['id'],cover_id=cover['id'],label='Korpus ↔ '+cover['label']+' · '+frame['label'],
            face=face,frame_key=frame['key'],start_mm=start,end_mm=end,length_mm=math.dist(start,end),
            rotation_deg=rotation,negative_space_mm=negative,positive_space_mm=cover['depth_mm'],
            u_axis=frame['u_axis'],v_axis=frame['v_axis'],normal=frame['normal']))
    return result


def resolve(group,line,frame,footprint):
    n=group['hinge_count'];inset=group['edge_inset_mm'];length=line['length_mm'];items=[]
    for i in range(n):
        distance=length/2 if n==1 else inset+i*(length-2*inset)/(n-1)
        pos=[line['start_mm'][k]+distance/length*(line['end_mm'][k]-line['start_mm'][k]) for k in range(3)]
        delta=[pos[k]-frame['origin_mm'][k] for k in range(3)]
        uv=[sum(delta[k]*a[k] for k in range(3))/frame['size_mm'][j] for j,a in enumerate((frame['u_axis'],frame['v_axis']))]
        size=list(footprint or [64.,44.]);angle=math.radians(line['rotation_deg'])
        cross=[-math.sin(angle)*line['u_axis'][k]+math.cos(angle)*line['v_axis'][k] for k in range(3)]
        halves=[dict(section_id=section,position_mm=[pos[k]+sign*size[1]/4*cross[k] for k in range(3)],uv_range=uv_range)
                for section,sign,uv_range in [('body',-1,[0,.5]),(line['cover_id'],1,[.5,1])]]
        if line['rotation_deg']%180:size.reverse()
        items.append(dict(id=group['id']+':joint:'+str(i),group_id=group['id'],part_id=group['part_id'],revision=group['revision'],
            section_id='body',face=line['face'],face_key=frame['key'],u=uv[0],v=uv[1],position_mm=pos,
            rotation_deg=line['rotation_deg'],footprint_mm=size,footprint_known=footprint is not None,
            u_axis=line['u_axis'],v_axis=line['v_axis'],normal=line['normal'],joint_id=line['id'],
            distance_along_joint_mm=distance,visual_halves=halves))
    return items
