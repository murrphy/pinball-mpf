# Firepower L-6 Extra Ball — Function 34 = 12

The production choice is the instruction-booklet setting **12**: attract sounds
ON, Extra Ball qualifies when FIRE advances the multiplier to 5X. Attract speech
is already enabled in `original_speech`; its conditions/timing are unchanged.
`extra_ball_feature` explicitly selects 12. This task implements no Match,
drain/trough changes, alternative award sources or ball-number manipulation.

## ROM evidence and the meaning of the two-ball limit

Reused the checksum-verified local L-6 ROM set and bounded 6800 interpreter.
`extra_ball_research/verify_l6.py` validates foreground CRCs, executes lighting,
collection, cleanup, normal/tilted state copies, first-scoring lamps and pending
ball limits. `l6_checks.json` preserves assertions/results and the loaded
foreground-region SHA256. Raw ROMs stay in `/tmp/firepower-audit-l6`; interpreter
and cached opcode/cycle sources are the existing sound-audit tools. No downloads
or emulator/framework modifications were needed. Installed MPF source used for
accounting is `/home/murray/mpf/mpf/devices/extra_ball.py` and its Game loop.

**Important distinction:** L-6 does not allow repeated center-target Extra Balls
on one physical ball. Its qualification latch is set on first lighting, and its
collection latch permits one center award. The documented two-Extra-Ball limit
is implemented in ROM as a clamp of **pending awards**, not a numeric count of
center-target awards earned on that physical ball. A second/third center award
on the same physical ball is therefore prevented by the latches, not enabled
by leaving the arrow on. Other original award paths are not added here.

Production additionally guards earned-this-physical-ball at two and pending
native awards at two, so it cannot create an unretainable third native award.
With this feature's actual qualification latch, at most one center-target award
is reachable on a physical ball. This does not claim a two-hit center-target
rule unsupported by the verified bytes. Native MPF pending awards are consumed
at extra-ball serve; the ROM consumes them at first eligible scoring instead.
The separate presentation latch preserves the original Shoot Again indication.

| Address / path | Exact behavior |
|---|---|
| `6873–6892` | FIRE switch handler checks all four FIRE bits and normal inhibition. |
| `68A4–68BA` | `01AC & 0F`: zero disables EB; `RAM18 & 80` inhibits repeat qualification. Odd selection requires `RAM14 & 40` (already 5X); even selection also accepts `RAM14 & 20` (prior 4X). |
| `68BC–68C3` | Sets flag27 (`RAM14 bit80`, EB arrow) and flag47 (`RAM18 bit80`, qualified once). Lighting happens in this same completion handler; no later target/foreground event is required. |
| switch table `6191–6194` | Original switch40 = center POWER, handler6E53, parameters FC/09. Top/bottom switches39/41 use FB/08 and FD/0A. Only center parameter09 is odd. |
| `6E53–6EAC` | Normal POWER hit scoring, target state and bank completion are processed before EB tests; collection does not bypass them. |
| `6EAF–6EBE` | Requires odd target parameter, arrow flag27 on and collected flag43 (`RAM18 bit08`) clear. |
| `6EC0–6EC9` | Effect FB queues table608D indexB/token84; saves FA cleanup, overrides repeat count57 to23. |
| `6ECB–6ECD` | Sends token88/raw08 to sound board: DF3A YOU, ONE/WON, ONE, MISSION. |
| `6ED0–6ED5` | Sets collected flag43, then72C1 sets pending-award bit08 in RAM78. Arrow flag27 remains on here. |
| `76F1–772C` | Foreground housekeeping converts pending bit08 into increment5B; pending5B invokes7925 to light Shoot Again. |
| `62E7–62FC`, `780E–7875` | Saved FA operation toggles flag27 off when the 23-step effect presentation completes or is replaced. `6053=27` is the FA flag lookup. |
| `6E25–6E2B` | At ball end, caps pending5B at two. This is not an incrementing per-physical-ball qualification counter. |
| `7306–7328`, `7520–755F` | Normal and tilt ball-end state copies clear arrow/qualification/collection bits for the next physical ball. Normal memory mask607B retains only low bits of RAM14 and bit0 of RAM18. Tilt copies6069 defaults. |
| `73CC–73EE` | Pending5B skips player and regular ball advancement, including after tilt. Awarded extras survive tilt; lit uncollected EB does not. |
| `7925–792C` | Sets logical flag00 (playfield Shoot Again) and flag3E (backbox indication) together while extras are pending. |
| `76F1–7730` | First eligible scoring with RAM78 bit80 clear consumes an extra; clears both flags if no extras remain, otherwise lights both again. |

