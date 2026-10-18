"""Re-execute cached FA64 tooling; check production model and independent fixtures.

Run: /usr/bin/python3 audio/bonus_research/verify_fa64.py --tools-dir /tmp
Requires existing fp_synth.py, fp_trace.py, fp-disasm.py, ROMs and cycle table.
No downloads and no ROM images are written into the project.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools-dir", type=Path, default=Path("/tmp"))
    args = parser.parse_args()
    sys.path.insert(0, str(args.tools_dir))
    from fp_synth import Sound  # Existing local bounded interpreter, not a dependency of production.

    class FastSound(Sound):
        def step(self):
            if self.pc == 0xFB0C:
                # Exact DECA/BNE delay loop, 6 cycles/iteration including exit.
                self.clock += 6 * (self.a or 256)
                self.a = self.n = self.v = 0
                self.z = 1
                self.pc = 0xFB0F
            else:
                super().step()

    root = Path(__file__).resolve().parent
    model = json.loads((root.parent / "fa64_model.json").read_text())
    fixtures = json.loads((root / "dac_checks.json").read_text())
    pcm_fixtures = json.loads((root / "render_checks.json").read_text())
    cpu = FastSound()
    total = 0
    for stage in range(1, 148):
        cpu.sp = 0x7F
        cpu.pushw(0xFFFF)
        cpu.pc = 0xFA64
        cpu.clock = 0
        cpu.dac = []
        while cpu.pc != 0xFFFF:
            cpu.step()
            if cpu.clock > 2_000_000:
                raise RuntimeError("FA64 execution did not terminate")
        period = 147 - stage
        first = 24353 if stage == 1 else 6 * period + 180
        expected = [
            (first + index * (6 * period + 25) + (index // 72) * 110, value)
            for index, value in enumerate(model["waveform"] * 8)
        ] if stage <= 146 else []
        assert cpu.dac == expected, stage
        if expected:
            assert cpu.clock == expected[-1][0] + 89, stage
        data = b"".join(t.to_bytes(4, "little") + bytes([value]) for t, value in cpu.dac)
        assert hashlib.sha256(data).hexdigest() == fixtures[str(stage)], stage
        if str(stage) in pcm_fixtures:
            # Independent output-frame integration of EXECUTED events, rather
            # than the production renderer's calculated event schedule.
            frames = math.ceil(cpu.clock * 48000 / 895000)
            pcm = bytearray()
            event_index = 0
            held = 114
            for frame in range(frames):
                start = frame * 895000 / 48000
                finish = (frame + 1) * 895000 / 48000
                cursor, area = start, 0.0
                while event_index < len(cpu.dac) and cpu.dac[event_index][0] < finish:
                    edge = max(cursor, cpu.dac[event_index][0])
                    area += (edge - cursor) * (held - 114)
                    cursor = edge
                    held = cpu.dac[event_index][1]
                    event_index += 1
                area += (finish - cursor) * (held - 114)
                sample = max(-32768, min(32767, round(area / (finish - start) * 200)))
                pcm.extend(sample.to_bytes(2, "little", signed=True))
            assert frames == pcm_fixtures[str(stage)]["frames"], stage
            assert hashlib.sha256(pcm).hexdigest() == pcm_fixtures[str(stage)]["sha256"], stage
        total += len(expected)
    print(f"FA64 verified: {total} exact DAC writes, 146 audible states, then silence")


if __name__ == "__main__":
    main()
