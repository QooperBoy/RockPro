"""Revision-bound Studio to native-CAD planning; never treats a mesh as a CAD asset.

The first increment accounts for the complete draft and records concrete missing
bindings. Native adapters are enabled only after their full contract is implemented.
"""
import copy
import hashlib
import json
import re
import uuid
from pathlib import Path

from . import configurator, studio_parts
from .mcp import project_store
from .part_registry import contract

SCHEMA = 'rockpro.studio-cad-plan/1'
# Candidate recipes exist in these modules. They do not yet bind Studio UVN
# frames to a particular native source revision and therefore cannot enable CAD.
RECIPES = {
    'H7159': dict(revision='t1-fit-v2', operations=['through_cut', 'flange_pocket'],
                  reference='docs/T1_MACHINING_PROTOTYPE.md'),
    '17251S': dict(revision='t1-fit-v2', operations=['panel_cut', 'profile_relief'],
                  reference='docs/T1_MACHINING_PROTOTYPE.md'),
    '270836': dict(revision='t1-fit-v2', operations=['panel_cut', 'profile_relief'],
                  reference='docs/T1_MACHINING_PROTOTYPE.md'),
    '27095': dict(revision='27095-opening-v1', operations=['panel_cut', 'profile_relief'],
                 reference='core_case/t1_mounting.py'),
    'W0968Z': dict(revision='t1-fit-v2', operations=['panel_cut'],
                  reference='docs/T1_MACHINING_PROTOTYPE.md'),
}


class PlanConflict(ValueError):
    pass


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def compiler_revision():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def dependency_revisions():
    root = Path(__file__).parent
    names = ('configurator.py', 'studio_parts.py', 'studio_placement.py',
             'studio_structure.py', 'studio_closures.py', 'studio_joints.py', 'part_registry.py',
             'studio_native_t1.py', 'studio_native.py')
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}


def _id(key):
    if not isinstance(key, str) or not re.fullmatch('[0-9a-f]{32}', key):
        raise ValueError('Nieprawidłowy identyfikator planu lub draftu')
    return key


