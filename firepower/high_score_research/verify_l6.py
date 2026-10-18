"""Bounded execution of checksummed L-6 HSTD; no complete PIA/IRQ emulation."""
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'audio/diagnostics/sound_audit/tools'))
from firepower_audit_cpu import CPU
from firepower_audit_decode import m

CRCS = {'prom1_6.474': 'af6eb0b9', 'prom2.474': 'f75ade1a',
        'prom3.474': '242ec687', 'gamerom.716': 'fdd3b983',
        'green1.716': '2145f8ab', 'green2.716': '1c978a4a'}
for name, crc in CRCS.items():
    assert f'{zlib.crc32((Path("/tmp/firepower-audit-l6") / name).read_bytes()):08x}' == crc


def packed(score):
    return bytes.fromhex(f'{score:06d}')


def store(cpu, address, score):
    cpu.mem[address:address + 6] = bytes(int(d) for d in f'{score:06d}')


def stored(cpu):
    return int(''.join(str(d & 15) for d in cpu.mem[0x148:0x14e]))


class Probe(CPU):
    def __init__(self):
        super().__init__()
        self.tokens = []
        self.ticks = 0

    def step(self):
        if self.pc in (0x79cd, 0x768e):
            self.ticks += self.mem[0x3a]
            self.mem[0x3a] = 0
        if self.pc == 0x71cb:
            self.tokens.append((self.a, self.ticks))
            self.pc = self.popw()
            return
        if self.pc in (0x76cc, 0x7aa9):
            self.pc = self.popw()
            return
        super().step()


rows = []
for scores in ((540000,), (550000,), (550010,), (550100,), (600000, 700000),
               (700000, 600000, 650000), (600000, 700000, 700000, 650000),
               (500000, 500000, 500000, 500000)):
    for maximum, credits in ((12, 0), (12, 11), (12, 12), (0, 0)):
        c = Probe()
        c.mem[0x56] = len(scores) - 1
        c.mem[0x181:0x183] = bytes((5, 5))  # Function13=55, feature enabled
        c.mem[0x199:0x19b] = bytes((0, 3))  # Function25=03
        c.mem[0x18b:0x18d] = bytes((maximum // 10, maximum % 10))
        c.mem[7] = (credits // 10) * 16 + credits % 10
        store(c, 0x148, 550000)
        for player, score in enumerate(scores):
            c.mem[4 * player:4 * player + 3] = packed(score)
        c.run(0x746b, stop={0x7507})
        winner = scores.index(max(scores))
        # 74DA is BNE, not the expected BCS: equal low byte qualifies,
        # a different low byte with identical upper bytes does not.
        qualifies = max(scores) // 100 > 550000 // 100 or max(scores) == 550000
        assert c.mem[0x73] == winner
        assert c.word(0x80) == winner * 4
        assert stored(c) == (max(scores) if qualifies else 550000), (scores, stored(c), c.mem[0x70:0x74].hex())
        assert c.mem[0x21] == 1 << winner  # winning Player Up flash flag
        expected_tokens = [(0x8f, 0)] if qualifies else []
        award = 3 if qualifies and maximum > credits else 0
        expected_tokens += [(0x4d, 744 + 16 * i) for i in range(award)]
        assert c.tokens == expected_tokens, (scores, c.tokens)
        final = credits + award
        assert c.mem[7] == (final // 10) * 16 + final % 10
        rows.append(dict(scores=scores, winner=winner + 1, qualifies=qualifies,
                         maximum=maximum, before=credits, after=final, tokens=c.tokens))

# Cold factory initialization and dedicated HSTD reset use Function13.
c = Probe()
c.run(0x7af0, stop={0x7b08})
assert stored(c) == 550000
assert bytes(d & 15 for d in c.mem[0x181:0x183]) == bytes((5, 5))
assert c.mem[0x199:0x19b] == bytes((0, 3))
store(c, 0x148, 987650)
c.run(0x7e36, stop={0x7062})
assert stored(c) == 550000

# Disabled Function13 skips qualification regardless of stored score.
c = Probe()
c.mem[0:3] = packed(900000)
store(c, 0x148, 550000)
c.run(0x746b, stop={0x7507})
assert stored(c) == 550000 and not c.tokens

# Attract alternates only the winning score record: HSTD / final game score.
c = Probe()
c.mem[0x181:0x183] = bytes((5, 5))
c.mem[0x80:0x82] = bytes((0, 8))  # player3 display record
c.mem[0x70:0x73] = packed(430000)
c.mem[8:11] = packed(430000)
store(c, 0x148, 550000)
phases = []
for expected in (550000, 430000, 550000, 430000):
    c.mem[0x43] = 0
    c.run(0x7155, stop={0x7186})
    assert c.mem[8:11] == packed(expected)
    assert c.mem[0x43] == 127
    phases.append(dict(score=expected, lamp=bool(c.mem[0x17] & 0x80)))
assert [p['lamp'] for p in phases] == [True, False, True, False]

# Exhaust the low score byte against a nonzero stored low byte. This pins
# the surprising BNE at74DA independently of the default's trailing00.
low_byte_cases = []
for low in range(100):
    c = Probe()
    c.mem[0x181:0x183] = bytes((5, 5))
    c.mem[0:3] = packed(550000 + low)
    store(c, 0x148, 550050)
    c.run(0x746b, stop={0x7507})
    assert bool(c.tokens) == (low == 50)
    low_byte_cases.append(dict(score=550000 + low, stored=550050, qualifies=bool(c.tokens)))

report = dict(rom_crc32=CRCS, default=550000, default_credits=3,
              descriptor=m[0x6227:0x622c].hex(), cases=rows, attract=phases,
              low_byte_cases=low_byte_cases)
Path(__file__).with_name('l6_checks.json').write_text(json.dumps(report, indent=2) + '\n')
print(f'L-6 HSTD: {len(rows)} comparisons/credit cases, 100 low-byte cases, factory/reset, disabled and four attract phases passed')
