"""Shared presentation contract; family identity remains separate from stage identity."""
import hashlib
import json
import re

VERSION = 1
STAGES = (
    dict(id='plywood', order=1, label='Sklejka', color='#408080', background='#d3e9e5'),
    dict(id='profiles', order=2, label='Profile aluminiowe', color='#458bc1', background='#d9eafa'),
    dict(id='corners', order=3, label='Narożniki i wzmocnienia', color='#a47c36', background='#f4e8ce'),
    dict(id='closures', order=4, label='Zamki i zawiasy', color='#9465b6', background='#e8def4'),
    dict(id='handles', order=5, label='Uchwyty', color='#cf6578', background='#f5dfe6'),
    dict(id='wheels', order=6, label='Koła i gniazda do piętrowania', color='#637595', background='#dfe4ed'),
)
FAMILIES = {
    'panels': 'plywood', 'profiles': 'profiles', 'corners': 'corners',
    'braces': 'corners', 'latches': 'closures', 'hinges': 'closures',
    'handles': 'handles', 'wheels': 'wheels', 'stacking_sockets': 'wheels',
    'wheel_pads': 'wheels',
}
ALIASES = {'plate':'panels', 'plates':'panels','panel':'panels','plywood':'panels',
           'profile':'profiles','corner':'corners','brace':'braces','hinge':'hinges',
           'hinge_lid':'hinges','hinge_base':'hinges','latch':'latches','lock':'latches',
           'handle':'handles','wheel':'wheels','caster':'wheels','sockets':'stacking_sockets',
           'socket':'stacking_sockets','pad':'wheel_pads','wheelpad':'wheel_pads','wheelpads':'wheel_pads'}

def family_id(value):
    value=str(value or '').lower()
    if value in FAMILIES:return value
    if value in ALIASES:return ALIASES[value]
    # Explicit legacy occurrence prefixes, never arbitrary substring matching.
    prefix=re.split(r'[/ -]',value)[0]
    return prefix if prefix in FAMILIES else ALIASES.get(prefix)

def metadata(family):
    family=family_id(family)
    if family is None:raise ValueError('Unknown part family')
    return dict(family_id=family,stage_id=FAMILIES[family],registry_version=VERSION)

def stage_for(family):
    family=family_id(family)
    return FAMILIES.get(family,'other')

def contract():
    data=dict(version=VERSION,stages=[dict(s) for s in STAGES],families=dict(FAMILIES))
    data['sha256']=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return data

def legacy_export_family(name):
    """Migration for names emitted by the pinned RockPro prototype, not general CAD."""
    name=re.sub(r'[^a-z0-9]', '', name.lower())
    for prefix,family in [('rockprosocket','stacking_sockets'),('rockprowheel','wheels'),
        ('rockpropad','wheel_pads'),('rockproeg0113','profiles'),('rockproeg0500','profiles'),
        ('rockproh7159','handles'),('rockprohinge','hinges'),('rockprob1121','braces'),
        ('rockprob1930','braces'),('rockprobase','panels'),('rockprolid','panels'),
        ('rockprodno','panels'),('rockprowieko','panels')]:
        if name.startswith(prefix):return family
    if name in ('17251s','17251s1'):return 'latches'
    if name=='410429':return 'corners'
    raise ValueError('Unmapped legacy export root: '+name)
