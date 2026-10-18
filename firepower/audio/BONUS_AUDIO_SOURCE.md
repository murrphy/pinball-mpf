# FA64 source resolution and implementation — 2026-10-02

Later continuation: [BONUS_LONG_RUN.md](BONUS_LONG_RUN.md) diagnoses the full
39x5 failure and records the authorized restoration of the 29-unit maximum.
The range-defect descriptions below are historical.

This continues [BONUS_ROM_INVESTIGATION.md](BONUS_ROM_INVESTIGATION.md). The
established foreground timing/command research was reused, not repeated.
**Production now uses a derived FA64 renderer**, not an unidentified FP sample.
The first report's research-only status describes the earlier task.

## Source decision and proof

No existing recording passed a strong identity test. Reusing cached Sound ROM 3
execution, the small model in `fa64_model.json` and `fa64_renderer.gd` reproduces
**every DAC value and cycle timestamp for 146 audible FA64 states: 84,096 writes**.
The next state produces no DAC writes. This is a digital synthesis validation,
not a claim to emulate the original speaker, amplifier, microphone, or room.

The ROM files remain in `/tmp`; no ROM image is included in the project.
`fa64_model.json` contains the 72-byte **derived, post-predecay** waveform and
model provenance. `bonus_research/fa64_initial.wav` is the generated first-state
reference: 48 kHz, mono, 16-bit PCM, approximately 607.04 ms (frame-rounded).
Production generates one finite PCM stream per trigger from the model; it does
not load that reference WAV or store a collection of pre-pitched assets.

Validation is reproducible with the existing cached execution environment:

```sh
/usr/bin/python3 audio/bonus_research/verify_fa64.py --tools-dir /tmp
```

That script requires the previous `fp_synth.py`, `fp_trace.py`, `fp-disasm.py`,
ROMs, and cycle table. It executes FA64, accelerating only the exact DECA/BNE
period loop (6 cycles per iteration), and checks derived events against both
production-model values and independent recorded hashes. It does not perform
foreground timing research, download anything, or modify production assets.
The Godot test independently checks all those event hashes and five complete
PCM hashes generated in Python at steps 1, 2, 29, 87, and 145.

## State, waveform, and modern rendering

The authoritative RAM/dispatch details are in the first report. In brief:

- Foreground 96 -> raw 16 -> sound routine FA64. Sound RAM 07 (`B2FLG`)
  distinguishes initialization from continuation; preceding BGEND clears it.
- First trigger loads vector FEC3, wave FE0E, predecay 11, and single period
  byte 92 from FF68. Predecay's byte arithmetic produces the derived waveform;
  this is not a generic oscillator or sine wave.
- RAM 24 (`FOFSET`) starts at zero and decrements modulo 256 on each further
  trigger. RAM 18 likewise starts at zero, then becomes FF, FE, etc. RAM 22
  is the instantaneous synthesis period; its value after return is not a
  reliable pitch snapshot because the end-of-pattern probe has already run.
- RAM 14/15/16 selects eight waveform cycles, one pattern cycle, and no echo
  decay. RAM 19:1A, 1C:1D, 1E:1F, and 20:21 hold waveform/pattern/end pointers.
  The waveform lives at 25–6C. Loader/decay scratch and stack are also touched;
  they are not additional persistent musical state.
- Each command interrupts the previous burst and restarts waveform phase.
  Natural completion does not increment pitch. Inter-pass silence does not
  reset state. Another non-16 sound command would clear the original latch.

For step n, period p = 147-n. The exact DAC schedule measured from entry FA64 is:

```text
first = 24353 CPU cycles                 if n == 1
first = 6*p + 180 CPU cycles             otherwise
DAC write j (0 <= j < 576):
    time = first + j*(6*p+25) + floor(j/72)*110
    value = derived_waveform[j % 72]
return = final_DAC_time + 89 cycles
```

