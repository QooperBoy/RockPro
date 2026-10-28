"""Local prototype for selecting source families and exporting concept drafts."""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import re
from urllib.parse import urlsplit
import webbrowser

from .family_concepts import build_catalog, validate_draft
from . import configurator
from . import studio_parts
from . import part_images
from . import source_parts
from . import company_catalog, supplier_parts
from . import part_preferences
from . import manufacturer_images
from . import studio_review

STATIC = Path(__file__).with_name('reference_studio')
IMPORT_MAP = '{"imports":{"three":"./vendor/three.module.min.js"}}'
IMPORT_HASH = base64.b64encode(hashlib.sha256(IMPORT_MAP.encode()).digest()).decode()


def load_preview(folder, catalog, model_key='M04'):
    folder = Path(folder).resolve(strict=True)
    model = json.loads((folder / 'model.json').read_text(encoding='utf-8'))
    reference = next(v for f in catalog['families'] for v in f['variants'] if v['id'] == model_key)
    if model.get('kind') not in ('workstation_native_preview', 'reference_native_preview') or model.get('units') != 'm':
        raise ValueError('Unsupported preview format')
    if model.get('model_key', 'M04') != model_key:
        raise ValueError('Preview key does not match selected variant')
    if model['source_sha256'] != reference['source_sha256'] or model['inventory_sha256'] != reference['inventory_sha256']:
        raise ValueError('Preview is bound to another reference revision')
    elements, empty_parts = model.get('elements', []), model.get('source_empty_parts', [])
    if len(elements)+len(empty_parts) != reference['part_count']:
        raise ValueError('Preview does not account for every inventoried part')
    paths = [r['path'] for r in elements] + [r['path'] for r in empty_parts]
    if (len(set(paths)) != len(paths) or set(paths) != set(reference['part_paths'])
            or {r['path'] for r in empty_parts} != set(reference['source_empty_paths'])):
        raise ValueError('Preview part identity or source-empty accounting mismatch')
    if hashlib.sha256((folder / 'geometry.bin').read_bytes()).hexdigest() != model['geometry_sha256']:
        raise ValueError('Preview geometry checksum mismatch')
    return folder, model


def load_previews(index_path, catalog):
    index_path = Path(index_path).resolve(strict=True)
    index = json.loads(index_path.read_text(encoding='utf-8'))
    if index.get('schema') != 'rockpro.preview-index/1':
        raise ValueError('Unsupported preview index')
    previews = {}
    for key, relative in index['models'].items():
        folder = (index_path.parent / relative).resolve(strict=True)
        if not folder.is_relative_to(index_path.parent):
            raise ValueError('Preview dataset must stay inside its selected library')
        previews[key] = load_preview(folder, catalog, key)
    return previews


