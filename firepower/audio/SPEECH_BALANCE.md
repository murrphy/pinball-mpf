# Firepower speech/sound balance

**Current cabinet setting:** speech balance 4.0 dB, with foreground-only
5 dB speech ducking. See the final section. Earlier sweeps below remain
historical measurement evidence.

## Cabinet finding and diagnosis

The cabinet remains authoritative: both the +4 dB clean boost and the subsequent
compressor/+18 dB makeup/limiter implementation were physically reported too quiet.
The prior production gain was active in the actual GMC-created speech player.
This pass measures the actual mixer again; no cabinet SPL/transfer response was
measured. It does not claim that a meter reading proves cabinet intelligibility.

Two measured factors explain why raising average voltage alone was ineffective:

- Speech has about 87–96% of its rendered spectral energy below 1.5 kHz; only
  about 2–5% lies in 1.5–4 kHz. Jets have substantially more upper-frequency
  energy. Cabinet frequency response and simultaneous masking can therefore
  change prominence in ways that full-band RMS cannot describe. Their exact
  acoustic contributions remain unmeasured.
- The previous limiter was already holding gain down throughout nearly all
  active speech, so additional makeup mostly increased gain reduction.

**Correction to the previous report:** its 5–7% figure was the fraction of
pre-limiter samples exceeding the ceiling. It was not the percentage of time
under limiting. In the current-setting captures, actual limiting above 0.1 dB
covers 97.79 to 100.00% of nonzero active speech samples. Mean instantaneous
limiter reduction is 2.5–3.2 dB; maximum is about 5.4–5.7 dB. Mean compressor
reduction is 4.0–8.7 dB. These are sample-inferred gain statistics, distinct from
RMS energy-loss measurements. No extra player attenuation or missing gain
assignment was found in the workspace's production path.

## Makeup-only sweep (prior production chain)

Actual Godot captures of all six representative phrases use +18 dB makeup as
current, then +20/+22/+24 dB. The setter accepted the latter diagnostic values;
Godot's documented/editor range ends at +20 dB. Production avoids this issue
by using fixed +14 dB compressor makeup plus a separate balance amplifier.

RMS is the arithmetic mean of the six individual active RMS values; LUFS and GR
columns are phrase ranges. Peak columns show the highest Master sample/true peak.

| Extra makeup | Mean active RMS | LUFS range | Peak / true peak | Mean compressor GR | Mean limiter GR | Limiter active |
|---|---:|---:|---:|---:|---:|---:|
| +0 | -10.09 | -8.60 to -7.60 | -1.39 / -1.2 | 3.96 to 8.68 | 2.51 to 3.19 | 97.79 to 100.00% |
| +2 | -9.98 | -8.20 to -7.30 | -1.39 / -1.2 | 3.96 to 8.68 | 4.30 to 4.86 | 100.00 to 100.00% |
| +4 | -9.90 | -8.50 to -7.40 | -1.38 / -1.1 | 3.96 to 8.68 | 6.15 to 6.76 | 100.00 to 100.00% |
| +6 | -9.85 | -8.10 to -7.40 | -1.38 / -1.1 | 3.96 to 8.68 | 8.01 to 8.70 | 100.00 to 100.00% |

Adding 6 dB raises mean active RMS by only about 0.25 dB. This is saturation of
the gain/limiter combination, not a useful 6 dB cabinet balance correction.
The high-makeup settings were rejected as production defaults.

## Speech-only presence shaping and attack trials

The production chain is **90 Hz high-pass → broad presence EQ → compressor →
balance gain → predictive limiter**, all on `voice`. No other bus is processed.

The 90 Hz low cut uses 12 dB/octave, resonance 0.5. It removes very-low-frequency
and DC energy with a cutoff well below the useful voice body. The octave EQ has
+2 dB at 1 kHz, +4 dB at 2 kHz and +2 dB at 4 kHz; all other bands are 0 dB.
Adjacent boosted bands form broad shoulders rather than a narrow telephone-like
peak. No 8/16 kHz boost was added. The spectrum measurements identified weak
presence energy and support this modest broad boost, not a uniform RMS target.

Actual rendered 1.5–4 kHz energy at the selected preset rises **4.5–5.5 dB**
across FIRE, POWER, FIRE ONE, TWO, THREE and MISSION ACCOMPLISHED. This is an
active-RMS/STFT band-energy estimate, not a measured 4.5–5.5 dB acoustic gain.

