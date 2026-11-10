"""Read-only cloud planner: no database, CAD, filesystem writes or stock access."""
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad import configurator,studio_review


class handler(BaseHTTPRequestHandler):
    def respond(self,status,value):
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status)
        for key,value in [('Content-Type','application/json; charset=utf-8'),('Content-Length',str(len(raw))),
                          ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff')]:
            self.send_header(key,value)
        self.end_headers();self.wfile.write(raw)

    def do_GET(self):
        self.respond(405,dict(error='Planer przyjmuje POST.'))

    def do_POST(self):
        route=parse_qs(urlsplit(self.path).query).get('endpoint',[''])[0]
        if route not in ('preview','convert','review'):
            self.respond(404,dict(error='Nieznana operacja.'));return
        origin=self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            self.respond(403,dict(error='Nieprawidłowe źródło żądania.'));return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32768: raise ValueError('Szkic musi mieć maksymalnie 32 KB.')
            data=json.loads(self.rfile.read(length).decode('utf-8'))
            result=studio_review.review(data) if route=='review' else configurator.preview(data) if route=='preview' else configurator.convert_legacy(data)
            self.respond(200,result)
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError) as exc:
            self.respond(400,dict(error=str(exc)[:300]))


if __name__=='__main__':
    from http.server import ThreadingHTTPServer
    ThreadingHTTPServer(('127.0.0.1',51344),handler).serve_forever()
