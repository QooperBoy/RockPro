"""Neutral guillotine contract and independent checker; no machine postprocessor.

Coordinates are millimetres in each trimmed sheet. A cut partitions one entire
remaining rectangle and removes kerf; children are checked from the root down.
The reference first-fit solver proves feasibility, never optimality.
"""
from collections import Counter
import copy
import csv
from datetime import date
import io
import time

from material_service import digest, positive, token

TOLERANCE=1e-6


def validate_inputs(demand, sheets, technology):
    if not isinstance(demand,dict) or demand.get('demand_sha256')!=digest({k:v for k,v in demand.items() if k!='demand_sha256'}):
        raise ValueError('DEMAND_INTEGRITY_FAILED')
    if not demand.get('groups') or sum(g['quantity'] for g in demand['groups'])>2000:
        raise ValueError('Reference cutting limit: 1..2000 parts')
    if (not isinstance(technology,dict) or set(technology)!={'id','profile_revision','kerf_mm','trim_mm','cut_type'} or
        technology['cut_type']!='guillotine'):
        raise ValueError('Explicit guillotine technology profile required')
    for k in ('id','profile_revision'):token(technology[k],k)
    positive(technology['kerf_mm'],'kerf',30)
    trims=technology['trim_mm']
    if not isinstance(trims,list) or len(trims)!=4:raise ValueError('Four explicit edge trims required')
    for n in trims:
        if type(n) not in (int,float) or not 0<=n<=1000:raise ValueError('Invalid trim')
    if not isinstance(sheets,list) or not 1<=len(sheets)<=500:raise ValueError('Explicit sheet inventory required')
    ids=set()
    for s in sheets:
        if not isinstance(s,dict) or set(s)!={'id','material_id','finish','technology_id','thickness_mm','length_mm','width_mm','grain_axis','available_date'}:
            raise ValueError('Exact sheet fields required')
        for k in ('id','material_id','finish','technology_id'):token(s[k],k)
        if s['id'] in ids:raise ValueError('Duplicate physical sheet ID')
        ids.add(s['id'])
        for k in ('thickness_mm','length_mm','width_mm'):positive(s[k],k,10000)
        if s['grain_axis'] not in ('X','Y','free'):raise ValueError('Explicit sheet grain required')
        if date.fromisoformat(s['available_date']).isoformat()!=s['available_date']:raise ValueError('ISO sheet availability required')
        if s['length_mm']<=trims[0]+trims[1] or s['width_mm']<=trims[2]+trims[3]:raise ValueError('Trims consume sheet')
    return digest(dict(demand_sha256=demand['demand_sha256'],sheets=sheets,technology=technology))


def compatible(group, sheet, technology, rotated):
    if any(group[k]!=sheet[k] for k in ('material_id','finish','technology_id','thickness_mm')):return False
    if group['technology_id']!=technology['id'] or sheet['available_date']>group['required_date']:return False
    if rotated and not group['rotation_allowed']:return False
    grain=group['grain_axis']
    if grain!='free' and rotated:grain={'X':'Y','Y':'X'}[grain]
    return grain=='free' or grain==sheet['grain_axis']


def verify_cut_plan(demand, sheets, technology, plan):
    binding=validate_inputs(demand,sheets,technology)
    if not isinstance(plan,dict) or set(plan)!={'input_sha256','sheets'} or plan['input_sha256']!=binding:
        raise ValueError('CUT_PLAN_INPUT_MISMATCH')
    if not isinstance(plan['sheets'],list) or len(plan['sheets'])>len(sheets):raise ValueError('Invalid plan sheets')
    stock={s['id']:s for s in sheets};used=set();counts=Counter();placements=[];cuts=[];waste=0;nodes=0
    trims=technology['trim_mm'];kerf=technology['kerf_mm']

    def walk(node,x,y,w,h,sheet,depth):
        nonlocal waste,nodes
        nodes+=1
        if depth>128 or nodes>20000 or not isinstance(node,dict):raise ValueError('Cut tree limit exceeded')
        kind=node.get('type')
        if kind=='waste' and set(node)=={'type'}:
            waste+=w*h;return
        if kind=='part' and set(node)=={'type','group_index','rotated'}:
            index=node['group_index'];rotated=node['rotated']
            if type(index) is not int or not 0<=index<len(demand['groups']) or type(rotated) is not bool:raise ValueError('Invalid part reference')
            group=demand['groups'][index]
            if not compatible(group,sheet,technology,rotated):raise ValueError('Material/grain/rotation/date mismatch')
            size=[group['cut_length_mm'],group['cut_width_mm']]
            if rotated:size.reverse()
            if abs(size[0]-w)>TOLERANCE or abs(size[1]-h)>TOLERANCE:raise ValueError('Part leaf does not match technology cutting dimensions')
            counts[index]+=1
            placements.append(dict(sheet_id=sheet['id'],group_index=index,x_mm=x,y_mm=y,length_mm=w,width_mm=h,rotated=rotated,sources=group['sources']))
            return
        if kind!='cut' or set(node)!={'type','axis','at_mm','first','second'} or node['axis'] not in ('X','Y'):
            raise ValueError('Invalid guillotine cut node')
        at=node['at_mm'];span=w if node['axis']=='X' else h
        if type(at) not in (int,float) or not 0<at<span-kerf:raise ValueError('Cut leaves no material after kerf')
        cuts.append(dict(sheet_id=sheet['id'],axis=node['axis'],at_mm=(x if node['axis']=='X' else y)+at,origin_mm=[x,y],region_mm=[w,h]))
        if node['axis']=='X':
            walk(node['first'],x,y,at,h,sheet,depth+1);walk(node['second'],x+at+kerf,y,w-at-kerf,h,sheet,depth+1)
        else:
            walk(node['first'],x,y,w,at,sheet,depth+1);walk(node['second'],x,y+at+kerf,w,h-at-kerf,sheet,depth+1)

    for entry in plan['sheets']:
        if not isinstance(entry,dict) or set(entry)!={'sheet_id','tree'}:raise ValueError('Invalid plan sheet entry')
        ident=entry['sheet_id']
        if ident not in stock or ident in used:raise ValueError('Unknown or repeated physical sheet')
        used.add(ident);s=stock[ident]
        walk(entry['tree'],trims[0],trims[2],s['length_mm']-trims[0]-trims[1],s['width_mm']-trims[2]-trims[3],s,0)
    if counts!=Counter({i:g['quantity'] for i,g in enumerate(demand['groups'])}):raise ValueError('Required part quantities not met exactly')
    return dict(valid=True,input_sha256=binding,plan_sha256=digest(plan),placements=placements,
                cut_sequence=cuts,remaining_area_mm2=waste,optimality='not_proven',
                machine_profile_verified=False,production_approved=False)


