"""Portable supplier display geometry, separate from approved machining assets."""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from .part_registry import metadata

FOLDER=Path(__file__).resolve().parents[2]/'assets/supplier-parts'

@lru_cache(maxsize=4)
def _index(path,stamp):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema')!='rockpro.supplier-parts/1':raise ValueError('Unsupported supplier assets')
    ids=[r['id'] for r in data['items']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate supplier definition')
    return data

def index():
    path=FOLDER/'index.json'
    return _index(str(path),path.stat().st_mtime_ns) if path.exists() else dict(items=[],assets={})

def definitions():
    rows=[]
    for spec in index()['items']:
        row=copy.deepcopy(spec);row.update(metadata(row.pop('family_id')))
        row.update(revision=1,manufacturer='Penn Elcom',aliases=[],description=row['name'],
            note='Rzeczywisty model STEP producenta. Rama podglądu i montaż wymagają potwierdzenia; brak zatwierdzonych wycięć.',
            source_document='Katalog CAD producenta',source_checked_on='2026-10-28',
            selectable=True,selection_blocker=None,show_as_complete_part=True,component_only=False,
            cutout_status='unknown',mounting_status='unconfirmed',geometry_status='supplier_step_display',
            automatic_placement_approved=False,production_approved=False)
        rows.append(row)
    return rows

def routes():
    result={};folder=FOLDER.resolve()
    for asset in index()['assets'].values():
        for kind,checksum in [('mesh','mesh_sha256'),('image','image_sha256')]:
            file=(folder/asset[kind]).resolve(strict=True)
            if not file.is_relative_to(folder):raise ValueError('Invalid supplier asset path')
            raw=file.read_bytes()
            if len(raw)>16*1024*1024 or hashlib.sha256(raw).hexdigest()!=asset[checksum]:raise ValueError('Supplier asset checksum mismatch')
            result['supplier-parts/'+file.name]=(file,'application/gzip' if kind=='mesh' else 'image/png')
    return result

def decorate(catalog):
    by_id={r['id']:r for r in index()['items']}
    for row in catalog['items']:
        spec=by_id.get(row['id'])
        if not spec:continue
        a=index()['assets'][spec['asset_id']]
        row['image']=dict(url='supplier-parts/'+a['image'],kind='cad_render',label='Model 3D producenta',
            source=dict(url=spec['source_url'],description='Render z modelu STEP producenta; montaż do potwierdzenia.'),
            sha256=a['image_sha256'],mesh_url='supplier-parts/'+a['mesh'],mesh_sha256=a['mesh_sha256'],
            mesh_compression='gzip',mesh_frame='mount.local_uvn',frame_status='supplier_visual_frame_requires_mount_review')
        row['show_as_complete_part']=True
    return catalog
