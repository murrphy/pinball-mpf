import sys,json
from pathlib import Path
sys.path.insert(0,'/tmp')
from firepower_audit_cpu import CPU
from firepower_audit_decode import m
class Probe(CPU):
 def __init__(self):super().__init__();self.records=[];self.ticks=0
 def step(self):
  if self.pc==0x79cd:self.mem[0x3a]=0 # inject elapsed descriptor delay, no wall-clock claim
  if self.pc in (0x7062,0x7300,0x73e9,0x6c48):self.pc=0xffff;return
  if self.pc==0x6c6c:self.ticks+=self.a;self.mem[0x3a]=0;self.pc=self.popw();return
  if self.pc==0x71cb:self.records.append({'token':f'{self.a:02X}','ticks':self.ticks});self.pc=self.popw();return
  if self.pc==0x77f0:self.records.append({'effect':f'{self.a:02X}','token':f'{self.mem[0x608d+2*(self.a&15)]:02X}'})
  super().step()
rows=[]
c=Probe();c.mem[0x82:0x84]=b'\x00\x10';c.run(0x6ba3);rows.append({'case':'full nine-frame prelude and three releases; nominal explicit waits only','records':c.records})
c=Probe();c.run(0x6bf0);rows.append({'case':'three-release nominal explicit wait counts; excludes execution/IRQ latency','records':c.records})
c=Probe();c.run(0x75b9);rows.append({'case':'accepted first-player start indirect descriptor','records':c.records})
for player in (1,2,3):
 c=Probe();c.mem[0x56]=player;c.run(0x75c7);rows.append({'case':f'added player index {player}','records':c.records})
c=Probe();c.mem[0x19]=0x64;c.run(0x77a8)
rows.append({'case':'POWER completion flags schedule cleanup','timer40':c.mem[0x40],'callback41':f'{c.word(0x41):04X}','timer43':c.mem[0x43],'callback44':f'{c.word(0x44):04X}'})
for busy in (0,1,3,17):
 c=Probe();c.mem[0x19]=0x64;c.mem[0x70]=busy;c.run(0x6f28)
 rows.append({'case':f'POWER cleanup presentation70={busy}','records':c.records,'flags19':f'{c.mem[0x19]:02X}'})
path=Path(__file__).resolve().with_name('foreground_checks.json')
path.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows,indent=2))
