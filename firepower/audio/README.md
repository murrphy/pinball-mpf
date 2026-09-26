# Firepower FP03 background

MPF owns the ROM-derived eligible-time counter, accepted reference and BG1
stage. GMC renders one looping instance of `sounds/fx/FP03.wav` on the music
bus. See [ROM_INVESTIGATION.md](ROM_INVESTIGATION.md) for the reused evidence and
the separate implemented-mapping section. No ROM or new audio download is needed.

## Tuning

`modes/background_audio/config/background_audio.yaml` owns BG1 rate and smoothing tuning:

- `enabled: true`: background command enable.
- `minimum_rate: 0.85`, `maximum_rate: 1.25`: linear stage 1-31 endpoints.
- `slow_region_rate: 0.85`: common approximation for distinct stages 32-36.
- `ramp_ms: 150`: short smoothing of live rate changes.

FP03-only level is `VOLUME_DB = -3.0` in `audio/fp03_player.gd`. It does not
change the music bus or any effects/speech player.

The mapping is `low + (stage - 1) / 30 * (high - low)` for stages 1-31;
32-36 use the slow-region rate. State 36 advances to 1. This is an audio-rendering
approximation, not an exact conversion of ROM sweep parameters to sample playback pitch.
The existing low-state identification and conservative physical tuning were
reused. The user reports that BG1 timing/state works well physically and has
verified the production 40 ms overlap-add loop as seamless on the cabinet.

## Timing and lifecycle

One nominal tick is `16 * 928 * 4 / 3579545` seconds. The mode stores accumulated
eligible seconds and an MPF monotonic-clock start timestamp; it derives the
counter as `floor(eligible_seconds / tick_seconds) % 3472` on demand. No periodic
background timer is scheduled. Normal high-byte boundaries are 256 ticks
(4.24756554 seconds); the final segment is 144 ticks (2.38925562 seconds).

A new ball starts FP03 at stage 1 during `ball_starting` mode preparation, before
serve completion. First selected gameplay activity starts eligible timing.
Shooter and flipper activity do not activate it; returning to the shooter after
activation does not pause it. Idle active-ball time accumulates, but only a
selected gameplay opportunity may consume a changed high byte, once. Scores
and score amounts do not drive progression. Blocked checks preserve the reference.

Phase/reference live on the persistent MPF mode object across balls, players,
multiball and games; process startup initializes them. `ball_will_end` stops FP03
before bonus, pauses timing and sets stage 0. Tilt, slam tilt, game end, service
entry and mode teardown also clean up. Multiball and return to one ball preserve
timing/reference/stage. The release presentation gates increments temporarily;
FP03 continues alongside existing effects/speech on separate buses.

The gate observes FIRE/POWER award and multiball-release presentation start/stop
events. It never observes mixer activity. The award show retains its existing
70 ms steps and `loops: 3` setting (four passes in installed MPF, 1.12 seconds).
Release lasts 2.85 seconds including MPF's existing one-second final step.
Stopping/replacing shows updates the gate without changing their lighting or
speech content. Gate opening does not itself advance BG1.

There is no modern shared effect-delay/token queue, so no justified token-89
exception mapping. Standalone effects remain ungated. This is a narrow semantic
approximation, not an emulation of all ROM sound priority or monophonic masking.
BGEND uses MPF's confirmed ball-ending boundary without delaying bonus to wait
for audio playback. See the investigation's mapping section for exact events.

## GMC ownership

MPF sends `firepower_background` directly to `local_display` with `action`,
`cycle`, `stage`, `rate`, and `ramp_ms`. `audio/firepower_server.gd` uses the
existing supported GMCServer override; no framework files are patched.
`fp03_player.gd` duplicates the existing WAV resource once and sets
`AudioStreamWAV.LOOP_FORWARD`, `loop_begin = 0`, and `loop_end = 135496`
(the full frame count, derived from stream length and mix rate). Import compression
is disabled, preserving 16-bit mono PCM at 22050 Hz without trim/normalization.
No `smpl` loop metadata exists in the source. The player applies live `pitch_scale`
(pitch and tempo together). Rate commands replace
the tween without restarting playback. Same-cycle sync is idempotent; a new ball
cycle restarts the stream. Stop, disconnect, BCP reset and teardown clean up.

