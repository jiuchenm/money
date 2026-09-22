"""Serve built site and private data on loopback. Never exposes raw data to Pages."""
import argparse
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit
from collect import ROOT

p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--port',type=int,default=4174);a=p.parse_args()
site=(ROOT/'nikki/site/dist').resolve();private=(ROOT/'research-private'/f'tencent-{a.date}'/'site-data').resolve()
class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        clean=unquote(urlsplit(path).path)
        prefix='/money/data/tencent/'
        base=private if clean.startswith(prefix) else site
        relative=clean[len(prefix):] if clean.startswith(prefix) else clean.removeprefix('/money/').lstrip('/')
        resolved=(base/relative).resolve()
        if not resolved.is_relative_to(base):return str(base/'not-found')
        return str(resolved)
    def end_headers(self):
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
print(f'Local Tencent page: http://127.0.0.1:{a.port}/money/#/tencent',flush=True)
ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
