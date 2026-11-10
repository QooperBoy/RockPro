"""Prepare an explicit in-memory repair of the measured 72-root T1 prototype.

Input evidence/IDs stay private. No CAD calls; no source models are saved.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Integracja'))
from rockpro_cad.core_case.t1_mounting import PARAMETERS_PL, corner_pose, SOCKET_SEAT
from rockpro_cad.core_case.profile_rules import value
from rockpro_cad.core_case.machining_rules import local_cut_pose


def polish_label(key):
    words={'plywood':'Sklejka','base':'korpus','lid':'pokrywa','floor':'dno','roof':'płyta górna',
           'front':'przód','rear':'tył','left':'lewa','right':'prawa','top':'góra','bottom':'dół',
           'profile':'Profil','handle':'Uchwyt H7159','latch':'Zamek L905/915','hinge':'Zawias 27095',
           'wheel':'Koło','socket':'Gniazdo koła 38083','support':'Podpora kół',
           'brace':'Wzmocnienie','corner':'Narożnik 410429'}
    if key.startswith('corner/'):
        t,r,b=map(int,key.split('/')[1]);return 'Narożnik 410429 — '+('góra' if t else 'dół')+' / '+('prawa' if r else 'lewa')+' / '+('tył' if b else 'przód')
    return ' — '.join(words.get(x,x) for segment in key.split('/') for x in (segment.split('-') if segment.startswith(('brace-','front-','rear-')) else [segment]))


def prepare(original, before):
    req=copy.deepcopy(original)
    if before['document']!='Scene14' or len(before['nodes'])!=72:
        raise ValueError('Expected the measured Scene14 prototype')
    req.update(contract='rockpro-t1-mounting-repair-v1',mode='repair-unsaved',document='Scene14',guid=before['guid'])
    req['expected_names']={str(n['id']):n['name'] for n in before['nodes']}
    ids={n['name'].removeprefix('RockPro / '):n['id'] for n in before['nodes']}
    req['parameters'].update(RP_HandleOffset=0.,RP_HandleHeightOffset=0.,RP_LatchInset=150.,RP_HingeInset=150.,RP_MountClearance=2.)
    p=req['parameters'];parts={s['key']:s for s in req['parts']}
    def replace_inset(expr,parameter):
        return expr.replace('150 mm',parameter)
    for s in req['parts']:
        k=s['key'];s['id']=ids[k];s['label']='RockPro | '+polish_label(k)
        if k.startswith('corner/'):
            t,r,b=map(int,k.split('/')[1]);R,_=corner_pose(t,r,b,(600,500,350));s['rotation']=R
            limits=['RP_Length' if r else '0 mm','RP_Depth' if b else '0 mm','RP_BaseHeight+RP_LidHeight+RP_DisplayGap' if t else '0 mm']
            s['position']=[f'({limits[j]}) - ({16.5*sum(R[a][j] for a in range(3)):g} mm)' for j in range(3)]
        elif k.startswith('socket/'):
            s['position'][2]=f'RP_BaseHeight+RP_LidHeight+RP_DisplayGap - ({SOCKET_SEAT[2]:.15g} mm)'
        elif k.startswith('support/'):
            s['position'][1]='33 mm+RP_MountClearance'
            s['dimensions'][1]='RP_Depth-2*(33 mm+RP_MountClearance)'
        elif k.startswith('handle/'):
            s['position'][1]+='+RP_HandleOffset';s['position'][2]+='+RP_HandleHeightOffset'
        elif k.startswith(('hinge/','latch/')):
            s['position'][0]=replace_inset(s['position'][0],'RP_HingeInset' if k.startswith('hinge/') else 'RP_LatchInset')
            if k.endswith('/lid'):s['position'][2]+='+RP_DisplayGap'
        if k.startswith('plywood/lid/'):
            s['position'][2]+='+RP_DisplayGap'
    for c in req['cuts']:
        if c['key'].startswith('handle/'):
            c['position'][1]+='+RP_HandleOffset';c['position'][2]+='+RP_HandleHeightOffset'
        if c['key'].startswith(('latch/','latch-profile/')):
            c['position'][0]=replace_inset(c['position'][0],'RP_LatchInset')
            # Existing cut local coordinates remain attached to the moving lid.
    req['new_cuts']=[]
    for slot,x in enumerate(['RP_HingeInset','RP_Length-RP_HingeInset'],1):
        for sku in ['EG-0500_1','EG-0500_2']:
            target=parts['profile/'+sku+'/rear']
            world=[x+'-51 mm-RP_MountClearance','RP_Depth-30 mm','RP_BaseHeight-70 mm'+('+RP_DisplayGap' if sku.endswith('_2') else '')]
            rotation,pos=local_cut_pose([[1,0,0],[0,1,0],[0,0,1]],world,target['rotation'],target['position'])
            req['new_cuts'].append(dict(key=f'hinge-profile/{slot}/{sku}',target=target['key'],rotation=rotation,position=pos,dimensions=['102 mm+2*RP_MountClearance','60 mm','140 mm']))
    # All shape formulas and names are translated in this new prototype only.
    mapping={k:v[0] for k,v in PARAMETERS_PL.items()}
    def tr(text):
        return re.sub(r'\bRP_\w+\b',lambda m:mapping.get(m[0],m[0]),text)
    for s in req['parts']+req['cuts']+req['new_cuts']:
        s['initial']=[value(x,p) for x in s['position']]
        s['position']=[tr(x) for x in s['position']]
        if 'dimensions' in s:
            s['dimensions_initial']=[value(x,p) for x in s['dimensions']]
            s['dimensions']=[tr(x) for x in s['dimensions']]
        if 'length' in s:s['length']=tr(s['length'])
    req['old_parameters']=list(original['parameters'])
    req['parameters']={mapping[k]:v for k,v in p.items()}
    req['notes']={name:note for name,note in PARAMETERS_PL.values()}
    req['check_cases']=[dict(name='wymiary_docelowe',parameters=req['parameters']),dict(name='zmiana_parametrow',parameters=dict(req['parameters'],RP_Dlugosc=640.,RP_Glebokosc=540.,RP_WysokoscKorpusu=255.,RP_WysokoscPokrywy=125.,RP_PrzesuniecieUchwytow=5.,RP_PodniesienieUchwytow=4.,RP_OdsuniecieZawiasow=165.,RP_OdsuniecieZamkow=160.,RP_LuzMontazowy=3.,RP_RozsunieciePokrywy=15.)),dict(name='powrot_600_500_350',parameters=req['parameters'])]
    for case in req['check_cases']:
        case['checks']=[]
        for s in req['parts']:
            row=dict(key=s['key'],position=[value(x,case['parameters']) for x in s['position']],rotation=s['rotation'])
            if 'dimensions' in s:row['dimensions']=[value(x,case['parameters']) for x in s['dimensions']]
            if 'length' in s:row['length']=value(s['length'],case['parameters'])
            case['checks'].append(row)
    return req


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('original',type=Path);parser.add_argument('before',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    plan=prepare(read(args.original),read(args.before))
    with args.output.open('x',encoding='utf-8') as f:json.dump(plan,f,ensure_ascii=False,indent=2)
    print('Plan:',len(plan['parts']),'elementów,',len(plan['new_cuts']),'przerw przy zawiasach; bez zapisu CAD')
