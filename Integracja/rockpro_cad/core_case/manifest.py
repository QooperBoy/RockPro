"""ROC-42 read-only source-bound inventory accounting, never a CAD writer.

UUIDs are RockPro proposals persisted in identity_map. CAD IDs and tree paths
identify evidence within one exact inventory only; they imply no cross-edit ID.
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import copy
import hashlib
import json
import math
from pathlib import Path
import uuid


SCHEMA_VERSION = 1
CLASSIFICATIONS = {'structural', 'physical', 'reference', 'empty', 'unresolved'}
POLICIES = {'rebuild', 'rigid_move', 'manual_preserve', 'replace', 'structural', 'exclude_explicit'}
FAMILIES = {
    'konstrukcja': ('panels', 'rebuild'), 'EG-0500_1': ('closure_profile_base', 'rebuild'),
    'EG-0500_2': ('closure_profile_lid', 'rebuild'), 'EG-0113': ('edge_profiles', 'rebuild'),
    '410429': ('corners', 'rigid_move'), 'B1930': ('braces', 'rigid_move'),
    'B1121': ('braces', 'rigid_move'), 'H2026': ('corner_handles', 'rigid_move'),
    'H7159': ('handles', 'rigid_move'), '17251S': ('latch_base', 'rigid_move'),
    '17251S_1': ('latch_lid', 'rigid_move'), '270836': ('hinge_base', 'rigid_move'),
    '270836_góra': ('hinge_lid', 'rigid_move'), 'PN - W0968Z': ('stacking_sockets', 'rigid_move'),
    'koła': ('wheels_and_pads', 'manual_preserve'), 'Srodek': ('interior', 'manual_preserve'),
    'Zespół1': ('reference_import', 'manual_preserve'),
    'Część2648': ('unresolved_custom', 'manual_preserve'), '2643': ('empty_placeholder', 'exclude_explicit'),
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _key(path):
    if not isinstance(path, list) or any(type(v) is not int or v < 0 for v in path):
        raise ValueError('invalid source occurrence_path')
    return '/'.join(map(str, path)) or 'root'


def _rows(inventory):
    if not isinstance(inventory, dict) or inventory.get('scope') != 'assembly_part_hierarchy':
        raise ValueError('inventory must be an assembly_part_hierarchy report')
    rows = inventory.get('rows')
    if not isinstance(rows, list) or not rows:
        raise ValueError('inventory rows required')
    keys = [_key(r.get('occurrence_path')) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate source occurrence_path')
    return rows


@dataclass(frozen=True)
class ManifestDiagnostic:
    code: str
    path: str
    message: str
    severity: str = 'blocker'

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ManifestValidation:
    valid: bool
    production_ready: bool
    diagnostics: tuple
    summary: dict

    def as_dict(self):
        return dict(valid=self.valid, production_ready=self.production_ready,
            diagnostics=[d.as_dict() for d in self.diagnostics], summary=self.summary)


def build_manifest(inventory, identity_map=None, *, inventory_sha256=None):
    """Account all rows with conservative candidates; reuse IDs only exact-source.

    Persist the returned identity_map to repeat this operation. A changed report
    requires explicit reconciliation: this builder never matches identity by name.
    inventory_sha256 is the optional byte hash of the original JSON file.
    """
    rows = _rows(inventory)
    digest = _digest(inventory)
    binding = dict(inventory_content_sha256=digest,
        source=copy.deepcopy(inventory.get('source')),
        cad_document=copy.deepcopy(inventory.get('cad_document')))
    if identity_map is not None:
        if not isinstance(identity_map, dict) or identity_map.get('source_binding') != binding:
            raise ValueError('identity map belongs to another source inventory; reconcile explicitly')
        ids = copy.deepcopy(identity_map.get('ids', {}))
    else:
        ids = {}

    def ident(key):
        if key not in ids:
            if identity_map is not None:
                raise ValueError('incomplete identity map; reconcile explicitly')
            ids[key] = 'rp-' + str(uuid.uuid4())
        return ids[key]

    by_path = {_key(r['occurrence_path']): r for r in rows}
    definitions, occurrences, groups = [], [], {}
    for row in rows:
        path = row['occurrence_path']
        key = _key(path)
        group_row = by_path.get(_key(path[:2])) if len(path) >= 2 else None
        family = group_row.get('name') if group_row else None
        section = by_path.get(_key(path[:1]), {}).get('name') if path else 'scene'
        role, policy = FAMILIES.get(family, ('unresolved', 'manual_preserve'))
        kind = row.get('kind')
        if kind == 'scene' or (kind == 'assembly' and row.get('children') != 0):
            classification = 'structural'
            effective_policy = 'structural'
        elif kind == 'assembly' and row.get('children') == 0:
            classification, effective_policy = 'empty', 'exclude_explicit'
        elif kind == 'part':
            classification = ('reference' if role == 'reference_import' else
                              'unresolved' if role in ('unresolved', 'unresolved_custom', 'wheels_and_pads') else 'physical')
            effective_policy = policy
        else:
            classification, effective_policy = 'unresolved', 'manual_preserve'
        definition_id = ident('definition:' + key)
        # No unproven merging of the multiple components of a catalog assembly.
        definitions.append(dict(definition_id=definition_id, catalog_candidate=family,
            identity_status='candidate_pending_confirmation', purchase_material=None,
            approved_for_automatic_placement=False, mounting_rule_status='unapproved',
            geometry_status='not_validated', source_evidence='inventory_node_only'))
        group_id = None
        if group_row:
            group_key = json.dumps([section, family], ensure_ascii=False)
            if group_key not in groups:
                group_id = ident('group:' + group_key)
                groups[group_key] = dict(symmetry_group_id=group_id, section_candidate=section,
                    family_candidate=family, semantic_role=role, status='pending_confirmation',
                    frame_ref='case.closed', wall_frame_ref=None,
                    frame_selection_status='pending_confirmation', mode='pending_confirmation',
                    members=[], rule_status='unapproved', exception_approval=None,
                    position_evidence_status='not_available')
            group = groups[group_key]
            group_id = group['symmetry_group_id']
            group['members'].append(ident('occurrence:' + key))
        occurrences.append(dict(rockpro_id=ident('occurrence:' + key),
            definition_id=definition_id, role_id=ident('role:' + key),
            semantic_role=role if group_row else 'assembly_structure',
            role_status='candidate_pending_confirmation', classification=classification,
            policy=effective_policy, policy_status='pending_confirmation',
            policy_reason='empty inventory assembly is not a purchase item' if classification == 'empty'
                else 'source accounting proposal; constructor confirmation required',
            parent_id=ident('occurrence:' + _key(path[:-1])) if path else None,
            symmetry_group_id=group_id, physical_quantity_approved=False,
            source_group_owner_id=ident('occurrence:' + _key(path[:2])) if group_row else None,
            inventory_function='geometry_component' if len(path) > 2 else
                'aggregate_candidate' if group_row and kind == 'assembly' and row.get('children') else
                'source_structure' if classification == 'structural' else 'occurrence_candidate',
            purchase_quantity=None,
            source_ref=dict(occurrence_path=copy.deepcopy(path), cad_id=row.get('id'),
                cad_name=row.get('name'), kind=kind, children=row.get('children'),
                material_cad_raw=row.get('material_cad_raw'),
                bounding_box=copy.deepcopy(row.get('bounding_box')), errors=copy.deepcopy(row.get('errors', []))),
            world_transform=dict(status='not_available', matrix=None)))
    pairings = []
    for name, roles, match in [('closures', {'latch_base', 'latch_lid'}, 'closed_XYZ'),
            ('hinges', {'hinge_base', 'hinge_lid'}, 'closed_XYZ'),
            ('closure_profiles', {'closure_profile_base', 'closure_profile_lid'}, 'closed_interface'),
            ('wheels_sockets', {'wheels_and_pads', 'stacking_sockets'}, 'closed_XY')]:
        candidates = [g for g in groups.values() if g['semantic_role'] in roles]
        if candidates:
            pairings.append(dict(pairing_id=ident('pair:' + name), kind=name,
                status='pending_confirmation', group_ids=[g['symmetry_group_id'] for g in candidates],
                required_roles=sorted(roles), matching_rule=match, frame_ref='case.closed',
                pairs=[], position_evidence_status='not_available', approved=False))
    return dict(schema_version=SCHEMA_VERSION, manifest_kind='source_bound_inventory',
        manifest_stage='inventory_draft', runtime_template_compatible=False,
        manifest_id=ident('manifest'), units='mm', production_approved=False,
        identity_status='proposed_ids_persisted_source_bound_only',
        source_binding=binding, inventory_file_sha256=inventory_sha256,
        inventory_evidence=dict(node_count=len(rows), scope=inventory['scope'],
            partial=inventory.get('partial'), limit_reasons=copy.deepcopy(inventory.get('limit_reasons', [])),
            errors=copy.deepcopy(inventory.get('errors', [])),
            operation_log_status=inventory.get('operation_log_status'),
            operation_log=inventory.get('operation_log'), reader_code_sha256=inventory.get('reader_code_sha256')),
        identity_map=dict(source_binding=copy.deepcopy(binding), ids=ids),
        frames=[dict(frame_id='case.closed', kind='case', status='pending_confirmation',
            origin=None, rotation=None, evidence='world positions not present in source inventory')],
        definitions=definitions, occurrences=occurrences, symmetry_groups=list(groups.values()), pairings=pairings,
        purchase_bom_status='not_available_no_approved_physical_quantities')


def _bbox_valid(box):
    if not isinstance(box, dict) or box.get('valid') is not True or box.get('unit') != 'mm' or box.get('frame') != 'part_local':
        return False
    values = [box.get(k) for k in ('minimum', 'maximum', 'size')]
    if any(not isinstance(v, list) or len(v) != 3 or any(type(x) not in (int, float)
            or not math.isfinite(x) for x in v) for v in values):
        return False
    lo, hi, size = values
    return all(s > 0 and hi[i] > lo[i] and abs(hi[i]-lo[i]-s) <= 1e-6 for i, s in enumerate(size))


def _validate_manifest(manifest, inventory=None):
    """Return separate schema/accounting validity and production readiness.

    Pending truthful proposals are structurally valid but block readiness.
    A diagnostic severity of error denotes invalid or contradictory data.
    """
    diagnostics = []
    def add(code, path, message, severity='blocker'):
        diagnostics.append(ManifestDiagnostic(code, path, message, severity))
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest.get('schema_version') != SCHEMA_VERSION or manifest.get('manifest_kind') != 'source_bound_inventory':
        add('INVALID_MANIFEST', '$', 'unsupported manifest schema or kind', 'error')
        return ManifestValidation(False, False, tuple(diagnostics), {})
    if manifest.get('units') != 'mm':
        add('UNITS_MISMATCH', 'units', 'manifest units must be mm', 'error')
    if manifest.get('manifest_stage') != 'inventory_draft' or manifest.get('runtime_template_compatible') is not False:
        add('INVALID_MANIFEST_STAGE', '$', 'source inventory remains an unapproved draft', 'error')
    add('MOUNTING_EVIDENCE_NOT_IMPLEMENTED', '$',
        'inventory accounting has no measured mounting geometry or production approval workflow')
    fields = ('definitions', 'occurrences', 'symmetry_groups', 'pairings', 'frames')
    if any(not isinstance(manifest.get(k), list) or any(not isinstance(x, dict) for x in manifest[k]) for k in fields):
        add('INVALID_MANIFEST', '$', 'manifest collections must be lists of objects', 'error')
        return ManifestValidation(False, False, tuple(diagnostics), {})
    occurrences, definitions, groups = (manifest[k] for k in ('occurrences', 'definitions', 'symmetry_groups'))
    evidence = manifest.get('inventory_evidence', {})
    binding = manifest.get('source_binding', {})
    if not occurrences or len(occurrences) != evidence.get('node_count'):
        add('INVENTORY_COVERAGE', 'occurrences', 'every source row must be accounted once', 'error')
    for items, field in [(occurrences, 'rockpro_id'), (occurrences, 'role_id'),
            (definitions, 'definition_id'), (groups, 'symmetry_group_id'), (manifest['pairings'], 'pairing_id')]:
        values = [x.get(field) for x in items]
        if any(not isinstance(v, str) or not v for v in values) or len(values) != len(set(values)):
            add('DUPLICATE_ID', field, 'IDs must be nonempty and unique', 'error')
    oid = {o.get('rockpro_id') for o in occurrences}
    did = {d.get('definition_id') for d in definitions}
    gid = {g.get('symmetry_group_id') for g in groups}
    frame_ids = {f.get('frame_id') for f in manifest['frames']}
    if len(manifest['frames']) != 1 or frame_ids != {'case.closed'} or any(
            f.get('status') != 'pending_confirmation' or f.get('origin') is not None or f.get('rotation') is not None
            for f in manifest['frames']):
        add('UNSUPPORTED_FRAME_CLAIM', 'frames', 'inventory draft cannot assert measured or approved frames', 'error')
    if Counter(o.get('definition_id') for o in occurrences) != Counter(d.get('definition_id') for d in definitions):
        add('DEFINITION_MEMBERSHIP', 'definitions', 'draft definitions must account for exactly one source node each', 'error')
    mapping = manifest.get('identity_map', {})
    if mapping.get('source_binding') != binding:
        add('IDENTITY_MAP_MISMATCH', 'identity_map', 'identity map must have the same source binding', 'error')
    ids = mapping.get('ids', {})
    for map_key, value in ids.items():
        try:
            if not isinstance(value, str) or not value.startswith('rp-'):
                raise ValueError()
            uuid.UUID(value[3:])
        except (ValueError, AttributeError):
            add('INVALID_ROCKPRO_ID', 'identity_map.ids', 'RockPro identities must be persisted UUID proposals', 'error')
            break
    if len(ids.values()) != len(set(ids.values())):
        add('DUPLICATE_ID', 'identity_map.ids', 'different roles, definitions and occurrences need distinct IDs', 'error')
    source_paths = []
    expected_members = defaultdict(set)
    path_to_id = {}
    for i, o in enumerate(occurrences):
        p = f'occurrences[{i}]'
        ref = o.get('source_ref', {})
        try:
            key = _key(ref.get('occurrence_path'))
        except (ValueError, AttributeError):
            add('SOURCE_REFERENCE_INVALID', p, 'source occurrence path required', 'error')
            continue
        source_paths.append(key)
        path_to_id[key] = o.get('rockpro_id')
        if any(o.get(field) != ids.get(prefix + key) for field, prefix in
               [('rockpro_id', 'occurrence:'), ('definition_id', 'definition:'), ('role_id', 'role:')]):
            add('IDENTITY_MAP_MISMATCH', p, 'IDs disagree with persisted source mapping', 'error')
        if o.get('classification') not in CLASSIFICATIONS or o.get('policy') not in POLICIES:
            add('INVALID_CLASSIFICATION_POLICY', p, 'explicit classification and policy required', 'error')
        if ((ref.get('kind') == 'part' and (o.get('classification') not in {'physical', 'reference', 'unresolved'}
                or o.get('policy') in {'exclude_explicit', 'structural'}))
                or (ref.get('kind') == 'scene' and (o.get('classification') != 'structural' or o.get('policy') != 'structural'))
                or (ref.get('kind') == 'assembly' and ref.get('children') != 0
                    and (o.get('classification') != 'structural' or o.get('policy') != 'structural'))):
            add('INVALID_SOURCE_CLASSIFICATION', p, 'classification/policy contradict source node kind', 'error')
        if o.get('physical_quantity_approved') is not False or o.get('purchase_quantity') is not None:
            add('UNSUPPORTED_PURCHASE_CLAIM', p, 'draft inventory has no approved purchase quantities', 'error')
        if o.get('role_status') != 'candidate_pending_confirmation' or o.get('policy_status') != 'pending_confirmation':
            add('UNSUPPORTED_APPROVAL_CLAIM', p, 'draft mapping has no approval workflow', 'error')
        if o.get('world_transform') != {'status': 'not_available', 'matrix': None}:
            add('UNSUPPORTED_POSITION_CLAIM', p, 'inventory does not supply measured world transforms', 'error')
        if o.get('definition_id') not in did:
            add('DEFINITION_MISSING', p, 'definition ID does not exist', 'error')
        if ref.get('kind') == 'assembly' and ref.get('children') == 0 and (o.get('classification') != 'empty' or o.get('policy') != 'exclude_explicit' or o.get('physical_quantity_approved') is not False):
            add('EMPTY_ASSEMBLY_PHYSICAL', p, 'empty assembly cannot count as a physical item', 'error')
        group = o.get('symmetry_group_id')
        if len(ref['occurrence_path']) >= 2 and group not in gid:
            add('SYMMETRY_GROUP_MISSING', p, 'inventory group must have explicit symmetry accounting', 'error')
        if group:
            expected_members[group].add(o.get('rockpro_id'))
        if o.get('classification') == 'unresolved':
            add('UNRESOLVED_PART', p, 'role or product identity unresolved')
        if o.get('semantic_role') == 'wheels_and_pads':
            add('WHEEL_SKU_UNRESOLVED', p, 'wheel SKU, capacity and mating geometry unconfirmed')
        if o.get('semantic_role') == 'reference_import':
            add('IMPORT_IDENTITY_UNRESOLVED', p, 'reference import identity and scope unconfirmed')
        if ref.get('kind') == 'part' and not _bbox_valid(ref.get('bounding_box')):
            add('INVALID_BOUNDING_BOX', p, 'missing/invalid local AABB; no geometry approval')
        if o.get('policy_status') != 'approved' or o.get('role_status') != 'approved':
            add('MAPPING_PENDING', p, 'role and policy require constructor evidence')
        if o.get('world_transform', {}).get('status') != 'measured':
            add('WORLD_POSITION_UNAVAILABLE', p, 'source inventory has no measured world transform')
    if len(source_paths) != len(set(source_paths)):
        add('DUPLICATE_SOURCE_NODE', 'occurrences', 'source node accounted multiple times', 'error')
    child_counts = Counter(tuple(o['source_ref']['occurrence_path'][:-1]) for o in occurrences
        if isinstance(o.get('source_ref', {}).get('occurrence_path'), list) and o['source_ref']['occurrence_path'])
    for i, o in enumerate(occurrences):
        ref = o.get('source_ref', {})
        path = ref.get('occurrence_path')
        if not isinstance(path, list):
            continue
        if (not path and o.get('parent_id') is not None) or (path and o.get('parent_id') != path_to_id.get(_key(path[:-1]))):
            add('PARENT_GRAPH_INVALID', f'occurrences[{i}]', 'parent must match source hierarchy', 'error')
        if ref.get('kind') in ('scene', 'assembly'):
            count = child_counts[tuple(path)]
            if type(ref.get('children')) is not int or count != ref['children']:
                add('CHILD_COUNT_MISMATCH', f'occurrences[{i}]', 'inventory hierarchy is truncated or inconsistent')
    for i, g in enumerate(groups):
        p = f'symmetry_groups[{i}]'
        group_key = json.dumps([g.get('section_candidate'), g.get('family_candidate')], ensure_ascii=False)
        if g.get('symmetry_group_id') != ids.get('group:' + group_key):
            add('IDENTITY_MAP_MISMATCH', p, 'group ID differs from persisted source mapping', 'error')
        members = g.get('members', [])
        if not isinstance(members, list) or len(members) != len(set(members)) or set(members) != expected_members[g.get('symmetry_group_id')]:
            add('GROUP_MEMBERSHIP', p, 'symmetry membership must match occurrence assignments exactly', 'error')
        if g.get('frame_ref') not in frame_ids:
            add('FRAME_MISSING', p, 'group requires explicit case/wall frame', 'error')
        if (g.get('status') != 'pending_confirmation' or g.get('rule_status') != 'unapproved'
                or g.get('frame_selection_status') != 'pending_confirmation' or g.get('wall_frame_ref') is not None
                or g.get('mode') != 'pending_confirmation' or g.get('exception_approval') is not None):
            add('UNSUPPORTED_APPROVAL_CLAIM', p, 'draft symmetry cannot claim measured geometry or approval', 'error')
        if g.get('status') != 'approved' or g.get('rule_status') != 'approved' or g.get('frame_selection_status') != 'approved':
            add('SYMMETRY_PENDING', p, 'group symmetry, frame and mounting rules need confirmation')
    for i, pair in enumerate(manifest['pairings']):
        p = f'pairings[{i}]'
        if pair.get('pairing_id') != ids.get('pair:' + str(pair.get('kind'))):
            add('IDENTITY_MAP_MISMATCH', p, 'pairing ID differs from persisted source mapping', 'error')
        if not isinstance(pair.get('group_ids'), list) or any(g not in gid for g in pair.get('group_ids', [])):
            add('PAIRING_MEMBER_MISSING', p, 'pair candidate references missing groups', 'error')
        if pair.get('status') != 'approved' or pair.get('approved') is not True or not pair.get('pairs'):
            add('PAIRING_PENDING', p, 'candidate groups are not measured and approved physical pairs')
        if pair.get('status') != 'pending_confirmation' or pair.get('approved') is not False or pair.get('pairs') != []:
            add('UNSUPPORTED_APPROVAL_CLAIM', p, 'draft has no measured occurrence pairs', 'error')
    roles = {g.get('semantic_role') for g in groups}
    required_pairs = {'closures': {'latch_base', 'latch_lid'}, 'hinges': {'hinge_base', 'hinge_lid'},
        'closure_profiles': {'closure_profile_base', 'closure_profile_lid'},
        'wheels_sockets': {'wheels_and_pads', 'stacking_sockets'}}
    for kind, pair_roles in required_pairs.items():
        matches = [p for p in manifest['pairings'] if p.get('kind') == kind]
        if roles & pair_roles and not matches:
            add('PAIRING_MISSING', 'pairings', f'{kind} requires explicit pairing status', 'error')
        expected = {g.get('symmetry_group_id') for g in groups if g.get('semantic_role') in pair_roles}
        for pair in matches:
            actual = pair.get('group_ids', [])
            if len(matches) != 1 or not isinstance(actual, list) or len(actual) != len(set(actual)) or set(actual) != expected or pair.get('required_roles') != sorted(pair_roles):
                add('PAIRING_MEMBERSHIP', 'pairings', f'{kind} must include exactly its candidate groups and roles', 'error')
    if any(p.get('kind') not in required_pairs for p in manifest['pairings']):
        add('PAIRING_MEMBERSHIP', 'pairings', 'unsupported pairing kind', 'error')
    for i, d in enumerate(definitions):
        if (d.get('approved_for_automatic_placement') is not False or d.get('mounting_rule_status') != 'unapproved'
                or d.get('geometry_status') != 'not_validated' or d.get('purchase_material') is not None):
            add('UNSUPPORTED_APPROVAL_CLAIM', f'definitions[{i}]', 'catalog candidate cannot claim geometry/material approval', 'error')
        if d.get('approved_for_automatic_placement') is not True or d.get('mounting_rule_status') != 'approved' or d.get('geometry_status') != 'validated':
            add('DEFINITION_UNAPPROVED', f'definitions[{i}]', 'catalog candidate is not approved mounting geometry')
    source = binding.get('source') or {}
    if not source.get('sha256_before') or source.get('sha256_before') != source.get('sha256_after') or source.get('unchanged') is not True:
        add('SOURCE_INTEGRITY_UNPROVEN', 'source_binding', 'equal before/after source hashes required')
    cad = binding.get('cad_document') or {}
    if any(cad.get(phase, {}).get('modified') is not False for phase in ('before', 'after')):
        add('SOURCE_DOCUMENT_MODIFIED', 'source_binding.cad_document', 'disk hash does not prove the live document state')
    if not cad.get('before', {}).get('file_guid'):
        add('SOURCE_IDENTITY_UNPROVEN', 'source_binding', 'source document GUID missing')
    if evidence.get('partial') is not False or evidence.get('limit_reasons') or evidence.get('errors'):
        add('SOURCE_INVENTORY_PARTIAL', 'inventory_evidence', 'source report partial/errors/limits retained')
    if inventory is not None:
        try:
            rows = _rows(inventory)
            if _digest(inventory) != binding.get('inventory_content_sha256'):
                add('SOURCE_BINDING_MISMATCH', 'source_binding', 'manifest belongs to another inventory', 'error')
            if binding.get('source') != inventory.get('source') or binding.get('cad_document') != inventory.get('cad_document'):
                add('SOURCE_BINDING_MISMATCH', 'source_binding', 'source provenance differs from bound inventory', 'error')
            expected_evidence = dict(node_count=len(rows), scope=inventory['scope'], partial=inventory.get('partial'),
                limit_reasons=inventory.get('limit_reasons', []), errors=inventory.get('errors', []),
                operation_log_status=inventory.get('operation_log_status'), operation_log=inventory.get('operation_log'),
                reader_code_sha256=inventory.get('reader_code_sha256'))
            if evidence != expected_evidence:
                add('SOURCE_EVIDENCE_MISMATCH', 'inventory_evidence', 'source diagnostics/provenance changed', 'error')
            if set(source_paths) != {_key(r['occurrence_path']) for r in rows}:
                add('INVENTORY_COVERAGE', 'occurrences', 'manifest omits or adds source nodes', 'error')
            source_rows = {_key(r['occurrence_path']): r for r in rows}
            for i, o in enumerate(occurrences):
                ref = o.get('source_ref', {})
                try:
                    row = source_rows.get(_key(ref.get('occurrence_path')))
                except ValueError:
                    continue
                if row and any(ref.get(k) != row.get(source_key) for k, source_key in
                    [('cad_id', 'id'), ('cad_name', 'name'), ('kind', 'kind'), ('children', 'children'),
                     ('material_cad_raw', 'material_cad_raw'), ('bounding_box', 'bounding_box')]):
                    add('SOURCE_EVIDENCE_MISMATCH', f'occurrences[{i}]', 'source evidence was changed', 'error')
        except (ValueError, TypeError):
            add('INVALID_INVENTORY', 'inventory', 'invalid input inventory', 'error')
    if manifest.get('production_approved') is True and diagnostics:
        add('FALSE_PRODUCTION_APPROVAL', 'production_approved', 'manifest has unresolved readiness blockers', 'error')
    valid = not any(d.severity == 'error' for d in diagnostics)
    return ManifestValidation(valid, valid and not diagnostics, tuple(diagnostics),
        dict(accounted_nodes=len(occurrences), classification_counts=dict(Counter(o.get('classification') for o in occurrences)),
             symmetry_group_count=len(groups), purchase_quantity=None,
             accounting_complete=valid and not any(d.code == 'CHILD_COUNT_MISMATCH' for d in diagnostics),
             current_cad_state='not_verified_offline_cached_inventory'))


def validate_manifest(manifest, inventory=None):
    """Fail closed on malformed serialized fields; never leak a parser crash."""
    try:
        return _validate_manifest(manifest, inventory)
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return ManifestValidation(False, False,
            (ManifestDiagnostic('INVALID_MANIFEST', '$', 'malformed nested manifest data', 'error'),), {})


def read_manifest(path):
    """Read a local artifact; callers decide whether it is valid/ready."""
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON value')))


def write_manifest_exclusive(path, manifest):
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(payload)


def main(argv=None):
    """JSON-only CLI: no adapter, CAD connection, database or overwrite."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--identity-map', help='previous manifest containing a source-bound identity_map')
    args = parser.parse_args(argv)
    try:
        raw = Path(args.inventory).read_bytes()
        inventory = json.loads(raw.decode('utf-8'))
        prior = read_manifest(args.identity_map)['identity_map'] if args.identity_map else None
        manifest = build_manifest(inventory, prior, inventory_sha256=hashlib.sha256(raw).hexdigest())
        validation = validate_manifest(manifest, inventory)
        write_manifest_exclusive(args.output, manifest)
        print(json.dumps(validation.as_dict(), ensure_ascii=True, allow_nan=False))
        return 0 if validation.production_ready else 2 if validation.valid else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps(dict(status='error', code=type(exc).__name__, message=str(exc)), ensure_ascii=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
