"""Plan source-pinned hinge openings and stage grouping for an owned T1 scene."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Integracja'))
from rockpro_cad.core_case.scene_structure import group_for_part, validate_t1_machining
from rockpro_cad.core_case.machining_rules import local_cut_pose
from rockpro_cad.core_case.profile_rules import value
from rockpro_cad.core_case.t1_mounting import HINGE_27095_OPENING


def prepare(prior, inventory, source):
    req=copy.deepcopy(prior)
    req.update(contract='rockpro-t1-structure-v1', mode='structure-unsaved', phase='cuts')
    req['expected_names']={str(p['id']):p['label'] for p in req['parts']}
    req['source']=str(source.resolve(strict=True))
    req['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    rows={r['id']:r for r in inventory['rows']}
    parts={p['key']:p for p in req['parts']}
    groups={}
    for p in req['parts']:
        stage=group_for_part(p['key']);p['group_id']=stage['id'];groups[stage['id']]=stage
    req['groups']=sorted(groups.values(),key=lambda g:g['label'])
    ops=[]
    for c in req['cuts']:
        owner=c['key'].replace('latch-profile/','latch/')
        ops.append(dict(key=c['key'],owner=owner,target=c['target']))
    for c in req['new_cuts']:
        _,slot,sku=c['key'].split('/')
        owner='hinge/'+slot+('/base' if sku.endswith('_1') else '/lid')
        ops.append(dict(key=c['key'],owner=owner,target=c['target']))
    req['hinge_cuts']=[]
    for slot in (1,2):
        for half,fid,root_id in [('base',13737,13974),('lid',13731,14028)]:
            owner=f'hinge/{slot}/{half}';target=f'plywood/{half}/rear'
            mount=parts[owner]
            original_rotation=[[round(x) for x in row[:3]] for row in rows[root_id]['world_mm'][:3]]
            if original_rotation!=mount['rotation']:raise ValueError('Unconfirmed hinge orientation')
            template=copy.deepcopy(HINGE_27095_OPENING)
            world=[f'({mount["position"][0]}) - {template["width_mm"]/2:g} mm',
                   'RP_Glebokosc + 1 mm',
                   f'({mount["position"][2]}) - {template["height_mm"]/2:g} mm']
            r=[[1,0,0],[0,0,1],[0,-1,0]]
            rotation,position=local_cut_pose(r,world,parts[target]['rotation'],parts[target]['position'])
            key=f'hinge-panel/{slot}/{half}'
            cut=dict(key=key,owner=owner,target=target,template=template,rotation=rotation,position=position,
                     initial=[value(x,req['parameters']) for x in position],
                     label=f'Wycięcie pod zawias {slot} — '+('korpus' if half=='base' else 'pokrywa'),
                     template_revision=template['revision'])
            req['hinge_cuts'].append(cut);ops.append(dict(key=key,owner=owner,target=target))
    validate_t1_machining(parts,ops)
    req['operations']=ops
    for case in req['check_cases']:
        case['cut_checks']=[dict(key=c['key'],target=c['target'],position=[value(x,case['parameters']) for x in c['position']]) for c in req['hinge_cuts']]
    return req


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('prior',type=Path);parser.add_argument('inventory',type=Path);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    req=prepare(read(args.prior),read(args.inventory),args.source)
    with args.output.open('x',encoding='utf-8') as f:json.dump(req,f,ensure_ascii=False,indent=2)
    print('READY:',len(req['hinge_cuts']),'hinge plywood cuts;',len(req['groups']),'stage groups;',len(req['operations']),'required operations complete')
