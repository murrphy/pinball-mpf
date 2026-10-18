"""Analyze real Godot float captures; never reads or rewrites production WAVs.
Run after test_speech_render.gd captures baseline and final audio into /tmp.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def loudness(path, rate, master_db):
    result = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(int(rate)),
                             "-ac", "2", "-i", str(path), "-af",
                             f"volume={master_db}dB,ebur128=peak=true", "-f", "null", "-"],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    summary = result.stderr.split("Summary:")[-1]
    return {"integrated_lufs": float(re.search(r"I:\s+([\d.-]+) LUFS", summary)[1]),
            "true_peak_dbfs": float(re.search(r"Peak:\s+([\d.-]+) dBFS", summary)[1])}


def analyze(folder):
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    assert report["failures"] == 0
    for row in report["renders"]:
        path = folder / (row["label"] + "_master.f32")
        row["capture_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        row.update(loudness(path, report["mix_rate"], report["buses"]["Master"]["gain_db"]))
        # A sub-400 ms scoring effect cannot supply an EBU integration block;
        # capture padding would dominate the number. Keep its active RMS/peak.
        if row["duration"] < 0.4:
            row["integrated_lufs"] = None
        if row["category"] == "speech" and not report["baseline"]:
            assert row["true_peak_dbfs"] <= -1.0, (row["label"], "Oversampled speech peak exceeds -1 dBFS")
            path = folder / (row["label"] + "_prelimit.f32")
            samples = array.array("f", path.read_bytes())
            if sys.byteorder != "little":
                samples.byteswap()
            step = int(report["mix_rate"] / 50) * 2
            frames = [samples[i:i+step] for i in range(0, len(samples), step)]
            powers = [sum(x*x for x in frame)/len(frame) for frame in frames]
            gate = max(10**(-50/10), max(powers)*10**(-35/10))
            active = [x for frame, power in zip(frames, powers) if power >= gate for x in frame]
            ceiling = 10**(report["settings"]["limiter_db"]/20)
            row["prelimit_active_samples_above_ceiling_percent"] = 100*sum(abs(x)>ceiling for x in active)/len(active)
            row["limiter_rms_reduction_db"] = row["taps"]["prelimit"]["active_rms_dbfs"]-row["taps"]["voice"]["active_rms_dbfs"]
    return report


def main():
    before = analyze(Path("/tmp/firepower-speech-before"))
    after = analyze(Path("/tmp/firepower-speech-after"))
    for row in after["renders"]:
        previous = next((x for x in before["renders"] if x["label"] == row["label"]), None)
        if previous:
            row["active_rms_increase_db"] = row["taps"]["master"]["active_rms_dbfs"]-previous["taps"]["master"]["active_rms_dbfs"]
            if row["category"] == "speech":
                row["effective_gain_from_original_db"] = 4+row["active_rms_increase_db"]
                row["compressor_rms_reduction_db"] = previous["taps"]["voice"]["active_rms_dbfs"]+after["settings"]["makeup_db"]-row["taps"]["prelimit"]["active_rms_dbfs"]
    output = ROOT / "audio/speech_research/rendered_levels.json"
    output.write_text(json.dumps({"before": before, "after": after}, indent=2)+"\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
