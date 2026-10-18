import json, math, array, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
model=json.loads((ROOT/'audio/speech_model.json').read_text(encoding='utf-8'))
# Reuse the earlier standard-library FFT, without running its full inventory.
exec(Path('/tmp/firepower_audit_fingerprint.py').read_text(encoding='utf-8').split('rows=[]')[0])
def samples(path):
 data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ac','1','-ar','8000','-f','s16le','-'])
 return [v/32768 for v in array.array('h',data)]
def fingerprint(x):
 spectrum=[0.]*257
 for i in range(0,len(x)-512,128):
  f=fft([complex(x[i+k]*(.5-.5*math.cos(2*math.pi*k/511))) for k in range(512)])
  for k in range(1,257):spectrum[k]+=abs(f[k])**2
 return [math.sqrt(v) for v in spectrum]
def cosine(a,b):return sum(x*y for x,y in zip(a,b))/math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
refs={};durations={}
for phrase in model['phrases'].values():
 x=samples(ROOT/phrase['production_file'])
 for i,w in enumerate(phrase['words']):
  start=w['cycle']/model['clock_hz'];end=phrase['words'][i+1]['cycle']/model['clock_hz'] if i+1<len(phrase['words']) else phrase['duration']
  if w['word'] not in refs:
   refs[w['word']]=fingerprint(x[round(start*8000):round(end*8000)]);durations[w['word']]=end-start
 # YOU ARE is a contiguous ROM range, not a single vocabulary word.
 if [w['word'] for w in phrase['words'][:2]]==['you','are'] and 'you_are' not in refs:
  start=phrase['words'][0]['cycle']/model['clock_hz'];end=phrase['words'][2]['cycle']/model['clock_hz']
  refs['you_are']=fingerprint(x[round(start*8000):round(end*8000)]);durations['you_are']=end-start
 if [w['word'] for w in phrase['words'][:2]]==['fire','power'] and 'fire_power' not in refs:
  start=phrase['words'][0]['cycle']/model['clock_hz'];end=phrase['words'][2]['cycle']/model['clock_hz'] if len(phrase['words'])>2 else phrase['duration']
  refs['fire_power']=fingerprint(x[round(start*8000):round(end*8000)]);durations['fire_power']=end-start
result=[]
for path in sorted((ROOT/'sounds/voice').glob('*.wav')):
 x=samples(path);spectrum=fingerprint(x)
 scores=sorted(((name,cosine(spectrum,ref)) for name,ref in refs.items()),key=lambda v:-v[1])
 result.append({'asset':path.name,'reference_duration':durations[path.stem],'asset_duration':len(x)/8000,'spectral_cosines':scores,'classification':'D: spectral evidence only; exact pronunciation/trim/gain identity not proven. Original retained; whole-phrase C asset used.'})
(ROOT/'audio/speech_research/asset_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
for item in result:print(item['asset'],item['spectral_cosines'][:3],round(item['reference_duration'],5))
