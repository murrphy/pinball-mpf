"""ROM-derived BG1 timing/state; GMC owns only playback and interpolation."""
from mpf.core.mode import Mode


class BackgroundAudio(Mode):
    TICK_SECONDS = 16 * 928 * 4 / 3579545
    COUNTER_TICKS = 0x0D90
    # Deliberate gameplay paths, not score updates or every playfield switch.
    PLAY_EVENTS = (
        "s_spinner_active", "sw_side_bumper_active", "sw_fire_arrow_active",
        "s_power_1_active", "s_power_2_active", "s_power_3_active",
        "s_lane_f_active", "s_lane_i_active", "s_lane_r_active", "s_lane_e_active",
        "s_top_target_active", "s_left_return_lane_active", "s_right_return_lane_active",
        "s_left_out_lane_active", "s_right_out_lane_active",
        "s_lock_1_active", "s_lock_2_active", "s_lock_3_active", "tilt_warning",
    )

    @staticmethod
    def get_config_spec():
        return {
            "enabled": "single|bool|true",
            "minimum_rate": "single|float|0.85",
            "maximum_rate": "single|float|1.25",
            "slow_region_rate": "single|float|0.85",
            "ramp_ms": "single|ms|150ms",
        }

    def mode_init(self):
        # Mode objects survive balls/players/games. Only machine startup zeros
        # the foreground phase/reference; BGEND resets the sound board only.
        self.phase_seconds = 0.0
        self.eligible_since = None
        self.reference = 0
        self.stage = 0
        self.running = False
        self.cycle = 0
        self.presentations = set()
        settings = self.config["mode_settings"]
        if not (0 < settings["minimum_rate"] <= settings["maximum_rate"]
                and settings["slow_region_rate"] > 0 and settings["ramp_ms"] >= 0):
            raise ValueError("Invalid FP03 rate/ramp settings")
        self.rate = settings["minimum_rate"]
        self.machine.events.add_handler("firepower_background_sync", self._sync)

    @property
    def counter(self):
        elapsed = self.phase_seconds
        if self.eligible_since is not None:
            elapsed += self.machine.clock.get_time() - self.eligible_since
        return int(elapsed / self.TICK_SECONDS) % self.COUNTER_TICKS

    def mode_start(self, **kwargs):
        self.presentations.clear()
        for event in self.PLAY_EVENTS:
            self.add_mode_event_handler(event, self._gameplay)
        # Jets check before their own effects, as in 6A26 -> 6284.
        self.add_mode_event_handler("sw_pop_bumpers_active", self._jet, priority=1000)
        for name in ("award", "release"):
            self.add_mode_event_handler(f"firepower_background_{name}_started",
                                        self._presentation_started, presentation=name)
            self.add_mode_event_handler(f"firepower_background_{name}_stopped",
                                        self._presentation_stopped, presentation=name)
        # ball_starting mode preparation precedes ball_started/serve completion.
        self.eligible_since = None
        self.stage = 0
        self.running = self.config["mode_settings"]["enabled"]
        if self.running:
            self.cycle += 1
            self._increment()
            self._send("start")

    def _live(self):
        game = self.machine.game
        return self.active and game and not game.ending and not game.tilted

    def _activate(self):
        if not self._live():
            return False
        if self.eligible_since is None:
            self.eligible_since = self.machine.clock.get_time()
        return True

    def _gameplay(self, **kwargs):
        if self._activate():
            # MPF drains nested event work before event callbacks. This allows
            # a target/lane completion's award gate to close before its check.
            self.machine.events.post("firepower_background_check", callback=self._opportunity)

    def _jet(self, **kwargs):
        if self._activate():
            self._opportunity()

    def _presentation_started(self, presentation, **kwargs):
        self.presentations.add(presentation)

    def _presentation_stopped(self, presentation, **kwargs):
        self.presentations.discard(presentation)
        # Gate opening alone is not a foreground opportunity.

    def _opportunity(self, **kwargs):
        if not self.running or not self._live():
            return
        current = self.counter >> 8
        if current == self.reference or self.presentations:
            return
        self.reference = current
        self._increment()
        self._send("rate")

    def _increment(self):
        self.stage = self.stage % 36 + 1
        settings = self.config["mode_settings"]
        # Rendering approximation, NOT reciprocal ROM sweep parameter/pitch.
        self.rate = (settings["slow_region_rate"] if self.stage >= 32 else
                     settings["minimum_rate"] + (self.stage - 1) / 30 *
                     (settings["maximum_rate"] - settings["minimum_rate"]))

    def mode_stop(self, **kwargs):
        if self.eligible_since is not None:
            self.phase_seconds = (self.phase_seconds + self.machine.clock.get_time() -
                                  self.eligible_since) % (self.COUNTER_TICKS * self.TICK_SECONDS)
            self.eligible_since = None
        was_running = self.running
        self.running = False
        self.stage = 0
        self.presentations.clear()
        if was_running:
            self._send("stop")

    def _sync(self, **kwargs):
        self._send("start" if self.running and self._live() else "stop")

    def _send(self, action):
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.bcp_trigger_client(
                client, "firepower_background", action=action, cycle=self.cycle,
                rate=self.rate, stage=self.stage,
                ramp_ms=self.config["mode_settings"]["ramp_ms"])
