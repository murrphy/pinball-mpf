# Start button lamp

`coils.l_start_button` is the user-identified bayonet-lamp driver at
`cabinet-3` (current cabinet mapping). Its existing electrical configuration
is unchanged. `lights.l_start_button` wraps it with MPF's
`drivers` light platform, including the existing default 40 ms software fade.
No RGB hardware or additional coil output is used.

Previously the lamp had only a driver definition, with no attract/game owner.
The non-game `start_button_lamp` mode now owns it continuously across attract
and gameplay. `reset_complete`/`mode_attract_started` starts the owner;
`game_starting` arms the initial-launch latch without restarting its show.
`game_ended` clears the latch and resumes flashing. Service entry stops the show.
There is no competing attract or base show layer.

The existing tokenized `player_up_flash` show supplies 133 ms on / 133 ms off.
This reuses only the show asset with the Start lamp token; Player Up state,
configuration and behavior are unchanged.

The mechanical shooter device is `bd_plunger_lane`; its switch is `s_plunger`
on `playfield1-7`. Trough serving, `ball_starting`/`ball_started`, and Start
switch `s_start_button` (`cabinet-8`, tag `start`) retain their existing behavior.
`balldevice_bd_plunger_lane_ball_eject_success` stops the flash and latches OFF
for the rest of the game. This is the confirmed shooter-to-playfield transfer;
it can follow the first playfield switch. No polling or launch timer is used.

## Physical trace and correction

The cabinet log `logs/2026-09-26-14-23-44-mpf-firepower.log` records:

- 14:24:12.632: `game_starting`; 14:24:13.055: P1 ball 1 `ball_started`.
- 14:24:13.151: trough eject attempt toward the shooter.
- 14:24:13.458–13.664: audited shooter closures and four `s_plunger_inactive`
  events, but **no shooter `ball_entered` event** for this initial serve.
- 14:24:16.188: MPF posts shooter `ejecting_ball` for the skipped-device path.
- 14:24:17.465: `playfield_active` from top lane E.
- 14:24:17.636: shooter `ball_eject_success`, followed by playfield ball entry.

The former stop event did occur. Its guard required a settled shooter
`ball_entered` event, so it never armed and ignored the open events. The logs
show brief contacts rather than settled occupancy; they do not establish the
physical cause of those contacts or precisely timestamp the human launch.
The confirmed eject path avoids interpreting serve-time switch openings as a
launch and also handles normal settled shooter occupancy. In this capture,
confirmation followed first playfield activity by about 170 ms.

A regression reproduces the short contacts without a settled entry using real
switch transitions and MPF's mechanical-device skip/confirmation path. It failed
against the old controller and passes with the confirmed eject handler. No
synthetic launch event or temporary production logging is required.

Later player additions, balls, extra balls, multiball and shooter returns have
no reset handler. Only a new game's `game_starting` re-arms the latch. Existing
player-add rules are untouched (including their actual admission conditions).

Tests observe both light colors and the underlying driver's enabled/disabled
state: attract, unchanged show through initial serve and four-player addition,
confirmed launch, later turns/balls, extra ball, shooter return, game end,
and the next game. Cabinet verification is still required for output mapping,
brightness/fade, initial shooter departure and game-end flash resumption.
