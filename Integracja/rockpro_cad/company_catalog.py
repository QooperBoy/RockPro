"""Read-only company workbook snapshot; no stock writes or CAD approval."""
from functools import lru_cache
import copy
import hashlib
import json
import os
from pathlib import Path
import re
from . import manufacturer_images

DEFAULT_PATH=Path(__file__).resolve().parents[2]/'artifacts/erp-company-parts/catalog.json'


def configured_path():
    return Path(os.environ.get('ROCKPRO_COMPANY_CATALOG',DEFAULT_PATH))


def normalize_code(code):
    code=re.sub(r'^(?:AH|PN)\s*[-–]\s*','',str(code).strip(),flags=re.I)
    return re.sub(r'\s+','',code).upper()


@lru_cache(maxsize=4)
def _load(path,stamp):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema')!='rockpro.company-catalog/1' or not isinstance(data.get('items'),list) or len(data['items'])>1000:
        raise ValueError('Unsupported company catalogue')
    if not re.fullmatch('[a-f0-9]{64}',data.get('source',{}).get('sha256','')):raise ValueError('Missing workbook identity')
    ids=set()
    for row in data['items']:
        if not re.fullmatch('company-[a-f0-9]{24}',row['id']) or row['id'] in ids:raise ValueError('Company item identity differs')
        ids.add(row['id'])
        if row['geometry_approved'] is not False or row['production_approved'] is not False:raise ValueError('Workbook cannot approve CAD')
    return data


def catalog(parts=None):
    path=configured_path()
    if not path.exists():return dict(schema='rockpro.company-catalog/1',source=None,items=[],summary=dict(records=0))
    result=copy.deepcopy(_load(str(path.resolve()),path.stat().st_mtime_ns))
    by_code={}
    for part in (parts or {}).get('items',[]):
        if part.get('show_as_complete_part') is False or part.get('component_only'):continue
        for code in [part.get('sku'),part.get('catalog_code_raw'),*part.get('aliases',[])]:
            if code:by_code.setdefault(normalize_code(code),{})[part['id']]=part
    for row in result['items']:
        matches=by_code.get(normalize_code(row['code']),{}) if not row['duplicate_code'] else {}
        row['geometry_candidates']=[dict(id=r['id'],name=r['name'],has_mesh=bool((r.get('image') or {}).get('mesh_url')),
            status='exact_code_candidate_requires_variant_review') for r in matches.values()]
        if row['image']:row['image']['url']='company-images/'+row['id']
    result['summary']['records_with_geometry_candidates']=sum(bool(r['geometry_candidates']) for r in result['items'])
    manufacturer_images.decorate(result)
    result['summary']['workbook_images']=sum(bool(r.get('image')) for r in _load(str(path.resolve()),path.stat().st_mtime_ns)['items'])
    result['summary']['manufacturer_photos']=sum((r.get('image') or {}).get('kind')=='manufacturer_photo' for r in result['items'])
    result['summary']['images']=sum(bool(r.get('image')) for r in result['items'])
    return result


def images():
    path=configured_path()
    if not path.exists():return {}
    return dict(_image_routes(str(path.resolve()),path.stat().st_mtime_ns))


@lru_cache(maxsize=4)
def _image_routes(path,stamp):
    path=Path(path)
    data=_load(str(path),stamp);folder=path.parent.resolve();result={}
    for row in data['items']:
        if not row.get('image'):continue
        image=row['image'];file=(folder/image['file']).resolve(strict=True)
        if not file.is_relative_to(folder) or file.suffix.lower() not in ('.png','.jpg','.jpeg'):raise ValueError('Invalid company image path')
        raw=file.read_bytes()
        if len(raw)>2*1024*1024 or hashlib.sha256(raw).hexdigest()!=image['sha256']:raise ValueError('Company image checksum mismatch')
        mime='image/png' if file.suffix.lower()=='.png' else 'image/jpeg'
        if not raw.startswith(b'\x89PNG\r\n\x1a\n' if mime=='image/png' else b'\xff\xd8\xff'):raise ValueError('Company image signature mismatch')
        result['company-images/'+row['id']]=(file,mime)
    return result


def decorate(parts):
    data=catalog(parts);refs={}
    for row in data['items']:
        for candidate in row['geometry_candidates']:
            refs.setdefault(candidate['id'],[]).append(dict(code=row['code'],cached_stock_raw=row['cached_stock_raw'],
                source_cell=row['source']['stock_cell'],source_sha256=data['source']['sha256'],cutout_note=row['cutout_note']))
    for row in parts['items']:
        if row['id'] in refs:row['company_references']=refs[row['id']]
    return parts


def picker_entries(parts, data=None):
    """Expose every workbook record for browsing; never infer a mounting definition.

    Explicit presentation allowlist excludes stock, prices, workbook cells and IDs
    of customer projects. Duplicate SKU records keep their separate source IDs.
    """
    data = catalog(parts) if data is None else data
    known_ids={r['id'] for r in parts['items']}
    for row in data['items']:
        if row['id'] in known_ids:continue
        family = 'company:'+row['category']
        parts['categories'][family] = 'Excel · '+row['category']
        image = copy.deepcopy(row.get('image'))
        if image:
            image = {k:v for k,v in image.items() if k in ('url','kind','label','source')}
            image.setdefault('kind','workbook_photo')
            image.setdefault('label','Zdjęcie z katalogu firmowego')
            image.setdefault('source',dict(description='Obraz z przekazanego wykazu części. Nie potwierdza montażu ani modelu 3D.'))
        parts['items'].append(dict(id=row['id'],revision=1,sku=row['code'],name=row['name'],
            manufacturer=row.get('manufacturer'),aliases=[],family_id=family,
            description=row['name'],note=row.get('cutout_note') or 'Brak opisu wycięcia w źródle.',
            source_url=row.get('source_url'),source_document='Katalog firmowy',source_checked_on='Import katalogu',
            catalog_only=True,catalog_source='company_workbook',duplicate_code=row.get('duplicate_code',False),
            show_as_complete_part=True,selectable=False,component_only=False,
            selection_blocker='Pozycja katalogowa z Excela. Wybór do montażu wymaga powiązania i sprawdzenia modelu 3D.',
            cutout_status='required' if row.get('cutout_note') else 'unknown',mounting_status='unknown',
            geometry_status='catalog_only',automatic_placement_approved=False,production_approved=False,
            image=image))
    parts['company_record_count']=len(data['items'])
    return parts
