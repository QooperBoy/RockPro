"""Steps 1–5: concept topology, selected parts and section-bound placement drafts.

No CAD jobs, purchasing quantities or inferred mounting geometry.
"""
import copy
import hashlib
import json
import math
import uuid

from .mcp import project_store
from . import studio_parts
from . import studio_placement
from . import studio_structure

TYPES = {
    'case': {'label': 'Skrzynia', 'description': 'Jedno górne wieko: otwierane na zawiasach po jednej stronie lub zdejmowane.', 'covers': [['top', 'hinged']]},
    'cabinet': {'label': 'Szafa', 'description': 'Jedna przednia powłoka: otwierana na zawiasach lub zdejmowana.', 'covers': [['front', 'hinged']]},
    'three_piece': {'label': 'Skrzynia 3-elementowa', 'description': 'Korpus, zdejmowany przód i zdejmowana góra. Przód licuje z górną pokrywą.', 'covers': [['top', 'removable'], ['front', 'removable']]},
}
FACES = {'top': 'Góra', 'front': 'Przód'}


def _t1_panel_layout(d, size):
    """Pinned 9.8 mm T1 joints: non-overlapping panels, before machining.

    Preserve the historical panel order used by face/panel_index bindings.
    Body height includes only the floor. The lid height includes the profile
    joint: its walls begin 8.63 mm above the body rim, without growing the box.
    """
    w, depth, base = size
    t = d['thickness_mm']; lid = d['covers'][0]['depth_mm']; joint = 8.63
    rows = []
    for section, z, height in [('body', t, base-t),
                               (d['covers'][0]['id'], base+joint, lid-joint-t)]:
        specs = [([0, t, z], [t, depth-2*t, height]),
                 ([w-t, t, z], [t, depth-2*t, height]),
                 ([0, 0, z], [w, t, height]),
                 ([0, depth-t, z], [w, t, height]),
                 ([0, 0, 0 if section == 'body' else base+lid-t], [w, depth, t])]
        for lo, dims in specs:
            if any(x <= 0 for x in dims):
                raise ValueError('Brak miejsca na płyty T1 przy wybranym złączu profili.')
            rows.append(dict(section=section, size_mm=dims,
                             center_mm=[lo[k]+dims[k]/2 for k in range(3)]))
    return rows



