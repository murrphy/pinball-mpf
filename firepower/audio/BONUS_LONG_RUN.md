# Full-range FA64 diagnosis — 2026-10-04

Production before this change allowed 39 units. Maximum 5X therefore issued
195 triggers: 5X 1–39, 4X 40–78, 3X 79–117, 2X 118–156, 1X 157–195.
The user explicitly authorized restoring the original 29-unit maximum after
being told that keeping 195 audible triggers would require a modern extension.
Production now caps earned bonus at 29: 145 triggers, with passes 1–29, 30–58,
59–87, 88–116, 117–145. Total maximum collection award is 145,000 points.

## Evidence and limits

Current production already uses direct FA64 synthesis. It loads no source WAV,
and sets AudioStreamPlayer.pitch_scale to 1.0 for every trigger. The generated
stream duration and effective playback duration are identical. The initial WAV
in bonus_research is a reference only, 607.041667 ms at 48 kHz.

The existing independent ROM DAC hashes match all 146 audible states and the
empty 147th state in the Godot test. Prior research executed through 165 and
found no further GWAVE output. The cached /tmp ROM binaries and interpreter
are absent, and a search under /home/murray found no cached fp_synth.py,
fp_trace.py or fp-disasm.py. No downloads were performed. This task could not
freshly execute the ROM through 195 or 256; do not mistake renderer measurements
beyond 147 for independent CPU state traces. CPU pointer/scratch state beyond
the previously validated range remains unmeasured in this continuation.

[fa64_full_range.csv](bonus_research/fa64_full_range.csv) records all 195 modern
rendered states, measured PCM RMS, duration, relative cycle pitch, frequency,
and trigger spacing. Added offset/counter fields are algebraic reconstructions
from prior ROM research through 147, explicitly labeled rather than fresh RAM
captures. Rows after 147 deliberately leave original CPU state unclaimed.

## State and root cause

B2FLG (RAM 07) initializes once, remains set between passes. First offset and
counter are zero. Subsequent unsigned 8-bit decrements give (1-n)&255 in RAM 24
and RAM 18, and the single table entry 146 plus offset produces period 147-n
through 146. The waveform is unchanged: 72 post-predecay samples, eight cycles,
one pattern cycle and no echo decay. No new envelope, clamp or pitch reset.

At 31/32 periods are 116/115; at 63/64 they are 84/83. At 127/128 they are
20/19, offsets and counters 130/129. Offset/counter cross the signed boundary
at 129/130 (128/127), with no special effect in the verified DAC hashes.
Step 128 is the 11th step in the former 2X pass, and is fully playable.
Step 146 has period 1; step 147 reaches zero and exhausts the sole frequency
entry. Production renderer explicitly returns null thereafter. An audible
period wrap, saturation or waveform change is unsupported by the ROM evidence.
255/256 is outside both the old and corrected production ranges; no behavior
there is invented here.

The exact disappearance in current code starts at **147**, the 30th step of
the old 2X pass. Every remaining trigger through 195 has no stream. Before that,
finite ROM bursts become shorter than the step interval at **135**. This may
explain the earlier perceptual thinning, but no cabinet observation proves its
precise perceptual threshold. PCM remains strong through 146.

The root cause is the 39-unit gameplay range exceeding the original FA64
sequence, not playback-speed exhaustion, a Godot pitch limit, ultrasonic output,
or a signed overflow at 128. The renderer implements the known ROM cutoff;
it does not extrapolate rising pitch past it. The method does not incorrectly
scale envelope duration: burst shortening follows executed DAC timing.

## Measured representative states before the fix

Cycle frequency is the 72-sample pattern repeat rate, not the strongest audible
harmonic. All pitch_scale values are **1.0**, including silent requests. Ordinary
spacing is 66.368 ms; pass-final rows 39/78/117/156 have 165.448 ms to the next
trigger. Row 195 instead has 66.368 ms until lifecycle stop.

