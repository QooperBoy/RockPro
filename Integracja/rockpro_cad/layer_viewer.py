"""Loopback-only viewer for an explicitly selected local native mesh export."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit
import webbrowser
from .part_registry import contract

STATIC=Path(__file__).with_name('viewer3d')
MAX_MODEL_BYTES=8*1024*1024
MAX_GEOMETRY_BYTES=128*1024*1024
MAX_STATIC_BYTES=8*1024*1024


def _read_bounded(path,limit):
    # Bound the read itself, not a previous stat which can race a file replacement.
    with path.open('rb') as stream:data=stream.read(limit+1)
    if len(data)>limit:raise ValueError('Viewer file exceeds byte limit: '+path.name)
    return data


def make_handler(dataset,token):
    dataset=Path(dataset).resolve(strict=True)
    model_bytes=_read_bounded(dataset/'model.json',MAX_MODEL_BYTES)
    model=json.loads(model_bytes.decode('utf-8'))
    if not isinstance(model,dict):raise ValueError('A model metadata object is required')
    if 'registry' in model and model['registry']!=contract():raise ValueError('Registry mismatch; regenerate export')
    if model.get('kind')!='ironcad_native_mesh':raise ValueError('Unknown dataset')
    geometry=_read_bounded(dataset/'geometry.bin',MAX_GEOMETRY_BYTES)
    if hashlib.sha256(geometry).hexdigest()!=model.get('geometry_sha256'):
        raise ValueError('Geometry checksum mismatch')
    # Serve the exact bytes verified above for this session. An export/replacement
    # on disk requires a new viewer; never mix a new model with an old mesh.
    routes={'':(_read_bounded(STATIC/'index.html',MAX_STATIC_BYTES),'text/html; charset=utf-8'),
            'app.js':(_read_bounded(STATIC/'app.js',MAX_STATIC_BYTES),'text/javascript; charset=utf-8'),
            'model.json':(model_bytes,'application/json'),
            'geometry.bin':(geometry,'application/octet-stream')}
    for name in ('three.module.min.js','three.core.min.js','OrbitControls.js'):
        routes['vendor/'+name]=(_read_bounded(STATIC/'vendor'/name,MAX_STATIC_BYTES),'text/javascript')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            prefix='/'+token+'/'
            path=urlsplit(self.path).path
            if not path.startswith(prefix) or path[len(prefix):] not in routes:
                self.send_error(404);return
            data,mime=routes[path[len(prefix):]]
            self.send_response(200);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            view=memoryview(data)
            for offset in range(0,len(view),1024*1024):self.wfile.write(view[offset:offset+1024*1024])
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
