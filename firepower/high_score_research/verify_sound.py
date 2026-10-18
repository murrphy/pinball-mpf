"""Recover raw0F/APPEAR with the established Sound ROM3 renderer.
Default byte-verifies; --write promotes this one new asset/manifest row.
"""
import array, hashlib, io, json, math, sys, wave, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'audio/diagnostics/sound_audit/tools'))
from firepower_audit_cpu import CPU
assert f'{zlib.crc32(Path("/tmp/firepower-audit-l6/sound3.716").read_bytes()):08x}' == '55a10d13'
c = CPU()
# Same documented reference seed as launch; real shared noise history varies.
c.mem[0x0a:0x0c] = bytes([0x3c, 0])
c.run(0xfc24, a=0x0e, stop={0xfc3e}, limit=20_000_000)
out = array.array('h')
index, held = 0, 128
for frame in range(math.ceil(c.clock * 48000 / 895000)):
    start, end = frame * 895000 / 48000, (frame + 1) * 895000 / 48000
    cursor, area = start, 0.0
    while index < len(c.dac) and c.dac[index][0] < end:
        edge = max(cursor, c.dac[index][0])
        area += (edge - cursor) * (held - 128)
        cursor, held = edge, c.dac[index][1]
        index += 1
    area += (end - cursor) * (held - 128)
    out.append(round(area / (end - start) * 200))
assert sys.byteorder == 'little'
buffer = io.BytesIO()
with wave.open(buffer, 'wb') as w:
    w.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
    w.writeframes(out.tobytes())
asset = ROOT / 'sounds/fx/l6_cmd_0f.wav'
row = dict(raw=15, loader='FC24', vector='FCD3', routine='F898', duration=c.clock / 895000,
           dac_writes=len(c.dac), dac_sha256=hashlib.sha256(b''.join(t.to_bytes(4, 'little')+bytes([v]) for t,v in c.dac)).hexdigest(),
           pcm_sha256=hashlib.sha256(out.tobytes()).hexdigest(), wav_sha256=hashlib.sha256(buffer.getvalue()).hexdigest(),
           file='command_0f.wav', production_file='sounds/fx/l6_cmd_0f.wav',
           rng_seed_hex='3c00', noise_routine='F8A2',
           entry_note='FC24 A=0E after first raw0F decrement, stop FC3E; APPEAR reference seed3C00, excludes speech/IRQ/analog filtering')
manifest = ROOT / 'audio/l6_effect_sources.json'
data = json.loads(manifest.read_text(encoding='utf-8'))
if '--write' in sys.argv:
    asset.write_bytes(buffer.getvalue())
    data['effects'] = [x for x in data['effects'] if x['raw'] != 15] + [row]
    data['effects'].sort(key=lambda x: x['raw'])
    manifest.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
assert asset.read_bytes() == buffer.getvalue()
assert next(x for x in data['effects'] if x['raw'] == 15) == row
print('Raw0F APPEAR reference render verified:', row)
