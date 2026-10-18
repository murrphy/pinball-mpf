"""Deterministic L-6 HSTD through the existing Match/game-ending controller."""
import copy
from mpf.core.machine_vars import MachineVariables
from mpf.tests.TestDataManager import TestDataManager
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_match


class HighScoreToDateTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_match.FirepowerMatchTest.get_enable_plugins
    _start_single_ball_game = test_firepower_match.FirepowerMatchTest._start_single_ball_game
    packets = test_firepower_match.FirepowerMatchTest.packets
    end = test_firepower_match.FirepowerMatchTest.end
    unit_count = test_firepower_match.FirepowerMatchTest.unit_count
    payload = test_firepower_match.FirepowerMatchTest.payload

    @property
    def hstd(self):
        return self.machine.modes['high_score_to_date']

    @property
    def match(self):
        return self.machine.modes['firepower_match']

    @property
    def credits(self):
        return self.machine.modes['credits']

    def start(self, scores=(600010,), old=550000, match=90):
        self._start_single_ball_game()
        for _ in scores[1:]:
            self.hit_and_release_switch('s_start_button')
            self.advance_time_and_run(0.1)
        self.machine.variables.set_machine_var(self.hstd.VARIABLE, old)
        for player, score in zip(self.machine.game.player_list, scores):
            player.score = score
        self.machine.game.player.bonus_value = 0
        self.match.phase_source = lambda: match // 10 << 4
        self.advance_time_and_run(3)
        self.packets()

    def stored(self):
        return self.machine.variables.get_machine_var(self.hstd.VARIABLE)

    def requests(self, rows, name):
        return [p['raw_command'] for p in rows if p.get('name') == name
                and p.get('action') in ('play', 'request')]

    def test_factory_default_no_rankings_and_persistent_configuration(self):
        self.assertEqual(550000, self.stored())
        self.assertEqual(55, self.hstd.config['mode_settings']['function_13'])
        self.assertEqual(3, self.hstd.config['mode_settings']['function_25'])
        self.assertTrue(self.machine.variables.machine_vars[self.hstd.VARIABLE]['persist'])
        self.assertIsNone(self.machine.variables.machine_vars[self.hstd.VARIABLE]['expire_secs'])
        self.assertNotIn('high_score', self.machine.modes)

    def test_below_hstd_match_still_runs_and_no_award_or_speech(self):
        self.start(scores=(540010,))
        self.end(1)
        self.assertEqual(550000, self.stored())
        self.assertFalse(self.machine.game)
        self.assertEqual(90, self.match.match_number)
        self.assertNotIn(15, self.requests(self.packets(), 'firepower_speech'))
        self.assertEqual(0, self.unit_count())

    def test_exact_tie_qualifies_once_with_original_award(self):
        self.start(scores=(550000,))
        self.end(1)
        self.assertTrue(self.hstd.queue)
        self.assertEqual(550000, self.stored())
        self.assertIn(15, self.requests(self.packets(), 'firepower_speech'))
        self.advance_time_and_run(14)
        self.assertEqual(6, self.unit_count())
        self.assertFalse(self.machine.game)

    def test_improvement_in_only_last_two_digits_does_not_qualify(self):
        self.start(scores=(550010,))
        self.end(1)
        self.assertEqual(550000, self.stored())
        self.assertFalse(self.hstd.queue)
        self.assertEqual(0, self.unit_count())

    def test_improvement_in_hundreds_qualifies_and_saves_full_six_digits(self):
        self.start(scores=(550110,))
        self.end(1)
        self.assertEqual(550110, self.stored())
        self.assertTrue(self.hstd.queue)
        self.advance_time_and_run(14)
        self.assertEqual(6, self.unit_count())

    def test_two_players_later_player_beats_earlier_only_one_award(self):
        self.start(scores=(600010, 700020))
        self.end(15)
        self.assertEqual(700020, self.stored())
        self.assertEqual(2, self.hstd.winner)
        self.assertEqual(6, self.unit_count())

    def test_three_players_provisional_scores_do_not_update_during_game(self):
        self.start(scores=(700010, 600020, 650030))
        self.advance_time_and_run(1)
        self.assertEqual(550000, self.stored())
        self.end(15)
        self.assertEqual(700010, self.stored())
        self.assertEqual(1, self.hstd.winner)
        self.assertEqual(6, self.unit_count())

    def test_four_players_tied_highest_selects_first_noncurrent_player(self):
        self.start(scores=(600010, 700020, 700020, 650030))
        self.machine.game.player = self.machine.game.player_list[3]
        self.end(1)
        self.assertEqual(2, self.hstd.winner)
        self.assertEqual(700020, self.stored())
        self.assertEqual([600010, 700020, 700020, 650030],
                         [p.score for p in self.machine.game.player_list])
        self.advance_time_and_run(14)
        self.assertEqual(6, self.unit_count())

    def test_match_then_hstd_then_game_over_and_attract(self):
        self.start(scores=(600040,), match=40)
        timeline = []
        for event in ('firepower_match_selected', 'firepower_match_credit',
                      'firepower_high_score_qualified', 'firepower_high_score_speech',
                      'firepower_high_score_credit', 'game_ended', 'mode_attract_started'):
            self.machine.events.add_handler(event, lambda e=event, **kwargs: timeline.append(e))
        self.end(18)
        self.assertEqual(['firepower_match_selected', 'firepower_match_credit',
                          'firepower_high_score_qualified', 'firepower_high_score_speech',
                          'firepower_high_score_credit', 'firepower_high_score_credit',
                          'firepower_high_score_credit', 'game_ended', 'mode_attract_started'], timeline)
        self.assertEqual(8, self.unit_count())
        self.assertEqual(40, self.match.match_number)

    def test_hstd_descriptor_waits_for_last_match_credit_timer(self):
        self.start(scores=(600040,), match=40)
        times = {}
        for event in ('firepower_match_credit', 'firepower_high_score_speech'):
            self.machine.events.add_handler(event, lambda e=event, **kwargs: times.update(
                {e: self.machine.clock.get_time()}))
        self.end(4)
        self.assertAlmostEqual(16 * self.hstd.TICK,
                               times['firepower_high_score_speech'] - times['firepower_match_credit'], places=5)

    def test_attract_cadence_is_127_ticks_and_cancel_stays_clear_in_service(self):
        self.start(scores=(540010,))
        changes = []
        self.end(1)
        original = self.hstd._attract_step
        def observed():
            changes.append(self.machine.clock.get_time())
            original()
        self.hstd._attract_step = observed
        self.advance_time_and_run(7)
        self.assertGreaterEqual(len(changes), 2)
        self.assertAlmostEqual(self.hstd.ATTRACT_PHASE, changes[1] - changes[0], places=5)
        self.machine.variables.set_machine_var(self.hstd.VARIABLE, 650000)
        self.machine.service.start_service()
        self.advance_time_and_run(5)
        self.assertIsNone(self.hstd.attract_display)
        self.assertFalse(any(self.machine.lights['l_high_score_indicator'].get_color()))
        task = self.machine.clock.loop.create_task(self.machine.service.stop_service())
        self.advance_time_and_run(0.2)
        self.assertTrue(task.done())
        task.result()
        self.assertEqual(650000, self.stored())
        self.assertTrue(self.hstd.showing_high_score)

    def test_bonus_and_extra_ball_finish_before_hstd_check(self):
        self.start(scores=(600010,))
        self.machine.game.balls_per_game = 1
        self.machine.game.player.extra_balls = 1
        self.machine.game.player.bonus_value = 2
        self.machine.game.player.bonus_multiplier = 2
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(4)
        self.assertEqual(550000, self.stored())
        self.assertFalse(self.hstd.queue)
        self.assertTrue(self.machine.game)
        self.release_switch_and_run('s_plunger', 0.1)
        self.hit_and_release_switch('s_spinner')
        self.advance_time_and_run(1)
        self.machine.game.player.score = 700010
        self.machine.game.player.bonus_value = 0
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(1)
        self.assertEqual(700010, self.stored())
        self.assertTrue(self.hstd.queue)

    def test_speech_then_appear_no_overlap_with_match_and_three_248_tick_waits(self):
        self.start()
        speech_times, sound_times, credit_times = [], [], []
        for event, times in (('firepower_high_score_speech', speech_times),
                             ('firepower_high_score_sound', sound_times),
                             ('firepower_high_score_credit', credit_times)):
            self.machine.events.add_handler(event, lambda t=times, **kwargs: t.append(self.machine.clock.get_time()))
        self.end(1)
        rows = self.packets()
        self.assertEqual([15], self.requests(rows, 'firepower_speech'))
        self.assertEqual([], self.requests(rows, 'firepower_electronic'))
        self.advance_time_and_run(3)
        self.assertEqual([15], self.requests(self.packets(), 'firepower_electronic'))
        self.assertAlmostEqual(self.hstd.speech_duration, sound_times[0] - speech_times[0], places=5)
        self.assertEqual(0, self.unit_count())
        self.advance_time_and_run(11)
        self.assertAlmostEqual(self.hstd.PRESENTATION, credit_times[0] - speech_times[0], places=5)
        self.assertEqual(3, len(credit_times))
        self.assertAlmostEqual(16 * self.hstd.TICK, credit_times[1] - credit_times[0], places=5)
        self.assertAlmostEqual(16 * self.hstd.TICK, credit_times[2] - credit_times[1], places=5)

    def test_original_cap_checked_once_batch_can_overshoot_and_is_not_erased(self):
        self.start()
        for _ in range(11):
            self.credits.add_credit(price_tiering=False)
        self.end(15)
        self.assertEqual(28, self.unit_count())  # 11+3, original ROM behavior
        self.hit_and_release_switch('s_coin_left')
        self.advance_time_and_run(0.1)
        self.assertEqual(28, self.unit_count())
        self.assertEqual(12, self.credits.credits_config['max_credits'].evaluate([]))

    def test_already_at_cap_has_presentation_but_no_award(self):
        self.start()
        for _ in range(12):
            self.credits.add_credit(price_tiering=False)
        self.end(1)
        self.assertTrue(self.hstd.queue)
        self.assertIn(15, self.requests(self.packets(), 'firepower_speech'))
        self.advance_time_and_run(14)
        self.assertEqual(24, self.unit_count())
        self.assertFalse(self.machine.game)

    def test_free_play_keeps_presentation_and_sounds_without_hidden_credits(self):
        self.start()
        self.credits.enable_free_play()
        self.end(1)
        self.assertEqual(600010, self.stored())
        self.assertIn(15, self.requests(self.packets(), 'firepower_speech'))
        self.advance_time_and_run(3)
        self.assertIn(15, self.requests(self.packets(), 'firepower_electronic'))
        self.advance_time_and_run(11)
        self.assertEqual(0, self.unit_count())
        self.assertFalse(self.machine.game)

    def test_zero_credit_adjustment_still_presents_hstd(self):
        self.start()
        self.hstd.config['mode_settings']['function_25'] = 0
        self.end(15)
        self.assertEqual(600010, self.stored())
        self.assertEqual(0, self.unit_count())
        self.assertFalse(self.machine.game)

    def test_function13_disabled_skips_hstd_and_attract_advertisement(self):
        self.start()
        self.hstd.config['mode_settings']['function_13'] = 0
        self.end(1)
        self.assertEqual(550000, self.stored())
        self.assertFalse(self.machine.game)
        self.assertIsNone(self.hstd.attract_display)

    def test_persistence_round_trip_retains_value_without_expiration(self):
        self.start()
        self.end(15)
        variables = self.machine.variables
        variables._write_machine_vars_to_disk()
        data = copy.deepcopy(variables.machine_var_data_manager.written_data)
        self.assertEqual(600010, data[self.hstd.VARIABLE]['value'])
        self.assertIsNone(data[self.hstd.VARIABLE]['expire'])
        restored = MachineVariables(self.machine)
        restored.load_machine_vars(TestDataManager(data), self.machine.clock.get_datetime().timestamp())
        self.assertEqual(600010, restored.get_machine_var(self.hstd.VARIABLE))

    def test_attract_alternates_only_highest_player_display_and_high_score_lamp(self):
        self.start(scores=(430010, 440020, 450030, 420040))
        self.end(1)
        self.assertEqual(3, self.hstd.winner)
        self.assertTrue(self.hstd.showing_high_score)
        self.assertEqual('550,000', self.machine.segment_displays['player3_display'].text.strip())
        self.assertEqual(430010, int(self.machine.segment_displays['player1_display'].text.replace(',', '')))
        self.assertEqual('PA:1C,0  90 ', self.payload())
        self.assertTrue(any(self.machine.lights['l_high_score_indicator'].get_color()))
        for _ in range(200):
            if not self.hstd.showing_high_score:
                break
            self.advance_time_and_run(0.01)
        self.assertFalse(self.hstd.showing_high_score)
        self.advance_time_and_run(0.05)
        self.assertEqual('450,030', self.machine.segment_displays['player3_display'].text.strip())
        self.assertFalse(any(self.machine.lights['l_high_score_indicator'].get_color()))
        self.advance_time_and_run(self.hstd.ATTRACT_PHASE)
        self.assertTrue(self.hstd.showing_high_score)
        # Attract does not restore the removed Player Up owner or flash scores.
        for number in range(1, 5):
            self.assertFalse(any(self.machine.lights[f'l_player_{number}_score_indicator'].get_color()))

    def test_end_presentation_scores_steady_winner_lamp_flashes_then_cleans(self):
        self.start(scores=(600010, 700020))
        self.end(1)
        self.assertIsNotNone(self.hstd.flash)
        for _ in range(20):
            self.assertEqual('700,020', self.machine.segment_displays['player2_display'].text.strip())
            self.advance_time_and_run(0.01)
        self.assertFalse(any(self.machine.lights['l_high_score_indicator'].get_color()))
        self.advance_time_and_run(14)
        self.assertIsNone(self.hstd.flash)
        self.assertFalse(any(self.machine.lights['l_player_2_score_indicator'].get_color()))

    def test_new_game_clears_attract_hstd_and_immediately_initializes_00(self):
        self.start(scores=(540010,))
        self.end(1)
        self.assertTrue(self.hstd.showing_high_score)
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(0.1)
        self.assertTrue(self.machine.game)
        self.assertIsNone(self.hstd.attract_display)
        self.assertEqual('     00', self.machine.segment_displays['player1_display'].text)
        self.assertIsNone(self.match.match_number)
        self.advance_time_and_run(0.05)
        self.assertFalse(any(self.machine.lights['l_high_score_indicator'].get_color()))

    def test_service_cancels_delayed_sound_credit_and_releases_ending(self):
        self.start()
        self.end(1)
        self.post_event('service_mode_entered')
        self.packets()
        self.advance_time_and_run(20)
        self.assertFalse(self.hstd.queue)
        self.assertEqual(0, self.unit_count())
        self.assertNotIn(15, self.requests(self.packets(), 'firepower_electronic'))

    def test_original_six_digit_rollover_preserves_modern_seven_digit_score(self):
        self.start(scores=(1600010, 700020))
        self.end(1)
        self.assertEqual(2, self.hstd.winner)
        self.assertEqual(700020, self.stored())
        self.assertEqual(1600010, self.machine.game.player_list[0].score)
        self.assertEqual('1,600,010', self.machine.segment_displays['player1_display'].text.strip())