def make_handler(catalog, images, token, preview=None, previews=None, hardware_images=None):
    hardware_images = hardware_images or {}
    routes = {name: (STATIC / name, mime) for name, mime in (
        ('index.html', 'text/html; charset=utf-8'), ('app.js', 'text/javascript; charset=utf-8'),
        ('style.css', 'text/css; charset=utf-8'), ('workstation3d.js', 'text/javascript; charset=utf-8'),
        ('reference3d.js', 'text/javascript; charset=utf-8'),
        ('wizard.html', 'text/html; charset=utf-8'), ('wizard.js', 'text/javascript; charset=utf-8'),
        ('wizard3d.js', 'text/javascript; charset=utf-8'), ('wizard.css', 'text/css; charset=utf-8'),
        ('parts-picker.js', 'text/javascript; charset=utf-8'),
        ('placement-editor.js', 'text/javascript; charset=utf-8'),
        ('closure-editor.js', 'text/javascript; charset=utf-8'),
        ('viewport-ui.js', 'text/javascript; charset=utf-8'),
        ('studio-shell.js', 'text/javascript; charset=utf-8'),
        ('studio-shell.css', 'text/css; charset=utf-8'),
        ('placement3d.js', 'text/javascript; charset=utf-8'),
        ('mesh-codec.js', 'text/javascript; charset=utf-8'),
        ('structure3d.js', 'text/javascript; charset=utf-8'),
        ('company-parts.html','text/html; charset=utf-8'),
        ('company-parts.js','text/javascript; charset=utf-8'),
        ('company-parts.css','text/css; charset=utf-8'),
        ('part-preferences.js','text/javascript; charset=utf-8'),
        ('part-preferences.css','text/css; charset=utf-8'),
        ('cost-summary.js','text/javascript; charset=utf-8'),
        ('cost_math.mjs','text/javascript; charset=utf-8'),
        ('review-panel.js','text/javascript; charset=utf-8'),
        ('placement_math.mjs', 'text/javascript; charset=utf-8'),
        ('scene-controls.js', 'text/javascript; charset=utf-8'),
        ('preview_math.mjs', 'text/javascript; charset=utf-8'), ('favicon.svg', 'image/svg+xml'))}
    vendor = STATIC.parent / 'viewer3d' / 'vendor'
    for name in ('three.module.min.js', 'three.core.min.js', 'OrbitControls.js', 'three-viewport-gizmo.js'):
        routes['vendor/' + name] = (vendor / name, 'text/javascript; charset=utf-8')
    if preview:
        folder, model = preview
        for name, mime in (('model.json', 'application/json'), ('geometry.bin', 'application/octet-stream')):
            routes['workstation/' + name] = (folder / name, mime)
    for key, (folder, model) in (previews or {}).items():
        for name, mime in (('model.json', 'application/json'), ('geometry.bin', 'application/octet-stream')):
            routes['models/' + key + '/' + name] = (folder / name, mime)
    routes.update({'images/' + name: (path, 'image/png') for name, path in images.items()})
    company_catalog.images()  # Verify the optional snapshot assets before serving.
    routes.update({row['metadata']['url']: (row['path'], row['mime']) for row in hardware_images.values()})
    routes.update({row['metadata']['mesh_url']: (row['mesh_path'], 'application/json') for row in hardware_images.values() if 'mesh_path' in row})
    routes.update({row['metadata']['url']: (row['path'], row['mime']) for row in manufacturer_images.routes().values()})
    routes.update(supplier_parts.routes())
    def preference_ids():
        parts=part_images.decorate(studio_parts.catalog(),hardware_images)
        return {r['id'] for r in parts['items'] if r['show_as_complete_part']}|{r['id'] for r in company_catalog.catalog()['items']}
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, mime='application/json; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'sha256-" + IMPORT_HASH + "'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except ConnectionError:
                pass  # Browser navigation can cancel a large preview download.
        def endpoint(self):
            prefix = '/' + token + '/'
            path = urlsplit(self.path).path
            return path[len(prefix):] if path.startswith(prefix) else None
        def do_GET(self):
            name = self.endpoint()
            if name == 'catalog.json':
                self.respond(200, json.dumps(catalog, ensure_ascii=False).encode('utf-8'))
            elif name == 'wizard/options':
                self.respond(200, json.dumps(dict(types=configurator.TYPES, faces=configurator.FACES), ensure_ascii=False).encode())
            elif name == 'wizard/parts':
                self.respond(200, json.dumps(company_catalog.picker_entries(company_catalog.decorate(manufacturer_images.decorate(part_images.decorate(studio_parts.catalog(), hardware_images)))), ensure_ascii=False).encode())
            elif name == 'company/catalog':
                parts=part_images.decorate(studio_parts.catalog(),hardware_images)
                self.respond(200,json.dumps(company_catalog.catalog(parts),ensure_ascii=False).encode())
            elif name and name.startswith('company-images/'):
                asset=company_catalog.images().get(name)
                if asset:self.respond(200,asset[0].read_bytes(),asset[1])
                else:self.respond(404,b'{"error":"Unknown company image"}')
            elif name == 'wizard/drafts':
                self.respond(200, json.dumps(configurator.list_drafts(), ensure_ascii=False).encode())
            elif name == 'parts/preferences':
                try:self.respond(200,json.dumps(part_preferences.read(preference_ids()),ensure_ascii=False).encode())
                except ValueError as exc:self.respond(400,json.dumps({'error':str(exc)},ensure_ascii=False).encode())
            elif name and name.startswith('wizard/drafts/'):
                try:
                    self.respond(200, json.dumps(configurator.read_draft(name.rsplit('/', 1)[1]), ensure_ascii=False).encode())
                except ValueError as exc:
                    self.respond(404, json.dumps({'error': str(exc)}).encode())
            elif name in routes or name == '':
                path, mime = routes[name or 'index.html']
                self.respond(200, path.read_bytes(), mime)
            else:
                self.respond(404, b'{}')
        def do_POST(self):
            origin = self.headers.get('Origin')
            expected_origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.endpoint() not in ('validate', 'wizard/preview', 'wizard/review', 'wizard/save', 'wizard/convert','parts/preferences') or self.headers.get('X-RockPro-Session') != token or origin != expected_origin:
                self.respond(403, b'{}')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32768:
                    raise ValueError('Nieprawidłowy rozmiar szkicu')
                draft = json.loads(self.rfile.read(length).decode('utf-8'))
                if self.endpoint() == 'parts/preferences':
                    receipt=part_preferences.set_favorite(draft,preference_ids())
                elif self.endpoint() == 'wizard/preview':
                    receipt = configurator.preview(draft)
                elif self.endpoint() == 'wizard/review':
                    receipt = studio_review.review(draft)
                elif self.endpoint() == 'wizard/convert':
                    receipt = configurator.convert_legacy(draft)
                elif self.endpoint() == 'wizard/save':
                    if not isinstance(draft, dict) or set(draft) != {'draft', 'id', 'expected_revision'}:
                        raise ValueError('Nieprawidłowe polecenie zapisu')
                    receipt = configurator.save_draft(draft['draft'], draft['id'], draft['expected_revision'])
                else:
                    receipt = validate_draft(draft, catalog)
                self.respond(200, json.dumps(receipt, ensure_ascii=False).encode('utf-8'))
            except configurator.DraftConflict as exc:
                self.respond(409, json.dumps({'error': str(exc)}, ensure_ascii=False).encode())
            except (ValueError, KeyError, TypeError) as exc:
                self.respond(400, json.dumps({'error': str(exc)}, ensure_ascii=False).encode('utf-8'))
        def log_message(self, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--workstation', type=Path, help='Receipt-bound converted native mesh folder')
    parser.add_argument('--previews', type=Path, help='Private index of receipt-bound preview datasets')
    parser.add_argument('--part-images', type=Path, help='Local verified part thumbnail folder')
    parser.add_argument('--source-parts', type=Path, help='Optional source-bound candidate catalogue')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--session-token', help='Reuse a local session URL when restarting the prototype')
    args = parser.parse_args()
    if args.source_parts:os.environ['ROCKPRO_SOURCE_PARTS']=str(args.source_parts.resolve(strict=True))
    catalog, images = build_catalog(args.bundle)
    preview = load_preview(args.workstation, catalog) if args.workstation else None
    previews = load_previews(args.previews, catalog) if args.previews else {}
    if preview:
        previews.setdefault('M04', preview)
    if previews:
        catalog['previews'] = {key: dict(source_sha256=model['source_sha256'],
            baseline_external_mm=[1000*(model['baseline_bounds'][k+3]-model['baseline_bounds'][k]) for k in range(3)],
            url='models/'+key, motions={m['id']: dict(min=m['min'], max=m['max']) for m in model.get('motions',
                [dict(s, min=0, max=500) for s in model.get('shelves', [])])})
            for key, (_, model) in previews.items()}
    if preview:
        model = preview[1]
        catalog['workstation_preview'] = dict(source_sha256=model['source_sha256'],
            baseline_external_mm=[1000*(model['baseline_bounds'][k+3]-model['baseline_bounds'][k]) for k in range(3)])
    token = args.session_token or secrets.token_urlsafe(24)
    if not re.fullmatch(r'[A-Za-z0-9_-]{24,80}', token):
        parser.error('Invalid local session token')
    image_folder = args.part_images or (part_images.DEFAULT_FOLDER if part_images.DEFAULT_FOLDER.exists() else None)
    hardware_images = part_images.load(image_folder)
    source_images=source_parts.configured_path().parent/'images'
    if source_images.is_dir():
        imported_images=part_images.load(source_images)
        if hardware_images.keys()&imported_images.keys():raise ValueError('Duplicate part image between packages')
        hardware_images.update(imported_images)
    requested_images=Path(__file__).resolve().parents[2]/'artifacts/studio-requested-parts/images'
    if requested_images.is_dir():hardware_images.update(part_images.load(requested_images))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(catalog, images, token, preview, previews, hardware_images))
    server.timeout = 1
    url = f'http://127.0.0.1:{server.server_port}/{token}/'
    print(url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
