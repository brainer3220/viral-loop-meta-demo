"""Build deterministic synthetic assets and a local review UI. No provider calls."""
from pathlib import Path
import json
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont
from studio import digest, validate_plan

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
plan = validate_plan({'synthetic': True, 'brief': 'A fictional coffee brand for late-night builders.', 'concepts': [
 {'id': 'focus', 'title': 'One more line', 'hook': 'The idea is awake. Are you?', 'scenes': [
  {'caption': 'THE IDEA IS AWAKE.', 'seconds': 3}, {'caption': 'ONE MORE LINE.', 'seconds': 3}, {'caption': 'MAKE ROOM FOR IT.', 'seconds': 3}]},
 {'id': 'ritual', 'title': 'Small rituals', 'hook': 'Good work starts small.', 'scenes': [
  {'caption': 'A QUIET MOMENT.', 'seconds': 3}, {'caption': 'A WARM CUP.', 'seconds': 3}, {'caption': 'A FRESH START.', 'seconds': 3}]},
 {'id': 'break', 'title': 'Take five', 'hook': 'Your best idea needs a break.', 'scenes': [
  {'caption': 'STEP BACK.', 'seconds': 3}, {'caption': 'TAKE A SIP.', 'seconds': 3}, {'caption': 'COME BACK CURIOUS.', 'seconds': 3}]}]})
font_path = next((p for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf'] if Path(p).exists()), None)
font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default(size=36)
small = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default(size=18)
clips=[]
for i, scene in enumerate(plan['concepts'][0]['scenes']):
 im=Image.new('RGB',(720,1280),(20+i*8,38+i*6,37));d=ImageDraw.Draw(im)
 for x in range(0,720,36): d.line((x,0,x,1280),fill=(33+i*6,57+i*4,53))
 d.ellipse((130,300,590,760),fill=(72+i*12,112,91));d.rounded_rectangle((250,405,470,675),radius=35,fill=(237,222,190));d.ellipse((270,420,450,490),fill=(71,43,30))
 d.text((38,60),'VIRAL LOOP / CONTENT STUDIO',font=small,fill='white')
 d.text((38,880),scene['caption'],font=font,fill='white')
 d.text((38,1190),'SYNTHETIC OFFLINE PREVIEW / NO META CALL',font=small,fill=(180,198,189))
 image=OUT/f'scene-{i+1}.png';im.save(image)
 clip=OUT/f'scene-{i+1}.mp4';clips.append(clip)
 subprocess.run(['ffmpeg','-y','-loglevel','error','-loop','1','-i',str(image),'-t','3','-r','24','-vf',"zoompan=z='min(zoom+0.0006,1.08)':d=72:s=720x1280:fps=24",'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p',str(clip)],check=True)
(OUT/'clips.txt').write_text(''.join("file '"+p.name+"'\n" for p in clips))
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','1','-i',str(OUT/'clips.txt'),'-c','copy','-movflags','+faststart',str(OUT/'preview.mp4')],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height,codec_name','-of','json',str(OUT/'preview.mp4')]))
manifest={'mode':'offline-synthetic','provider_calls':0,'selected_concept':'focus','preview_sha256':digest(OUT/'preview.mp4'),'media':probe,'plan':plan}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Synthetic preview ready:', OUT/'preview.mp4',manifest['preview_sha256'])
