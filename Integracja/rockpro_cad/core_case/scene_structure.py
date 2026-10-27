"""Shared assembly stages and complete machining ownership for the T1 prototype.

Machining remains a feature of its plywood/profile, never a separate BOM part.
Presence of a profile interruption does not satisfy a required plywood opening.
"""
from ..part_registry import STAGES, metadata

STRUCTURE_VERSION = 1


def group_for_part(key):
    if '/brace-' in key:
        family = 'braces'
    elif key.startswith('support/'):
        family = 'wheel_pads'
    else:
        family = key.split('/')[0]
    stage_id = metadata(family)['stage_id']
    stage = next(s for s in STAGES if s['id'] == stage_id)
    return dict(id=stage_id, label=f"{stage['order']:02d}. {stage['label']}")


def required_t1_machining(parts):
    """Exact owner/target roles for current measured hardware, not guessed SKUs."""
    required = set()
    for key in parts:
        bits = key.split('/')
        if bits[0] == 'hinge':
            _, slot, half = bits
            required.add((key, 'plywood/' + half + '/rear'))
            required.add((key, 'profile/' + ('EG-0500_1' if half == 'base' else 'EG-0500_2') + '/rear'))
        elif bits[0] == 'latch':
            _, slot, half = bits
            required.add((key, 'plywood/' + half + '/front'))
            required.add((key, 'profile/' + ('EG-0500_1' if half == 'base' else 'EG-0500_2') + '/front'))
        elif bits[0] == 'handle':
            required.add((key, 'plywood/base/' + bits[1]))
        elif bits[0] == 'socket':
            required.add((key, 'plywood/lid/roof'))
    return required


def validate_t1_machining(parts, operations):
    known = set(parts)
    observed = set()
    keys = set()
    for op in operations:
        if op['key'] in keys:
            raise ValueError('Powtórzone ID obróbki: ' + op['key'])
        keys.add(op['key'])
        owner, target = op['owner'], op['target']
        if owner not in known or target not in known:
            raise ValueError('Obróbka bez istniejącego okucia lub części docelowej')
        if group_for_part(owner)['id'] not in ('handles', 'closures', 'wheels'):
            raise ValueError('Niepotwierdzona rodzina obróbki')
        if not target.startswith(('plywood/', 'profile/')):
            raise ValueError('Nie wolno wycinać geometrii katalogowego okucia')
        observed.add((owner, target))
    missing = required_t1_machining(parts) - observed
    if missing:
        raise ValueError('BRAK_WYMAGANYCH_WYCIEC: ' + repr(sorted(missing)))
    return True


def rebase_scene_expression(text, names, extra_levels=1):
    """Add ancestors only to scene parameter references, preserving local names."""
    import re
    pattern = r'(?P<parents>(?:Parent\\)+)Params\\(?P<name>' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r')\b'
    return re.sub(pattern, lambda m: 'Parent\\' * extra_levels + m[0], text)