Relevant pseudocode, omitting unrelated FIRE/POWER work:

```text
on FIRE completion:
    if adjustment_low != 0 and not qualified_once:
        if prior_5X or (adjustment_low even and prior_4X):
            extra_ball_arrow = ON
            qualified_once = true
on POWER target:
    normal scoring / target / bank logic
    if target_parameter odd and arrow_ON and not collected:
        queue token84, repeat23, saved_cleanup=FA
        request token88 (YOU WON ONE MISSION)
        collected = true
        pending_award_bit = true
foreground housekeeping:
    pending_award_bit -> pending_extra_balls += 1
    if pending_extra_balls: both Shoot Again indications ON
presentation end/replacement:
    FA toggles arrow OFF
ball end (normal or tilt):
    pending_extra_balls = min(pending_extra_balls, 2)
    clear per-physical-ball EB flags
    if pending_extra_balls: same player, same regular ball number
first scoring of served extra:
    pending_extra_balls -= 1
    if none remain: both Shoot Again indications OFF
```

## Existing device inventory and implementation

No duplicate physical definitions were created:

| Purpose | Existing object / number |
|---|---|
| Center POWER target | `s_power_2`, playfield2-18 |
| Extra Ball When Lit arrow | `l_extra_ball_arrow`, playfield-3-6 |
| Playfield Same Player Shoots Again | `l_fire_again`, playfield-2-18 |
| Two backbox Shoot Again lamps | `l_fire_again_1`, backbox-1-11; `l_fire_again_2`, backbox-1-12 |
| FIRE completions | `mltp_lanes_done(count)`, existing lane-change counter |
| Multiplier | Existing `bonus_multiplier` and 2X–5X lamps, untouched |
| Extra Ball accounting | New native mode device `firepower_center`, unlimited per-game count; guarded qualifications/awards |

The ball-owned feature starts on ball_starting and stops on ball_ended/game_ended.
Its four player variables hold lit, qualified, collected and earned-this-ball
state; all reset each physical ball, including awarded extras and turn changes.
MPF's native device awards increment `player.extra_balls`, post native award
events and retain the Game loop's same-player/same-ball-number behavior. No
hand-written serve requests, ball-number changes or lock replacement accounting.
Existing bonus collection holds ball_ending until its countdown completes.

At collection the center target still scores its normal 1000. Existing POWER
bank/FIREPOWER awards can also score on that hit (the tested third-target case
adds7000 bank +10000 current FIREPOWER award). EB itself adds no score, clears no
POWER/FIRE progress and writes no multiplier/bonus/lock memory. Once the sound
presentation finishes, another FIRE completion cannot relight EB on the same
physical ball. A fresh physical extra or regular ball can qualify afresh.

All three Shoot Again lamps turn on together as soon as a valid award is processed,
remain on through bonus and extra serve, and go off together on first scoring if
no further awards are pending. Their outputs use the existing 40ms fade. The
playfield/backbox indications have no separate invented timing. Teardown removes
only this feature's light-stack entries. Other lamp shows remain untouched.

## Electronic sound and speech

`original_speech` observes the feature's successful-collection event and requests
raw08 on the independent protected speech path. Existing ROM-derived phrase PCM,
word order, one-PIA-latch sequencing, ducking/presence DSP and cleanup are unchanged.
The phrase's existing literal encoded words are YOU, ONE, ONE, MISSION, pronounced
YOU WON ONE MISSION; no new WON sample or per-word concatenation is introduced.

`original_audio` uses its existing effect queue/monophonic electronic player for
**23 token84/raw04 requests, separated by 10 nominal ticks**. The nominal complete
presentation is23*10*16*928*4/3579545 =3.816 seconds before queue cleanup, subject
to existing gates, pending waits and replacement. Successful speech request is
posted before the electronic presentation. Saved-FA cleanup is represented by a
semantic completion event, also sent on queue replacement or audio mode stop.
No legacy FP04 guess is used.

Raw04 executes Sound ROM3 FC1B (A=03 after first decrement) → FA88 → vectorFE76
→ FAEE. `verify_sound.py` reproduces only this routine with the existing
895000Hz/integrated48k PCM16 renderer and DAC gain200/center128. Newly promoted
`sounds/fx/l6_cmd_04.wav` has SHA256
`41654ec327c8d3041f842c891f5f73b8280d48688535f681a5b78441edb7837d`;
PCM SHA256 `ddd3c4e4be5835855f6c8a0bf07cfac522fc6efabce869e79246568d89c489c9`.
The complete uninterrupted routine lasts14.099324s; each normal award request
interrupts it at the existing10-tick cadence. The next ordinary score/effect
retains normal interruption rights. Import trim/normalization/compression are off.
Existing foreground gates and independent DAC/CVSD playback are modern presentation
approximations, not a new sound-board CPU/IRQ emulator. FP03, FA64, speech assets
and unrelated electronic sounds are unchanged.

