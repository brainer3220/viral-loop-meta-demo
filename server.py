"""Loopback-only offline workflow. No provider or credential endpoints."""
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess
import threading
from studio import validate_plan
ROOT=Path(__file__).resolve().parent
LOCK=threading.Lock()
def make_plan(brief):
    brief=brief.strip()
    if not 3 <= len(brief) <= 1000: raise ValueError('Use a brief between 3 and 1000 characters')
    return validate_plan({'synthetic':True,'brief':brief,'concepts':[
      {'id':key,'title':title,'hook':hook,'scenes':[{'caption':text,'seconds':3} for text in captions]}
      for key,title,hook,captions in [
       ('focus','One more step','A story about making progress.',['THE IDEA IS AWAKE.','ONE MORE STEP.','MAKE ROOM FOR IT.']),
       ('ritual','Small rituals','Good work starts small.',['A QUIET MOMENT.','A SMALL RITUAL.','A FRESH START.']),
       ('break','Take five','Your next idea needs a break.',['STEP BACK.','TAKE FIVE.','COME BACK CURIOUS.'])]]})
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def _public_path(self):
  relative=unquote(urlsplit(self.path).path).lstrip('/')
  if relative in ('','index.html'):relative='index.html'
  allowed={'index.html','output/manifest.json','output/preview.mp4',
           'output/scene-1.png','output/scene-2.png','output/scene-3.png'}
  if relative not in allowed:return False
  target=ROOT/relative
  return target.is_file() and target.resolve().is_relative_to(ROOT.resolve()) and not target.is_symlink()
 def do_GET(self):
  if not self._public_path():self.send_error(404);return
  super().do_GET()
 def do_HEAD(self):
  if not self._public_path():self.send_error(404);return
  super().do_HEAD()
 def do_POST(self):
  if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765','http://localhost:8765'):
   self.send_error(403);return
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<20000:raise ValueError('Invalid request size')
   data=json.loads(self.rfile.read(n))
   if self.path=='/api/plan':out=make_plan(str(data.get('brief','')))
   elif self.path=='/api/render':
    if data.get('rights') is not True:raise ValueError('Confirm asset rights before rendering')
    plan=make_plan(str(data.get('brief','')));selected=data.get('selected')
    if selected not in {x['id'] for x in plan['concepts']}:raise ValueError('Choose a direction')
    with LOCK:
     (ROOT/'output').mkdir(exist_ok=True)
     p=ROOT/'output/plan.json';p.write_text(json.dumps(plan))
     subprocess.run(['python3',str(ROOT/'demo.py'),'--plan',str(p),'--selected',selected],cwd=ROOT,check=True,timeout=120,capture_output=True)
     out=json.loads((ROOT/'output/manifest.json').read_text())
   else:self.send_error(404);return
   body=json.dumps(out).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  except (ValueError,KeyError,subprocess.SubprocessError) as e:
   body=json.dumps({'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
