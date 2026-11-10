import json,sys,math
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Integracja'))
from rockpro_cad.core_case.profile_rules import rules,value
from rockpro_cad.core_case.machining_rules import local_cut_pose
out=Path('artifacts/t1-600x500x350-ic2023-20261026')
rows=json.loads((out/'inspect-recovered/inventory.json').read_text(encoding='utf-8-sig'))['rows'];by={r['id']:r for r in rows};fs={f['id']:f for r in rows for f in r.get('features',[])}
p=dict(RP_Length=600.,RP_Depth=500.,RP_BaseHeight=235.,RP_LidHeight=115.,RP_Thickness=9.8,RP_JointGap=8.63,RP_DisplayGap=0.)
I=[[1,0,0],[0,1,0],[0,0,1]]
req={'contract':'rockpro-t1-2023-unsaved-v1','mode':'unsaved','expected_pid':1424,'parameters':p,'sources':{'t1':str(Path('artifacts/ironcad2023-pu1sp1-validation/t1-inspect/source_copy.ics').resolve()),'t2':str(Path('artifacts/ironcad2023-pu1sp1-validation/t2-roundtrip-03/RockPro_T2_reference_IC2023.ics').resolve())},'parts':[],'cuts':[],'check_cases':[]}
parts=req['parts'];index={}
def add(key,kind,R,pos,**kw):
 s=dict(key=key,kind=kind,rotation=R,position=pos,initial=[value(x,p) for x in pos],**kw);parts.append(s);index[key]=s;return s
def box(key,dims,pos):return add(key,'box',I,pos,dimensions=dims,dimensions_initial=[value(x,p) for x in dims])
box('plywood/base/floor',['RP_Length','RP_Depth','RP_Thickness'],['0 mm','0 mm','0 mm'])
box('plywood/lid/roof',['RP_Length','RP_Depth','RP_Thickness'],['0 mm','0 mm','RP_BaseHeight+RP_LidHeight-RP_Thickness'])
for role,z,h in [('base','RP_Thickness','RP_BaseHeight-RP_Thickness'),('lid','RP_BaseHeight+RP_JointGap','RP_LidHeight-RP_JointGap-RP_Thickness')]:
 for wall,y in [('front','0 mm'),('rear','RP_Depth-RP_Thickness')]:box('plywood/'+role+'/'+wall,['RP_Length','RP_Thickness',h],['0 mm',y,z])
 for wall,x in [('left','0 mm'),('right','RP_Length-RP_Thickness')]:box('plywood/'+role+'/'+wall,['RP_Thickness','RP_Depth-2*RP_Thickness',h],[x,'RP_Thickness',z])
profile_id={'EG-0113':9019,'EG-0500_1':248,'EG-0500_2':854}
for row in rules():
 R=row['rotation'];center=list(row['center']);key='profile/'+row['id']
 if row['sku'].startswith('EG-'):
  feature=profile_id[row['sku']];bb=fs[feature]['bbox_m'];mid=[f'{(bb[i]+bb[i+3])*500:.15g} mm' for i in range(2)]+['('+row['cut_length']+')/2']
  if row['sku']=='EG-0500_1':
   for i in (0,1):center[i]=center[i].replace('RP_Thickness/2 - 1 mm','RP_Thickness/2')
  if row['sku']=='EG-0500_2':center[2]+=' + 0.05 mm'
  pos=['('+center[j]+') - ('+' + '.join(f'({R[k][j]})*({mid[k]})' for k in range(3) if R[k][j])+')' for j in range(3)]
  add(key,'profile',R,pos,source='t1',feature_id=feature,length=row['cut_length'])
 else:
  sid=9428 if row['sku']=='B1930' else 13207;bb=by[sid]['bounds_local_m'];mid=[(bb[i]+bb[i+3])*500 for i in range(3)]
  pos=['('+center[j]+f') - ({sum(mid[k]*R[k][j] for k in range(3)):.15g} mm)' for j in range(3)]
  add(key,'hardware',R,pos,source='t1',source_id=sid,source_name=by[sid]['name'])
# Opaque carrying handles from the 2023-compatible T2, four occurrences.
for side,x,R in [('left','0 mm',[[0,-1,0],[-1,0,0],[0,0,-1]]),('right','RP_Length',[[0,1,0],[1,0,0],[0,0,-1]])]:
 for slot,y in enumerate(['RP_Depth/4','3*RP_Depth/4'],1):add(f'handle/{side}/{slot}','hardware',R,[x,y,'RP_BaseHeight/2'],source='t2',source_id=8001,source_name='H7159')
# Front closures and rear lid-stay hinges; each half moves with its own half-case.
for slot,x in enumerate(['150 mm','RP_Length-150 mm'],1):
 for role,sid in [('base',13788),('lid',13740)]:add(f'latch/{slot}/{role}','hardware',[[1,0,0],[0,-1,0],[0,0,-1]],[x,'-2 mm','RP_BaseHeight+3.8538734605 mm'],source='t1',source_id=sid,source_name=by[sid]['name'])
 for role,sid in [('base',13974),('lid',14028)]:add(f'hinge/{slot}/{role}','hardware',[[-1,0,0],[0,1,0],[0,0,-1]],[x,'RP_Depth-6 mm','RP_BaseHeight+RP_JointGap/2-13.5 mm'],source='t1',source_id=sid,source_name=by[sid]['name'])
