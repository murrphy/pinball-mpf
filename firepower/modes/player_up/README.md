# Player Up lamps

The four physical lamps are `l_player_1_score_indicator` through
`l_player_4_score_indicator`, at FAST `backbox-1-1`, `backbox-1-3`,
`backbox-1-4`, and `backbox-1-5`. These are distinct from the numbered
"can play" indicators. Their existing warm color and default 40 ms fade remain.

Previously base started indefinite steady-on shows on ball start and an off
show on ball end; attract did not use these lamps. Score displays instead
flashed on later balls. Player Up now owns flashing; score text stays steady,
including the existing `player_added` two-zero initialization.

## Local L-6 evidence

Reused the previously downloaded original L-6 ROMs and local disassembly
(`/tmp/fp-l6`, `/tmp/fp-l6.dis`) and instruction booklet (`/tmp/fp-manual.pdf`).
No new download or MPF framework edit was needed. Booklet Figure 6 (page 12)
places Player Up 1–4 at lamp column 8, rows 1–4 (zero-based lamp IDs $38–$3B).
The relevant L-6 code is:

- `$7419–$741D`: add current player index `$55` to `$38`, call `$794A`.
- `$794A–$7951`: set that lamp's flash-mask bit. `$70C0–$70CD` XORs
  the flash mask into lamp output on each flash-timer expiry.
- `$76F1–$76FD`: if first-play flag `$78.7` is clear, set it and call
  `$792C` for `$38 + player`. `$792C–$7937` clears the flash-mask bit
  and sets the output bit: **steady ON**, not off. Later calls skip this block.
- `$6C77–$6C7C` reaches this path from qualifying gameplay.
- `$73CC–$73F3`: a pending same-player shoot-again skips player rotation,
  but still reaches the common ball setup/flash initialization.
- `$604C` contains 8; `$7F86–$7F93` decrements `$54` every 16 IRQs.
  With the previously recovered 928-E-clock IRQ divider, half-cycle is
  `8 * 16 * 928 * 4 / 3579545 = 0.132736423 s`. The shared show rounds
  to **133 ms on / 133 ms off** (about 3.76 Hz), with the existing 40 ms fade.
  Foreground servicing may add small original timing variation.

Bounded execution with the existing local `fp_lifecycle.Board` harness verified
all four players: after setup, RAM `$21` flash mask is respectively 1,2,4,8;
shooter switch 46 leaves it unchanged; scoring standup 14 clears it and sets
the corresponding `$17` output bit. This is focused path execution, not a
cycle-accurate whole-machine emulation. ROM CRCs were rechecked against the
existing investigation: prom1_6 af6eb0b9, prom2 f75ade1a, prom3 242ec687,
gamerom fdd3b983, green1 2145f8ab, green2 1c978a4a.

## Firepower lifecycle mapping

`ball_starting` starts the mode each ball, including MPF extra balls. Only the
active player's lamp flashes. A positive `player_score` change for that player
latches steady ON once. This central path includes the real switch scoring
handlers without duplicating their switch list; initialization, zero/negative
changes and other players' updates do not qualify. Non-scoring start, coin,
shooter, flipper and warning activity does not change score and cannot stop it.
The mode ends at `ball_will_end`, before bonus scoring, and also cleans up on
end-game, tilt, slam tilt and service entry. It stops its show and removes only
its own lamp layers. It neither changes scores nor schedules scoring events.

Per cabinet verification, Player Up indication is gameplay-only in this
implementation. All four lamps are OFF in game over/attract. The former explicit
attract P1 flash entry has been removed; gameplay cleanup already releases all
its layers, leaving no persistent off show or attract lamp owner.
Gameplay uses one key on these four lamps plus one active flash show; the old
base lamp-show event bindings are removed. No playfield insert show is changed.
The cadence is centralized in `shows/player_up_flash.yaml`.

No extra-ball award rules currently exist in this configuration. Tests exercise
MPF's supported extra-ball lifecycle by granting an extra ball directly; this
adds no production award rule. Gameplay flashing, first-hit steady state,
multiplayer handoff and extra balls have been physically verified. The corrected
game-over OFF state and next-game handoff should be checked on the cabinet.
