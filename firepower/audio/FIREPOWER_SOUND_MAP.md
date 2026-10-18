# Firepower sound audit — 2026-10-08 / validated 2026-10-09

The subsequent dedicated [speech restoration](FIREPOWER_SPEECH_MAP.md) supersedes
this report's provisional speech/integration rows. Its indirect-descriptor probes
correct accepted first-player start to token9F (FIRE POWER), establish delayed
POWER through timer callback6F28, and recover all four multiball98 requests,
including the prelude and protected-IRQ input overwrite. The electronic behavior
documented below was preserved during that speech pass.

## Baseline inventory (captured before production edits)

| MPF event / switch | Condition | Current sound | Track/bus | Source file |
|---|---|---|---|---|
| mode_attract_started | unconditional within owner context | fire_power | voice | config/sounds.yaml |
| mode_attract_started | unconditional within owner context | FP11 | effects | config/sounds.yaml |
| s_start_button_active | unconditional within owner context | fire_power | effects | config/sounds.yaml |
| play_fire_sound | unconditional within owner context | fire | voice | config/sounds.yaml |
| play_one_sound | unconditional within owner context | one | voice | config/sounds.yaml |
| play_two_sound | unconditional within owner context | two | voice | config/sounds.yaml |
| play_three_sound | unconditional within owner context | three | voice | config/sounds.yaml |
| fire_lane_group_hit_complete | unconditional within owner context | FP15 | effects | modes/base/config/base.yaml |
| s_lane_f_active | unconditional within owner context | FP13 | effects | modes/base/config/base.yaml |
| s_lane_i_active | unconditional within owner context | FP13 | effects | modes/base/config/base.yaml |
| s_lane_r_active | unconditional within owner context | FP13 | effects | modes/base/config/base.yaml |
| s_lane_e_active | unconditional within owner context | FP13 | effects | modes/base/config/base.yaml |
| sw_pop_bumpers_active | unconditional within owner context | FP13 | effects | modes/base/config/base.yaml |
| s_spinner_active | unconditional within owner context | FP09 | effects | modes/base/config/base.yaml |
| s_plunger_inactive | unconditional within owner context | FP12 | effects | modes/base/config/base.yaml |
| sw_side_bumper_active | unconditional within owner context | side_bumpers | effects | modes/base/config/base.yaml |
| sw_fire_arrow_active | unconditional within owner context | fire_targets | effects | modes/base/config/base.yaml |
| sw_power_arrow_active | unconditional within owner context | power_target | effects | modes/base/config/base.yaml |
| ball_starting / firepower_background | background enabled; stage 1–36 | FP03.wav / fp03_player.gd | music | modes/background_audio/code/background_audio.py |
| start_bonus_collect / counted step | non-tilted bonus collection, 0–29 units × 1–5 | FA64 renderer / bonus_player.gd | effects | modes/bonus_collect/code/bonus_collect.py |

No `track_player` mappings or explicit YAML sound definitions were found in the active configuration. GMC discovers WAV assets by basename in `sounds/`. Legacy MP3s in `modes/sounds/` are retained candidates, not evidence of active playback.

Baseline bus configuration: music solo; effects simultaneous (3 voices); voice sequential. FP03 and FA64 use dedicated players.

Switch tag bindings: `pop_bumpers` → FP13; `side_bumper` → side_bumpers; `fire_arrow` → fire_targets. The base binding uses `power_arrow`, but POWER switches carry `power_target`; `play_power_target_sound` also has no playback handler. POWER audio is therefore absent through both paths.

Multiball release show posts fire/one/two/three at 0/0.6/1.05/1.85 s. Attract intentionally plays fire_power and FP11; Start plays fire_power on effects. Return lanes, outlanes, stars, top target, actual locks, awards, extra ball, special, replay, game over, match and high score have no direct sound mappings. Some can incidentally trigger other mapped events.

The tables below separate a proven original command from a proven modern integration. An unresolved original presentation is not proof of silence.


## Sources and reproducibility

Revision: **Firepower L-6, game 497**, original ROMs checksum-verified against the earlier investigations. Existing durable documents, FA64 state hashes, FP03 reconstruction and local sound assets were reused. A search of `/tmp` and `/home/murray` did not find the earlier ROM/disassembly/tool caches. Consequently a replacement L-6 archive, annotated Sound ROM 3/speech listings, MAME opcode/cycle references and the manual were downloaded; this was necessary recovery, not a second broad bonus/background investigation.

| Image | Load address | CRC32 | SHA1 |
|---|---:|---|---|
| prom1_6.474 | 6000 | af6eb0b9 | 28f8366737e09ffd60cb5ea55a5734143cdb9663 |
| prom2.474 | 6200 | f75ade1a | a5572c5c721dbcb82988b709f4ef2119118e37c2 |
| prom3.474 | 6400 | 242ec687 | c3366c898a66c78034687e6a6000193d52be4141 |
| gamerom.716 | 6800 | fdd3b983 | fb5d1eb01589311cf4b2ef16e25db03d40bca2f7 |
| green1.716 | 7000 | 2145f8ab | ddf63208559a3a08d4e88327c55426b0eed27654 |
| green2.716 | 7800 | 1c978a4a | 1959184764643d58f1740c54bb74c2aad7d667d2 |
| sound3.716 | F800 | 55a10d13 | 521d4cdfb0ed8178b3594cedceae93b772a951a4 |
| v_ic5.532 | C000 | 1737fdd2 | 6307e0ae715e97294ee8aaaeb2e2bebb0cb590c2 |
| v_ic6.532 | D000 | e56f7aa2 | cb922c3f4d91285dda4ccae880c2d798a82fd51b |
| v_ic7.532 | B000 | 94c5c0a7 | ff7c618d1666c1d5c3319fdd72c1af2846659290 |