def validate(value):
    fields = {'schema', 'name', 'type', 'internal_mm', 'thickness_mm', 'cooperation', 'covers'}
    if (not isinstance(value, dict) or not fields.issubset(value)
            or set(value)-fields-{'hardware','placements','construction'} or value['schema'] != 'rockpro.configurator/3'):
        raise ValueError('Nieobsługiwany format kreatora (wymagana wersja 3, szczelina jest wynikiem doboru okucia)')
    d = copy.deepcopy(value)
    d.setdefault('hardware', [])
    studio_parts.resolve(d['hardware'])
    if not isinstance(d['name'], str) or not 1 <= len(d['name'].strip()) <= 200:
        raise ValueError('Podaj nazwę draftu (1–200 znaków)')
    if not isinstance(d['type'], str) or d['type'] not in TYPES:
        raise ValueError('Wybierz jeden z trzech typów konstrukcji')
    def number(n, lo, hi):
        return type(n) in (float, int) and math.isfinite(n) and lo <= n <= hi
    if not isinstance(d['internal_mm'], list) or len(d['internal_mm']) != 3 or not all(number(n, 50, 10000) for n in d['internal_mm']):
        raise ValueError('Wnętrze: trzy wymiary od 50 do 10000 mm')
    if not number(d['thickness_mm'], 3, 30):
        raise ValueError('Grubość sklejki: 3–30 mm')
    if d['cooperation'] not in ('independent', 'together', 'sequence', 'custom'):
        raise ValueError('Nieznany sposób współpracy pokryw')
    covers = d['covers']
    if not isinstance(covers, list) or len(covers) != len(TYPES[d['type']]['covers']):
        raise ValueError('Liczba pokryw nie odpowiada wybranemu typowi')
    ids = []
    for c in covers:
        if not isinstance(c, dict) or set(c) != {'id', 'label', 'face', 'depth_mm', 'kind', 'hinge_edge', 'requires', 'height_override'}:
            raise ValueError('Nieprawidłowy opis sekcji pokrywy')
        if not isinstance(c['id'], str) or not 1 <= len(c['id']) <= 80 or c['id'] == 'body' or c['id'] in ids:
            raise ValueError('Sekcje wymagają różnych, stabilnych identyfikatorów')
        ids.append(c['id'])
        if not isinstance(c['label'], str) or not 1 <= len(c['label'].strip()) <= 100:
            raise ValueError('Podaj nazwę każdej sekcji pokrywy')
        if c['face'] not in FACES or c['kind'] not in ('hinged', 'removable') or c['hinge_edge'] not in ('low', 'high'):
            raise ValueError('Nieprawidłowa ściana lub sposób otwierania')
        if not number(c['depth_mm'], 2*d['thickness_mm'], 3000):
            raise ValueError('Wysokość/głębokość pokrywy: od 2 grubości sklejki do 3000 mm')
        if type(c['height_override']) is not bool:
            raise ValueError('Odstępstwo konstruktora musi być jawne')
        if (c['face'] == 'top' and c['kind'] == 'hinged' and d['type'] == 'case'
                and c['depth_mm'] > d['internal_mm'][2]*.15 and not c['height_override']):
            raise ValueError('Górne wieko przekracza 15% wysokości korpusu. Zaznacz jawne odstępstwo konstruktora albo zmniejsz wysokość wieka.')
        if not isinstance(c['requires'], list) or len(c['requires']) != len(set(c['requires'])) or not all(isinstance(x, str) for x in c['requires']):
            raise ValueError('Nieprawidłowa lista poprzedników pokrywy')
    if [c['face'] for c in covers] != [face for face, _ in TYPES[d['type']]['covers']]:
        raise ValueError('Ściany pokryw nie odpowiadają wybranemu typowi')
    if d['type'] == 'three_piece' and any(c['kind'] != 'removable' for c in covers):
        raise ValueError('Skrzynia 3-elementowa ma zdejmowany przód i górę')
    for i, c in enumerate(covers):
        if any(x not in ids or x == c['id'] for x in c['requires']):
            raise ValueError('Poprzednik musi wskazywać inną istniejącą pokrywę')
        if d['cooperation'] != 'custom' and c['requires']:
            raise ValueError('Własne zależności wymagają trybu „Własna kolejność”')
    graph = {c['id']: c['requires'] for c in covers}
    def visit(key, chain):
        if key in chain:
            raise ValueError('Cykl w kolejności otwierania pokryw')
        for parent in graph[key]:
            visit(parent, chain | {key})
    for key in ids:
        visit(key, set())
    studio_placement.validate(d)
    studio_structure.validate(d)
    return d