Clock: the existing sound tooling's nominal 895,000 Hz. Dispatch/IRQ entry
latency before FA64 is excluded. All waveform sample holds, fixed cycle-boundary
intervals, and the initialization delay are preserved by the derived schedule.
First output occurs at 27.210 ms; step 2 first output at 1.173 ms. Full entry-to-
return duration is 607.0246 ms at step 1, 577.1330 ms at step 2, and 24.9453 ms
at step 145. The amplitude pattern repeats; it has no independently guessed
exponential decay. At ordinary countdown cadence, low-stage bursts are cut
short by retriggers. Later bursts can finish before the next counted step.

**One initial WAV plus `pitch_scale` is not sufficient.** Uniform resampling
would scale the initialization delay and the fixed 110-cycle boundary overhead.
It cannot change a 27 ms first-trigger initialization into the later ~1 ms
retrigger path. The discrepancy is especially large at high stages.

The relative waveform-cycle frequency remains:

```text
relative_pitch(n) = 64982 / (72*(6*(147-n)+25)+110)
```

| Step | Period | Relative cycle frequency |
| --- | --- | --- |
| 1 | 146 | 1.000000 |
| 2 | 145 | 1.006692 |
| 29 | 118 | 1.228718 |
| 30 | 117 | 1.238838 |
| 58 | 89 | 1.610139 |
| 87 | 60 | 2.334962 |
| 116 | 31 | 4.246634 |
| 145 | 2 | 23.425379 |

This ratio describes the waveform cycle, not necessarily the strongest audible
harmonic. Production uses the exact period schedule and **pitch_scale=1**, so
there is no uncalibrated sample-rate-to-register mapping. It advances only on
actual counted steps and never resets at a multiplier boundary.

The renderer integrates the piecewise-constant DAC over each 48 kHz output
frame (box averaging), centers the derived waveform's mean at 114, scales by
200 PCM units per DAC unit, and uses -3 dB on its own effects player. It does
not normalize or alter another sound. Analog filtering is unmodeled; box
averaging reduces sampling artifacts but is not an ideal reconstruction filter.
The finite modern stream uses silence during its preamble and after its end;
original hardware retains its last DAC voltage until another write. That DC
hold and the cabinet's AC coupling are not reproduced. Abrupt retriggers remain
monophonic; there is no invented crossfade or pitch smoothing.

Valid original collection ends at most at step 145 (29 by 5). Step 146 is still
audible; step 147 exhausts the frequency table rather than wrapping audibly or
saturating. The unrelated existing 0–39 bonus-range defect remains: the legacy
39-by-5 regression still awards all 195 steps, with no synthesized burst after
146. No arbitrary pitch clamp or unrelated range change was introduced.

## Asset inventory and comparison

`bonus_research/asset_analysis.json` records each plausible project's short
non-speech WAV: native rate/channels/bit depth, duration, active onset/end,
10 ms RMS envelope, spectral centroid, strongest autocorrelation periods, and
spectral score after modest reference-rate normalization (0.75–1.3333).
FP03 background, long FP09/FP11, and speech were excluded. All 18 remaining
short effects were considered, including renamed effects and `bump`.

The cached archive and `modes/sounds` files include the corresponding MP3s.
The prior archive-to-WAV PCM alignment checks were reused; numeric filenames
were never interpreted as sound-command IDs. The earlier broad 0.25–4 rate
search was not treated as an identity test.

Leading candidates in the restricted comparison:

| Asset | Duration s | Spectral cosine | Fitted reference rate | Strong autocorrelation peak |
| --- | --- | --- | --- | --- |
| FP12 | 0.7858 | 0.798 | 1.082 | 21.995 ms, r=0.200 |
| FP17 | 1.2821 | 0.717 | 1.075 | 20.952 ms, r=0.317 |
| FP08 | 0.3156 | 0.709 | 1.268 | 18.141 ms, r=0.323 |
| FP14 | 0.3940 | 0.683 | 1.241 | 13.379 ms, r=0.215 |
| FP16 | 0.9687 | 0.557 | 0.755 | 20.998 ms, r=0.539 |
| FP13 | 0.4723 | 0.488 | 0.755 | 20.227 ms, r=0.441 |

