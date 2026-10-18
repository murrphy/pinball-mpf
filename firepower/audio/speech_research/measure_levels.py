"""Read-only PCM balance measurement; run from any directory with Python 3."""
import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]


def db(value):
    return 20 * math.log10(max(value, 1e-12))


def measure(path):
    data = (ROOT / path).read_bytes()
    with wave.open(str(ROOT / path)) as wav:
        assert wav.getsampwidth() == 2 and wav.getnchannels() == 1
        samples = array.array("h", wav.readframes(wav.getnframes()))
        rate = wav.getframerate()
    if sys.byteorder != "little":
        samples.byteswap()
    frames = [samples[i:i + rate // 50] for i in range(0, len(samples), rate // 50)]
    energy = [sum(x * x for x in frame) / len(frame) for frame in frames]
    threshold = max(32768 ** 2 * 10 ** (-50 / 10), max(energy) * 10 ** (-35 / 10))
    active = [x for frame, power in zip(frames, energy) if power >= threshold for x in frame]
    peak = db(max(abs(x) for x in samples) / 32768)
    rms = db(math.sqrt(sum(x * x for x in active) / len(active)) / 32768)
    return dict(file=path, wav_sha256=hashlib.sha256(data).hexdigest(),
                peak_dbfs=peak, active_rms_dbfs=rms, crest_db=peak-rms,
                active_seconds=len(active)/rate, duration_seconds=len(samples)/rate,
                full_scale_samples=sum(abs(x) >= 32767 for x in samples))


def main():
    speech = json.loads((ROOT / "audio/speech_model.json").read_text(encoding="utf-8"))
    effects = json.loads((ROOT / "audio/l6_effect_sources.json").read_text(encoding="utf-8"))
    report = dict(method="20ms frame RMS gate: max(-50 dBFS, loudest frame minus 35 dB); peak over entire PCM; no per-sample gate", speech=[], electronic=[])
    for phrase in speech["phrases"].values():
        row = measure(phrase["production_file"])
        assert row["wav_sha256"] == phrase["wav_sha256"]
        row["words"] = [word["word"] for word in phrase["words"]]
        report["speech"].append(row)
    for effect in effects["effects"]:
        row = measure(effect["production_file"])
        assert row["wav_sha256"] == effect["wav_sha256"]
        row["command"] = effect["raw"]
        report["electronic"].append(row)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
