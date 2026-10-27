"""Source-bound reference gallery and draft intake; no CAD or project-store writes."""
import hashlib
import json
import math
from pathlib import Path


# These are candidate classifications of the surveyed package, not CAD templates.
PROFILES = (
    ('mixer', 'Mikser i czapka', ('M02',), 'Podstawa, osłona i osobne urządzenie.',
     ['Podział wysokości czapki', 'Podparcie miksera i piany', 'Trzy uchwyty wzorca'],
     ['Potwierdzić całkowicie zdejmowaną czapkę i punkty podparcia.']),
    ('hoists', 'Wciągarki', ('M03',), 'Stanowiska urządzeń, wnętrze i osprzęt jezdny.',
     ['Układ dwóch stanowisk', 'Komory łańcuchów', 'Pokrywa i zawiasy'],
     ['Układ łańcuchów, podparcie i masa zestawu wymagają potwierdzenia.']),
    ('moving_heads', 'Głowy oświetleniowe', ('M06',), 'Dwa urządzenia i indywidualne podparcia.',
     ['Rozstaw stanowisk', 'Pozycja transportowa głów', 'Kontury pian'],
     ['Nazwa pliku wskazuje XIP, a drzewo XP: pasowanie nie jest potwierdzone.']),
    ('multi_slot', 'Wiele gniazd', ('M05',), 'Powtarzany wkład i ograniczenie gabarytu.',
     ['Liczba i układ gniazd', 'Wkłady piankowe', 'Stały albo wyliczany gabaryt'],
     ['Pięć wkładów we wzorcu; potwierdzić docelową liczbę i ograniczenie obudowy.']),
    ('screens', 'Ekrany', ('M01', 'M07'), 'Dwa warianty osłon, docisków i podparcia ekranu.',
     ['Osłony góra/dół', 'Strefy docisku', 'Wariant osprzętu i pian'],
     ['Wspólna rodzina jest hipotezą; nie utożsamiać rewizji ani kierunków demontażu.']),
    ('workstation', 'Workstation', ('M04',), 'Góra, dół, klapa i wysuwane półki potwierdzone przez użytkownika.',
     ['Wysuwane półki', 'Wysokość robocza', 'Poziomy półek i dostęp do złącza'],
     ['Funkcja wysuwanych półek potwierdzona 27.10.2026. Liczba, osie prowadnic, skok i obciążenia wymagają mapowania.']),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build_catalog(bundle):
    """Load surveyed references. Never infer mounting approval or closed dimensions."""
    bundle = Path(bundle).resolve(strict=True)
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    models = {row['key']: row for row in manifest['models']}
    if len(manifest['models']) != 7 or len(models) != 7 or set(models) != {f'M{i:02d}' for i in range(1, 8)}:
        raise ValueError('Expected seven distinct surveyed references')
    families = []
    images = {}
    bindings = {}
    for family_id, label, keys, description, controls, questions in PROFILES:
        variants = []
        for key in keys:
            row = models[key]
            raw = (bundle / 'native-02' / (key + '-inventory.json')).read_bytes()
            standard = json.loads((bundle / 'working-standard-v1' / (key + '.json')).read_text(encoding='utf-8'))
            if standard['source_sha256'] != row['sha256'] or standard['inventory_sha256'] != sha(raw):
                raise ValueError('Source/inventory binding mismatch: ' + key)
            nodes = standard['nodes']
            count = sum(n['type'] == 'Z_ELEMENT_PART' for n in nodes)
            if count != standard['physical_part_count']:
                raise ValueError('Part count mismatch: ' + key)
            groups = [dict(path=n['source_path'], label=n['name_raw']) for n in nodes
                      if n['type'] == 'Z_ELEMENT_ASSEMBLY' and n['source_path'].count('/') <= 2]
            image_routes = {}
            for view, folder in (('closed', 'images-full-2027'), ('inside', 'review-2027')):
                image = bundle / folder / (key + '.png')
                if image.is_file():
                    name = key + '-' + view + '.png'
                    images[name] = image
                    image_routes[view] = 'images/' + name
            variants.append(dict(id=key, label=Path(row['name']).stem, part_count=count,
                                 source_sha256=row['sha256'], inventory_sha256=sha(raw),
                                 groups=groups, images=image_routes,
                                 geometry_dimensions='unmapped', cad_generation=False))
            bindings[key] = dict(source_sha256=row['sha256'], inventory_sha256=sha(raw))
        families.append(dict(id=family_id, label=label, classification='candidate',
                             description=description, controls=controls, questions=questions,
                             confirmed_functions=['sliding_shelves'] if family_id == 'workstation' else [],
                             variants=variants))
    catalog = dict(schema='rockpro.reference-gallery/1', families=families,
                   reference_count=len(models), family_count=len(families),
                   part_count=sum(v['part_count'] for f in families for v in f['variants']),
                   cad_generation=False, production_approved=False,
                   linear_url='https://linear.app/rock-pro/issue/ROC-45')
    catalog['binding'] = sha(json.dumps(bindings, sort_keys=True).encode('utf-8'))
    return catalog, images


def validate_draft(value, catalog):
    """A concept can be captured before its family has an executable CAD adapter."""
    required = {'schema', 'catalog_binding', 'family_id', 'variant_id', 'internal_mm',
                'cover_height_mm', 'opening', 'transport', 'notes', 'sliding_shelves'}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError('Nieprawidłowy zestaw pól szkicu')
    if value['schema'] != 'rockpro.concept-draft/1' or value['catalog_binding'] != catalog['binding']:
        raise ValueError('Szkic pochodzi z innej wersji katalogu')
    family = next((f for f in catalog['families'] if f['id'] == value['family_id']), None)
    if family is None or value['variant_id'] not in {v['id'] for v in family['variants']}:
        raise ValueError('Wariant nie należy do wybranej rodziny')
    def positive(number):
        return type(number) in (int, float) and math.isfinite(number) and 0 < number <= 10000
    dims = value['internal_mm']
    if not isinstance(dims, list) or len(dims) != 3 or not all(positive(n) for n in dims):
        raise ValueError('Podaj trzy dodatnie wymiary wymaganego wnętrza w mm (do 10000)')
    if value['cover_height_mm'] is not None and not positive(value['cover_height_mm']):
        raise ValueError('Wysokość osłony musi być dodatnia albo nieustalona')
    if value['opening'] not in ('source_unconfirmed', 'hinged', 'removable', 'sliding'):
        raise ValueError('Nieznany sposób otwierania')
    if value['transport'] not in ('source_unconfirmed', 'feet', 'casters', 'stacking', 'trolley'):
        raise ValueError('Nieznana podstawa')
    if not isinstance(value['notes'], str) or len(value['notes']) > 4000:
        raise ValueError('Uwagi mogą mieć do 4000 znaków')
    shelves = value['sliding_shelves']
    if value['family_id'] != 'workstation' and shelves is not None:
        raise ValueError('Moduł półek nie jest jeszcze zmapowany dla tej rodziny')
    if shelves is not None:
        if not isinstance(shelves, dict) or set(shelves) != {'count', 'requested_travel_mm'}:
            raise ValueError('Nieprawidłowy opis półek')
        if shelves['count'] is not None and (type(shelves['count']) is not int or not 1 <= shelves['count'] <= 30):
            raise ValueError('Podaj liczbę półek od 1 do 30 albo pozostaw nieustaloną')
        if shelves['requested_travel_mm'] is not None and not positive(shelves['requested_travel_mm']):
            raise ValueError('Podaj dodatni wymagany wysuw albo pozostaw nieustalony')
    return dict(valid_draft=True, cad_ready=False, production_approved=False,
                message='Szkic poprawny. Wymiary i wybory zapisują wymagania; nie zmieniają obrazu wzorca.',
                missing=['Mapowanie światła wnętrza i osłon', 'Reguły okuć i obróbek',
                         'Wykonywalny adapter rodziny oraz próba natywna'])
