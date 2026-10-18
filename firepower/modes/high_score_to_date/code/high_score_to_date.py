"""Original L-6 HSTD, attached to Match's existing queued ending hook.

One persistent six-digit score; no modern rankings or initials. See
HIGH_SCORE_TO_DATE.md for the unusual low-byte comparison and fidelity limits.
"""
import json
from pathlib import Path

from mpf.core.mode import Mode


class HighScoreToDate(Mode):
    TICK = 16 * 928 * 4 / 3579545
    PRESENTATION = 3 * 248 * TICK
    ATTRACT_PHASE = 127 * TICK
    VARIABLE = 'firepower_high_score_to_date'
    KEY = 'high_score_to_date'

    @staticmethod
    def get_config_spec():
        return {'function_13': 'single|int|55', 'function_25': 'single|int|3'}

    def mode_init(self):
        self.queue = None
        self.winner = 1
        self.awards_left = 0
        self.flash = None
        self.attract_display = None
        self.attract_text = None
        self.showing_high_score = False
        self.match_wait_until = 0.0
        self.in_service = False
        model = json.loads((Path(self.machine.machine_path) / 'audio/speech_model.json').read_text())
        self.speech_duration = model['phrases'][model['commands']['0f_0']['phrase']]['duration']

    def mode_start(self, **kwargs):
        del kwargs
        self.in_service = self.machine.service.is_in_service()
        for name in ('function_13', 'function_25'):
            if not 0 <= self.config['mode_settings'][name] <= 99:
                raise ValueError(f'{name} must be an original two-digit adjustment')
        self.add_mode_event_handler('firepower_high_score_check', self._check)
        self.add_mode_event_handler('firepower_match_credit', self._match_credit, priority=1000)
        self.add_mode_event_handler('game_starting', self._cancel, priority=1200)
        self.add_mode_event_handler('service_mode_entered', self._service, priority=1200)
        self.add_mode_event_handler('service_mode_exited', self._service_exit)
        self.add_mode_event_handler('mode_attract_started', self._attract)
        self.add_mode_event_handler('mode_attract_stopped', self._stop_attract)
        if self.machine.modes['attract'].active:
            self._attract()

    @staticmethod
    def qualifies(score, stored):
        # 74C2/74CF accept greater upper bytes; 74DA is BNE, so the
        # equal-upper-byte path accepts ONLY an exactly equal low byte.
        return score // 100 > stored // 100 or score == stored

    def _match_credit(self, **kwargs):
        del kwargs
        credits = self.machine.modes['credits']
        maximum = credits.credits_config['max_credits'].evaluate([])
        current = self.machine.variables.get_machine_var('credits_whole_num') or 0
        if maximum > current and not self.machine.settings.get_setting_value('free_play'):
            # 767F leaves a 16-tick timer after the last Match credit. The
            # following HSTD descriptor waits for it before sending token8F.
            self.match_wait_until = self.machine.clock.get_time() + 16 * self.TICK

    def _check(self, queue, **kwargs):
        del kwargs
        if self.queue or not self.machine.game:
            return
        players = self.machine.game.player_list
        # Original three BCD bytes roll over at one million; modern score
        # devices and player score variables retain all seven digits.
        player = max(players, key=lambda p: p.score % 1_000_000)
        self.winner = player.number  # max keeps the first player on a tie.
        score = player.score % 1_000_000
        stored = self.machine.variables.get_machine_var(self.VARIABLE)
        if not self.config['mode_settings']['function_13'] or not self.qualifies(score, stored):
            return
        self.queue = queue
        queue.wait()
        self.machine.variables.set_machine_var(self.VARIABLE, score)
        # No score-text animation: the winning final score stays on its display.
        # Preserve the established gameplay-only Player Up policy in attract.
        self.flash = self.machine.shows['player_up_flash'].play(
            priority=self.priority,
            show_tokens={'lamp': f'l_player_{self.winner}_score_indicator'})
        self.machine.events.post('firepower_high_score_qualified', player=self.winner, score=score)
        wait = max(0, self.match_wait_until - self.machine.clock.get_time())
        if wait:
            self.delay.reset(name='hstd_begin', ms=wait * 1000, callback=self._present)
        else:
            self._present()

    def _present(self):
        if not self.queue:
            return
        self.machine.events.post('firepower_match_audio_stop')
        self.machine.events.post('firepower_high_score_speech')
        self.delay.reset(name='hstd_electronic', ms=self.speech_duration * 1000,
                         callback=self._electronic)
        self.delay.reset(name='hstd_award', ms=self.PRESENTATION * 1000,
                         callback=self._start_awards)

    def _electronic(self):
        if self.queue:
            self.machine.events.post('firepower_high_score_sound')

    def _start_awards(self):
        if not self.queue:
            return
        credits = self.machine.modes['credits']
        maximum = credits.credits_config['max_credits'].evaluate([])
        current = self.machine.variables.get_machine_var('credits_whole_num') or 0
        # Original 766C checks once before the batch. Max00 is free play.
        allowed = not self.machine.settings.get_setting_value('free_play') and maximum > current
        self.awards_left = self.config['mode_settings']['function_25'] if allowed else 0
        if self.awards_left:
            self._award()
        else:
            self._finish()

    def _award(self):
        if not self.queue:
            return
        self.machine.events.post('firepower_high_score_credit', rom_hstd_batch=True)
        self.awards_left -= 1
        if self.awards_left:
            self.delay.reset(name='hstd_award', ms=16 * self.TICK * 1000, callback=self._award)
        else:
            # Final Game Over descriptor also waits for the last credit timer.
            self.delay.reset(name='hstd_award', ms=16 * self.TICK * 1000, callback=self._finish)

    def _finish(self):
        self.delay.remove('hstd_begin')
        self.delay.remove('hstd_electronic')
        self.delay.remove('hstd_award')
        self.awards_left = 0
        self.match_wait_until = 0.0
        if self.flash:
            self.flash.stop()
            self.flash = None
        self.machine.events.post('firepower_high_score_audio_stop')
        if self.queue:
            queue, self.queue = self.queue, None
            queue.clear()

    def _attract(self, **kwargs):
        del kwargs
        self._stop_attract()
        if self.in_service or not self.config['mode_settings']['function_13']:
            return
        if self.machine.game:
            # Attract's start event can precede clearing the native Game object.
            if self.machine.game.ending:
                self.delay.reset(name='hstd_attract_start', ms=1, callback=self._attract)
            return
        self.attract_display = self.machine.segment_displays[f'player{self.winner}_display']
        self.attract_text = self.attract_display.text
        self.showing_high_score = False
        self._attract_step()

    def _attract_step(self):
        if self.machine.game or not self.attract_display:
            return
        self.showing_high_score = not self.showing_high_score
        lamp = self.machine.lights['l_high_score_indicator']
        if self.showing_high_score:
            score = self.machine.variables.get_machine_var(self.VARIABLE)
            self.attract_display.add_text(f'{score:>7,d}')
            lamp.on(priority=self.priority, key=self.KEY)
        else:
            self.attract_display.add_text(self.attract_text)
            lamp.color('off', priority=self.priority, key=self.KEY)
        self.delay.reset(name='hstd_attract', ms=self.ATTRACT_PHASE * 1000,
                         callback=self._attract_step)

    def _stop_attract(self, **kwargs):
        del kwargs
        self.delay.remove('hstd_attract')
        self.delay.remove('hstd_attract_start')
        if self.attract_display:
            self.attract_display.add_text(self.attract_text)
        self.attract_display = None
        self.attract_text = None
        self.showing_high_score = False
        self.machine.lights['l_high_score_indicator'].remove_from_stack_by_key(self.KEY)

    def _cancel(self, **kwargs):
        del kwargs
        self._stop_attract()
        self._finish()

    def _service(self, **kwargs):
        self.in_service = True
        self._cancel(**kwargs)

    def _service_exit(self, **kwargs):
        del kwargs
        self.in_service = False
        if self.machine.modes['attract'].active:
            self._attract()

    def mode_stop(self, **kwargs):
        self._cancel(**kwargs)
