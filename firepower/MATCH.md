# Firepower L-6 Match — Function26 = 00 (ON)

This implements the recovered end-of-game Match on the physical FAST segmented
displays. No generic MPF percentage-based Match or animation,
LCD/GMC replacement, new lamp/device mapping or lock-counter modification.
High Score to Date now uses its existing queued hook; see
[HIGH_SCORE_TO_DATE.md](HIGH_SCORE_TO_DATE.md) for that separate feature.

## Original L-6 algorithm and ordering

The final regular ball and any awarded extras finish, with normal bonus first.
The regular-ball advancement path73D9–73E7 recognizes the configured final ball
and branches to **7426**. Match runs **before** High Score to Date processing at
746B–7504, and before the final game-over descriptor at7507 and attract state at
750D–751D. This differs from an assumed High Score-before-Match ordering.

The bytes were rechecked against the existing checksum-verified local L-6 set
(`/tmp/firepower-audit-l6`). `match_research/verify_l6.py` reuses the established
bounded6800 interpreter and asserts **156 cases** across all10 values and1–4
players, multiple matches, credits/free-play limits, disabled Match and BCD phase
wrap. `l6_checks.json` records evidence. Probes omit audit/display-PIA routines
and inject elapsed waits; they are not a complete machine or acoustic emulator.
No ROM/manual downloads were needed. MPF inspected:0.81.0.dev4.

| ROM path | Result |
|---|---|
| `7067–706C` | RAM46 adds10 hexadecimal, DAA, stores46 once per foreground main-loop iteration. Sequence00,10,…90,00; no PRNG/LFSR or player-score-dependent weighting. |
| `7426–742D` | Clears ball-in-play flag36 and configures display output. |
| `7430–7436` | Reads BCD adjustment at019B; nonzero skips Match (Function26=01). Zero enables it. |
| `7438–743F` | Sets Match lamp flag35 (`RAM16 bit20`), samples RAM46 into RAM03, the credits/ball display's ball/match byte. |
| `7441–7455` | Compares that complete BCD byte with score byte atX+2 for each four-byte player-score record, player indices0 throughRAM56 inclusive. |
| `7457–7459` | RAM67 holds total matching players; zero skips Match sound/credit work. |
| `745B–745E`, descriptor`6224=80 9C 00` | A winning result sends token9C once, then waits80 hexadecimal=128 nominal ticks. |
| `7461–7468` | Audits the count of matching players and calls766C with the full count. |
| `766C–7692` | One whole credit per matching player. Token4D is a mechanical knocker operation before each credit increment; increments RAM07 using DAA. Subsequent increments are spaced by60CE=10 hexadecimal=16 ticks. |
| `76C3–76CB` | Maximum-credit BCD adjustment018B is compared against current credits. This check occurs once before the whole batch. |
| `746B–7504` | Current-player flag clears; greatest score is found and compared with High Score to Date. Implemented by the separate high_score_to_date owner through the existing queued hook. |
| `7507–751D` | Final descriptor622C sends9B/game-over speech family and original lock-release operations23/24/25; game-over/attract state follows. |

```text
on each original foreground main-loop pass:
    phase46 = DAA(phase46 + 0x10)   # 00..90, wrap00
on final ball after extras and bonus:
    turn off Ball In Play indication
    if Function26 == 00:
        Match lamp ON
        displayed ball/match byte03 = phase46
        winners = every player's score-byte[2] equal to byte03
        if winners > 0:
            send token9C; wait128 ticks
            audit winners
            if credits < configured maximum:
                repeat winners times:
                    operate mechanical4D; increment one BCD credit
                    wait16 ticks between increments
    process High Score to Date
    run final Game Over descriptor and enter attract
```

**Match values are00,10,20,30,40,50,60,70,80,90.** Comparison is the full final
two score digits: `score % 100 == match_number`. Matching tens with a nonzero
ones digit is insufficient. All actual players are checked, including players
who are not last in rotation, and multiple winners each receive a credit.
Player scores are never modified. The modern7-digit score devices retain their
full score; comparison still uses the original final two digits.

## Randomness: exact ROM state, explicit modern timing approximation

