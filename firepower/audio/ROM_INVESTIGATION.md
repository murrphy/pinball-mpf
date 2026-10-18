# Firepower L-6 background ROM investigation — updated 2026-09-23

Research only. Production audio, the temporary positive-score `0.0005` driver,
playback endpoints, smoothing, lifecycle and production tests remain unchanged.

**Result:** BG1 uses an eligible-play-time comparison, serviced by particular
foreground event paths. It is neither a score accumulator nor an autonomous
wall-clock background scheduler. With the standard System 6 interrupt circuit,
ordinary counter-high-byte changes are approximately **4.2476 seconds** apart;
actual BG1 commands wait for an eligible foreground opportunity and sound gates.

Three corrections to the initial investigation are material:

- `77A8` is an event epilogue, **not part of every idle main-loop pass**. A settled
  idle ball accumulates eligible time but does not autonomously advance BG1.
- The System 6 schematic supports **928 E-clock cycles per IRQ**, matching
  PinMAME. MAME's `980 + 32` model gives a different result and is not the basis
  for the recommended original-hardware cadence.
- The sound state resets at BGEND; **the foreground timer and saved reference
  do not reset each ball**. No multiball-end low-stage reset was found. The
  recovered multiball paths preserve those values and the background flag.

FP03 now has useful spectral evidence supporting **low-state BG1**, but an exact
command-labelled recording match remains unproven. The implementation model
below is sufficiently concrete for review; reproducing every sound-priority
interaction and validating physical timing still require care.

## Sources and revision

Analyzed original **Firepower L-6 (`frpwr_l6`), game 497**, using locally
disassembled binaries. No matching ROM set was found in the searched local home
and temporary directories before downloading reference material.

Sources:

