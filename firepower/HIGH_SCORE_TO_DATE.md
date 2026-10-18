# Firepower L-6 High Score to Date

One original machine-wide HSTD, with no initials or ranked categories. This
extends the existing Match queue hook instead of creating another game-ending
controller. Physical FAST displays and their installed comma-encoding hotfix
remain in use. MPF inspected: **0.81.0.dev4**.

## Verified source and comparison

Reused the existing game497 L-6 files at `/tmp/firepower-audit-l6`, the bounded
6800 interpreter, decoder and Sound ROM3 rendering tools. Foreground CRC32s:
`prom1_6.474 af6eb0b9`, `prom2.474 f75ade1a`, `prom3.474 242ec687`,
`gamerom.716 fdd3b983`, `green1.716 2145f8ab`, `green2.716 1c978a4a`.
Sound3 CRC32 is `55a10d13`; speech uses the unchanged checksummed model/assets.
No downloads or framework changes were necessary.

`high_score_research/l6_high_score.dis` preserves decoded instructions.
`verify_l6.py` rechecks checksums and executes 32 multiplayer/comparison/credit
cases, 100 low-byte comparisons, factory initialization, dedicated HSTD reset,
disabled behavior and four attract phases. `l6_checks.json` records results.
Probes hook physical outputs/audits and advance waits; this is bounded path
execution, not complete CPU/PIA/IRQ or cabinet emulation.

| Address | Behavior |
|---|---|
| `73CC–73E4`, `7426–7468` | Finish extras/final regular ball after bonus, then Match. |
| `746B–7472` | Clear final current-player indication; initialize highest-score selection. |
| `7479–74A9` | Compare all participating three-byte BCD scores; retain first player on an exact inter-player tie. `70–72` holds the greatest score, `73` its zero-based player, `80/81` its score-record pointer. |
| `74AB–74AF` | Set the selected player's Player Up flash bit. No score-text flashing operation. |
| `74B2–74B8` | Function13 at nonvolatile `0181/0182`: zero disables the HSTD check and attract advertisement. |
| `74BA–74DA` | Compare with current HSTD in six battery-backed nibble cells `0148–014D`. See unusual low-byte rule below. |
| `74DC–74EF` | Save the complete selected six-digit score to `0148–014D`. No intermediate per-player updates. |
| `74F2–74F5`, `[60EA]=6227` | Descriptor `F8 8F FF FF 00`: send token8F, then three248-tick waits. FF means wait only. |
| `74F8–7504` | Function25 at `0199/019A` supplies the one game's HSTD credit count; audit and call common credit routine766C. |
| `766C–7692`, `76C3–76CB` | Check maximum once, then positive mechanical token4D and one credit per increment;16 ticks between increments. |
| `7507–751D` | Final Game Over descriptor622C (`05 9B 23 24 25 00`), four5-tick steps including original lock releases, then attract. |
| `7155–7183` | If Function13 nonzero, alternate selected player's displayed score between current HSTD and saved highest game score;127 ticks per phase, lamp flag3F ON for HSTD and OFF for the game score. |
| `7AF0–7B05`, ROM `6005` | Factory initialization makes current HSTD550000, Function13=55 and Function25=03. |
| `7E36–7E49` | Original switch8 dedicated HSTD reset copies Function13 into the upper BCD byte and zeros the lower four digits. |

**The actual rule is neither ordinary `>` nor ordinary `>=`.** Greater upper
four digits qualify. If those four digits are identical, only an exactly equal
last two digits qualify. `74DA` is BNE (`26 2B`), so a differing low byte skips
the award in either direction. Thus550000 ties and qualifies;550010 does not
qualify against550000;550100 does. This oddity is verified against executable
ROM bytes and intentionally retained.

