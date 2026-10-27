"""Steps 1–3: validated concept topology, plywood preview and revisioned drafts.

No CAD jobs, purchasing quantities or inferred mounting geometry.
"""
import copy
import hashlib
import json
import math
import uuid

from .mcp import project_store

TYPES = {
    'case': {'label': 'Skrzynia', 'subtypes': ['top', 'hood', 'two_covers', 'custom']},
    'cabinet': {'label': 'Szafa', 'subtypes': ['front', 'double_front', 'custom']},
    'workstation': {'label': 'Stanowisko / workstation', 'subtypes': ['top', 'front', 'custom']},
    'suitcase': {'label': 'Walizka', 'subtypes': ['front', 'custom']},
}
SUBTYPES = {'top': 'Górne wieko na zawiasach', 'hood': 'Zdejmowana czapka',
            'two_covers': 'Górne wieko i osłona przednia', 'front': 'Jedna klapa przednia',
            'double_front': 'Dwoje drzwi przednich', 'custom': 'Własny podział pokryw'}
FACES = {'top': 'Góra', 'front': 'Przód', 'rear': 'Tył', 'left': 'Lewa', 'right': 'Prawa'}


def validate(value):
    fields = {'schema', 'name', 'type', 'subtype', 'internal_mm', 'thickness_mm', 'joint_gap_mm', 'cooperation', 'covers'}
    if not isinstance(value, dict) or set(value) != fields or value['schema'] != 'rockpro.configurator/1':
        raise ValueError('Nieobsługiwany format kreatora (wymagana wersja 1)')
    d = copy.deepcopy(value)
    if not isinstance(d['name'], str) or not 1 <= len(d['name'].strip()) <= 200:
        raise ValueError('Podaj nazwę draftu (1–200 znaków)')
    if d['type'] not in TYPES or d['subtype'] not in TYPES[d['type']]['subtypes']:
        raise ValueError('Podtyp nie pasuje do głównego typu konstrukcji')
    def number(n, lo, hi):
        return type(n) in (float, int) and math.isfinite(n) and lo <= n <= hi
    if not isinstance(d['internal_mm'], list) or len(d['internal_mm']) != 3 or not all(number(n, 50, 10000) for n in d['internal_mm']):
        raise ValueError('Wnętrze: trzy wymiary od 50 do 10000 mm')
    if not number(d['thickness_mm'], 3, 30) or not number(d['joint_gap_mm'], .5, 10):
        raise ValueError('Sklejka: 3–30 mm; szczelina prezentacyjna: 0,5–10 mm')
    if d['cooperation'] not in ('independent', 'together', 'sequence', 'custom'):
        raise ValueError('Nieznany sposób współpracy pokryw')
    covers = d['covers']
    if not isinstance(covers, list) or not 1 <= len(covers) <= 4:
        raise ValueError('Wybierz od jednej do czterech pokryw')
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
        if (c['face'] == 'top' and c['kind'] == 'hinged' and d['type'] in ('case', 'workstation')
                and c['depth_mm'] > d['internal_mm'][2]*.15 and not c['height_override']):
            raise ValueError('Górne wieko przekracza 15% wysokości korpusu. Zaznacz jawne odstępstwo konstruktora albo zmniejsz wysokość wieka.')
        if not isinstance(c['requires'], list) or len(c['requires']) != len(set(c['requires'])) or not all(isinstance(x, str) for x in c['requires']):
            raise ValueError('Nieprawidłowa lista poprzedników pokrywy')
    expected_faces = {'top': ['top'], 'hood': ['top'], 'two_covers': ['top', 'front'], 'front': ['front'], 'double_front': ['front', 'front']}
    if d['subtype'] != 'custom' and [c['face'] for c in covers] != expected_faces[d['subtype']]:
        raise ValueError('Zmiana liczby lub ścian pokryw wymaga podtypu „Własny podział”')
    if d['subtype'] == 'hood' and covers[0]['kind'] != 'removable':
        raise ValueError('Zdejmowana czapka musi mieć tryb zdejmowany')
    kinds = {'top': ['hinged'], 'front': ['hinged'], 'double_front': ['hinged', 'hinged'], 'two_covers': ['hinged', 'removable']}
    if d['subtype'] in kinds and [c['kind'] for c in covers] != kinds[d['subtype']]:
        raise ValueError('Sposób otwierania wymaga podtypu „Własny podział”')
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
    return d


def preview(value):
    d = validate(value)
    t, gap = d['thickness_mm'], d['joint_gap_mm']
    size = [x+2*t for x in d['internal_mm']]
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
        dims[split] = (size[split]-(len(peers)-1)*gap)/len(peers)
        if dims[split] < 2*t:
            raise ValueError('Zbyt wąskie skrzydło pokrywy dla tej grubości sklejki')
        lo = [0, 0, 0]; lo[split] = order*(dims[split]+gap)
        lo[axis] = size[axis]+gap if sign > 0 else -dims[axis]-gap
        box(c['id'], lo, dims, (axis, -sign))
        requires = c['requires'] if d['cooperation'] == 'custom' else ([d['covers'][i-1]['id']] if d['cooperation'] == 'sequence' and i else [])
        sections.append(dict(id=c['id'], label=c['label'], size_mm=dims, position_mm=lo, face=c['face'], kind=c['kind'], hinge_edge=c['hinge_edge'], requires=requires))
        joints.append(dict(id='joint-'+c['id'], sections=['body', c['id']], face=c['face'], gap_mm=gap))
    return dict(draft=d, panels=panels, sections=sections, joints=joints, cad_ready=False,
                warnings=['Schemat sekcji bez okuć i tolerancji produkcyjnych. Ruchy pokazują intencję otwierania; oś rzeczywistego zawiasu wymaga doboru części.',
                          'Wymiary wnętrza są wymaganiem. Pokrywy są dodatkowymi sekcjami; nie zmniejszają korpusu.'])


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
        old = conn.execute('SELECT revision FROM configurator_drafts WHERE id=?', (key,)).fetchone() if key else None
        if (key and old is None) or (old['revision'] if old else 0) != expected_revision:
            raise DraftConflict('Draft zmienił się w innym oknie. Wczytaj bieżącą wersję lub zapisz jako nowy.')
        key = key or uuid.uuid4().hex; revision = expected_revision+1; stamp = project_store.now()
        conn.execute('INSERT OR REPLACE INTO configurator_drafts VALUES (?,?,?,?,?)', (key, revision, d['name'], stamp, payload))
        conn.execute('INSERT INTO configurator_draft_versions VALUES (?,?,?,?,?)', (key, revision, stamp, payload, hashlib.sha256(payload.encode()).hexdigest()))
    return dict(id=key, revision=revision, draft=d)


def re_id(value):
    return len(value) == 32 and all(c in '0123456789abcdef' for c in value)
