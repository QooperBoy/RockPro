"""Deterministic offline case planner for the explicitly synthetic v1 recipe.

The output is a proposal, never CAD execution or production approval. The module
reads only its request; catalog definitions, formulas and approvals are inert JSON.
"""
import copy
import hashlib
import itertools
import json
from .contracts import ValidationError, validate_request
from .expressions import Interpreter, OPS, SELECTORS, bounded_json, fail, finite

TOL = 1e-6
RULE_PACK = 'synthetic-roc43-rules-v1'
GROUP_FIELDS = {'symmetry_group_id', 'family', 'mode', 'datum', 'axes', 'scope',
                'exception_approval', 'centers', 'definition', 'slots', 'rotation',
                'shape', 'count_override'}
GROUP_METADATA = ('family', 'mode', 'datum', 'axes', 'scope', 'exception_approval')


def require(condition, code, message, path='$.template_recipe'):
    if not condition:
        fail(code, message, path)


def obj(value, allowed, required=None):
    require(isinstance(value, dict), 'RECIPE_INVALID', 'Expected a JSON object')
    require(set(value) <= set(allowed) and (set(required or ()) <= set(value)),
            'RECIPE_INVALID', 'Unknown or missing recipe fields')
    return value


def vector(value, positive=False):
    require(isinstance(value, list) and len(value) == 3, 'RECIPE_INVALID_NUMBER', 'Expected a 3D vector')
    for n in value:
        finite(n)
        if positive:
            require(n > 0, 'RECIPE_INVALID_NUMBER', 'Geometry dimensions must be positive')
    return value


def near(a, b):
    if type(b) in (int, float):
        return type(a) in (int, float) and abs(a-b) <= TOL
    if isinstance(b, list):
        return isinstance(a, list) and len(a) == len(b) and all(near(x, y) for x, y in zip(a, b))
    if isinstance(b, dict):
        return isinstance(a, dict) and set(a) == set(b) and all(near(a[k], b[k]) for k in b)
    return type(a) is type(b) and a == b


def rotation(matrix):
    require(isinstance(matrix, list) and len(matrix) == 3, 'INVALID_RIGID_ROTATION', 'Expected a 3x3 rotation')
    for row in matrix:
        vector(row)
    for i in range(3):
        for j in range(3):
            require(near(sum(matrix[k][i]*matrix[k][j] for k in range(3)), int(i == j)),
                    'INVALID_RIGID_ROTATION', 'Rotation must be orthonormal')
    a, b, c = matrix
    det = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    require(near(det, 1), 'INVALID_RIGID_ROTATION', 'Reflections are forbidden')
    return matrix


def transformed(origin, matrix, point):
    return [finite(origin[i] + sum(matrix[i][j]*point[j] for j in range(3))) for i in range(3)]


def bounds(value):
    require(isinstance(value, list) and len(value) == 2, 'RECIPE_INVALID_NUMBER', 'Expected min/max local bounds')
    lo, hi = (vector(v) for v in value)
    require(all(a < b for a, b in zip(lo, hi)), 'RECIPE_INVALID_NUMBER', 'Bounds must have positive extents')
    return value


def unique(items, code, key=None):
    require(isinstance(items, list), code, 'Expected an explicit list')
    values = [item[key] if key else item for item in items]
    require(all(isinstance(v, str) and v for v in values) and len(set(values)) == len(values),
            code, 'Identifiers must be nonempty and unique')
    return values


def approval(recipe, token, group_id, parameters=()):
    require(token is not None, 'SYMMETRY_EXCEPTION_REQUIRED', 'Explicit scoped approval is required')
    approved = recipe['approvals'].get(token) if isinstance(token, str) else None
    require(isinstance(approved, dict) and group_id in approved.get('groups', [])
            and set(parameters) <= set(approved.get('parameters', [])),
            'SYMMETRY_EXCEPTION_UNAPPROVED', 'Approval does not cover this group and its parameters')


