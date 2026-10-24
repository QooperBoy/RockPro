"""Rigid paired hinges and caster/socket registration for full-case v3.

Prototype registration, not wheel SKU, load, collision or stacking approval.
"""
from .profile_rules import validate_values
from ..part_registry import metadata

I=[[1,0,0],[0,1,0],[0,0,1]]

def validate_transport_values(values):
    validate_values(values)
    if values['RP_Length']<600 or values['RP_BaseHeight']<160:
        raise ValueError('Case too small for this hinge and caster pattern')
    return dict(values)

def make_rules(catalog):
    if set(catalog)!={'hinge_lid','hinge_base','wheel','socket'}:
        raise ValueError('Explicit four-asset catalog required')
    wheel=catalog['wheel'];socket=catalog['socket']
    cylinder=wheel['rubber_cylinder']
    if abs(cylinder['radius_m']-.05)>1e-6 or abs(abs(cylinder['axis'][2])-1)>1e-6:
        raise ValueError('Pinned 100 mm tread cylinder required')
    tread=[x*1000 for x in wheel['contact_point_m']]
    if max(abs(x-y) for x,y in zip(tread,[-36,-132.1,0]))>.003:
        raise ValueError('Unexpected caster contact datum')
    mount=[x*1000 for x in socket['mount_point_m']]
    if socket['mount_face']['reversed'] is not True or max(abs(x-y) for x,y in zip(socket['mount_face']['normal'],[0,0,1]))>1e-6:
        raise ValueError('Socket underside plane required')
    rows=[]
    for side in ('left','right'):
        jointx=None
        for role in ('base','lid'):
            bounds=catalog['hinge_'+role]['export_signature'][0]['bounds_m']
            cx=(bounds[0]+bounds[3])*500
            x=('150 mm' if side=='left' else 'RP_Length - 150 mm')+f' - ({cx:.15g} mm)'
            if jointx is not None and abs(cx-jointx)>.003:raise ValueError('Hinge halves have different joint X datum')
            jointx=cx
            z='RP_BaseHeight + 1.01 mm + (RP_JointGap - 8.63 mm)/2'
            if role=='lid':z+=' + RP_DisplayGap'
            rows.append(dict(id='hinge/'+side+'/'+role,asset='hinge_'+role,kind='hinge',
                rotation=I,local_anchor_mm=[0,0,0],anchor=[x,'RP_Depth + 10.70980476265 mm',z]))
    for side in ('left','right'):
        x='150 mm' if side=='left' else 'RP_Length - 150 mm'
        rows.append(dict(id='pad/'+side,kind='pad',rotation=I,
            dimensions=['120 mm','RP_Depth - 40 mm','18 mm'],
            anchor=[x,'RP_Depth/2','-18 mm']))
        R=[[-1,0,0],[0,0,1],[0,1,0]] if side=='left' else [[1,0,0],[0,0,1],[0,-1,0]]
        dx=sum(tread[k]*R[k][0] for k in range(3))
        for end in ('front','rear'):
            y='100 mm' if end=='front' else 'RP_Depth - 100 mm'
            pair=side+'/'+end
            rows.append(dict(id='wheel/'+pair,pair=pair,asset='wheel',kind='wheel',rotation=R,
                local_anchor_mm=[0,0,0],anchor=[x,y,'-18 mm'],contact_local_mm=tread))
            rows.append(dict(id='socket/'+pair,pair=pair,asset='socket',kind='socket',rotation=I,
                local_anchor_mm=mount,anchor=[f'({x}) + ({dx:.15g} mm)',y,
                    'RP_BaseHeight + RP_LidHeight + RP_DisplayGap']))
    for row in rows:
        row.update(metadata(row['kind']))
        if row.get('pair'):row['stacking_interface_id']='caster100/'+row['pair']
        R=row['rotation'];det=sum(R[0][i]*(R[1][(i+1)%3]*R[2][(i+2)%3]-R[1][(i+2)%3]*R[2][(i+1)%3]) for i in range(3))
        if det!=1:raise ValueError('Reflection/scaling refused')
    return rows
