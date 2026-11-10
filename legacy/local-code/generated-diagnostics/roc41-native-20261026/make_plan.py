import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.machining_rules import *
from rockpro_cad.core_case.profile_rules import value
B=Path(__file__).resolve().parent
req=json.loads((B/'prototype_request.json').read_text());pars=req['parameters'];pars.pop('RP_HandleHeight',None);pars['RP_HandleHeightOffset']=0.
inv=json.loads((B/'inspect-prototype/inventory.json').read_text(encoding='utf-8-sig'))['rows'];byid={r['id']:r for r in inv}
receipt=json.loads((B/'base_receipt.json').read_text());pro=receipt['source_profile_report']
bindings={r['id']:r['position'] for r in pro['old_bindings']}
bindings.update({r['node_id']:r['position'] for r in pro['bindings']})
req['cuts']=[];req['mounts']=[]
def mount(id,key,pos):
 r=[[round(x) for x in row[:3]] for row in byid[id]['world_mm'][:3]]
 req['mounts'].append(dict(id=id,key=key,rotation=r,position=pos,initial_mm=[value(x,pars) for x in pos]));return key

def cut(key,owner,family,target,template,rotation,world):
 tr=[[round(x) for x in row[:3]] for row in byid[target]['world_mm'][:3]]
 r,pos=local_cut_pose(rotation,world,tr,bindings[target])
 step=machining_step(key,owner,family,target,template,r,pos,pars);step['world_position']=world;step['world_rotation']=rotation;req['cuts'].append(step)

for side,ids,target in [('left',[682,1726],1002),('right',[836,1880],1008)]:
 for slot,id in enumerate(ids,1):
  y=('RP_Depth/4' if slot==1 else '3*RP_Depth/4')+' + RP_HandleOffset';z='RP_BaseHeight/2 + RP_HandleHeightOffset';key='handles/'+side+'/'+str(slot)
  mount(id,key,['0 mm' if side=='left' else 'RP_Length',y,z])
  r=[[0,-1,0],[0,0,-1],[1,0,0]] if side=='left' else [[0,1,0],[0,0,-1],[-1,0,0]]
  world=['-1 mm' if side=='left' else 'RP_Length + 1 mm',y+(' + 65 mm' if side=='left' else ' - 65 mm'),z+' + 39.067874119633 mm']
  cut(key+'/opening',key,'handles',target,10353,r,world)

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
validate_layout(pars)
validate_steps(req['cuts'],set(m['key'] for m in req['mounts'])|{c['mount_key'] for c in req['cuts'] if c['stage_id']=='wheels'})
req['schema_version']=1;req['contract']='t1-machining-prototype-v1';req['expected_root_count']=66
(B/'full_request.json').write_text(json.dumps(req,indent=2));print(len(req['cuts']),len(req['mounts']))
