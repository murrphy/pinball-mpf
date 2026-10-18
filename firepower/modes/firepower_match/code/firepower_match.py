"""L-6 final-ball Match, native credit awards and FAST credits/ball display.

The ten-state timing phase approximates the original main-loop counter; there
is no score-dependent probability adjustment or animation. See MATCH.md.
"""
from mpf.core.mode import Mode


class FirepowerMatch(Mode):
    TICK = 16 * 928 * 4 / 3579545
    KEY = 'firepower_match'

    @staticmethod
    def get_config_spec():
        return {'function_26': 'single|int|0'}

    def mode_init(self):
        self.epoch = self.machine.clock.get_time()
        self.phase_source = self._timing_phase  # callable seam, returns ROM-format BCD
        self.ending_queue = None
        self.episode = 0
        self.match_number = None
        self.winners = []
        self.awards_left = 0
        self.running = False
        self.waiting_home = False
        self.ball = None

    def _timing_phase(self):
        # ROM RAM46 advances once per main-loop iteration (7067), not IRQ.
        # MPF has no 6800 workload: sample an elapsed-time phase at nominal
        # tick resolution, lazily, across games. Never choose from player scores.
        elapsed = self.machine.clock.get_time() - self.epoch
        return (int(elapsed / self.TICK) % 10) << 4

    def mode_start(self, **kwargs):
        del kwargs
        self.add_mode_event_handler('game_ending', self._ending, priority=1000)
        self.add_mode_event_handler('game_starting', self._new_game, priority=1000)
        self.add_mode_event_handler('ball_started', self._ball_started)
        self.add_mode_event_handler('machine_var_credits_whole_num', self._display)
        self.add_mode_event_handler('enabling_free_play', self._display)
        self.add_mode_event_handler('enabling_credit_play', self._display)
        self.add_mode_event_handler('service_mode_entered', self._cancel)
        self.add_mode_event_handler('collecting_balls_complete', self._home_check)
        for device in self.machine.ball_devices.items_tagged('home'):
            self.add_mode_event_handler('balldevice_' + device.name + '_ball_entered', self._home_check)
        self._display()

    def _ending(self, queue, **kwargs):
        del kwargs
        if self.ending_queue or not self.machine.game:
            return
        # This native event runs only after final regular/extra ball and bonus.
        self.episode += 1
        self.ending_queue = queue
        queue.wait()
        self.waiting_home = True
        self._home_check()
        if self.waiting_home:
            # One request through the existing BallController, never manual
            # lock counts/coils/eject retries. Match waits until return is verified.
            self.machine.ball_controller.collect_balls('home')

    def _home_check(self, **kwargs):
        del kwargs
        if not self.waiting_home or not self.machine.game:
            return
        if self.machine.game.balls_in_play or self.machine.modes['bonus_collect'].active:
            return
        if not self.machine.ball_controller.are_balls_collected('home'):
            return
        self.waiting_home = False
        self._begin()

    def _begin(self):
        if self.config['mode_settings']['function_26'] != 0:
            self._post_high_score_hook()
            return
        bcd = int(self.phase_source())
        assert 0 <= bcd <= 0x90 and bcd & 15 == 0, 'Match phase must be decimal00..90'
        self.match_number = (bcd >> 4) * 10
        self.winners = [p.number for p in self.machine.game.player_list
                        if p.score % 100 == self.match_number]
        self.running = True
        self.machine.lights['l_match'].on(priority=self.priority, key=self.KEY)
        self._display()
        self.machine.events.post('firepower_match_selected', number=self.match_number,
                                 winners=list(self.winners))
        self.awards_left = len(self.winners)
        if self.awards_left:
            self.machine.events.post('firepower_match_sound')
            self.delay.reset(name='match_award', ms=128 * self.TICK * 1000,
                             callback=self._award)
        else:
            self._post_high_score_hook()

    def _award(self):
        if not self.running or not self.ending_queue:
            return
        # Configured native Credits event awards one whole credit, no price
        # tier bonus. In free play its handler is disabled, as in ROM max=00.
        self.machine.events.post('firepower_match_credit')
        self.awards_left -= 1
        if self.awards_left:
            self.delay.reset(name='match_award', ms=16 * self.TICK * 1000,
                             callback=self._award)
        else:
            self._post_high_score_hook()

    def _post_high_score_hook(self):
        # Future High Score handler may queue.wait()/clear() here. Match precedes
        # it in L-6; final game_ended speech/attract follow the released outer queue.
        self.machine.events.post_queue('firepower_high_score_check', callback=self._complete, episode=self.episode)

    def _complete(self, episode=None, **kwargs):
        del kwargs
        if episode is not None and episode != self.episode:
            return
        self.running = False
        self.machine.events.post('firepower_match_audio_stop')
        if self.ending_queue:
            queue, self.ending_queue = self.ending_queue, None
            queue.clear()
        # The original final digits/lamp persist through attract until new game.

    def _ball_started(self, ball=None, **kwargs):
        del kwargs
        if ball is not None:
            self.ball = ball
        self._display()

    def _display(self, **kwargs):
        del kwargs
        credit = int(self.machine.variables.get_machine_var('credits_whole_num') or 0)
        right = f'{self.match_number:02d}' if self.match_number is not None else f'{self.ball:<2}' if self.ball is not None else '  '
        self.machine.segment_displays['credit_ball_display'].add_text(f'{credit:<2d} {right} ')

    def _new_game(self, **kwargs):
        del kwargs
        self._cancel()
        self.ball = None
        self._display()

    def _cancel(self, **kwargs):
        del kwargs
        self.delay.remove('match_award')
        self.waiting_home = False
        self.running = False
        self.awards_left = 0
        self.match_number = None
        self.winners = []
        self.machine.lights['l_match'].remove_from_stack_by_key(self.KEY)
        self._complete()
        self.episode += 1
        self._display()

    def mode_stop(self, **kwargs):
        self._cancel(**kwargs)
