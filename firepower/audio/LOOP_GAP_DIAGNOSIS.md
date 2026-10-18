> Historical investigation: the cabinet-approved 40 ms overlap-add WAV is now
> production. See [README.md](README.md#production-loop-provenance) for final provenance.

# FP03 loop-gap measurements — 2026-09-24

## Result and scope

**The measured short quiet interval comes from the PCM asset. The reported
approximately one-third-second cabinet gap remains unresolved.** It did not
reproduce in the isolated Godot mixer capture or the clean Pi audio-server
monitor capture. There is no evidence here justifying a production workaround.

All captures ran on the cabinet host `firepower`, Raspberry Pi/aarch64, Debian
12, kernel `6.12.96+rpt-rpi-v8`, Godot `4.6.2.stable.official.71f334935`.
Production controller, source, rate mapping, 150 ms smoothing, -3 dB level,
BG1 state/timing/lifecycle and global audio settings were left unchanged.
The production controller/resource were copied into a diagnostic-only project;
this did not instrument an already-running gameplay session.

## 1. Raw PCM and boundary

`sounds/fx/FP03.wav` is uncompressed PCM16 little-endian, mono, **22050 Hz**,
**137135 frames**, **274270 audio bytes**, **6.219274376417234 seconds**.
RIFF chunks are `fmt `, `data`, `LIST`, and `id3 `; no `smpl` loop metadata.
The cached imported resource's decoded PCM is byte-for-byte equal to this data.

Near-silence has two explicitly different measurements:

- **Individual samples:** consecutive edge samples with absolute amplitude below
  -50 dBFS (103.62 PCM16 units). Leading: **447 frames / 20.272109 ms**. Trailing:
  **366 frames / 16.598639 ms**. The combined 36.870748 ms becomes 43.377350 ms
  at pitch 0.85, before accounting for output attenuation and resampling.
- **Level windows:** non-overlapping approximately 1 ms RMS blocks (22 source
  samples, 44 at 44100 Hz, 48 at 48000 Hz); both channels included. At -50 dBFS,
  source leading/trailing low-RMS spans are **20.952 / 17.959 ms**. At -30 dBFS
  they are **29.932 / 45.896 ms**. Window measurements have about 1 ms resolution.
  These are low-level intervals, not necessarily exact digital zero.

| Raw region | RMS dBFS | Peak dBFS |
| --- | ---: | ---: |
| First 500 ms | -9.153 | -0.064 |
| Final 500 ms | -9.205 | -0.234 |
| First 400 samples (18.14 ms) | -65.276 | -53.532 |
| Last 400 samples (18.14 ms) | -65.573 | -47.638 |

The beginning has roughly 20 ms of very low-level samples, then rises through
approximately -35 dBFS (10 ms RMS block) into roughly -10 dBFS. The end falls
from normal signal through roughly -39/-41 dBFS into -53 and -84 dBFS in its
last 10 ms blocks. The overall half-second averages conceal these quiet edges.

Last sample = 0; first sample = 12 PCM16 units. The join's jump is only
12/32768 (-68.73 dBFS relative to full-scale amplitude), with neighboring slopes
of 1 unit on each side. First/last 400-sample correlation is -0.0232: these quiet
edge sequences are not matching waveform cycles. The primary observed boundary
feature is a level dip, not a large instantaneous discontinuity. GarageBand's
reported clean loop does not prove the raw edge is sample-perfect.

## 2. Runtime/import verification and loop-end variants

The actual production controller was loaded in the isolated project, and its
private stream inspected after `_ready()`:

| Property | Measured value |
| --- | --- |
| Type/format | AudioStreamWAV / FORMAT_16_BITS (1) |
| mix_rate / stereo | 22050 / false |
| loop_mode | LOOP_FORWARD (1) |
| loop_begin | 0 |
| loop_end | **137135, equal to frame count** |
| PCM frame count | 137135 |
| Player volume | -3 dB |
| Output mixer | 44100 Hz stereo |

Import: `compress/mode=0`; normalization and trim false; forced mono, 8-bit,
and max-rate conversion false. No import resampling is enabled. Import
`edit/loop_mode=0`, begin 0, end -1 are overridden on the private runtime copy
by the controller. The production loop end is not frame_count - 1.

[Godot issue #119778](https://github.com/godotengine/godot/issues/119778) reports
inconsistent exclusive/inclusive forward-loop handling and possible one-frame
skip/overread. It is relevant to precision at the boundary, but is not evidence
of a third-second pause. Both 137135 and 137134 were tested without changing
production. Neither removed or materially lengthened the quiet interval.

## 3. Captured engine output

`AudioEffectRecord` recorded the production player's actual music-bus mix after
pitch/resampling/player gain. It did not record raw source concatenation. Each
case ran for 3.2 loops, with three natural wraps, the same playback object,
no stopped frames and no `finished` signals. Production rates 0.85 and 1.25 were
tested with Dummy output; rate 0.85 was additionally recorded through PulseAudio.

| Driver / pitch / loop_end | Three boundary low-RMS durations at -50 dBFS |
| --- | --- |
| Dummy / 0.85 / 137135 | 47.891, 50.884, 49.887 ms |
| Dummy / 0.85 / 137134 | 47.891, 48.889, 47.891 ms |
| Dummy / 1.25 / 137135 | 33.923, 34.921, 33.923 ms |
| Dummy / 1.25 / 137134 | 33.923, 33.923, 33.923 ms |
| PulseAudio / 0.85 / 137135 | 47.891, 50.884, 49.887 ms |

Absolute -50 dBFS after -3 dB player gain is not the same threshold as raw-source
-50 dBFS; resampling/window alignment also affects those numbers. At -30 dBFS,
the engine's low region is about 90 ms at 0.85 and 61 ms at 1.25. No internal
quiet span remotely near 333 ms was found at any tested threshold (-50/-40/-30).
Recording startup and deliberate end-of-test stop silence are excluded.

For production loop_end, expected periods are **7.316793384 s at 0.85** and
**4.975419501 s at 1.25**. Cross-correlating a 10000-sample early-playback segment
with each repetition gave periods of about **7.3170068 s** and **4.9754195 s**,
respectively (correlations 0.9978–1.0). There is no extra pause added each loop.
The slight low-rate deviation is far below a millisecond per loop. For end
137134, matched periods were about 7.31695 and 4.97538 s. Main-thread wrap
observation times are less precise and must not be treated as sample timing.

## 4. Pi output path, monitor capture and native comparison

Observed live route:

`Godot PCM16 stereo 44100 -> PulseAudio protocol -> PipeWire 1.2.7 ->
bcm2835 Headphones PCM16 stereo 48000 -> analog jack/amplifier/speaker`

The sink is `alsa_output.platform-fe00b840.mailbox.stereo-fallback`.
Godot reports driver **PulseAudio**, device **Default** resolving to this sink.
There is a 44100-to-48000 resampling layer in PipeWire. Native `paplay` instead
submitted mono 22050, also resampled/remixed by PipeWire.

The first sink-monitor comparison was contaminated by the separately running
Firepower process and discarded. After that process stopped, the comparison
was rerun with stream-count checks and snapshots showing only the diagnostic
playback. No existing application was stopped by these tools.

| Clean monitor capture, 48000 Hz | Three boundary low-RMS durations at -50 dBFS |
| --- | --- |
| Godot production controller, pitch 0.85 | **49, 49, 49 ms** |
| Native `paplay`, original rate 1.0 | **41, 42, 43 ms** |

Godot monitor quiet regions start at 8.458, 15.775, 23.092 s in the recording;
spacing is **7.317 s**. At -30 dBFS they are 90 ms each. Native monitor quiet
regions start at 6.840, 13.058, 19.277 s; spacing is about **6.219 s**. At -30
dBFS they are 76–77 ms. Neither has a third-second interruption at its joins.

Native comparison used one uninterrupted `paplay` session with a temporary WAV
containing four exact source PCM repetitions at -3 dB. This provides three exact
contiguous source joins without process/file-reopen delays. Production audio was
not edited. The short dip exists outside Godot as well; physical listening during
these sequences was not independently assessed by the agent.

The monitor records the audio server's digital output, **not the physical jack**.
`arecord -l` reports no capture hardware. There was no analog loopback recording,
so DAC/amplifier behavior is not measured. Nor does isolated playback reproduce
all load, effects, or device activity of an actual game.

### Buffer and error observations

- No project audio-driver/mix-rate/latency overrides. Godot defaults observed at
  runtime: **44100 Hz**, requested output latency **15 ms**.
- Godot reported output latency **39.821 ms** in the clean capture (36.870 ms in
  the earlier run). These are latency estimates, not gaps.
- Godot Pulse stream advertises `node.latency=512/44100`; initial live Firepower
  stream `tlength=6144` bytes (34.83 ms for stereo PCM16 at 44100), minreq=2048.
- PipeWire clock 48000; nominal quantum setting 1024, allowed 32–2048, no forced
  rate/quantum. Observed graph quantum was **512** during Godot playback and
  **2048** during native playback. No settings were changed by diagnostics.
- ALSA hardware observed: S16_LE stereo 48000, period_size **480 frames**,
  buffer_size **32768 frames**, configured headroom **480 frames**. Allocated
  buffer capacity (682.67 ms) must not be mistaken for a loop gap or current delay.
- PipeWire device ERR counter was **5** initially and **6** by native playback
  in the clean comparison. Diagnostic stream ERR counters were **0**. This is
  an observed device error-counter increment, not proof of a periodic underrun
  or its timing/cause. No corresponding repeated dropout appears in the monitor.
- Diagnostic Godot/ffmpeg logs contained no underrun, xrun, device-reopen or
  audio-server-reset warning. Historical service journal access was denied to
  this user, so historical absence of xruns cannot be asserted.

## 5. Supported conclusion and next step

The known quiet edge in the asset survives both Godot and native Pi playback.
Changing loop_end by one frame cannot remove tens of milliseconds of quiet PCM.
The one-third-second symptom was **not reproduced**, so it is not established
as a Godot mixer, backend, OS-server or hardware defect. In particular, continuous
server output in this isolated test does not by itself prove a hardware cause.

**No production fix is recommended yet for the claimed longer gap.** The smallest
next diagnostic is a synchronized analog/line-in recording and server-monitor
recording during a real game that audibly reproduces it. Also compare whether
the 41–49 ms measured dip is the perceived symptom rather than a separate longer
pause. If the asset's short dip is confirmed as the unwanted sound, selecting
verified useful-signal loop points would be a smaller candidate than adding
players or altering global buffers—but that change is not implemented here.

## 6. Files, artifacts and validation

New diagnostic files only:

- `audio/diagnostics/capture_fp03.gd`: music-bus capture and runtime metadata.
- `audio/diagnostics/run_capture.py`: isolated project staging/engine runner.
- `audio/diagnostics/compare_output.py`: native/Godot playback and sink monitor.
- `audio/diagnostics/analyze_pcm.py`: PCM/threshold measurements.
- `audio/diagnostics/README.md`: reproduction commands and capture limitations.
- This report, `audio/LOOP_GAP_DIAGNOSIS.md`.

Temporary evidence: `/tmp/fp03-dummy/` (four engine cases and analysis),
`/tmp/fp03-output-clean/` (valid engine/monitor/native captures, metadata and
before/during/after snapshots). `/tmp/fp03-output-compare/` is the contaminated
first monitor comparison and must not be used for output-continuity conclusions.
No captured audio, copies of production assets or ROMs were added to Git.

Validation: **17 focused tests passed** (background plus gameplay sound ownership),
**56 full machine tests passed**, existing FP03 Godot test **exited 0**. Existing
Godot test shutdown ObjectDB/resource warnings remain. New isolated capture runs
completed successfully. `git diff --check` and whitespace checks for new files
passed. No existing tests were weakened. No commit or push was performed.
