"""Optional source-bound catalogue candidates, separate from approved mounting data."""
import copy
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from .part_registry import metadata

DEFAULT_PATH=Path(__file__).resolve().parents[2]/'artifacts/studio-project-parts/catalog.json'


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema')!='rockpro.source-parts/1' or not isinstance(data.get('items'),list) or len(data['items'])>256:
        raise ValueError('Unsupported source part catalogue')
    seen=set()
    for row in data['items']:
        if not isinstance(row['id'],str) or not row['id'].startswith('source-') or row['id'] in seen:
            raise ValueError('Invalid source part identity')
        seen.add(row['id'])
        if row['revision']!=1 or type(row['revision']) is not int or row['definition_sha256']!=digest({k:v for k,v in row.items() if k!='definition_sha256'}):
            raise ValueError('Source definition revision or checksum mismatch')
        if row['automatic_placement_approved'] is not False or row['production_approved'] is not False or row['purchase_unit'] is not None:
            raise ValueError('Source candidates cannot approve production or purchasing')
        if row['mounting_status']!='unknown' or row['cutout_status']!='unknown' or row['sku'] is not None:
            raise ValueError('Unconfirmed source metadata cannot be promoted')
        if row['family_id'] in ('hinges','latches') and row.get('component_only') is not True:
            raise ValueError('Unconfirmed closures must remain source components')
        if row['family_id']=='unclassified' and row['stage_id'] is not None:
            raise ValueError('Unknown source function cannot acquire a production stage')
        if row['family_id']!='unclassified' and any(row[k]!=v for k,v in metadata(row['family_id']).items()):
            raise ValueError('Source family registry mismatch')
    return data


@lru_cache(maxsize=1)
def _configured(path):
    return load(path)


def catalog():
    path=configured_path()
    if not path.exists():return dict(items=[],report={})
    return copy.deepcopy(_configured(str(path.resolve())))


def configured_path():
    return Path(os.environ.get('ROCKPRO_SOURCE_PARTS',DEFAULT_PATH))
