# Firepower L-6 speech restoration

Williams Firepower, game497. Foreground bytes establish speech requests; speech
firmware establishes vocabulary, ordering, timing and selector state. This report
supersedes the earlier sound audit's provisional speech rows, particularly game
start, delayed POWER and the multiball prelude. Ordinary electronics, launch,
FP03, FA64, rules, lamps, devices and release choreography are preserved.

## Reused sources and permission preflight

Reused `/tmp/firepower-audit-l6/`, `/tmp/firepower-audit-l6.dis`, the bounded6800
interpreter and cached MAME cycle/disassembly sources, and WiLL-i-ROMS
`Talk/FirepowerSpeech6.asm` / `Pinball Sound ROMS/Sound ROM 3.asm`. Verified bytes
override transcription errors in the annotated speech listing. The existing
manual cache is image-only; its empty text extraction cannot prove factory defaults.

| Speech ROM | CPU range | CRC32 | SHA-1 |
| --- | --- | --- | --- |
| v_ic7.532 | B000-BFFF | 94c5c0a7 | ff7c618d1666c1d5c3319fdd72c1af2846659290 |
| v_ic5.532 | C000-CFFF | 1737fdd2 | 6307e0ae715e97294ee8aaaeb2e2bebb0cb590c2 |
| v_ic6.532 | D000-DFFF | e56f7aa2 | cb922c3f4d91285dda4ccae880c2d798a82fd51b |

Foreground CRCs: prom1_6.474 af6eb0b9, prom2.474 f75ade1a, prom3.474 242ec687,
gamerom.716 fdd3b983, green1.716 2145f8ab, green2.716 1c978a4a. Sound3.716 is
55a10d13. These are the previously checksum-verified L-6 files, not another revision.