def _validate_recipe(recipe, manifest, interpreter):
    require(recipe.get('rule_pack_version') == RULE_PACK, 'RECIPE_VERSION_UNSUPPORTED', 'Unsupported rule pack')
    interpreter.group_ids = set(unique(recipe['groups'], 'SYMMETRY_GROUP_DUPLICATE', 'symmetry_group_id'))
    language = recipe['expression_language']
    require(type(language.get('version')) is int and language['version'] == 1,
            'RECIPE_VERSION_UNSUPPORTED', 'Unsupported expression language')
    require(set(language['op_allowlist']) == OPS and len(language['op_allowlist']) == len(OPS)
            and set(language['input_selector_allowlist']) == SELECTORS,
            'RECIPE_OPERATION_UNSUPPORTED', 'Language capabilities must match the closed runtime allowlist')
    require(language.get('no_code_execution') is True,
            'RECIPE_OPERATION_UNSUPPORTED', 'Recipe must be inert data')
    for matrix in recipe['rotations'].values():
        rotation(matrix)
    variable_policies = {'panel': 'two_dimensions_variable_thickness_fixed',
                         'profile': 'one_length_variable_section_fixed',
                         'device-envelope': 'already_oriented_envelope_from_layout',
                         'divider': 'planar_from_layout'}
    for name, definition in recipe['catalog'].items():
        policy = definition.get('geometry_policy')
        require(policy == variable_policies.get(name, 'rigid'),
                'GEOMETRY_POLICY_CONFLICT', 'Definition cannot change its geometry policy')
        if policy == 'rigid':
            obj(definition, {'shape', 'local_bounds', 'geometry_policy', 'mounting_point', 'synthetic_approved'},
                {'shape', 'local_bounds', 'geometry_policy', 'mounting_point', 'synthetic_approved'})
            vector(definition['shape'], positive=True)
            bounds(definition['local_bounds'])
            require(definition['synthetic_approved'] is True and definition['mounting_point'] == [0, 0, 0],
                    'GEOMETRY_POLICY_CONFLICT', 'This recipe supports only approved, origin-mounted rigid parts')
        else:
            obj(definition, {'geometry_policy', 'local_bounds_operation', 'section', 'rotation'},
                {'geometry_policy', 'local_bounds_operation'})
            require(definition['local_bounds_operation'] == 'centered_box_from_shape',
                    'GEOMETRY_POLICY_CONFLICT', 'Unsupported variable geometry bounds operation')
    names = set(interpreter.values)
    for entry in recipe['derived']:
        obj(entry, {'name', 'value'}, {'name', 'value'})
        name = entry['name']
        require(isinstance(name, str) and name and '.' not in name and name not in names,
                'RECIPE_REFERENCE_INVALID', 'Derived names must be unique and cannot shadow input')
        interpreter.validate(entry['value'], names)
        interpreter.values[name] = interpreter.evaluate(entry['value'])
        names.add(name)
    # Validate expressions in every branch, including inactive scenarios and unused catalog data.
    interpreter.validate({k: v for k, v in recipe.items() if k != 'derived'}, names)
    group_ids = unique(recipe['groups'], 'SYMMETRY_GROUP_DUPLICATE', 'symmetry_group_id')
    require(set(group_ids) == set(manifest['group_roles']), 'SYMMETRY_GROUP_MISSING', 'Recipe and manifest groups differ')
    require(type(recipe['group_count']) is int and recipe['group_count'] == len(group_ids),
            'INVENTORY_INCOMPLETE', 'Declared group count differs from recipe')
    require(set(g['family'] for g in recipe['groups']) == set(manifest['required_families']),
            'INVENTORY_INCOMPLETE', 'Recipe does not account for all manifest families')
    require(recipe['inventory'] == {'empty_assembly_ids': manifest['empty_assembly_ids'], 'unresolved_ids': []},
            'INVENTORY_UNRESOLVED', 'Recipe and manifest inventory differ')
    require(sum(len(g['slots']) for g in recipe['groups']) == recipe['physical_occurrence_count_default'],
            'INVENTORY_INCOMPLETE', 'Declared physical count differs from slots')
    for frame in recipe['frames'].values():
        obj(frame, {'origin', 'rotation'}, {'origin', 'rotation'})
        require(frame['rotation'] in recipe['rotations'], 'INVALID_RIGID_ROTATION', 'Unknown frame rotation')
    for g in recipe['groups']:
        obj(g, GROUP_FIELDS, GROUP_FIELDS - {'shape', 'count_override'})
        require(g['datum'] in recipe['frames'], 'ANCHOR_FRAME_MISMATCH', 'Unknown datum')
        require(g['definition'] in recipe['catalog'], 'INVENTORY_UNRESOLVED', 'Unknown catalog definition')
        require(isinstance(g['slots'], list) and 0 < len(g['slots']) <= 1000,
                'INVENTORY_INCOMPLETE', 'Group requires bounded slots')
        require(isinstance(g['axes'], list) and len(g['axes']) == len(set(g['axes']))
                and all(axis in ('0', '1', '2') for axis in g['axes']) and set(g['centers']) == set(g['axes']),
                'SYMMETRY_INVALID', 'Axes and local symmetry centers must agree')
        rotations = g['rotation'] if isinstance(g['rotation'], list) else [g['rotation']] * len(g['slots'])
        require(len(rotations) == len(g['slots']) and all(r in recipe['rotations'] for r in rotations),
                'INVALID_RIGID_ROTATION', 'Every slot requires a known proper rotation')
        if g['exception_approval'] is not None:
            approval(recipe, g['exception_approval'], g['symmetry_group_id'])
        if 'count_override' in g:
            require(g['count_override'] == 'scenario_contract.set_group_count'
                    and g['symmetry_group_id'] == recipe['scenario_contract']['set_group_count']['group_id'],
                    'RECIPE_SELECTOR_INVALID', 'Unknown count override selector')
    require(recipe['transport_envelope']['operation'] == 'union_transformed_local_bounds'
            and recipe['transport_envelope']['include_display_gap'] is False,
            'RECIPE_INVALID', 'Transport envelope must be the closed physical AABB union')


