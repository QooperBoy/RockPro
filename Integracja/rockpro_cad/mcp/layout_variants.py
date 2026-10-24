"""ROC-25: up to three allowed layouts with conservative vertical-removal checks."""
import itertools
import math
import hashlib
import json
import copy
from layout import _calculate_layout
from device_catalog import preview_device_record


def _overlap(a,b):
    return all(min(p+d,q+e)-max(p,q)>1e-6 for p,d,q,e in zip(a['pos'],a['size'],b['pos'],b['size']))


def _removal_check(result,clearance):
    """Independent removal upward through a fully open rectangular lid aperture."""
    boxes=result['boxes'];inside=result['internal'];failures=[]
    for i,device in enumerate(boxes):
        if device['kind']!='device':continue
        p=device['pos'];d=device['size']
        sweep=dict(pos=[p[0]-clearance,p[1]-clearance,p[2]],
                   size=[d[0]+2*clearance,d[1]+2*clearance,inside[2]-p[2]])
        if any(sweep['pos'][j]<-1e-6 or sweep['pos'][j]+sweep['size'][j]>inside[j]+1e-6 for j in (0,1)):
            failures.append(device['label']+': brak luzu chwytu w otworze pokrywy')
        for j,other in enumerate(boxes):
            if j!=i and _overlap(sweep,other):failures.append(device['label']+': tor wyjęcia przecina '+other['label'])
    return dict(passed=not failures,failures=failures,
        scope='Independent +Z AABB removal through fully open/removable lid; no fitting intrusions, cables or articulated CAD collision proof')


def preview_device_layouts(record,spec,allowed_orientations,allowed_arrangements,removal_clearance_mm=0,max_external_mm=None):
    device=preview_device_record(record)
    orientations=set(map(''.join,itertools.permutations('XYZ')))
    if (not isinstance(allowed_orientations,list) or not allowed_orientations or len(allowed_orientations)>6 or
        len(set(allowed_orientations))!=len(allowed_orientations) or set(allowed_orientations)-orientations):raise ValueError('Explicit allowed orientations required')
    if (not isinstance(allowed_arrangements,list) or not allowed_arrangements or len(allowed_arrangements)>3 or
        len(set(allowed_arrangements))!=len(allowed_arrangements) or set(allowed_arrangements)-set('XYZ')):raise ValueError('Explicit allowed arrangements required')
    if type(removal_clearance_mm) not in (int,float) or not math.isfinite(removal_clearance_mm) or not 0<=removal_clearance_mm<=500:raise ValueError('Invalid removal clearance')
    if max_external_mm is not None and (not isinstance(max_external_mm,list) or len(max_external_mm)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 or x>10000 for x in max_external_mm)):raise ValueError('Invalid maximum external XYZ envelope')
    if not isinstance(spec,dict) or any(k in spec for k in ('x','y','z')):raise ValueError('Device dimensions come from the cited record; omit x/y/z in layout spec')
    blockers=[]
    if not device['dimensions_ready']:blockers.append('DEVICE_DIMENSIONS_UNCONFIRMED')
    values=[device['fields'][axis]['value'] for axis in 'XYZ']
    if any(v is None for v in values):
        return dict(status='blocked',variants=[],rejected=[],release_blockers=blockers+['DEVICE_DIMENSIONS_MISSING_OR_CONFLICTING'],production_approved=False)
    base=copy.deepcopy(spec)|dict(zip(('x','y','z'),values))
    variants=[];rejected=[];geometries=set()
    for orientation in allowed_orientations:
        for arrangement in allowed_arrangements:
            choice=dict(orientation=orientation,arrangement=arrangement)
            try:
                layout=_calculate_layout(base|choice)
                if max_external_mm is not None and any(v>limit+1e-6 for v,limit in zip(layout['external'],max_external_mm)):raise ValueError('Gabaryt przekracza dozwolone XYZ')
                removal=_removal_check(layout,removal_clearance_mm)
                if not removal['passed']:raise ValueError('; '.join(removal['failures']))
            except ValueError as exc:
                rejected.append(dict(**choice,reason=str(exc)));continue
            signature=json.dumps(dict(external=layout['external'],boxes=[{k:b[k] for k in ('kind','pos','size')} for b in layout['boxes']]),sort_keys=True)
            if signature in geometries:continue
            geometries.add(signature)
            ident=hashlib.sha256(json.dumps(dict(record_sha=device['record_sha256'],spec=layout['spec'],removal_clearance_mm=removal_clearance_mm),sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()
            variants.append(dict(id=ident,**choice,layout=layout,removal_check=removal,
                reasons=['Dozwolona orientacja i kierunek','Obrysy bez kolizji i wewnątrz skrzyni','Niezależne wyjęcie w +Z sprawdzone obrysami'],
                source_record_sha256=device['record_sha256'],source_catalog_id=device['catalog_id'],
                release_blockers=list(blockers),production_approved=False))
    variants.sort(key=lambda v:(round(v['layout']['volume_l'],9),v['orientation'],v['arrangement']))
    return dict(status='proposals' if variants else 'manual_design_required',variants=variants[:3],rejected=rejected,
        feasible_distinct_count=len(variants),release_blockers=blockers,
        constructor_can_edit_or_reject=True,automatic_save=False,production_approved=False)