No ROM or recorded audio download was needed. The missing HC55516 decoder source
was fetched once, with upfront approval, from
[MAME](https://raw.githubusercontent.com/mamedev/mame/master/src/devices/sound/hc55516.cpp).
Its SHA256 is in `speech_model.json`; the decoder translation's credits/license
are in `speech_research/MAME_DECODER_LICENSE.txt`.
[MAME's System6 implementation](https://raw.githubusercontent.com/mamedev/mame/master/src/mame/shared/williamssound.cpp)
confirms the shared6802, separate DAC/CVSD outputs and CA2 digit/CB2 clock wiring.
Godot import/test access was approved during preflight. No dependency installation
or MPF/GMC framework edit was required. Installed MPF:0.81.0.dev4; Godot:4.6.2.

## Pre-edit MPF inventory

The actual release show was connected, unlike AGENTS.md's historical description.
This table records the implementation before this pass, not original Williams behavior.

| MPF event | Condition | Current voice file(s) | Sequence/timing | Bus | Assessment |
| --- | --- | --- | --- | --- | --- |
| mode_attract_started | every attract entry | fire_power.wav | immediate | sequential voice | guessed phrase/cadence |
| play_fire_sound | release show | fire.wav | absolute0 seconds | voice | partial |
| play_one_sound | release show | one.wav | +0.250s, absolute0.250 | voice | partial, before FIRE recording ends |
| play_two_sound | release show | two.wav | +0.800s, absolute1.050 | voice | partial |
| play_three_sound | release show | three.wav | +0.800s, absolute1.850 | voice | partial |
| mltp_lanes_done | FIRE completed | none | no mapping | — | missing |
| circle_target_group_hit_complete | POWER completed | none | no mapping | — | missing |
| collect_* / light_outlane_specials | FIREPOWER progression | none | no mapping | — | missing |
| fire_qualifier_lit_complete | six center arrows | none | no mapping | — | missing |
| collect_special | qualified outlane | none | no mapping | — | missing |
| accepted start, tilt, game end | lifecycle | none | no mapping | — | missing |
| high score, extra ball | no configured awarding owner | none | no mapping | — | missing integration |
| accomplished/destroyed/enemy/mission/power/you_are | no active reference | corresponding WAVs | unused vocabulary | — | unused |

All eleven WAVs under `sounds/voice/` and legacy MP3 counterparts under
`modes/sounds/` were inventoried. No additional active speech mapping was found.
The empty ball-start voice show and unused `play_power_target_sound` do not play
voice. Attract's FP11 effects playback is preserved.

## Complete original foreground speech matrix

Addresses/tokens are hexadecimal. Electronics below are evidence, not new playback
mappings. Queued requests remain subject to original foreground gates/replacement.

| Event | Condition | Foreground path | Token / raw | Complete speech | Electronic sound |
| --- | --- | --- | --- | --- | --- |
| Accepted first player/game | credits/player acceptance succeeds | 633F→7571→75B9→[60E0]=64C8→79CB | 9F /1F | FIRE POWER | VARI1F continuation |
| Added second/third/fourth player | accepted, RAM56=1/2/3 | 75C7 indexed60E0→64CB/621E/6221 | 84/99/9D | none | GW04 / VARI19 / VARI1D |
| FIRE completion | all four flags; no qualification inhibition | 6873, slot8 of608D | 8D /0D | FIRE | GW0D, deferred score0B |
| POWER immediate completion | all three flags | 6E53→6E95 | 97 /17 | none immediately | LITE |
| POWER cleanup | flag4A timer expires; RAM70=0 | 6E9E→77A8;6212=4A406F28→6F35→effect19 | 9A /1A | POWER | VARI1A after speech |
| FIRE+POWER progression | both RAM10 bits0C; RAM15 awards0/1/3/7 | 68FA→6C9F→6CAC→effect1D; descriptors6269-626C | 9E /1E | FIRE POWER | LITE, then VARI1E |
| Six center arrows | bank/memory checks pass, all six RAM73 flags | 6974→69B2→69DE→69EC | 8E /0E | delay0040, ENEMY DESTROYED | consumed into00; qualification GW06 elsewhere |
| Extra-ball/mission qualification | odd target parameter8D; RAM14 bit80; RAM18 bit08 clear | 6EAF→6ECB→72C1 | 88 /08 | YOU, ONE, ONE, MISSION | consumed00, then queued GW04 |
| Collected Special | side qualifier2F/30 and RAM18 bit10 | 6EDB→6F02→effectEC | 8C /0C | MISSION ACCOMPLISHED | GW0C, score0B, original configured knocker |
| Multiball last prelude frame | nine-frame counter reaches11 | 6B6C→6BA3→6BD5 | 98 /18 | stateful, normally FIRE ONE | returns TURBO14; demo83 follows |
| Three release cycles | third ball retained | 6BF9 /6BFE /6C0F | 98 /18,97,94 | stateful counting, detailed below | TURBO14, LITE17, mechanical25/24/23 |
| True tilt | threshold reached, first execution of path | 7993/79A3→6D55→6D58 | 87 /07 | YOU ARE DESTROYED | BGEND, remapped tilt01 |
| Qualifying high score | end-game comparison qualifies | 74DC→74F2→[60EA]=6227→79CB | 8F /0F | FIRE POWER MISSION ACCOMPLISHED | APPEAR0F |
| Game over | after end-game/high-score/match processing | 7507→[60EC]=622C→79CB | 9B /1B | one of16 selector slots | GW1B |
| Periodic attract | RAM78 bit01;01AB bit0; final lamp scan; counter>3C; rotating94=0 | 6494→6499-64C5 | 9B /1B | same random table | original1B/1C/1D rotation |

Corrections to prior reports: `60E0` points to `64C8`, so accepted first-player
start speaks FIRE POWER. Token99 belongs to the third-player descriptor. Existing
electronic start/add-player behavior is intentionally preserved under this task's
scope. POWER comes from delayed callback **6F28**, not directly from shield
cleanup6F1F. The normal multiball prelude contains nine frames and one speech
request, rather than an optional guessed flourish. Bounded probes are recorded
in `speech_research/foreground_checks.json`.

Reachability coverage included executable immediate callers, effect table608D-60AC,
indirect descriptors60D8-60EC, transition/timer tables61F4-621E, switch dispatch
60F1 onward, and the full multiball prelude/release loop. Every selected command
has a normal foreground caller. DDF1/DF4C's diagnostic full-vocabulary path is
excluded from normal gameplay production.

## Canonical speech commands and every original phrase

Entry DDF6 is reached through DFFD with speech enabled and a valid ROM signature.
The existing research clock3579545/4 Hz is reused; MAME's nominal3580000 oscillator
differs by0.013%. No existing electronic renderer was retuned.

| Raw | Table | Exact word order | Electronic return / state | Duration seconds |
| --- | --- | --- | --- | --- |
| 07 | DF1A | YOU, ARE, DESTROYED | 01; reset02 | 1.943496 |
| 08 | DF3A | YOU, ONE, ONE, MISSION | 00; reset02 | 3.006271 |
| 0C | DF28 | MISSION, ACCOMPLISHED | 0C; reset02 | 1.781670 |
| 0D | DF2E | FIRE | 0D; reset02 | 0.661980 |
| 0E | DEFC | delay0040, ENEMY, DESTROYED | 00; reset02 | 1.738181 |
| 0F | DF24→DF28 | FIRE, POWER, MISSION, ACCOMPLISHED | 0F; reset02 | 3.106597 |
| 18,02=0 | DF04 | FIRE, ONE | 14;02 becomes1 | 1.410850 |
| 18,02=1 | DF0E | TWO | 14;02 becomes2 | 0.705535 |
| 18,02≥2 | DF14 | THREE | 14;02 becomes0 | 0.738160 |
| 1A | DF34 | POWER | 1A; reset02 | 0.661956 |
| 1B | DFDA, indexed by09&0F | random table below | 1B; reset02 | variable |
| 1E | DF5A | FIRE, POWER | 1E; reset02 | 1.325053 |
| 1F | DF5A | FIRE, POWER | 1F; reset02 | 1.325044 |

Raw00-06,09-0B,10-17,19,1C,1D have **no speech selector**, and preserve02.
ONE is a homophone of WON: raw08 repeats exactly the B7A0-BBEF range twice.
“You won one mission” is a plausible transcript, not a separately encoded WON
word. No invented YOU ARE ACCOMPLISHED phrase was added.

| Selector09 low nibble | Table | Complete order, including fallthrough | Duration seconds |
| --- | --- | --- | --- |
| 0 | DF52→DF5A | YOU, DESTROYED, FIRE, POWER | 2.985898 |
| 1 | DF60 | ENEMY, DESTROYED, YOU | 2.367539 |
| 2 | DF6A | MISSION, TWO, ONE, THREE, ACCOMPLISHED | 3.972591 |
| 3,F | DF80 | YOU, ARE, ENEMY | 1.682688 |
| 4,C | DF8A→DF8E | ENEMY, FIRE, DESTROYED, YOU | 3.028112 |
| 5 | DF9C | MISSION, DESTROYED, YOU | 2.474977 |
| 6 | DFAA | ENEMY, POWER, ONE | 2.117514 |
| 7,D | DFB4 | YOU, DESTROYED, ENEMY, MISSION | 3.180301 |
| 8 | DFC6→DFD0 | YOU, ONE, delay0040, FIRE, POWER, DESTROYED | 3.799910 |
| 9,A | DFD0 | FIRE, POWER, DESTROYED | 2.291444 |
| B,E | DF8E | FIRE, DESTROYED, YOU | 2.322788 |

Eleven distinct random phrases occupy sixteen slots with original duplicate
weighting. Their unusual grammar is retained. Sound IRQ increments09 before
selection; labels alone would miss the fallthrough words.

## Vocabulary and intra-phrase timing

| Word | ROM range |
| --- | --- |
| FIRE | B000-B3CF |
| POWER | B3D0-B79F |
| ONE/WON | B7A0-BBEF |
| TWO | BBF0-BFFF |
| THREE | C000-C43F |
| ENEMY | C440-C84F |
| DESTROYED | C850-CDDF |
| MISSION | CDE0-D28F |
| ACCOMPLISHED | D290-D81F |
| YOU | D820-DC1F |
| ARE | DC20-DDBF |

These are vocabulary ranges, not eleven independent foreground commands.
Contiguous ranges chain FIRE POWER, YOU ARE, ENEMY DESTROYED and MISSION
ACCOMPLISHED without resetting the decoder. DEAF-DEF4 skips the leadingAA marker,
shifts data through CA2 and clocks CB2. End-pointer comparisons follow executable
firmware, including its exclusive endpoint, not a WAV-name interpretation.
DEF6 executes its fixed94h decrement loop64 times for delay0040: about65 ms,
not64 MPF ticks. Decoder state persists through the whole phrase and explicit gaps.

`speech_model.json` records exact cycle offsets for every word, return cycle,
PIA-edge hash, PCM/WAV hashes and asset paths. Raw0E ENEMY begins at58532 and
DESTROYED at690825 cycles. Raw18 state0 FIRE begins at215 and ONE at592488:
ONE starts0.662081913 s after the request. These are ROM data-read boundaries;
encoded leading quiet remains part of the word. Whole-phrase PCM preserves these
boundaries to one48kHz frame and avoids recording-padding or GMC word-FIFO timing.

Combined68FA passes `2*(RAM15&7)+3` to6C9F. The first decrement is immediate;
remaining decrements each wait10 ticks. Award0/1/3/7 gives20/40/80/160 ticks to
the end request:0.331841/0.663682/1.327364/2.654728 s. Original queue replacement
and timer contention can change delivery. Modern speech uses these nominal
presentation ends without changing the existing1.12-second lamp show. POWER's
64-tick cleanup is suppressed while this recovered presentation proxy is busy;
after a shorter combined award ends, POWER can still be requested at cleanup.

## Multiball requests, audible words and original eject relationship

Trace starts at6BA3, after initial lock/accounting/setup waits. Nine frames count
AA-11 down to11; each waits12h+06h=24 ticks. Only the last frame requests98,
then demo83. Each subsequent release cycle requests98 then97, waits28h=40 ticks,
issues mechanical25/24/23 and94, then waits `(8+7+6+5+4)+(3+5+7+9+11)=65`
more ticks. Release-request spacing is105 ticks, rather than the old show's800 ms.

| Action | Nominal ticks from prelude start | Seconds |
| --- | ---: | ---: |
| Last prelude98, normally FIRE ONE | 192 | 3.185674 |
| First release98 then97 | 233 | 3.865948 |
| First eject25 then94 | 273 | 4.529630 |
| Second release98 then97 | 338 | 5.608114 |
| Second eject24 then94 | 378 | 6.271796 |
| Third release98 then97 | 443 | 7.350279 |
| Third eject23 then94 | 483 | 8.013962 |

These sums exclude execution/IRQ, initial accounting and mechanical arbitration
latencies. They are not oscilloscope measurements or the current MPF coil timings.

Normal speech masks IRQ. With02 initially0, FIRE ONE lasts1.410850 s. The first
release98 arrives41 ticks(0.680274 s) into that protected phrase;97 overwrites the
pending input and94 at81 ticks overwrites it again. Thus first-release98 normally
**does not execute as another counted phrase**. The next98 at146 ticks selects
TWO and the next at251 ticks selects THREE. Relative to the first spoken request:
FIRE starts approximately0, ONE0.662082, TWO2.422690, THREE4.164868 s. First eject
occurs during ONE; second near the end of TWO; third near the end of THREE.

Production reproduces nine prelude notifications, four98 requests, and97/94
inputs to the **speech latch only**. No additional electronic playback or coil
request is emitted. `multiball_firepower_started` anchors the nominal prelude;
speech begins at192 ticks. The old release show/physical MPF releases are unchanged,
and its old word events no longer have sound_player handlers. Synchronizing ejects
or restoring banner/display/lamp choreography remains a separate task.

## Attract, lifecycle and confirmed no-speech events

Original6499 requires attract mode, RAM01AB bit0(attract-sound adjustment), and
RAM47=ROM60F2=29h, the final lamp frame. Packed counter017D/E increments at this
opportunity, emits when greater than3Ch and resets:62 opportunities from zero.
RAM94 rotates1/2/0, requesting9C/9D/9B; only9B speaks, using the random table.
7130 reloads a6-tick frame timer; frames1 through29h normally repeat. Nominal
rotation is62*41*6 ticks=253.061991 s; speech every third rotation is759.185973 s.
Initial scan/selector phase and other presentation/IRQ work affect wall-clock timing.

Periodic attract speech is temporarily disabled by setting
`mode_settings.attract_speech: false` in
`modes/original_speech/config/original_speech.yaml`. To re-enable it,
change that setting to `attract_speech: true`; the existing timing and 1C/1D/1B
rotation remain intact. This switch is independent of gameplay. True was the
previous project default, not a proved factory default. A named timer approximates
eligible scan cycles.
No unconditional FIRE POWER plays on attract entry. Existing FP11 effects playback
is preserved, although it is not the original rotating electronic attract pattern.
Accepted start cancels attract playback/timer. Gameplay speech cannot leak into
attract. Game-over speech remains independent of the attract-speech adjustment.

| Event | Original speech finding |
| --- | --- |
| Ball start, launch, ordinary drain, end-ball bonus | none |
| First/second lock capture, unqualified hole | none |
| Partial center bank | none independently; all-six branch speaks |
| Lock qualification | ENEMY DESTROYED on established all-six branch |
| Added player | none |
| Replay/credit | none dedicated; positive4D knocker |
| Match | none;9C electronic only |
| Tilt warning, slam tilt | none dedicated; true tilt has07 |
| Special merely lit | combined FIRE POWER, not collected-Special phrase |
| High score | proven0F phrase; modern qualifying owner absent |
| Extra ball | conditional08 qualification, not every extra-ball counter change/ball start |

## Asset verification and recovery

`speech_research/existing_assets.json` preserves hashes, format, duration, RMS,
peaks and active boundaries for all eleven originals. They are mono16-bit22,050 Hz;
RMS10432-15535 PCM units spans about3.46 dB. Most have25.9-30.6 ms leading quiet
and trailing recording padding. `asset_comparison.json` records comparisons to
ROM-derived word spectra at8kHz. Most matching labels lead their spectral rankings,
but ENEMY/THREE/TWO are close and THREE marginally ranks behind TWO. Spectrum
alone cannot certify pronunciation/source identity. Existing YOU ARE lasts1.282132 s
versus a0.97709 s firmware range; FIRE POWER1.467120 s versus about1.325 s.
Concatenation would add padding/gain inconsistencies and lose decoder continuity.

| Class | Result |
| --- | --- |
| A, verified existing waveform | none promoted from filename/spectrum alone |
| B, confidently identified correction | none; originals were not trimmed/normalized |
| C, authentic complete phrase/timing missing |23 ROM-derived WAVs in sounds/voice/l6 |
| D, recording identity/trim/gain unresolved | all eleven existing WAVs retained byte-for-byte |

The23 assets cover nine fixed commands, three counting states and eleven unique
random phrases. Separate1E/1F FIRE POWER assets retain their small entry-timing
difference. ROM bytes execute in the reused bounded6800 interpreter; the HC55516
integer model processes both clock edges. Held output is integrated into48kHz
mono16-bit PCM. No imitation voice, guessed word speed or per-word normalization
was used. Lossless imports disable trim/normalize/compression; pitch_scale=1 and
the dedicated player's restoration-time gain was-3 dB. Current centralized
speech gain/dynamics are documented in [SPEECH_BALANCE.md](SPEECH_BALANCE.md).
Original WAVs and MP3s are untouched.

## Production mapping and architecture

| Feature | MPF event | Asset/sequence | Confidence / limit |
| --- | --- | --- | --- |
| Accepted game | game_started |1F FIRE POWER | proven indirect descriptor and semantic boundary |
| FIRE | mltp_lanes_done |0D FIRE | proven completion; nominal delivery |
| POWER | circle_target_group_hit_complete |64-tick cleanup1A, presentation gate | proven callback; queue approximated |
| Combined awards | collect_firepower_bonus_10000/30000/50000, light_outlane_specials |20/40/80/160 ticks then1E | proven count; current rules reused |
| Center completion | fire_qualifier_lit_complete |0E with pre-delay | proven all-six branch; current memory rules preserved |
| Special | collect_special |0C MISSION ACCOMPLISHED | proven collection, no raw duplicate |
| Multiball | multiball_firepower_started | prelude + release raw-input timeline | proven nominal waits/latch; coils preserved |
| Tilt | tilt | cancel futures,07 | true-tilt boundary |
| Game over | game_ended | random1B | proven phrase family; modern end boundary |
| Attract | mode_attract_started/stopped and timer |1C/1D/1B rotation | condition/counter proven, scan proxy |
| High score | no configured owner |0F asset ready, unwired | original proven; modern qualification unresolved |
| Extra ball | no configured owner |08 asset ready, unwired | original conditional path proven; modern equivalent unresolved |

Persistent machine-wide `original_speech` sends only local `firepower_speech` BCP
requests. `speech_player.gd` has its own AudioStreamPlayer on voice. It observes
the existing `firepower_electronic_command` event without changing, delaying or
duplicating electronic playback. Whole phrases guarantee word ordering and timing.

The daughterboard has a separate analog path but shares the sound CPU. IRQFBBF
resets the stack, acknowledges input and masks IRQ. Normal speech does not CLI
untilDE8A after the phrase. Incoming requests update one PIA input: latest wins,
not a FIFO of phrases. Raw1B executes CLI atDE5C **before** speaking, so ordinary
or speech requests can interrupt it. After speech, the common code optionally
waits2EE0 iterations before electronics; raw14 skips that gap. Those shared-CPU
electronic latencies are not imposed on the preserved modern electronic player.

The local owner reproduces protected phrases, one pending raw input including
non-speech, selector advancement on execution, and interruptible1B. Duplicate/stale
BCP serials/generations are rejected. Speech cannot overlap itself and does not
mask/stop/restart electronic, FP03 or FA64 players. Godot tests exercise actual
natural completion, latest-input overwrite, ordinary-input state preservation,
random interruption and independent playback.

Ball-will-end cancels feature timers/voice before bonus. Accepted start clears
attract/game-over voice. Tilt cancels future awards/counts before its own phrase.
Multiball end cancels current/pending release speech and future notifications,
preserving unrelated voice. Game end clears gameplay and requests random speech.
Service/mode teardown/shutdown, BCP reset/disconnect stop playback. Sync sends a
fresh generation without replaying old phrases. Lifecycle cleanup overrides normal
phrase protection to prevent orphaned voice.

## Unresolved integrations and fidelity compromises

High-score and extra-ball assets are decoded, but current rules have no qualifying
owner matching the original condition. No generic score, player-extra_balls, raw
POWER hit or ball-start trigger was invented. Original speech-disabled returns are
documented; this pass does not introduce new electronic remapping for a speech-off
cabinet setting.

The semantic producer is not a foreground/PIA emulator. Nominal deadlines exclude
execution/IRQ latency, effect-queue replacement, shared timer contention and banner
work. Modern physical releases remain unchanged. Current gameplay can replace a
pending speech request, particularly after the shorter modern release show ends.
Random selection counts observed/accepted modern requests, not all original
background commands; vocabulary/slot weights match, but exact historical random
sequence does not. Attract uses a time proxy and known startup selector, rather
than saved RAM94/scan phase. Factory adjustment default remains unverified.

Digital CVSD bits, clock cadence, fallthrough and intra-phrase continuity are
recovered. Cabinet amplifier/filter/speaker response and acoustic balance need
physical verification. Decoder initialization resets per modern whole phrase;
original analog state can persist between commands. Cross-phrase history, idle DC
hold/AC coupling and audible reset transients are not emulated. Hash verification
proves this explicit digital model, not recording-perfect acoustic fidelity.

## Cabinet checklist

| Setup | Expected speech | Original accompanying electronics / preserved implementation |
| --- | --- | --- |
| Accepted first-player Start; separately press without acceptance | FIRE POWER only on acceptance | original VARI1F; current start cue retained |
| Four FIRE lanes, then repeat lit lane | FIRE once; none on repeat | original GW0D; current score/electronics preserved |
| POWER completed with FIRE incomplete | POWER after about1.062 s, no immediate word | original LITE then VARI1A; current electronics preserved |
| Both features at10K/30K/50K/Special-light | FIRE POWER after nominal0.332/0.664/1.327/2.655 s; cleanup POWER only once presentation has ended | original LITE/VARI1E; lamp show unchanged |
| One center bank, then all six | no bank-only voice; ENEMY DESTROYED with about65 ms pre-delay | original qualification GW06 / consumed0E |
| First/second qualified lock | no capture speech | existing03/replacement behavior |
| Third lock starts multiball; allow full sequence | FIRE ONE about3.186 s, TWO5.608 s, THREE7.350 s; no repeated FIRE before numbers | original demo03/LITE17/TURBO14; only speech notifications added; actual ejects unchanged |
| End multiball/game/service during counts | no orphaned later counts | current electronic/lifecycle behavior |
| Light Special, collect qualified outlane, repeat outlane | FIRE POWER when lit; MISSION ACCOMPLISHED once when collected | original GW0C/score/knocker; rules unchanged |
| True tilt versus warning | YOU ARE DESTROYED only on tilt | electronic tilt preserved |
| Game over | one original random template, possibly odd grammar | original GW1B; current attract FP11 retained |
| Attract setting true, then false | no immediate FIRE POWER; random voice nominally every12.65 min; false disables periodic voice | FP11 unchanged; no gameplay switch leakage |
| Gameplay switches in attract | no gameplay speech | existing electronic ownership |
| Future high-score implementation | FIRE POWER MISSION ACCOMPLISHED, currently unwired | original APPEAR0F |
| Future extra-ball/mission implementation | YOU/ONE/ONE/MISSION on recovered condition, currently unwired | original consumed08 then GW04 |
| Speech alongside spinner/launch and at bonus boundary | independent voice; electronic identity/timing intact; cleanup at boundary | monophonic electronics, FP03/FA64 preserved |

## Files and validation

Added `modes/original_speech/`, `audio/speech_player.gd`, `audio/speech_model.json`,
23 phrase WAVs/import settings, `machine_tests/test_original_speech.py`,
`gmc_tests/test_speech_audio.gd`, and `audio/speech_research/` scripts/evidence.
Updated local server/mode registration and removed old voice-only sound_player
bindings. Existing sound tests inspect the new BCP boundary. README and the sound
map link here. No release show, hardware/rule config, ordinary controller or
existing sound asset was edited by this pass. No commit or push.

From `firepower/`:

```sh
python3 audio/speech_research/render_speech.py --verify
python3 audio/speech_research/verify_foreground.py
/home/murray/mpf-venv/bin/python -m unittest machine_tests.test_original_speech machine_tests.test_original_audio machine_tests.test_gameplay_sounds
/home/murray/mpf-venv/bin/python -m unittest discover -s machine_tests -p '*.py'
godot --headless --path . --script res://gmc_tests/test_speech_audio.gd
godot --headless --path . --script res://gmc_tests/test_original_audio.gd
godot --headless --path . --script res://gmc_tests/test_fp03.gd
godot --headless --path . --script res://gmc_tests/test_bonus_audio.gd
git diff --check
```

Research requires reused `/tmp` ROM/interpreter/MAME caches; production does not.
`render_speech.py --verify` leaves assets unchanged. Foreground probes inject
elapsed descriptor waits and sum explicit waits; they do not emulate IRQ/electrical
or mechanical latency.

Final results:

- Firmware/PCM verification: **49 selector executions passed**, covering all32
  raw commands, all three18 states and all sixteen1B slots; all23 production
  waveform/PCM hashes matched. All eleven legacy voice PCM hashes stayed unchanged.
- Foreground probes: accepted/added-player descriptors,64-tick POWER callback and
  RAM70 suppression, all nine prelude frames, four98 requests and three original
  eject positions matched the documented nominal trace.
- Focused speech/electronic/gameplay MPF tests: **35 passed**,33.929 s; the dedicated
  speech module contains14 semantic tests.
- Full requested machine discovery: **117 passed**,95.958 s.
- Godot speech, restored electronics, FP03 and FA64 bonus tests: **all exit0**.
  Lossless PCM/import hashes, native timing, natural queue completion, latest-input
  overwrite, selector preservation, recovered multiball audible sequence,
  interruption, independent playback and reset/disconnect cleanup passed.
- `git diff --check`: passed. No commit or push.

The previously known GMC editor SVG import errors remain unrelated; runtime test
scripts load successfully. Godot tests retain existing shutdown ObjectDB/resource
warnings. No speech assertion or runtime parse error remains. Cabinet/acoustic
verification and the documented high-score/extra-ball integrations remain open.

## Extra Ball rule integration — 2026-10-11

The previously unwired raw08/DF3A phrase is now requested by successful native
`firepower_center` Extra Ball collection through `firepower_extra_ball_collected`.
It retains the literal encoded YOU, ONE, ONE, MISSION sequence (YOU WON ONE
MISSION), whole-phrase PCM, protected PIA latch, presence/ducking and cleanup.
It is not triggered by generic player-extra_balls changes or extra-ball serves.
See [EXTRA_BALL.md](../EXTRA_BALL.md) for L-6 qualification, collection, tilt,
lamps, once-per-physical-ball latches, pending two-ball limit and test results.
The high-score integration remains unwired; no Match work was performed.

## Match boundary — 2026-10-11

Original Match raw1C has no speech selector. The new end-of-game Match holds
`game_ending` through its credit work and the queued future High Score hook.
Existing game-over raw1B speech remains at `game_ended`, after those stages;
it is not Match speech. No speech PCM, word ordering, protected-latch policy,
DSP/ducking or attract cadence changed. See [MATCH.md](../MATCH.md).

## High Score to Date integration — October 13, 2026

The original `74F2 → [60EA]=6227 → 79CB` token8F now runs from the existing
post-Match queued check. Its actual L-6 comparison includes exact ties and the
unusual low-byte BNE rule; see [HIGH_SCORE_TO_DATE.md](../HIGH_SCORE_TO_DATE.md).
One selected highest final score across1–4 players requests existing raw0F:
`DF24 → DF28`, **FIRE POWER MISSION ACCOMPLISHED**. The complete protected phrase,
PCM, speech selector/latch architecture, DSP and ducking controls remain unchanged.
APPEAR electronics follow actual phrase completion using a single continuation
on the existing electronic player. Game-over raw1B follows the HSTD descriptor
and credits; no modern callout, ranking or initials flow is introduced.