- [MAME System 6 implementation and ROM manifest](https://github.com/mamedev/mame/blob/master/src/mame/pinball/s6.cpp)
- [MAME 6800 instruction decoding table](https://github.com/mamedev/mame/blob/master/src/devices/cpu/m6800/6800dasm.cpp)
- [L-6 archive download page](https://www.planetemu.net/rom/mame-roms-merged/frpwr-l6)
- [Williams/Planetary Pinball ROM index](https://www.planetarypinball.com/mm5/Williams/tech/sys6roms.html)
  and its L-2 archive, used only for comparison; L-2 was not substituted for L-6.
- [WiLL-i-ROMS sound disassembly archive](https://codeberg.org/kaputnikGo/WiLL-i-ROMS),
  `Pinball Sound ROMS/Sound ROM 3.asm` and `Talk/FirepowerSpeech6.asm`.
- [Original Williams instruction booklet](https://www.pinrepair.com/sys37/manuals/wms6-firepower.pdf),
  pages 4 and 10: background-sound adjustment and original switch identities.
- [Published Firepower sample archive](https://www.firepowerpinball.com/downloads/FirepowerSounds.zip)
- [WiLL-i-ROMS reference recordings](https://akm.net.au/will-i-roms/audio.html)

All seven binaries below matched MAME's CRC32 and SHA-1. ROMs and downloaded
disassemblies remain under `/tmp`, outside the project. No ROM image was modified
or added to the project.

| Binary | CPU address | CRC32 | SHA-1 |
| --- | --- | --- | --- |
| prom1_6.474 | 6000–61FF | af6eb0b9 | 28f8366737e09ffd60cb5ea55a5734143cdb9663 |
| prom2.474 | 6200–63FF | f75ade1a | a5572c5c721dbcb82988b709f4ef2119118e37c2 |
| prom3.474 | 6400–65FF | 242ec687 | c3366c898a66c78034687e6a6000193d52be4141 |
| gamerom.716 | 6800–6FFF | fdd3b983 | fb5d1eb01589311cf4b2ef16e25db03d40bca2f7 |
| green1.716 | 7000–77FF | 2145f8ab | ddf63208559a3a08d4e88327c55426b0eed27654 |
| green2.716 | 7800–7FFF | 1c978a4a | 1959184764643d58f1740c54bb74c2aad7d667d2 |
| sound3.716 | F800–FFFF | 55a10d13 | 521d4cdfb0ed8178b3594cedceae93b772a951a4 |

The local decoder used MAME's instruction lengths, addressing modes and
6800-validity flags. Linear output includes data interpreted as instructions;
only the specific executable paths traced below should be treated as code.
The first investigation was static analysis. The continuation adds bounded
instruction-level execution of selected paths; it is not a boot-to-game,
cycle-accurate machine emulator. See validation limits below.


## Additional sources and verification

- [PinMAME System 6 source](https://github.com/vpinball/pinmame/blob/master/src/wpc/s6.c):
  `S6_IRQFREQ = 3579545 / 4 / (0x380 + 32)`.
- [System 6 CPU logic diagram, issue 4](https://www.firepowerpinball.com/2ya/downloads/03-cpulogic.pdf):
  IC25 4020, IC11 NAND, IC5 reset logic, J6, BUS phase 2 and CR1.
  This is a redrawn hardware schematic, not a frequency measurement.
- [MAME 6800 CPU timing table](https://github.com/mamedev/mame/blob/master/src/devices/cpu/m6800/m6800.cpp):
  `cycles_6800`, used for the bounded sound synthesis comparison.
- [MAME Williams sound-board implementation](https://github.com/mamedev/mame/blob/master/src/mame/shared/williamssound.cpp):
  sound CPU clock and sound-input wiring/DIP handling. Its S6 `write()` remaps
  upper bits; flash-lamp output must not be mistaken for a raw chime-mode bit.

Retrieved/reference-checked during this continuation. The pre-existing L-6
files were reused and their CRCs rechecked. Speech ROMs additionally matched
the Firepower manifest:

| Binary | CRC32 | SHA-1 |
| --- | --- | --- |
| v_ic5.532 | 1737fdd2 | 6307e0ae715e97294ee8aaaeb2e2bebb0cb590c2 |
| v_ic6.532 | e56f7aa2 | cb922c3f4d91285dda4ccae880c2d798a82fd51b |
| v_ic7.532 | 94c5c0a7 | ff7c618d1666c1d5c3319fdd72c1af2846659290 |

All addresses below are hexadecimal unless explicitly described otherwise.
Foreground and sound-board RAM are separate address spaces.

## Counter, timebase and reference (deliverables 1–7)

### What `74:75` measures

Foreground RAM **0074:0075** is a big-endian, 16-bit eligible-play-time counter.
The BG1 code reads only **0074**, its high byte. It is shared game-time/audit
machinery, not a dedicated background-stage counter:

```text
7F67: require B == 08                 # display/IRQ phase
7F6B: A = RAM[78]
7F6D: if A & 03: skip increment       # attract/game-over or tilt
7F71: if !(A & 80): skip increment    # ball not yet marked active
7F75: X = word[74]
7F77: X += 1
7F78: if X == 0D90:
7F7D:     RAM[78] = A | 10
7F81:     X = 0
7F84: word[74] = X
```

`71A1–71AD` consumes bit `10`, clears it, and calls `7AA9` with A=1/B=10
(decimal audit index 10). Thus the wrap also feeds accumulated play-time
accounting. The ROM's audit interval must not be assumed to be exactly one
minute: its literal count is **3472**, not 3600 or 65536.

The phase is generated by the IRQ display scan at `7E4C–7EA3`: it masks `7D`
to its low nibble, uses that phase, then increments it. `7F0A–7F69` selects
phase 08 once per **16 IRQs**. This is a crystal-derived display/system IRQ,
not mains zero crossing or a 60 Hz tick. Timers such as `3A` decrement on the
other selected phase, 00 (`7F10–7F29`).

### Conversion to seconds

On the standard schematic, IC25 counts E/BUS-phase-2 clocks. Q7/Q8/Q9 feed
the NAND: the combined condition begins at `0380` (896). Q5 and the IRQ reset
logic terminate/reset the pulse after another 32 counts. Therefore:

```text
E clock                    = crystal / 4
nominal IRQ period         = 928 / E_clock
counter tick               = 16 * 928 / E_clock
ordinary high-byte change  = 256 counter ticks
last segment before wrap   = 144 counter ticks   # 0D00 -> 0D90 -> 0000
```

Using the more precise nominal crystal value in PinMAME:

| Quantity | Value |
| --- | --- |
| Crystal | 3,579,545 Hz |
| E clock | 894,886.25 Hz |
| IRQ frequency | 964.31708 Hz |
| One `74:75` tick | 0.0165920529 s |
| Ordinary 256-tick segment | **4.24756554 s** |
| Final 144-tick segment | **2.38925562 s** |
| Whole `0D90` counter cycle | **57.60760767 s** |

The schematic labels CR1 approximately 3.58 MHz; using exactly 3,580,000 Hz
changes the ordinary segment to 4.24703 s. These are **nominal hardware-derived
values**, not measured machine timings. Crystal tolerance, interrupt masking,
PIA interrupt activity and foreground dispatch latency affect observation.

For comparison only, current MAME uses 980+32 cycles and 3.58 MHz: 4.63145 s
per ordinary segment. That was the previous document's estimate. It conflicts
with the schematic decode and PinMAME, so it is superseded here. Do not average
the two emulator values or tune by ear.

### Saved reference `DC`

Foreground **00DC** stores the last observed high byte for which the advance
routine accepted an update. `7030–7036` clears it, along with the other low RAM,
on the CPU reset/startup path. The same startup clear initializes `74:75`.

The accepted-update store is **6294**. There is no subtraction, minimum score,
background-stage lookup or increasing threshold:

```text
6284: if !(RAM[01AD] & 01): return    # adjustment 35 background enabled
628A: B = RAM[74]
628C: if B == RAM[DC]: return
6290: if sound_gate_is_blocked(): return
6294: RAM[DC] = B
6296: send_BG1_increment()           # token 91 -> command 11
```

No ordinary new-ball initialization resets `74:75` or `DC`. The normal write
paths were traced including the indirect block-copy routines: player records
occupy `94–DB`, the ball-state copies target `10–21`, and game-over scratch uses
`70–73`. The counter/reference lie outside those copies. A bounded execution
of `6800` with counter `05AB` and reference `05` preserved both.

Consequences:

- The next ball inherits the partial counter segment and saved reference.
- First advance need not wait a whole 4.2476 s after launch/first switch.
- Missing multiple high-byte changes produces **one** later advance, not
  catch-up commands. Missing a complete counter cycle can leave the high byte
  equal to the reference and produce no advance at that opportunity.
- Cadence is independent of BG1 stage. The short interval is a **timer-wrap**
  property, unrelated to sound state 32 or sound state 36.

## Foreground opportunities and gates (deliverables 8–10)

### Important correction: timer expiration alone does not call BG1

The main idle loop is `7062 ... 71B0 -> 7062`. Its game-specific callback is
`6CDC`, via the pointer at `60D8`. Neither the settled callback path nor the
settled idle loop calls `6284` or `77A8` merely because `74` changed.

The relevant entry paths are:

| Entry | Why BG1 can be checked |
| --- | --- |
| `6A26 -> 6A29 -> 6284` | Jet-bumper handlers, switches 25–28; check before their sound/score work. |
| `6274 -> 6277 -> 6284` | Plum-bob tilt-warning handler, before `7993` updates the tilt-warning count. This is an explicit non-score opportunity. |
| `7300 -> 76F1 -> 7303 -> 77A8` | Common gameplay event epilogue, including handlers/deferred work that return through it. |
| `620A = 48 00 62 98` | Event table entry calls `6298 -> 6284` while flag 48 is active. |

`681F–6824` sends the initial command and sets flag **48**, which maps through
`7953` to **RAM[19] bit 01** (flag identifiers are zero-based). `629A–629E`
discards its call return and resumes at `77DD`, bypassing `77D8`'s normal
clear-the-flag operation. This makes the flag persist across event processing;
it does **not** make the event table run continuously.

A bounded real-instruction probe ran 1,000 settled main-loop passes (574,182
instructions), with active play, background flag enabled, clear sound gates,
and `74=03/DC=00`: no visit to `6284`, no BG1 output, and DC stayed 00.
Executing the common event epilogue then emitted one command 11 and set DC=03.

Therefore **an idle ball on the playfield accumulates eligible time, but a
settled idle machine does not issue an advance until an appropriate event**.
Pending callbacks can provide an opportunity; not every switch does. For
example, shooter switch 46 dispatches straight to `7062`, and the lane-change
handler ordinarily returns there as well. This corrects the earlier idle-poll
claim without changing the finding that positive scoring is not the driver.

The literal activation condition is reaching `76F1` with bit 80 clear, not
“any switch” or “first positive score.” A plum-bob warning also reaches the
common epilogue through `7993 -> 79BC -> 7300`; it can therefore mark a ball
active even before an ordinary scoring shot. Coin, shooter and other handlers
that bypass this path do not provide that activation.

### The sound gate

`62D3–62E5` implements exactly:

```text
allowed = (RAM[70] == 0) and (RAM[3A] < 0x10 or RAM[58] == 0x89)
```

- **70:** foreground FIRE/POWER award presentation countdown. `6931–6938`
  computes `2 * (RAM[15] & 07) + 3` and enters `6C9F`, which stores it and
  immediately decrements it. While nonzero, `6CB8–6CD3` sets `3A=FF` and
  schedules `6CA7` after 0A timer ticks using callback slots `40/41` or
  `43/44`. Completion/fallback `6CAC–6CB3` clears 70/3A and queues its final
  effect. Ball initialization also clears 70 at `6835`. It is **not** a
  ball-count or multiball flag. Attract uses the address as unrelated scratch.
- **3A:** shared effect/score-sequence delay, decremented on IRQ phase 00.
  The exact inequality is **less than 16**, not less-than-or-equal. Delays of
  16 or more block unless the next exception applies.
- **58:** queued sound token; `77F0–780B` loads it and the repetition/delay
  state from the effect table `608D–60AC`. Token **89**, raw effect 09, is
  expressly allowed despite a long 3A delay. The code tests the token even
  if the repetition count in 57 is zero; don't add an invented queue-active
  condition.
- Blocked checks leave DC untouched. Opening a gate is **not itself** a call
  to the BG1 check; another foreground opportunity must occur.

The phase gates and command gates are distinct. `6284` itself does not test
78, shooter occupancy, score, number of balls, or the sound board's BG1 stage.
Its callers/game lifecycle supply the remaining context.

### Lifecycle eligibility by situation

| Situation | Time counter / command behavior |
| --- | --- |
| Fresh ball in shooter lane | Initial BG1 already requested; 78 bit 80 remains clear, so timer is paused. Shooter switch alone does not set it. |
| First qualifying playfield event | `76F1–76F7` sets bit 80 through gameplay processing. This begins eligible timing, not the initial sound. |
| Normal single-ball play | Counter runs; listed event opportunities may advance if the high byte differs and sound gates pass. |
| Scoring | Neither score amount nor positive-score update is a trigger. Particular switch paths and resulting sound delays matter. |
| Idle live ball | Counter runs; no unconditional idle BG1 polling. An event after the wait may advance once. |
| Multiball | Counter continues because normal active-play flags remain; release presentation can withhold foreground opportunities and occupy sound. No ball-count gate in 6284. |
| Return to one live ball | Same timer/reference/background flag; no dedicated sound reset on the two-to-one transition was found. |
| Drain recognition | Timer remains eligible until end-of-ball clears bit 80; BGEND is sent after the foreground confirms its ball-accounting conditions and finishes queued effects. |
| Bonus | `7326–7328` clears bit 80; background already ended at 6E42. |
| Tilt | `79AA–79AC` sets bit 02, immediately inhibiting time accumulation. Next game-loop handling sends BGEND once. |
| Game over / attract | 78 bit 01 inhibits timing; normal background event processing is not continuously run. |
| CPU reset / slam tilt | Startup clears low RAM including timer/reference; slam-tilt wrapper first sends BGEND. |
| Service / diagnostics | Ordinary game timing/dispatch cannot be applied to diagnostic execution. Sound-board diagnostics explicitly select sounds and can exercise synthesis independently. |

“Shooter time does not count” applies to a **fresh, not-yet-active ball**. There
is no continuous shooter-switch exclusion: returning to the shooter lane after
bit 80 is set does not, by itself, pause the timer.

## Start, termination and multiball (deliverables 11–15)

### New ball and next ball

The next-ball path calls the game hook via `73F6–73F9`, pointer `60DA=635A`.
`635A–6380` leads to `6800`; `6819–6824` checks adjustment 35, sends token 91,
and enables persistent event flag 48. The ordinary ball release through
`682B–682D -> 7832` follows that command. Thus BG1 starts **before ball serve
completes**, not on shooter exit or first score.

After the previous ball's BGEND cleared the sound flags, that command takes
BG1 from silence/flag 0 to **flag 1**, the first audible state. It does not
explicitly zero the sound state itself; reset depends on prior termination.
`7420` leaves 78=00 for the served ball. `76F1` later marks active play.

The sound stage resets between normally terminated balls. The timer and DC do
not. “Complete reset” is therefore **false if it includes timer phase**.

### BGEND and tilt

Foreground helper **627C** loads 93 and outputs through `62A1/6252`.
Normal identified callers/entries are:

- **6D55:** first handling of tilt (`78 bit 02`, with the low nibble of 015B
  still zero); it increments 015B as a latch, sends BGEND, then tokens 87 and
  the tilt sound from 60CF. Subsequent main-loop passes do not resend it.
- **6E42:** confirmed end-of-ball, immediately before jumping to bonus at 7306.
- **626F:** slam-tilt/reset wrapper, BSR 627C followed by JMP 7000.

On the sound board, **FA0D–FA13** clears **04 (BG1FLG)** and **05 (BG2FLG)**.
The sound reset path **F820–F829** also clears them. Neither action writes the
foreground counter or DC. `BGEND` should not be modeled as resetting that clock.

### Drain is confirmed by ball accounting, not the first outhole closure

`6CDC–6CF0` handles the outhole input (switch 9, RAM[2A] bit 01), requests its
kick and updates the 0159 activity latch. The end-of-ball decision is later:

```text
6DE9: retained = physical_lock_bits & RAM[0154]
6301: accounted = (retained << 3) | (RAM[25] & 04) | (RAM[24] & 07)
6DF0: compare accounted with previous RAM[71]; save new value
6DF4: require stable equality
6DF7: require accounted bit 01              # right ball-ramp switch 57
6310: require three set bits among the six accounted positions
6E00: require RAM[72] == 0
6E04: require low_nibble(RAM[0159]) != 0
6E15: require RAM[78] bit 80 for normal played-ball ending
6E1C: clear callback state
6E25: limit saved-ball/extra-ball state as coded
6E2D: wait out and finish queued sound repetitions
6E42: BGEND
6E45: jump 7306
7328: clear active-play bit 80 before bonus collection
```

`6E48` reloads the stabilization counter 72 with 1E as applicable; `640B–640F`
decrements it on IRQ phase 0C. Its nominal 30-phase duration is about 0.498 s,
with phase/foreground recognition latency. Physical lock bits come from
`632C` (original switches 13, 30, 36); the three ramp positions are switches
51, 57, 58. An outhole closure is **not itself** the all-balls-accounted test.
If there has been no qualifying active-play event, the `6E19 -> 6830` route
handles the unplayed-ball case instead of normal bonus/BGEND processing.

An instruction probe with two ramp balls and one still live returned to the
main loop without BGEND. With all three ramp switches, the stable reference,
0159 latch and 72 expiration satisfied, it sent 13 and reached 7306.

### Multiball start and return to single ball

The third qualifying lock reaches **6B6C**. The release presentation runs
through **6C69**, including token 98 at `6BD5`/`6BF9`, token 97 at `6BFE`, and
**94 (TURBO)** at `6C0F`. It temporarily changes display/scan timing and runs
wait loops. It then restores player/display data and rejoins `7300`.

**This path does not call BGEND, clear flag 48, clear the active-play bit,
reset 74:75/DC, or send a BG2 advance.** Existing BG1 state can be acoustically
interrupted by speech/effects. The sound IRQ exit at `FC3E–FC52` resumes the
selected background; positive BG1FLG sends execution to `F9D3`. That recalculates
the waveform seed, but does not reset the stage.

The low-five-bit effect sequence in the bounded release trace included
`03 ... 18/03 ... 18/17/14` for the release presentation; **no 13 or 15**.
The counter changed from 0500 to 0732 under the probe's injected IRQ schedule;
DC stayed 05. That number is evidence of preservation/continued accumulation,
**not a measured release duration** (the foreground probe was not cycle-timed).

The normal ball-accounting path waits until all three balls are accounted for;
it contains no two-live-balls-to-one-live-ball BGEND/restart branch. A qualifying
jet event with two balls on the ramp and one live accepted the outstanding
counter change and sent 11, not 13 followed by a new initial 11.

Accordingly, the user's remembered low restart after multiball is **not
explained by an L-6 foreground stage-reset mechanism in the recovered code**.
Do not silently convert that recollection into a ROM claim. Waveform restarting
after effects, the slow states 32–36, or the eventual 36-to-1 wrap are possible
perceptual explanations, not verified explanations of that memory. A recording
with command/RAM capture would resolve the observational discrepancy.

## Command decoding and actual BG1 stages (deliverables 16–19, 21)

At sound IRQ **FC14**, A is decremented before table dispatch. Raw commands are:

| Foreground token | Raw command | Sound routine |
| --- | --- | --- |
| 91 | **11** | BG1INC at F9C0 |
| 93 | **13** | BGEND at FA0D |
| 95, if sent | **15** | BG2INC at FA14 |

Raw 10 is KNOCK, raw 12 is SP1, raw 14 is TURBO. The ten-token 90 burst from
`6981/60AB` is not ten background advances. The shooter-release sound at
`6DB2` is also TURBO, not BG2.

The executable callers, effect table `608D–60AC`, and the examined indirect
sound sequences do not supply a gameplay BG2 transition. Speech dispatch
`DDF6–DE8B` handles selected tokens and can substitute 00, 01, or 14 on its
special paths; it does not turn these game tokens into a BG2 advance or BGEND.
The relevant speech-dispatch bytes were checked against `v_ic6.532`; the
published listing has differences elsewhere and is not the binary authority.
This supports **ordinary L-6 BG1 progression without a BG2 transition**, not a
claim that diagnostic operation or arbitrary sound-board inputs cannot use BG2.

Sound RAM **04** holds BG1FLG, with bit 80 used as an override flag. `F9C0–F9D2`:

```text
BG2FLG |= 80
B = BG1FLG & 7F
if B == 36: B = 0                    # decimal 36 = hex 24
BG1FLG = B + 1
```

The actual sequence is **1 through 36, then 1**, not saturation at 31 or 32.
`VARPRM` clamps only the synthesis parameter calculation to effective state 32.
There is no foreground stage counter/cap in `6284`.

### Why state 32 slows abruptly

For s=min(BG1FLG,32), `F9E0` starts X at 56 and B at 32-s. The first loop adds
16 while B>15. The second loop at `F9F3` adds 8 **before decrementing/testing B**.
At s=32, B enters this loop as zero, underflows to 255, and runs 256 times:

```text
T(s) = 56 + 16*max(32-s-15,0) + 8*min(32-s,15), 1 <= s <= 31
T(32..36) = 56 + 8*256 = 2104
```

| Actual flag | 1 | 8 | 16 | 17 | 24 | 31 | 32–36 | next after 36 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sweep parameter | 432 | 320 | 192 | 176 | 120 | 64 | 2104 | 432 |

This is a demonstrated eight-bit loop-underflow effect. Whether its author
intended the audible result cannot be recovered from instructions alone.
It is not a BG2 transition, a special foreground command, or unreachable solely
because the foreground caps progression.

### Constructive foreground reachability

A bounded probe executed the actual `7F67` tick path and actual jet handler
`6A26`, supplying one eligible jet closure at each high-byte transition with
sound cooldowns expired. Starting at counter zero and sound state 1:

| Eligible counter ticks | Counter after wrap(s) | BG1 flag |
| --- | --- | --- |
| 7456 | 0200 | 31 |
| **7712** | **0300** | **32** |
| 8736 | 0700 | 36 |
| 8992 | 0800 | 1 |

Thus a sufficiently long normal active ball with adequate event opportunities
can reach state 32, state 36, and wrap. This requires no impossible RAM stage
injection or special BG2 command. The initial timer-zero example reaches state
32 at approximately **127.958 s** eligible time and wraps to 1 at **149.196 s**.
Those are illustrative prompt-service times, not guaranteed ball ages: inherited
phase, gated/missed opportunities and intervening sound handling change them.

There are **36 command stages**, **32 distinct sweep-parameter values**, and
only **31 monotonically accelerating values**. States 32–36 share the slow
parameter; repeated commands can still change the waveform seed. They must not
be collapsed into a permanently saturated “highest pitch” stage.

## FP03 identification (deliverable 20)

The established archive match remains unchanged:

```text
modes/sounds/FP03.mp3
50,074 bytes; mono 22050 Hz; about 6.25925 s
SHA-256 0a9a22d89aa313c4c8ad5d53df1fa3688132d24aa51d988da5e5bda232a22f56
```

The archive contains no command manifest. MAME's S6 driver synthesizes electronic
sound with the Williams sound device; its generic samples cover mechanical
sounds such as the outhole/knocker. It does not establish an FP03 filename map.
WiLL-i-ROMS recording numbers also cannot simply be read as raw command numbers
(for example its page calls recording 9 “RESET”).

New bounded comparison: the verified sound ROM was executed from BG1 VARPRM
with flag 1 and seed 3C, and from BG2 with flag 1. DAC writes were resampled at
22050 Hz using MAME's 6800 instruction-cycle table and the nominal 895 kHz
sound E clock. This omits analog filtering and is not full sound-board emulation.

Comparing the first 1.5 seconds spectrally, FP03 and BG1 have similar broadband,
repeating sweep texture; the tested BG2 state has conspicuous tonal bands.
Log-spectrum temporal autocorrelation (512-sample Hann windows, 32-sample hop,
bins 2–99, searching lags 0.08–0.30 s) peaks at:

| Audio | Peak repeating interval |
| --- | --- |
| FP03, first two seconds used for feature calculation | 0.191565 s |
| Synthesized BG1 flag 1 | 0.193016 s |
| Synthesized BG2 flag 1 | 0.233651 s |

The BG1 match is within one analysis hop (1.45 ms). It is **stronger practical
support for low-state BG1**, not proof of identical waveform/seed, recording
speed, or exact captured command sequence. Only the initial BG2 state was tested;
this is not an exhaustive classifier of every possible sound. Operationally,
FP03 is a reasonable BG1 candidate. Do not claim that its entire recording is a
rising sequence through all BG1 stages, or derive a universal pitch table from
this comparison alone.

## Recommended MPF model (deliverable 23; not implemented)

Keep three independent pieces of state:

1. **Eligible time phase:** a machine-wide counter modulo 3472, paused when no
   ball has yet been activated or when tilted/attract. Preserve it across normal
   balls and players. Its nominal tick is 16.592 ms on standard System 6 hardware.
2. **Accepted high-byte reference:** DC-equivalent, also preserved across balls.
3. **Sound state:** BG1 command stage 0/1–36, where BGEND sets zero and an initial
   command advances zero to one. Preserve stage across multiball unless a real
   termination occurs; keep synthesis/playback restarts distinct from stage reset.

```text
on fresh ball serve preparation, if background enabled:
    emit BG1_INC                     # normally 0 -> 1 after prior BGEND
    enable background event flag
    ball_active = false             # original fresh-ball lifecycle
    # preserve timer phase and reference

on first event reaching original active-play processing:
    ball_active = true

on clock tick:
    if ball_active and not tilted and not attract:
        timer = (timer + 1) % 3472
    # do not emit sound from this callback

on original-equivalent foreground opportunity:
    if background enabled and (timer >> 8) != reference:
        if award_countdown == 0 and (sound_delay < 16 or queued_token == 0x89):
            reference = timer >> 8
            emit BG1_INC             # one only, no catch-up loop

on confirmed end-of-ball after queued effects, tilt handling, or slam tilt:
    emit BGEND
    sound_stage = 0
    # pause eligible time as original lifecycle dictates; do not zero its phase
```

Preserve command stage 32–36 and wrap even if the eventual audio renderer uses
an approximation. Do not equate reciprocal sweep parameter with exact playback
pitch: the synthesis modifies duty-cycle periods and a seed as well.

A faithful implementation should map **specific original event opportunities**
(jets, relevant playfield handler completion, tilt warning and relevant deferred
work), and represent the effect-priority gate deliberately. A generic positive
score handler cannot preserve their ordering, and an unconditional 4.25-second
callback cannot preserve idle behavior. Current MPF sound playback/queueing is
not a one-to-one representation of RAM 3A/58/70; translating those semantic
states requires a separate implementation review. Do not substitute “any sound
is playing” for the recovered gate.

No automatic stop-at-multiball/start-low-at-one-ball behavior is recommended as
ROM fidelity on this evidence. Retaining such a behavior would be an explicit
project preference pending contrary original-machine evidence.

## Evidence limits and remaining uncertainties (deliverable 22)

- **Nominal versus measured timing:** 928-cycle divider is supported by the
  schematic and PinMAME. No physical oscilloscope/logic-analyzer capture was made.
  PIA service activity and interrupt masking were not exhaustively cycle-traced.
- **Bounded execution:** the temporary interpreter executes original instructions
  for selected initialized states; it does not emulate every PIA, speech analog
  path, interrupt edge, ball trajectory, or operator configuration. Foreground
  lifecycle probes inject IRQs at instruction-count intervals. Their sequencing
  and RAM preservation results are evidence; their wall-time durations are not.
- **Multiball recollection:** no matching L-6 low-stage reset mechanism was found;
  observed audio on an original machine remains the appropriate cross-check.
- **FP03:** practical BG1 identification is supported, but exact state/seed and
  a calibrated mapping from ROM parameters to MP3 playback rate remain open.
- **Diagnostics:** CPU service and sound-board diagnostic programs are separate
  execution paths. Their entire command repertoire was not treated as normal
  gameplay or exhaustively modeled. Reset/startup and normal gameplay gates were.
- **Implementation mapping:** every modern MPF event corresponding to a ROM
  opportunity, and every modern equivalent of 3A/58/70, still needs explicit
  selection. This is integration work, not license to replace the recovered rule
  with a score or wall-clock heuristic.

## Continuation validation and preservation

Executed from temporary local files, with no ROM copies in production/Git:

- ROM CRC verification and speech CRC/SHA-1 verification against the manifest.
- Main-loop versus gameplay-event BG1 probe; accepted/deferred command checks at
  sound-delay boundaries 0/15/16/255, including the 89 exception and 70 gate.
- Tick probes for 78 values 00/01/02/80/81/82/88/90 and the 0D90 wrap.
- Ball setup, shooter wait, first standup and subsequent ball setup probes.
- Multiball-release command trace; two-ramp-ball survivor jet; all-three-ramp
  confirmed-end-of-ball trace; one-shot tilt BGEND trace.
- Sound BG1 increment/parameter execution through 38 commands, confirming all
  stages, underflow plateau and wrap; foreground reachability trace above.
- Bounded DAC synthesis and numerical spectral comparison with FP03.

Temporary artifacts include `/tmp/fp_trace.py`, `/tmp/fp_experiments.py`,
`/tmp/fp_lifecycle.py`, `/tmp/fp_more.py`, `/tmp/fp_reachability.py`,
`/tmp/fp_synth.py`, `/tmp/fp_compare.py`, `/tmp/fp_audio_features.py`, reference
sources and WAV/spectral output. These are not production dependencies or a
validated reusable emulator. Durable conclusions, numeric results and executable
path pseudocode are recorded here so the report does not depend on retaining /tmp.

Only this document was changed in the project during the continuation. No
production tests were added or changed; no commit or push was performed.
The pre-existing uncommitted production files were preserved. The prior task's
8 targeted tests, 47 machine tests and headless Godot check validated that
placeholder implementation, **not ROM fidelity**; they were not rerun for this
research-document-only change. Document whitespace/diff checks were performed.

## Implemented MPF mapping (2026-09-24; separate from historical research)

The historical findings above were reused without ROM retrieval, checksum,
disassembly, spectral or lifecycle re-analysis. This section supersedes only
statements about the production placeholder still being unchanged; it does not
revise the recovered ROM evidence. Installed MPF source is 0.81.0.dev4.

Implementation lives in `modes/background_audio/code/background_audio.py`:

- **Activation/opportunities:** `sw_pop_bumpers_active` checks immediately before
  its sound handlers. `s_spinner_active`, `sw_side_bumper_active`,
  `sw_fire_arrow_active`, `s_power_1_active` through `s_power_3_active`,
  `s_lane_f_active`, `s_lane_i_active`, `s_lane_r_active`, `s_lane_e_active`,
  `s_top_target_active`, left/right return-lane and out-lane active events,
  `s_lock_1_active` through `s_lock_3_active`, and `tilt_warning` activate time
  and request a deferred `firepower_background_check` callback. MPF drains nested
  event work before callbacks, so same-hit award presentation can block the
  check. These are selected current gameplay paths, not a claim of exhaustive
  one-for-one ROM dispatch reconstruction. Coin/shooter/flipper/score events and
  arbitrary switch activity are excluded. No synthetic idle opportunity exists.
- **Award gate (70 equivalent):** actual `firepower_bonus_awarded` show start/stop
  events emitted for 10K/30K/50K/Special presentations maintain award state. Its
  lighting, timing, loops and scoring are unchanged. This follows the current
  presentation duration, not the ROM's award-dependent countdown length.
- **Delay/token approximation:** the current sound player sends independent
  effects and speech, with no shared 3A/58 equivalent. The existing
  `firepower_multiball_release` show supplies a bounded release-presentation gate
  via start/stop events. Individual effects have no invented cooldown. There is
  no verified modern token-89 equivalent; FP09 is not assumed to be that token.
  This leaves original short/long effect-delay priority unresolved. Neither
  mixer activity nor media duration controls the gate. Gate opening alone never
  requests an increment. This deliberately stops short of inventing ROM queue
  behavior or broadly emulating the sound board.
- **Timer:** accumulated eligible seconds plus MPF monotonic start timestamp;
  `floor(seconds / (16*928*4/3579545)) % 3472`. Counter high byte is read on
  opportunities; no repeating callback. It reproduces 256-tick ordinary segments
  and the 144-tick final segment. Fractional phase is retained when paused.
- **Persistence:** phase and accepted high-byte reference are initialized once
  on the machine's mode object and survive balls, players, games and multiball.
  A successful opportunity stores the high byte and issues exactly one increment;
  blocked/equal checks leave it untouched, even after multiple missed boundaries.
- **Stage/rendering:** BGEND sets 0; initial increment sets 1; increments run
  through 36 and wrap to 1. Stages 1-31 map linearly from 0.85 to 1.25. Distinct
  stages 32-36 all map to configurable `slow_region_rate`, initially 0.85. This
  approximates the discontinuous slow region conservatively; it is not a measured
  ROM-to-MP3 pitch conversion. Existing FP03 evidence/tuning was inspected and
  reused; no physical listening test was possible in this session. Smoothing
  remains 150 ms and the single stream architecture is retained.
- **Lifecycle:** start stage 1 in `ball_starting` mode preparation before
  `ball_started`/serve completion, with time inactive until selected gameplay.
  `ball_will_end` is the existing confirmed pre-bonus boundary: BGEND stops FP03,
  sets stage 0, and pauses phase without zeroing phase/reference. Tilt performs
  the same termination once; subsequent stop events cannot reissue it. Game end,
  service, slam tilt and teardown clean up. Multiball start/return-to-one no longer
  stop/reset playback. Existing effects coexist on their existing buses; original
  monophonic masking/resumption is not reproduced. No bonus delay is added to wait
  for queued sounds, since this project has no equivalent foreground sound queue.

The old score-update increment and its progress/configuration state were removed.
The BCP snapshot now reports `stage` instead of obsolete `progress`; GMC continues
using the same cycle/rate protocol. Show changes add only presentation lifecycle
notifications. No scoring, coils, locks, drain, bonus, lighting content, displays,
high scores, accounting, diagnostics or gameplay/attract sound ownership changed.

Implementation validation: 15 background tests plus 2 existing gameplay-sound
ownership tests passed; full machine discovery passed all 56 tests. Updated Godot
FP03 checks (including slow-region updates without replacing playback) exited 0;
the previously recorded shutdown resource warning persists. Diff/whitespace checks
passed. These results validate the implemented mapping, not exact physical ROM
audio fidelity. No new external downloads, ROM tools, commit or push were needed.