def _state(request):
    spec, recipe, scenario = (request[k] for k in ('spec', 'template_recipe', 'scenario'))
    binding = {k: spec[k] for k in ('case_id', 'revision', 'template_version')}
    binding['rule_pack_version'] = recipe['rule_pack_version']
    for name, value in (('spec_digest', spec), ('recipe_digest', recipe)):
        binding[name] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                  ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
    previous = scenario.get('previous')
    state = {'binding': binding, 'group_parameters': {}, 'manual_overrides': [], 'manual_additions': []}
    if previous is not None:
        require(isinstance(previous, dict) and previous.get('status') == 'planned'
                and isinstance(previous.get('manual_state'), dict),
                'PREVIOUS_PLAN_INVALID', 'Previous proposal requires replayable state')
        prior = previous['manual_state']
        obj(prior, state, state)
        require(prior['binding'] == binding, 'PREVIOUS_PLAN_CONFLICT', 'Previous plan belongs to another case, revision or recipe')
        state = copy.deepcopy(prior)
    obj(state['group_parameters'], {'handles'})
    for parameters in state['group_parameters'].values():
        obj(parameters, {'count', 'edge_offset', 'inner_offset', 'minimum_clearance'})
    unique(state['manual_overrides'], 'SYMMETRY_MANUAL_CONFLICT', 'group_id')
    unique(scenario.get('manual_overrides', []), 'SYMMETRY_MANUAL_CONFLICT', 'group_id')
    for item in state['manual_overrides'] + scenario.get('manual_overrides', []):
        group_id = item['group_id']
        allowed = recipe['scenario_contract']['reconcile']['allowed_group_parameters']
        require(group_id in allowed, 'SYMMETRY_MANUAL_CONFLICT', 'Only declared whole-group parameters are accepted')
        parameters = set(item) - {'group_id', 'approval'}
        require(parameters and parameters <= set(allowed[group_id]), 'SYMMETRY_MANUAL_CONFLICT', 'Unknown manual group parameter')
        approval(recipe, item.get('approval'), group_id, parameters)
        for name in parameters:
            n = finite(item[name])
            require(n >= 0 and (name != 'count' or type(n) is int), 'INVALID_OFFSET', 'Invalid group parameter')
    for item in scenario.get('manual_overrides', []):
        state['manual_overrides'] = [p for p in state['manual_overrides'] if p['group_id'] != item['group_id']] + [copy.deepcopy(item)]
    for change in scenario.get('manual_changes', []):
        kind = change['kind']
        if kind == 'move':
            fail('SYMMETRY_MANUAL_CONFLICT', 'Member moves require approval of the entire group')
        if kind == 'delete':
            fail('MANUAL_DELETE_CONFLICT', 'Required physical members cannot be removed')
        if kind == 'add':
            state['manual_additions'].append(copy.deepcopy(change))
    if scenario['operation'] == 'set_group_count':
        contract = recipe['scenario_contract']['set_group_count']
        require(scenario['group_id'] == contract['group_id'], 'SYMMETRY_MANUAL_CONFLICT', 'This group has no count rule')
        state['group_parameters']['handles'] = {k: scenario[k] for k in ('count', 'edge_offset', 'inner_offset', 'minimum_clearance') if k in scenario}
    return state


