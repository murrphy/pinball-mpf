"""Reproduce verified speech firmware PIA transitions; no ROMs are distributed.

Requires the reused /tmp/firepower_audit_cpu.py, firepower_audit_decode.py,
verified /tmp/firepower-audit-l6 ROMs and cached MAME cycle/disassembly sources.
Run with --verify to check existing production without changing assets.
The HC55516 integer decoder below follows MAME's BSD-3-Clause implementation
by Aaron Giles and Jonathan Gevaryahu. See MAME_DECODER_LICENSE.txt.
"""
import sys, json, hashlib, wave, array, math, struct, subprocess
from pathlib import Path
sys.path.insert(0, '/tmp')
from firepower_audit_cpu import CPU
from firepower_audit_decode import m, listing
ROOT = Path(__file__).resolve().parents[2]
CLOCK = 3579545 / 4
RATE = 48000
WORDS = {'fire':0xb000,'power':0xb3d0,'one':0xb7a0,'two':0xbbf0,'three':0xc000,
         'enemy':0xc440,'destroyed':0xc850,'mission':0xcde0,'accomplished':0xd290,
         'you':0xd820,'are':0xdc20}
class SpeechCPU(CPU):
 def __init__(self):
  super().__init__(); self.edges=[]; self.data=0; self.words=[]; self.interrupts=[]
 def write(self,p,v):
  super().write(p,v)
  if p==0x401:self.data=(v>>3)&1
  if p==0x403:self.edges.append((self.clock,self.data,(v>>3)&1))
 def step(self):
  if self.pc in (0xdeb1,0xdece) and self.x in WORDS.values():
   self.words.append({'word':next(k for k,v in WORDS.items() if v==self.x), 'cycle':self.clock})
  if self.mem[self.pc]==0x0e:self.interrupts.append(self.clock)
  super().step()
def signed(v):return ((v+512)&1023)-512
def render(cpu):
 syl=63; integrator=0; shift=0; events=[(0,0)]
 for cycle,bit,rising in cpu.edges:
  frozen=(integrator>=384 and not bit) or (integrator<=-384 and bit)
  if rising:
   shift=((shift<<1)|bit)&7
   if not frozen:syl=(syl+((~syl&0xfc0)>>6)+(0 if shift in (0,7) else 0xfc1))&4095
   delta=signed(((~integrator)>>4)+1)
  else:delta=signed(-max(2,syl>>6) if shift&1 else max(2,syl>>6))
  if not frozen:integrator=signed(integrator+delta)
  events.append((cycle,(integrator<<6)|(((integrator&1023)^512)>>4)))
 # Integrate sample holds at the actual firmware cycle timestamps. End at RTS.
 events.append((cpu.clock,0)); pcm=array.array('h'); index=0
 for frame in range(math.ceil(cpu.clock*RATE/CLOCK)):
  lo=frame*CLOCK/RATE; hi=min((frame+1)*CLOCK/RATE,cpu.clock); pos=lo; total=0
  while index+1<len(events) and events[index+1][0]<=pos:index+=1
  while pos<hi:
   end=min(hi,events[index+1][0]) if index+1<len(events) else hi
   total+=(end-pos)*events[index][1];pos=end
   if index+1<len(events) and pos>=events[index+1][0]:index+=1
  pcm.append(max(-32768,min(32767,round(total/(CLOCK/RATE)))))
 if sys.byteorder!='little':pcm.byteswap()
 return pcm.tobytes()
def probe(raw,state=0,selector=0):
 cpu=SpeechCPU();cpu.mem[2]=state;cpu.mem[9]=selector;cpu.run(0xddf6,a=raw|0x20)
 return cpu
