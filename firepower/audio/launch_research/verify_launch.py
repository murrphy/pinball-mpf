"""Narrow L-6 launch probes and Sound ROM 3 TURBO render using audit CPU."""
import array
import hashlib
import io
import json
import math
import wave
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "audio/diagnostics/sound_audit/tools"))
from firepower_audit_cpu import CPU

class LaunchProbe(CPU):
    def __init__(self):
        super().__init__()
        self.tokens = []
    def step(self):
        if self.pc == 0x71cb:
            self.tokens.append(self.a)
            self.pc = self.popw()
            return
        super().step()

rows = []
for game in (0, 0x80, 1, 2, 0x81, 0x82):
    for occupied in (False, True):
        for latched in (0, 1):
            for timer in (0, 1, 2):
                cpu = LaunchProbe()
                cpu.mem[0x78] = game
                cpu.mem[0x26] = 0x20 if occupied else 0
                cpu.mem[0x15a] = latched
                cpu.mem[0x157] = timer
                cpu.run(0x6d40, stop={0x6de9, 0x6d6f, 0x6d55})
                expected = [0x94] if not game & 3 and latched and not occupied and timer == 0 else []
                assert cpu.tokens == expected, (game, occupied, latched, timer, cpu.tokens)
                rows.append(dict(game=game, occupied=occupied, latch=latched,
                                 timer=timer, tokens=cpu.tokens, next_latch=cpu.mem[0x15a]))
# Timer itself pauses while the release's RAM7A is nonzero.
for held in (0, 0xff):
    cpu = CPU()
    cpu.mem[0x7d] = 0x0c
    cpu.mem[0x7a] = held
    cpu.mem[0x157] = 2
    cpu.run(0x63e7, stop={0x6427})
    assert cpu.mem[0x157] == (2 if held else 1)
(root / 'audio/diagnostics/sound_audit/launch_probes.json').write_text(
    json.dumps(rows, indent=2) + '\n', encoding='utf-8')

cpu = CPU()
# F81C initializes HI to 3C; LO is explicitly chosen as 00 for this reference.
# The reset routine does not initialize LO. Original shared noise history is
# not emulated by the existing modern background player.
cpu.mem[0x0a:0x0c] = bytes([0x3c, 0])
cpu.run(0xfc24, a=0x13, stop={0xfc3e})  # post FC14 decrement, raw14
frames = math.ceil(cpu.clock * 48000 / 895000)
out = array.array('h')
index = 0
held = 128
for frame in range(frames):
    start = frame * 895000 / 48000
    end = (frame + 1) * 895000 / 48000
    cursor = start
    area = 0.0
    while index < len(cpu.dac) and cpu.dac[index][0] < end:
        edge = max(cursor, cpu.dac[index][0])
        area += (edge - cursor) * (held - 128)
        cursor = edge
        held = cpu.dac[index][1]
        index += 1
    area += (end - cursor) * (held - 128)
    out.append(max(-32768, min(32767, round(area / (end - start) * 200))))
path = root / 'sounds/fx/l6_cmd_14.wav'
buffer = io.BytesIO()
with wave.open(buffer, 'wb') as wav:
    wav.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
    wav.writeframes(out.tobytes())
events = b''.join(t.to_bytes(4, 'little') + bytes([v]) for t, v in cpu.dac)
row = dict(raw=20, routine='F8D1', noise_routine='F8E0', vector='FCDD',
           duration=cpu.clock / 895000, cycles=cpu.clock, dac_writes=len(cpu.dac),
           rng_seed='3C00', rng_final=cpu.mem[0x0a:0x0c].hex().upper(),
           dac_sha256=hashlib.sha256(events).hexdigest(),
           pcm_sha256=hashlib.sha256(out.tobytes()).hexdigest(),
           wav_sha256=hashlib.sha256(buffer.getvalue()).hexdigest(),
           production_file='sounds/fx/l6_cmd_14.wav',
           entry_note='FC24 A=13 (raw14 after first decrement), stop at FC3E; fixed reference RNG seed, excludes IRQ latency and analog filtering')
manifest = root / 'audio/l6_effect_sources.json'
data = json.loads(manifest.read_text(encoding='utf-8'))
if '--write' in sys.argv:
    path.write_bytes(buffer.getvalue())
    data['effects'] = [effect for effect in data['effects'] if effect['raw'] != 20] + [row]
    manifest.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
else:
    assert path.read_bytes() == buffer.getvalue(), 'Production launch WAV differs from ROM execution'
    assert next(effect for effect in data['effects'] if effect['raw'] == 20) == row
print('72 launch condition probes and timer pause probes passed')
print(json.dumps(row, indent=2))