def _group_parameters(state):
    parameters = copy.deepcopy(state['group_parameters'])
    for override in state['manual_overrides']:
        parameters.setdefault(override['group_id'], {}).update({k: v for k, v in override.items() if k not in ('approval', 'group_id')})
    return parameters


def _make_part(part_id, group, uvn, shape, local_bounds, matrix, frames):
    vector(uvn)
    vector(shape, positive=True)
    bounds(local_bounds)
    require(near([b-a for a, b in zip(*local_bounds)], shape), 'GEOMETRY_POLICY_CONFLICT', 'Shape and catalog bounds differ')
    return {'id': part_id, 'definition': group['definition'], 'family': group['family'],
            'symmetry_group_id': group['symmetry_group_id'], 'frame': group['datum'],
            'uvn': copy.deepcopy(uvn), 'shape': copy.deepcopy(shape),
            'local_bounds': copy.deepcopy(local_bounds), 'rotation': copy.deepcopy(matrix),
            'closed_xyz': transformed(frames[group['datum']]['origin'], frames[group['datum']]['rotation'], uvn)}


def _count_slots(recipe, interpreter, parameters):
    rule = recipe['scenario_contract']['set_group_count']
    count = parameters.get('count', 1)
    require(type(count) is int and count in rule['allowed_counts'], 'GROUP_NO_SPACE', 'Unsupported handle pattern count')
    for field in ('edge_offset', 'inner_offset'):
        interpreter.values['scenario.' + field] = parameters.get(field, rule[field + '_default'])
        require(finite(interpreter.values['scenario.' + field]) >= 0, 'INVALID_OFFSET', 'Offsets cannot be negative')
    positions = interpreter.evaluate(rule['patterns'][str(count)])
    fit = recipe['fit_and_allowances']['ordinary_handle_wall_fit']
    separation = max(fit['adjacent_separation_min'], finite(parameters.get('minimum_clearance', fit['adjacent_separation_min'])))
    width, height = (finite(fit[k]) for k in ('width', 'height'))
    require(width > 0 and height > 0 and separation >= 0, 'RECIPE_INVALID_NUMBER', 'Invalid handle fit policy')
    require(all(width/2 + fit['edge_clearance_min'] <= x <= interpreter.values['W']-width/2-fit['edge_clearance_min'] for x in positions)
            and all(b-a >= width+separation for a, b in zip(positions, positions[1:]))
            and interpreter.values['B'] >= height,
            'GROUP_NO_SPACE', 'Handle pattern does not fit the wall')
    return [[x, interpreter.evaluate(rule['v']), interpreter.evaluate(rule['n'])] for x in positions], rule['mode_by_count'][str(count)]


