"""One owner for the Start lamp across attract and the initial game launch."""
from mpf.core.mode import Mode


class StartButtonLamp(Mode):
    def mode_start(self, **kwargs):
        del kwargs
        self.flash = None
        self.waiting_for_launch = False
        self.add_mode_event_handler("game_starting", self._new_game)
        self.add_mode_event_handler("game_ended", self._attract)
        self.add_mode_event_handler("balldevice_bd_plunger_lane_ball_eject_success", self._launched)
        self._attract()

    def _flash(self):
        if self.flash is None:
            self.flash = self.machine.shows["player_up_flash"].play(
                priority=self.priority, show_tokens={"lamp": "l_start_button"})

    def _attract(self, **kwargs):
        del kwargs
        self.waiting_for_launch = False
        self._flash()

    def _new_game(self, **kwargs):
        del kwargs
        self.waiting_for_launch = True
        self._flash()  # Keep the existing show and phase across game start.

    def _launched(self, **kwargs):
        del kwargs
        # Confirmed mechanical eject also covers a ball that passes the shooter
        # without a settled ball-entered event. Ignore subsequent launches.
        if self.waiting_for_launch:
            self.waiting_for_launch = False
            self.flash.stop()
            self.flash = None

    def mode_stop(self, **kwargs):
        del kwargs
        if self.flash:
            self.flash.stop()
            self.flash = None