def solve_reference(demand,sheets,technology,max_seconds=5,clock=time.monotonic):
    binding=validate_inputs(demand,sheets,technology)
    positive(max_seconds,'max seconds',30);deadline=clock()+max_seconds
    plan=dict(input_sha256=binding,sheets=[]);free=[]
    t=technology['trim_mm'];kerf=technology['kerf_mm']
    for s in sheets:
        tree={'type':'waste'};plan['sheets'].append(dict(sheet_id=s['id'],tree=tree))
        free.append((tree,s,s['length_mm']-t[0]-t[1],s['width_mm']-t[2]-t[3],0))
    parts=[i for i,g in enumerate(demand['groups']) for _ in range(g['quantity'])]
    parts.sort(key=lambda i:-(demand['groups'][i]['cut_length_mm']*demand['groups'][i]['cut_width_mm']))
    for index in parts:
        if clock()>=deadline:return dict(status='timeout',plan=None,last_verified_plan=None,optimality='not_proven')
        g=demand['groups'][index];found=None
        for position,(node,s,w,h,depth) in enumerate(free):
            if depth>124:continue
            for rotated in (False,True):
                if not compatible(g,s,technology,rotated):continue
                a,b=(g['cut_width_mm'],g['cut_length_mm']) if rotated else (g['cut_length_mm'],g['cut_width_mm'])
                # A positive remainder narrower than kerf cannot be represented
                # as another material leaf. Refuse rather than hide the loss.
                if ((abs(w-a)<=TOLERANCE or w-a>kerf) and (abs(h-b)<=TOLERANCE or h-b>kerf)):
                    found=(position,rotated,a,b);break
            if found:break
        if found is None:return dict(status='no_result',plan=None,last_verified_plan=None,optimality='not_proven')
        position,rotated,a,b=found;node,s,w,h,depth=free.pop(position)
        part={'type':'part','group_index':index,'rotated':rotated};inner=part
        if h-b>TOLERANCE:
            rest={'type':'waste'};inner=dict(type='cut',axis='Y',at_mm=b,first=part,second=rest)
            free.append((rest,s,a,h-b-kerf,depth+2))
        if w-a>TOLERANCE:
            rest={'type':'waste'};inner=dict(type='cut',axis='X',at_mm=a,first=inner,second=rest)
            free.append((rest,s,w-a-kerf,h,depth+1))
        node.clear();node.update(inner)
    plan['sheets']=[e for e in plan['sheets'] if e['tree']['type']!='waste']
    verification=verify_cut_plan(demand,sheets,technology,plan)
    return dict(status='feasible',plan=plan,verification=verification,optimality='not_proven')


def export_neutral_csv(demand):
    """Column contract to map in a verified PLAN import profile, not a postprocessor."""
    if demand.get('demand_sha256')!=digest({k:v for k,v in demand.items() if k!='demand_sha256'}):raise ValueError('Demand hash mismatch')
    stream=io.StringIO(newline='');writer=csv.writer(stream,delimiter=';')
    writer.writerow(['group','material_id','finish','thickness_mm','length_mm','width_mm','quantity','grain_axis','rotation_allowed','required_date'])
    for i,g in enumerate(demand['groups']):writer.writerow([i,*[g[k] for k in ('material_id','finish','thickness_mm','cut_length_mm','cut_width_mm','quantity','grain_axis','rotation_allowed','required_date')]])
    return dict(format='rockpro-neutral-csv-v1',text=stream.getvalue(),demand_sha256=demand['demand_sha256'],
                profile_mapping_required=True,machine_ready=False)
