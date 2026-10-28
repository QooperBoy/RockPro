"""Actionable concept checks from the shared planner. Never CAD approval."""
import math
from . import configurator, studio_parts

ERROR_CODES={'overlap','edge_clearance','hinge_mount_space','closure_no_space',
             'closure_handle_overlap','closure_mount_space','missing_wall','missing_joint'}
INFO_CODES={'closure_reference','joint_mount_pending','unbound_joint'}
STEP_NAMES={1:'Typ konstrukcji',2:'Wieka i współpraca',3:'Wymiary sekcji',4:'Części i okucia',
            5:'Uchwyty i ścianki',6:'Zatrzaski i zawiasy',7:'Konstrukcja i podstawa'}


def _invalid_step(d):
    if not isinstance(d,dict) or d.get('schema')!='rockpro.configurator/3' or not isinstance(d.get('type'),str) or d['type'] not in configurator.TYPES or not d.get('name'):return 1
    def number(v,lo,hi):return type(v) in (int,float) and math.isfinite(v) and lo<=v<=hi
    dims=d.get('internal_mm')
    if not isinstance(dims,list) or len(dims)!=3 or not all(number(x,50,10000) for x in dims) or not number(d.get('thickness_mm'),3,30):return 3
    covers=d.get('covers')
    if not isinstance(covers,list) or len(covers)!=len(configurator.TYPES[d['type']]['covers']):return 2
    for c in covers:
        if not isinstance(c,dict):return 2
        if not number(c.get('depth_mm'),2*d['thickness_mm'],3000):return 3
        if d['type']=='case' and c.get('face')=='top' and c.get('kind')=='hinged' and c['depth_mm']>.15*dims[2] and not c.get('height_override'):return 3
    try:studio_parts.resolve(d.get('hardware',[]))
    except (ValueError,TypeError,KeyError):return 4
    if isinstance(d.get('construction'),dict) and d['construction'].get('enabled') and d['type']=='case' and covers[0].get('depth_mm',0)<110:return 3
    return 6 if d.get('placements') else 7


def review(value):
    issues=[]
    def add(code,message,step,severity='warning',**target):
        issues.append(dict(id='review-'+str(len(issues)+1),code=code,message=message,step=step,severity=severity,**target))
    try:
        model=configurator.preview(value)
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError) as exc:
        step=_invalid_step(value)
        add('invalid_data',str(exc)[:500],step,'error')
        add('geometry_not_checked','Kontrola obrysów czeka na poprawienie danych projektu.',step,'info')
        return _report(issues,False)
    d=model['draft'];definitions={r['id']:r for r in studio_parts.resolve(d['hardware'])}
    groups={g['id']:g for g in d.get('placements',[])};families={key:r['family_id'] for key,r in definitions.items()}
    for warning in model['placement']['warnings']:
        code=warning['code']
        if code in INFO_CODES:continue
        group=groups.get(warning.get('group_id'),{})
        # Legacy wall-mounted latches/joint rows still belong to the wall editor.
        step=6 if group.get('pattern')=='closure_line' else 5
        target={k:warning[k] for k in ('group_id','other_group_id','occurrence_id') if k in warning}
        if group:target['part_id']=group['part_id']
        add(code,warning['message'],step,'error' if code in ERROR_CODES else 'warning',**target)
    if not definitions:add('missing_parts','Nie wybrano żadnych części z biblioteki.',4)
    for message in model['hardware_summary']['warnings']:add('selection_inconsistency',message,4)
    for key in model['project_summary']['unplaced_selection']:
        family=families[key];step=6 if family in ('hinges','latches') else 5 if family=='handles' else 7
        add('part_not_placed',key+': część wybrana, lecz nierozmieszczona w projekcie.',step,part_id=key)
    handles=[r for r in model['placement']['items'] if families.get(r['part_id'])=='handles']
    if not handles:add('missing_handles','Brak rozmieszczonych uchwytów do przenoszenia.',5)
    elif not any({a,b}.issubset({r['face'] for r in handles}) for a,b in [('left','right'),('front','rear')]):
        add('handles_one_side','Uchwyty nie tworzą zestawu na przeciwległych ścianach. Sprawdź sposób podnoszenia.',5,group_id=handles[0]['group_id'])
    seam_cover={r['id']:r['cover_id'] for r in model['placement']['closure_lines']}
    resolved={r['group_id'] for r in model['placement']['items']}
    for cover in d['covers']:
        bound=[g for g in groups.values() if g['id'] in resolved and (seam_cover.get(g.get('seam_id'))==cover['id'] or g.get('joint_id')=='joint-'+cover['id'])]
        if cover['kind']=='hinged' and not any(families[g['part_id']]=='hinges' for g in bound):
            add('missing_hinge',cover['label']+': brak zawiasów przypisanych do złącza.',6,section_id=cover['id'])
        if not any(families[g['part_id']]=='latches' for g in bound):
            add('missing_latch',cover['label']+': brak zatrzasków przypisanych do złącza.',6,section_id=cover['id'])
    if not d.get('construction',{}).get('enabled'):
        if d['type']=='case':add('missing_construction','Nie dodano zestawu profili, narożników i wzmocnień.',7)
        else:add('construction_not_supported','Automatyczne profile i wzmocnienia tego typu nie są jeszcze obsługiwane. Wymagają opracowania konstrukcyjnego.',7)
    add('native_check_pending','Wycięcia, pasowanie profili i rzeczywista przestrzeń ruchu wymagają sprawdzenia w IronCAD.',7,'info')
    report=_report(issues,True)
    report['part_count']=model['project_summary']['total_count']
    return report


def _report(issues,valid):
    counts={severity:sum(i['severity']==severity for i in issues) for severity in ('error','warning','info')}
    return dict(schema='rockpro.studio-review/1',issues=issues,counts=counts,data_valid=valid,
                status='errors' if counts['error'] else 'needs_attention' if counts['warning'] else 'concept_checks_passed',
                steps=[dict(step=n,label=label,status='blocked' if any(i['step']==n and i['severity']=='error' for i in issues) else
                            'attention' if any(i['step']==n and i['severity']=='warning' for i in issues) else 'checked' if valid else 'pending')
                       for n,label in STEP_NAMES.items()],
                collision_scope='known_2d_envelopes_same_wall',production_approved=False)
