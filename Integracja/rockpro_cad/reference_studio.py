"""Local prototype for selecting source families and exporting concept drafts."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit
import webbrowser

from .family_concepts import build_catalog, validate_draft

STATIC = Path(__file__).with_name('reference_studio')


def make_handler(catalog, images, token):
    routes = {name: (STATIC / name, mime) for name, mime in (
        ('index.html', 'text/html; charset=utf-8'), ('app.js', 'text/javascript; charset=utf-8'),
        ('style.css', 'text/css; charset=utf-8'))}
    routes.update({'images/' + name: (path, 'image/png') for name, path in images.items()})
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, mime='application/json; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)
        def endpoint(self):
            prefix = '/' + token + '/'
            path = urlsplit(self.path).path
            return path[len(prefix):] if path.startswith(prefix) else None
        def do_GET(self):
            name = self.endpoint()
            if name == 'catalog.json':
                self.respond(200, json.dumps(catalog, ensure_ascii=False).encode('utf-8'))
            elif name in routes or name == '':
                path, mime = routes[name or 'index.html']
                self.respond(200, path.read_bytes(), mime)
            else:
                self.respond(404, b'{}')
        def do_POST(self):
            origin = self.headers.get('Origin')
            expected_origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.endpoint() != 'validate' or self.headers.get('X-RockPro-Session') != token or origin != expected_origin:
                self.respond(403, b'{}')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32768:
                    raise ValueError('Nieprawidłowy rozmiar szkicu')
                draft = json.loads(self.rfile.read(length).decode('utf-8'))
                receipt = validate_draft(draft, catalog)
                self.respond(200, json.dumps(receipt, ensure_ascii=False).encode('utf-8'))
            except (ValueError, KeyError, TypeError) as exc:
                self.respond(400, json.dumps({'error': str(exc)}, ensure_ascii=False).encode('utf-8'))
        def log_message(self, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    catalog, images = build_catalog(args.bundle)
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(catalog, images, token))
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