Original RAM46 is a continuously advancing **ten-state decimal phase counter**,
not a pseudo-random generator. CPU workload, IRQ activity, switch/scoring paths,
wait loops, elapsed time and the exact sampling moment influence how many main
loops execute. The visible digits do not roll/step; the selected value appears
once. It is independent of how many players would match a candidate.

MPF does not execute the6800 foreground workload, so it cannot recover the
original cabinet's exact RAM46 phase. Production samples a lazily advanced,
monotonic elapsed-time phase at the established nominal tick resolution, across
all games/attract since initialization. It preserves the modulo10 state/range,
timing dependence and score independence; **it does not claim cycle-identical
original randomness or its workload-dependent distribution**. No generic MPF
match_percentage, forced-win/loss probability or score-derived choice is used.
`phase_source`, a callable returning original-format BCD, is the test seam.
Tests inject exact00/20/40/90 states; production never has a forced-result config.

## Physical display and lamp presentation

Existing definitions are reused:

- `credit_ball_display`: FAST number4, size6, no integrated commas.
- `l_match`: backbox-1-13, with the existing40ms incandescent-style fade.
- Four existing7-digit player displays: untouched, including installed FAST
  comma-encoding hotfix and steady score behavior.

There is one active six-cell text owner, `firepower_match`. The old normal
ball show binding in segment_display is retired; its dormant show definition
and all score bindings remain. Normal ball starts for every player and native
credit changes refresh the same display. Credits use native **whole credits**,
not raw pricing units (two quarter units buy one game here). Fractional balance
remains in native accounting; the physical two-digit credit field shows whole
credits as on the original machine.

The six-cell format is `CC BB `: credit cells0/1, separator2, ball/Match cells3/4,
trailing blank5. Normal ball text retains left alignment; Match uses two digits,
including00/90. Example1 credit, Match40: `1  40 `; maximum12, Match90: `12 90 `.
The real FAST encoder sends `PA:1C,1  40 `: Match cells are physical addresses
**1F and20**. No graphical media-controller display is involved.

Match lamp and final digits appear together at selection. There is **no rolling
animation and no arbitrary display timeout**. They remain steady through the
post-Match hook, game over and attract until a new game is accepted, service
cleanup or mode shutdown clears them. Credit changes update only the credit
field, retaining the final value. Disabled Match creates no selected value,
lamp, Match sound or credit award; ordinary credits/ball presentation remains.
ROM disabled path leaves03 as its advanced regular-ball counter (typicallyF6),
not a generated Match value; this implementation preserves the existing normal
ball display rather than inventing a disabled-Match presentation.

## Native credits integration and current start policy

The project had a credits configuration but **no registered credits mode**, so
its existing start behavior was unrestricted. Match needs a real native credit
owner. `credits` is now registered with a thin subclass of installed MPF Credits.
Its pricing, paid coin inputs, event awards, auditing, credit strings, free play,
persistence and credit-unit arithmetic remain native. Undefined `s_service_coin`
is removed as an active reference (`service_credits_switch: []`); neither paid
coin switch is substituted for it and no hardware definition is invented.

`firepower_match_credit` is a native credits event, **one whole credit**, type
match, with price-tier bonuses disabled. Match does not write credit machine
variables. Cap12 is respected for a single or multiple winner batch, including
a fractional11.5-credit boundary. The installed native `_add_credit_units` can
otherwise overwrite its cap on fractional non-purchase awards; the local subclass
bounds the amount passed into that native API. No framework patch or direct
credit-variable write is used.

**ROM distinction:** L-6 checks its maximum once before the winner batch. If
credits are11, maximum12 and four players match, the verified routine finishes
at15; if already at12 it awards none. The user explicitly requires respecting
the configured maximum, so production caps at12 instead of reproducing that
overshoot. Sound/presentation and evaluation of all winners still occur at cap.

Free play is independent of Function26. In original free play (max credits00),
Match still displays and sends9C for winners, but credits/knocker are suppressed.
Native free play disables credit-event handlers, so this implementation also
presents Match without silently accumulating hidden credits. No new mechanical
knocker output is added: the machine currently has no mapped knocker device.