The current incorrect `bump` scores 0.723, above several contenders. Spectral
cosine alone remains insufficient. Most asset onsets include approximately
20–30 ms quiet before their attack; their duration/envelope and periodic
structure do not establish the eight-cycle FA64 burst or a particular native
state. FP12 is the leading candidate **for further investigation**, not a
confirmed source. No recommended starting playback rate is assigned to it.
The low FP16/FP13 restricted scores also undermine the earlier impression from
low-frequency centroids and very large rate shifts. No subjective listening
judgment was used as proof.

## Uploaded original-machine recording

The user supplied `audio/FP_bonus_collect_sound.m4a` during this continuation.
It is stereo AAC at 48 kHz, **9.962667 seconds** container duration. It was only
read, not edited. The previous “reference unavailable” limitation is superseded.

Spectral-frame autocorrelation in 3.7–5.0 s and 5.0–7.0 s has a leading local
peak at **63.854875 ms**, correlations approximately 0.442 and 0.446. Resolution
here is a 128-sample hop at 22,050 Hz (5.805 ms), so this measurement cannot
precisely discriminate 64 ms from the established 66.368 ms scheduler. The
recording shows rising bands and sustained sound during the middle section.
Background audio, transients, and compression prevent isolating every trigger.

`bonus_research/reference_spectrogram.png` compares the recording with the
ROM-derived sequence. `fa64_23x3_reference.wav` is an **illustrative** 23-unit,
3X sequence, 4.77754 s; 23 is not asserted as the original video's bonus value.
Both display rising spectral bands, while the raw digital synthesis is richer
in upper-frequency energy and the recorded machine has stronger low-frequency
and persistent background components. This supports the broad trajectory;
it is not an exact frequency-response/envelope match.

A strongest-peak detector in 350–1500 Hz illustrates why simple tuning by peak
is misleading: recording windows at 3.8/4.5/5.5/6.5/7.5 s give approximately
357/390/513/510/516 Hz, whereas corresponding illustrative synthesis offsets
0.2/0.9/1.9/2.9/3.9 s give 369/378/425/486/548 Hz. The detector switches between
harmonics/background components. These observations do not justify changing
ROM state, starting pitch, cadence, or inventing an EQ fit. Exact starting-state
and envelope agreement remains a cabinet/listening validation item.

## Production changes and lifecycle

- `modes/bonus_collect/code/bonus_collect.py`: retains one named one-shot delay,
  schedules only after score/lamp/sound descendant events finish, sends a BCP
  step index once per counted step, and owns start/stop/sync lifecycle.
- `modes/bonus_collect/config/bonus_collect.yaml`: **66.368 ms** ordinary steps,
  **165.448 ms** last-award-to-next-pass-first-award nominal spacing. The pass
  gap replaces the ordinary interval; it is not an added delay. Removed the
  empty pass tick, delayed restore, and incorrect `bump` sound mapping.
- The original 80 ms initial presentation pause remains. Last-step completion
  occurs one normal interval later, allowing its 40 ms fade and some sound
  before the mode stops. Score and lamp decrement remain atomic as requested.
  Saved bonus lamps are restored at the beginning of the pass pause; the normal
  configured 40 ms fade remains, although immediate restoration can supersede
  the last decrement's fade at a pass boundary.
- `audio/bonus_player.gd`, `fa64_renderer.gd`, `fa64_model.json`: one controlled
  effects player renders finite derived bursts. No background/attract start is
  possible from a step command alone. Duplicate/stale steps and generations
  are rejected. A fresh collection resets step state; a pass pause does not.
- `audio/firepower_server.gd`: adds the bonus child/handler and reset/disconnect
  cleanup. `fp03_player.gd`, FP03 source, rate logic, smoothing and existing
  protocol are unchanged. No MPF/GMC framework files were patched.

Installed MPF is 0.81.0.dev4. Its `ms` validator truncates fractional values;
settings therefore use floats explicitly in milliseconds. DelayManager passes
those floats to the clock without truncation. Tests assert the actual event
intervals, not just configuration strings.

On a display reconnect/reset, MPF sends fresh eligibility and the current step
under a new generation. It does not replay previously counted audio. Mode stop
cancels pending delays and stops the audio; disconnect/reset also clears the
Godot player. Rendering is performed on Godot's main thread through the existing
local BCP handler mechanism. Physical host/render latency is not simulated.

