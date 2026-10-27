"""Versioned selection catalogue built from the existing local reference library.

Selection is a design intention, never placement approval or a purchase BOM.
No CAD files, inventory balances or private source paths are exposed.
"""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from .part_registry import metadata
from .core_case.t1_mounting import HINGE_27095_OPENING

CATEGORIES = {'handles': 'Uchwyty', 'latches': 'Zamki / zatrzaski',
              'hinges': 'Zawiasy', 'profiles': 'Profile', 'corners': 'Narożniki',
              'braces': 'Wzmocnienia', 'stacking_sockets': 'Gniazda do piętrowania',
              'wheels': 'Koła'}
# Stable definition IDs and family membership; aliases are not separate parts.
FAMILIES = {'H7159': 'handles', 'H2026': 'handles', '17251S': 'latches',
            '270836': 'hinges', '2643': 'hinges', 'EG-0113': 'profiles',
            'EG-0500/1': 'profiles', 'EG-0500/2': 'profiles', '410429': 'corners',
            'B1930': 'braces', 'B1121': 'braces', 'W0968Z': 'stacking_sockets'}
REFERENCE = Path(__file__).resolve().parents[2]/'docs/catalog/hardware-reference.json'


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def _definitions():
    raw = json.loads(REFERENCE.read_text(encoding='utf-8'))
    rows = []
    for item in raw['items']:
        code = item['code']
        if code not in FAMILIES:
            raise ValueError('Unmapped reference catalogue code: '+code)
        family = FAMILIES[code]
        row = dict(id=code, revision=1, sku=code, name=item['name_pl'],
                   manufacturer=item['manufacturer'], aliases=item['aliases'],
                   description=item['function_pl'], note=item['note'],
                   source_url=item['source_url'], source_document='docs/catalog/hardware-reference.json',
                   source_checked_on=raw['checked_on'], selectable=code!='2643',
                   selection_blocker='W zapisanym źródle to pusty zespół; brak geometrii do użycia.' if code=='2643' else None,
                   cutout_status='required' if code in ('H7159','17251S','W0968Z') else 'unknown',
                   mounting_status='prototype_specific' if code in ('H7159','17251S','410429','EG-0113','EG-0500/1','EG-0500/2','B1121','B1930','W0968Z','270836') else 'unknown',
                   geometry_status='source_empty' if code=='2643' else 'source_reference',
                   purchase_unit=None, automatic_placement_approved=False, production_approved=False,
                   **metadata(family))
        rows.append(row)
    rows.append(dict(id='27095', revision=1, sku='27095', name='Zawias wpuszczany',
        manufacturer='Adam Hall', aliases=['27095'], description='Zawias używany w poprawionym prototypie T1.',
        note='Ma osobny kontur montażowy w prototypie T1. Nie zastępować wycięciem L905/915. Nowy układ wymaga sprawdzenia.',
        source_url=HINGE_27095_OPENING['source_url'], source_document='docs/CASE_STRUCTURE.md',
        source_checked_on='2026-10-26', selectable=True, selection_blocker=None,
        cutout_status='required', mounting_status='prototype_specific', geometry_status='source_reference',
        purchase_unit=None, automatic_placement_approved=False, production_approved=False,
        **metadata('hinges')))
    rows.append(dict(id='source-caster-epson', revision=1, sku=None, name='Koło z modelu Epson — SKU niepotwierdzone',
        manufacturer=None, aliases=['Assembly1'], description='Źródłowy zespół koła z prototypu transportowego.',
        note='Referencja koncepcyjna, bez potwierdzonego SKU, nośności i jednostki zakupowej. Nie traktować jako zamówienia.',
        source_url=None, source_document='docs/CASE_TRANSPORT_V3.md', source_checked_on='2026-10-24',
        selectable=True, selection_blocker=None, cutout_status='unknown', mounting_status='prototype_specific',
        geometry_status='source_reference', purchase_unit=None,
        automatic_placement_approved=False, production_approved=False, **metadata('wheels')))
    by_id = {r['id']: r for r in rows}
    if len(by_id)!=len(rows):
        raise ValueError('Duplicate catalogue definition ID')
    by_id['EG-0500/1']['paired_id']='EG-0500/2'
    by_id['EG-0500/2']['paired_id']='EG-0500/1'
    for row in rows:
        row['definition_sha256']=_hash(row)
    return rows


def catalog():
    rows = copy.deepcopy(_definitions())
    return dict(schema='rockpro.studio-parts/1', revision=_hash(rows), categories=dict(CATEGORIES),
                items=rows, scope='existing_reference_and_prototype_candidates',
                placement_available=False, inventory_connected=False)


def resolve(selection):
    if not isinstance(selection,list) or len(selection)>64:
        raise ValueError('Wybór części musi być listą do 64 pozycji katalogowych')
    by_id = {r['id']: r for r in _definitions()}
    seen = set(); result = []
    for ref in selection:
        if not isinstance(ref,dict) or set(ref)!={'part_id','revision'}:
            raise ValueError('Wybór części wymaga part_id i revision; liczność i montaż są kolejnym krokiem')
        key=ref['part_id']
        if not isinstance(key,str) or key not in by_id:
            raise ValueError('Nieznana pozycja katalogowa')
        row=by_id[key]
        if type(ref['revision']) is not int or ref['revision']!=row['revision']:
            raise ValueError('Nieobsługiwana rewizja części: '+key)
        if key in seen:
            raise ValueError('Pozycja katalogowa wybrana więcej niż raz: '+key)
        if not row['selectable']:
            raise ValueError(row['selection_blocker'])
        seen.add(key);result.append(copy.deepcopy(row))
    return result


def summarize(selection, covers):
    rows=resolve(selection);ids={r['id'] for r in rows};warnings=[]
    for row in rows:
        if row.get('paired_id') and row['paired_id'] not in ids:
            warnings.append('Profil '+row['id']+' ma parę '+row['paired_id']+' — nie została jeszcze wybrana.')
    if any(r['family_id']=='hinges' for r in rows) and all(c['kind']=='removable' for c in covers):
        warnings.append('Wybrano zawias przy zdejmowanych pokrywach. Sprawdź potrzebę jego zastosowania w kroku montażu.')
    return dict(items=rows, definition_count=len(rows), warnings=warnings,
                placement_status='not_started', purchase_bom_ready=False,
                note='Wybrano rodzaje części. Liczby sztuk, ściany, kotwy i obróbki powstaną przy rozmieszczaniu.')
