"""Rigid H7159 on opposing side walls, perpendicular to the rear hinge wall."""
from .profile_rules import value


def side_handle_rules(values, per_wall=2):
    if type(per_wall) is not int or per_wall not in (1, 2):
        raise ValueError('Wybierz 1 albo 2 uchwyty na każdej z dwóch przeciwległych ścian')
    slots=['RP_Depth/2'] if per_wall==1 else ['RP_Depth/4','3*RP_Depth/4']
    centers=[value(s,values) for s in slots]
    # Measured flange 161 x 107 mm; leave room for 35 mm edge profiles.
    if (min(centers)-80.5<35 or values['RP_Depth']-max(centers)-80.5<35
            or (per_wall==2 and centers[1]-centers[0]<181)
            or values['RP_BaseHeight']/2-53.5<35):
        raise ValueError('Uchwyty nie mieszczą się: wybierz po jednym na ścianę lub zmień gabaryt; nie skaluj okuć')
    rows=[]
    for side,x,rotation in (
        ('left','0 mm',[[0,-1,0],[-1,0,0],[0,0,-1]]),
        ('right','RP_Length',[[0,1,0],[1,0,0],[0,0,-1]])):
        for i,y in enumerate(slots):
            rows.append(dict(id=f'handles/{side}/{i+1}',side=side,kind='handles',
                             rotation=rotation,position=[x,y,'RP_BaseHeight/2']))
    return rows
