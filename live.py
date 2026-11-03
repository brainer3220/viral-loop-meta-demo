"""Manual live boundary. Nothing here runs at import or from the rehearsal UI."""
import argparse
import hashlib
import json
from pathlib import Path
from studio import MetaAdapter, validate_plan

def request_hash(payload):
 return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser(description='Prepare exact requests offline, or execute one separately approved request. No retries.')
 p.add_argument('action',choices=['prepare-plan','execute-plan','prepare-images','execute-image'])
 p.add_argument('--brief-file',type=Path);p.add_argument('--plan-file',type=Path)
 p.add_argument('--source',type=Path);p.add_argument('--selected');p.add_argument('--scene',type=int,choices=[1,2,3])
 p.add_argument('--permit',type=Path);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();adapter=MetaAdapter()
 if a.action.endswith('plan'):
  if not a.brief_file:p.error('--brief-file required')
  brief=a.brief_file.read_text().strip();payload=adapter.plan_payload(brief)
  if a.action=='prepare-plan':result={'path':'/responses','payload':payload,'request_sha256':request_hash(payload),'executed':False}
  else:
   if not a.permit:p.error('A separately approved exact-request --permit is required')
   result=adapter.plan(brief,json.loads(a.permit.read_text()))
 else:
  if not a.plan_file or not a.selected or not a.source:p.error('--plan-file, --selected and --source required')
  plan=validate_plan(json.loads(a.plan_file.read_text()));concept=next(c for c in plan['concepts'] if c['id']==a.selected)
  def prompt(s):return 'Fictional brand illustration. Vertical frame, no text. '+concept['title']+'. '+s['caption']+'. Brief: '+str(plan.get('brief',''))
  if a.action=='prepare-images':result={'executed':False,'requests':[{'scene':i+1,'path':'/images/edits','payload':(x:=adapter.image_payload(prompt(s),a.source)),'request_sha256':request_hash(x)} for i,s in enumerate(concept['scenes'])]}
  else:
   if not a.scene or not a.permit:p.error('--scene and separately approved --permit required')
   result=adapter.image(prompt(concept['scenes'][a.scene-1]),a.source,a.out,json.loads(a.permit.read_text()))
   a.out.with_suffix('.provenance.json').write_text(json.dumps(result,indent=2));return
 a.out.write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
