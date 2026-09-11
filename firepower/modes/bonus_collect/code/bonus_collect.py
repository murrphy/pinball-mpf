"""Schedule bonus cycles without the periodic timer's catch-up behavior."""
from mpf.core.mode import Mode


class BonusCollect(Mode):
    @staticmethod
    def get_config_spec():
        return {"step_interval": "single|ms|130ms"}

    def mode_start(self, **kwargs):
        self._cycles = 0
        if self.player.bonus_collect_running:
            # Preserve the initial presentation pause, with mode-owned cleanup.
            self.delay.add(name="bonus_cycle", ms=80, callback=self._tick)

    def _tick(self):
        if not self.active or not self.player.bonus_collect_running:
            return
        self._cycles += 1
        if self._cycles > 1000:
            # Preserve the old timer's bounded collection safety stop.
            self.machine.events.post("bonus_collect_done")
            return
        self.machine.events.post("bonus_collect_countdown_tick",
                                 callback=self._schedule_next)

    def _schedule_next(self, **kwargs):
        # MPF runs event callbacks after all descendant events (score, value,
        # lamps and sound dispatch). There is no future cycle while they run.
        # A named one-shot delay allows at most one pending cycle and is
        # automatically cancelled when this mode stops.
        if self.active and self.player.bonus_collect_running:
            self.delay.add(name="bonus_cycle",
                           ms=self.config["mode_settings"]["step_interval"],
                           callback=self._tick)