def preview(value):
    d = validate(value)
    t = d['thickness_mm']
    # Sections share nominal joint planes. Hardware will determine plywood
    # setbacks/trim inside this envelope; no invented gap expands the case.
    size = [x+2*t for x in d['internal_mm']]
    structural_t1 = (d.get('construction', {}).get('enabled') is True
                     and d['type'] == 'case' and len(d['covers']) == 1
                     and d['covers'][0]['face'] == 'top'
                     and d['covers'][0]['kind'] == 'hinged' and t == 9.8)
    if structural_t1:
        size[2] = d['internal_mm'][2]+t  # Open body: floor, no second top panel.
    panels, sections, joints = [], [], []
    axes = {'top': (2, 1), 'front': (1, -1), 'rear': (1, 1), 'left': (0, -1), 'right': (0, 1)}
    def box(section, lo, lengths, open_face=None):
        # The five/six flat panels are concept geometry, without catalog profiles.
        for axis in range(3):
            for sign in (-1, 1):
                if open_face == (axis, sign):
                    continue
                dims = list(lengths); dims[axis] = t
                center = [lo[k]+lengths[k]/2 for k in range(3)]
                center[axis] = lo[axis]+(t/2 if sign < 0 else lengths[axis]-t/2)
                panels.append(dict(section=section, center_mm=center, size_mm=dims))
    opening_faces = {axes[c['face']] for c in d['covers']}
    box('body', [0, 0, 0], size)
    panels[:] = [p for p in panels if not any(p['size_mm'][a] == t and abs(p['center_mm'][a]-(t/2 if s < 0 else size[a]-t/2)) < 1e-6 for a, s in opening_faces)]
    sections.append(dict(id='body', label='Korpus', size_mm=size, position_mm=[0, 0, 0]))
    for i, c in enumerate(d['covers']):
        axis, sign = axes[c['face']]; peers = [x for x in d['covers'] if x['face'] == c['face']]
        order = peers.index(c); split = 0 if axis != 0 else 1
        dims = list(size); dims[axis] = c['depth_mm']
        if d['type'] == 'three_piece' and c['face'] == 'front':
            # Both outer top planes and both bottom planes must coincide.
            # Raising the front adds the top section, never a free gap or base height.
            dims[2] = size[2] + d['covers'][0]['depth_mm']
        dims[split] = size[split]/len(peers)
        if dims[split] < 2*t:
            raise ValueError('Zbyt wąskie skrzydło pokrywy dla tej grubości sklejki')
        lo = [0, 0, 0]; lo[split] = order*dims[split]
        lo[axis] = size[axis] if sign > 0 else -dims[axis]
        box(c['id'], lo, dims, (axis, -sign))
        requires = c['requires'] if d['cooperation'] == 'custom' else ([d['covers'][i-1]['id']] if d['cooperation'] == 'sequence' and i else [])
        sections.append(dict(id=c['id'], label=c['label'], size_mm=dims, position_mm=lo, face=c['face'], kind=c['kind'], hinge_edge=c['hinge_edge'], requires=requires))
        joints.append(dict(id='joint-'+c['id'], sections=['body', c['id']], face=c['face'], gap_mm=None, plywood_trim_mm=None, fit_status='awaiting_mounting_layout' if d['hardware'] else 'awaiting_hardware'))
    if structural_t1:
        panels = _t1_panel_layout(d, size)
        joints[0].update(gap_mm=8.63, plywood_trim_mm=8.63,
                         fit_status='t1_reference_joint_layout')
    placement=studio_placement.preview(d,sections,panels)
    construction=studio_structure.preview(d,sections,placement)
    summary=studio_parts.summarize(d['hardware'],d['covers'])
    if placement['items']:
        summary['placement_status']='concept_draft'
        summary['note']='Wystąpienia i kotwy zapisano w koncepcji. Wycięcia, pasowanie złączy i BOM zakupowy wymagają dalszej walidacji.'
    return dict(draft=d, panels=panels, sections=sections, joints=joints, cad_ready=False,
                panel_dimensions_status='t1_reference_layout_not_cutting' if structural_t1 else 'nominal_not_cutting',
                joint_fitting_status='t1_reference_joint_layout' if structural_t1 else ('awaiting_mounting_layout' if d['hardware'] else 'awaiting_hardware'),
                hardware_summary=summary,placement=placement,construction=construction,
                project_summary=studio_structure.summarize(d,panels,placement,construction),
                warnings=[('Układ płyt T1 uwzględnia złącze profili 8,63 mm. Wycięcia pod okucia i odbiór produkcyjny pozostają osobnymi etapami.' if structural_t1 else 'Schemat sekcji bez okuć i tolerancji produkcyjnych. Ruchy pokazują intencję otwierania; oś rzeczywistego zawiasu wymaga doboru części.'),
                          'Wymiary wnętrza są wymaganiem. Pokrywy są dodatkowymi sekcjami; nie zmniejszają korpusu.'])