def _addition(recipe, interpreter, change, frames, new=False):
    rule = recipe['scenario_contract']['reconcile']['manual_additions']
    require('anchor' in change and set(rule['required']) <= set(change), 'MANUAL_ANCHOR_REQUIRED', 'Manual part requires a reviewed parametric anchor')
    require(change['group_id'] == rule['allowed_group_id'] and change['id'] == change['group_id'] + '/1',
            'SYMMETRY_MANUAL_CONFLICT', 'Manual group and occurrence identity mismatch')
    approval(recipe, change['approval'], change['group_id'], ['anchored_addition'])
    anchor = change['anchor']
    require(anchor['frame'] == rule['allowed_anchor_frame'] and isinstance(anchor.get('rules'), list)
            and len(anchor['rules']) == 3 and all(r in rule['anchor_rule_allowlist'] for r in anchor['rules']),
            'MANUAL_ANCHOR_REQUIRED', 'Unknown manual anchor rule or frame')
    uvn = [interpreter.evaluate(rule['anchor_rule_allowlist'][name]) for name in anchor['rules']]
    require(anchor['rules'] == list(rule['anchor_rule_allowlist']), 'MANUAL_ANCHOR_REQUIRED', 'Anchor rules must address the declared axes')
    contract, supplied = rule['group_contract'], change['group']
    require(all(supplied.get(k) == contract[k] for k in ('family', 'mode', 'datum', 'axes', 'scope'))
            and supplied.get('exception_approval') == change['approval'],
            'SYMMETRY_MANUAL_CONFLICT', 'Manual addition must match the reviewed group scope')
    require(change['definition'] in rule['approved_definition_allowlist'], 'INVENTORY_UNRESOLVED', 'Unknown manual definition')
    definition = rule['approved_definition_allowlist'][change['definition']]
    members = supplied.get('members')
    require(isinstance(members, list) and len(members) == 1 and members[0].get('id') == change['id']
            and members[0].get('frame') == anchor['frame']
            and near(members[0].get('uvn'), anchor['uvn'])
            and near(members[0].get('shape'), definition['shape'])
            and near(members[0].get('local_bounds'), definition['local_bounds'])
            and near(members[0].get('rotation'), recipe['rotations'][definition['rotation']]),
            'SYMMETRY_MANUAL_CONFLICT', 'Supplied manual group and definition do not agree')
    if new:
        require(near(anchor['uvn'], uvn), 'MANUAL_ANCHOR_REQUIRED', 'Manual mounting point differs from its parametric anchor')
        require(near(supplied.get('centers'), {'0': interpreter.values['W']/2, '1': interpreter.values['D']/2}),
                'SYMMETRY_MANUAL_CONFLICT', 'Manual group has incorrect local symmetry centers')
    group = {k: copy.deepcopy(contract[k]) for k in ('family', 'mode', 'datum', 'axes', 'scope')}
    group.update(symmetry_group_id=change['group_id'], exception_approval=change['approval'], members=[change['id']],
                 definition=change['definition'])
    part = _make_part(change['id'], group, uvn, definition['shape'], definition['local_bounds'], recipe['rotations'][definition['rotation']], frames)
    del group['definition']
    return group, part


