"""Atomic bonus awards with one-shot scheduling and a mode-owned FA64 voice."""
from mpf.core.mode import Mode


class BonusCollect(Mode):
    MULTIPLIER_LIGHT_KEY = "bonus_collect_multiplier"

    @staticmethod
    def get_config_spec():
        # MPF's ms validator truncates fractional milliseconds; retain floats.
        return {"step_interval": "single|float|66.368",
                "pass_interval": "single|float|165.448"}

    def mode_init(self):
        self._cycle = 0
        self._sound_step = 0
        self.machine.events.add_handler("firepower_bonus_audio_sync", self._sync_audio)

    def mode_start(self, **kwargs):
        self._cycles = 0
        self._sound_step = 0
        self._cycle += 1
        self._display_multiplier = self.player.bonus_multiplier
        self.add_mode_event_handler("bonus_collect_score_step", self._sound)
        if self.player.bonus_collect_running:
            self._show_multiplier(initial=True)
            self._send_audio("start")
            # Retain the existing initial presentation pause.
            self.delay.add(name="bonus_cycle", ms=80, callback=self._tick)

    def _tick(self):
        if not self.active or not self.player.bonus_collect_running:
            return
        self._cycles += 1
        if self._cycles > 1000:
            self.machine.events.post("bonus_collect_done")
            return
        self.machine.events.post("bonus_collect_countdown_tick",
                                 callback=self._schedule_next)

    def _schedule_next(self, **kwargs):
        # Descendant events have completed: score, decrement, lamps, and sound
        # all belong to this actual step. Schedule from now, never catch up.
        if not self.active or not self.player.bonus_collect_running:
            return
        if self.player.bonus_value <= 0:
            if self.player.bonus_collect_pass < self.player.bonus_multiplier:
                # Consume the displayed level only after this pass's final
                # score/decrement/sound events, as the inter-pass pause begins.
                self._display_multiplier -= 1
                self._show_multiplier()
                self.machine.events.post("bonus_collect_next_pass")
                self.machine.events.post("bonus_collect_restore_base",
                                         callback=self._schedule_pass)
            else:
                # Keep the last step audible and allow its 40ms fade to finish.
                self.delay.add(name="bonus_cycle",
                               ms=self.config["mode_settings"]["step_interval"],
                               callback=self._finish)
        else:
            self.delay.add(name="bonus_cycle",
                           ms=self.config["mode_settings"]["step_interval"],
                           callback=self._tick)

    def _schedule_pass(self, **kwargs):
        if self.active and self.player.bonus_collect_running:
            # This replaces a step interval; it is not added on top of one.
            self.delay.add(name="bonus_cycle",
                           ms=self.config["mode_settings"]["pass_interval"],
                           callback=self._tick)

    def _finish(self):
        self.machine.events.post("bonus_collect_done")

    def _sound(self, **kwargs):
        self._sound_step += 1
        self._send_audio("step")

    def mode_stop(self, **kwargs):
        self._send_audio("stop")
        for level in range(2, 6):
            self.machine.lights[f"l_bonus_multiplier_{level}x"].remove_from_stack_by_key(
                self.MULTIPLIER_LIGHT_KEY)

    def _show_multiplier(self, initial=False):
        # Presentation state only: earned bonus_multiplier still controls totals.
        # Gameplay's light owner stops at ball_ending. Restore the achieved
        # display immediately on takeover; subsequent changes use the 40ms fade.
        for level in range(2, 6):
            self.machine.lights[f"l_bonus_multiplier_{level}x"].color(
                "on" if level == self._display_multiplier else "off",
                fade_ms=0 if initial else None,
                priority=self.priority, key=self.MULTIPLIER_LIGHT_KEY)

    def _sync_audio(self, **kwargs):
        # Resynchronize eligibility, never replay an already awarded step.
        self._cycle += 1
        self._send_audio("start" if self.active and self.player.bonus_collect_running else "stop")

    def _send_audio(self, action):
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.bcp_trigger_client(
                client, "firepower_bonus_audio", action=action,
                cycle=self._cycle, step=self._sound_step)