Attack trials covered 0.2, 2, 4 and 8 ms. Without EQ, slower attacks left active
RMS essentially unchanged and increased average limiter reduction from roughly
3 dB to 5–8 dB. With identical EQ/makeup, 2 ms improved presence-band energy by
only about -0.05 to +0.47 dB compared with 0.2 ms; first-100-ms RMS changed by
only -0.44 to +0.51 dB. There was no consistent useful transient improvement.
We therefore **retain 0.2 ms attack and 80 ms release** rather than transferring
more transient control to the limiter. Threshold -15 dBFS and ratio 3:1 remain
unchanged. The 4/8 ms diagnostic setter values exceeded the documented editor
attack range; no such value is used in production.

References: [Godot EQ10](https://docs.godotengine.org/en/stable/classes/class_audioeffecteq10.html),
[filters](https://docs.godotengine.org/en/stable/classes/class_audioeffectfilter.html),
[compressor](https://docs.godotengine.org/en/stable/classes/class_audioeffectcompressor.html),
[amplifier](https://docs.godotengine.org/en/stable/classes/class_audioeffectamplify.html).

## Centralized cabinet balance and A/B presets

**Change only `SPEECH_BALANCE_DB` in `audio/speech_player.gd`.**
The initial recommendation is **3.0**. Fixed compressor makeup is now +14 dB,
so the recommended +3 balance gives +17 dB total post-compressor gain before
limiting. Player pre-gain stays +1 dB. All presets use the same one player,
EQ, compressor and limiter; there is no electronic ducking or attenuation.

Cabinet presets are **0, +3 and +6 dB nominal balance**. The 0 preset is the new
EQ-path reference, not an exact recreation of the previous no-EQ sound. The
previous cabinet setting is shown separately below. All cells are active RMS
(dBFS) / indicative integrated LUFS at the layout's Master output.

| Phrase | Previous cabinet setting | New reference 0 | Recommended +3 | Strong +6 |
|---|---:|---:|---:|---:|
| FIRE | -10.02 / -8.2 | -10.57 / -7.9 | -8.48 / -5.7 | -8.35 / -5.6 |
| POWER | -10.28 / -8.1 | -10.81 / -8.6 | -8.64 / -5.7 | -8.51 / -5.6 |
| FIRE ONE | -9.79 / -7.6 | -10.67 / -8.0 | -8.84 / -5.9 | -8.65 / -5.7 |
| TWO | -10.05 / -8.6 | -12.51 / -10.0 | -10.43 / -7.9 | -9.89 / -7.4 |
| THREE | -9.88 / -7.7 | -11.60 / -8.9 | -9.80 / -7.4 | -9.61 / -6.8 |
| MISSION ACCOMPLISHED | -10.54 / -8.3 | -11.30 / -8.3 | -10.32 / -7.2 | -10.06 / -7.0 |

Recommended +3 has mean limiter reduction of 1.55 to 2.25 dB. It remains active
through most speech but is light compared with the rejected +6 preset's
4.20 to 4.77 dB continuous reduction. +6 adds little level and is a diagnostic A/B
option, **not the recommended default**. These are nominal presets; the ceiling
prevents claiming that +6 is physically or digitally 6 dB louder than reference.

At the recommendation, speech LUFS are about -5.7 to -7.5, versus jets about
-5.7 and launch about -9.6. Active speech RMS remains about -8.5 to -10.4 dBFS,
versus electronic scoring/jets/launch about -6.3 to -6.9. The target is prominence
and intelligibility; the spectral gain is more useful than forcing identical RMS.
Listen on the cabinet before accepting this as the final balance.

## Headroom, latency and preservation

The limiter retains its -1.3 dBFS internal ceiling and 50 ms release. Across all
23 speech phrases at the strongest tested +6 preset, worst voice sample peak is
-1.298 dBFS, worst Master sample peak -1.386 dBFS, and worst oversampled
Master true peak **-1.2 dBFS**. No clipping occurs in the captured speech output;
true-peak headroom is about 1.2 dB. Test-only taps prove the actual pipeline,
including player gain, EQ/dynamics, voice fader and Master routing. Internal
floating-point pre-limiter values above 0 dBFS are controlled before output.

The total measured impulse peak delay is **2.041 ms**, at both +3 and +6,
including EQ/filter and limiter. This matches the previous limiter lookahead;
no new block delay or phrase scheduling delay was introduced. Limiter waveform
sample order is checked after its common 90-frame delay at 44.1 kHz. EQ changes
frequency response/phase as intended, not word sequence or phrase duration.

All 23 production WAV and imported PCM hashes remain byte-identical to the
ROM-derived manifest. There is no per-phrase normalization. Phrase identity,
word onsets/order, sample counts, random weighting, multiball timing, attract
conditions, queue/interruption rules and cleanup remain unchanged. The same
global processing retains relative character, though EQ/compression naturally
change relative measured energy for differently voiced phrases.

Electronic foreground remains -3 dB on effects (0 dB), FP03 -3 dB on music
(0 dB), and FA64 -3 dB on effects. Launch/spinner/electronic assets and controllers
are untouched. Voice remains -0.0438385 dB to Master; Master remains at its layout
-0.0438385 dB, or -3.098 dB when persisted MPF `master_volume = 0.7` arrives.
No Master processing or shared gain changed. Isolated speech headroom does not
guarantee headroom for simultaneous speech/electronic summation; test that
condition on the physical cabinet as part of the listening pass.

## Measurement methods, reproduction and verification

Captures use the actual Godot 4.6.2/GMC production player and 44.1 kHz Dummy mixer,
including native 48 kHz speech resampling. Master taps precede its fader, so the
measured Master attenuation is applied mathematically in analysis. This is not
an acoustic cabinet capture. RMS uses 20 ms frames gated at -50 dBFS and 35 dB
below the loudest frame; padding is excluded. Spectra use active 2048-point Hann
STFTs. FFmpeg EBU R128 supplies LUFS/true peak. Short-phrase LUFS can vary by
several tenths with capture/block alignment; scoring below 400 ms has no LUFS.

Compressor gain reduction is inferred from its input/output after removing
makeup gain. Limiter reduction is inferred from pre/post samples aligned by
lookahead. Active time means more than 0.1 dB reduction, on nonzero samples in
active frames. `presence_levels.json` includes per-phrase active seconds,
percentages, mean/max/p95 GR, all spectra, sweeps and strongest-preset meters.
Earlier `rendered_levels.json` and raw `level_measurements.json` remain unchanged
as historical evidence. Float captures stay under /tmp; WAV assets are never
written by the research tools.

From `firepower/`:

```sh
# Historical makeup-only and attack/EQ comparisons reconstructed in the real mixer.
godot --headless --path . --script res://gmc_tests/study_speech_presence.gd
godot --headless --path . --script res://gmc_tests/study_speech_presence.gd -- --shaping
# Three presets in one player, serially.
godot --headless --path . --script res://gmc_tests/study_speech_presence.gd -- --balance
# Actual configured default and strongest preset, including measured latency/cleanup.
godot --headless --path . --script res://gmc_tests/test_speech_render.gd -- --output-dir=/tmp/firepower-presence-3
godot --headless --path . --script res://gmc_tests/test_speech_render.gd -- --balance-db=6 --all-phrases --output-dir=/tmp/firepower-presence-6-all
python3 audio/speech_research/analyze_presence.py
```

Focused Python speech tests: **14 passed**. Full machine suite: **117 passed**
in 145.407 seconds. All four Godot audio suites (speech, electronic, FP03, FA64)
passed; makeup/shaping/balance sweeps, configured-default captures and all-23
strong-preset captures passed. Oversampled analysis confirms all tested speech
true peaks at or below -1 dBFS. Existing ObjectDB/resource shutdown warnings
remain. `git diff --check` and scoped whitespace/hash checks pass. No commit/push.

**Physical cabinet verification is still required.** Start at balance 3.0 and
listen to FIRE, POWER, FIRE ONE, TWO, THREE and MISSION ACCOMPLISHED alone and
against gameplay effects. Confirm prominence, intelligibility, preserved voice
character, no harshness/pumping/distortion and correct drain/tilt/game-end silence.
If balance is wrong, adjust only the central balance constant and repeat rendered
peak checks. The cabinet result decides whether this pass is sufficient.

## Speech intelligibility: foreground-only ducking — 2026-10-10

Cabinet listening confirmed the presence processing is substantially improved,
but electronic foreground effects can still mask speech. Raising balance to
10 dB produces little extra voice level: the existing speech limiter defines
the output ceiling, and additional pre-limiter gain primarily increases gain
reduction. We retain the workspace's natural **4.0 dB speech balance**, with
all voice EQ, filtering, compression, limiter, bus gain and PCM unchanged.
No further makeup or compression is added.

The only attenuated target is the production `OriginalElectronicAudio`
AudioStreamPlayer (`audio/electronic_player.gd`), normally **-3 dB**, on
`effects`. While speech owns the duck it ramps to **-8 dB**, using:

- `SPEECH_EFFECTS_DUCK_DB = -5.0`
- `SPEECH_DUCK_ATTACK_MS = 15.0`
- `SPEECH_DUCK_RELEASE_MS = 150.0`

These three cabinet controls are centralized in the foreground player.
Ducking uses its gain only: the effects bus is unchanged because FA64 also
routes there. FP03, FA64, Master, mechanical/unrelated effects and speech
remain untouched. The existing foreground-triggered FP03 mask is preserved.
No electronic token, routine, asset, playback object, position, interruption
or command scheduling changes.

The speech controller emits ownership changes at whole-phrase boundaries.
FIRE ONE, YOU ARE DESTROYED and MISSION ACCOMPLISHED are complete original
phrase WAVs; no word-end callbacks can release their duck. On natural
completion, the pending input latch is consumed before releasing ownership.
A queued speech continuation keeps the player at -8 dB continuously. A
non-speech pending command or genuine idle gap starts the release. New speech
during release cancels the upward tween and ramps downward from the current
gain, without jumping toward full level. Duplicate active notifications do not
restart ramps. Queue policy, original phrase order and timing are unchanged.

Normal ends release smoothly to exactly -3 dB. Explicit cancellation/clear,
reset, disconnect and speech-controller teardown restore immediately and
cancel any in-flight tween, preventing stale attenuation after lifecycle
cleanup. Electronic-player reset/teardown also clears its duck state.

### Actual simultaneous mixer measurements

`gmc_tests/test_speech_duck.gd` captures actual production voice/effects/Master
output for FIRE ONE and MISSION ACCOMPLISHED over launch/TURBO. The A/B reference
bypasses only the speech-to-duck connection; speech DSP is identical. No assets
are rewritten. Results and frame-observed ramps are in
`speech_research/duck_levels.json`; raw stereo float captures remain in
`/tmp/firepower-duck/`. Reproduce with:

```sh
godot --headless --path . --script res://gmc_tests/test_speech_duck.gd
python3 audio/speech_research/analyze_duck.py
```

The same 100–600 ms simultaneous window measures electronic RMS **-6.65 dBFS
without ducking and -11.65 dBFS with ducking** for both phrases. Voice RMS
remains unchanged within 0.3 dB (capture alignment tolerance); FIRE ONE is
about -7.65 dBFS and MISSION ACCOMPLISHED about -9.9 dBFS in that window.
This is approximately **5 dB more speech-to-foreground separation**, without
raising voice or changing ordinary non-speech gameplay level.

Configured linear-in-dB ramps are 15/150 ms. In the headless mixer run the
first frame-observed target was 9.953 ms for attack and 151.612 ms for release.
Tween integration and frame scheduling limit wall-clock measurement precision;
these are observations, not sample-accurate envelope promises. Gain moves
monotonically in both traces. Actual speaker attack, consonant intelligibility
and release/pumping require cabinet listening before tuning further.

At the persisted cabinet Master gain `master_volume=0.7` (-3.098 dB), measured
simultaneous true peaks change from **+0.7 to -1.2 dBFS** for FIRE ONE and from
**+0.1 to -1.6 dBFS** for MISSION ACCOMPLISHED. Ducking improves summation
headroom. At the nearly-unity startup layout Master fader, simultaneous summed
true peaks still exceed 0 dBFS; the report records both fader conditions.
This pass does not modify Master or add shared processing. Voice-only captures
of all six representatives at balance 4.0 remain at **-1.2 dBFS true peak**.

### Preservation and validation

All 23 ROM WAVs, imported PCM, speech model, electronic/launch/spinner assets,
FP03/FA64 source/controller files, MPF mappings and gameplay files remain
unchanged. Source hashes and ordering/onset assertions pass in the existing
speech suite. The new integration test verifies no-speech normal gain,
foreground-only attenuation, surviving playback identity, whole-phrase/queued
count continuity, exact restoration, release reversal, cancellation, BCP reset,
disconnect and speech teardown. Existing electronic tests protect monophonic
interruption/serial behavior; FP03 and bonus suites protect those players.

- Focused speech/original/gameplay Python suite: **35 passed**, 36.459 seconds.
- Full machine suite: **117 passed**, 107.484 seconds.
- All four Godot audio suites: **passed** (speech, original, FP03, bonus).
- New ducking integration/mixer test: **passed**.
- Representative speech-render and oversampled peak analysis: **passed**.
- Preservation audit, scoped whitespace and `git diff --check`: **passed**.

Known ObjectDB/resource-at-exit warnings remain on successful Godot exits.
No commit or push. Changed this pass: `speech_player.gd`, `electronic_player.gd`,
`firepower_server.gd`, `gmc_tests/test_speech_duck.gd`, `audio/README.md`, this
report, `speech_research/analyze_duck.py` and `speech_research/duck_levels.json`.

**Physical cabinet verification is still required.** Listen to speech alone,
over launch/jets/spinner, through FIRE ONE and longer phrases, and through rapid
consecutive commands. Confirm initial consonants, natural recovery, no pumping,
unchanged ordinary effects and correct cancellation/tilt/drain/service cleanup.
Start with -5 dB duck and 15/150 ms ramps; tune only those foreground controls
if cabinet listening calls for adjustment.