| Trigger | Period | Relative cycle pitch | Cycle Hz | Generated/effective ms |
| --- | --- | --- | --- | --- |
| 1 | 146 | 1.000000 | 13.773 | 607.042 |
| 39 | 108 | 1.338014 | 18.429 | 434.271 |
| 78 | 69 | 2.048742 | 28.217 | 283.667 |
| 117 | 30 | 4.370007 | 60.188 | 133.083 |
| 118 | 29 | 4.500762 | 61.989 | 129.208 |
| 128 | 19 | 6.422415 | 88.456 | 90.604 |
| 135 | 12 | 9.160135 | 126.163 | 63.562 |
| 137 (2X midpoint) | 10 | 10.430498 | 143.660 | 55.854 |
| 145 (corrected final) | 2 | 23.425379 | 322.639 | 24.958 |
| 146 (last supported audible) | 1 | 27.746371 | 382.152 | 21.104 |
| 147 | exhausted | none | none | no stream |
| 156 | exhausted | none | none | no stream |
| 157 | exhausted | none | none | no stream |
| 195 | exhausted | none | none | no stream |

Maximum legal original state is period 2, relative pitch 23.425379, cycle
frequency 322.638789 Hz. Period 1 is executable but outside legal 29x5 play.
Highest Godot pitch_scale is 1.0. There is no arbitrary pitch cap.

## Change and verification

Only production bonus_ladder's increment limit and decade representation change.
The collector configuration comment now states 0..29. Audio renderer/player,
66.368 ms steps, 165.448 ms pass gap, one-shot/no-catch-up scheduler, +1000 per
step, 40 ms fades, earned multiplier, multiplier-lamp countdown, FP03 and other
sounds remain unchanged. Legal values retain their existing lamp representation.
The formerly invalid 30–39 state is no longer earned during gameplay. The
collector still scores directly injected out-of-range values; this patch does
not silently discard already supplied accounting state.

The maximum machine regression earns 50 bonus increments through production,
asserts saturation at 29, collects at earned 5X, and checks 145 awards, decrements,
audio step packets, score, pass/step intervals and final cleanup. Existing tests
cover multiplier transitions, fades and delayed callback without catch-up.
Godot exercises all 145 actual player triggers at nominal intervals, checks
non-null playback, pitch_scale=1, exact ROM period, RMS >1000 PCM units and
>10 ms of active PCM at every step, and clean final stop. It separately measures
all 195 old-range states and verifies the 147 cutoff. Exact DAC hashes remain
checked for 1–147. PCM energy checks prove rendered signal, not cabinet loudness.

Physical cabinet verification is still required at 29 units and 5X, especially
the final pass, sound level, pass continuity, lamps and clean completion.
No commit or push.

## Final validation and changed files

- Focused `python -m unittest machine_tests.test_bonus_collect`: 16 passed,
  14.562 seconds.
- Requested full discovery: 84 passed, 63.709 seconds.
- Godot full maximum bonus test: exit 0, including 145 timed player commands,
  195 rendered-range measurements and existing DAC/PCM/lifecycle checks.
- Existing FP03 Godot regression: exit 0.
- Both Godot runs retain the previously documented shutdown ObjectDB leak /
  one resource still in use warning.
- `git diff --check`: passed.

Files changed in this continuation (pre-existing user changes were preserved):

- `modes/bonus_ladder/config/bonus_ladder.yaml`: legal earning cap and decade lamps.
- `modes/bonus_collect/config/bonus_collect.yaml`: range comment only.
- `machine_tests/test_bonus_collect.py`: actual earning-cap / 145-step regression.
- `gmc_tests/test_bonus_audio.gd`: full-range measurements and legal playback test.
- `audio/bonus_research/fa64_full_range.csv`: measured 195-step diagnostic table.
- `audio/BONUS_LONG_RUN.md`: this report.
- `audio/BONUS_AUDIO_SOURCE.md`, `audio/BONUS_ROM_INVESTIGATION.md`: continuation links.
- `AGENTS.md`: corrected range-defect status.

No production audio code was changed. Fresh full CPU execution could not be
performed without the missing cached ROM/interpreter; existing validated hashes
and measured modern rendering are the evidence available in this session.
