# Firepower GMC without X11 or Wayland

Run from the Firepower machine directory with the MPF virtual environment active:

```sh
cd /home/murray/mpf-configs/firepower
env -u DISPLAY -u WAYLAND_DISPLAY mpf both -a
```

Use a real TTY/SSH terminal for MPF's curses UI (`TERM=xterm-256color` is suitable).
Redirecting MPF into pipes under a dumb terminal can fail with
`curses.curs_set() returned ERR`; that is separate from Godot display selection.
An automated console test must allocate a pseudo-terminal.

## Installed runtime and launch

Inventory on October13,2026:

| Item | Observed value |
|---|---|
| MPF | 0.81.0.dev4, `/home/murray/mpf-venv/bin/mpf` |
| Godot | `4.6.2.stable.official.71f334935` |
| Resolved executable | `/usr/bin/godot` → `/opt/godot/Godot_v4.6.2-stable_linux.arm64` |
| Architecture | ELF64 ARM aarch64, Linux |
| Display drivers from this binary's `--help` | x11, wayland, headless |
| Audio drivers from this binary's `--help` | PulseAudio, ALSA, Dummy |
| Previous launch | `godot` in the Firepower project, optionally `-v` |
| Desktop comparison | X11 display, PulseAudio audio |
| New launch | `godot --display-driver headless --audio-driver PulseAudio` |
| Project | `/home/murray/mpf-configs/firepower/project.godot` |
| Console environment | DISPLAY and WAYLAND_DISPLAY absent; XDG_RUNTIME_DIR retained as `/run/user/1000` |

The installed launcher `/home/murray/mpf/mpf/commands/both.py` reads `[cli]`
from `gmc.cfg`. It supports `godot_exec_path` and `gmc_project_path`, but no
additional-Godot-arguments setting. It resolves the executable with `shutil.which`
and invokes it with the GMC project as its working directory.

`gmc.cfg` now selects **`./tools/godot-cabinet`**, an executable project-local
shell wrapper. It uses `exec` to launch Godot with the headless **display** and
explicit **PulseAudio** backend, forwarding MPF's arguments. It uses Godot from
PATH; optional `GODOT_BIN` can select another installed binary. No user-specific
absolute executable path is embedded in production configuration or the wrapper.
Relative wrapper resolution requires invoking MPF from the Firepower directory;
this is also the future service's required WorkingDirectory. `-G godot` remains
the installed launcher's explicit override for development desktop launches.

Plain **`--headless` is unsuitable for the cabinet**: this binary documents it
as `--display-driver headless --audio-driver Dummy`. Dummy can validate PCM and
mixer logic but does not send cabinet audio. Do not add `--headless` to this
wrapper's arguments or override its backend with Dummy for a production run.

No MPF/GMC framework source, project audio settings, rendering configuration,
audio asset, speech DSP, gain, gameplay mode, display or hardware definition was
changed. No fake display, package installation or download was used.

## Actual audio path and user session

The verified path is:

```text
Godot PulseAudio → /run/user/1000/pulse/native
→ pipewire-pulse (PulseAudio protocol15.0.0 on PipeWire1.2.7)
→ PipeWire/WirePlumber → ALSA physical Pi output
→ alsa_output.platform-fe00b840.mailbox.stereo-fallback
```

The physical sink's monitor is
`alsa_output.platform-fe00b840.mailbox.stereo-fallback.monitor`. Monitor captures
contained nonzero PCM throughout electronic10, launch14, dynamic spinner12,
FP03, FA64 and protected HSTD speech playback. Actual PulseAudio sink inputs
belonged to the running Godot process and used stereo44100Hz, converted to the
sink's48000Hz path. This proves routing and digital output at the real sink;
it is not a microphone measurement of cabinet speaker sound or acoustic latency.

The installed ALSA backend also ran with a headless display and produced monitor
audio. Its **Default** ALSA device routes through the same PipeWire/Pulse stack
on this installation; it is not evidence of exclusive direct-hardware access.
Godot's ALSA latency query returned0, unsuitable as a latency comparison. Keep
PulseAudio because it preserves the known working path and device selection.

`pipewire.service`, `pipewire-pulse.service` and `wireplumber.service` were all
active in murray's user manager. Their runtime sockets existed. These audio
services remain required for the chosen backend. Keep `XDG_RUNTIME_DIR` and its
same-user permissions; do not strip it along with graphical variables. No
PULSE_SERVER or PIPEWIRE_REMOTE override was set. Existing user D-Bus/session
infrastructure was retained, not redesigned. Godot uses the Pulse socket; this
task does not establish that all daemon startup dependencies can operate without
the normal user session bus. A separate runtime/audio probe passed with
DBUS_SESSION_BUS_ADDRESS also unset: the Godot audio client does not require
that explicit environment variable when the Pulse socket and user services are
already available.

Labwc and Xwayland were running elsewhere in the login session during testing.
They were not stopped or used for headless launch. The process's display driver
reported **headless** with both graphical environment variables absent. A future
boot with those graphical services disabled has not been performed in this task.

## Verification and reproduction

Direct proof before editing production launch:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY godot \
  --display-driver headless --audio-driver PulseAudio \
  --path /home/murray/mpf-configs/firepower \
  --script /tmp/firepower-runtime.gd