**Default start policy remains unrestricted.**
`modes/credits/config/credits.yaml: unrestricted_starts: true` removes native
paid-start/player-debit gates while retaining the native ledger. This preserves
the established cabinet workflow rather than silently enabling paid starts.
The preference question about full paid-start activation was left optional;
this is the conservative default in its absence. Set that explicit setting
false only when paid-start enforcement is desired; the opt-in regression checks
native payment approval/debit. Thus the configured paid coin ledger works now,
but Match credits do not restrict purchasing/start behavior under this default.

## Sound and lifecycle ownership

The proven raw1C sound already existed in audit evidence but not production.
`match_research/verify_sound.py` byte-reproduces only this routine and promotes
`sounds/fx/l6_cmd_1c.wav` with lossless import. Pipeline:
**token9C → raw1C → FC36 (A=1B after first decrement) → F82E → FD30 → F843 VARI3**.
It is a finite2.7442055866s digital render, monoPCM16/48k, using the established
895000Hz, integrated held-DAC renderer, gain200 and center128.

WAV SHA256: `36c776536f8ad91dfa48ec2f377d231b035c74ec1cabfe6ef16300b1d02b5ba5`.
PCM SHA256: `827c5affe80c5f8dff4859a4ab08ebf458d83b98f8b4bcad31852a93a20b9828`.
No FPxx guess. No Match sound on a losing or disabled result. Raw1C has **no
speech selector**. Existing final-game9B speech still follows the game-ended
boundary; it is not Match speech. FP03/FA64/speech gains, assets, timings and
queues remain unchanged.

OriginalAudio gets a narrow post-ball ownership window on its same monophonic
GMC electronic player: new generation/start, raw1C, stop at completion/cancel.
It does not reactivate gameplay effects/score queues or another AudioStreamPlayer.
High Score qualification now stops the Match tail before its protected speech;
otherwise cleanup stops the Match stream when ending work completes.

The persistent mode holds native `game_ending`, which follows the final regular
and extra ball, normal bonus and player-turn ending. Before selection it waits
for all known balls to reach home through **one existing BallController
`collect_balls('home')` request**, with normal device routing/ejection and return
events. This meets the requested safety condition even though the original final
lock-release descriptor followed Match. No lock count, eject strength, timeout,
trough/drain definition or manual ball accounting changes. An unrecovered physical
ball prevents presentation until collected; existing service cleanup cancels the
pending ending work. New-game approval retains MPF's existing ball-home checks.

After Match, queued `firepower_high_score_check` is the integration point.
The high_score_to_date handler uses `queue.wait()` and `queue.clear()` for its
original qualifying presentation before outer game_ending releases and native
game_ended/attract occur. Nonqualifying games complete immediately. Episode tokens protect the next game from stale
queued callbacks. Service/mode cleanup cancels award timers, stops only Match
sound, releases owned queues and clears the Match lamp/value.

## Cabinet checks

1. Finish the final regular/extra ball with bonus: no Match during gameplay or
   countdown; confirm held balls return home before selection.
2. Observe a single stationary00–90 result in the physical ball/Match cells,
   steady MATCH lamp and unchanged final player scores.
3. Force/listen to a winning result:9C/VARI3, then first credit after128 nominal
   ticks (about2.124s), additional credits at16 ticks (about0.265s) per winner.
4. Check1–4 players, different/multiple winners, full and fractional credit cap,
   both paid coin inputs and free-play presentation without hidden awards.
5. Final digits/lamp persist through attract; accepting a new game clears them
   and restores normal ball text. Coin insertion changes credits only.
6. Set Function26=01: no Match value/lamp/sound/award; ordinary game over remains.
7. Service/mode shutdown during a pending award leaves no delayed credits or
   stuck Match presentation. Recheck Extra Ball, FP03, FA64 and speech ducking.
8. Confirm whether unrestricted starts should remain the cabinet policy. No new
   knocker wiring, High Score feature or unrelated hardware fix was attempted.

Physical verification is still required. No commit or push.

HSTD integration now adds original127-tick attract alternation on the highest
player's score display while retaining Match lamp/digits and credit formatting.
Its original one-check credit batch can overshoot the maximum; this does not
change Match's documented strict cap. Match's multiplayer score-preservation
test now checks displayed final scores during the attract original-score phase.

## Independent verification — October 13, 2026