def _build(request, state, scenario=None):
    spec, recipe, manifest = (request[k] for k in ('spec', 'template_recipe', 'manifest'))
    scenario = copy.deepcopy(request['scenario'] if scenario is None else scenario)
    parameters = _group_parameters(state)
    # References used by the count rule exist even when the rule is inactive.
    count_rule = recipe['scenario_contract']['set_group_count']
    scenario.setdefault('edge_offset', count_rule['edge_offset_default'])
    scenario.setdefault('inner_offset', count_rule['inner_offset_default'])
    interpreter = Interpreter(spec, scenario, parameters)
    _validate_recipe(recipe, manifest, interpreter)
    values = interpreter.values
    iv = recipe['input_validation']
    require(spec['layout']['count'] == iv['layout_count'], 'INVALID_COUNT', 'Recipe defines a fixed device count')
    require(spec['layout']['side'] in iv['side'], 'INVALID_SIDE', 'Unsupported accessory axis')
    require(spec['layout']['orientation'] in iv['orientation'] and spec['layout']['arrangement'] in iv['arrangement'],
            'INVALID_ORIENTATION', 'Unsupported layout orientation')
    for name in iv['positive_finite_mm']:
        require(finite(spec['layout'][name]) > 0, 'INVALID_DIMENSION', 'Recipe dimensions must be positive')
    external = [finite(values[name]) for name in ('W', 'D', 'H')]
    require(all(v <= iv['max_plywood_dimension'] for v in external)
            and values['B'] > values['T'] and values['L'] > values['T']
            and all(a + TOL >= b for a, b in zip(values['internal'], values['initial_internal'])),
            'CASE_TOO_SMALL', 'Resized envelope cannot contain the specified layout')
    frames = {name: {'origin': vector(interpreter.evaluate(f['origin'])),
                     'rotation': copy.deepcopy(recipe['rotations'][f['rotation']])} for name, f in recipe['frames'].items()}
    groups, parts = [], []
    for rule in recipe['groups']:
        gid = rule['symmetry_group_id']
        group = {k: copy.deepcopy(rule[k]) for k in GROUP_METADATA}
        group['symmetry_group_id'] = gid
        slots = interpreter.evaluate(rule['slots'])
        if 'count_override' in rule:
            slots, group['mode'] = _count_slots(recipe, interpreter, parameters.get(gid, {}))
        require((group['mode'] == 'centered' and len(slots) == 1)
                or (group['mode'] == 'mirrored_pair' and len(slots) == 2)
                or (group['mode'] == 'centered_pattern' and len(slots) >= 3)
                or (group['mode'] == 'scoped_exception' and rule['exception_approval']),
                'SYMMETRY_INVALID', 'Group mode and cardinality differ')
        centers = interpreter.evaluate(rule['centers'])
        for axis, center in centers.items():
            finite(center)
            positions = sorted(vector(slot)[int(axis)] for slot in slots)
            require(all(near(a+b, 2*center) for a, b in zip(positions, reversed(positions))),
                    'SYMMETRY_INVALID', 'Slots violate declared local symmetry')
        for slot in slots:
            for axis, center in centers.items():
                counterpart = list(slot)
                counterpart[int(axis)] = 2*center-slot[int(axis)]
                require(any(near(other, counterpart) for other in slots), 'SYMMETRY_INVALID',
                        'Slot distribution lacks the complete reflection in a declared axis')
        require(len({tuple(slot) for slot in slots}) == len(slots), 'SYMMETRY_INVALID', 'Duplicate mounting slots')
        definition = recipe['catalog'][rule['definition']]
        shape = interpreter.evaluate(rule['shape']) if 'shape' in rule else copy.deepcopy(definition['shape'])
        vector(shape, positive=True)
        if definition.get('geometry_policy') == 'rigid':
            require(definition.get('synthetic_approved') is True and near(shape, definition['shape']),
                    'GEOMETRY_POLICY_CONFLICT', 'Rigid catalog geometry cannot be resized')
        elif rule['definition'] == 'panel':
            require(near(shape[2], values['T']), 'GEOMETRY_POLICY_CONFLICT', 'Panel thickness must remain fixed')
        elif rule['definition'] == 'profile':
            section = definition['section']
            require(isinstance(section, list) and len(section) == 2 and all(finite(v) > 0 for v in section)
                    and any(near([shape[i] for i in range(3) if i != axis], section) for axis in range(3)),
                    'GEOMETRY_POLICY_CONFLICT', 'Profile cross section must remain fixed')
        local = copy.deepcopy(definition['local_bounds']) if 'local_bounds' in definition else [[-v/2 for v in shape], [v/2 for v in shape]]
        rotations = rule['rotation'] if isinstance(rule['rotation'], list) else [rule['rotation']] * len(slots)
        require(len(rotations) == len(slots), 'INVALID_RIGID_ROTATION', 'Catalog rotation count mismatch')
        group['members'] = [gid + '/' + str(i+1) for i in range(len(slots))]
        for part_id, slot, name in zip(group['members'], slots, rotations):
            parts.append(_make_part(part_id, rule, slot, shape, local, recipe['rotations'][name], frames))
        groups.append(group)
    for addition in state['manual_additions']:
        group, part = _addition(recipe, interpreter, addition, frames,
                                addition in scenario.get('manual_changes', []))
        groups.append(group)
        parts.append(part)
    ids = unique(parts, 'OCCURRENCE_ID_DUPLICATE', 'id')
    unique(groups, 'SYMMETRY_GROUP_DUPLICATE', 'symmetry_group_id')
    require(not set(ids) & set(manifest['empty_assembly_ids']), 'INVENTORY_INCOMPLETE', 'Empty assemblies cannot be physical parts')
    by_part = {p['id']: p for p in parts}
    for pairing in recipe['pairings']:
        obj(pairing, {'kind', 'members', 'axes', 'datum', 'display_gap_effect'}, {'kind', 'members', 'axes', 'datum', 'display_gap_effect'})
        require(len(pairing['members']) == 2 and all(i in by_part for i in pairing['members'])
                and pairing['datum'] == 'closed' and pairing['display_gap_effect'] == 'none'
                and isinstance(pairing['axes'], list) and all(type(i) is int and i in (0, 1, 2) for i in pairing['axes']),
                'PAIRING_INVALID', 'Invalid closed pairing')
        a, b = (by_part[i] for i in pairing['members'])
        require(all(near(a['closed_xyz'][i], b['closed_xyz'][i]) for i in pairing['axes']),
                'PAIRING_MISMATCH', 'Paired mounting points differ')
    corners = [transformed(p['closed_xyz'], p['rotation'], list(corner)) for p in parts
               for corner in itertools.product(*zip(*p['local_bounds']))]
    transport = [[fn(point[i] for point in corners) for i in range(3)] for fn in (min, max)]
    presentation = {'lid_translation': interpreter.evaluate(recipe['presentation']['lid_translation']),
                    'lid_groups': copy.deepcopy(recipe['presentation']['lid_groups'])}
    vector(presentation['lid_translation'])
    require(recipe['presentation']['physical_coordinates'] == 'unchanged',
            'RECIPE_INVALID', 'Presentation cannot change physical coordinates')
    require(set(presentation['lid_groups']) <= {g['symmetry_group_id'] for g in groups},
            'SYMMETRY_GROUP_MISSING', 'Presentation names an unknown lid group')
    approvals = [item['approval'] for item in state['manual_overrides'] + state['manual_additions']]
    return {'status': 'planned', 'schema_version': 1, 'units': 'mm', 'synthetic': True,
            'production_approved': False, 'proof_scope': 'synthetic offline proposal; no CAD, collision or strength approval',
            'case_id': spec['case_id'], 'revision': spec['revision'], 'template_version': spec['template_version'],
            'rule_pack_version': recipe['rule_pack_version'], 'internal': copy.deepcopy(values['internal']),
            'plywood_external': external, 'base_height': values['B'], 'lid_height': values['L'],
            'frames': frames, 'groups': groups, 'occurrences': parts, 'pairings': copy.deepcopy(recipe['pairings']),
            'inventory': {'physical_ids': ids, 'unresolved_ids': [], 'empty_assembly_ids': copy.deepcopy(manifest['empty_assembly_ids'])},
            'transport_bounds': transport, 'transport_external': [b-a for a, b in zip(*transport)],
            'presentation': presentation, 'manual_state': copy.deepcopy(state),
            'preserved_manual_approvals': list(dict.fromkeys(approvals)), 'diagnostics': [],
            'changes': [{'kind': 'propose_occurrence', 'id': part['id']} for part in parts]}


