"""ROC-24: bounded deterministic candidate filters and an explicit benchmark.

Profiles are supplied source-bound capability claims, never assembly approval.
No corpus or historical success labels are invented by this module.
"""
import math
import re


def _number(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=100000:raise ValueError('Positive finite millimetres required')
    return float(value)


def _equipment(value):
    if not isinstance(value,list) or len(value)>50 or any(not isinstance(v,str) or not v or len(v)>100 for v in value) or len(set(value))!=len(value):raise ValueError('Unique bounded equipment names required')
    return set(value)


def recommend_case_families(query,families):
    if not isinstance(query,dict) or set(query)!={'dimensions_mm','device_count','equipment'}:raise ValueError('Exact query fields required')
    dims=query['dimensions_mm']
    if not isinstance(dims,list) or len(dims)!=3:raise ValueError('Explicit X/Y/Z device dimensions required')
    dims=[_number(v) for v in dims];count=query['device_count']
    if type(count) is not int or not 1<=count<=30:raise ValueError('Device count 1..30 required')
    equipment=_equipment(query['equipment'])
    if not isinstance(families,list) or len(families)>200:raise ValueError('At most 200 family profiles')
    ids=set();accepted=[];rejected=[]
    for family in families:
        fields={'id','name','device_ranges_mm','count_range','equipment','reference_device_mm','reference_count','source_revision','limitations'}
        if not isinstance(family,dict) or set(family)!=fields:raise ValueError('Exact family profile fields required')
        identity=family['id']
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',identity) or identity in ids:raise ValueError('Unique stable family ID required')
        ids.add(identity)
        if not isinstance(family['name'],str) or not family['name'] or len(family['name'])>200:raise ValueError('Family name required')
        source=family['source_revision']
        if (not isinstance(source,dict) or set(source)!={'project_id','revision_id','sha256'} or
            any(not isinstance(source[k],str) or not source[k] or len(source[k])>160 for k in source) or
            not re.fullmatch('[0-9a-f]{64}',source['sha256'])):raise ValueError('Source project revision and SHA required')
        limits=family['limitations']
        if not isinstance(limits,list) or len(limits)>30 or any(not isinstance(v,str) or not v or len(v)>500 for v in limits):raise ValueError('Explicit family limitations required')
        ranges=family['device_ranges_mm'];reference=family['reference_device_mm']
        if not isinstance(ranges,list) or len(ranges)!=3 or not isinstance(reference,list) or len(reference)!=3:raise ValueError('Three device ranges and reference dimensions required')
        for i,pair in enumerate(ranges):
            if not isinstance(pair,list) or len(pair)!=2 or _number(pair[0])>_number(pair[1]):raise ValueError('Invalid family dimension range')
            if not pair[0]<=_number(reference[i])<=pair[1]:raise ValueError('Reference outside family capability range')
        counts=family['count_range'];refcount=family['reference_count']
        if (not isinstance(counts,list) or len(counts)!=2 or any(type(v) is not int for v in counts) or
            not 1<=counts[0]<=counts[1]<=30 or type(refcount) is not int or not counts[0]<=refcount<=counts[1]):raise ValueError('Invalid family count range')
        available=_equipment(family['equipment']);reasons=[]
        for axis,dim,bounds in zip('XYZ',dims,ranges):
            if not bounds[0]<=dim<=bounds[1]:reasons.append(f'{axis}: {dim:g} mm poza zakresem {bounds[0]:g}..{bounds[1]:g} mm')
        if not counts[0]<=count<=counts[1]:reasons.append('Liczba urządzeń poza zakresem rodziny')
        missing=sorted(equipment-available)
        if missing:reasons.append('Brak obsługi wyposażenia: '+', '.join(missing))
        if reasons:
            rejected.append(dict(family_id=identity,reasons=reasons));continue
        dimensional=sum(abs(d-r)/r for d,r in zip(dims,reference))/3
        count_distance=abs(count-refcount)/refcount
        accepted.append(dict(family_id=identity,name=family['name'],score=dimensional+count_distance,
            score_components=dict(mean_relative_dimension_distance=dimensional,relative_count_distance=count_distance),
            reasons=['Wymiary XYZ w zadeklarowanym zakresie','Liczba urządzeń w zakresie','Wyposażenie obsługiwane'],
            limitations=list(limits),source_revision=dict(source),assembly_approved=False))
    accepted.sort(key=lambda r:(r['score'],r['family_id']))
    return dict(status='candidates' if accepted else 'manual_design_required',candidates=accepted,rejected=rejected,
        score_rule='mean relative XYZ distance + relative device count distance; lower is closer',
        dimensions_unit='mm',axis_order='XYZ',automatic_selection=False,production_approved=False)


def benchmark_case_recommendations(families,cases):
    if not isinstance(cases,list) or not 1<=len(cases)<=500:raise ValueError('A nonempty closed labeled benchmark is required')
    ids=set();rows=[]
    for case in cases:
        if not isinstance(case,dict) or set(case)!={'id','query','expected_family_id','source_sha256'}:raise ValueError('Exact benchmark cases required')
        if not isinstance(case['id'],str) or not case['id'] or case['id'] in ids:raise ValueError('Unique benchmark case ID required')
        ids.add(case['id'])
        if not re.fullmatch('[0-9a-f]{64}',case['source_sha256']):raise ValueError('Benchmark source checksum required')
        expected=case['expected_family_id']
        if expected is not None and expected not in {f['id'] for f in families}:raise ValueError('Expected family is absent from benchmark corpus')
        result=recommend_case_families(case['query'],families)
        actual=result['candidates'][0]['family_id'] if result['candidates'] else None
        rows.append(dict(case_id=case['id'],expected_family_id=expected,actual_family_id=actual,passed=actual==expected))
    correct=sum(r['passed'] for r in rows)
    return dict(cases=rows,count=len(rows),correct=correct,top1_accuracy=correct/len(rows),
        labeling_is_caller_supplied=True,production_approved=False)
