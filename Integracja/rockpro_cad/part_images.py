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
    known = {r['id']:r for r in studio_parts.catalog()['items']}
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
        if row.get('mesh'):
            mesh=(folder/row['mesh']['file']).resolve(strict=True)
            if not mesh.is_relative_to(folder) or mesh.suffix!='.json':
                raise ValueError('Part mesh must be local JSON')
            data=mesh.read_bytes()
            if len(data)>16*1024*1024 or hashlib.sha256(data).hexdigest()!=row['mesh']['sha256']:
                raise ValueError('Part mesh checksum or size mismatch')
            model=json.loads(data)
            if model.get('schema')!='rockpro.part-mesh/1' or model.get('units')!='m' or model.get('frame')!='mount.local_uvn':
                raise ValueError('Unsupported display mesh')
            if known[key].get('source_binding'):
                if model.get('source_binding')!=known[key]['source_binding'] or model.get('display_only') is not True:
                    raise ValueError('Display mesh source binding mismatch')
                result[key]['metadata']['mesh_scope']=row['mesh'].get('scope')
                result[key]['metadata']['display_body_count']=row['mesh']['display_body_count']
                result[key]['metadata']['source_body_count']=row['mesh']['source_body_count']
                result[key]['metadata']['frame_status']=model['frame_status']
            result[key]['mesh_path']=mesh
            result[key]['metadata']['mesh_url']='part-models/'+mesh.name
            result[key]['metadata']['mesh_sha256']=row['mesh']['sha256']
    if len({r['metadata']['url'] for r in result.values()}) != len(result):
        raise ValueError('Duplicate part image filename')
    mesh_urls=[r['metadata']['mesh_url'] for r in result.values() if 'mesh_path' in r]
    if len(set(mesh_urls))!=len(mesh_urls):
        raise ValueError('Duplicate part mesh filename')
    return result


def decorate(catalog, images):
    coverage={r['selected_definition']:r for r in catalog.get('source_report',{}).get('coverage',[])}
    observations={key:sorted({o['project'] for o in r['occurrences']}) for key,r in coverage.items()}
    for row in catalog['items']:
        row['image'] = images.get(row['id'], {}).get('metadata')
        if row.get('source_project'):
            row['observed_projects']=observations.get(row['id'],[row['source_project']])
            entry=coverage.get(row['id'],{})
            match=next((o for o in entry.get('occurrences',[]) if o['project']==row['source_project'] and o['root_path']==row['source_binding']['root_path']),{})
            row['source_body_count']=match.get('part_count')
    return catalog
