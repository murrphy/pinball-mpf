"""Recover only raw04/GW04 with existing verified Sound ROM3 renderer.
Default byte-verifies; --write promotes this one new asset/manifest row.
"""
import array, hashlib, io, json, math, sys, wave, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'audio/diagnostics/sound_audit/tools'))
from firepower_audit_cpu import CPU
assert f'{zlib.crc32(Path("/tmp/firepower-audit-l6/sound3.716").read_bytes()):08x}' == '55a10d13'
c = CPU()
c.run(0xfc1b, a=3, stop={0xfc3e})
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
asset = ROOT / 'sounds/fx/l6_cmd_04.wav'
row = dict(raw=4, loader='FA88', vector='FE76', routine='FAEE', duration=c.clock / 895000,
           dac_writes=len(c.dac), dac_sha256=hashlib.sha256(b''.join(t.to_bytes(4, 'little')+bytes([v]) for t,v in c.dac)).hexdigest(),
           pcm_sha256=hashlib.sha256(out.tobytes()).hexdigest(), wav_sha256=hashlib.sha256(buffer.getvalue()).hexdigest(),
           file='command_04.wav', production_file='sounds/fx/l6_cmd_04.wav',
           entry_note='FC1B A=03 after first raw04 decrement, stop FC3E; GWLD, no IRQ/speech/analog filtering')
manifest = ROOT / 'audio/l6_effect_sources.json'
data = json.loads(manifest.read_text(encoding='utf-8'))
if '--write' in sys.argv:
    asset.write_bytes(buffer.getvalue())
    data['effects'] = [x for x in data['effects'] if x['raw'] != 4] + [row]
    data['effects'].sort(key=lambda x: x['raw'])
    manifest.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
assert asset.read_bytes() == buffer.getvalue()
assert next(x for x in data['effects'] if x['raw'] == 4) == row
print('Exact raw04 render verified:', row)