def _tables(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS studio_cad_plans (
        id TEXT PRIMARY KEY, draft_id TEXT NOT NULL, draft_revision INTEGER NOT NULL,
        created_at TEXT NOT NULL, sha256 TEXT NOT NULL, payload TEXT NOT NULL)''')


def analyze(record):
    """Compile every selected definition and placement, with explicit unresolved work.

    All dimensions remain explicitly nominal. No cutting dimensions, native poses
    or missing products are invented here. This plan is useful before an adapter
    becomes executable and must remain inspectable when it is blocked.
    """
    if (not isinstance(record, dict) or set(record) != {'id', 'revision', 'draft'}
            or type(record['revision']) is not int or record['revision'] < 1):
        raise ValueError('Plan wymaga zapisanej rewizji draftu')
    _id(record['id'])
    catalog_before = studio_parts.catalog()['revision']
    model = configurator.preview(record['draft'])
    draft = model['draft']
    definitions = studio_parts.resolve(draft['hardware'])
    catalog_revision = studio_parts.catalog()['revision']
    if catalog_before != catalog_revision:
        raise PlanConflict('Katalog zmienił się podczas przygotowywania planu.')
    placements = model['placement']
    construction = model.get('construction', {})
    occurrences = copy.deepcopy(placements['items']) + copy.deepcopy(construction.get('items', []))
    blockers = []
    def block(code, message, **refs):
        blockers.append(dict(code=code, message=message, **refs))
    block('PANEL_JOINERY_UNRESOLVED',
          'Nominalne płyty wymagają receptury połączeń, luzów i docelowych wymiarów cięcia.')
    block('NATIVE_ADAPTER_PENDING',
          'Pełny adapter tej konstrukcji do IronCAD 2027 jest w trakcie wdrażania.')
    if placements['unresolved_groups']:
        block('UNRESOLVED_PLACEMENTS', 'Nie wszystkie grupy mają poprawne miejsce montażu.',
              group_ids=placements['unresolved_groups'])
    for warning in placements['warnings']:
        if warning['code'] in ('overlap', 'edge_clearance', 'hinge_mount_space', 'insufficient_space'):
            block('PLACEMENT_CONFLICT', warning['message'], group_id=warning['group_id'])
    accounting = []
    for definition in definitions:
        key = definition['id']
        items = [item for item in occurrences if item['part_id'] == key]
        # Closure rows may refer to a separate mating definition.
        mates = [g['id'] for g in draft.get('placements', []) if g.get('mate_part_id') == key]
        recipe = copy.deepcopy(RECIPES.get(key))
        row = dict(part_id=key, revision=definition['revision'], family_id=definition['family_id'],
                   definition_sha256=definition['definition_sha256'],
                   instance_ids=[item['id'] for item in items], mate_group_ids=mates,
                   cutout_status=definition['cutout_status'], native_binding_status='pending',
                   recipe_candidate=recipe, production_approved=False)
        accounting.append(row)
        block('NATIVE_ASSET_BINDING_REQUIRED',
              key + ': trzeba powiązać źródłowy model, komplet części i bazę montażu z wystąpieniem Studio.',
              part_id=key)
        if not items and not mates:
            block('SELECTED_PART_UNPLACED', key + ': wybrano część bez określonego montażu.', part_id=key)
        if definition['cutout_status'] == 'unknown':
            block('MACHINING_KNOWLEDGE_REQUIRED', key + ': brak rozstrzygnięcia wymaganych obróbek.', part_id=key)
        elif definition['cutout_status'] == 'required' and recipe is None:
            block('MACHINING_RECIPE_REQUIRED', key + ': brak powiązanej receptury obróbki.', part_id=key)
    intents = []
    for item in occurrences:
        recipe = RECIPES.get(item['part_id'])
        if recipe:
            for operation in recipe['operations']:
                intents.append(dict(id=item['id'] + '/' + operation, owner_mount=item['id'],
                                    operation=operation, recipe_revision=recipe['revision'],
                                    target_part=None, native_pose=None, status='awaiting_native_binding'))
    if not any(d['family_id'] == 'profiles' for d in definitions):
        block('JOINT_PROFILE_SELECTION_REQUIRED', 'Pełna skrzynia wymaga doboru profili i receptury ich styków.')
    result = dict(schema=SCHEMA, draft_id=record['id'], draft_revision=record['revision'],
                  draft_sha256=fingerprint(draft), target_year=2027, expected_api_major=29,
                  compiler_revision=compiler_revision(), dependency_revisions=dependency_revisions(), catalog_revision=catalog_revision,
                  registry=contract(), parameters=dict(internal_mm=draft['internal_mm'],
                      thickness_mm=draft['thickness_mm'], covers=draft['covers'],
                      cooperation=draft['cooperation'], plywood_color='#408080'),
                  construction_parameters=draft.get('construction'),
                  project_summary=model.get('project_summary'),
                  sections=model['sections'], panels=model['panels'],
                  panel_dimensions_status=model['panel_dimensions_status'], joints=model['joints'],
                  occurrences=occurrences, selected_parts=accounting, machining_intents=intents,
                  blockers=blockers, adapter_id=None, executable=False,
                  native_status='NOT RUN', production_approved=False)
    from .studio_native import configured
    adapter = configured()
    if adapter is not None:
        try:
            native = adapter.compile(record)
        except (ValueError, KeyError, OSError) as error:
            # Local file paths/errors must not leak into the browser.
            result['blockers'].append(dict(code='NATIVE_T1_CONTRACT_REQUIRED',
                message='Wybrany układ nie spełnia przypiętego kontraktu T1: '+str(error)
                if isinstance(error, ValueError) else 'Brak kompletnego źródła CAD dla tego układu.'))
        else:
            # Compilation accounts for every selected SKU, target and operation;
            # unsupported kits fail above rather than silently substituting parts.
            result.update(native_spec=native, blockers=[], adapter_id='t1-source-bound-v1', executable=True)
            result['machining_intents']=native['cuts']
            for row in result['selected_parts']:
                row['native_binding_status']='source_pinned'
    return result


def prepare(draft_id, expected_revision):
    _id(draft_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError('Nieprawidłowa rewizja draftu')
    record = configurator.read_draft(draft_id)
    if record['revision'] != expected_revision:
        raise PlanConflict('Draft zmienił się. Zapisz lub wczytaj bieżącą rewizję i przygotuj nowy plan.')
    plan = analyze(record)
    plan['plan_id'] = uuid.uuid4().hex
    plan['plan_sha256'] = fingerprint(plan)
    with project_store.db() as conn:
        _tables(conn)
        # CAS in the same database transaction as the plan insert.
        conn.execute('BEGIN IMMEDIATE')
        current = conn.execute('SELECT revision,payload FROM configurator_drafts WHERE id=?', (draft_id,)).fetchone()
        if (current is None or current['revision'] != expected_revision
                or fingerprint(configurator.validate(json.loads(current['payload']))) != plan['draft_sha256']):
            raise PlanConflict('Draft zmienił się podczas przygotowywania planu.')
        conn.execute('INSERT INTO studio_cad_plans VALUES (?,?,?,?,?,?)',
                     (plan['plan_id'], draft_id, expected_revision, project_store.now(),
                      plan['plan_sha256'], json.dumps(plan, ensure_ascii=False, allow_nan=False)))
    return plan


def read_plan(plan_id, expected_sha256):
    _id(plan_id)
    if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('Nieprawidłowy skrót planu')
    with project_store.db() as conn:
        _tables(conn)
        row = conn.execute('SELECT payload,sha256 FROM studio_cad_plans WHERE id=?', (plan_id,)).fetchone()
    if row is None or row['sha256'] != expected_sha256:
        raise PlanConflict('Nie znaleziono wskazanej rewizji planu.')
    plan = json.loads(row['payload'])
    verify_plan(plan)
    return plan


def verify_plan(plan):
    if not isinstance(plan, dict) or plan.get('schema') != SCHEMA:
        raise ValueError('Nieobsługiwany format planu CAD')
    _id(plan.get('plan_id')); _id(plan.get('draft_id'))
    unsigned = {k: v for k, v in plan.items() if k != 'plan_sha256'}
    if plan.get('plan_sha256') != fingerprint(unsigned):
        raise PlanConflict('Naruszona integralność planu CAD.')
    record = configurator.read_draft(plan['draft_id'])
    expected = analyze(record)
    supplied = {k: v for k, v in plan.items() if k not in ('plan_id', 'plan_sha256')}
    if supplied != expected:
        raise PlanConflict('Plan jest nieaktualny albo zmieniony. Przygotuj nowy z bieżącego draftu i katalogu.')
    return True