```

That temporary inventory/playback probe ran the actual project/autoload server,
reported `DisplayServer=headless`, `AudioServer=PulseAudio`, opened BCP, played
all six representative sound classes and exited0. The durable replacement probe
is `gmc_tests/test_headless_runtime.gd`:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY ./tools/godot-cabinet \
  --path . --script res://gmc_tests/test_headless_runtime.gd \
  --log-file /tmp/firepower-headless-runtime.log
cat /tmp/firepower-headless-runtime.json
```

It rejects Dummy, verifies the actual Firepower server/BCP listener, captures
nonzero Master mixer output from all six sound classes, checks FP03 loop/rate and
speech bus processing, and shuts down during active speech. Existing dedicated
audio suites retain their original assertions and test waveform hashes, pitch,
loops, interruption, speech ordering/DSP/ducking and cancellation more deeply.

To repeat physical-sink monitoring, start this before the probe, then stop it
afterward and inspect the raw signed16-bit stereo48000Hz capture:

```sh
parec --device=@DEFAULT_MONITOR@ --raw --format=s16le \
  --rate=48000 --channels=2 > /tmp/firepower-output.pcm
```

Initial single output-latency queries were59.15ms headless versus41.63ms X11;
these startup snapshots are not an acoustic latency measurement. Three matched
warmed runs per mode,30 readings each, gave:

| PulseAudio display mode | Samples | Minimum ms | Median ms | Maximum ms |
|---|---:|---:|---:|---:|
| headless |90|41.76|57.91|73.25|
| X11 |90|26.51|52.29|111.69|

The5.62ms median difference is within overlapping observed buffer-latency ranges;
no large regression was observed in this query. Acoustic/input-to-speaker latency
has not been measured. No latency,
sample-rate, buffer, device-selection or OS audio setting was changed.

Real combined console integration used a140×40 pseudo-terminal, TERM set,
DISPLAY/WAYLAND_DISPLAY removed and the ordinary `mpf both -a` command. **Two
consecutive launches stayed alive through attract and shut down with exit0.**
MPF logged `bcp_clients_connected` and `reset_complete`. FAST connected normally:
NET FP-CPU-2000 v02.28; AUD FP-AUD-0100 v0.01; SEG FP-DSP-0007 v0.10; EXP and
EXP_INT initialized. No game was started and no diagnostic coil test was run.

A third combined launch captured the actual production attract sound at the
physical sink monitor: signed16-bit PCM peak**25178**, RMS**4667.50** over1769472
interleaved samples. MPF remained alive, reached attract, and both ends of its
live IPv6 loopback BCP5050 connection were owned by MPF/Godot. Shutdown exited0.
This verifies the configured production launcher and BCP-delivered audio
together, beyond the standalone playback/mixer probes.

Installed GMC's BCP disconnect policy is important: `GMCServer.stop(false)`
cleans audio and **exits6** rather than listening for an in-process reconnect.
Normal MPF shutdown quits GMC; restarting the pair reconnects successfully, as
the two cabinet launches verified. This task preserves that policy. A future
supervisor should restart the pair instead of assuming GMC waits indefinitely
after losing MPF. Existing reset/disconnect audio tests protect fresh-generation
cleanup; no interrupted historical sound is replayed on synchronization.

## Future appliance boot

Use the existing **murray** user, working directory
`/home/murray/mpf-configs/firepower`, and a PATH with
`/home/murray/mpf-venv/bin`, `/usr/bin` and `/bin`. Verify the Godot executable
resolves to the above ARM64 build. Preserve serial-device access and FAST port
ownership; do not launch a second MPF instance against the cabinet.

A user-systemd unit should order after/want the user PipeWire, pipewire-pulse
and WirePlumber services and retain the user's runtime directory. Starting a
user manager at boot may require a later linger/login policy decision. System
services must not simply impersonate a different user and point at murray's
socket. Preserve the audio-session/user-bus facilities until their startup
dependencies are tested separately.

MPF's current console UI requires a terminal. A future unattended unit must
either supply a TTY or deliberately use MPF's installed `-t` no-text-UI option;
this task leaves the requested interactive command unchanged. Supervise both
processes, permit clean SIGINT shutdown and account for GMC's exit-on-disconnect
policy. No display-server, window-manager, Xvfb or virtual-compositor dependency
is part of the new launch command. Full appliance boot configuration is deferred.

## Files and validation

- `gmc.cfg`: select the supported project-local executable override.
- `tools/godot-cabinet`: executable wrapper, explicit headless/PulseAudio flags.
- `machine_tests/test_gmc_launcher.py`: two tests for installed MPF spawning,
  executable configuration, argument forwarding and backend selection.
- `gmc_tests/test_headless_runtime.gd`: real-driver/display/server/mixer probe.
- `HEADLESS_GMC.md`: runtime evidence, console procedure and boot requirements.

Machine suite: **173 passed in144.850s**. New launcher tests: **2 passed**.
All **eight Godot suites passed** with DISPLAY/WAYLAND_DISPLAY removed and
explicit real PulseAudio: headless runtime, HSTD, original electronics, FP03,
FA64 bonus, speech audio, speech rendering and speech ducking. The new probe's
first run exposed an exact floating-point equality in its own rate assertion;
using the existing suites' approximate comparison corrected that new assertion.
No existing test was weakened. The final probe reports zero failures, headless
display, PulseAudio and nonzero mixer peaks for every requested sound class.
Known ObjectDB/resource shutdown warnings remain at successful exit; no runtime
failure was introduced. `git diff --check` passed.

No commit or push.
