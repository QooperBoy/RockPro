"""Generate the pinned T1 machining plan from a measured inventory and v3 receipt.

No CAD mutation here. Run the resulting plan with run_t1_machining_job.py.
The plan is local/private evidence, not a general-purpose ICS interface.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.machining_rules import local_cut_pose, machining_step, validate_layout, validate_steps, minimum_lid_height
from rockpro_cad.core_case.profile_rules import value

BASELINE_SHA='b3b6b2f83a916602a575816663025e954588b4f5112a1e5be610f3c6dd2ad3f5'
TEMPLATES_SHA='e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1'

def make_plan(source, templates, inventory, receipt, pid):
    source=Path(source).resolve(strict=True);templates=Path(templates).resolve(strict=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(source)!=BASELINE_SHA or sha(templates)!=TEMPLATES_SHA:
        raise ValueError('Only the measured T1 prototype/source pair is supported')
    if inventory['source_sha256']!=BASELINE_SHA or receipt['contract']!='full_case_transport_v3' or receipt['passed'] is not True:
        raise ValueError('Pinned inventory and successful full-case receipt required')
    pars=dict(RP_Length=650.,RP_Depth=500.,RP_BaseHeight=300.,RP_LidHeight=115.,RP_Thickness=9.8,RP_DisplayGap=0.,RP_JointGap=8.63,
              RP_HandleOffset=0.,RP_HandleHeightOffset=0.,RP_LatchInset=150.,RP_HingeInset=150.)
    req=dict(mode='build',expected_pid=pid,source=str(source),source_sha256=BASELINE_SHA,templates=str(templates),templates_sha256=TEMPLATES_SHA,parameters=pars)
    inv=inventory['rows'];byid={r['id']:r for r in inv}
    pro=receipt['source_profile_report']
    bindings={r['id']:r['position'] for r in pro['old_bindings']}
    bindings.update({r['node_id']:r['position'] for r in pro['bindings']})
    req['cuts']=[];req['mounts']=[]
    def mount(id,key,pos):
        r=[[round(x) for x in row[:3]] for row in byid[id]['world_mm'][:3]]
        req['mounts'].append(dict(id=id,key=key,rotation=r,position=pos,initial_mm=[value(x,pars) for x in pos]));return key
    def cut(key,owner,family,target,template,rotation,world):
        tr=[[round(x) for x in row[:3]] for row in byid[target]['world_mm'][:3]]
        r,pos=local_cut_pose(rotation,world,tr,bindings[target])
        step=machining_step(key,owner,family,target,template,r,pos,pars)
        step.update(world_position=world,world_rotation=rotation)
        req['cuts'].append(step)
    # Align groove centre with plywood; preserve the measured section, not the old offset.
    for node,axis,delta in [(1146,1,1),(1152,1,-1),(1158,0,1),(1164,0,-1),
                            (1170,2,.05),(1176,2,.05),(1182,2,.05),(1188,2,.05)]:
        bindings[node]=list(bindings[node]);bindings[node][axis]+=f' + ({delta} mm)'
        mount(node,'profile_seating/'+str(node),bindings[node])

    for side,ids,target in [('left',[682,1726],1002),('right',[836,1880],1008)]:
     for slot,id in enumerate(ids,1):
      y=('RP_Depth/4' if slot==1 else '3*RP_Depth/4')+' + RP_HandleOffset';z='RP_BaseHeight/2 + RP_HandleHeightOffset';key='handles/'+side+'/'+str(slot)
      mount(id,key,['0 mm' if side=='left' else 'RP_Length',y,z])
      r=[[0,-1,0],[0,0,-1],[1,0,0]] if side=='left' else [[0,1,0],[0,0,-1],[-1,0,0]]
      world=['-1 mm' if side=='left' else 'RP_Length + 1 mm',y+(' + 65 mm' if side=='left' else ' - 65 mm'),z+' + 39.067874119633 mm']
      cut(key+'/opening',key,'handles',target,10353,r,world)
      # The current cup flares at the mounting face: shallow relief, not a larger through-hole.
      pocket=[('0 mm' if side=='left' else 'RP_Length'),y+(' + 68 mm' if side=='left' else ' - 68 mm'),z+' + 42.067874119633 mm']
      cut(key+'/flange_relief',key,'handles',target,10353,r,pocket)
      req['cuts'][-1].update(through_target=False,size=['136 mm','84 mm','1.25 mm'])

    for family,wall,ids in [('latches','front',[(192,78),(494,380)]),('hinges','rear',[(1226,1336),(1386,1496)])]:
     for n,(base,lid) in enumerate(ids):
      inset='RP_LatchInset' if family=='latches' else 'RP_HingeInset';x=inset if n==0 else 'RP_Length - '+inset
      key=family+'/'+str(n+1)
      for half,id in [('base',base),('lid',lid)]:
       if family=='latches':pos=[x,'11.9 mm','RP_BaseHeight - 15.646126539485 mm'+(' + RP_DisplayGap' if half=='lid' else '')]
       else:pos=[x+' + 4.8170105088013 mm','RP_Depth + 10.70980476265 mm','RP_BaseHeight + 1.01 mm'+(' + RP_DisplayGap' if half=='lid' else '')]
       mount(id,key+'/'+half,pos)
       upper=half=='lid';front=wall=='front';target=(1014 if upper else 990) if front else (1020 if upper else 996)
       # Constructor's exact rounded profiles, anchored to the two plywood edges.
       r=[[0,0,-1],[-1 if front else 1,0,0],[0,1 if front else -1,0]] if upper else [[0,0,-1],[1 if front else -1,0,0],[0,1 if front else -1,0]]
       template=(12455 if upper else 12459) if front else (12451 if upper else 12447)
       wx=x+(' + 49.1 mm' if (front==upper) else ' - 49.1 mm')
       wz='RP_BaseHeight + RP_JointGap + RP_DisplayGap + 47 mm' if upper else 'RP_BaseHeight'
       cut(key+'/'+half+'/panel',key+'/'+half,family,target,template,r,[wx,'-1 mm' if front else 'RP_Depth + 1 mm',wz])
       # Profile relief is a separate target and travels in the same assembly step.
       target=(1170 if upper else 1146) if front else (1176 if upper else 1152)
       template=12932 if front else (13198 if upper else 13202)
       width=98.2 if front else (103.65 if upper else 100.2)
       r=[[0,0,-1],[1,0,0],[0,1 if front else -1,0]]
       wz='RP_BaseHeight + 29 mm'+(' + RP_DisplayGap' if upper else '')
       cut(key+'/'+half+'/profile',key+'/'+half,family,target,template,r,[x+f' - {width/2} mm','-3 mm' if front else 'RP_Depth + 14 mm',wz])

    # Recessed stacking cups use the constructor's 103 x 55 mm contour.
    for side in ['left','right']:
     for end in ['front','rear']:
      x='186 mm' if side=='left' else 'RP_Length - 186 mm';y='100 mm' if end=='front' else 'RP_Depth - 100 mm';key='stacking_sockets/'+side+'/'+end
      cut(key+'/opening',key,'stacking_sockets',1044,13218,[[0,1,0],[1,0,0],[0,0,-1]],[x+' - 51.5 mm',y+' - 27.5 mm','RP_BaseHeight + RP_LidHeight + RP_DisplayGap + 1 mm'])
    # Double-sided edge rebates leave a 9.4 mm tongue in the measured 9.5 mm groove.
    for half,targets in [('base',[990,996,1002,1008]),('lid',[1014,1020,1026,1032])]:
        z='RP_BaseHeight - 20 mm' if half=='base' else 'RP_BaseHeight + RP_JointGap + RP_DisplayGap'
        height='21 mm' if half=='base' else '16 mm'
        for wall,target in zip(['front','rear','left','right'],targets):
            frontback=wall in ('front','rear')
            rotation=[[0,0,1],[1,0,0],[0,1,0]] if frontback else [[0,0,1],[0,1,0],[1,0,0]]
            starts={'front':['0 mm','RP_Thickness - .2 mm'], 'rear':['RP_Depth - RP_Thickness','RP_Depth - .2 mm'],
                    'left':['0 mm','RP_Thickness - .2 mm'],'right':['RP_Length - RP_Thickness','RP_Length - .2 mm']}[wall]
            owner='profile_seating/'+str({'base':{'front':1146,'rear':1152,'left':1158,'right':1164},
                                          'lid':{'front':1170,'rear':1176,'left':1182,'right':1188}}[half][wall])
            for face,start in enumerate(starts):
                world=['-1 mm',start,z] if frontback else [start,'-1 mm',z]
                key='edge_rebate/'+half+'/'+wall+'/'+str(face)
                cut(key,owner,'profiles',target,12932,rotation,world)
                req['cuts'][-1].update(through_target=False,size=[height,('RP_Length' if frontback else 'RP_Depth')+' + 2 mm','.2 mm'])

    # Leave 0.1 mm axial clearance above the female groove bottom after its fit correction.
    for wall,target in zip(['front','rear','left','right'],[1014,1020,1026,1032]):
        frontback=wall in ('front','rear')
        rotation=[[0,0,1],[1,0,0],[0,1,0]] if frontback else [[0,0,1],[0,1,0],[1,0,0]]
        start={'front':'-1 mm','rear':'RP_Depth - RP_Thickness - 1 mm','left':'-1 mm','right':'RP_Length - RP_Thickness - 1 mm'}[wall]
        z='RP_BaseHeight + RP_JointGap + RP_DisplayGap'
        world=['-1 mm',start,z] if frontback else [start,'-1 mm',z]
        owner='profile_seating/'+str({'front':1170,'rear':1176,'left':1182,'right':1188}[wall])
        cut('lid_seating/'+wall,owner,'profiles',target,12932,rotation,world)
        req['cuts'][-1].update(through_target=False,size=['.1 mm',('RP_Length' if frontback else 'RP_Depth')+' + 2 mm','RP_Thickness + 2 mm'])

    validate_layout(pars)
    validate_steps(req['cuts'],set(m['key'] for m in req['mounts'])|{c['mount_key'] for c in req['cuts'] if c['stage_id']=='wheels'})
    req['schema_version']=1;req['contract']='t1-machining-prototype-v2';req['expected_root_count']=66
    req['handles_per_wall'] = 2
    req['mounting_library'] = [
        dict(sku=sku, template_version='t1-fit-v2',
             plywood_cutout_requirement='required', profile_relief_required=profile,
             source_sha256=TEMPLATES_SHA, template_feature_ids=features,
             production_approved=False)
        for sku, profile, features in [
            ('H7159', False, [10353]),
            ('17251S', True, [12455, 12459, 12932]),
            ('270836', True, [12451, 12447, 13198, 13202]),
            ('W0968Z', False, [13218]),
        ]
    ]
    req['clearance_policy'] = dict(minimum_lid_height_mm=minimum_lid_height(),
                                  hardware_to_top_profile_mm=5.,
                                  lid_height_override_authorized=True,
                                  male_profile_transverse_correction_mm=1.,
                                  female_profile_axial_clearance_mm=.05,
                                  plywood_edge_rebate_per_face_mm=.2,
                                  lid_plywood_end_trim_mm=.1)
    return req

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('source','templates','inventory','receipt','output'):parser.add_argument('--'+arg,required=True,type=Path)
    parser.add_argument('--pid',required=True,type=int)
    args=parser.parse_args()
    plan=make_plan(args.source,args.templates,json.loads(args.inventory.read_text(encoding='utf-8-sig')),
                   json.loads(args.receipt.read_text(encoding='utf-8-sig')),args.pid)
    with args.output.open('x',encoding='utf-8') as f:json.dump(plan,f,ensure_ascii=False,indent=2)
