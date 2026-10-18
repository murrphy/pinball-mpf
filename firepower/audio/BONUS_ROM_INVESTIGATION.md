# Firepower L-6 end-of-ball bonus research — 2026-10-02

Later continuation: [BONUS_LONG_RUN.md](BONUS_LONG_RUN.md) diagnoses the full
39x5 failure and records the authorized restoration of the 29-unit maximum.
The range-defect descriptions below are historical.

Continuation: [BONUS_AUDIO_SOURCE.md](BONUS_AUDIO_SOURCE.md) records the later
validated FA64-derived source and implementation. The status below is historical.

Research only. **Do not promote a new sound or cadence from this report yet.**
The foreground command and nominal timing are established; identification of a
matching project recording is not. No production code, configuration, audio,
or tests were changed. Existing user changes were preserved.

## Evidence and scope

Reused `/tmp/fp-l6`, `/tmp/fp-l6.dis`, the existing bounded 6800 interpreter,
MAME instruction-cycle table, Sound ROM 3 disassembly, published sample archive,
and previous hardware-clock research. No downloads or installations were needed.
All seven ROM CRCs rechecked against the values in
[ROM_INVESTIGATION.md](ROM_INVESTIGATION.md#sources-and-revision):
`af6eb0b9 f75ade1a 242ec687 fdd3b983 2145f8ab 1c978a4a 55a10d13`.
No ROM binaries were added to the repository.

Addresses below are hexadecimal. Foreground and sound RAM are distinct.
Disassembly comments are secondary evidence: the actual binary and executed
branch/table indices determine identity. In particular, the table called
`BONSND` at FED8 is **not** the frequency table used by this Firepower command.

Temporary analysis artifacts:

- `/tmp/fp_bonus_probe.py`, `/tmp/fp-bonus-probes.json`: foreground probes.
- `/tmp/fp_bonus_audio.py`, `/tmp/fp-bonus-sound-states.json`: repeated sound
  commands and state captures, including the end of the valid range.
- `/tmp/fp_bonus_match.py`, `/tmp/fp-bonus-match.txt`: isolated synthesis and
  exploratory rate-dependent spectral comparisons.
- `/tmp/fp-bonus-single.wav`, `/tmp/fp-bonus-synth.wav`: isolated and repeated
  synthesized DAC output, for research only.
- `/tmp/fp-bonus-audio-analysis.txt`: project effect inventory and features.

These probes reuse `/tmp/fp_trace.py` and `/tmp/fp_synth.py`; they are not a
validated general emulator. Foreground waits are accelerated to the next timer
tick; the separately instruction-counted inter-pass loop is substituted by its
cycle count. IRQ timer decrements are injected at nominal phase boundaries.
Actual IRQ execution overhead, PIA behavior, lamp scanning, and analog audio
filtering are not emulated. Sound synthesis executes original instructions with
the cached 6800 cycle table, using the earlier nominal 895,000 Hz sound clock.

## Foreground routine and representation

The previously established drain/accounting path is `6DE9–6E45`: stable ball
accounting, all three balls accounted for, stabilization timer expired, and an
active played ball. `6E2D–6E3B` finishes queued sound repetitions. `6E3D–6E40`
sets descriptor pointer 8C to 61DD; byte 61DD is **13**, the encoded 1,000-point
award. `6E42` sends BGEND through 627C; `6E45` enters **7306**.

`7306–7339` clears effect bookkeeping, saves the 18-byte current-player lamp/state
record, clears active-play bit 80 in RAM 78, and branches around normal bonus for
attract/tilt/unplayed-ball cases. `7562` selects the saved player record at
`0094 + 18 * player_index`; 92 retains its pointer. `733C–7340` saves award code
13 in **5C**. `7342–7345` selects bonus descriptor **60C0**.

There is no scalar foreground “remaining bonus” byte in this collector:

| Descriptor/state | Meaning |
| --- | --- |
| 60C0–60C3 = `0D 15 17 18` | Nine cumulative unit flags 0D–15, 10K flag 17, 20K flag 18 |
| Flag helper 7953 | Zero-based flag ID: address `10 + id//8`, mask `1 << (id%8)` |
| 792C / 793D | Set steady / clear flag, also clear its flashing-bank bit at address +0A |
| 777C / 779C | Test steady/flashing state |
| 60C4–60C7 = `23 24 25 26` | Multiplier lamp flags 2X, 3X, 4X, 5X |
| 60C8–60CB = `02 03 04 05` | Corresponding numeric pass counts |
| RAM 47 | Remaining passes, selected highest-first at 7347–735C; defaults to 1 |

For ordinary valid states, value is the number of lit unit flags plus 10 or 20
from the decade flag. The original 20-to-19 transition clears 20K, sets 10K,
and fills the nine units. The 10-to-9 transition clears 10K and fills units.
The collector does not require a modern scalar bonus variable to do this.

`735E–7361` calls game hook **6872**, which is an RTS. It introduces no bonus
sound initialization or pitch modifier. `7363–7393` searches/decrements lamp
state, using `78A8` with A=E0 for a unit decrement, or `7897` to refill units
when borrowing from a decade.

### Actual order and pass boundaries

```text
on confirmed normal end of ball:
    finish pending foreground effects
    send BGEND
    save player lamp/state record
    clear active-play flag
    award_code = 0x13
    passes = highest lit multiplier, otherwise 1

repeat:
    if a unit is lit:
        clear highest remaining unit
    else if 20K is lit:
        clear 20K; set 10K; set all nine units
    else if 10K is lit:
        clear 10K; set all nine units
    else:
        passes -= 1
        if passes == 0: go to 73C0
        restore saved lamp/state record
        busy_wait(A=0x60, B=0)
        continue

    wait until RAM[3A] == 0          # 739C–739E
    add 1,000 to packed-BCD score    # 73A0–73A2 -> 7A00–7A37
    RAM[3A] = 4                     # 7A3D–7A50, ROM[60BF]
    send token 0x96                 # 7A52–7A53, ROM[60BE]
    perform score-threshold checks
    continue                       # 73A5 -> 7363
```

Thus the lamp-memory decrement is **before the wait and score**, not an atomic
score/lamp/sound operation. Except at startup/pass boundaries, the next lamp
decrement follows the previous award and precedes its own award by approximately
one interval. Physical lamp visibility additionally depends on scanning and
incandescent response. This proves a logical sequencing difference, not a
reason to silently dismantle the working MPF atomic presentation.

`73A7–73BE` decrements the pass count, restores the saved 18-byte record through
76DD, then calls **76D9 with A=60 and B=00**. This is a real inter-pass pause,
not an extra empty four-tick countdown step. No sound is sent during restoration
or this pause. The prior four-tick timer expires during the busy-wait.

The inner loop is `DECB; BNE` (256 iterations when B starts at zero), followed
by `DECA; BNE`, repeated 96 times. Including routine entry/return, the bounded
cycle execution counts **148,057 CPU cycles**, or **165.447843 ms** at the
foreground E clock, before interrupt-service overhead. Including surrounding
restore/search/score-check code, the simplified 12-by-3 probe has about
**175.045 ms between last and next-pass first award**. That latter number is
an illustrative probe result, not a measured hardware specification.

`73C0` increments the ball audit through 7AA9, calls game cleanup hook **684F**
via 60DE, then handles extra ball/player/ball advancement at `73CC–73E7`.
The next-ball path is `73E9–73F9 -> 635A`; the final-ball route can branch to
7426. There is no collector-specific final four-tick wait or sound-stop command
at 73C0. The last sound may finish its finite burst or be interrupted by the
next command. Tilt bypasses normal collection to 73C0.

## Countdown timing versus the recording

The exact timer load is **4** at **7A50**, from **60BF**. IRQ code
**7F17–7F29** decrements timer 3A on phase 00, once per 16 IRQs. Reusing the
schematic/PinMAME-supported System 6 timebase from the previous investigation:

```text
E_clock = 3,579,545 / 4 Hz
timer_tick = 16 * 928 / E_clock = 16.5920529006 ms
ordinary_countdown_interval = 4 * timer_tick = 66.3682116023 ms
ordinary_countdown_frequency = 15.0674544 Hz
```

Every multiplier pass uses this same timer load. This is a phase-driven timer:
the first interval after a new load can differ because the IRQ phase is not
reset. The first score need not wait four ticks if 3A is already zero. The
first interval following the busy-wait also depends on phase. A modern one-shot
66.3682116 ms delay reproduces nominal cadence, not every original phase edge.

The reported 64 ms / 15.6 Hz component is close (about **3.7% shorter**) but is
not the literal hardware-derived four-tick interval. It is not evidence for
replacing the ROM result by exactly 64 ms. Moreover, the synthesized waveform
itself has a roughly 64 ms cycle around counted step 19 (see below), whereas
its cycle changes substantially through collection. Both sound periodicity
and retrigger timing can therefore contribute. The supplied audio observations
alone cannot distinguish them. No matching 9.92-second reference recording or
video file was located; the submitted measurements were not independently
remeasured.

For base bonus N and 3X, there are 3N actual awards. From first award to last,
an approximate duration is `(3N-1)*66.368 ms + 2*~109 ms`, replacing two normal
intervals by illustrative ~175 ms pass transitions. Examples: N=12 gives about
2.54 s; N=20 about 4.13 s; N=29 about 5.93 s. Startup phase, drain processing,
IRQ overhead, and sound tails are additional uncertainties. The full 9.92 s
clip and transient at 3.56 s do not identify either bonus boundary or N. In
particular, subtracting them and treating all 6.36 s as collection is unjustified.

## Sound command and pitch state

**Foreground token 96 -> raw five-bit command 16 (decimal 22).**
`71CB–71E9` masks the token with 1F, pulses the output through 2202, then clears
the command bits. Every actual 1,000-point step sends the same command. There
is no foreground per-step pitch parameter or separate modifier command.

Sound-board dispatch is **FBBF -> FC10 -> FC24–FC32 -> FCE1 -> FA64** (`BON2`
in the cached disassembly). The human label “Laser Ball Bonus #2” does not
exclude its use by Firepower; the L-6 foreground command proves the connection.

At **FBD1–FBD7**, commands other than 16 clear sound RAM **07 (B2FLG)**.
BGEND 13 before collection therefore ensures a fresh start. When 07 is zero,
**FA64–FA70** sets it and loads vector index **0D** through FA88. The actual
address is `FE68 + 7*0D = FEC3`, whose bytes are:

```text
81 09 11 FF 00 01 90
8 waveform repetitions; 1 cycle per pattern entry
waveform index 9 at FE0E (72 samples)
predecay factor 0x11; echo decay 0
frequency increment -1; delta counter initially 0
one frequency-table entry at FED8+90 = FF68, value 0x92 (146)
```

The predecay is literal repeated 8-bit subtraction at **FB90–FBBE**, not an
assumed smooth amplitude envelope. It materially reshapes the waveform.

On later command 16, 07 remains set and **FA73 -> FB37** advances the retained
state: decrement RAM 18, add FF to **RAM 24 (FOFSET)**, validate the frequency
range, then start GWAVE again. **FAF8–FAFC** forms the period in RAM 22 from
the table byte plus this offset. Natural burst completion sees B2FLG at
FB31–FB35 and returns; it does **not** advance pitch autonomously.

```text
first command after reset:
    offset = 0; delta_counter = 0; B2FLG = 1
each subsequent command 16:
    delta_counter = (delta_counter - 1) & 255
    if delta_counter == 0: return
    offset = (offset - 1) & 255
    retain only positive, non-underflowed frequency entries
    if none remain: return
on each audible command:
    period = (146 + offset) & 255
    restart waveform/pattern; play up to eight waveform cycles
```

For counted step **n=1..145**, period is exactly **147-n**. Pitch follows the
number of commands already collected across the **whole multiplied bonus**,
not remaining bonus, a multiplier lookup, or a foreground pitch counter.
There is **no reset between passes**; silence during a pass pause does not
clear B2FLG. Another command can reset it, which is why unrelated sounds must
not be treated as harmless in an exact monophonic emulation.

| Counted step n | Period | Relative cycle frequency | Waveform cycle at 895 kHz |
| --- | --- | --- | --- |
| 1 | 146 | 1.000000 | 72.6056 ms |
| 2 | 145 | 1.006692 | 72.1229 ms |
| 29 | 118 | 1.228718 | 59.0905 ms |
| 30 | 117 | 1.238838 | 58.6078 ms |
| 58 | 89 | 1.610139 | 45.0927 ms |
| 87 | 60 | 2.334962 | 31.0950 ms |
| 116 | 31 | 4.246634 | 17.0972 ms |
| 145 | 2 | 23.425379 | 3.0994 ms |

The maximum valid original 29-by-5 case ends at period 2, offset **70** hex.
The counter wraps from 00 to FF on command 2; this is intentional unsigned
state, not saturation. Outside valid original play, command 146 reaches period
1; command 147 removes the sole frequency entry at zero. Probes through 165
produce no new GWAVE entry after that cutoff. Do not model an audible period
wrap to 255 or clamp to an invented final pitch. Arbitrary further invalid
commands are not a supported game-state model.

The current project's documented 0–39 range defect matters: 39-by-5 exceeds
this original audible progression. Correcting that defect would need explicit
scope in an eventual production patch; it was not changed here.

### Relative pitch mapping

For this 72-sample waveform, a steady cycle takes **72*(6*p+25)+110** CPU cycles
(confirmed by consecutive DAC writes 72 samples apart). Thus the normalized
frequency approximation is:

```text
relative_rate(n) = 64982 / (72*(6*(147-n)+25)+110)
```

This is better than a bare `146/p` approximation because instruction overhead
dominates at the high end. It is a **synthesis-cycle frequency ratio**, not a
calibration for any existing WAV. A recording would require its original state,
onset, duration, and filtering to be identified before setting
`pitch_scale = calibrated_start_rate * relative_rate(n)`.

An isolated initial command generates approximately **607 ms** of output in
the bounded synthesis. Normal 66 ms retriggering interrupts that burst. At high
states, all eight cycles fit inside one countdown interval. A static sample
can only approximate that behavior if its source state and complete burst are
known. The analysis WAVs have no emulated speaker/filter chain and are not
production-ready audio.

## Local asset inventory and identification limit

All project effects were decoded locally with ffmpeg to mono 22,050 Hz PCM.
Durations and Hann-window spectral centroids below are descriptive, not command
labels. Centroids include low-frequency energy and depend on windowing.

| File | Seconds | Spectral centroid Hz |
| --- | --- | --- |
| FP01 | 1.2821 | 3794 |
| FP02 | 1.4389 | 1767 |
| FP03 | 6.1449 | 614 |
| FP04 | 0.9164 | 775 |
| FP05 | 0.9687 | 1343 |
| FP06 | 0.8380 | 3643 |
| FP07 | 1.3344 | 632 |
| FP08 | 0.3156 | 688 |
| FP09 | 2.4315 | 2680 |
| FP10 | 0.9948 | 680 |
| FP11 | 5.3834 | 1699 |
| FP12 | 0.7858 | 618 |
| FP13 | 0.4723 | 100 |
| FP14 | 0.3940 | 966 |
| FP15 | 1.7001 | 1013 |
| FP16 | 0.9687 | 224 |
| FP17 | 1.2821 | 549 |
| bump | 0.1567 | 289 |
| fire_targets / side_bumpers | 0.9404 | 775 |
| power_target | 1.7241 | 1013 |

Most numbered effects have roughly 20–30 ms of quiet onset before a strong
attack. For example, FP08's successive 10 ms RMS windows rise through
0.006, 0.206, 0.306, 0.345, 0.445; FP13 rises to 0.279 then fluctuates near
0.17–0.24; FP12 and FP16 attack strongly near 0.44 and 0.55 respectively.
These are normalized PCM measurements, not perceived loudness judgments.
Restarting an untrimmed asset every 66 ms would repeatedly include that onset.

Exploratory comparison: average 2048-point Hann magnitude spectra, with bins
below about 43 Hz removed, scanning 161 logarithmic rate factors from 0.25 to
4 for the synthesized initial burst. Provisional candidates:

| Candidate | Best cosine similarity | Rate applied to synthesis for comparison |
| --- | --- | --- |
| FP17 | 0.8294 | 0.6050 |
| FP12 | 0.8282 | 0.5844 |
| FP16 | 0.8211 | 0.2872 |
| FP13 | 0.8168 | 0.2872 |
| FP08 | 0.7844 | 1.8661 |
| FP14 | 0.7123 | 0.5743 |

**This ranking is weak and does not identify a winner.** The known current
`bump` scores 0.8288 by the same metric, demonstrating its poor discrimination.
The required large and inconsistent rate changes also do not establish a
source state. FP16 has a relatively close unshifted centroid; FP13 is short and
low-frequency; FP12/FP17 score slightly higher after rate fitting. None has
sufficient command, temporal-envelope, and waveform evidence to select it.

The cached published Firepower MP3 archive was checked against FP08, FP12,
FP13, FP14, FP16, and FP17: after aligning a 529-frame offset at 22,050 Hz,
PCM correlations are at least 0.999988. These WAVs inherit the archive recordings,
so the archive does not provide an independent command identity. Cached
command-reference audio is for decimal 16, 17, and 20, not required decimal 22.
Filename FP16 must not be equated with raw hexadecimal command 16.

No defensible best matching **identified** asset is established. A command-22
recording, or a calibrated waveform/envelope match to a particular retained
state, remains the missing evidence. Do not substitute the top spectral score
as production authorization.

## Smallest eventual implementation and validation

The Firepower-local server in `audio/firepower_server.gd` already supports
machine-local BCP handlers and a child AudioStreamPlayer. Reuse that extension
point with a **separate bonus child/player**, keeping `fp03_player.gd`, its
stream, smoothing, and command protocol intact. Do not repurpose the FP03
player: it loops continuously and treats repeated starts as synchronization,
whereas bonus commands restart a finite waveform on every counted step.

Once an asset is identified, use one finite stream, max_polyphony=1, explicit
collection generation/state, immediate per-trigger pitch, and stop/reset on
bonus mode stop, disconnect, service/reset, or completion. Advance pitch only
on an actual counted step, never the current empty pass-transition tick. Reset
once per complete collection; retain state across multiplier passes. No global
GMC/MPF patch or collection of pre-pitched files is needed.

Keep the current named one-shot/no-catch-up scheduler and 40 ms fade. Replace
the nominal step delay only together with confirmed sound integration. Model
the inter-pass pause explicitly, accounting for its overlap with the prior
timer; do not simply add 165 ms after another full 66 ms delay. Document whether
the existing atomic lamp/score presentation is intentionally retained despite
the original lamp-memory lead. The ROM establishes that difference, but a
physical lamp observation should guide whether reproducing it improves fidelity.

The present mode also has an 80 ms initial delay, an empty transition tick,
and a 10 ms deferred restore. Those are modern presentation choices, not values
recovered here. Final-mode audio stop is the requested modern lifecycle rule;
the original collector itself does not issue a final stop command.

For an eventual patch, deterministic tests must cover exact nominal cadence,
delayed-callback no-catch-up, one 1,000-point award per decrement, 1X–5X step
totals and boundaries, continuous per-step pitch/state including start/end,
the selected asset, one audio instance, lifecycle stop, 40 ms fade, unchanged
FP03 behavior, and the existing regressions. No implementation tests were added
because production was not changed.

Physical verification still required: synchronized lamp/score/audio observation
at known bonus and multiplier, pass-gap duration, first/last audible state,
high-count pitch, mode-completion tails, and no bonus sound in attract/gameplay.

## Validation results and delivery status

- Bounded foreground probes: bases 0, 1, 9, 10, 12, 20, 29 crossed with every
  multiplier 1–5 (35 cases). Verified N*M awards, exact remaining-lamp sequence
  per pass, packed-BCD score total N*M*1,000, and only raw command 16 per award.
- Sound probes: 165 consecutive command-16 triggers; verified offsets and the
  single table entry through 146, then no new GWAVE entry at 147–165. These
  establish state behavior within the stated interpreter limits.
- Existing focused bonus/background tests: **20 passed**, 17.106 s.
- Requested full machine discovery: **73 passed**, 55.676 s.
- `git diff --check`: passed. The new report was also checked for trailing
  whitespace; Git's normal diff check does not include untracked files.
- Godot tests: **not run**; no Godot/audio implementation was changed. Machine
  tests validate the existing production baseline, not the proposed ROM mapping.
- Files added by this task: **this report only**. No production or test changes,
  no commit, no push. Existing working-tree changes remain present.

Stop condition: cadence/control identity is established, but the matching
project sound asset and its calibrated playback mapping are unresolved. This
is the requested research-only outcome rather than another guessed correction.