def convert_legacy(value):
    """Explicit conversion to a NEW draft; never rewrites archived versions."""
    if not isinstance(value, dict) or value.get('schema') not in ('rockpro.configurator/1','rockpro.configurator/2'):
        raise ValueError('Konwersja dotyczy wyłącznie archiwalnego draftu w wersji 1 lub 2')
    d = copy.deepcopy(value)
    if d['schema'] == 'rockpro.configurator/2':
        d.pop('joint_gap_mm', None);d.update(schema='rockpro.configurator/3')
        return preview(d)['draft']
    faces = [c.get('face') for c in d.get('covers', [])]
    if faces == ['top']:
        kind = 'case'
    elif faces == ['front']:
        kind = 'cabinet'
    elif len(faces) == 2 and set(faces) == {'top', 'front'}:
        kind = 'three_piece'
        d['covers'].sort(key=lambda c: c['face'] != 'top')
        for cover in d['covers']:
            cover['kind'] = 'removable'
    else:
        raise ValueError('Ten archiwalny układ nie pasuje do trzech obecnych typów. Oryginał pozostaje zachowany; utwórz nowy draft.')
    d.pop('subtype', None);d.pop('joint_gap_mm', None);d.update(schema='rockpro.configurator/3', type=kind)
    return preview(d)['draft']


def _tables(conn):
    conn.executescript('''CREATE TABLE IF NOT EXISTS configurator_drafts (
      id TEXT PRIMARY KEY, revision INTEGER NOT NULL, name TEXT NOT NULL,
      updated_at TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS configurator_draft_versions (
      id TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL,
      payload TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(id,revision));''')


def list_drafts():
    with project_store.db() as conn:
        _tables(conn)
        return [dict(r) for r in conn.execute('SELECT id,revision,name,updated_at FROM configurator_drafts ORDER BY updated_at DESC LIMIT 100')]


def read_draft(key):
    with project_store.db() as conn:
        _tables(conn)
        row = conn.execute('SELECT * FROM configurator_drafts WHERE id=?', (key,)).fetchone()
        if row is None:
            raise ValueError('Nie znaleziono draftu')
        return dict(id=row['id'], revision=row['revision'], draft=json.loads(row['payload']))


class DraftConflict(ValueError):
    pass


def save_draft(value, key=None, expected_revision=0):
    d = preview(value)['draft']
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError('Nieprawidłowa oczekiwana rewizja')
    if key is not None and (not isinstance(key, str) or not re_id(key)):
        raise ValueError('Nieprawidłowy identyfikator draftu')
    payload = json.dumps(d, ensure_ascii=False, sort_keys=True, allow_nan=False)
    with project_store.db() as conn:
        _tables(conn); conn.execute('BEGIN IMMEDIATE')
        old = conn.execute('SELECT revision,payload FROM configurator_drafts WHERE id=?', (key,)).fetchone() if key else None
        if old and json.loads(old['payload']).get('schema') != 'rockpro.configurator/3':
            raise ValueError('Archiwalny draft pozostaje zachowany. Zapisz konwersję jako nowy draft.')
        if (key and old is None) or (old['revision'] if old else 0) != expected_revision:
            raise DraftConflict('Draft zmienił się w innym oknie. Wczytaj bieżącą wersję lub zapisz jako nowy.')
        key = key or uuid.uuid4().hex; revision = expected_revision+1; stamp = project_store.now()
        conn.execute('INSERT OR REPLACE INTO configurator_drafts VALUES (?,?,?,?,?)', (key, revision, d['name'], stamp, payload))
        conn.execute('INSERT INTO configurator_draft_versions VALUES (?,?,?,?,?)', (key, revision, stamp, payload, hashlib.sha256(payload.encode()).hexdigest()))
    return dict(id=key, revision=revision, draft=d)


def re_id(value):
    return len(value) == 32 and all(c in '0123456789abcdef' for c in value)
