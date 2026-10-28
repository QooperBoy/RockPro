"""Optional, verified manufacturer photos. Never approve geometry or merge SKUs."""
from functools import lru_cache
import copy
import hashlib
import json
import os
from pathlib import Path

DEFAULT_FOLDER = Path(__file__).resolve().parents[2] / 'artifacts/manufacturer-images'


def routes():
    folder = Path(os.environ.get('ROCKPRO_MANUFACTURER_IMAGES', DEFAULT_FOLDER))
    index = folder / 'index.json'
    if not index.exists():
        return {}
    return _load(str(folder.resolve()), index.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _load(folder, stamp):
    folder = Path(folder)
    data = json.loads((folder / 'index.json').read_text(encoding='utf-8'))
    if data.get('schema') != 'rockpro.manufacturer-images/1':
        raise ValueError('Unsupported manufacturer image index')
    result = {}
    for key, row in data['images'].items():
        path = (folder / row['file']).resolve(strict=True)
        if not path.is_relative_to(folder) or path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            raise ValueError('Invalid manufacturer image path')
        raw = path.read_bytes()
        mime = 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else None
        if not mime or not 0 < len(raw) <= 2*1024*1024 or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Manufacturer photo integrity mismatch')
        result[key] = dict(path=path, mime=mime, metadata=dict(
            url='manufacturer-images/'+path.name, kind='manufacturer_photo',
            label='Zdjęcie producenta · '+row['manufacturer'], sha256=row['sha256'],
            source=dict(url=row['image_url'], page_url=row['page_url'],
                        checked_at=row['checked_at'], description='Zdjęcie katalogowe producenta. Nie potwierdza geometrii ani montażu.')))
    return result


def decorate(parts):
    photos = routes()
    for row in parts['items']:
        if row['id'] not in photos:
            continue
        old = row.get('image') or {}
        photo = copy.deepcopy(photos[row['id']]['metadata'])
        # Photo replacement must preserve the independent native mesh and its evidence.
        photo.update({k:v for k,v in old.items() if k not in ('url','kind','label','sha256','source')})
        row['image'] = photo
    return parts
