"""Mount-owned machining in millimetres; geometry comes from pinned CAD features.

Row-vector transforms match ICAPI. A bounding box is used for clearance only,
never as a substitute for the catalog's cutting contour.
"""
import math
import copy
import heapq
import re
from .profile_rules import value
from ..part_registry import metadata, contract

# Measured complete upper halves, relative to the base rim; includes the flange.
LID_HARDWARE_REACH_MM = {'17251S': 69.854, '270836': 67.01}
TOP_PROFILE_REACH_MM = 35.
MIN_HARDWARE_CLEARANCE_MM = 5.


def lid_threshold(hardware_reaches_mm, profile_reach_mm, clearance_mm=MIN_HARDWARE_CLEARANCE_MM):
    """Reusable catalog threshold; missing reach data cannot imply zero clearance."""
    if not hardware_reaches_mm or any(type(v) not in (float, int) or not math.isfinite(v) or v < 0
                                     for v in hardware_reaches_mm):
        raise ValueError('Measured hardware reaches required')
    if type(profile_reach_mm) not in (float, int) or not math.isfinite(profile_reach_mm) or profile_reach_mm < 0:
        raise ValueError('Measured edge profile reach required')
    if not math.isfinite(clearance_mm) or clearance_mm < MIN_HARDWARE_CLEARANCE_MM:
        raise ValueError('Hardware clearance must be at least 5 mm')
    return math.ceil(max(hardware_reaches_mm) + profile_reach_mm + clearance_mm)


def minimum_lid_height(clearance_mm=MIN_HARDWARE_CLEARANCE_MM):
    return lid_threshold(list(LID_HARDWARE_REACH_MM.values()), TOP_PROFILE_REACH_MM, clearance_mm)


def local_cut_pose(world_rotation, world_position, target_rotation, target_position):
    """Compose cut_world * inverse(target_world), retaining native expressions."""
    for matrix in (world_rotation, target_rotation):
        if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
            raise ValueError('A 3 by 3 orthogonal frame is required')
        if any(not math.isfinite(x) for row in matrix for x in row):
            raise ValueError('Nonfinite frame')
        for i in range(3):
            for j in range(3):
                if abs(sum(matrix[i][k]*matrix[j][k] for k in range(3)) - (i == j)) > 1e-7:
                    raise ValueError('Scaling a machining contour is forbidden')
    rotation = [[sum(world_rotation[i][k]*target_rotation[j][k] for k in range(3))
                 for j in range(3)] for i in range(3)]
    position = []
    for j in range(3):
        terms = [f'({target_rotation[j][k]:.15g}) * (({world_position[k]}) - ({target_position[k]}))'
                 for k in range(3) if abs(target_rotation[j][k]) > 1e-12]
        position.append(' + '.join(terms) or '0 mm')
    return rotation, position


def machining_step(key, mount_key, family, target_id, template_id, rotation, position, parameters):
    if not key or not mount_key or type(target_id) is not int or type(template_id) is not int:
        raise ValueError('Explicit mount, target and measured template identities required')
    return dict(key=key, mount_key=mount_key, target_id=target_id, template_id=template_id,
                rotation=rotation, position=position,
                initial_mm=[value(x, parameters) for x in position],
                through_target=True, **metadata(family))


def validate_layout(parameters, handles_per_wall=2):
    """Prototype envelope for H7159 / 17251S / 270836 and measured EG-0500 pair.

    This does not approve load capacity or arbitrary catalog substitutions.
    Changing the measured joint gap or plywood thickness needs a new fit study.
    """
    from .transport_rules import validate_transport_values
    from .profile_rules import PARAMETERS
    validate_transport_values({k: parameters[k] for k in PARAMETERS})
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in parameters.values()):
        raise ValueError('Finite dimensions required')
    if handles_per_wall not in (1, 2):
        raise ValueError('One or two handles per opposing wall required')
    if abs(parameters['RP_Thickness']-9.8) > 1e-6 or abs(parameters['RP_JointGap']-8.63) > 1e-6:
        raise ValueError('This measured profile pair requires T=9.8 and J=8.63 mm')
    if parameters['RP_LidHeight'] < minimum_lid_height():
        raise ValueError('Lid hardware/hinge overlaps the top profile: minimum 110 mm')
    L, D, B = (parameters[k] for k in ('RP_Length', 'RP_Depth', 'RP_BaseHeight'))
    offset = parameters['RP_HandleOffset']
    h = B/2 + parameters['RP_HandleHeightOffset']
    centers = [D/2+offset] if handles_per_wall == 1 else [D/4+offset, 3*D/4+offset]
    # Full handle flange (161 x 107), not merely its smaller opening.
    if any(c-80.5 < 40 or c+80.5 > D-40 for c in centers):
        raise ValueError('Handle flange reaches corner/hinge-wall reserve')
    if len(centers) == 2 and centers[1]-centers[0] < 171:
        raise ValueError('Handle flanges overlap or lack assembly clearance')
    if h-53.5 < 40 or h+53.5 > B-40:
        raise ValueError('Handle flange reaches edge profiles or joint')
    for name in ('RP_LatchInset', 'RP_HingeInset'):
        inset = parameters[name]
        if inset < 105 or inset > (L-140)/2:
            raise ValueError('Closure reaches corner or opposite closure')
    return True


