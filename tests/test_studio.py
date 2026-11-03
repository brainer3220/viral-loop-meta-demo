import sys, unittest, tempfile, json, hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio import MetaAdapter, validate_plan

class Contracts(unittest.TestCase):
 def test_live_disabled_without_matching_permit(self):
  calls=[];a=MetaAdapter(key='fixture-only',transport=lambda *args:calls.append(args))
  with self.assertRaises(PermissionError):a.plan('fictional coffee')
  self.assertEqual(calls,[])
 def test_exact_request_permit_and_output_contract(self):
  plan={'concepts':[{'id':str(i),'title':'Idea','scenes':[{'caption':'Hello','seconds':3}]*3} for i in range(3)]}
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
  a=MetaAdapter(ledger=Path(temporary.name)/'ledger.json',key='fixture-only',transport=lambda p,x:{'output':[{'content':[{'type':'output_text','text':json.dumps(plan)}]}]})
  payload=a.plan_payload('test');permit={'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),'max_cost_usd':.01}
  self.assertEqual(len(a.plan('test',permit)['concepts']),3)
  with self.assertRaises(PermissionError):a.plan('different',permit)
 def test_reject_incomplete_plan(self):
  with self.assertRaises(ValueError):validate_plan({'concepts':[]})
 def test_documented_json_edit_shape(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.png';p.write_bytes(b'fixture')
   x=MetaAdapter.image_payload('edit',p)
   self.assertIn('images',x);self.assertNotIn('image',x)
   self.assertEqual(x['n'],1)
if __name__=='__main__':unittest.main()

class OfflineWorkflow(unittest.TestCase):
 def test_brief_validation_and_template_identity(self):
  from server import make_plan
  p=make_plan('Fictional tea for makers')
  self.assertEqual(p['brief'],'Fictional tea for makers')
  self.assertEqual(len(p['concepts']),3)
  self.assertTrue(p['synthetic'])
 def test_short_brief_rejected(self):
  from server import make_plan
  with self.assertRaises(ValueError):make_plan('')

class Preparation(unittest.TestCase):
 def test_prepare_plan_has_no_network(self):
  import subprocess
  with tempfile.TemporaryDirectory() as d:
   brief=Path(d)/'brief.txt';brief.write_text('Fictional tea')
   out=Path(d)/'request.json'
   subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'live.py'),'prepare-plan','--brief-file',str(brief),'--out',str(out)],check=True)
   data=json.loads(out.read_text());self.assertFalse(data['executed'])
   self.assertEqual(len(data['request_sha256']),64)
 def test_malformed_plan_rejected(self):
  for x in [None, {'concepts':[None]*3}, {'concepts':[{'id':1}]*3}]:
   with self.assertRaises(ValueError):validate_plan(x)

class HardLimits(unittest.TestCase):
 def permit(self,payload):
  return {'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),'max_cost_usd':.01}
 def test_utf8_brief_and_prompt_bounds(self):
  for text in ['', '가'*1366]:
   with self.assertRaises(ValueError):MetaAdapter.plan_payload(text)
  self.assertEqual(MetaAdapter.plan_payload('safe')['max_output_tokens'],2048)
 def test_source_bytes_limit_before_encoding(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'large.png';source.write_bytes(b'x'*(2*1024*1024+1))
   with self.assertRaises(ValueError):MetaAdapter.image_payload('safe',source)
 def test_uncertain_attempt_consumes_persistent_slot(self):
  with tempfile.TemporaryDirectory() as d:
   ledger=Path(d)/'budget.json';calls=[]
   def fail(*args):calls.append(args);raise TimeoutError('uncertain fixture')
   a=MetaAdapter(key='fixture-only',transport=fail,ledger=ledger)
   payload=a.plan_payload('safe')
   with self.assertRaises(TimeoutError):a.plan('safe',self.permit(payload))
   b=MetaAdapter(key='fixture-only',transport=fail,ledger=ledger)
   for brief in ['safe','changed']:
    with self.assertRaises(PermissionError):b.plan(brief,self.permit(b.plan_payload(brief)))
   self.assertEqual(len(calls),1)
 def test_total_image_budget_survives_adapter_restart(self):
  with tempfile.TemporaryDirectory() as d:
   ledger=Path(d)/'budget.json';calls=[]
   for i in range(4):
    a=MetaAdapter(key='fixture-only',transport=lambda *x:calls.append(x) or {},ledger=ledger)
    payload={'model':'muse-image-1.0','n':1,'prompt':str(i)}
    if i<3:a._post('/images/edits',payload,self.permit(payload))
    else:
     with self.assertRaises(PermissionError):a._post('/images/edits',payload,self.permit(payload))
   self.assertEqual(len(calls),3)
 def test_response_bytes_limit(self):
  with tempfile.TemporaryDirectory() as d:
   a=MetaAdapter(key='fixture-only',transport=lambda *x:{'large':'x'*(12*1024*1024)},ledger=Path(d)/'budget.json')
   payload=a.plan_payload('safe')
   with self.assertRaises(ValueError):a.plan('safe',self.permit(payload))

 def test_concurrent_reservation_allows_one_plan(self):
  import concurrent.futures
  with tempfile.TemporaryDirectory() as d:
   ledger=Path(d)/'budget.json'
   def attempt(i):
    adapter=MetaAdapter(key='fixture-only',transport=lambda *x:{},ledger=ledger)
    payload=adapter.plan_payload(str(i))
    try:adapter._post('/responses',payload,self.permit(payload));return True
    except PermissionError:return False
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    self.assertEqual(sum(pool.map(attempt,range(8))),1)

class StaticServing(unittest.TestCase):
 def test_private_files_and_listings_not_served(self):
  import threading,urllib.request,urllib.error
  from http.server import ThreadingHTTPServer
  from server import Handler
  http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   base='http://127.0.0.1:'+str(http.server_port)
   self.assertEqual(urllib.request.urlopen(base+'/').status,200)
   for path in ['/studio.py','/.git/config','/.env','/output/','/brief.txt','/plan-request.json','/permit.json','/%2e%2e/studio.py']:
    for method in ['GET','HEAD']:
     with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(urllib.request.Request(base+path,method=method))
     self.assertEqual(caught.exception.code,404)
  finally:http.shutdown();http.server_close();thread.join()
