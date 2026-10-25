"""Explicit constructor proposals for bound H7159 handles, without CAD writes.

Offsets are world-axis millimetres from parametric side-wall anchors. Decisions
cover the entire declared handle group and do not approve the remaining case.
"""
import copy
import hashlib
import json
import math

from .contracts import ValidationError
from .native_changes import _dimension_values, _expected_handles, observed_pose_changes
from .profile_rules import validate_values

CHOICES=('preserve_absolute','restore_rule','adopt_offset','leave_manual')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def binding_for(baseline,mapping,per_wall):
    return digest(dict(binding=baseline['binding'],file_guid=baseline['file_guid'],mapping=mapping,per_wall=per_wall))


def review_handle_decision(baseline,current,mapping,per_wall,target_values,choice=None,prior_state=None):
    if choice is not None and choice not in CHOICES:raise ValueError('Explicit handle decision required')
    validate_values(target_values)
    original=_expected_handles(baseline,mapping,_dimension_values(baseline),per_wall,baseline['parameters'])
    if observed_pose_changes(original,baseline)['blocked']:
        raise ValidationError('BASELINE_NOT_RULE_BOUND','$.baseline','Initial baseline must be the measured rule-bound handle group')
    expected=_expected_handles(baseline,mapping,_dimension_values(current),per_wall,current['parameters'])
    # This validates GUID, binding, complete stable IDs and native IDs before
    # interpreting any movement as an intentional manual offset.
    observed_pose_changes(expected,current)
    token=binding_for(baseline,mapping,per_wall);ids={r['id'] for r in expected['members']}
    state=dict(schema_version=1,binding_sha256=token,offsets_mm={i:[0.,0.,0.] for i in sorted(ids)},manual_ids=[])
    if prior_state is not None:
        if (not isinstance(prior_state,dict) or set(prior_state)!=set(state) or prior_state['schema_version']!=1 or
            prior_state['binding_sha256']!=token or set(prior_state['offsets_mm'])!=ids or prior_state['manual_ids']):
            raise ValidationError('HANDLE_DECISION_BINDING_CONFLICT','$.prior_state','Only complete bound offset state is replayable')
        for delta in prior_state['offsets_mm'].values():
            if not isinstance(delta,list) or len(delta)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000 for v in delta):raise ValueError('Invalid prior handle offsets')
        state=copy.deepcopy(prior_state)
    expected_with_prior=copy.deepcopy(expected)
    for row in expected_with_prior['members']:
        for j,n in enumerate(state['offsets_mm'][row['id']]):row['matrix_world_mm'][3][j]+=n
    changes=observed_pose_changes(expected_with_prior,current)
    total_changes=observed_pose_changes(expected,current)
    target=_expected_handles(baseline,mapping,target_values,per_wall,{k:f'{v:g} mm' for k,v in target_values.items()})
    actual={r['id']:r for r in current['members']};issues=[]
    if choice=='restore_rule':state['offsets_mm']={i:[0.,0.,0.] for i in sorted(ids)}
    elif choice=='adopt_offset':
        if any(c['rotation_changed'] for c in total_changes['changes']):issues.append('ROTATION_REQUIRES_MANUAL_REVIEW')
        default={r['id']:r for r in expected['members']}
        state['offsets_mm']={i:[actual[i]['matrix_world_mm'][3][j]-default[i]['matrix_world_mm'][3][j] for j in range(3)] for i in sorted(ids)}
    elif choice=='leave_manual':
        state['manual_ids']=[c['id'] for c in changes['changes']]
        issues.append('MANUAL_MEMBERS_REQUIRE_APPROVED_ANCHORS')
    if choice is None and changes['blocked']:issues.append('CONSTRUCTOR_DECISION_REQUIRED')
    for row in target['members']:
        if choice=='preserve_absolute' or row['id'] in state['manual_ids']:
            row['matrix_world_mm']=copy.deepcopy(actual[row['id']]['matrix_world_mm'])
        else:
            for j,n in enumerate(state['offsets_mm'][row['id']]):row['matrix_world_mm'][3][j]+=n
    # Measured H7159 flange fit, same 35 mm edge and 20 mm pair gap policy
    # as handle_rules. Non-catalog rotations cannot reuse these dimensions.
    by_side={'left':[],'right':[]}
    for row in target['members']:
        side=row['id'].split('/')[1];x,y,z=row['matrix_world_mm'][3][:3]
        wall=0 if side=='left' else target_values['RP_Length']
        if abs(x-wall)>.05:issues.append('HANDLE_OFF_MOUNTING_WALL:'+row['id'])
        if not 115.5<=y<=target_values['RP_Depth']-115.5 or not 88.5<=z<=target_values['RP_BaseHeight']-88.5:
            issues.append('HANDLE_NO_EDGE_CLEARANCE:'+row['id'])
        by_side[side].append(y)
    for side,positions in by_side.items():
        positions.sort()
        if any(b-a<181 for a,b in zip(positions,positions[1:])):issues.append('HANDLE_PAIR_NO_CLEARANCE:'+side)
    # Preserve-absolute is deliberately not encoded as parametric offsets: it
    # cannot silently become an approved anchor for a later resize.
    replayable=choice in (None,'restore_rule','adopt_offset') and not issues
    result=dict(scope='Bound H7159 group only',binding_sha256=token,choice=choice,
        blocked=bool(issues),issues=sorted(set(issues)),manual_changes=changes['changes'],
        proposed_members=target['members'],target_values=copy.deepcopy(target_values),
        state=state if replayable else None,applicable_to_parametric_writer=replayable,constructor_choice_is_caller_claim=True,
        cad_changed=False,full_case_approved=False,production_approved=False)
    result['review_sha256']=digest(dict(baseline=baseline,current=current,mapping=mapping,per_wall=per_wall,
        target_values=target_values,choice=choice,prior_state=prior_state,result=result))
    return result


def apply_bound_handle_offsets(scene,api,mapping,per_wall,values,state):
    """Writer primitive for an owned copy only; caller must bind/review evidence.

    No global scene parameters or non-handle parts are changed here. The state
    is a proposal, not authorization; native runners own copy/lock/save checks.
    """
    from .handle_rules import side_handle_rules
    from .profile_rules import expression as qualify
    rules=side_handle_rules(values,per_wall);by_id={r['logical_id']:r['id'] for r in mapping}
    if set(by_id)!={r['id'] for r in rules} or set(state['offsets_mm'])!=set(by_id) or state['manual_ids']:
        raise ValueError('Complete bound parametric offset state required')
    utility=scene.QueryInterface(api.IZSceneDocUtility);prepared=[]
    for rule in rules:
        element=utility.GetElementById(by_id[rule['id']]).QueryInterface(api.IZSceneElement)
        delta=state['offsets_mm'][rule['id']]
        if len(delta)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000 for v in delta):raise ValueError('Invalid offset')
        matrix=element.GetTransformToGlobal()
        if any(abs(matrix.GetValue(i,j)-rule['rotation'][i][j])>1e-7 for i in range(3) for j in range(3)):
            raise ValueError('Translation writer does not reset a manually rotated handle')
        prepared.append((element,rule,delta))
    for element,rule,delta in prepared:
        for j,position_expression in enumerate(rule['position']):
            element.PositionTransformComponentExpression[j]=qualify(f'({position_expression}) + ({delta[j]:.9f} mm)')
        element.ForceSetupParameterExpression()
    scene.Update()