# Eight rigid ball corners, using proper rotations only.
for top in [False,True]:
 for right in [False,True]:
  for rear in [False,True]:
   signs=[-1 if right else 1,-1 if rear else 1,-1 if top else 1];R=[[int(i==j)*signs[i] for j in range(3)] for i in range(3)]
   if math.prod(signs)<0:R[0],R[1]=R[1],R[0]
   center=['RP_Length-15.5 mm' if right else '15.5 mm','RP_Depth-15.5 mm' if rear else '15.5 mm','RP_BaseHeight+RP_LidHeight-15.5 mm' if top else '15.5 mm']
   pos=[f'({center[j]}) - ({sum(-8.2500125*R[k][j] for k in range(3)):.15g} mm)' for j in range(3)]
   add(f'corner/{int(top)}{int(right)}{int(rear)}','hardware',R,pos,source='t1',source_id=9078,source_name='410429')
for side,x in [('left','150 mm'),('right','RP_Length-150 mm')]:
 box('support/'+side,['120 mm','RP_Depth-40 mm','18 mm'],[x+'-60 mm','20 mm','-18 mm'])
 R=[[-1,0,0],[0,0,1],[0,1,0]] if side=='left' else [[1,0,0],[0,0,1],[0,-1,0]]
 for end,y in [('front','100 mm'),('rear','RP_Depth-100 mm')]:
  add(f'wheel/{side}/{end}','hardware',R,[x,y,'-18 mm'],source='t1',source_id=594,source_name='Assembly1')
  sx=x+(' + 36 mm' if side=='left' else ' - 36 mm')
  add(f'socket/{side}/{end}','hardware',I,[sx,y+'-58.21088152752 mm','RP_BaseHeight+RP_LidHeight+30.20838152752 mm'],source='t1',source_id=13227,source_name='38083')
def cut(key,target,fid,R,center):
 bb=fs[fid]['bbox_m'];mid=[(bb[i]+bb[i+3])*500 for i in range(2)]+[0]
 world=['('+center[j]+f') - ({sum(mid[k]*R[k][j] for k in range(3)):.15g} mm)' for j in range(3)]
 t=index[target];rot,pos=local_cut_pose(R,world,t['rotation'],t['position'])
 req['cuts'].append(dict(key=key,target=target,source='t1',feature_id=fid,rotation=rot,position=pos,initial=[value(v,p) for v in pos]))
for side in ['left','right']:
 R=[[0,1,0],[0,0,1],[1,0,0]] if side=='left' else [[0,-1,0],[0,0,1],[-1,0,0]]
 for slot,y in enumerate(['RP_Depth/4','3*RP_Depth/4'],1):cut(f'handle/{side}/{slot}','plywood/base/'+side,10353,R,['-1 mm' if side=='left' else 'RP_Length+1 mm',y,'RP_BaseHeight/2'])
for slot,x in enumerate(['150 mm','RP_Length-150 mm'],1):
 for role,fid,z in [('base',13727,'RP_BaseHeight-26 mm'),('lid',13723,'RP_BaseHeight+19 mm')]:
  R=[[1,0,0],[0,0,-1],[0,1,0]]
  cut(f'latch/{slot}/{role}','plywood/'+role+'/front',fid,R,[x,'-1 mm',z])
  cut(f'latch-profile/{slot}/{role}','profile/'+('EG-0500_1' if role=='base' else 'EG-0500_2')+'/front',fid,R,[x,'-3 mm',z])
for side,x in [('left','186 mm'),('right','RP_Length-186 mm')]:
 for end,y in [('front','100 mm'),('rear','RP_Depth-100 mm')]:cut(f'socket/{side}/{end}','plywood/lid/roof',13218,[[0,1,0],[1,0,0],[0,0,-1]],[x,y,'RP_BaseHeight+RP_LidHeight+1 mm'])
for name,v in [('resize',dict(p,RP_Length=620.,RP_Depth=520.,RP_BaseHeight=245.)),('final',p)]:
 checks=[]
 for key in ['plywood/base/floor','plywood/lid/roof','handle/left/1','handle/right/2','wheel/right/rear','socket/right/rear']:
  s=index[key];check=dict(key=key,position=[value(x,v) for x in s['position']])
  if s['kind']=='box':check['dimensions']=[value(x,v) for x in s['dimensions']]
  checks.append(check)
 req['check_cases'].append(dict(name=name,parameters=v,checks=checks))
(out/'unsaved-request.json').write_text(json.dumps(req,ensure_ascii=False,indent=2),encoding='utf-8')
print('READY:',len(parts),'parts;',len(req['cuts']),'cutouts; total height',p['RP_BaseHeight']+p['RP_LidHeight'])
