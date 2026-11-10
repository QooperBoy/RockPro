"""Mount-owned machining in millimetres; geometry comes from pinned CAD features.

Row-vector transforms match ICAPI. A bounding box is used for clearance only,
never as a substitute for the catalog's cutting contour.
"""
import math
from .profile_rules import value
from ..part_registry import metadata

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
