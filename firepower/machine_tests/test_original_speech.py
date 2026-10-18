"""Speech ownership at the real outgoing MPF/GMC command boundary."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class OriginalSpeechTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game
    SPEECH = {7, 8, 12, 13, 14, 15, 24, 26, 27, 30, 31}

    @property
    def speech(self):
        return self.machine.modes['original_speech']

    def packets(self):
        queue = self.machine.bcp.transport.get_named_client('local_display').send_queue
        result = []
        while not queue.empty():
            command, payload = queue.get_nowait()
            if command == 'trigger' and payload.get('name') == 'firepower_speech':
                result.append(payload)
        return result

    def voices(self):
        return [p['raw_command'] for p in self.packets()
                if p['action'] == 'request' and p['raw_command'] in self.SPEECH]

    def start(self):
        self._start_single_ball_game()
        self.advance_time_and_run(3)
        self.packets()

    def test_fire_completion_once_from_real_lanes(self):
        self.start()
        for letter in 'fir':
            self.hit_and_release_switch('s_lane_' + letter)
            self.advance_time_and_run(0.1)
            self.assertEqual([], self.voices())
        self.hit_and_release_switch('s_lane_e')
        self.advance_time_and_run(0.1)
        self.assertEqual([0x0d], self.voices())
        self.hit_and_release_switch('s_lane_e')
        self.advance_time_and_run(0.1)
        self.assertEqual([], self.voices())

    def test_accepted_game_start_fire_power_but_no_raw_button_voice(self):
        self.packets()
        self.post_event('s_start_button_active')
        self.assertEqual([], self.voices())
        self._start_single_ball_game()
        self.assertEqual([0x1f], self.voices())

    def test_multiball_end_cancels_later_count_requests(self):
        self.start()
        self.post_event('multiball_firepower_started')
        self.advance_time_and_run(192 * self.speech.TICK + 0.01)
        self.assertEqual([0x18], self.voices())
        self.post_event('multiball_firepower_ended')
        self.assertIn('cancel_release', [p['action'] for p in self.packets()])
        self.advance_time_and_run(4)
        self.assertEqual([], self.voices())

    def test_power_completion_speaks_only_after_cleanup_timer(self):
        self.start()
        for number in (1, 2):
            self.hit_and_release_switch('s_power_' + str(number))
            self.advance_time_and_run(3)
            self.assertEqual([], self.voices())
        self.hit_and_release_switch('s_power_3')
        self.advance_time_and_run(64 * self.speech.TICK - 0.001)
        self.assertEqual([], self.voices())
        self.advance_time_and_run(0.002)
        self.assertEqual([0x1a], self.voices())
        self.assertEqual(1, self.machine.game.player.power_lit)

    def test_power_cleanup_is_suppressed_by_long_combined_presentation(self):
        self.start()
        self.machine.game.player.fire_lit = 1
        self.machine.game.player.firepower_bonus_level = 3
        for number in (1, 2, 3):
            self.hit_and_release_switch('s_power_' + str(number))
            self.advance_time_and_run(0.1)
        self.advance_time_and_run(2)
        self.assertEqual([0x1e], self.voices())

    def test_enemy_only_on_all_six_not_partial_banks_or_raw_duplicate(self):
        self.start()
        for number in range(1, 7):
            self.hit_and_release_switch('s_arrow_' + str(number))
            self.advance_time_and_run(0.1)
            self.assertEqual([0x0e] if number == 6 else [], self.voices())

    def test_all_combined_awards_use_recovered_delay_without_changing_show(self):
        self.start()
        for level, ticks in ((1, 20), (2, 40), (3, 80), (4, 160)):
            self.machine.game.player.firepower_bonus_level = level
            self.post_event('fire_power_lit')
            self.assertEqual([], self.voices())
            self.advance_time_and_run(ticks * self.speech.TICK - 0.001)
            self.assertEqual([], self.voices())
            self.advance_time_and_run(0.002)
            self.assertEqual([0x1e], self.voices())
            self.advance_time_and_run(3)
            self.packets()

    def test_special_is_collected_outlane_not_merely_lighting_it(self):
        self.start()
        self.machine.game.player.special_lit = 0
        self.hit_and_release_switch('s_right_out_lane')
        self.advance_time_and_run(0.1)
        self.assertEqual([], self.voices())
        self.machine.game.player.special_lit = 1
        self.hit_and_release_switch('s_right_out_lane')
        self.advance_time_and_run(0.1)
        self.assertEqual([0x0c], self.voices())
        self.hit_and_release_switch('s_right_out_lane')
        self.advance_time_and_run(0.1)
        self.assertEqual([], self.voices())

    def test_multiball_prelude_and_three_release_requests_at_original_spacing(self):
        self.start()
        times = []
        send = self.speech._send
        def observe(action, **payload):
            if action == 'request' and payload.get('raw_command') == 0x18:
                times.append(self.machine.clock.get_time())
            send(action, **payload)
        self.speech._send = observe
        start_time = self.machine.clock.get_time()
        self.post_event('multiball_firepower_started')
        self.assertEqual([], self.voices())
        for ticks in (192, 233, 338, 443):
            due = start_time + ticks * self.speech.TICK
            self.advance_time_and_run(due - self.machine.clock.get_time() - 0.001)
            self.assertEqual([], self.voices())
            self.advance_time_and_run(0.002)
            self.assertEqual([0x18], self.voices())
        self.assertEqual(4, len(times))
        for actual, ticks in zip(times, (192, 233, 338, 443)):
            self.assertAlmostEqual(ticks * self.speech.TICK, actual - start_time, places=8)
        self.advance_time_and_run(2)
        self.assertEqual([], self.voices())

    def test_attract_periodic_speech_is_temporarily_disabled(self):
        self.assertFalse(self.speech.config['mode_settings']['attract_speech'])
        self.assertTrue(self.machine.modes['attract'].active)
        self.packets()
        # Cover two complete rotations through the speech selector, not only
        # the first two non-speech intervals.
        for _ in range(6):
            self.advance_time_and_run(self.speech.ATTRACT_ROTATION + 0.001)
            self.assertEqual([], [p for p in self.packets()
                                  if p['action'] == 'request'])

    def test_attract_can_be_reenabled_and_gameplay_is_suppressed(self):
        self.packets()
        for event in ('mltp_lanes_done', 'fire_qualifier_lit_complete',
                      'collect_special', 'multiball_firepower_started',
                      'collect_firepower_bonus_10000', 'tilt'):
            self.post_event(event)
        self.assertEqual([], self.voices())
        self.speech.config['mode_settings']['attract_speech'] = True
        self.post_event('mode_attract_started')
        for expected in ([], [], [0x1b]):
            self.advance_time_and_run(self.speech.ATTRACT_ROTATION + 0.001)
            self.assertEqual(expected, self.voices())
        self.speech.config['mode_settings']['attract_speech'] = False
        self.advance_time_and_run(self.speech.ATTRACT_ROTATION + 1)
        self.assertEqual([], self.voices())

    def test_no_ball_start_lock_capture_drain_match_or_replay_voice(self):
        self.start()
        for event in ('ball_started', 'multiball_lock_firepower_lock_1_locked_ball',
                      'ball_drain', 'replay_awarded', 'match_no_match'):
            self.post_event(event)
        self.advance_time_and_run(3)
        self.assertEqual([], self.voices())

    def test_tilt_cancels_future_words_but_speaks_destroyed(self):
        self.start()
        self.post_event('multiball_firepower_started')
        self.voices()
        self.post_event('tilt')
        self.assertEqual([0x07], self.voices())
        self.advance_time_and_run(4)
        self.assertEqual([], self.voices())

    def test_game_end_random_and_teardown_sync_do_not_replay(self):
        self.start()
        self.post_event('game_ended')
        self.assertEqual([0x1b], self.voices())
        self.post_event('firepower_speech_sync')
        self.assertEqual(['start'], [p['action'] for p in self.packets()])
        self.speech.stop()
        self.advance_time_and_run(0)
        self.assertEqual(['stop'], [p['action'] for p in self.packets()])
        self.advance_time_and_run(5)
        self.assertEqual([], self.voices())

    def test_electronics_are_observed_without_extra_electronic_requests(self):
        self.start()
        self.hit_and_release_switch('s_left_slingshot')
        self.advance_time_and_run(1)
        self.assertEqual([5], [p['raw_command'] for p in self.packets()
                               if p['action'] == 'request'])
