"""ROC-40: read-only evidence of manual poses for explicitly watched occurrences.

This is a preflight guard, not approval, three-way merge or an editable recipe.
Only occurrences declared in the snapshot are covered. Parameter changes need
a new expected plan; they are never silently classified as manual member moves.
"""
import copy
import re
from .contracts import ValidationError
from .native_reader import validate_matrix
from .handle_rules import side_handle_rules
from .profile_rules import value, validate_values


def capture_selected_poses(document, api, selection, binding):
    """Read an owned or user document without writing, opening or activating it."""
    scene = document.QueryInterface(api.IZSceneDoc)
    utility = scene.QueryInterface(api.IZSceneDocUtility)
    rows = []
    for item in selection:
        element = utility.GetElementById(item['node_id'])
        # A missing/unknown occurrence is a read error, never an inferred deletion.
        if not element or int(element.Id) != item['node_id']:
            raise ValidationError('NATIVE_MEMBER_MISSING', '$.selection', 'Cannot read the bound occurrence')
        matrix = element.QueryInterface(api.IZSceneElement).GetTransformToGlobal()
        pose = [[float(matrix.GetValue(i, j)) for j in range(4)] for i in range(4)]
        for j in range(3):
            pose[3][j] *= 1000
        validate_matrix(pose)
        rows.append(dict(id=item['id'], node_id=item['node_id'], group_id=item['group_id'],
                         matrix_world_mm=pose))
    return dict(binding=copy.deepcopy(binding), file_guid=str(document.FileGUID),
                parameters={name: str(scene.ParameterMgr.GetParameterByName(name).Expression)
                            for name in binding['parameter_names']}, members=rows)


def observed_pose_changes(baseline, current, tolerance_mm=.05, rotation_tolerance=1e-7):
    if (baseline['binding'] != current['binding'] or baseline['file_guid'] != current['file_guid']):
        raise ValidationError('PREVIOUS_PLAN_CONFLICT', '$.binding', 'Snapshots belong to different bound documents')
    if baseline['parameters'] != current['parameters']:
        raise ValidationError('NATIVE_REPLAN_REQUIRED', '$.parameters', 'Regenerate expected poses before auditing a resize')
    def indexed(snapshot):
        result = {}
        native_ids = set()
        for row in snapshot['members']:
            validate_matrix(row['matrix_world_mm'])
            if row['id'] in result or row['node_id'] in native_ids:
                raise ValidationError('DUPLICATE_ID', '$.members', 'Ambiguous occurrence identity')
            result[row['id']] = row
            native_ids.add(row['node_id'])
        return result
    old, new = indexed(baseline), indexed(current)
    if set(old) != set(new):
        raise ValidationError('NATIVE_MEMBER_SET_CONFLICT', '$.members', 'Watched set changed; do not infer additions/deletions')
    changes = []
    for identity, before in old.items():
        after = new[identity]
        if (before['node_id'], before['group_id']) != (after['node_id'], after['group_id']):
            raise ValidationError('PREVIOUS_PLAN_CONFLICT', '$.members', 'Bound occurrence mapping changed')
        a, b = before['matrix_world_mm'], after['matrix_world_mm']
        delta = [b[3][j]-a[3][j] for j in range(3)]
        rotation_error = max(abs(a[i][j]-b[i][j]) for i in range(3) for j in range(3))
        if max(abs(x) for x in delta) > tolerance_mm or rotation_error > rotation_tolerance:
            changes.append(dict(kind='move', id=identity, group_id=before['group_id'],
                                delta=delta, rotation_changed=rotation_error > rotation_tolerance,
                                code='SYMMETRY_MANUAL_CONFLICT'))
    return dict(status='conflict' if changes else 'unchanged', blocked=bool(changes),
                changes=changes, watched_members=len(old), automatic_changes_applied=False)


def guard_native_changes(baseline, current):
    result = observed_pose_changes(baseline, current)
    if result['blocked']:
        raise ValidationError('SYMMETRY_MANUAL_CONFLICT', '$.native_changes',
                              'Manual member movement requires a constructor decision for the group')
    return result


def _dimension_values(snapshot):
    values={}
    for name,text in snapshot['parameters'].items():
        match=re.fullmatch(r'\s*([+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*mm\s*',text)
        if not match:
            raise ValidationError('NATIVE_REPLAN_REQUIRED','$.parameters',
                                  'Expected explicit millimetres; do not guess a CAD expression')
        values[name]=float(match.group(1).replace(',','.'))
    validate_values(values)
    return values


def _expected_handles(reference, mapping, values, per_wall, parameters):
    rules=side_handle_rules(values,per_wall)
    by_id={row['logical_id']:row for row in mapping}
    if len(by_id)!=len(mapping) or set(by_id)!={r['id'] for r in rules}:
        raise ValidationError('NATIVE_MEMBER_SET_CONFLICT','$.mapping','Incomplete or duplicate handle mapping')
    expected=copy.deepcopy(reference)
    expected['parameters']=copy.deepcopy(parameters)
    expected['members']=[]
    for rule in rules:
        matrix=[list(row)+[0.] for row in rule['rotation']]
        matrix.append([value(s,values) for s in rule['position']]+[1.])
        expected['members'].append(dict(id=rule['id'],node_id=by_id[rule['id']]['id'],
                                        group_id='handles',matrix_world_mm=matrix))
    return expected


def review_handle_update(baseline,current,mapping,per_wall,target_values):
    """Compare baseline, measured CAD and a proposed handle layout without writes.

    Native resize is compared with regenerated expectations at current dimensions.
    This covers bound handles only; it cannot authorize a full-case operation.
    """
    old_values=_dimension_values(baseline)
    current_values=_dimension_values(current)
    validate_values(target_values)
    expected_old=_expected_handles(baseline,mapping,old_values,per_wall,baseline['parameters'])
    guard_native_changes(expected_old,baseline)
    expected_current=_expected_handles(baseline,mapping,current_values,per_wall,current['parameters'])
    observed=observed_pose_changes(expected_current,current)
    target=_expected_handles(baseline,mapping,target_values,per_wall,
                             {k:f'{v:g} mm' for k,v in target_values.items()})
    return dict(scope='Explicitly bound handles only',blocked=observed['blocked'],
                current_dimensions_mm=current_values,target_dimensions_mm=target_values,
                parameter_resize_observed=old_values!=current_values,
                manual_changes=observed['changes'],watched_handles=observed['watched_members'],
                proposed_members=target['members'],automatic_changes_applied=False,
                full_case_approved=False)


def guard_handle_update(baseline,current,mapping,per_wall,target_values):
    result=review_handle_update(baseline,current,mapping,per_wall,target_values)
    if result['blocked']:
        raise ValidationError('SYMMETRY_MANUAL_CONFLICT','$.native_changes',
                              'Manual handle change survives resize; constructor decision required')
    return result
