"""Bounded probes of verified L-6 Match bytes; no complete machine emulation."""
import json, sys, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'audio/diagnostics/sound_audit/tools'))
from firepower_audit_cpu import CPU
from firepower_audit_decode import m
CRCS = {'prom1_6.474':'af6eb0b9','prom2.474':'f75ade1a','prom3.474':'242ec687',
        'gamerom.716':'fdd3b983','green1.716':'2145f8ab','green2.716':'1c978a4a'}
for name, crc in CRCS.items():
    assert f'{zlib.crc32((Path("/tmp/firepower-audit-l6")/name).read_bytes()):08x}' == crc

class Probe(CPU):
    def __init__(self):
        super().__init__()
        self.records = []
        self.ticks = 0
    def step(self):
        if self.pc in (0x79cd, 0x768e):
            self.ticks += self.mem[0x3a]
            self.mem[0x3a] = 0
        if self.pc == 0x71cb:
            self.records.append({'token':f'{self.a:02x}','ticks':self.ticks,'credits_bcd':f'{self.mem[7]:02x}'})
            self.pc = self.popw()
            return
        if self.pc in (0x76cc, 0x7aa9):
            self.pc = self.popw()
            return
        super().step()

rows=[]
for digit in range(10):
    c=Probe()
    c.mem[0x46]=digit<<4
    c.run(0x7067,stop={0x706e})
    assert c.mem[0x46]==((digit+1)%10)<<4
    rows.append({'case':'decimal phase increment','before':digit*10,'after':(digit+1)%10*10})
for players in range(1,5):
    for digit in range(10):
        for winners in range(players+1):
            c=Probe()
            c.mem[0x46]=digit<<4
            c.mem[0x56]=players-1
            c.mem[0x03]=0xf6
            c.mem[0x18b:0x18d]=bytes([1,2]) # max credits12
            for p in range(players):
                c.mem[4*p+2]=(digit if p<winners else (digit+1)%10)<<4
            c.run(0x7426,stop={0x746b})
            assert c.mem[0x03]==digit<<4
            assert c.mem[0x16]&0x20
            assert c.mem[7]==winners
            tokens=[x['token'] for x in c.records]
            assert tokens==(['9c']+['4d']*winners if winners else [])
            if winners:
                assert c.records[1]['ticks']==128
                assert [x['ticks'] for x in c.records[1:]]==[128+16*i for i in range(winners)]
            rows.append({'case':'match','players':players,'number':digit*10,'winners':winners,'records':c.records})
for maximum, existing, winners in [(12,11,4),(12,12,4),(0,0,4)]:
    c=Probe()
    c.mem[0x56]=3
    c.mem[0x46]=0x90
    c.mem[0x18b:0x18d]=bytes([maximum//10,maximum%10])
    c.mem[7]=(existing//10)*16+existing%10
    for p in range(4):c.mem[4*p+2]=0x90
    c.run(0x7426,stop={0x746b})
    expected=existing+winners if maximum>existing else existing
    assert c.mem[7]==(expected//10)*16+expected%10
    assert [x['token'] for x in c.records].count('4d')==max(0,expected-existing)
    assert c.records[0]['token']=='9c' # free play/max still gets the sound/presentation
    rows.append({'case':'credit cap/free play','maximum':maximum,'existing':existing,'after':expected,'records':c.records})
c=Probe();c.mem[0x19b:0x19d]=bytes([0,1]);c.mem[3]=0xf6
c.run(0x7426,stop={0x746b})
assert not c.mem[0x16]&0x20 and c.mem[3]==0xf6 and not c.records
rows.append({'case':'disabled','display03_bcd':'f6','match_lamp':False})
# Generic no-speech byte1C is absent from speech selector (already pinned model).
model=json.loads((ROOT/'audio/speech_model.json').read_text(encoding='utf-8'))
assert not model['commands']['1c_0']['speech']
for digit in (0, 9):
    c=Probe()
    c.mem[0x46]=digit<<4
    c.mem[0x56]=0
    c.mem[2]=(digit<<4)|1
    c.run(0x7426,stop={0x746b})
    assert not c.records
    rows.append({'case':'same tens but different ones does not match','number':digit*10,'score_last_byte':f'{c.mem[2]:02x}'})
report={'rom_crc32':CRCS,'descriptor6224_hex':m[0x6224:0x6227].hex(),
        'credit_spacing_ticks':m[0x60ce],'cases':rows}
Path(__file__).with_name('l6_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('L-6 Match probes passed:',len(rows))
