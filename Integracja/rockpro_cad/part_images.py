"""Optional, local-only thumbnails; presentation assets do not change part revisions."""
import hashlib
import json
from pathlib import Path

from . import studio_parts

DEFAULT_FOLDER = Path(__file__).resolve().parents[2] / 'artifacts/studio-part-images'


def load(folder):
    """Serve only known IDs and verified raster files inside the selected folder."""
    if folder is None:
        return {}
    folder = Path(folder).resolve(strict=True)
    index = json.loads((folder / 'index.json').read_text(encoding='utf-8'))
    if index.get('schema') != 'rockpro.part-images/1':
        raise ValueError('Unsupported part image index')
    known = {r['id'] for r in studio_parts.catalog()['items']}
    result = {}
    for key, row in index['images'].items():
        if key not in known or row['kind'] not in ('cad_render', 'manufacturer_photo'):
            raise ValueError('Unknown part or image kind')
        path = (folder / row['file']).resolve(strict=True)
        if not path.is_relative_to(folder) or path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            raise ValueError('Part image must be a local raster file')
        raw = path.read_bytes()
        if not 0 < len(raw) <= 2*1024*1024 or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Part image checksum or size mismatch')
        mime = 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'
        if not raw.startswith(b'\x89PNG\r\n\x1a\n' if mime == 'image/png' else b'\xff\xd8\xff'):
            raise ValueError('Invalid part raster signature')
        result[key] = dict(path=path, mime=mime, metadata=dict(
            url='part-images/'+path.name, kind=row['kind'], label=row['label'],
            source=row['source'], sha256=row['sha256']))
    if len({r['metadata']['url'] for r in result.values()}) != len(result):
        raise ValueError('Duplicate part image filename')
    return result


def decorate(catalog, images):
    for row in catalog['items']:
        row['image'] = images.get(row['id'], {}).get('metadata')
    return catalog