```text
after final ball, extras and bonus:
    run Match if enabled
    winner = first player with greatest six-digit final score
    best = winner.score modulo 1000000
    if Function13 != 00 and
       (best // 100 > HSTD // 100 or best == HSTD):
        HSTD = best                         # persistent, full six digits
        wait for residual Match credit timer, if any
        send 8F                             # speech, then APPEAR
        wait 248 + 248 + 248 ticks
        if current whole credits < maximum:
            award Function25 credits        # one initial cap check
            space increments by16 ticks
    final Game Over; enter attract
```

All1–4 players are evaluated **once after the whole game**. P1's provisional
score does not update HSTD before P2/P3/P4 finish. Only the greatest final score
can receive this award; multiple players exceeding the old score do not each
earn it. Tied highest players select the earliest player. The selected player
can differ from the last/current player. The modern seven-digit player scores
remain intact; HSTD comparison uses the original six-digit rollover domain.

## Persistence and adjustments

`machine_vars.firepower_high_score_to_date` is an integer, initialized to
**550000**, `persist: true`, with no expiry. MPF loads an existing persisted
value before applying the initial default. Only the final L-6 qualifying rule
changes it during gameplay. Native MPF persistence stores it alongside existing
machine variables without replacing audits or final-player-score variables.
There was no pre-existing HSTD variable or active modern high_score mode.

Mode settings expose original **Function13=55** and **Function25=03**. Function13
is the reset value in ten-thousands and00 disables the feature. Changing it does
not erase an existing HSTD; the original dedicated reset action copies it into
the record. No unverified physical reset switch, diagnostics menu or bookkeeping
UI was added. Wiring switch8 and operator adjustment/reset flows belongs to the
later diagnostics project. Cold factory initialization clears bookkeeping and
restores550000; normal power cycles retain the battery-backed record. The traced
gameplay/reset paths keep only current HSTD, not a previous-record history.

## Credits and free play

The default **three credits** are awarded once for the game's selected score,
including an exact stored-score tie. Function25=00 retains the presentation with
no credits. Native `firepower_high_score_credit` events award one whole credit
at a time with pricing-tier bonuses disabled and native credit auditing/timeouts.
No feature code writes credit machine variables.

L-6 checks the maximum **once before the batch**:11 credits with maximum12 and
award3 finishes at14; already12 receives none. `CreditsAdapter` scopes the native
per-increment cap exemption to these approved HSTD events and restores the cap
immediately after every native call. Further rejected coins/awards cannot erase
the overshoot. Match retains its previously requested strict cap12. Native paid
coin inputs, fractional ledger, free-play setting and explicit unrestricted-start
policy remain as documented in MATCH.md. There is no automatic paid-start change.

Original max00 suppresses credits/knocker while HSTD saving/presentation still
runs. Native free play has the same presentation without hidden credit additions.
The modern fractional ledger is preserved; eligibility uses its whole-credit
field as the original routine compares whole credits.

Positive token4D is a **mechanical knocker**, not a raw electronic sound or speech
command. The cabinet has no mapped knocker; none was invented. Credit digits
update through the existing six-cell Match/credits owner and retain Match digits.

## Physical display and lamps

During the new-HSTD descriptor the four player score displays stay steady with
their final scores; no new score-text animation or generic flashing is added.
The winning Player Up lamp flashes using the existing133ms half-cycle show and
40ms incandescent fade during this qualifying presentation. The High Score lamp
is not turned on during that descriptor. Match lamp/value remain owned by Match.

On entry to attract, the **selected highest player's display only** alternates:

1. Current stored HSTD, existing `l_high_score_indicator` ON.
2. That player's final game score, High Score indicator OFF.

Each phase is127 nominal ticks = about**2.107191s**. At cold startup the selected
display defaults to P1. Other score displays and all score machine variables are
untouched. Seven logical cells and existing comma formatting remain in use.
The physical credits/ball display participates only through normal credit updates;
HSTD never writes it. Match digits persist through these phases.