def _audit(current, expected):
    require(isinstance(current, dict), 'AUDIT_INVALID', 'Expected an explicit observation')
    require(current.get('status') == 'planned', 'AUDIT_INVALID', 'Observation must be a planned physical proposal')
    strict = 'schema_version' in current
    if strict:
        for key in ('schema_version', 'case_id', 'revision', 'template_version', 'rule_pack_version', 'synthetic', 'production_approved'):
            require(near(current.get(key), expected[key]), 'PREVIOUS_PLAN_CONFLICT', 'Observation provenance differs')
    groups = current.get('groups')
    group_ids = unique(groups, 'SYMMETRY_GROUP_DUPLICATE', 'symmetry_group_id')
    wanted_groups = {g['symmetry_group_id']: g for g in expected['groups']}
    require(set(group_ids) == set(wanted_groups), 'SYMMETRY_GROUP_MISSING', 'Observation group inventory is incomplete')
    parts = current.get('occurrences')
    part_ids = unique(parts, 'OCCURRENCE_ID_DUPLICATE', 'id')
    wanted_parts = {p['id']: p for p in expected['occurrences']}
    require(set(part_ids) == set(wanted_parts), 'INVENTORY_INCOMPLETE', 'Observation physical inventory is incomplete')
    inventory = current.get('inventory', {})
    require(inventory.get('unresolved_ids') == [], 'INVENTORY_UNRESOLVED', 'Observation contains unresolved parts')
    observed_inventory = unique(inventory.get('physical_ids'), 'INVENTORY_INCOMPLETE')
    require(set(observed_inventory) == set(expected['inventory']['physical_ids'])
            and inventory.get('empty_assembly_ids') == expected['inventory']['empty_assembly_ids'],
            'INVENTORY_INCOMPLETE', 'Physical and empty assembly accounting differ')
    for group in groups:
        wanted = wanted_groups[group['symmetry_group_id']]
        if wanted['exception_approval']:
            require(group.get('exception_approval') is not None, 'SYMMETRY_EXCEPTION_REQUIRED', 'Observation lost scoped approval')
        require(all(near(group.get(k), wanted[k]) for k in GROUP_METADATA + ('members',)),
                'SYMMETRY_INVALID', 'Observation group metadata or membership differs')
    for part in parts:
        wanted = wanted_parts[part['id']]
        rotation(part.get('rotation'))
        require(part.get('frame') == wanted['frame'], 'ANCHOR_FRAME_MISMATCH', 'Observation used an incorrect wall frame')
        require(all(near(part.get(k), wanted[k]) for k in ('uvn', 'closed_xyz', 'rotation', 'shape', 'local_bounds')),
                'GEOMETRY_OBSERVATION_MISMATCH', 'Physical mounting or geometry differs from the planned rule')
        for key in ('definition', 'family', 'symmetry_group_id'):
            if strict or key in part:
                require(part.get(key) == wanted[key], 'INVENTORY_UNRESOLVED', 'Physical semantic identity differs')
    for key in ('units', 'frames', 'internal', 'plywood_external', 'base_height', 'lid_height', 'transport_bounds', 'transport_external'):
        require(near(current.get(key), expected[key]), 'GEOMETRY_OBSERVATION_MISMATCH', 'Observation datums or envelopes differ')
    if 'pairings' in current:
        require(near(current['pairings'], expected['pairings']), 'PAIRING_MISMATCH', 'Observation pairing rules differ')


def plan_case(request):
    """Return a detached proposal or stable diagnostics and no executable changes."""
    try:
        bounded_json(request)
        data = validate_request(request)
        require('template_recipe' in data, 'RECIPE_REQUIRED', 'An explicit recipe is required')
        state = _state(data)
        previous = data['scenario'].get('previous')
        if previous is not None:
            # Replay its saved decisions at its original size; refuse unilateral edits.
            prior_state = previous['manual_state']
            prior = _build(data, prior_state, {'operation': 'resize', 'target_plywood_external': previous['plywood_external']})
            _audit(previous, prior)
        result = _build(data, state)
        if data['scenario']['operation'] == 'audit':
            _audit(data['scenario'].get('current'), result)
        return result
    except ValidationError as exc:
        return {'status': 'blocked', 'diagnostics': [exc.as_dict()], 'changes': []}
    except (KeyError, TypeError, IndexError, ValueError, OverflowError, RecursionError):
        # Malformed untrusted recipe data is a refusal, never a partial plan.
        return {'status': 'blocked', 'diagnostics': [{'code': 'RECIPE_INVALID', 'path': '$',
                'message': 'Malformed recipe, observation, or persisted proposal data'}], 'changes': []}
