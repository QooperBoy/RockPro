"""ROC-15 v1 JSON contracts, using only the standard library.

Validation returns detached dictionaries; it never changes caller data, evaluates
recipe expressions, opens CAD, queries a source, or grants production approval.
"""
import copy
import itertools
import math


SCHEMA_VERSION = 1
DEFAULT_TEMPLATE_VERSIONS = ('synthetic-roc43-v1',)
LAYOUT_FIELDS = frozenset(('name', 'x', 'y', 'z', 'count', 'orientation',
    'arrangement', 'gap', 'clearance', 'separator', 'side', 'side_width',
    'side_depth', 'side_height', 'side_name', 'thickness', 'lid_height'))
TOLERANCE = 1e-6


class ValidationError(ValueError):
    """A stable machine code and JSON path, with a human-readable explanation."""
    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f'{code} at {path}: {message}')

    def as_dict(self):
        return dict(code=self.code, path=self.path, message=self.message)


def _fail(code, path, message):
    raise ValidationError(code, path, message)


def _object(value, path, allowed, required=()):
    if not isinstance(value, dict):
        _fail('INVALID_OBJECT', path, 'Expected a JSON object')
    for key in value:
        if not isinstance(key, str) or key not in allowed:
            _fail('UNKNOWN_FIELD', path + '.' + str(key), 'Field is not in this schema')
    for key in sorted(required):
        if key not in value:
            _fail('FIELD_REQUIRED', path + '.' + key, 'Required field is missing')
    return value


def _text(value, path, code='IDENTITY_REQUIRED', maximum=200):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _fail(code, path, f'Expected nonempty text up to {maximum} characters')
    return value


def _integer(value, path, low=1, high=None, code='INVALID_REVISION'):
    if isinstance(value, bool) or not isinstance(value, int) or value < low or (high is not None and value > high):
        _fail(code, path, 'Expected an integer in the supported range')