Accepted new-game start cancels the attract timer, restores the original display
text and releases the High Score lamp before the existing player-added immediate
`00` initialization. Gameplay Player Up remains unchanged. Service/mode shutdown
cancels waits, drops pending audio, releases the nested ending queue and removes
temporary lamp/display ownership. Service exit resumes attract advertisement.

## Speech and electronic sound

Foreground `74F2 → [60EA]=6227 → 79CB → 71CB` emits **token8F/raw0F**.
Speech selector `DF24 → DF28` says **FIRE POWER MISSION ACCOMPLISHED** in that
order, including fallthrough; it is one existing protected phrase. The unchanged
asset is `sounds/voice/l6/phrase_212a61bf57ff.wav`, duration**3.1065970675s**,
PCM SHA256`4238a244e3a23bb275ee4bd12dd802c7f278749bfc999c7016115b4b796117d5`.

Speech returns raw0F to Sound ROM3: `FC10 → FC24 → [FCD3]=F898 APPEAR → F8A2
LITEN`. Electronics follow speech, not concurrent start. The existing single
electronic player accepts an HSTD-only `after_speech` continuation; if mixer
latency leaves the protected phrase playing, it waits for actual completion.
Cancellation clears this one pending continuation. Ordinary commands, speech
latch/selector policy, phrase DSP, gains and ducking controls are unchanged.

`high_score_research/verify_sound.py` executes the verified routine with the
established reference noise seed**3C00**, rendering held DAC to monoPCM16/48kHz
at895000Hz, center128/gain200, without analog filtering. New lossless asset:
`sounds/fx/l6_cmd_0f.wav`, duration**9.1094223464s**. WAV SHA256
`7e4369769c71ec54aaf1adb27f20a5610e132596ed266760e34e1c6f6bc0cb86`;
PCM SHA256`d8bd97ee373e20148de1c89f83cbc1f1536cf54e156c5264569d9b24506a9afc`.
There is no FPxx substitution. As with the established launch render, actual
original shared noise history varies; this is exact routine execution for the
declared seed, not cycle-identical restoration of all sound-board RNG history.

Three248-tick waits total**12.3444873s** from token8F. First credit then occurs,
with additional credits16 ticks =**0.265472846s** apart. The final Game Over
descriptor waits the last credit's16-tick timer too. A preceding awarded Match
credit leaves the same16-tick timer before token8F. At cap/free play there are no
HSTD credit waits, but the full descriptor still runs. Existing game-over9B speech
and intentional periodic attract speech/FP11 follow their established owners.

## Fidelity limits and preserved scope

- Original winning Player Up flash persists into attract, including after a
  nonqualifying game. The cabinet's explicitly established attract-off Player Up
  policy is preserved: HSTD flashes it only during a qualifying ending, then
  releases it. The PlayerUp mode itself is unchanged.
- MPF nominal timers approximate IRQ ticks and foreground servicing; attract
  startup can defer1ms until the native Game object is cleared. Lamp show cadence
  retains the existing rounded133ms half-cycle and40ms fade.
- Noise uses the documented reference seed; actual sound-board shared history
  and analog output are not emulated. Whole-phrase completion gates prevent
  speech/electronic overlap despite host/mixer scheduling variation.
- The prior Match balls-home safety gate and strict credit cap remain unchanged;
  original L-6 released locks later. No locks, ball counts, coils, trough/drain
  timings, Extra Ball rules, bonus29 cap, FP03, FA64 or gameplay scoring changed.
- Final Game Over speech remains at native `game_ended`, followed by native
  attract entry. The original20-tick final descriptor's mechanical release
  choreography is not inserted into MPF; the existing balls-home safety gate
  has already collected the balls before Match. HSTD precedes this boundary.
- No operator-service UI, dedicated reset-switch mapping or knocker wiring was
  added. Modern start policy and attract FP11 remain existing project choices.

## Cabinet verification

1. Finish below HSTD: normal bonus and Match, then attract alternation on the
   highest player's display. Confirm other scores and credit/Match digits.