## Validation and remaining cabinet checks

New/updated tests are `machine_tests/test_bonus_collect.py` and
`gmc_tests/test_bonus_audio.gd`. They cover fractional cadence, inter-pass spacing,
no catch-up after delayed delivery, atomic score/decrements, all multipliers,
40 ms fades, continuous audio step numbering, final cleanup, sync without replay,
stale-message rejection, one voice, exact DAC state progression, independent
PCM rendering, and FP03 playback independence. The legacy 39-by-5 accounting
regression remains. Existing background tests and the original FP03 Godot test
also run unchanged.

Results:

- ROM model verification: 84,096 DAC writes matched across 146 states, followed
  by silence; five independent PCM reference hashes verified.
- Focused bonus/background tests: **26 passed**, 20.634 s.
- Full requested machine discovery: **79 passed**, 59.155 s.
- New bonus Godot checks: **exit 0**; existing FP03 Godot checks: **exit 0**.
  Both retain the previously documented Godot shutdown ObjectDB/resource warning.
- `git diff --check`: passed. No commit or push.

Research artifacts added: this report, `bonus_research/asset_analysis.json`,
`dac_checks.json`, `render_checks.json`, `verify_fa64.py`, `fa64_initial.wav`,
`fa64_23x3_reference.wav`, and `reference_spectrogram.png`. The prior bonus report
has a continuation link. The uploaded M4A and other pre-existing working-tree
changes were preserved.

Cabinet checks still required: source character and volume against the recording,
starting and final pitch at known counts, inter-pass continuity, Pi rendering/BCP
latency, audible retrigger artifacts, score/lamp agreement, and clean exits to
next-ball/game-over/service. Automated checks prove the software model and
lifecycle; they cannot certify the physical amplifier/speaker response.

## Collection multiplier-lamp countdown

The collection display now consumes multiplier levels at pass boundaries:

| Achieved multiplier | Display through collection |
| --- | --- |
| 1X | No multiplier lamp |
| 2X | 2X -> none (final 1X pass) |
| 3X | 3X -> 2X -> none |
| 4X | 4X -> 3X -> 2X -> none |
| 5X | 5X -> 4X -> 3X -> 2X -> none |

Gameplay uses a single lit multiplier indicator. Collection preserves that
representation: after a pass's last score/decrement/sound event finishes, the
completed level fades off and the next lower level fades on, if it has a lamp.
This happens at the start of the existing 165.448 ms pause, with no additional
timer or effect on the continuously increasing audio step. Individual bonus
steps do not change the multiplier display.

`BonusCollect._display_multiplier` owns this temporary state. The earned player
`bonus_multiplier` continues to control the total passes and is not decremented
for the animation. The existing completion reset to 1 remains. The collector's
priority-250 light-stack entries override gameplay presentation and are removed
on mode stop. Gameplay relinquishes its lamps at ball ending, so the achieved
display is restored immediately on collection takeover to avoid a startup
blink. Every subsequent transition inherits the machine's **40 ms fade**.

This is the user's requested presentation, not an asserted original L-6 lamp
sequence. The targeted ROM check at **73A7–73BE** found a decrement of pass RAM
47, restoration of the saved 18-byte lamp/state block through 76DD, and the
busy-wait call. It does **not** explicitly clear the consumed multiplier lamp;
the restored block includes the original multiplier flags. This difference was
reported before implementation, and the requested display order was retained.

Changes for this addition are limited to `bonus_collect.py`, its machine tests,
and this documentation. The tests exercise 1X–5X using normal multiplier-earning
events, verify full brightness through the earlier steps, check that the off
fade begins at the final award timestamp and lasts exactly 40 ms, verify score,
bonus lamps and audio step synchronization, and exercise next-ball setup and
earning 2X again after collection cleanup. No Godot/audio source change was
needed for this presentation addition.

Addition validation: **16 focused bonus tests passed** (14.256 s); the full
machine suite passed **84 tests** (64.997 s); `git diff --check` passed. Godot
tests were not rerun because this addition changes only MPF lamp presentation.
Cabinet confirmation of the visible descending indicators and fade remains.
No commit or push.
