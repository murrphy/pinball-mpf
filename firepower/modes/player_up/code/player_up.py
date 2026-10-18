"""Own only the four Player Up lamps, once per served ball (including extras)."""
from mpf.core.mode import Mode


class PlayerUp(Mode):
    KEY = "player_up"

    def mode_start(self, **kwargs):
        del kwargs
        self.number = self.player.number
        self.lamps = [self.machine.lights[f"l_player_{n}_score_indicator"]
                      for n in range(1, 5)]
        for lamp in self.lamps:
            lamp.color("off", priority=self.priority, key=self.KEY)
        self.flash = self.machine.shows["player_up_flash"].play(
            priority=self.priority + 1,
            show_tokens={"lamp": self.lamps[self.number - 1].name})
        self.add_mode_event_handler("player_score", self._score)

    def _score(self, player_num, change, **kwargs):
        del kwargs
        # Initial zero events and other players' updates are not first scoring.
        # This mode stops before bonus, so countdown awards cannot qualify.
        if not self.flash or player_num != self.number or change <= 0:
            return
        self.flash.stop()
        self.flash = None
        self.lamps[self.number - 1].on(priority=self.priority, key=self.KEY)

    def mode_stop(self, **kwargs):
        del kwargs
        if self.flash:
            self.flash.stop()
            self.flash = None
        for lamp in self.lamps:
            lamp.remove_from_stack_by_key(self.KEY)
