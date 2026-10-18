# Coin-door power-on lamps

`coils.l_coin_lamps` uses FAST output `cabinet-1`. It remains a switched driver,
not an RGB light. Existing electrical configuration is preserved:
`allow_enable: true`, `default_pulse_ms: 0`, no explicit `default_hold_power`.
Installed MPF 0.81.0.dev4 resolves that allowed enable to hold power 1.0.
No pulse/hold/current settings or Start-button configuration were changed.

The machine-level `coil_player` entry in `config/coils.yaml` enables it on
`init_phase_4`. Device setup and FAST configuration/synchronization finish in
phase 1; FAST starts communicator tasks/watchdog in phase 3. Phase 4 is the
first subsequent initialization phase, and is run only once per process,
not on service resets. Config-player machine handlers are registered in phase 1.

The enable belongs to the global config-player context, not a game or attract
mode. FAST keeps the output in hold mode until shutdown. There are no shows,
timers, pulses or game lifecycle handlers for the coin lamps. Service entry
stops modes but not this context. Service exit's normal reset queries/verifies
FAST driver configuration against its current enabled configuration; it does
not deliberately disable this driver or require another enable command.

## Shutdown boundary

The installed shutdown path is:

1. `MachineController.shutdown()` calls `_platform_stop()`.
2. `FastHardwarePlatform.stop()` calls each communicator's `stopping()`, cancels
   its scheduled tasks (including watchdog refresh), allows 100 ms for serial
   messages, then closes the connections.
3. `FastNetNeuronCommunicator.stopping()` sends `WD:1`, expiring the watchdog
   after 1 ms. The hardware watchdog blanks all FAST I/O driver outputs,
   including this lamp. This is hardware output blanking, not a change to MPF's
   in-memory driver state. If communication/process execution disappears,
   the normal watchdog expires without further host refreshes.

See FAST's authoritative [watchdog protocol](https://fastpinball.com/fast-serial-protocol/net/wd/).
No duplicate shutdown event or custom teardown code is needed. The smart-virtual
machine tests do not emulate the FAST watchdog and cannot prove physical power
removal at shutdown; asserting a fake virtual driver disable would test the
wrong mechanism.

Tests cover enabled startup/attract, game start, bonus and ball transition,
game end, actual service entry/exit/reset, and absence of later pulse/enable/
disable calls. Existing Start-button tests run unchanged. On the cabinet,
verify steady coin illumination through these transitions and OFF after MPF
exits (including with cabinet power still present).