The Match implementation and its 19 regressions were already present in the
working tree when this request was opened. Review rechecked the checksummed ROM
path, reran the 156 bounded probes and byte-identical raw1C render, and preserved
the existing implementation. `match_research/l6_match.dis` now retains the actual
decoded instructions for the phase increment, final-ball branch, Match, High
Score boundary, game-over transition, credit routine and descriptor interpreter.
The ROM files remain in `/tmp/firepower-audit-l6`; the listing contains no ROM
binaries. The elapsed-time phase remains an explicit approximation of original
foreground execution, and the configured credit cap and balls-home gate retain
the documented task-required differences from L-6.

Fresh validation: 69 focused machine tests passed in 73.926 seconds; the full
requested machine suite passed all 147 tests in 140.052 seconds. All six
Godot suites passed: original electronic audio, FP03, bonus/FA64, speech audio,
speech rendering and speech ducking. Successful Godot shutdowns still report
the existing ObjectDB/resource cleanup warnings. Cabinet checks above remain
pending physical verification.

## Final automated validation and files

- L-6 bounded probes: **156 cases passed**; sound reproduction: **byte-identical**
  to the proven ordinary-audit1C waveform/manifest hashes.
- Focused Match/segment-display/Extra Ball/electronic/speech machine suite:
  **69 passed**, 69.997 seconds.
- Full requested `unittest discover -s machine_tests -p '*.py'`:
  **147 passed**, 133.202 seconds.
- Godot original electronic, speech, FP03 and FA64 suites: **all passed**.
  New raw1C imported-PCM hash, finite playback and no-speech checks are included.
- Preservation audit, changed-file whitespace and `git diff --check`: **passed**.

Godot retains the known ObjectDB/resource shutdown warnings on successful exits.
Editor import also reported existing addon/socket/settings errors; the actual
new WAV imported losslessly and runtime hash assertions passed. No framework or
installed FAST encoder hotfix was edited.

Changed/added this task:

- `modes/firepower_match/config/firepower_match.yaml`,
  `modes/firepower_match/code/firepower_match.py`: L-6 Match and six-cell owner.
- `modes/credits/config/credits.yaml`, `modes/credits/code/credits_adapter.py`:
  native ledger with explicit existing-start-policy preservation and bounded
  non-purchase awards.
- `config/modes.yaml`, `config/credits.yaml`: register owners and one-credit
  Match event; disable the unresolved service-credit switch reference.
- `modes/segment_display/config/segment_display.yaml`: replace only the old
  credits/ball show binding; all score-display bindings remain.
- `modes/original_audio/code/original_audio.py`: narrow post-ball raw1C ownership
  on the existing monophonic player, with generation/cleanup handling.
- `audio/l6_effect_sources.json`, `sounds/fx/l6_cmd_1c.wav`, its `.import`: exact
  ROM VARI3 production sound.
- `machine_tests/test_firepower_match.py`: **19 new regressions**, including
  deterministic outcomes, all player counts, native ledger/caps/free-play,
  FAST payloads, bonus/extra/lock lifecycle and High Score callback ownership.
- `machine_tests/test_firepower_multiball.py`: reusable test-only physical
  plunge confirmation without scoring.
- `machine_tests/test_background_audio.py`, `test_coin_lamps.py`,
  `test_gameplay_sounds.py`, `test_player_up.py`: end-game fixtures now finish
  the simulated ball's actual plunge/drain and allow the ending lifecycle.
  These previously ended with a simulated ball still in the shooter/playfield;
  Match's required home gate exposed that inconsistency. The legacy-attract
  sound case forces a non-winning phase so its unrelated expectation is stable.
- `gmc_tests/test_original_audio.gd`: raw1C waveform/playback/no-speech checks.
- `match_research/verify_l6.py`, `l6_checks.json`, `verify_sound.py`: reusable
  checksum-based evidence and one-routine asset reproduction.
- `MATCH.md`, `audio/FIREPOWER_SOUND_MAP.md`, `audio/FIREPOWER_SPEECH_MAP.md`,
  `audio/README.md`: durable integration, constraints and validation.

All pre-existing hardware/device/coil configuration, lock accounting, scoring
rules, Extra Ball production code, 29-unit bonus cap, FP03/FA64 controllers and
assets, speech controller/DSP/ducking/model and all23 speech WAVs are unchanged
from the task baseline. No commit or push. Cabinet verification remains required.
