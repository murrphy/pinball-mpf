"""L-6 speech requests only; never modify rules, coils or electronic playback.

The local Godot speech owner decodes selectors and models the sound-PIA latch.
See audio/FIREPOWER_SPEECH_MAP.md for original paths and bounded approximations.
"""
from mpf.core.mode import Mode


class OriginalSpeech(Mode):
    TICK = 16 * 928 * 4 / 3579545
    RELEASE_INTERVAL = 105 * TICK
    ATTRACT_ROTATION = 62 * 41 * 6 * TICK

    @staticmethod
    def get_config_spec():
        return {"attract_speech": "single|bool|true"}

    def mode_init(self):
        self.generation = 0
        self.serial = 0
        self.attract_selector = 0
        self.award_busy_until = 0.0
        self.machine.events.add_handler("firepower_speech_sync", self._sync)

    def mode_start(self, **kwargs):
        self.generation += 1
        self._send("start")
        bindings = {
            "game_started": self._game_started,
            "game_ended": self._game_ended,
            "ball_will_end": self._clear,
            "slam_tilt": self._clear,
            "tilt": self._tilt,
            "mode_attract_started": self._attract,
            "mode_attract_stopped": self._leave_attract,
            "mltp_lanes_done": self._fire,
            "circle_target_group_hit_complete": self._power,
            "fire_qualifier_lit_complete": self._enemy,
            "collect_special": self._special,
            "firepower_extra_ball_collected": self._extra_ball,
            "firepower_high_score_speech": self._high_score,
            "firepower_high_score_audio_stop": self._high_score_stop,
            "multiball_firepower_started": self._multiball,
            "multiball_firepower_ended": self._end_release,
            "firepower_electronic_command": self._electronic,
        }
        for event, handler in bindings.items():
            self.add_mode_event_handler(event, handler, priority=2000)
        for event, ticks in (("collect_firepower_bonus_10000", 20),
                             ("collect_firepower_bonus_30000", 40),
                             ("collect_firepower_bonus_50000", 80),
                             ("light_outlane_specials", 160)):
            self.add_mode_event_handler(event, self._award, ticks=ticks, priority=2000)
        if self.machine.modes["attract"].active:
            self._attract()

    def _live(self):
        game = self.machine.game
        return self.active and game and not game.ending and not game.tilted

    def _send(self, action, **payload):
        self.serial += 1
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.bcp_trigger_client(
                client, "firepower_speech", action=action,
                generation=self.generation, serial=self.serial, **payload)

    def _request(self, raw_command):
        if self.active:
            self._send("request", raw_command=raw_command)

    def _electronic(self, raw_command, **kwargs):
        # The physical sound PIA has one pending input, including non-speech
        # commands. Observe the restored controller without changing its output.
        if self._live():
            self._request(raw_command)

    def _fire(self, **kwargs):
        if self._live():
            self._request(0x0d)

    def _enemy(self, **kwargs):
        if self._live():
            self._request(0x0e)

    def _extra_ball(self, **kwargs):
        if self._live():
            self._request(0x08)  # DF3A: YOU, ONE/WON, ONE, MISSION.

    def _high_score(self, **kwargs):
        if self.active and self.machine.game and self.machine.game.ending:
            self._clear()
            self._request(0x0f)  # 74F2 -> 6227: FIRE POWER MISSION ACCOMPLISHED.

    def _high_score_stop(self, **kwargs):
        if self.machine.game and self.machine.game.ending:
            self._clear()

    def _special(self, **kwargs):
        if self._live():
            self._request(0x0c)

    def _power(self, **kwargs):
        if self._live():
            # Completion sets flag4A. 6206's timer descriptor schedules
            # 6F28 after 40 hexadecimal ticks; it queues19 -> token9A only
            # if the independent RAM70 combined-presentation count is zero.
            self.delay.reset(name="power_speech", ms=64 * self.TICK * 1000,
                             callback=self._power_finished)

    def _power_finished(self):
        if self._live() and self.machine.clock.get_time() >= self.award_busy_until:
            self._request(0x1a)

    def _award(self, ticks, **kwargs):
        if self._live():
            self.award_busy_until = self.machine.clock.get_time() + ticks * self.TICK
            self.delay.reset(name="award_speech", ms=ticks * self.TICK * 1000,
                             callback=self._award_finished)

    def _award_finished(self):
        if self._live():
            self._request(0x1e)

    def _multiball(self, **kwargs):
        if not self._live():
            return
        self._end_release()
        self._prelude_frame(0)

    def _prelude_frame(self, number):
        if not self._live():
            return
        # 6BA3: nine frames AA-11 through 11. Each waits 12h+06h ticks.
        # 6BD5's last frame speaks before the three actual release requests.
        if number == 8:
            self._request(0x18)
        self._request(0x03)  # Speech-PIA observation only; no electronic play.
        if number < 8:
            self.delay.reset(name="release_prelude", ms=24 * self.TICK * 1000,
                             callback=self._prelude_frame, number=number + 1)
        else:
            self.delay.reset(name="release_speech", ms=41 * self.TICK * 1000,
                             callback=self._release_number, number=0)

    def _release_number(self, number):
        if not self._live():
            return
        self._request(0x18)
        self._request(0x17)  # 6BFE immediately follows98, overwriting its latch.
        self.delay.reset(name="release_turbo", ms=40 * self.TICK * 1000,
                         callback=self._release_turbo)
        if number < 2:
            self.delay.reset(name="release_speech", ms=self.RELEASE_INTERVAL * 1000,
                             callback=self._release_number, number=number + 1)

    def _release_turbo(self):
        if self._live():
            self._request(0x14)

    def _end_release(self, **kwargs):
        self.delay.remove("release_speech")
        self.delay.remove("release_prelude")
        self.delay.remove("release_turbo")
        self._send("cancel_release")

    def _tilt(self, **kwargs):
        if self.active and self.machine.game:
            self._clear()
            self._request(0x07)

    def _clear(self, **kwargs):
        self.delay.remove("award_speech")
        self.delay.remove("power_speech")
        self.award_busy_until = 0.0
        self._end_release()
        self._send("clear")

    def _game_started(self, **kwargs):
        self._leave_attract()
        self._clear()
        self._request(0x1f)  # 75B9 -> [60E0]=64C8 -> descriptor token9F.

    def _game_ended(self, **kwargs):
        self._clear()
        self._request(0x1b)

    def _attract(self, **kwargs):
        # No unconditional FIRE POWER on entering attract. 6499 rotates
        # non-speech 1C/1D and random speech 1B at eligible scan boundaries.
        if self.config["mode_settings"]["attract_speech"]:
            self.delay.reset(name="attract_speech", ms=self.ATTRACT_ROTATION * 1000,
                             callback=self._attract_tick)

    def _attract_tick(self):
        if self.machine.game or not self.machine.modes["attract"].active:
            return
        if self.config["mode_settings"]["attract_speech"]:
            self.attract_selector = (self.attract_selector + 1) % 3
            self._request(0x1b + self.attract_selector)
            self._attract()

    def _leave_attract(self, **kwargs):
        self.delay.remove("attract_speech")

    def _sync(self, **kwargs):
        if self.active:
            self.generation += 1
            self._send("start")  # Never replay a historical phrase on reconnect.

    def mode_stop(self, **kwargs):
        self.delay.clear()
        self._send("stop")