def _number(value, path, low=None, high=None, code='INVALID_DIMENSION', finite_code=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(code, path, 'Expected a finite number, never a boolean')
    try:
        finite = math.isfinite(value)
    except (OverflowError, ValueError):
        finite = False
    if not finite:
        _fail(finite_code or code, path, 'NaN and infinity are not supported')
    if (low is not None and value < low) or (high is not None and value > high):
        _fail(code, path, 'Number is outside the supported range')
    return value


def _vector(value, path, *, positive=False, code='INVALID_DIMENSION'):
    if not isinstance(value, list) or len(value) != 3:
        _fail(code, path, 'Expected a three-component JSON vector')
    for i, item in enumerate(value):
        _number(item, f'{path}[{i}]', low=0 if positive else None, code=code)
        if positive and item == 0:
            _fail(code, f'{path}[{i}]', 'Dimension must be positive')
    return value


def _version(obj, path):
    version = obj.get('schema_version')
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        _fail('UNSUPPORTED_SCHEMA', path + '.schema_version', 'Only schema version 1 is supported; no implicit migration')


def _units(obj, path):
    if 'units' not in obj:
        _fail('UNITS_REQUIRED', path + '.units', 'Explicit millimetres are required')
    if obj['units'] != 'mm':
        _fail('UNITS_MISMATCH', path + '.units', 'Contract values must be in mm')


def _approval(value, path, scope, code='SOURCE_SCOPE_INVALID', bindings=None):
    bindings = bindings or {}
    fields = {'scope', 'reference', 'approved_by'} | set(bindings)
    _object(value, path, fields, fields)
    if value['scope'] != scope:
        _fail(code, path + '.scope', 'Approval must name this exact scope')
    for field in ('reference', 'approved_by'):
        _text(value[field], path + '.' + field, code)
    for field, expected in bindings.items():
        if value[field] != expected:
            _fail(code, path + '.' + field, 'Approval does not bind this group, template and source')


def validate_dimension_source(value, *, path='$', scope='dimensions'):
    """Validate supplied provenance claims; do not authenticate an approval."""
    if value is None:
        _fail('DIMENSION_SOURCE_REQUIRED', path, 'Dimension provenance is required')
    _object(value, path, {'kind', 'reference', 'confirmation', 'approval'}, {'kind', 'reference', 'confirmation'})
    if value['kind'] not in ('synthetic', 'manufacturer', 'measurement', 'constructor'):
        _fail('SOURCE_SCOPE_INVALID', path + '.kind', 'Unsupported source kind')
    _text(value['reference'], path + '.reference', 'DIMENSION_SOURCE_REQUIRED', 1000)
    if value['kind'] == 'synthetic':
        if value['confirmation'] != 'test-only' or 'approval' in value:
            _fail('SOURCE_SCOPE_INVALID', path, 'Synthetic input is test-only and cannot carry production approval')
    else:
        if value['reference'].upper().startswith(('SYNTHETIC', 'NONE-SYNTHETIC', 'ROC-43/')):
            _fail('SOURCE_SCOPE_INVALID', path + '.reference', 'Synthetic references cannot represent a real source')
        if value['confirmation'] not in ('confirmed', 'unconfirmed'):
            _fail('SOURCE_SCOPE_INVALID', path + '.confirmation', 'Unsupported source confirmation')
        if value['confirmation'] == 'confirmed' and 'approval' not in value:
            _fail('SOURCE_SCOPE_INVALID', path + '.approval', 'Confirmed source requires a scoped approval reference')
        if 'approval' in value:
            _approval(value['approval'], path + '.approval', scope)
            if value['confirmation'] != 'confirmed':
                _fail('SOURCE_SCOPE_INVALID', path, 'Unconfirmed source cannot carry approval')
            if value['approval']['reference'].upper().startswith('SYNTHETIC'):
                _fail('SOURCE_SCOPE_INVALID', path + '.approval.reference', 'Synthetic approval cannot approve real input')
    return copy.deepcopy(value)


def _layout(value, path):
    _object(value, path, LAYOUT_FIELDS, LAYOUT_FIELDS)
    for field in ('name', 'side_name'):
        _text(value[field], path + '.' + field, 'INVALID_NAME', 100)
    bounds = {key: (1, 5000) for key in ('x', 'y', 'z', 'side_width', 'side_depth', 'side_height')}
    bounds.update(gap=(0, 500), clearance=(0, 500), separator=(0, 50),
                  thickness=(1, 100), lid_height=(2, 1000))
    for field, (low, high) in bounds.items():
        code = ('INVALID_THICKNESS' if field == 'thickness' else
                'INVALID_CLEARANCE' if field in ('gap', 'clearance') else 'INVALID_DIMENSION')
        _number(value[field], path + '.' + field, low, high, code, 'NONFINITE_DIMENSION')
    _integer(value['count'], path + '.count', 1, 30, 'INVALID_COUNT')
    if value['orientation'] not in tuple(map(''.join, itertools.permutations('XYZ'))):
        _fail('INVALID_ORIENTATION', path + '.orientation', 'Expected a permutation of XYZ')
    if value['arrangement'] not in ('X', 'Y', 'Z'):
        _fail('INVALID_ARRANGEMENT', path + '.arrangement', 'Expected X, Y or Z')
    if value['side'] not in ('none', 'X', 'Y'):
        _fail('INVALID_SIDE', path + '.side', 'Expected none, X or Y')
    # Envelope feasibility is the existing layout boundary, not a CAD generator.
    sizes = [value[key.lower()] for key in value['orientation']]
    axis = 'XYZ'.index(value['arrangement'])
    extent = sizes.copy()
    extent[axis] = value['count'] * sizes[axis] + (value['count'] - 1) * (value['gap'] + value['separator'])
    inside = [v + 2 * value['clearance'] for v in extent]
    if value['side'] != 'none':
        side = 'XY'.index(value['side'])
        inside[1-side] = max(inside[1-side], value['side_depth'] + 2 * value['clearance'])
        inside[2] = max(inside[2], value['side_height'] + 2 * value['clearance'])
        inside[side] += value['thickness'] + value['side_width'] + 2 * value['clearance']
    plywood = [v + 2 * value['thickness'] for v in inside]
    if max(plywood) > 10000:
        _fail('CASE_TOO_LARGE', path, 'Plywood envelope exceeds the existing 10000 mm limit')
    if value['lid_height'] <= value['thickness'] or plywood[2] - value['lid_height'] <= value['thickness']:
        _fail('CASE_TOO_SMALL', path + '.lid_height', 'Base and lid height must each exceed panel thickness')
    return inside, plywood


def validate_case_spec(value, *, supported_templates=DEFAULT_TEMPLATE_VERSIONS):
    fields = {'case_id', 'schema_version', 'revision', 'expected_revision', 'template_version',
              'units', 'axes', 'dimension_source', 'layout', 'display_gap',
              'interior_symmetry_approval', 'dimension_envelopes', 'order_quantity'}
    _object(value, '$', fields)
    _version(value, '$')
    _text(value.get('case_id'), '$.case_id', 'CASE_ID_REQUIRED')
    _units(value, '$')
    if value.get('axes') != 'right-handed-XYZ':
        _fail('AXES_MISMATCH', '$.axes', 'Expected explicit right-handed-XYZ')
    if value.get('template_version') not in supported_templates:
        _fail('UNSUPPORTED_TEMPLATE', '$.template_version', 'Template version must be explicitly registered')
    _integer(value.get('revision'), '$.revision')
    expected = value.get('expected_revision')
    _integer(expected, '$.expected_revision', code='REVISION_CONFLICT')
    if expected != value['revision']:
        _fail('REVISION_CONFLICT', '$.expected_revision', 'Expected revision differs from this specification revision')
    if 'order_quantity' in value:
        _integer(value['order_quantity'], '$.order_quantity', 1, 100000, 'INVALID_ORDER_QUANTITY')
    source = validate_dimension_source(value.get('dimension_source'), path='$.dimension_source')
    if value['template_version'].startswith('synthetic-') and source['kind'] != 'synthetic':
        _fail('SOURCE_SCOPE_INVALID', '$.dimension_source', 'Synthetic template requires synthetic input provenance')
    if not value['template_version'].startswith('synthetic-') and source['kind'] == 'synthetic':
        _fail('SOURCE_SCOPE_INVALID', '$.dimension_source', 'Synthetic provenance cannot approve a real template')
    inside, plywood = _layout(value.get('layout'), '$.layout')
    _number(value.get('display_gap'), '$.display_gap', 0, 1000, 'INVALID_DIMENSION', 'NONFINITE_DIMENSION')
    if 'interior_symmetry_approval' in value:
        approval = value['interior_symmetry_approval']
        if source['kind'] == 'synthetic':
            if not isinstance(approval, str) or not approval.startswith('SYNTHETIC-'):
                _fail('SYMMETRY_EXCEPTION_UNAPPROVED', '$.interior_symmetry_approval', 'Synthetic exception must remain explicitly test-only')
        else:
            _approval(approval, '$.interior_symmetry_approval', 'interior', 'SYMMETRY_EXCEPTION_REQUIRED')
            if approval['reference'].upper().startswith('SYNTHETIC'):
                _fail('SYMMETRY_EXCEPTION_REQUIRED', '$.interior_symmetry_approval.reference', 'Synthetic approval cannot approve a real template')
    elif value['layout']['side'] != 'none':
        _fail('SYMMETRY_EXCEPTION_REQUIRED', '$.interior_symmetry_approval', 'Accessory interior requires an explicit symmetry exception')
    if 'dimension_envelopes' in value:
        envelopes = _object(value['dimension_envelopes'], '$.dimension_envelopes',
            {'device', 'internal', 'plywood_external', 'transport_external'})
        expected_spaces = {'device': [value['layout'][k] for k in ('x','y','z')],
                           'internal': inside, 'plywood_external': plywood}
        for name, item in envelopes.items():
            path = '$.dimension_envelopes.' + name
            _object(item, path, {'value', 'units', 'source'}, {'value', 'units', 'source'})
            _units(item, path)
            dims = _vector(item['value'], path + '.value', positive=True)
            validate_dimension_source(item['source'], path=path + '.source')
            if name in expected_spaces and any(abs(a-b) > TOLERANCE for a,b in zip(dims, expected_spaces[name])):
                _fail('DIMENSION_ENVELOPE_MISMATCH', path, 'Declared envelope disagrees with explicit layout inputs')
            if name == 'transport_external' and any(a + TOLERANCE < b for a,b in zip(dims, plywood)):
                _fail('DIMENSION_ENVELOPE_MISMATCH', path, 'Transport envelope cannot be smaller than plywood')
    return copy.deepcopy(value)


def _rotation(value, path, code='INVALID_ROTATION'):
    if not isinstance(value, list) or len(value) != 3:
        _fail(code, path, 'Expected a 3x3 rotation matrix')
    for i, row in enumerate(value):
        _vector(row, f'{path}[{i}]', code=code)
    for i in range(3):
        for j in range(3):
            if abs(sum(value[i][k] * value[j][k] for k in range(3)) - (1 if i == j else 0)) > TOLERANCE:
                _fail(code, path, 'Basis must be orthonormal')
    a,b,c = value
    determinant = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    if abs(determinant - 1) > TOLERANCE:
        _fail(code, path, 'Rotation must have determinant +1')


def validate_wall_frame(value, *, path='$'):
    _object(value, path, {'origin', 'u', 'v', 'n'}, {'origin', 'u', 'v', 'n'})
    _vector(value['origin'], path + '.origin', code='INVALID_FRAME')
    _rotation([value['u'],value['v'],value['n']], path, 'INVALID_FRAME')
    return copy.deepcopy(value)


def validate_anchor(value, *, path='$'):
    fields = {'schema_version','anchor_id','wall_id','datum','frame','edge','offsets','orientation'}
    _object(value, path, fields, fields)
    _version(value, path)
    for field in ('anchor_id','wall_id'):
        _text(value[field], path + '.' + field)
    if value['datum'] not in ('panel','profile','closure_plane'):
        _fail('INVALID_DATUM', path + '.datum', 'Expected panel, profile or closure_plane')
    if value['edge'] not in ('left','right','top','bottom','center','seam'):
        _fail('INVALID_EDGE', path + '.edge', 'Unknown semantic edge')
    validate_wall_frame(value['frame'], path=path + '.frame')
    offsets = _object(value['offsets'], path + '.offsets', {'u','v','n'}, {'u','v','n'})
    for axis, offset in offsets.items():
        offset_path = path + '.offsets.' + axis
        _object(offset, offset_path, {'mode','value'}, {'mode'})
        mode = offset['mode']
        if mode == 'centered':
            if 'value' in offset:
                _fail('INVALID_OFFSET', offset_path, 'Centered offset has no independent numeric value')
        elif mode in ('fixed','proportional'):
            _number(offset.get('value'), offset_path + '.value', 0 if mode == 'proportional' else -10000,
                    1 if mode == 'proportional' else 10000, 'INVALID_OFFSET')
        else:
            _fail('INVALID_OFFSET', offset_path + '.mode', 'Expected fixed, proportional or centered')
    _rotation(value['orientation'], path + '.orientation')
    return copy.deepcopy(value)


def validate_part_definition(value, *, path='$'):
    fields = {'schema_version','definition_id','family','units','geometry_policy',
              'dimensions','dimension_source','catalog_reference'}
    _object(value, path, fields, fields - {'catalog_reference'})
    _version(value, path)
    for field in ('definition_id','family'):
        _text(value[field], path + '.' + field)
    _units(value, path)
    if value['geometry_policy'] not in ('rigid','panel','profile','interior'):
        _fail('INVALID_GEOMETRY_POLICY', path + '.geometry_policy', 'Unknown geometry policy; rigid parts must never be scaled')
    _vector(value['dimensions'], path + '.dimensions', positive=True)
    validate_dimension_source(value['dimension_source'], path=path + '.dimension_source')
    if 'catalog_reference' in value:
        _text(value['catalog_reference'], path + '.catalog_reference')
    return copy.deepcopy(value)


def validate_part_occurrence(value, *, path='$'):
    fields = {'schema_version','occurrence_id','definition_id','semantic_role','anchor','cad_reference'}
    _object(value, path, fields, fields - {'cad_reference'})
    _version(value, path)
    for field in ('occurrence_id','definition_id','semantic_role'):
        _text(value[field], path + '.' + field)
    validate_anchor(value['anchor'], path=path + '.anchor')
    if 'cad_reference' in value:
        ref_path = path + '.cad_reference'
        _object(value['cad_reference'], ref_path, {'document_id','node_id'}, {'document_id','node_id'})
        for field in ('document_id','node_id'):
            _text(value['cad_reference'][field], ref_path + '.' + field)
    return copy.deepcopy(value)


def validate_symmetry_group(value, *, path='$'):
    fields = {'schema_version','symmetry_group_id','mode','scope','member_ids','axes','datum',
              'exception_approval','template_version','source_reference'}
    _object(value, path, fields, fields - {'exception_approval','template_version','source_reference'})
    _version(value, path)
    for field in ('symmetry_group_id','scope','datum'):
        _text(value[field], path + '.' + field)
    members = value['member_ids']
    if not isinstance(members, list) or not members:
        _fail('SYMMETRY_GROUP_INVALID', path + '.member_ids', 'Symmetry group must name every member')
    for i, member in enumerate(members):
        _text(member, f'{path}.member_ids[{i}]')
    if len(members) != len(set(members)):
        _fail('DUPLICATE_ID', path + '.member_ids', 'A member may occur only once')
    axes = value['axes']
    if not isinstance(axes, list) or not axes or any(axis not in ('u','v','n') for axis in axes) or len(set(axes)) != len(axes):
        _fail('SYMMETRY_GROUP_INVALID', path + '.axes', 'Expected distinct explicit local symmetry axes')
    mode = value['mode']
    if mode not in ('centered','mirrored_pair','centered_pattern','scoped_exception'):
        _fail('SYMMETRY_GROUP_INVALID', path + '.mode', 'Unknown symmetry mode')
    if (mode == 'centered' and len(members) != 1) or (mode == 'mirrored_pair' and len(members) != 2) or (mode == 'centered_pattern' and len(members) < 3):
        _fail('SYMMETRY_GROUP_INVALID', path + '.member_ids', 'Member count does not match the symmetry mode')
    if mode == 'scoped_exception':
        if 'exception_approval' not in value:
            _fail('SYMMETRY_EXCEPTION_REQUIRED', path + '.exception_approval', 'Scoped exception requires constructor approval')
        for field in ('template_version','source_reference'):
            _text(value.get(field), path + '.' + field, 'SYMMETRY_EXCEPTION_REQUIRED')
        _approval(value['exception_approval'], path + '.exception_approval', value['scope'], 'SYMMETRY_EXCEPTION_REQUIRED',
            {'symmetry_group_id':value['symmetry_group_id'], 'template_version':value['template_version'],
             'source_reference':value['source_reference']})
        synthetic = value['template_version'].startswith('synthetic-')
        synthetic_approval = value['exception_approval']['reference'].upper().startswith('SYNTHETIC')
        if synthetic != synthetic_approval:
            _fail('SYMMETRY_EXCEPTION_REQUIRED', path + '.exception_approval.reference', 'Test-only and real approvals must not be mixed')
    elif value.get('exception_approval') is not None:
        _fail('SYMMETRY_EXCEPTION_REQUIRED', path + '.exception_approval', 'Approval applies only to an explicit scoped exception')
    return copy.deepcopy(value)


def validate_component_set(value):
    """Cross-check ready component data, never promote inventory candidates."""
    fields = {'schema_version','template_version','source_reference','definitions','occurrences','symmetry_groups'}
    _object(value, '$', fields, fields)
    _version(value, '$')
    for field in ('template_version','source_reference'):
        _text(value[field], '$.' + field)
    validators = {'definitions': (validate_part_definition,'definition_id'),
                  'occurrences': (validate_part_occurrence,'occurrence_id'),
                  'symmetry_groups': (validate_symmetry_group,'symmetry_group_id')}
    indexed = {}
    for field, (validator, identity) in validators.items():
        items = value[field]
        if not isinstance(items, list):
            _fail('INVALID_OBJECT', '$.' + field, 'Expected a JSON array')
        if not items:
            _fail('SYMMETRY_GROUP_MISSING' if field == 'symmetry_groups' else 'COMPONENT_SET_EMPTY',
                  '$.' + field, 'A component set must explicitly describe physical components and their symmetry groups')
        indexed[field] = {}
        for i, item in enumerate(items):
            path = f'$.{field}[{i}]'
            validator(item, path=path)
            key = item[identity]
            if key in indexed[field]:
                _fail('DUPLICATE_ID', path + '.' + identity, 'Identity must be unique in this component set')
            indexed[field][key] = item
    for i, definition in enumerate(value['definitions']):
        if value['template_version'].startswith('synthetic-') != (definition['dimension_source']['kind'] == 'synthetic'):
            _fail('SOURCE_SCOPE_INVALID', f'$.definitions[{i}].dimension_source', 'Definition provenance must match the synthetic or real template context')
    memberships = {key: 0 for key in indexed['occurrences']}
    for i, occurrence in enumerate(value['occurrences']):
        if occurrence['definition_id'] not in indexed['definitions']:
            _fail('DEFINITION_NOT_FOUND', f'$.occurrences[{i}].definition_id', 'Occurrence must reference a known definition')
    for i, group in enumerate(value['symmetry_groups']):
        if group['mode'] == 'scoped_exception':
            if group['template_version'] != value['template_version'] or group['source_reference'] != value['source_reference']:
                _fail('SYMMETRY_EXCEPTION_REQUIRED', f'$.symmetry_groups[{i}]', 'Exception belongs to another source or template')
        for member in group['member_ids']:
            if member not in memberships:
                _fail('OCCURRENCE_NOT_FOUND', f'$.symmetry_groups[{i}].member_ids', 'Group references an unknown occurrence')
            occurrence = indexed['occurrences'][member]
            if group['scope'] != occurrence['anchor']['wall_id']:
                _fail('SYMMETRY_SCOPE_MISMATCH', f'$.symmetry_groups[{i}].scope', 'Group scope must match every member anchor wall')
            memberships[member] += 1
    for member, count in memberships.items():
        if count != 1:
            _fail('SYMMETRY_GROUP_MISSING' if count == 0 else 'SYMMETRY_MEMBERSHIP_CONFLICT',
                  '$.occurrences.' + member, 'Each mounted occurrence requires exactly one symmetry group')
    return copy.deepcopy(value)


def _json_data(value, path='$', depth=0):
    """Require finite, serializable JSON data, including opaque observations."""
    if depth > 64:
        _fail('INVALID_JSON_DATA', path, 'JSON nesting limit exceeded or cyclic input')
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        _number(value, path, code='INVALID_JSON_DATA')
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _json_data(item, f'{path}[{i}]', depth+1)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail('INVALID_JSON_DATA', path, 'JSON keys must be strings')
            _json_data(item, path + '.' + key, depth+1)
    else:
        _fail('INVALID_JSON_DATA', path, 'Only JSON data is accepted')


def _request_manifest(manifest, spec):
    if not isinstance(manifest, dict) or not manifest:
        _fail('MANIFEST_INVALID', '$.manifest', 'An explicit nonempty manifest is required')
    if manifest.get('manifest_kind') == 'source_bound_inventory':
        from .manifest import validate_manifest
        validation = validate_manifest(manifest)
        if not validation.valid:
            _fail('MANIFEST_INVALID', '$.manifest', 'Source-bound inventory manifest is structurally invalid')
        # ROC-42 accounts source evidence. Its candidate roles do not satisfy the
        # ready definition/anchor/symmetry contract. No implicit promotion exists.
        _fail('MANIFEST_NOT_READY', '$.manifest', 'Inventory proposal requires explicit promotion to ready component contracts')
    fields = {'version','synthetic','production_approved','source_template','required_families',
              'empty_assembly_ids','unresolved_ids','interior_exception_approval','group_roles'}
    _object(manifest, '$.manifest', fields, fields)
    if manifest['version'] != spec['template_version'] or manifest['synthetic'] is not True or manifest['production_approved'] is not False or spec['dimension_source']['kind'] != 'synthetic':
        _fail('MANIFEST_INVALID', '$.manifest', 'ROC-43 summary is restricted to its explicitly synthetic template')
    if not manifest['version'].startswith('synthetic-'):
        _fail('MANIFEST_INVALID', '$.manifest.version', 'Summary is a synthetic compatibility contract')
    for field in ('required_families','empty_assembly_ids','unresolved_ids','group_roles'):
        items = manifest[field]
        if not isinstance(items, list):
            _fail('MANIFEST_INVALID', '$.manifest.' + field, 'Expected a list of explicit IDs')
        for i, item in enumerate(items):
            _text(item, f'$.manifest.{field}[{i}]', 'MANIFEST_INVALID')
        if len(items) != len(set(items)):
            _fail('DUPLICATE_ID', '$.manifest.' + field, 'Summary IDs must be unique')
    if manifest['unresolved_ids'] or not manifest['required_families'] or not manifest['group_roles']:
        _fail('MANIFEST_NOT_READY', '$.manifest', 'Unresolved or incomplete summary cannot cross the planning boundary')
    _text(manifest['source_template'], '$.manifest.source_template', 'MANIFEST_INVALID')
    if manifest['interior_exception_approval'] != spec.get('interior_symmetry_approval'):
        code = 'SYMMETRY_EXCEPTION_UNAPPROVED' if spec.get('interior_symmetry_approval') else 'SYMMETRY_EXCEPTION_REQUIRED'
        _fail(code, '$.manifest.interior_exception_approval', 'Exception must match this synthetic input')


def _recipe_header(recipe, spec):
    # Only the transport/header boundary is implemented in ROC-15. The recipe
    # remains inert JSON; AST semantics and evaluation belong to the future core.
    fields = {'schema_version','template_version','rule_pack_version','synthetic','production_approved',
              'source','units','axes','expression_language','input_validation','constants','catalog',
              'rotations','derived','frames','groups','pairings','inventory','scenario_contract',
              'coordinate_rules','approvals','fit_and_allowances','transport_envelope','presentation',
              'out_of_scope','group_count','physical_occurrence_count_default'}
    _object(recipe, '$.template_recipe', fields,
        {'schema_version','template_version','rule_pack_version','synthetic','production_approved','source','units','axes'})
    _version(recipe, '$.template_recipe')
    _units(recipe, '$.template_recipe')
    if recipe['template_version'] != spec['template_version'] or recipe['axes'] != spec['axes']:
        _fail('RECIPE_MISMATCH', '$.template_recipe', 'Recipe header must match this specification')
    if recipe['synthetic'] is not True or recipe['production_approved'] is not False:
        _fail('RECIPE_MISMATCH', '$.template_recipe', 'ROC-43 recipe compatibility is explicitly test-only')
    for field in ('source','rule_pack_version'):
        _text(recipe[field], '$.template_recipe.' + field, 'RECIPE_MISMATCH', 1000)


def validate_request(value, *, supported_templates=DEFAULT_TEMPLATE_VERSIONS):
    """Validate the input boundary only. No plan or production status is returned.

    ROC-43 summaries are explicitly synthetic compatibility inputs. Source-bound
    inventory proposals cannot be silently promoted to ready runtime components.
    """
    _object(value, '$', {'spec','manifest','template_recipe','scenario'}, {'spec','manifest','scenario'})
    scenario = value['scenario']
    if not isinstance(scenario, dict):
        _fail('INVALID_OBJECT', '$.scenario', 'Expected an explicit scenario object')
    operation = scenario.get('operation')
    fields = {
        'plan': {'operation'},
        'audit': {'operation','current'},
        'resize': {'operation','target_plywood_external','previous'},
        'display': {'operation','display_gap'},
        'set_group_count': {'operation','group_id','count','edge_offset','inner_offset','minimum_clearance','previous'},
        'reconcile': {'operation','manual_changes','manual_overrides','actor','expected_revision','current_revision','previous'},
    }
    if not isinstance(operation, str) or operation not in fields:
        _fail('UNSUPPORTED_OPERATION', '$.scenario.operation', 'Operation is not allowed by the offline contract')
    _object(scenario, '$.scenario', fields[operation], {'operation'})
    validate_case_spec(value['spec'], supported_templates=supported_templates)
    _request_manifest(value['manifest'], value['spec'])
    if 'template_recipe' in value:
        _recipe_header(value['template_recipe'], value['spec'])
    if operation == 'resize':
        _vector(scenario.get('target_plywood_external'), '$.scenario.target_plywood_external', positive=True)
    if operation == 'display':
        _number(scenario.get('display_gap'), '$.scenario.display_gap', 0, 1000)
    if operation == 'set_group_count':
        _text(scenario.get('group_id'), '$.scenario.group_id')
        _integer(scenario.get('count'), '$.scenario.count', 1, 10000, 'INVALID_COUNT')
        for field in ('edge_offset','inner_offset','minimum_clearance'):
            if field in scenario:
                _number(scenario[field], '$.scenario.' + field, 0, 10000, 'INVALID_OFFSET')
    if operation == 'reconcile':
        for field in ('expected_revision','current_revision'):
            if field in scenario:
                _integer(scenario[field], '$.scenario.' + field, code='REVISION_CONFLICT')
                if scenario[field] != value['spec']['revision']:
                    _fail('REVISION_CONFLICT', '$.scenario.' + field, 'Revision differs from this specification')
        if 'actor' in scenario and scenario['actor'] not in ('AI','UI','CLI','constructor'):
            _fail('INVALID_ACTOR', '$.scenario.actor', 'Unknown actor')
        for field in ('manual_changes','manual_overrides'):
            if field not in scenario:
                continue
            if not isinstance(scenario[field], list):
                _fail('INVALID_OBJECT', '$.scenario.' + field, 'Expected a list of explicit manual proposals')
            for i, item in enumerate(scenario[field]):
                path = f'$.scenario.{field}[{i}]'
                if field == 'manual_changes':
                    _object(item, path, {'kind','id','delta','definition','anchor','group','group_id','approval'}, {'kind','id'})
                    _text(item['id'], path + '.id')
                    if item['kind'] not in ('move','add','delete'):
                        _fail('UNSUPPORTED_OPERATION', path + '.kind', 'Unknown manual change')
                    if 'delta' in item:
                        _vector(item['delta'], path + '.delta')
                    if 'anchor' in item:
                        # Legacy ROC-43 observation anchor is inert data. It is
                        # deliberately not interpreted as a ready AnchorSpec.
                        _object(item['anchor'], path + '.anchor', {'frame','uvn','rules'}, {'frame','uvn'})
                        _text(item['anchor']['frame'], path + '.anchor.frame')
                        _vector(item['anchor']['uvn'], path + '.anchor.uvn')
                else:
                    _object(item, path, {'group_id','count','edge_offset','approval'}, {'group_id','approval'})
                    _text(item['group_id'], path + '.group_id')
                    if 'count' in item:
                        _integer(item['count'], path + '.count', 1, 10000, 'INVALID_COUNT')
                    if 'edge_offset' in item:
                        _number(item['edge_offset'], path + '.edge_offset', 0, 10000, 'INVALID_OFFSET')
                if 'approval' in item:
                    if not isinstance(item['approval'], str) or not item['approval'].startswith('SYNTHETIC-') or value['spec']['dimension_source']['kind'] != 'synthetic':
                        _fail('SOURCE_SCOPE_INVALID', path + '.approval', 'Legacy manual approval tokens are synthetic-only')
    _json_data(value)
    return copy.deepcopy(value)
