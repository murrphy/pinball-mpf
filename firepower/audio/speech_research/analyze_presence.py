"""Read-only analysis of actual mixer experiments; no production WAV writes."""
import json
import math
from pathlib import Path

from analyze_rendered import loudness
from presence_analysis import analyze, read, spectrum

ROOT = Path(__file__).resolve().parents[2]


def meters(folder, spectra=False):
    folder = Path(folder)
    report = analyze(folder, spectra)
    assert report["failures"] == 0
    for row in report["renders"]:
        row.update(loudness(folder / (row["label"]+"_master.f32"), report["mix_rate"],
                            report["buses"]["Master"]["gain_db"]))
        if row["duration"] < 0.4:
            row["integrated_lufs"] = None
        if row["category"] == "speech":
            assert row["true_peak_dbfs"] <= -1.0, (row["label"], row["true_peak_dbfs"])
    return report


def main():
    study = Path("/tmp/firepower-speech-study")
    makeup_sweep = [meters(study / ("makeup_"+str(value)), spectra=value == 0) for value in [0, 2, 4, 6]]
    current = makeup_sweep[0]
    selected = meters("/tmp/firepower-presence-3", spectra=True)
    strongest = meters("/tmp/firepower-presence-6-all")
    balances = [meters(study / ("balance_"+str(value))) for value in [0, 3, 6]]
    current_spectra = {row["label"]: row["spectrum_percent"] for row in current["renders"]}
    for row in selected["renders"]:
        if row["category"] == "electronic":
            current_spectra[row["label"]] = spectrum(read(Path("/tmp/firepower-presence-3") / (row["label"]+"_master.f32")))
    for row in selected["renders"]:
        if row["category"] != "speech":
            continue
        old = next(x for x in current["renders"] if x["label"] == row["label"])
        old_band = current_spectra[row["label"]]["1500-4000Hz"]
        new_band = row["spectrum_percent"]["1500-4000Hz"]
        row["presence_band_energy_increase_db"] = (
            row["taps"]["master"]["active_rms_dbfs"]-old["taps"]["master"]["active_rms_dbfs"]
            +10*math.log10(new_band/old_band))
    shaping = [analyze(study / name) for name in ["attack_2", "attack_4", "attack_8", "eq_2_makeup14", "eq_2_makeup16", "eq_2_makeup18", "eq_fast_makeup16"]]
    attack_spectra = {}
    for name in ["eq_2_makeup16", "eq_fast_makeup16"]:
        rows = []
        for row in next(x for x in shaping if x["settings"]["eq"] and x["settings"]["attack_us"] == (2000 if name == "eq_2_makeup16" else 200) and x["settings"]["makeup_db"] == 16)["renders"]:
            samples = read(study / name / (row["label"]+"_voice.f32"))
            start = next(i for i, x in enumerate(samples) if abs(x) > 0.0001)
            early = samples[start:start+4410]
            rows.append(dict(label=row["label"], bands=spectrum(samples),
                             early_100ms_rms=10*math.log10(sum(x*x for x in early)/len(early)),
                             rms=row["taps"]["voice"]["active_rms_dbfs"]))
        attack_spectra[name] = rows
    report = dict(current=current, current_spectra=current_spectra,
                  makeup_sweep=makeup_sweep,
                  shaping_sweep=shaping,
                  attack_spectra=attack_spectra,
                  selected=selected, balances=balances, strongest=strongest,
                  presence_method="Active RMS times Hann STFT band-energy fraction; comparison is an estimate of 1.5-4 kHz energy, not SPL/intelligibility.")
    output = ROOT / "audio/speech_research/presence_levels.json"
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    for row in selected["renders"]:
        if row["category"] == "speech":
            print(row["label"], round(row["taps"]["master"]["active_rms_dbfs"], 2), row["integrated_lufs"],
                  "presence change", round(row["presence_band_energy_increase_db"], 2),
                  "limiter", round(row["limiter_reduction"]["mean_db"], 2))
    print(output)


if __name__ == "__main__":
    main()