def validate_steps(steps, mount_keys):
    seen = set()
    for step in steps:
        if step['key'] in seen or step['mount_key'] not in mount_keys:
            raise ValueError('Duplicate or orphan machining feature')
        seen.add(step['key'])
    return True


_MACHINING_TYPES = frozenset(('cutout', 'pocket', 'drilling', 'profile_trim'))
_GRAPH_FIELDS = frozenset(('schema', 'registry', 'operations', 'target_parts',
                           'executable_template', 'production_approved', 'native_execution'))
_NODE_FIELDS = frozenset(('id', 'type', 'prerequisites', 'owner_mount', 'target_part',
                         'family_id', 'stage_id', 'registry_version'))


def _operation_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,159}', value):
        raise ValueError('A bounded stable operation or part ID is required')
    return value


def _prerequisites(values):
    if not isinstance(values, list) or len(values) > 128:
        raise ValueError('Bounded explicit prerequisites required')
    for value in values:
        _operation_id(value)
    if len(set(values)) != len(values):
        raise ValueError('Duplicate prerequisite')
    return list(values)


def validate_operation_graph(graph):
    """Return a detached, canonical offline graph with dependency/presentation views.

    Dependencies describe resolved placement data, not a physical assembly schedule.
    Target plates/profiles are explicitly supplied available parts, not inferred CAD.
    No contour, frame, fit or native operation is approved by this validation.
    """
    derived = {'topological_order', 'presentation_groups'}
    if (not isinstance(graph, dict) or not _GRAPH_FIELDS <= graph.keys()
            or set(graph) - _GRAPH_FIELDS - derived
            or graph['schema'] != 'rockpro.machining-dependencies/1'
            or graph['registry'] != contract()
            or graph['executable_template'] is not False or graph['production_approved'] is not False
            or graph['native_execution'] != 'NOT RUN'):
        raise ValueError('Pinned offline dependency graph required; no execution or approval')
    targets = graph['target_parts']
    if not isinstance(targets, list) or len(targets) > 2048:
        raise ValueError('Bounded explicit target part inventory required')
    target_map = {}
    for part in targets:
        if (not isinstance(part, dict) or set(part) != {'id', 'family_id'}
                or part['family_id'] not in ('panels', 'profiles')):
            raise ValueError('Machining targets must be explicit panels or profiles')
        identity = _operation_id(part['id'])
        if identity in target_map:
            raise ValueError('Duplicate target part')
        target_map[identity] = part
    operations = graph['operations']
    if not isinstance(operations, list) or not 1 <= len(operations) <= 2048:
        raise ValueError('A bounded nonempty operation list is required')
    nodes = {}
    edge_count = 0
    for node in operations:
        if not isinstance(node, dict) or set(node) != _NODE_FIELDS:
            raise ValueError('Exact dependency node fields required')
        identity = _operation_id(node['id'])
        if identity in nodes:
            raise ValueError('Duplicate operation ID')
        if not isinstance(node['type'], str) or node['type'] not in _MACHINING_TYPES | {'mount'}:
            raise ValueError('Unknown operation type')
        if not isinstance(node['family_id'], str) or node['family_id'] not in graph['registry']['families']:
            raise ValueError('Unknown operation family')
        expected = metadata(node['family_id'])
        if type(node['registry_version']) is not int or any(node[key] != val for key, val in expected.items()):
            raise ValueError('Operation stage differs from part registry')
        prerequisites = _prerequisites(node['prerequisites'])
        edge_count += len(prerequisites)
        if edge_count > 16384:
            raise ValueError('Dependency edge limit exceeded')
        nodes[identity] = node
    if not any(n['type'] == 'mount' for n in operations):
        raise ValueError('At least one explicit owner mount is required')
    for node in operations:
        if any(key not in nodes for key in node['prerequisites']):
            raise ValueError('Orphan prerequisite')
        if node['type'] == 'mount':
            if node['owner_mount'] is not None or node['target_part'] is not None:
                raise ValueError('Mount nodes cannot masquerade as machining')
        else:
            owner_id = _operation_id(node['owner_mount'])
            owner = nodes.get(owner_id)
            if owner is None or owner['type'] != 'mount':
                raise ValueError('Orphan machining owner mount')
            target = target_map.get(_operation_id(node['target_part']))
            if target is None:
                raise ValueError('Orphan machining target part')
            if node['type'] == 'profile_trim' and target['family_id'] != 'profiles':
                raise ValueError('Profile trim needs a profile target')
            if owner_id not in node['prerequisites']:
                raise ValueError('Machining must depend on its owner placement')
            if any(node[key] != owner[key] for key in ('family_id', 'stage_id', 'registry_version')):
                raise ValueError('Machining must share its owner family and stage')
    degree = {key: len(node['prerequisites']) for key, node in nodes.items()}
    followers = {key: [] for key in nodes}
    for key, node in nodes.items():
        for prerequisite in node['prerequisites']:
            followers[prerequisite].append(key)
    ready = [key for key, count in degree.items() if count == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        key = heapq.heappop(ready); order.append(key)
        for following in followers[key]:
            degree[following] -= 1
            if degree[following] == 0:
                heapq.heappush(ready, following)
    if len(order) != len(nodes):
        raise ValueError('Cyclic operation dependencies')
    groups = [dict(stage_id=stage['id'], order=stage['order'],
                   operation_ids=sorted(key for key, node in nodes.items() if node['stage_id'] == stage['id']))
              for stage in graph['registry']['stages']
              if any(node['stage_id'] == stage['id'] for node in operations)]
    for key, expected in (('topological_order', order), ('presentation_groups', groups)):
        if key in graph and graph[key] != expected:
            raise ValueError('Derived dependency order or presentation changed')
    result = copy.deepcopy(graph)
    result['topological_order'], result['presentation_groups'] = order, groups
    return result


def build_operation_graph(mounts, machining, target_parts):
    """Create a pure dependency plan; owner→machining is a required derived edge.

    Mount input: id, family_id, prerequisites. Machining input: id, type,
    owner_mount, target_part, prerequisites. All targets are explicit panels or
    profiles. Existing native machining_step/validate_steps contracts stay intact.
    """
    if (not isinstance(mounts, list) or not 1 <= len(mounts) <= 2048
            or not isinstance(machining, list) or len(mounts)+len(machining) > 2048):
        raise ValueError('Bounded explicit mount and machining lists required')
    nodes = []; by_id = {}; registry = contract()
    for mount in mounts:
        if not isinstance(mount, dict) or set(mount) != {'id', 'family_id', 'prerequisites'}:
            raise ValueError('Exact mount graph fields required')
        identity = _operation_id(mount['id'])
        if identity in by_id:
            raise ValueError('Duplicate operation ID')
        if not isinstance(mount['family_id'], str) or mount['family_id'] not in registry['families']:
            raise ValueError('Unknown operation family')
        node = dict(id=identity, type='mount', owner_mount=None, target_part=None,
                    prerequisites=_prerequisites(mount['prerequisites']), **metadata(mount['family_id']))
        nodes.append(node); by_id[identity] = node
    for step in machining:
        if not isinstance(step, dict) or set(step) != {'id', 'type', 'owner_mount', 'target_part', 'prerequisites'}:
            raise ValueError('Exact machining graph fields required')
        if not isinstance(step['type'], str) or step['type'] not in _MACHINING_TYPES:
            raise ValueError('Unknown machining operation type')
        owner = by_id.get(_operation_id(step['owner_mount']))
        if owner is None:
            raise ValueError('Orphan machining owner mount')
        dependencies = _prerequisites(step['prerequisites'])
        if owner['id'] not in dependencies:
            dependencies.append(owner['id'])
        nodes.append(dict(id=step['id'], type=step['type'], owner_mount=owner['id'], target_part=step['target_part'],
                          prerequisites=dependencies, **metadata(owner['family_id'])))
    return validate_operation_graph(dict(schema='rockpro.machining-dependencies/1', registry=registry,
        operations=nodes, target_parts=copy.deepcopy(target_parts), executable_template=False,
        production_approved=False, native_execution='NOT RUN'))
