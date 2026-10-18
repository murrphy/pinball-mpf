"""Analyze actual mixer captures: spectra and time spent under DSP reduction."""
import array
import cmath
import json
import math
from pathlib import Path
import sys

RATE = 44100


def read(path):
    data = array.array("f", Path(path).read_bytes())
    if sys.byteorder != "little":
        data.byteswap()
    return data[::2]  # identical mono speech in both output channels


def active_indices(samples):
    step = RATE // 50
    energies = [sum(x*x for x in samples[i:i+step])/len(samples[i:i+step])
                for i in range(0, len(samples), step)]
    gate = max(1e-5, max(energies)*10**(-3.5))
    return [i for i in range(len(samples)) if energies[i//step] >= gate]


def reduction(source, output, delay=0, makeup=0.0):
    indices = active_indices(source)
    values = [-20*math.log10(max(abs(output[i+delay]/source[i]), 1e-12))+makeup
              for i in indices if i+delay < len(output) and abs(source[i]) > 1e-5]
    values.sort()
    return dict(active_percent=100*sum(v > 0.1 for v in values)/len(values),
                active_seconds=sum(v > 0.1 for v in values)/RATE,
                mean_db=sum(values)/len(values), max_db=max(values),
                p95_db=values[int(len(values)*0.95)],
                method="20ms active frame gate; gain inferred only on nonzero samples; active means >0.1 dB reduction")


def fft(values):
    n = len(values)
    result = [complex(x) for x in values]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            result[i], result[j] = result[j], result[i]
    length = 2
    while length <= n:
        step = cmath.exp(-2j*math.pi/length)
        for start in range(0, n, length):
            weight = 1+0j
            for k in range(length//2):
                a = result[start+k]
                b = weight*result[start+k+length//2]
                result[start+k], result[start+k+length//2] = a+b, a-b
                weight *= step
        length *= 2
    return result


def spectrum(samples):
    n = 2048
    window = [0.5-0.5*math.cos(2*math.pi*i/(n-1)) for i in range(n)]
    frames = [samples[i:i+n] for i in range(0, len(samples)-n+1, n//2)]
    powers = [sum(x*x for x in frame)/n for frame in frames]
    gate = max(1e-5, max(powers)*10**(-3.5))
    accumulated = [0.0]*(n//2+1)
    for frame, power in zip(frames, powers):
        if power < gate:
            continue
        transformed = fft([x*w for x, w in zip(frame, window)])
        for k in range(n//2+1):
            accumulated[k] += abs(transformed[k])**2*(1 if k in (0, n//2) else 2)
    total = sum(accumulated)
    bands = [(0, 100), (100, 300), (300, 1000), (1000, 1500),
             (1500, 4000), (4000, 8000), (8000, RATE/2+1)]
    return {f"{int(lo)}-{int(hi)}Hz": 100*sum(p for k, p in enumerate(accumulated)
                                            if lo <= k*RATE/n < hi)/total
            for lo, hi in bands}


def analyze(folder, spectra=False):
    folder = Path(folder)
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    for row in report["renders"]:
        if row["category"] != "speech":
            continue
        label = row["label"]
        before = read(folder / (label+"_prelimit.f32"))
        after = read(folder / (label+"_voice.f32"))
        row["limiter_reduction"] = reduction(before, after, row["limiter_delay_frames"])
        input_path = folder / (label+"_input.f32")
        if input_path.exists():
            row["compressor_reduction"] = reduction(read(input_path), read(folder / (label+"_compout.f32")) if (folder / (label+"_compout.f32")).exists() else before, makeup=report["settings"]["makeup_db"])
        if spectra:
            row["spectrum_percent"] = spectrum(after)
    return report


if __name__ == "__main__":
    print(json.dumps(analyze(sys.argv[1], "--spectra" in sys.argv), indent=2))
