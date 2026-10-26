"""T2 family draft: source hierarchy is not the mechanical movement hierarchy.

No CAD operations, inferred manufacturing approvals, or T1 lid assumptions.
Joint frames/clearances may remain unknown in this non-executable draft.
"""
import copy
import re

from .contracts import ValidationError, validate_wall_frame

FAMILY = 'trolley_mixer_removable_hood_rack'
ROLES = ('base', 'hood', 'front_cap', 'rack')
JOINTS = {'base_hood': ('base', 'hood', 4),
          'hood_front_cap': ('hood', 'front_cap', 2)}


def fail(code, path, message):
    raise ValidationError(code, path, message)


def exact(value, fields, path):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail('T2_FIELDS', path, 'Missing or unknown contract fields')


def positive_id(value, path):
    if type(value) is not int or value < 1:
        fail('T2_SOURCE_ID', path, 'Expected a positive native node ID')


def validate_t2_family(value):
    exact(value, ('schema_version', 'family_id', 'source_sha256', 'state',
                 'components', 'joints', 'device_fit_confirmed'), '$')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        fail('T2_SCHEMA', '$.schema_version', 'Only version 1 is supported')
    if value['family_id'] != FAMILY or value['state'] != 'reference_draft':
        fail('T2_DRAFT_ONLY', '$', 'This contract does not authorize a CAD build')
    if value['device_fit_confirmed'] is not False:
        fail('T2_FIT_UNCONFIRMED', '$.device_fit_confirmed', 'Device fit remains unconfirmed')
    if not isinstance(value['source_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['source_sha256']):
        fail('T2_SOURCE_HASH', '$.source_sha256', 'Exact source revision is required')
    exact(value['components'], ROLES, '$.components')
    seen = set()
    for role, component in value['components'].items():
        path = '$.components.' + role
        exact(component, ('source_node_id', 'cad_path', 'motion', 'frame'), path)
        node = component['source_node_id']; positive_id(node, path + '.source_node_id')
        if node in seen:
            fail('T2_DUPLICATE_ROLE', path, 'One source occurrence cannot represent two components')
        seen.add(node)
        cad_path = component['cad_path']
        if not isinstance(cad_path, list) or not cad_path or len(cad_path) > 12:
            fail('T2_SOURCE_PATH', path, 'Bounded explicit CAD path required')
        for index, item in enumerate(cad_path):
            positive_id(item, path + f'.cad_path[{index}]')
        if cad_path[-1] != node or len(set(cad_path)) != len(cad_path):
            fail('T2_SOURCE_PATH', path, 'Path must end at its occurrence without cycles')
        expected_motion = 'fixed' if role == 'base' else 'independent_removable'
        if component['motion'] != expected_motion:
            fail('T2_MOTION', path + '.motion', 'Do not derive movement from CAD parentage or a T1 hinge')
        if component['frame'] is not None:
            validate_wall_frame(component['frame'], path=path + '.frame')
    exact(value['joints'], JOINTS, '$.joints')
    used_halves = set()
    for key, (a, b, count) in JOINTS.items():
        joint = value['joints'][key]; path = '$.joints.' + key
        exact(joint, ('members', 'kind', 'frame', 'clearance_mm', 'latch_pairs'), path)
        if joint['members'] != [a, b] or joint['kind'] != 'removable':
            fail('T2_JOINT', path, 'Two removable closure interfaces are required')
        if joint['frame'] is not None:
            validate_wall_frame(joint['frame'], path=path + '.frame')
        clearance = joint['clearance_mm']
        if clearance is not None:
            import math
            if type(clearance) not in (int, float) or not math.isfinite(clearance) or not 0 <= clearance <= 20:
                fail('T2_CLEARANCE', path + '.clearance_mm', 'Explicit finite mm clearance or null required')
        pairs = joint['latch_pairs']
        if not isinstance(pairs, list) or len(pairs) != count:
            fail('T2_LATCH_COUNT', path, 'Reference requires four base pairs and two cap pairs')
        for index, pair in enumerate(pairs):
            exact(pair, (a, b), path + f'.latch_pairs[{index}]')
            for half in pair.values():
                positive_id(half, path)
                if half in used_halves or half in seen:
                    fail('T2_LATCH_ID', path, 'Latch halves must be distinct and cannot be component roots')
                used_halves.add(half)
    return copy.deepcopy(value)


def blockers(value):
    value = validate_t2_family(value)
    result = ['device_fit_unconfirmed', 'native_recipe_not_implemented',
              'catalog_aliases_and_material_conflicts_unresolved']
    for role, component in value['components'].items():
        if component['frame'] is None:
            result.append('component_frame_missing:' + role)
    for key, joint in value['joints'].items():
        if joint['frame'] is None:
            result.append('joint_frame_missing:' + key)
        if joint['clearance_mm'] is None:
            result.append('joint_clearance_missing:' + key)
    return result


def draft_from_reference(reference):
    """Import only reviewed semantic roots; never guess by hardware names."""
    if (reference.get('schema') != 'rockpro.reference-analysis/1'
            or reference.get('state') != 'inventory_draft'
            or reference.get('family_candidate') != FAMILY
            or reference.get('executable_template') is not False
            or reference.get('production_approved') is not False):
        fail('T2_REFERENCE', '$', 'Expected a non-executable reviewed T2 reference map')
    components = {}
    roles = {'base': 'structural_base', 'hood': 'removable_hood',
             'front_cap': 'removable_front_cap', 'rack': 'removable_rack'}
    for role, source_role in roles.items():
        candidates = [p for p in reference['parts'] if p['role'] == source_role
                      and p['source_type'] == 'Z_ELEMENT_ASSEMBLY']
        roots = [p for p in candidates if not any(
            p['source_path'].startswith(other['source_path'] + '/')
            for other in candidates if other is not p)]
        if len(roots) != 1:
            fail('T2_ROLE_AMBIGUOUS', '$.components.' + role, 'Exactly one reviewed source root required')
        root = roots[0]
        if not re.fullmatch(r'root(?:/[1-9][0-9]*)+', root['source_path']):
            fail('T2_SOURCE_PATH', '$.components.' + role, 'Expected native-ID source path')
        components[role] = dict(source_node_id=root['source_id'],
            cad_path=[int(i) for i in root['source_path'].split('/')[1:]], frame=None,
            motion='fixed' if role == 'base' else 'independent_removable')
    joints = {key: dict(members=[a, b], kind='removable', frame=None,
                       clearance_mm=None, latch_pairs=[]) for key, (a, b, _) in JOINTS.items()}
    for pair in reference['latch_pairs']:
        owners = {pair['upper_owner'], pair['lower_owner']}
        matches = [key for key, (a, b, _) in JOINTS.items() if owners == {a, b}]
        if len(matches) != 1:
            fail('T2_LATCH_OWNER', '$.joints', 'Unrecognized source closure pairing')
        joints[matches[0]]['latch_pairs'].append({pair['upper_owner']: pair['upper_source_id'],
                                               pair['lower_owner']: pair['lower_source_id']})
    return validate_t2_family(dict(schema_version=1, family_id=FAMILY,
        source_sha256=reference['source_sha256'], state='reference_draft',
        components=components, joints=joints, device_fit_confirmed=False))