## Tilt and physical verification limits

Lit-but-uncollected EB is lost on tilt; successful native awards remain pending.
A tilted awarded extra ends normally without advancing player/regular ball if
another award is pending, otherwise the ordinary next turn/ball follows. Per-ball
qualification latches reset on every physical ball, including extras.

**The current machine defines neither a native tilt mode nor a physical tilt
switch.** This predates the feature. Tests exercise its existing public tilt event
and MPF Game.tilted boundary, clearing that boundary for the next simulated ball.
No switch/wiring or broader tilt/bonus subsystem was invented here. Thus these
results establish EB behavior at the logical tilt boundary, not physical tilt
recognition or a complete native tilt subsystem.

Cabinet checklist:

1. Complete FIRE through2X/3X/4X: arrow remains off; advance to5X: arrow lights.
2. Top/bottom POWER hits do not collect; middle hit awards exactly one extra,
   scores normally, speaks YOU WON ONE MISSION and plays the raw04 presentation.
3. Arrow stays lit during presentation, then clears; repeat middle hits and FIRE
   completions cannot earn another center EB on that physical ball.
4. All three Shoot Again lamps illuminate together, stay through bonus/extra
   serve, then clear together on first scoring. Listen for clear ducked speech.
5. Drain with bonus: full normal countdown completes before same player shoots
   the extra at the same regular ball number. Fresh extra can reach5X/qualify again.
6. Check two/four players: 5X/lit/collected/awards/counters do not leak to others;
   lock replacements do not reset the feature as a new physical player ball.
7. Once physical tilt integration exists, check lit-uncollected loss, awarded
   extra survival and tilted-extra consumption using the existing tilt boundary.
8. Check drain/game-end/service cleanup, FP03 return, FA64 cadence and29-unit cap.

No commit or push. Automated results and changed-file inventory follow below.

## Automated results and changed files

- Bounded checksum-verified L-6 lighting/collection/cleanup/tilt/lamp/limit probes:
  passed; `extra_ball_research/l6_checks.json` contains23 cases.
- Focused new-EB/original-electronic/speech/background/bonus/gameplay machine
  suite: **77 passed**, 79.910 seconds (11 new Extra Ball regressions).
- Full `unittest discover -s machine_tests -p '*.py'`: **128 passed**,
  118.919 seconds.
- Godot original-electronic, speech, FP03 and FA64 suites: **all passed**.
  Original-electronic checks the new raw04 WAV/imported PCM identity,
  independent award speech, retrigger and ordinary scoring interruption.
- `git diff --check`, scoped whitespace and preservation hash audit: **passed**.

Known successful-exit Godot ObjectDB/resource warnings remain; editor import
also reported its existing socket/settings warnings. The new WAV imported
losslessly and runtime hash assertions passed. No framework changes were made.

Changed/added this task:

- `config/modes.yaml`: register the ball-owned feature.
- `modes/extra_ball_feature/config/extra_ball_feature.yaml` and
  `code/extra_ball_feature.py`: native Extra Ball device, ROM latches and lamps.
- `modes/original_speech/code/original_speech.py`: successful-collection raw08.
- `modes/original_audio/code/original_audio.py`: raw04 queue and arrow cleanup.
- `audio/l6_effect_sources.json`, `sounds/fx/l6_cmd_04.wav` and its lossless
  `.import`: exact new electronic source.
- `machine_tests/test_extra_ball_feature.py`: deterministic machine regressions.
- `gmc_tests/test_original_audio.gd`: new electronic/speech integration checks.
- `extra_ball_research/verify_l6.py`, `l6_checks.json`, `verify_sound.py`: bounded
  evidence and reproducible narrow sound recovery.
- `EXTRA_BALL.md`, `audio/FIREPOWER_SPEECH_MAP.md` and
  `audio/FIREPOWER_SOUND_MAP.md`: durable rule/evidence and integration links.

Drain/trough definitions, coils, physical switches/lights, multiplier lamps,
existing FIRE/POWER rules, bonus29 cap, FP03/FA64 controllers/assets and all23
speech WAVs remain byte-identical to the task baseline. Physical cabinet
verification remains required. No commit/push.