2. Set a known old HSTD, earn a higher single-player score: Match first; steady
   score and winning lamp flash; FIRE POWER MISSION ACCOMPLISHED, then APPEAR;
   three credits after the recovered wait; final Game Over/attract follows.
3. Test exact tie, +10-only and +100 improvements to verify the L-6 comparison
   quirk. Confirm a tie awards once and +10-only does not.
4. In multiplayer let P1 exceed the old score and P2 beat P1; only P2's greatest
   final score is saved/awarded once. Check1–4 players and tied winners.
5. At11/maximum12 confirm three HSTD credits reach14; at12 confirm none. Check
   free-play presentation without credit accumulation and unchanged Match cap.
6. Observe127-tick attract alternation and High Score lamp; Player Up lamps OFF
   in attract. Start a new game: immediate00, no lingering HSTD/Match value/lamp.
7. Reboot after saving to confirm persistence; check service cancellation before
   sound/credit timers finish, plus normal extra-ball/bonus/lock return behavior.

Physical cabinet verification remains required. No commit or push.

## Files and automated validation

- `modes/high_score_to_date/config/high_score_to_date.yaml` and
  `code/high_score_to_date.py`: persistent-mode rule, nested Match hook, nominal
  presentation/credit waits, original attract advertisement and cleanup.
- `config/config.yaml`, `config/modes.yaml`, `config/credits.yaml`: one persistent
  machine variable, mode registration and native one-credit HSTD event.
- `modes/credits/code/credits_adapter.py`: scoped original batch cap semantics
  through the native credit API; preserve an already awarded cap overshoot.
- `modes/original_speech/code/original_speech.py`,
  `modes/original_audio/code/original_audio.py`, `audio/electronic_player.gd`:
  narrow ending speech/electronic bindings and completion-gated continuation.
- `audio/l6_effect_sources.json`, `sounds/fx/l6_cmd_0f.wav`, its `.import`:
  verified APPEAR reference render and lossless source identity.
- `machine_tests/test_high_score_to_date.py`:24 deterministic new regressions,
  including real service/reset persistence, comparison quirks,1–4 players,
  cap/free-play awards, speech/sound timing, Match/bonus/extras ordering,
  attract cadence, physical FAST credit positions and new-game cleanup.
- `machine_tests/test_firepower_match.py`: one existing multiplayer assertion
  now checks preserved final scores during attract's original-score phase.
- `gmc_tests/test_high_score_audio.gd`: actual existing players, unchanged phrase
  PCM/word sequence, continuation ordering, APPEAR PCM/finite playback, pending
  cancellation and generation cleanup. Existing audio regressions are unchanged.
- `high_score_research/verify_l6.py`, `l6_checks.json`, `l6_high_score.dis`,
  `verify_sound.py`: executable ROM evidence and reusable sound reproduction.
- `HIGH_SCORE_TO_DATE.md`, `MATCH.md`, `audio/FIREPOWER_SPEECH_MAP.md`,
  `audio/FIREPOWER_SOUND_MAP.md`, `audio/README.md`: current integration and limits.

The combined focused HSTD/Match/segment/Extra Ball suite passed **60 tests** in
66.698 seconds. All **seven Godot suites passed**: HSTD, original electronic,
FP03, FA64 bonus, speech audio, speech rendering and speech ducking. The known
ObjectDB/resource shutdown warnings remain on successful exits. Editor import
reported existing addon/socket/settings errors, but the new WAV imported
losslessly and the actual runtime PCM hash passed. No installed framework or
FAST segmented-display hotfix was edited.

Full requested `unittest discover -s machine_tests -p '*.py'`: **171 tests passed**
in209.153 seconds. `git diff --check`: **passed**. The HSTD132 comparison/credit
probes plus factory/reset/disabled/attract cases, all156 existing Match ROM cases,
and the byte-identical APPEAR reference render passed. No commit or push.
