"""Bounded verified-byte probes. Reuses existing local ROM/interpreter caches.
No ROM downloads, production regeneration or full hardware emulation.
"""
import hashlib
import json
from pathlib import Path
import sys
import zlib

TOOLS = Path(__file__).resolve().parents[1] / 'audio/diagnostics/sound_audit/tools'
sys.path.insert(0, str(TOOLS))
from firepower_audit_cpu import CPU
from firepower_audit_decode import m

EXPECTED = {'prom1_6.474': 'af6eb0b9', 'prom2.474': 'f75ade1a',
            'prom3.474': '242ec687', 'gamerom.716': 'fdd3b983',
            'green1.716': '2145f8ab', 'green2.716': '1c978a4a'}
for name, crc in EXPECTED.items():
    data = (Path('/tmp/firepower-audit-l6') / name).read_bytes()
    assert f'{zlib.crc32(data):08x}' == crc


class Probe(CPU):
    def __init__(self):
        super().__init__()
        self.records = []
        self.mem[0x78] = 0x80

    def step(self):
        if self.pc in (0x7300, 0x7062):
            self.pc = 0xffff
            return
        if self.pc in (0x79e4, 0x7a00):
            self.records.append({'score_descriptor': f'{self.a:02x}'})
            self.pc = self.popw()
            return
        if self.pc == 0x71cb:
            self.records.append({'output_token': f'{self.a:02x}'})
            self.pc = self.popw()
            return
        if self.pc == 0x7aa9:  # audits do not mutate feature flags
            self.pc = self.popw()
            return
        super().step()

    def flags(self):
        return {'lamp': bool(self.mem[0x14] & 0x80),
                'qualified_once': bool(self.mem[0x18] & 0x80),
                'collected': bool(self.mem[0x18] & 8), 'pending': self.mem[0x5b]}


def fire(c, multiplier_bits, adjustment=2):
    c.mem[0x10] = 0xf0
    c.mem[0x14] = (c.mem[0x14] & 0x80) | multiplier_bits
    c.mem[0x8d] = 7
    c.mem[0x1ac] = adjustment
    c.run(0x6873)


rows = []
for adjustment in (0, 1, 2):
    for bits in (0x10, 0x20, 0x40):
        c = Probe()
        fire(c, bits, adjustment)
        assert c.flags()['lamp'] == (adjustment != 0 and (bits == 0x40 or adjustment == 2 and bits == 0x20))
        rows.append({'case': 'FIRE lighting', 'adjustment_low': adjustment,
                     'multiplier_before_bits': bits, 'after': c.flags()})
c = Probe()
fire(c, 0x20)
assert c.flags()['lamp']
for switch in (39, 41):
    c.mem[0x8c:0x8e] = m[0x60f1+4*switch+2:0x60f1+4*switch+4]
    c.run(0x6eaf)
    assert not c.flags()['collected']
c.mem[0x8c:0x8e] = m[0x60f1+4*40+2:0x60f1+4*40+4]
c.run(0x6eaf)
assert c.flags()['collected'] and c.flags()['lamp'] and c.mem[0x57] == 23
assert {'output_token': '88'} in c.records
rows.append({'case': 'center collection before presentation cleanup', 'after': c.flags(), 'records': c.records, 'repeats': c.mem[0x57]})
c.run(0x76f1)
assert c.mem[0x5b] == 1
# FA descriptor is a toggle of flag27; normal valid presentation ends lit->off.
c.a = 0xfa
c.run(0x780e, a=0xfa)
assert not c.flags()['lamp']
fire(c, 0x40)
assert not c.flags()['lamp']
rows.append({'case': 'subsequent FIRE cannot relight on same physical ball', 'after': c.flags()})
# Tilt ball-end copy uses 6069: all per-ball EB flags are cleared, then 73CC
# still sees 5B and skips player/ball advancement. Normal copy also clears flags.
for tilted in (False, True):
    c = Probe()
    c.mem[0x14] = 0xc0
    c.mem[0x18] = 0x88
    c.mem[0x5b] = 1
    c.mem[0x55] = 0
    c.mem[0x78] = 0x82 if tilted else 0x80
    c.mem[0x82:0x84] = b'\x00\x94'
    c.x = 0x6069 if tilted else 0x10
    c.b = 18
    c.run(0x76dd)
    c.run(0x7520)
    assert not c.flags()['lamp'] and not c.flags()['qualified_once'] and not c.flags()['collected']
    assert c.mem[0x5b] == 1
    fire(c, 0x20)
    # Release the tilt lifecycle bit just as the next start path does.
    if tilted:
        c.mem[0x78] = 0x80
        fire(c, 0x20)
    assert c.flags()['lamp']
    rows.append({'case': 'next physical ball resets flags, awarded extra survives tilt', 'tilt': tilted, 'after': c.flags()})
for pending in range(5):
    c = Probe()
    c.mem[0x5b] = pending
    c.pc = 0x6e25
    c.pushw(0xffff)
    while c.pc != 0x6e2d:
        c.step()
    assert c.mem[0x5b] == min(2, pending)
    rows.append({'case': 'ball-end pending clamp', 'before': pending, 'after': c.mem[0x5b]})
# The two Shoot Again logical flags are set while pending awards exist.
# Extra starts with 78 bit7 clear; first eligible foreground/scoring work
# decrements5B before restoring the lamps from the remaining pending count.
for pending in (1, 2):
    c = Probe()
    c.mem[0x78] = 0
    c.mem[0x5b] = pending
    c.run(0x7925)
    before = {'playfield_flag00': bool(c.mem[0x10] & 1), 'backbox_flag3e': bool(c.mem[0x17] & 0x40)}
    assert all(before.values())
    c.run(0x76f1)
    after = {'playfield_flag00': bool(c.mem[0x10] & 1), 'backbox_flag3e': bool(c.mem[0x17] & 0x40)}
    assert c.mem[0x5b] == max(0, pending - 1)
    assert all(after.values()) if pending > 1 else not any(after.values())
    rows.append({'case': 'first scoring after extra serve', 'pending_before': pending,
                 'pending_after': c.mem[0x5b], 'lamps_before': before, 'lamps_after': after})
for pending in (0, 1, 2):
    c = Probe()
    c.mem[0x5b] = pending
    c.mem[0x55] = 0
    c.mem[0x56] = 0
    c.mem[0x03] = 0xf1
    c.run(0x73cc, stop={0x73e9, 0x7426})
    assert c.mem[0x03] == (0xf1 if pending else 0xf2)
    rows.append({'case': 'pending extra suppresses regular-ball advancement after normal or tilt path',
                 'pending': pending, 'ball_counter03': f'{c.mem[0x03]:02x}'})
report = {'rom_crc32': EXPECTED, 'rom_region_sha256': hashlib.sha256(m[0x6000:0x8000]).hexdigest(), 'cases': rows}
Path(__file__).with_name('l6_checks.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('All bounded L-6 extra-ball assertions passed')