Source references: [annotated listings](https://codeberg.org/kaputnikGo/WiLL-i-ROMS), [L-6 archive reference](https://www.planetemu.net/rom/mame-roms/frpwr-l6), [MAME System 6 foreground hardware](https://github.com/mamedev/mame/blob/master/src/mame/pinball/s6.cpp), [MAME Williams sound hardware](https://github.com/mamedev/mame/blob/master/src/mame/shared/williamssound.cpp), [6800 decoder](https://github.com/mamedev/mame/blob/master/src/devices/cpu/m6800/6800dasm.cpp), [instruction cycles](https://github.com/mamedev/mame/blob/master/src/devices/cpu/m6800/m6800.cpp), [Firepower manual, switch chart page 10](https://www.pinrepair.com/sys37/manuals/wms6-firepower.pdf). The annotated listings contain transcription errors; addresses and selector data below were checked against bytes, rather than trusting comments.

Recovered archive `/tmp/firepower-audit-frpwr_l6.zip`; extracted images `/tmp/firepower-audit-l6`; annotated repository `/tmp/firepower-sound-audit-will-i-roms`. Temporary disassembly `/tmp/firepower-audit-l6.dis` stays outside source control. Ignored `audio/diagnostics/sound_audit/` contains switch dispatch, bounded foreground probes, conditional probes, reference renders, DAC checks and asset fingerprints. `tools/` there preserves the audit scripts. Their absolute cache paths must be updated if caches move. They are analysis aids, not a universal emulator.

The 6800 runner reproduces **all 147 previously established FA64 state hashes** (including terminal empty state). Its sound timestamps are instruction-end DAC writes. Foreground probes hook scoring/output and stop at accounting/main-loop boundaries; they do not emulate the complete machine. Static branch tracing supplies queue counts, conditions and silent-score behavior that the hooked probe alone cannot prove.

## Number spaces and foreground scheduling

At **71CB**, a byte with bit 7 set goes to the sound output: `token & 0x1f` is the raw command. Positive bytes instead operate solenoids/flashers. Thus `3E` is a flasher operation, `4D` the replay knocker and `23/24/25` release coils; none is an electronic command. `9E` is the sound token for raw `1E`. Other helpers also consume flag/eject bytes; a high bit outside this traced output path does not by itself prove a sound.

**79E4/7A00** consume score descriptors, not sound tokens. For example descriptor `92` at a repeated center target schedules nine 100-point score sounds; it is **not** spinner command `92`. Score table **608D** supplies token/delay pairs. Bit 08 selects immediate versus counted scoring; main loop **70CF** services queued effects before counted scores. Effect helper **77F0** uses the low nibble as table index and high nibble as repetition count, with explicit overrides for certain completions.

| Index | Token | Raw | Delay ticks | Meaning |
|---:|---:|---:|---:|---|
| 0 | 89 | 09 | 32 | new FIRE lane |
| 1 | 85 | 05 | 5 | tens score |
| 2 | 8A | 0A | 4 | hundreds score |
| 3 | 8B | 0B | 2 | thousands score |
| 4 | 80 | 00 | 0 | silent / resume |
| 5 | 83 | 03 | 96 | actual lock |
| 6 | 82 | 02 | 5 | POWER ordinary effect |
| 7 | 86 | 06 | 8 | qualification effect |
| 8 | 8D | 0D | 128 | FIRE completion |
| 9 | 9A | 1A | 128 | POWER speech/VARI |
| A | 97 | 17 | 8 | LITE |
| B | 84 | 04 | 10 | extra-ball sequence |
| C | 8C | 0C | 7 | special |
| D | 9E | 1E | 176 | Firepower completion |
| E | 97 | 17 | 6 | LITE progression |
| F | 90 | 10 | 5 | new center target |

Gate **62D3** requires RAM70 zero and RAM3A below 16 ticks (or current token 89); **62CF** uses 32 ticks. Original tick is approximately `16 * 928 * 4 / 3579545` seconds. Flag helper **7953** is zero-based: RAM `10 + id//8`, mask `1 << (id%8)`.

## Original event matrix

All values are hexadecimal unless a repetition count is explicitly decimal. `GW(n)` means loader FA88 → wave routine FAEE, vector FE68 + 7*(n−2). Speech column describes the speech-enabled board; electronics may be remapped after speaking. The routine table below includes speech-disabled differences.

| Event / foreground path | Condition | Token | Raw | Electronic routine | Speech |
|---|---|---:|---:|---|---|
| Jets 6A26 | unlit, gate open | 8A | 0A | GW(0A), immediate | none |
| Jets 6A26 | lit, gate open | 8A | 0A | same, immediate 1,000 score | none |
| Jets 6A26 | gate blocked | 8A | 0A | deferred 1 pulse unlit / 10 lit | none |
| Spinner 68D3 | unlit | 8A | 0A | immediate or deferred by gate | none |
| Spinner 68D3 | lit, 32-tick gate open | 92 then 8B | 12 then 0B | SP1 FA3C → VARI F843; deferred score | none |
| Spinner 68D3 | lit, gate blocked | 8B | 0B | score remains; SP1 suppressed | none |
| FIRE 6873 | previously unlit, ordinary | 89 then 8B | 09 then 0B | GW(09), deferred score | none |
| FIRE 6873 | already lit / qualification suppressed by RAM19 bit10 | 8B | 0B | GW(0B) | none |
| FIRE completion 6873 | all four flags set | 8D replaces 89; then 8B | 0D then 0B | GW(0D), score follows presentation | Fire |
| Center target 642A → 6974 | new target | 90 ×10, then 8B | 10 then 0B | KNOCK F981, GW(0B) | none |
| Center target 6974 | repeated target | 8A ×10 | 0A | first immediate if gate permits; remainder deferred | none |
| Center bank completion 69B2/69DE | bank/memory/qualification branches | 86; possibly 8E | 06; 0E | GW(06), repetition override 22 decimal; speech may replace electronic 0E | Enemy Destroyed on explicit 8E path 69EC |
| POWER 6E53 | not inhibited by flag4D, no duplicate pending target | 82 ×10 then 8B | 02 then 0B | GW(02), GW(0B) | none |
| POWER completion 6E53 | all three flags set | 97 replaces ordinary effect | 17 | LITE F890 ×10; additional silent score descriptor14 | none for 17 |
| POWER/extra-ball qualification 6EAF–6ECD | feature/award tests pass | 88, queued84 | 08, 04 | speech consumes08; GW(04) count override23 decimal | literal sequence at DF3A, below |
| FIRE + POWER 68FA → 6C9F | both feature flags; RAM15 award bits | 97, then 9E | 17, then 1E | LITE; VARI5 F843 after speech | Fire Power |
| Firepower 10K/30K/50K/Special progression | score descriptors 5B/1C/3C/5C from6269–626C; count `2*(RAM15&7)+3` | 97, then9E | 17,1E | as preceding row; alternates mechanical3E | Fire Power |
| Special outlane 6EDB | RAM18 bit10 and side flag2F/30 | 8C, plus ordinary8B score | 0C,0B | GW(0C) after speech; counted score | Mission Accomplished |
| Extra ball 72C1 | qualification/award conditions | part of88/84 presentation | 08/04 | as above; no invented extra standalone cue | DF3A |
| Left shield/outlane 6EDB | shield flag01, clear71; release path | possible9A in cleanup6F1F/6F25 | 1A | VARI1 F843 after speech | Power |
| Outlanes 6EDB | ordinary | 8B | 0B | GW(0B) | none |
| Return lanes 7230 | unlit / lit descriptor | 8B ×1 / ×3 | 0B | GW(0B); lit feature consumed | none |
| Slings 7230 | ordinary descriptor11 | 85 | 05 | GW(05) once | none |
| Side standups 7230 | descriptor51 | 85 ×5 | 05 | GW(05) | none |
| Top-center target / original hole rollovers 7230 | descriptor13 | 8B | 0B | GW(0B), also bonus advance | none |
| Hole 7062 → 6AF0/6383 | unqualified, stable occupancy | 8B | 0B | GW(0B); E9/EA/EB are mechanical | none |
| Actual lock 6B26 | qualified first/second capture | 83 | 03 | GW(03), 96-tick presentation; silent score1C | none |
| Third capture 6B6C | third retained ball | sequence below | — | silent score4C; release presentation | see98 |
| Multiball release 6BD5/6BF9/6BFE/6C0F | optional prelude plus three release cycles | 98,97,94 (demo83) | 18,17,14 (03) | speech18 → TURBO14; LITE17; TURBO14 | Fire One / Two / Three, stateful |
| Lock qualification | center-completion branch, not every hole closure | 86 / 8E conditional | 06 /0E | qualification paths above | conditional Enemy Destroyed |
| Shooter46 / lane-change45 | raw switch dispatch only | none directly | — | handlers bypass sound; shooter departure is detected by periodic 6D88 path below | none |
| Shooter departure 7062 → 6CDC → 6D40/624C → 6494 → 6D46 → 6D88–6DB4 | RAM78 bits01/02 clear; RAM015A bit01 set; RAM26 bit20 clear; RAM0157 low nibble zero | 94 | 14 | FC24 → vector FCDD → F8D1 TURBO → F8E0 NOISE | none |
| Drain9, 6CDC/63AB | detection and eject retry | none dedicated | — | positive20 outhole coil | none |
| Stable ball end 6DE9 → 6E42 | all ball accounting satisfied, queued effects finish | 93 then96 | 13 then16 | BGEND FA0D, existing FA64 bonus | none |
| Ball start6800 | background adjustment35 enabled | 91 | 11 | existing BG1 F9C0/F9D3 | none |
| New accepted game633F →75B9 | credits/player tests pass, descriptor621E | 99 | 19 | VARI0 F843, FD15 | none |
| Added player75C7 | accepted player addition, descriptor6221 | 9D | 1D | VARI4 F843, FD39 | none |
| Plumb warning6274 →7993 | below tilt threshold | no dedicated warning | — | may update background | none |
| Tilt7993/79A3 →6D55 | threshold reached | 81;93,87,81 | 01;13,07→01,01 | tilt FC64, BGEND | You Are Destroyed |
| Slam626F | reset path | 93 | 13 | BGEND then reset7000 | none |
| Replay/credit7679 | award | **4D positive** | — | mechanical knocker only | none dedicated |
| Match7426–7468 | enabled, matching digit, descriptor6224 | 9C | 1C | VARI3 F843, FD30; credit knocker | none |
| High score74DC–7504 | qualifying score, descriptor6227 | 8F | 0F | APPEAR F898 after speech | Fire Power Mission Accomplished |
| Game over7507 | descriptor622C | 9B | 1B | VARI2 F843, FD27; positive23/24/25 releases | random template DFDA |

The award descriptors prove the common sequence and bit-dependent repetition, but do not alone establish a one-to-one translation between every modern award variable and original RAM15. No scoring or award-state rules were changed to force that correspondence.

## Complete physical switch dispatch

Dispatcher **7112** indexes `60F1 + 4*switch`, loading the word handler and two parameter bytes. These bytes are parameters, not necessarily sound tokens. The switch names use the original manual; current star-rollover physical identities have not been established.

| Original switch | Physical identity | Handler | Parameters |
|---:|---|---:|---|
| 1 | Plumb bob | 6274 | 00 00 |
| 2 | Ball roll tilt | 79A3 | 00 00 |
| 3 | Start | 633F | 00 00 |
| 4 | Left coin | 7606 | 00 00 |
| 5 | Center coin | 7602 | 00 00 |
| 6 | Right coin | 75FE | 00 00 |
| 7 | Slam tilt | 626F | 00 00 |
| 8 | High-score reset | 7E36 | 00 00 |
| 9 | Outhole | 7062 | 00 00 |
| 10 | Left outlane | 6EDB | F8 2F |
| 11 | Left return | 7230 | 61 DE |
| 12 | Left sling | 7230 | 61 E5 |
| 13 | Left lock | 7062 | 00 00 |
| 14 | Upper middle left standup | 7230 | 61 E8 |
| 15 | Spinner | 68D3 | 00 00 |
| 16 | Top left standup | 7230 | 61 E8 |
| 17 | Arrow1 | 642A | 00 02 |
| 18 | Arrow2 | 642A | 00 04 |
| 19 | Arrow3 | 642A | 00 08 |
| 20 | Unused bank1 completion | 6462 | 0E 31 |
| 21 | Arrow4 | 642A | 00 10 |
| 22 | Arrow5 | 642A | 00 20 |
| 23 | Arrow6 | 642A | 00 40 |
| 24 | Unused bank2 completion | 6467 | 70 32 |
| 25 | Jet bottom left | 6A26 | 00 2E |
| 26 | Jet top left | 6A26 | 00 2B |
| 27 | Jet top right | 6A26 | 00 2C |
| 28 | Jet bottom right | 6A26 | 00 2D |
| 29 | Top center target | 7230 | 61 F1 |
| 30 | Right lock | 7062 | 00 00 |
| 31 | Upper top right standup | 7230 | 61 E8 |
| 32 | F | 6873 | 43 04 |
| 33 | I | 6873 | 33 05 |
| 34 | R | 6873 | 23 06 |
| 35 | E | 6873 | 13 07 |
| 36 | Top lock | 7062 | 00 00 |
| 37 | Lower top right standup | 7230 | 61 E8 |
| 38 | Middle right standup | 7230 | 61 E8 |
| 39 | POWER top | 6E53 | FB 08 |
| 40 | POWER middle | 6E53 | FC 09 |
| 41 | POWER bottom | 6E53 | FD 0A |
| 42 | Right sling | 7230 | 61 E5 |
| 43 | Right return | 7230 | 61 DE |
| 44 | Right outlane | 6EF0 | F9 30 |
| 45 | Lane change | 63D9 | 00 00 |
| 46 | Shooter | 7062 | 00 00 |
| 47 | Playfield tilt | 79A3 | 00 00 |
| 48 | Lower right standup | 7230 | 61 E8 |
| 49 | Center middle left standup | 7230 | 61 E8 |
| 50 | Lower middle left standup | 7230 | 61 E8 |
| 51 | Left ramp | 7062 | 00 00 |
| 52 | Unused | 7230 | 61 E8 |
| 53 | Left lock rollover | 7230 | 61 F1 |
| 54 | Right lock rollover | 7230 | 61 F1 |
| 55 | Unused | 7230 | 61 E8 |
| 56 | Unused | 7062 | 00 00 |
| 57 | Right ramp | 7062 | 00 00 |
| 58 | Center ramp | 7062 | 00 00 |

Coin/service/reset/ramp/unused dispatch entries do not imply a new electronic switch cue. The event matrix covers their lifecycle effects where applicable.

## Sound ROM dispatch and routine behavior

IRQ **FBE2** first handles speech when enabled, then electronic dispatch **FC10**. Raw0 returns/resumes; raw1 is tilt. For raw2–0E, FC1B receives A=raw−1 and performs another decrement before vector selection. Archive recording numbers were never used as command IDs.

| Token(s) | Raw command | Entry / vector | Synthesis and state | Classification / disposition |
|---|---|---|---|---|
| 80 | 00 | FC10 → return | no one-shot; resume retained background flags | preserved |
| 81 / speech87 | 01 /07→01 | FC64 | tilt control, persistent behavior | E modern lifecycle integration; no guessed sample |
| 82–8E | 02–0E | FA88 → FAEE; FE68 +7*(raw−2) | parameterized digital wave/envelope; deterministic finite one-shot, no arbitrary pitch scaling | C for isolated electronic routine; coupled completion/speech integration E where noted |
| 8F | 0F | F898 APPEAR | noise, shared HI/LO RNG; speech precedes | E |
| 90 | 10 | F981 KNOCK | fixed finite DAC pattern | C implemented |
| 91 | 11 | F9C0 →F9D3 BG1 | persistent stage modifier/resuming background | established D, preserved FP03 |
| 92 | 12 | FA3C SP1 →F843 | persistent SP1 stage, repeating VARI | D implemented |
| 93 | 13 | FA0D BGEND | clears04/05 background flags; does not clear06 SP1 state | lifecycle preserved; no sample |
| 94 / speech98 | 14 /18→14 | FC24 → FCDD → F8D1 TURBO → F8E0 NOISE | finite one-shot, noise depends on shared RNG/history | C fixed-seed launch render; release integration remains E |
| 95 | 15 | FA14 →FA27 BG2 | persistent secondary background modifier | original path known; modern integration E |
| 96 | 16 | FA64 BON2 | finite persistent bonus progression | established D, unchanged |
| 97 | 17 | F890 LITE | noise depends on shared RNG/history | E |
| 98 without speech | 18 | FA76 BON1 | persistent bonus-style state | E; speech-enabled board instead selects14 |
| 99–9F | 19–1F | F82E VARILD →F843; FD15 +9*(raw−19) | parameterized finite VARI; some commands invoke speech before it | C isolated routine; 19/1D implemented; other event integration E |

All raw2–0E isolated wave routines were executed and reference-rendered. Production uses 02/03/05/09/0A/0B plus10/19/1D. Long source WAV durations are **not** presentation durations: foreground command repetition and interruption truncate them, as the original board does. Production duration/hash details are in `l6_effect_sources.json`; PCM is mono16 at 48 kHz, 895 kHz CPU clock, held DAC integrated per frame, center128, gain200, no analog filter. WAV imports explicitly disable Godot lossy compression. No new proven A match was accepted among the old electronic sample candidates. The established FP03/FA64 source evidence remains valid.

SP1 increments on an accepted lit-spinner command, wraps31→1, persists across balls/games and repeats until interrupted. All31 independent derived state models match CPU DAC hashes, every DAC timestamp and return cycle; `spinner_model.json` stores these identities. `spinner_renderer.gd` generates these states from the ROM timing model rather than a pitched WAV bank. Native loop rounding is bounded by one 48 kHz frame.

IRQ resets the sound stack and interrupts the current DAC routine. Finite effects return through FC3E and resume retained background flags. IRQ clears bonus B2 flag07 except raw16, bonus B1 flag08 except raw18; BGEND does not reset SP1 flag06. Noise shares RNG with background resumptions, so a fixed noise recording or arbitrary RNG seed would not reproduce the complete path.


### Isolated wave parameters and envelopes

The seven-byte vector supplies the original wave/envelope parameters, rather than a hand-selected pitch. Durations include loader and routine return, exclude speech and IRQ, and describe uninterrupted diagnostic playback; repeated foreground commands commonly truncate these envelopes. Exact DAC/PCM hashes remain in the render manifests.

| Raw | Vector | Seven parameter bytes | Duration s | DAC writes | Production |
|---:|---:|---|---:|---:|---|
| 02 | FE68 | 14 10 00 01 00 01 6A | 7.616820 | 7936 | C rendered WAV |
| 03 | FE6F | 81 27 00 00 00 16 54 | 1.219909 | 2816 | C rendered WAV |
| 04 | FE76 | 12 09 1A FF 00 27 91 | 14.099324 | 81936 | E event integration; diagnostic only |
| 05 | FE7D | 11 09 11 01 0F 01 6A | 0.168672 | 1080 | C rendered WAV |
| 06 | FE84 | 11 32 00 01 00 0D 1B | 24.194057 | 26064 | E event integration; diagnostic only |
| 07 | FE8B | 14 11 00 00 00 0E 0D | 0.150646 | 448 | E event integration; diagnostic only |
| 08 | FE92 | F4 13 00 00 00 14 6A | 5.257853 | 19200 | E event integration; diagnostic only |
| 09 | FE99 | 41 49 00 00 00 0F 7E | 0.601282 | 4320 | C rendered WAV |
| 0A | FEA0 | 21 39 11 FF 00 0D 1B | 1.085200 | 10080 | C rendered WAV |
| 0B | FEA7 | 42 46 00 00 00 0E 28 | 0.862332 | 1792 | C rendered WAV |
| 0C | FEAE | 15 00 00 FD 00 01 8C | 0.227556 | 880 | E event integration; diagnostic only |
| 0D | FEB5 | F1 18 00 00 00 0E 28 | 1.621283 | 3360 | E event integration; diagnostic only |
| 0E | FEBC | 31 12 00 01 00 03 8D | 17.117978 | 17832 | E event integration; diagnostic only |

### VARI parameter identities

VARILD selects nine bytes. The isolated continuation was additionally rendered for19/1A/1B/1C/1D;1E exceeded the bounded four-million-instruction diagnostic limit, and1F was not run after that failure. This does not establish a new production asset for those E integrations. There is no validated isolated1E duration/hash here.

| Raw | Vector | Nine parameter bytes | Isolated duration s / limit |
|---:|---:|---|---|
| 19 | FD15 | 40 01 00 10 E1 00 80 FF FF | 1.876308 |
| 1A | FD1E | 20 01 00 08 E1 00 80 FF FF | 1.881087 |
| 1B | FD27 | 28 01 00 08 81 02 00 FF FF | 5.318264 |
| 1C | FD30 | 00 FF 08 FF 68 04 80 00 FF | 2.744206 |
| 1D | FD39 | 28 81 00 FC 01 02 00 FC FF | 2.640879 |
| 1E | FD42 | 01 01 00 08 81 02 00 01 FF | bounded limit |
| 1F | FD4B | 01 08 00 01 20 01 00 01 FF | not executed |

## Complete speech selector matrix

Speech IRQ **DDF6** sees the low-five-bit command. Word identities use the verified ROM address vocabulary: Fire B000–B3CF, Power B3D0–B79F, One B7A0–BBEF, Two BBF0–BFFF, Three C000–C43F, Enemy C440–C84F, Destroyed C850–CDDF, Mission CDE0–D28F, Accomplished D290–D81F, You D820–DC1F, Are DC20–DDBF. Combined ranges concatenate words. Exact original CVSD identity of the project's WAV speech recordings was **not** proven.

| Raw input / token | Speech table | Literal ROM word sequence | Electronic continuation | Foreground condition |
|---|---|---|---|---|
| 07 /87 | DF1A | You Are Destroyed | 01 tilt | tilt |
| 08 /88 | DF3A | You / One / One / Mission | 00 | extra-ball/mission branch; do not normalize this into an assumed transcript |
| 0C /8C | DF28 | Mission Accomplished | 0C | qualified special outlane |
| 0D /8D | DF2E | Fire | 0D | FIRE completion |
| 0E /8E | DEFC | delay0040; Enemy Destroyed | 00 | conditional center completion |
| 0F /8F | DF24, falls through DF28 | **Fire Power Mission Accomplished** | 0F | high-score presentation |
| 18 /98 | DF04, DF0E, DF14 | Fire One, then Two, then Three | 14 TURBO | multiball release; state02 cycles0→1→2→0 |
| 1A /9A | DF34 | Power | 1A | shield/feature cleanup |
| 1B /9B | DFDA pointer selected by counter09 &0F | random template, below | 1B | game over |
| 1E /9E | DF5A | Fire Power | 1E | Firepower award end |
| 1F /9F | DF5A | Fire Power | 1F | selector available; distinct normal L-6 event not established |
| other raw commands | no selected speech | none | unchanged | electronic dispatch |

DF24 has no terminator after Fire Power: DF28 adds Mission Accomplished. Likewise DF52 and DFC6 fall through subsequent tables. The following list follows literal bytes to the zero terminator, including delays, rather than stopping at labels:

| Random index | Pointer | Literal sequence |
|---:|---:|---|
| 0 | DF52 | You / Destroyed / Fire Power |
| 1 | DF60 | Enemy Destroyed / You |
| 2 | DF6A | Mission / Two / One / Three / Accomplished |
| 3 | DF80 | You Are / Enemy |
| 4 | DF8A | Enemy / Fire / Destroyed / You |
| 5 | DF9C | Mission / Destroyed / You |
| 6 | DFAA | Enemy / Power One |
| 7 | DFB4 | You / Destroyed / Enemy / Mission |
| 8 | DFC6 | You / One / delay0040 / Fire Power / Destroyed |
| 9 | DFD0 | Fire Power / Destroyed |
| A | DFD0 | Fire Power / Destroyed |
| B | DF8E | Fire / Destroyed / You |
| C | DF8A | Enemy / Fire / Destroyed / You |
| D | DFB4 | You / Destroyed / Enemy / Mission |
| E | DF8E | Fire / Destroyed / You |
| F | DF80 | You Are / Enemy |

The optional multiball prelude can advance speech state02 before actual releases. Existing modern Fire/One/Two/Three timing at0/.6/1.05/1.85s remains intentional; it is not claimed to reproduce every original prelude/cycle timing. Attract's existing Fire Power and FP11 remain intentional, not a new claim about original game-over selection.

## Production comparison and evidence classification

A = proven existing asset; B = plausible existing asset without sufficient proof; C = original deterministic render; D = dynamic ROM state; E = unresolved event integration/source behavior. An original command can be proven while its mapping to modern rule state remains E.

| Event / condition | Before | Original L-6 | Production action / MPF owner | Confidence |
|---|---|---|---|---|
| Accepted start / add player | raw Start always Fire Power, including attract button | 99 /9D on acceptance | original_audio game_started/player_added → l6_cmd_19/1d; remove unconditional raw Start voice | C |
| Jet unlit/lit | FP13 fixed | 8A, conditional immediate/deferred count | original_audio snapshots existing jet state; l6_cmd_0a | C |
| Spinner unlit | FP09 | 8A | l6_cmd_0a | C |
| Spinner lit | FP09 fixed | 92 persistent then8B | SP1 renderer + l6_cmd_0b | D/C |
| FIRE new / lit | FP13 both | 89+8B /8B | lane_change_off_hit/on_hit → l6_cmd_09/0b | C |
| FIRE completion | dormant legacy FP15 binding | 8D replacing89, speech | remove ordinary pending09; preserve wait128; no invented speech; dormant FP15 binding retained | E |
| POWER ordinary | inactive power_arrow tag / orphan play event | 82 repeated +8B | circle_target_group_hit → l6_cmd_02/0b; suppress pending same-target duplicate | C |
| POWER completion | none | 97 replaces82, optional88/84 | clear ordinary effect queue; no new noise/speech presentation | E |
| Center new / repeat | fire_targets static | 90×10+8B /8A×10 | fire_qualifier_off_hit/lit_hit → l6_cmd_10/0b/0a | C |
| Center bank complete | none | conditional86/8E | clear ordinary pending effect; no fabricated qualification presentation | E |
| Slings / side standups | absent /side_bumpers | 85×1 /×5 | l6_cmd_05; original pulse count only, scoring unchanged | C |
| Top target | absent | 8B | l6_cmd_0b | C |
| Return unlit/lit | absent | 8B×1 /×3 | snapshot return_lanes_lit → l6_cmd_0b | C |
| Outlane ordinary | absent | 8B | l6_cmd_0b; feature-specific speech unresolved | C/E |
| Unqualified hole | absent | 8B | ball_entered + existing lock_N_lit → l6_cmd_0b | C |
| First two actual locks | absent | 83 | accounted locked_ball event → l6_cmd_03 | C |
| Third lock / release | existing Fire/One/Two/Three | stateful98/97/94 | preserve existing release show; do not duplicate lock03 | E for original fidelity |
| Star rollovers | absent | original53/54 use8B | physical correspondence not proven; leave unchanged | E |
| Shooter departure | formerly s_plunger_inactive → FP12; restoration omitted it | periodic 6D88 → token94/raw14 | stable occupied→empty shooter state in original_audio → l6_cmd_14, immediate monophonic command; release timer pauses | verified event/routine; C fixed-seed waveform |
| Award / Special / Extra Ball / shield | absent dedicated samples | conditional paths above | retain modern scoring/presentation, no guessed speech/noise replacement | E |
| Replay credit | no electronic mapping | mechanical4D | retain; no electronic sample | proven absence of dedicated electronic command |
| Match / high score / game over / tilt | absent or intentional attract presentation | paths above | no verified active modern lifecycle owner matching original conditions; leave unchanged | E integration |
| FP03 background | existing reconstruction | 91/modifiers/reset | preserve model, timing, pitch and stage | established D |
| FA64 bonus | existing renderer/countdown | 96 | preserve entirely | established D |

No B candidate was promoted on spectral similarity alone. Existing speech remains E for waveform identity. This pass restores the proven ordinary paths and start/player cues; it does not assert that unresolved award/completion/lifecycle sounds are now historically complete.

## Asset fingerprint inventory

Every local WAV/MP3 candidate, speech WAV and generated reference was decoded with ffmpeg. The ignored JSON records SHA256, original format/rate/duration, 10ms RMS envelope, 0–4kHz spectral centroid, normalized FFT magnitudes and autocorrelation. Spectral rank is diagnostic only: capture filtering, speech coupling, truncation and background mixing can change it. There was no accepted exact existing-asset match to the new isolated effects.

The compact candidate inventory below survives cache deletion. Full curves and comparison ranks remain ignored diagnostics. Centroid is computed after 8 kHz mono conversion; periodicity reports the strongest normalized autocorrelation and its lag in milliseconds. Envelope is min/max 10 ms RMS, not a claim of analog envelope equivalence.

| File | Duration s | Rate Hz / format / channels | Centroid Hz | Periodicity | RMS min–max |
|---|---:|---|---:|---|---|
| modes/sounds/Accomplished.mp3 | 0.9825 | 22050 / mp3 / 1 | 460.7 | [{"correlation":0.43848040688469286,"ms":9.5}] | 0.000–0.668 |
| modes/sounds/Destroyed.mp3 | 1.1131 | 22050 / mp3 / 1 | 478.6 | [{"correlation":0.5049622189957019,"ms":19.5}] | 0.000–0.648 |
| modes/sounds/Enemy.mp3 | 0.7996 | 22050 / mp3 / 1 | 374.2 | [{"correlation":0.7308441810451123,"ms":19.5}] | 0.000–0.520 |
| modes/sounds/FP01.mp3 | 1.3221 | 22050 / mp3 / 1 | 1682.8 | [{"correlation":0.3778606554639673,"ms":1.0}] | 0.000–0.385 |
| modes/sounds/FP02.mp3 | 1.4789 | 22050 / mp3 / 1 | 1060.0 | [{"correlation":0.4527858439714978,"ms":2.0}] | 0.000–0.513 |
| modes/sounds/FP03.mp3 | 6.2592 | 22050 / mp3 / 1 | 367.8 | [{"correlation":0.6123328229614199,"ms":21.0}] | 0.000–0.508 |
| modes/sounds/FP04.mp3 | 0.9564 | 22050 / mp3 / 1 | 729.2 | [{"correlation":0.34982282146228233,"ms":2.5}] | 0.000–0.664 |
| modes/sounds/FP05.mp3 | 1.0086 | 22050 / mp3 / 1 | 615.7 | [{"correlation":0.43625662157226097,"ms":1.5}] | 0.000–0.561 |
| modes/sounds/FP06.mp3 | 0.8780 | 22050 / mp3 / 1 | 2204.4 | [{"correlation":0.2643733150258019,"ms":20.0}] | 0.000–0.422 |
| modes/sounds/FP07.mp3 | 1.3744 | 22050 / mp3 / 1 | 350.1 | [{"correlation":0.5241073756252277,"ms":1.5}] | 0.000–0.682 |
| modes/sounds/FP08.mp3 | 0.3556 | 22050 / mp3 / 1 | 531.5 | [{"correlation":0.33325280963633874,"ms":3.0}] | 0.000–0.670 |
| modes/sounds/FP09.mp3 | 2.4715 | 22050 / mp3 / 1 | 883.3 | [{"correlation":0.357305928365058,"ms":1.0}] | 0.000–0.440 |
| modes/sounds/FP10.mp3 | 1.0348 | 22050 / mp3 / 1 | 437.9 | [{"correlation":0.41659501309708,"ms":40.5}] | 0.000–0.474 |
| modes/sounds/FP11.mp3 | 5.4234 | 22050 / mp3 / 1 | 1013.0 | [{"correlation":0.369800969773515,"ms":2.5}] | 0.000–0.708 |
| modes/sounds/FP12.mp3 | 0.8257 | 22050 / mp3 / 1 | 525.3 | [{"correlation":0.20524949482784424,"ms":22.0}] | 0.000–0.573 |
| modes/sounds/FP13.mp3 | 0.5124 | 22050 / mp3 / 1 | 97.8 | [{"correlation":0.8061342405968716,"ms":1.0}] | 0.000–0.814 |
| modes/sounds/FP14.mp3 | 0.4340 | 22050 / mp3 / 1 | 678.7 | [{"correlation":0.3702257711014052,"ms":1.5}] | 0.000–0.645 |
| modes/sounds/FP15.mp3 | 1.7401 | 22050 / mp3 / 1 | 879.4 | [{"correlation":0.27487805140184934,"ms":1.5}] | 0.000–0.629 |
| modes/sounds/FP16.mp3 | 1.0086 | 22050 / mp3 / 1 | 178.0 | [{"correlation":0.682504521010172,"ms":1.0}] | 0.000–0.696 |
| modes/sounds/FP17.mp3 | 1.3221 | 22050 / mp3 / 1 | 480.8 | [{"correlation":0.2941501269963001,"ms":21.0}] | 0.000–0.579 |
| modes/sounds/Fire.mp3 | 0.7474 | 22050 / mp3 / 1 | 585.0 | [{"correlation":0.6455900391568274,"ms":10.0}] | 0.000–0.636 |
| modes/sounds/Mission.mp3 | 0.9041 | 22050 / mp3 / 1 | 337.0 | [{"correlation":0.5333189373891386,"ms":19.5}] | 0.000–0.560 |
| modes/sounds/One.mp3 | 0.8780 | 22050 / mp3 / 1 | 463.4 | [{"correlation":0.44913943403470763,"ms":9.5}] | 0.000–0.743 |
| modes/sounds/Power.mp3 | 0.7996 | 22050 / mp3 / 1 | 513.4 | [{"correlation":0.5805186425163817,"ms":10.0}] | 0.000–0.664 |
| modes/sounds/TestSound.mp3 | 17.4135 | 22050 / mp3 / 1 | 717.1 | [{"correlation":0.2606461118849954,"ms":1.0}] | 0.000–0.726 |
| modes/sounds/Three.mp3 | 0.8519 | 22050 / mp3 / 1 | 318.2 | [{"correlation":0.7808046108011133,"ms":9.5}] | 0.000–0.706 |
| modes/sounds/Two.mp3 | 0.7735 | 22050 / mp3 / 1 | 327.9 | [{"correlation":0.8356585829579849,"ms":9.5}] | 0.000–0.668 |
| modes/sounds/YouAre.mp3 | 1.3221 | 22050 / mp3 / 1 | 341.1 | [{"correlation":0.7565278295074658,"ms":9.5}] | 0.000–0.714 |
| sounds/fx/FP01.wav | 1.2821 | 22050 / pcm_s16le / 1 | 1691.1 | [{"correlation":0.38066227068938746,"ms":1.0}] | 0.000–0.358 |
| sounds/fx/FP02.wav | 1.4389 | 22050 / pcm_s16le / 1 | 1061.8 | [{"correlation":0.4458535993694208,"ms":2.0}] | 0.000–0.509 |
| sounds/fx/FP03.wav | 6.1449 | 22050 / pcm_s16le / 1 | 369.0 | [{"correlation":0.6185922174910367,"ms":21.0}] | 0.175–0.551 |
| sounds/fx/FP04.wav | 0.9164 | 22050 / pcm_s16le / 1 | 728.3 | [{"correlation":0.3498282531812358,"ms":2.5}] | 0.000–0.689 |
| sounds/fx/FP05.wav | 0.9687 | 22050 / pcm_s16le / 1 | 615.0 | [{"correlation":0.4362212447326701,"ms":1.5}] | 0.000–0.576 |
| sounds/fx/FP06.wav | 0.8380 | 22050 / pcm_s16le / 1 | 2233.7 | [{"correlation":0.26341364822497826,"ms":20.0}] | 0.000–0.380 |
| sounds/fx/FP07.wav | 1.3344 | 22050 / pcm_s16le / 1 | 348.9 | [{"correlation":0.5242530597470355,"ms":1.5}] | 0.000–0.741 |
| sounds/fx/FP08.wav | 0.3156 | 22050 / pcm_s16le / 1 | 526.5 | [{"correlation":0.3332378542084506,"ms":3.0}] | 0.000–0.617 |
| sounds/fx/FP09.wav | 2.4315 | 22050 / pcm_s16le / 1 | 889.3 | [{"correlation":0.3572121318246874,"ms":1.0}] | 0.000–0.407 |
| sounds/fx/FP10.wav | 0.9948 | 22050 / pcm_s16le / 1 | 435.8 | [{"correlation":0.4165455595093683,"ms":40.5}] | 0.000–0.477 |
| sounds/fx/FP11.wav | 5.3834 | 22050 / pcm_s16le / 1 | 1013.7 | [{"correlation":0.3756920577475991,"ms":2.5}] | 0.000–0.690 |
| sounds/fx/FP12.wav | 0.7858 | 22050 / pcm_s16le / 1 | 524.7 | [{"correlation":0.20523558857793256,"ms":22.0}] | 0.000–0.529 |
| sounds/fx/FP13.wav | 0.4723 | 22050 / pcm_s16le / 1 | 97.9 | [{"correlation":0.8061334737632196,"ms":1.0}] | 0.000–0.758 |
| sounds/fx/FP14.wav | 0.3940 | 22050 / pcm_s16le / 1 | 664.1 | [{"correlation":0.3697530409511607,"ms":1.5}] | 0.000–0.655 |
| sounds/fx/FP15.wav | 1.7001 | 22050 / pcm_s16le / 1 | 884.0 | [{"correlation":0.2742752854674182,"ms":1.5}] | 0.000–0.613 |
| sounds/fx/FP16.wav | 0.9687 | 22050 / pcm_s16le / 1 | 175.4 | [{"correlation":0.6824987942413213,"ms":1.0}] | 0.000–0.723 |
| sounds/fx/FP17.wav | 1.2821 | 22050 / pcm_s16le / 1 | 472.3 | [{"correlation":0.29658743631161355,"ms":21.0}] | 0.000–0.625 |
| sounds/fx/bump.wav | 0.1567 | 44100 / pcm_s16le / 2 | 415.3 | [{"correlation":0.7256930464028332,"ms":1.0}] | 0.000–0.449 |
| sounds/fx/fire_targets.wav | 0.9404 | 22050 / pcm_s16le / 1 | 729.2 | [{"correlation":0.34982220506333994,"ms":2.5}] | 0.000–0.664 |
| sounds/fx/power_target.wav | 1.7241 | 22050 / pcm_s16le / 1 | 879.3 | [{"correlation":0.2749527434690253,"ms":1.5}] | 0.000–0.629 |
| sounds/fx/side_bumpers.wav | 0.9404 | 22050 / pcm_s16le / 1 | 729.2 | [{"correlation":0.34982220506333994,"ms":2.5}] | 0.000–0.664 |
| sounds/voice/accomplished.wav | 0.9425 | 22050 / pcm_s16le / 1 | 463.3 | [{"correlation":0.43848768150496187,"ms":9.5}] | 0.000–0.711 |
| sounds/voice/destroyed.wav | 1.0732 | 22050 / pcm_s16le / 1 | 477.2 | [{"correlation":0.504613537580789,"ms":19.5}] | 0.000–0.678 |
| sounds/voice/enemy.wav | 0.7597 | 22050 / pcm_s16le / 1 | 372.5 | [{"correlation":0.7308457935402106,"ms":19.5}] | 0.000–0.523 |
| sounds/voice/fire.wav | 0.7074 | 22050 / pcm_s16le / 1 | 585.3 | [{"correlation":0.6455949801458797,"ms":10.0}] | 0.000–0.645 |
| sounds/voice/fire_power.wav | 1.4671 | 22050 / pcm_s16le / 1 | 552.2 | [{"correlation":0.6340950246680762,"ms":10.0}] | 0.000–0.666 |
| sounds/voice/mission.wav | 0.8642 | 22050 / pcm_s16le / 1 | 336.3 | [{"correlation":0.5333200303561655,"ms":19.5}] | 0.000–0.596 |
| sounds/voice/one.wav | 0.8380 | 22050 / pcm_s16le / 1 | 468.1 | [{"correlation":0.44913930021632426,"ms":9.5}] | 0.000–0.723 |
| sounds/voice/power.wav | 0.7597 | 22050 / pcm_s16le / 1 | 515.6 | [{"correlation":0.5805217274235662,"ms":10.0}] | 0.000–0.674 |
| sounds/voice/three.wav | 0.8119 | 22050 / pcm_s16le / 1 | 319.0 | [{"correlation":0.78080908895604,"ms":9.5}] | 0.001–0.715 |
| sounds/voice/two.wav | 0.7336 | 22050 / pcm_s16le / 1 | 328.0 | [{"correlation":0.8356640012954087,"ms":9.5}] | 0.000–0.674 |
| sounds/voice/you_are.wav | 1.2821 | 22050 / pcm_s16le / 1 | 339.0 | [{"correlation":0.7384525022405265,"ms":9.5}] | 0.000–0.711 |

Current uses are in the baseline inventory. Unlisted archive-style files have no active assignment discovered; names FP01 etc are not a raw-command manifest.

## Electronic interruption policy and fidelity limits

`original_audio` is ball-owned; mode stop cancels delayed commands before bonus, tilt, service or game end. It uses a small effect-priority queue and counted-score queue with original table tick delays. Immediate gated jet/spinner commands interrupt the current electronic player; accepted spinner commands alone advance SP1. High-priority raw handlers only snapshot rule variables where the scoring modes mutate them later in the same event; FIRE/POWER/center/actual locks use established semantic events. Completion events replace pending ordinary effects. No scoring, lock, light, coil, ball accounting or bonus variable is written by this mode.

`electronic_player.gd` has one foreground voice, resets playback on each new serial command, rejects duplicate/stale generation packets and cleans up on reset/disconnect. Speech remains on the existing voice bus. The dedicated FP03 player is masked while foreground electronics play and unmasked on completion/cleanup: **its timeline, pitch, stages and tween continue unchanged**. This deliberately preserves the established FP03 model; original CPU resumptions would re-enter its routine and update shared RNG, so phase/RNG resumption is a remaining fidelity compromise. Original speech and DAC have separate analog paths but share CPU execution; preserving modern independent speech does not emulate original serial CVSD workload or electronic remapping latency.

The common queue is a bounded Firepower policy, not a universal foreground emulator. Original credit/high-score/match and award state do not all have validated modern semantic counterparts. No arbitrary priority system is added for those E paths. The dormant FP15 semantic binding remains available to an external poster and uses legacy GMC effects; no active current producer was found. Reconnecting GMC restores ownership, but does not replay an interrupted one-shot. At the modern ball-end boundary outstanding gameplay queues are cancelled rather than delaying the established bonus countdown until original queued effects finish. POWER completion can suppress its final score sound when the rules set power_lit before the semantic hit; this E presentation is intentionally silent. Source renderings omit IRQ entry and speech time and analog speaker/filter coloration. Runtime gain is fixed−3 dB, awaiting cabinet balance verification.

## Files and validation

Added: original_audio code/config; electronic_player.gd; spinner_renderer.gd/spinner_model.json; l6_effect_sources.json; nine l6_cmd WAVs with lossless imports; test_original_audio.py; test_original_audio.gd; this report. Updated: config/modes.yaml, config/sounds.yaml, base sound_player mappings, Firepower-local server integration, test_gameplay_sounds.py, root import ignore exception. Existing unrelated dirty work was retained; no framework changes, commits or pushes.

Focused MPF: **46 passed in 36.962 s**, covering original sound, gameplay ownership, FP03 and bonus, including FIRE/POWER/center completion replacement, Special and actual outgoing release speech. The final full-suite result follows below. Validation uses installed **MPF 0.81.0.dev4**, **Godot 4.6.2**.  Godot source tests verify production WAV hashes/import format, all 31 SP1 DAC identities, playback, duplicate suppression, retrigger/interruption, speech coexistence, FP03 masking without time reset and bonus-boundary cleanup. Existing FP03/FA64 tests protect their independent behavior.


### Final validation results

| Check | Result |
|---|---|
| Focused original/gameplay/background/bonus MPF suite | 46 passed, 36.962 s |
| Full requested `unittest discover -s machine_tests -p '*.py'` | 97 passed, 78.093 s |
| Godot `gmc_tests/test_fp03.gd` | exit 0; assertions passed |
| Godot `gmc_tests/test_bonus_audio.gd` | exit 0; assertions passed |
| Godot `gmc_tests/test_original_audio.gd` | exit 0; assertions passed |
| `git diff --check` | passed |
| New text artifacts whitespace check | 18 files passed |
| Physical cabinet | not performed; matrix below |

All three Godot scripts report the existing ObjectDB / one resource-in-use warning at shutdown despite exit 0. Editor import also encountered the existing GMC SVG importer errors; the production WAVs imported successfully, and the tests verify their exact uncompressed PCM hashes. These warnings were not fixed by an unrelated framework patch.

Final logs: `/tmp/firepower-audit-focused-verified2.log`, `/tmp/firepower-audit-full-final.log`, `/tmp/firepower-audit-fp03-final.log`, `/tmp/firepower-audit-bonus-final.log`, `/tmp/firepower-audit-electronic-final.log`. No commit or push was performed. ROMs, archive, listings and temporary disassembly remain outside tracked source; diagnostic captures/scripts remain ignored.

## Cabinet verification matrix

Use low volume initially; check outgoing `firepower_electronic` raw_command/stage where audible ambiguity exists. These are physical verification instructions, not tests already performed.

| Setup / easy action | Expected restored audio / check |
|---|---|
| Attract: tap jets, spinner, FIRE, POWER, center, return/outlane, sling and shooter | no gameplay packets/audio; intentional attract Fire Power/FP11 remains |
| Start accepted game; add player before later balls | raw19 then raw1D on accepted addition, no raw-button Fire Power |
| Jet lamp off, then on; shoot same jet | raw0A both; during long presentation count1 off /10 on after deferred release |
| Spinner unlit, then qualify/light spinner | unlit0A; lit12 with advancing stage then0B; rapid lit spins interrupt, stage persists into next ball |
| New FIRE lane, then repeat it lit | 09+0B, then0B; fourth lane suppresses ordinary09, completion speech remains unresolved |
| Hit first POWER; repeat same target while effect pending | repeated02 then0B; pending duplicate suppressed; completing third replaces ordinary02 and has unresolved presentation |
| Center new arrow, then same lit arrow | ten10 pulses then0B; repeat ten0A; bank completion clears ordinary effect and remains unresolved |
| Left/right sling; side standup; top-center target | 05 once;05 five times;0B once |
| Return lane unlit, then return feature lit | 0B once /three times; verify lamp consumed by existing rules |
| Ordinary outlane; qualified Special outlane separately | ordinary0B; Special score/rules unchanged, original Mission Accomplished not yet restored |
| Hole with lock lamp off; same hole qualified | unqualified0B; first/second accounted capture03; no03 on third capture |
| Qualify all locks and capture third ball | existing Fire/One/Two/Three release sequence, ball accounting unchanged; original noise/prelude fidelity unresolved |
| FIRE+POWER award at10K/30K/50K/Special; extra-ball qualification | existing score/lamp presentation unchanged; do not expect restored original noise/speech yet |
| Shooter departure / star rollovers | shooter raw14/TURBO after stable departure; stars unchanged |
| Long foreground effect then silence | one electronic foreground voice; FP03 returns with preserved phase/stage; speech can play on voice bus |
| Drain at29 bonus and5X, and tilt drain | existing145 FA64 steps and lamp/score cadence; tilt skips bonus, no queued gameplay effects leak |
| End game / match / high score / replay | existing behavior retained; replay remains mechanical; remaining original lifecycle cues are documented E |

## Narrow shooter-launch correction — 2026-10-09

The ordinary audit incorrectly treated switch46's direct `7062` dispatch as
proof that no launch cue existed, and removed `s_plunger_inactive → FP12`.
The current pre-correction implementation therefore had **no launch sound**.
This contradicted the existing `ROM_INVESTIGATION.md` finding at `6DB2`.
The correction reuses that evidence, checksum-verified L-6 bytes, Sound ROM 3
and the established audit interpreter; it does not reopen the ordinary audit.

### Foreground path and exact condition

`60D8=6CDC` is the game-specific callback called by each main-loop pass at
`7062/7065`. After ball accounting, `6D40` tests RAM78, then `624C → 6494 →
6D46`. Attract/game-over bit01 diverts to `6D6F`; tilt bit02 diverts to tilt
handling. Neither reaches `6D88`. **Bit80 (first active-play transition) is
not required.** A served ball has RAM78=00; an active ball normally has 80.

`6D88` reads shooter switch46 from **RAM26 bit20**, and **RAM015A bit01**
is its previously accepted occupancy. `6D94`/`6DA8` require **RAM0157 low
nibble zero** before accepting a changed state. `6DB7–6DB9` reload that timer
with 02 whenever the observed state matches the accepted state. `63E7–6408`
decrement it once per IRQ phase0C, provided RAM04 is not FF and RAM7A is zero.
Thus it recognizes a stable change after two nominal ticks (about 33.184 ms,
with original IRQ phase and foreground latency), rather than firing directly
from a raw open-switch interrupt. Brief closure/open bounce is insufficient.

On accepted closure, `6D9B` increments 015A without sound. On accepted
**occupied→empty** transition, `6DAF` clears 015A and `6DB2` loads **94**;
`6DB4 → 6252 → 63AB → 71CB` outputs **raw14** (`94 & 1F`). There is no
first-playfield-hit requirement, scoring operation, ball-number test,
ball-count test, or sound gate (`3A`/`70`) on this command. It is immediate,
interrupts any running electronic foreground routine, and neither clears the
queued effects/scores nor installs a new effect delay. Subsequent score/effect
commands can interrupt it. It has no speech selector.

`683D` clears the occupancy latch each normal/extra ball. The initial
`7A=20` serve wait expires before ordinary processing resumes; it cannot
produce a cue just by serving. The third-lock release holds RAM7A (`6B7A`,
`6BC4`, release wait loops), pausing the shooter timer; `6C48` clears it.
The ordinary first/second-lock replacement has no shooter-sound suppression.

| Shooter lifecycle | Original / implemented launch cue |
|---|---|
| Ball served; shooter becomes occupied | recognize occupancy, no sound |
| First normal ball; later ball; extra ball | one raw14 after stable departure |
| First playfield switch / first active-play transition | not the trigger; its own sound can interrupt TURBO |
| First/second-lock replacement serve | no cue on serve; raw14 on subsequent recognized departure |
| Third-lock multiball release directly from locks | no shooter transition, no added launch cue |
| Shooter serve during release | timer paused until release ends, then recognize stable state; no unconditional permanent multiball suppression |
| Shooter serve during settled multiball | same occupied→empty condition; ball count does not suppress it |
| Ball returns to shooter and launches again | raw14 again after recognized occupancy and departure |
| Attract, tilt, bonus, service, game ended | no launch command; pending modern callbacks cancelled |

MPF's `original_audio` observes `s_plunger_active/inactive`, maintains the
accepted state and applies the two-tick stabilization. Release start/stop
pauses/resumes only this sound-state timer using the existing presentation
notifications. This approximates the original interrupt phase with a modern
33.184 ms delay; it does not emulate every original RAM7A wait or service scan.
The command uses the existing electronic BCP path and one GMC foreground
player, with its existing masking/interruption policy. No independent WAV
sound_player layer was added. FP03 state/timing and FA64 are unchanged.

The Start lamp still uses its separate
`balldevice_bd_plunger_lane_ball_eject_success` handler and files are unchanged.
That accounted mechanical-eject event can occur later than the ROM sound's
short switch stabilization, or on a skipped shooter-device entry. It cannot
cleanly replace the sound condition without changing original timing/gates.

### Production source and reproducibility

Sound ROM 3's `FC14` first decrements raw14 to 13; `FC24–FC32` selects vector
**FCDD → F8D1 (TURBO)**. `F8D1` initializes cycle count32 decimal, amplitude255,
initial period1, amplitude decay1 and increasing noise period. `F8E0–F916`
executes the finite noise sweep and returns. This is a **one-shot**, not BG2
or another persistent background modifier. Its random shift state is shared
**sound-board RAM0A:0B (HI:LO)** and is not reset by TURBO itself.

No local FPxx sample has command-labelled proof of being this routine. Production
therefore uses **`sounds/fx/l6_cmd_14.wav`**, generated from actual Sound ROM 3
instructions at `FC24` with A=13, stopping at `FC3E`. The explicit seed is
**3C00** (reset HI from F81C and explicitly chosen LO=00; reset does not
initialize LO). Rendering uses the established
895000 Hz CPU, instruction-end DAC writes, integrated held-DAC resampling,
mono PCM16/48000 Hz, gain200 and center128. Import compression is disabled.
There are 8160 DAC writes, 8761808 cycles, and 469908 output frames (9.78973 s).
The long render is normally cut short by the next playfield score/effect.

This is an exact digital render **for the stated seed**, not a claim that each
physical launch has that identical noise sequence. Existing FP03 playback does
not emulate the shared RNG history; no background, speech or other noise
routines were changed to invent it. IRQ/speech latency and analog filtering
remain outside the established rendering model. Routine identity, envelope,
frequency progression and event are verified; cabinet acoustic balance remains
to be checked.

`audio/launch_research/verify_launch.py` uses the existing ignored audit CPU/
decoder and local ROM caches. Run with the project Python from any directory;
it asserts 72 combinations of RAM78, shooter state, latch and timer, checks
RAM7A timer pause, then reproduces and byte-compares the WAV and manifest.
Use `--write` to regenerate production; the default verifies without replacing it. Its cache dependencies
are documented above under Sources and reproducibility; none is needed at
runtime or for ordinary regression tests. SHA256 identities:

- DAC schedule: `1ae2d4e061bc578e8d46cb5e1748802d58bb5541fffd90a37f1094d2bf5c339c`
- PCM: `6434460405224cb3561f64382ac7ec57691a6359af5a69e5272bb4ae8a5aeb6d`
- WAV: `9eae6c9823f1ea1081fd147e78120a4d9484c3909d8e65b1b229c6c8637c17c5`

Cabinet checks: listen to a first-ball plunge before any playfield hit, later
balls and extra balls; verify replacement plunges and a return to shooter;
confirm serving is silent, the next foreground cue interrupts TURBO, and the
Start lamp retains its accounted-eject behavior. Verify release from locks adds
no extra launch cue and a genuine shooter departure during multiball follows
the same condition. Physical verification has not been performed here.

### Launch-correction validation and changed files

| Check | Result |
|---|---|
| Bounded L-6 shooter-state probes | 72 cases plus timer-pause checks passed |
| ROM render reproduction | production WAV byte-for-byte and manifest match |
| Focused original/gameplay/background/bonus/Start-lamp machine tests | 56 passed, 51.052 s |
| Full requested `unittest discover -s machine_tests -p '*.py'` | 103 passed, 95.221 s |
| Godot original electronic / launch test | exit 0, assertions passed |
| Godot bonus test | exit 0, assertions passed |
| Godot FP03 test | exit 0, assertions passed |
| `git diff --check` | passed |
| Physical cabinet | still required |

Changed for this correction: `modes/original_audio/code/original_audio.py`
(sound-only shooter state), `audio/l6_effect_sources.json`,
`sounds/fx/l6_cmd_14.wav` and its lossless `.import`,
`audio/launch_research/verify_launch.py`, `machine_tests/test_original_audio.py`,
`gmc_tests/test_original_audio.gd`, and this map. Existing dirty work was
preserved. No commit or push. Six new machine regressions exercise real
shooter transitions, bounce, return launches/queue interruption, extra/later
balls, actual lock replacements and multiball release timer pausing, plus tilt;
existing attract and Start-lamp coverage remains green. Godot pins the launch
PCM hash and verifies both directions of foreground interruption.

Logs: `/tmp/firepower-launch-focused.log`, `/tmp/firepower-launch-full.log`,
`/tmp/firepower-launch-rom-verification.log`, and
`/tmp/firepower-launch-godot-{original,bonus,fp03}.log`. Godot retains the known
ObjectDB/resource-at-exit warnings (three resources for original electronic,
one each for bonus/FP03) and the existing editor SVG-import errors. The actual
launch WAV imported losslessly and all runtime audio assertions passed.

## Extra Ball rule integration — 2026-10-11

Successful center POWER Extra Ball collection now requests original token88
speech and queues **23 token84/raw04 GW04 requests at10-tick spacing** in the
existing monophonic foreground controller. Sound ROM3 FE76/FAEE is reproduced
as the new lossless `sounds/fx/l6_cmd_04.wav`; no FPxx recording guess is used.
Saved-FA presentation completion/replacement clears the Extra Ball arrow.
Ordinary queue/interruption, FP03 and FA64 are preserved. See
[EXTRA_BALL.md](../EXTRA_BALL.md) for executable L-6 evidence, timing limits,
native award accounting, lamp lifecycle and validation.

## End-of-game Match integration — 2026-10-11

The L-6 Match path7426–7468 now runs after the final ball/extras/bonus and home
collection, before the future High Score hook and final game-over/attract.
Successful comparisons send **token9C/raw1C → FC36 → FD30 → F843 VARI3**, using
the exact newly promoted `sounds/fx/l6_cmd_1c.wav`. Losing/disabled Match is
silent. Credits use the native ledger; no Match speech or guessed FPxx asset.
See [MATCH.md](../MATCH.md) for156 verified ROM cases, timing/range, physical
FAST display formatting, maximum-credit distinction and lifecycle validation.

## High Score to Date integration — October 13, 2026

Foreground `74F2 → [60EA]=6227` sends **token8F/raw0F** after Match. Existing
protected FIRE POWER MISSION ACCOMPLISHED speech returns0F; electronics then
dispatch `FC24 → [FCD3]=F898 APPEAR → F8A2 LITEN`. The exact routine is now
rendered to `sounds/fx/l6_cmd_0f.wav` with the established reference noise seed3C00
and lossless PCM/import hashes in `l6_effect_sources.json`. Isolated electronic
duration9.1094223464s follows the3.1065970675s phrase. This is declared fixed-seed
routine execution; actual shared sound-board noise history remains approximated.
The existing monophonic electronic player holds only this HSTD continuation if
host/mixer latency leaves speech active; cancellation drops it. No FPxx guess,
new playback object, gain adjustment or FP03/FA64 change was made.
See [HIGH_SCORE_TO_DATE.md](../HIGH_SCORE_TO_DATE.md) for comparison, credits,
descriptor timing, attract display/lamp behavior and operator reset evidence.
