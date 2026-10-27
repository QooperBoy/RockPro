"""Convert a receipt-bound native export and explicit mapping into a local preview.

No CAD import; annotations belong in private artifacts and are not inferred from color.
"""
import argparse
from array import array
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def convert(export, receipt, inventory, mapping, output):
    export, receipt, inventory, mapping, output = map(Path, (export, receipt, inventory, mapping, output))
    proof = json.loads(receipt.read_text(encoding='utf-8-sig'))
    annotation = json.loads(mapping.read_text(encoding='utf-8'))
    inv = json.loads(inventory.read_text(encoding='utf-8'))
    if not proof.get('passed') or not proof.get('source_unchanged') or proof['export_sha256'] != sha(export):
        raise ValueError('Native export receipt mismatch')
    if inv['source_sha256'] != proof['source_sha256'] or annotation['source_sha256'] != proof['source_sha256']:
        raise ValueError('Mixed source revisions')
    if annotation['inventory_sha256'] != sha(inventory):
        raise ValueError('Inventory mapping mismatch')
    if len(annotation['shelves']) != 4:
        raise ValueError('This preview requires four explicitly mapped shelf modules')
    nodes = {r['path']: r for r in inv['rows']}
    for shelf in annotation['shelves']:
        for path in shelf['paths']:
            if path not in nodes:
                raise ValueError('Missing mapped shelf path')
    rows = []
    by_mesh = {}
    with zipfile.ZipFile(export) as archive:
        if sum(x.file_size for x in archive.infolist()) > 512 * 1024 * 1024:
            raise ValueError('Export exceeds preview budget')
        tree = json.loads(archive.read('tree.json'))
        def walk(node, parent, ancestors):
            path = parent + '/' + str(node['id'])
            chain = ancestors + [(path, node.get('n', ''))]
            if node.get('t') == 'p':
                # Native Web Viewer removes '-' and '_' from some display labels.
                # Exact hierarchical IDs, source hash and transforms remain primary.
                if path not in nodes or re.sub('[-_]', '', nodes[path]['name']) != re.sub('[-_]', '', node['n']):
                    raise ValueError('Export/inventory identity mismatch: ' + path)
                if int(node['i']) in by_mesh:
                    raise ValueError('Duplicate exported mesh reference')
                by_mesh[int(node['i'])] = (node, path, chain)
            for child in node.get('c') or []:
                walk(child, path, chain)
        for top in tree['t']:
            walk(top, 'root', [])
        if len(by_mesh) != sum(r['type'] == 'Z_ELEMENT_PART' for r in inv['rows']):
            raise ValueError('Export tree does not account for all inventoried parts')
        output.mkdir(parents=True, exist_ok=False)
        seen = set()
        with (output / 'geometry.bin').open('xb') as stream:
            for name in archive.namelist():
                if not name.endswith('.json') or name == 'tree.json':
                    continue
                raw = json.loads(archive.read(name))
                if int(raw['id']) in seen:
                    raise ValueError('Duplicate geometry payload')
                seen.add(int(raw['id']))
                node, path, ancestors = by_mesh[int(raw['id'])]
                vertices, normals, matrix = raw['v'], raw['n'], raw['p']
                if not vertices or len(vertices) % 9 or len(vertices) != len(normals) or len(matrix) != 16:
                    raise ValueError('Invalid native mesh')
                if not all(math.isfinite(v) for v in vertices + normals + matrix):
                    raise ValueError('Nonfinite native mesh')
                # The exporter stores column-major transforms in metres.
                local_min = [min(vertices[k::3]) for k in range(3)]
                local_max = [max(vertices[k::3]) for k in range(3)]
                corners = [[sum(p[k] * matrix[k*4+j] for k in range(3)) + matrix[12+j]
                            for j in range(3)] for p in itertools.product(*zip(local_min, local_max))]
                bounds = [min(p[k] for p in corners) for k in range(3)] + [max(p[k] for p in corners) for k in range(3)]
                expected = nodes[path]['world_mm']
                if max(abs(matrix[k*4+j] - expected[k][j] / (1000 if k == 3 and j < 3 else 1))
                       for k in range(4) for j in range(4)) > 2e-5:
                    raise ValueError('Native export frame differs from inventory')
                policy = annotation['parts'].get(path, {}).get('policy', 'rigid')
                rigid_group = annotation['parts'].get(path, {}).get('rigid_group', path)
                if policy not in ('panel', 'profile', 'rigid'):
                    raise ValueError('Unknown preview geometry policy')
                axes = []
                extents = [bounds[k+3] - bounds[k] for k in range(3)]
                if policy == 'panel':
                    axes = sorted(range(3), key=lambda k: extents[k], reverse=True)[:2]
                elif policy == 'profile':
                    axes = [max(range(3), key=lambda k: extents[k])]
                shelf_id = next((s['id'] for s in annotation['shelves']
                                 if any(path == prefix or path.startswith(prefix + '/') for prefix in s['paths'])), None)
                cover = any(path == prefix or path.startswith(prefix + '/') for prefix in annotation['cover_paths'])
                if sum(g['t'] for g in raw['c']) != len(vertices) // 3:
                    raise ValueError('Invalid material ranges')
                materials = []
                for g in raw['c']:
                    bgr = int(g['c'], 16)
                    materials.append(dict(count=g['t'], color=((bgr & 255) << 16) | (bgr & 0xff00) | ((bgr >> 16) & 255)))
                offset = stream.tell()
                array('f', vertices + normals).tofile(stream)
                rows.append(dict(node_id=node['id'], path=path, name=nodes[path]['name'], matrix=matrix,
                                 offset=offset, floats=len(vertices), materials=materials, bounds=bounds,
                                 policy=policy, resize_axes=axes, rigid_group=rigid_group,
                                 shelf_id=shelf_id, cover=cover,
                                 external_panel=path in annotation['external_panel_paths']))
    if seen != set(by_mesh):
        raise ValueError('Missing exported mesh; preview cannot silently omit geometry')
    external = [r['bounds'] for r in rows if r['external_panel']]
    baseline = [min(b[k] for b in external) for k in range(3)] + [max(b[k+3] for b in external) for k in range(3)]
    groups = {}
    for row in rows:
        key = row['rigid_group'] if row['policy'] == 'rigid' else row['path']
        row['deform_group'] = key
        groups.setdefault(key, []).append(row['bounds'])
    group_bounds = {key: [min(b[k] for b in values) for k in range(3)] + [max(b[k+3] for b in values) for k in range(3)]
                    for key, values in groups.items()}
    shelves = []
    for shelf in annotation['shelves']:
        members = [r for r in rows if r['shelf_id'] == shelf['id']]
        if not members:
            raise ValueError('Shelf has no exported geometry')
        shelves.append(dict(id=shelf['id'], label=shelf['label'], part_count=len(members)))
    model = dict(schema_version=1, kind='workstation_native_preview', units='m', elements=rows,
                 source_sha256=proof['source_sha256'], inventory_sha256=sha(inventory),
                 export_sha256=sha(export), geometry_sha256=sha(output / 'geometry.bin'),
                 baseline_bounds=baseline, group_bounds=group_bounds, shelves=shelves,
                 shelf_axis=annotation['shelf_axis'], mapping_status='preview_mapping',
                 physical_stroke_approved=False, production_approved=False,
                 description='Real native meshes; dimensions deform a concept preview, not CAD features.')
    (output / 'model.json').write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
    return dict(mesh_count=len(rows), shelves=shelves,
                external_mm=[round(1000*(baseline[k+3]-baseline[k]), 3) for k in range(3)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('export', 'receipt', 'inventory', 'mapping', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(convert(args.export, args.receipt, args.inventory, args.mapping, args.output), ensure_ascii=True))