def main():
 out=ROOT/'audio/speech_research';out.mkdir(exist_ok=True)
 model={'clock_hz':CLOCK,'sample_rate':RATE,'entry':'DDF6','decoder_source_sha256':hashlib.sha256(Path('/tmp/firepower-speech-hc55516.cpp').read_bytes()).hexdigest(),'commands':{},'phrases':{},'random_selectors':[]}
 assets=ROOT/'sounds/voice/l6';assets.mkdir(exist_ok=True)
 for raw in range(32):
  states=range(3) if raw==24 else range(16) if raw==27 else range(1)
  for state in states:
   cpu=probe(raw,state if raw==24 else 0,state if raw==27 else 0)
   key=f'{raw:02x}_{state}'
   if not cpu.edges:
    model['commands'][key]={'speech':False,'returned_command':cpu.a&31,'next_state':cpu.mem[2]};continue
   name=f'table_{cpu.word(0x18):04x}' # pointer at terminator, unique execution descriptor incl fallthrough
   # Identify by exact word sequence and timing, not by the final pointer alone.
   edgebytes=b''.join(struct.pack('<IBB',*e) for e in cpu.edges)
   identity=hashlib.sha256(edgebytes).hexdigest()
   name='phrase_'+identity[:12]
   entry={'speech':True,'phrase':name,'returned_command':cpu.a&31,'next_state':cpu.mem[2]}
   model['commands'][key]=entry
   if raw==27:model['random_selectors'].append(name)
   if name not in model['phrases']:
    data=render(cpu);path=assets/(name+'.wav')
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(data)
    model['phrases'][name]={'words':cpu.words,'cycles':cpu.clock,'duration':cpu.clock/CLOCK,'clock_edges':len(cpu.edges),'edge_sha256':identity,'interruptible':raw==27,'cli_cycles':cpu.interrupts,'production_file':str(path.relative_to(ROOT)),'wav_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pcm_sha256':hashlib.sha256(data).hexdigest()}
   print(key, [w['word'] for w in cpu.words], round(cpu.clock/CLOCK,6), cpu.mem[2],cpu.a&31)
 (ROOT/'audio/speech_model.json').write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
 (out/'speech_disassembly.txt').write_text(listing(0xddf1,0xdffb),encoding='utf-8')
 # Keep originals untouched; characterize every existing speech WAV.
 inventory=[]
 for path in sorted((ROOT/'sounds/voice').glob('*.wav')):
  with wave.open(str(path),'rb') as w:
   channels=w.getnchannels();width=w.getsampwidth();rate=w.getframerate();frames=w.getnframes();data=w.readframes(frames)
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','s16le','-ac','1','-ar','48000','-'])
  samples=array.array('h',raw); peak=max(abs(x) for x in samples);active=[i for i,x in enumerate(samples) if abs(x)>peak*.02]
  inventory.append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'channels':channels,'width':width,'rate':rate,'duration':frames/rate,'peak':peak,'rms':math.sqrt(sum(x*x for x in samples)/len(samples)),'onset':active[0]/48000,'end':active[-1]/48000})
 (out/'existing_assets.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
def verify():
 model=json.loads((ROOT/'audio/speech_model.json').read_text(encoding='utf-8'))
 for rom in model.get('roms',[]):
  data=(Path('/tmp/firepower-audit-l6')/rom['file']).read_bytes()
  assert hashlib.sha1(data).hexdigest()==rom['sha1'],rom['file']
 checks=[]
 for key,expected in model['commands'].items():
  raw_text,state_text=key.split('_');raw=int(raw_text,16);state=int(state_text)
  cpu=probe(raw,state if raw==24 else 0,state if raw==27 else 0)
  assert bool(cpu.edges)==expected['speech'],key
  assert cpu.a&31==expected['returned_command'],key
  if cpu.edges:
   phrase=model['phrases'][expected['phrase']]
   assert cpu.words==phrase['words'] and cpu.clock==phrase['cycles'],key
   assert hashlib.sha256(b''.join(struct.pack('<IBB',*e) for e in cpu.edges)).hexdigest()==phrase['edge_sha256'],key
   assert hashlib.sha256(render(cpu)).hexdigest()==phrase['pcm_sha256'],key
   assert hashlib.sha256((ROOT/phrase['production_file']).read_bytes()).hexdigest()==phrase['wav_sha256'],key
   assert (cpu.interrupts[0]<cpu.edges[0][0])==(raw==27),key
  checks.append({'command':key,'cycles':cpu.clock,'edges':len(cpu.edges),'passed':True})
 (ROOT/'audio/speech_research/verification.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
 print('Verified',len(checks),'firmware executions and all production PCM/hash identities')

if __name__=='__main__':
 if '--verify' in sys.argv:verify()
 else:main()

