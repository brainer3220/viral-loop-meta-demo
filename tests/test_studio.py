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
  a=MetaAdapter(key='fixture-only',transport=lambda p,x:{'output':[{'content':[{'type':'output_text','text':json.dumps(plan)}]}]})
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
