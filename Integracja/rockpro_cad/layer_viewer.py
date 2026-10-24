"""Loopback-only viewer for an explicitly selected local native mesh export."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit
import webbrowser

STATIC=Path(__file__).with_name('viewer3d')


def make_handler(dataset,token):
    dataset=Path(dataset).resolve(strict=True)
    model=json.loads((dataset/'model.json').read_text(encoding='utf-8'))
    if model.get('kind')!='ironcad_native_mesh':raise ValueError('Unknown dataset')
    if hashlib.sha256((dataset/'geometry.bin').read_bytes()).hexdigest()!=model['geometry_sha256']:
        raise ValueError('Geometry checksum mismatch')
    routes={'':(STATIC/'index.html','text/html; charset=utf-8'),
            'app.js':(STATIC/'app.js','text/javascript; charset=utf-8'),
            'model.json':(dataset/'model.json','application/json'),
            'geometry.bin':(dataset/'geometry.bin','application/octet-stream')}
    for name in ('three.module.min.js','three.core.min.js','OrbitControls.js'):
        routes['vendor/'+name]=(STATIC/'vendor'/name,'text/javascript')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            prefix='/'+token+'/'
            path=urlsplit(self.path).path
            if not path.startswith(prefix) or path[len(prefix):] not in routes:
                self.send_error(404);return
            file,mime=routes[path[len(prefix):]]
            self.send_response(200);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(file.stat().st_size))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            with file.open('rb') as stream:
                while block:=stream.read(1024*1024):self.wfile.write(block)
        def log_message(self,*args):pass
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',required=True,type=Path);p.add_argument('--no-browser',action='store_true');a=p.parse_args()
    token=secrets.token_urlsafe(24)
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(a.dataset,token))
    url=f'http://127.0.0.1:{server.server_port}/{token}/'
    print(url,flush=True)
    if not a.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()
