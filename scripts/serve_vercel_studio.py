"""Local check of the generated Vercel route map, not the desktop CAD server."""
import argparse
from http.server import ThreadingHTTPServer
import importlib.util
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit

ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--port',type=int,default=51345);args=ap.parse_args()
folder=args.folder.resolve();spec=importlib.util.spec_from_file_location('cloud_api',folder/'api/index.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Handler(module.handler):
    def do_GET(self):
        route=urlsplit(self.path).path
        route={'/':'/wizard.html','/wizard/options':'/options.json','/wizard/parts':'/catalog-parts.json'}.get(route,route)
        path=(folder/'public'/route.lstrip('/')).resolve()
        if not path.is_relative_to(folder/'public') or not path.is_file():self.respond(404,dict(error='Not found'));return
        raw=path.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(path)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        route=urlsplit(self.path).path
        if route.startswith('/wizard/'):self.path='/api/index?endpoint='+route.rsplit('/',1)[-1]
        super().do_POST()
    def log_message(self,*args):pass
print('Serving generated Vercel bundle on '+str(args.port),flush=True)
ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
