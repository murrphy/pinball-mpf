"""L-6 center-target qualification; MPF owns awarded-ball accounting.

See EXTRA_BALL.md: qualification is once per physical ball, not a permanent
5X level condition. The ROM's pending-ball cap is distinct from this latch.
"""
from mpf.core.mode import Mode


class ExtraBallFeature(Mode):
    KEY = 'firepower_extra_ball'
    MAX_PER_BALL = 2

    @staticmethod
    def get_config_spec():
        return {'function_34': 'single|int|12'}

    def mode_start(self, is_extra_ball=False, **kwargs):
        del kwargs
        self.live = True
        self.active_extra = is_extra_ball
        self.first_score = False
        self.player.firepower_extra_ball_lit = 0
        self.player.firepower_extra_ball_qualified = 0
        self.player.firepower_extra_ball_collected = 0
        self.player.firepower_extra_ball_earned_ball = 0
        self.add_mode_event_handler('mltp_lanes_done', self._fire, priority=-100)
        self.add_mode_event_handler('circle_target_group_hit', self._power, priority=2000)
        self.add_mode_event_handler('firepower_extra_ball_presentation_finished', self._extinguish)
        self.add_mode_event_handler('player_score', self._score)
        self.add_mode_event_handler('tilt', self._tilt)
        self.add_mode_event_handler('ball_will_end', self._ending)
        self._lamps()

    def _eligible(self):
        game = self.machine.game
        return self.live and game and not game.tilted and not game.ending

    def _fire(self, count, **kwargs):
        del kwargs
        if not self._eligible() or self.player.firepower_extra_ball_qualified:
            return
        setting = self.config['mode_settings']['function_34'] % 10
        # 68B1: even setting accepts prior 4X; odd requires prior 5X.
        if not setting or count < (5 if setting & 1 else 4):
            return
        if self.player.firepower_extra_ball_earned_ball >= self.MAX_PER_BALL or self.player.extra_balls >= 2:
            return
        self.player.firepower_extra_ball_qualified = 1
        self.player.firepower_extra_ball_lit = 1
        self._lamps()

    def _power(self, shot, **kwargs):
        del kwargs
        if not self._eligible() or shot != 'circle_target_2':
            return
        if not self.player.firepower_extra_ball_lit or self.player.firepower_extra_ball_collected:
            return
        if self.player.firepower_extra_ball_earned_ball >= self.MAX_PER_BALL or self.player.extra_balls >= 2:
            return
        device = self.machine.extra_balls['firepower_center']
        if not device.enabled:
            return
        self.player.firepower_extra_ball_collected = 1
        self.player.firepower_extra_ball_earned_ball += 1
        device.award()  # Native player.extra_balls and game-loop Shoot Again.
        self._lamps()
        self.machine.events.post('firepower_extra_ball_collected')

    def _extinguish(self, **kwargs):
        del kwargs
        self.player.firepower_extra_ball_lit = 0
        self._lamps()

    def _score(self, player_num, change, **kwargs):
        del kwargs
        if self._eligible() and player_num == self.player.number and change > 0:
            self.first_score = True
            self._lamps()

    def _lamps(self):
        self.machine.lights['l_extra_ball_arrow'].color(
            'on' if self.player.firepower_extra_ball_lit else 'off',
            priority=self.priority, key=self.KEY)
        # MPF consumes an extra at serve; L-6 consumes it at first scoring.
        # Keep that lamp presentation without modifying MPF's accounting.
        shoot_again = self.player.extra_balls > 0 or (self.active_extra and not self.first_score)
        for name in ('l_fire_again', 'l_fire_again_1', 'l_fire_again_2'):
            self.machine.lights[name].color('on' if shoot_again else 'off',
                                            priority=self.priority, key=self.KEY)

    def _tilt(self, **kwargs):
        del kwargs
        self.live = False
        self.active_extra = False
        self._extinguish()

    def _ending(self, **kwargs):
        del kwargs
        self.live = False  # Bonus scoring cannot extinguish first-score indication.

    def mode_stop(self, **kwargs):
        del kwargs
        self.live = False
        for name in ('l_extra_ball_arrow', 'l_fire_again', 'l_fire_again_1', 'l_fire_again_2'):
            self.machine.lights[name].remove_from_stack_by_key(self.KEY)