## Validation and physical checks

Run from the Firepower directory:

```sh
/home/murray/mpf-venv/bin/python -m unittest machine_tests.test_background_audio machine_tests.test_gameplay_sounds
/home/murray/mpf-venv/bin/python -m unittest discover -s machine_tests -p '*.py'
godot --headless --path . --script res://gmc_tests/test_fp03.gd --log-file /tmp/firepower-fp03-test.log
git diff --check
```

Tests advance simulated MPF time, inspect outgoing BCP packets, and exercise real
switch/award/multiball/ball transitions. Godot checks interpolation, native loops,
playback identity, slow-region rate changes and cleanup. Logical tests do not
establish acoustic fidelity on the cabinet.

Cabinet regression checks:

1. Attract switch silence and intentional attract audio; fresh-ball shooter wait.
2. First gameplay activation; idle then jet produces one advance, not catch-up.
3. FIRE/POWER award and release gates, including effects/speech audibility.
4. Long play through stage 31, slow stages 32-36, and 36-to-1 wrap.
5. Multiball and return to one ball preserve the background state.
6. Drain/bonus, next-ball inherited phase, tilt, game over and service cleanup.
7. WAV loop continuity at low/high rates and during 150 ms ramps, plus the new
   FP03-only -3 dB balance on physical speakers.

The production WAV is 135496 frames (6.144943 seconds), mono PCM16 at 22050 Hz. Existing spectral/sample findings
support low BG1; they do not prove that the sample contains every BG1 state or that
these playback rates reproduce the original synthesis.

Validation for this implementation: 17 focused tests passed (15 background and
2 gameplay-sound tests); all 56 machine tests passed. The updated headless Godot
FP03 test exited 0 with no failed assertions. The previously documented ObjectDB /
resource-at-exit warning remains. Project stdout is disabled, so the success print
is suppressed. `git diff --check` and untracked implementation whitespace checks
passed. No commit or push was performed.

## Production loop provenance

The original sample had an audible low-energy seam even with native WAV looping.
Removing its quiet edges improved the seam but did not eliminate the cabinet gap.
The user physically verified a 40 ms equal-power overlap-add version as seamless
and sounding correct. That approved WAV was copied byte-for-byte to
`sounds/fx/FP03.wav`; production has no diagnostic source selector or dependency.
FP03 player volume remains -3 dB.

Construction used the original 137135-frame mono PCM16 / 22050 Hz WAV. Conservative
edge trimming removed 425 leading and 332 trailing frames, leaving 136378 frames.
The final 882 frames and first 882 frames were combined with equal-power weights:
`tail[i] * cos(pi*i/(2*881)) + head[i] * sin(pi*i/(2*881))`, rounded to PCM16.
This is a 40 ms overlap, reducing the loop to 135496 frames. The circular loop's
file boundary was rotated to frame 478 within the blend near a zero crossing.
There was no normalization, resampling or playback pitch processing. The overlap
is baked into one WAV; playback still uses one native-looping player.

Approved production WAV SHA-256:
`83c5c331d7208725b280e8df64c2394ddd31d4e53c79923f3485c617f7d03677`.
Raw PCM SHA-256:
`26472ba369cd90caf35c46433412db5e5f01e22abf05eb1e428d393c9dd11506`.
The Godot test checks both, including the imported PCM, to detect a stale import.

Local investigation scripts, captures, reports and variants remain under
`audio/diagnostics/`, ignored by Git. The exact pre-promotion source is archived
there as `archive/FP03_unprocessed.wav` for investigation reproducibility only
(SHA-256 `ab9aa4e1f10763d778148d807015eeb727f394734863cd3bc5f17cfe8f4d61e1`).
These files are not required to run production or its tests.

The runtime test observes two complete natural wraps without seeking, checks the
same player and playback object each frame, requires zero `finished` signals and
continuous `playing`, verifies pitch changes just before/after a wrap, and checks
-3 dB volume, unchanged bus volumes, one player and cleanup. Cabinet listening,
reported above, establishes the acoustic result separately from these checks.
