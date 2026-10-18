"""Exercise authoritative FP03 lifecycle and actual MPF-to-GMC BCP packets."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class BackgroundAudioTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game
    _lock_ball = test_firepower_multiball.FirepowerMultiballTest._lock_ball

    def _packets(self):
        queue = self.machine.bcp.transport.get_named_client('local_display').send_queue
        packets = []
        while not queue.empty():
            command, payload = queue.get_nowait()
            if command == 'trigger' and payload.get('name') == 'firepower_background':
                packets.append(payload)
        return packets

    def _assert_start(self, packets):
        starts = [p for p in packets if p['action'] == 'start']
        self.assertEqual(1, len(starts))
        self.assertEqual(1, starts[0]['stage'])
        self.assertEqual(self.machine.modes['background_audio'].config['mode_settings']['minimum_rate'], starts[0]['rate'])
        return starts[0]

    @property
    def bg(self):
        return self.machine.modes['background_audio']

    def _fresh_ball(self):
        for switch in ('s_trough1', 's_trough2', 's_trough3'):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)

    def _advance_ticks(self, ticks):
        self.advance_time_and_run(ticks * self.bg.TICK_SECONDS)

    def test_fresh_ball_activation_and_idle_opportunity(self):
        self.hit_and_release_switch('s_spinner')
        self.assertEqual([], self._packets())
        self._fresh_ball()
        self._assert_start(self._packets())
        self.assertIsNone(self.bg.eligible_since)
        self.advance_time_and_run(12)
        self.hit_and_release_switch('s_plunger')
        self.hit_and_release_switch('s_flipper_right')
        self.machine.game.player.score += 50000
        self.advance_time_and_run(0)
        self.assertEqual(0, self.bg.counter)
        self.assertEqual([], self._packets())
        self.hit_and_release_switch('s_spinner')
        self.assertIsNotNone(self.bg.eligible_since)
        self._advance_ticks(257)
        self.assertEqual(1, self.bg.stage)
        self.assertEqual([], self._packets())
        self.hit_and_release_switch('s_pop_bumper_1')
        self.assertEqual(2, self.bg.stage)
        self.assertEqual(1, self.bg.reference)
        self.assertEqual(['rate'], [p['action'] for p in self._packets()])
        self._advance_ticks(800)
        self.assertEqual(2, self.bg.stage)
        self.machine.game.player.score += 100
        self.advance_time_and_run(0)
        self.assertEqual([], self._packets())
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(3, self.bg.stage)
        self.assertEqual(4, self.bg.reference)
        self.assertEqual(1, len(self._packets()))

    def test_exact_cadence_short_wrap_and_equal_reference(self):
        self._fresh_ball()
        self.hit_and_release_switch('s_spinner')
        self.assertAlmostEqual(4.24756554, 256 * self.bg.TICK_SECONDS, places=7)
        self.assertAlmostEqual(2.38925562, 144 * self.bg.TICK_SECONDS, places=7)
        self._advance_ticks(255.5)
        self.assertEqual(0, self.bg.counter >> 8)
        self._advance_ticks(1)
        self.assertEqual(1, self.bg.counter >> 8)
        self.hit_and_release_switch('s_spinner')
        self._advance_ticks(3072)
        self.assertEqual(13, self.bg.counter >> 8)
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(13, self.bg.reference)
        self._advance_ticks(143)
        self.assertEqual(13, self.bg.counter >> 8)
        self._advance_ticks(1)
        self.assertEqual(0, self.bg.counter >> 8)
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(0, self.bg.reference)
        stage = self.bg.stage
        self._advance_ticks(3472)
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(stage, self.bg.stage)

    def test_award_gate_defers_reference_until_later_gameplay(self):
        self._fresh_ball()
        self.hit_and_release_switch('s_spinner')
        self._advance_ticks(257)
        self.post_event('collect_firepower_bonus_10000')
        self.assertIn('award', self.bg.presentations)
        self.hit_and_release_switch('s_pop_bumper_1')
        self.assertEqual(0, self.bg.reference)
        self.assertEqual(1, self.bg.stage)
        self.advance_time_and_run(1.2)
        self.assertNotIn('award', self.bg.presentations)
        self.assertEqual(1, self.bg.stage)
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(2, self.bg.stage)
        self.assertEqual(1, self.bg.reference)

    def test_award_from_same_target_blocks_deferred_check(self):
        self._fresh_ball()
        self.hit_and_release_switch('s_power_1')
        self.hit_and_release_switch('s_power_2')
        self.machine.game.player.fire_lit = 1
        self._advance_ticks(257)
        self.hit_and_release_switch('s_power_3')
        self.assertIn('award', self.bg.presentations)
        self.assertEqual(0, self.bg.reference)
        self.assertEqual(1, self.bg.stage)

    def test_all_36_stages_and_wrap(self):
        self._fresh_ball()
        self.hit_and_release_switch('s_spinner')
        previous = self.bg.rate
        for stage in range(2, 38):
            # Cross exactly the next high-byte boundary, including short wrap.
            ticks = min(((self.bg.counter >> 8) + 1) * 256, 3472) - self.bg.counter
            self._advance_ticks(ticks + 0.01)
            self.hit_and_release_switch('s_pop_bumper_1')
            expected = (stage - 1) % 36 + 1
            self.assertEqual(expected, self.bg.stage)
            if expected <= 31 and stage <= 31:
                self.assertGreater(self.bg.rate, previous)
            else:
                self.assertEqual(0.85, self.bg.rate)
            if expected == 31:
                self.assertEqual(1.25, self.bg.rate)
            previous = self.bg.rate

    def test_real_multiball_preserves_background_on_return_to_one(self):
        self._start_single_ball_game()
        for n in (1, 2):
            self._lock_ball(n)
        before = self.bg.counter
        stage, reference, cycle = self.bg.stage, self.bg.reference, self.bg.cycle
        self._packets()
        self._lock_ball(3)
        self.assertEqual(3, self.machine.game.balls_in_play)
        self.assertEqual((stage, reference, cycle), (self.bg.stage, self.bg.reference, self.bg.cycle))
        self.assertGreater(self.bg.counter, before)
        self.assertIn('release', self.bg.presentations)
        self.hit_and_release_switch('s_pop_bumper_1')
        self.assertEqual(stage, self.bg.stage)
        for remaining in (2, 1):
            self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
            self.advance_time_and_run(2)
            self.assertEqual(remaining, self.machine.game.balls_in_play)
            self.assertEqual((stage, reference, cycle), (self.bg.stage, self.bg.reference, self.bg.cycle))
        self.assertEqual([], self._packets())
        self.assertNotIn('release', self.bg.presentations)
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(stage + 1, self.bg.stage)

    def test_timer_reference_persist_across_ball_and_player(self):
        self._start_single_ball_game()
        self.hit_and_release_switch('s_start_button')  # Add player two.
        self._advance_ticks(257)
        self.hit_and_release_switch('s_spinner')
        self.assertNotEqual(0, self.bg.reference)
        self.machine.game.player.bonus_value = 10
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(0.2)
        self.assertEqual(0, self.bg.stage)
        phase, reference = self.bg.counter, self.bg.reference
        self.advance_time_and_run(6)
        self.assertEqual(2, self.machine.game.player.number)
        self.assertEqual(1, self.bg.stage)
        self.assertEqual((phase, reference), (self.bg.counter, self.bg.reference))
        self.advance_time_and_run(8)
        self.assertEqual(phase, self.bg.counter)

    def test_tilt_bg_end_once_preserves_phase(self):
        self._start_single_ball_game()
        self._advance_ticks(257)
        self.hit_and_release_switch('s_spinner')
        phase, reference = self.bg.counter, self.bg.reference
        self._packets()
        self.post_event('tilt')
        self.assertEqual(['stop'], [p['action'] for p in self._packets()])
        self.post_event('tilt')
        self.hit_and_release_switch('s_spinner')
        self.advance_time_and_run(2)
        self.assertEqual([], self._packets())
        self.assertEqual(0, self.bg.stage)
        self.assertEqual((phase, reference), (self.bg.counter, self.bg.reference))

    def test_normal_next_ball_keeps_partial_phase_and_reference(self):
        self._start_single_ball_game()
        self._advance_ticks(257)
        self.hit_and_release_switch('s_spinner')
        self.machine.game.player.bonus_value = 10
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(0.2)
        phase, reference = self.bg.counter, self.bg.reference
        self.advance_time_and_run(6)
        self.assertEqual(2, self.machine.game.player.ball)
        self.assertEqual(1, self.bg.stage)
        self.assertEqual((phase, reference), (self.bg.counter, self.bg.reference))
        self.hit_and_release_switch('s_spinner')
        self._advance_ticks(256 - phase % 256 + 1)
        self.hit_and_release_switch('s_spinner')
        self.assertEqual(2, self.bg.stage)

    def test_disabled_background_and_warning_activation(self):
        self.bg.config['mode_settings']['enabled'] = False
        self._fresh_ball()
        self.assertEqual([], self._packets())
        self.post_event('tilt_warning')
        self.assertIsNotNone(self.bg.eligible_since)
        self._advance_ticks(257)
        self.hit_and_release_switch('s_pop_bumper_1')
        self.assertEqual(0, self.bg.stage)
        self.assertEqual(0, self.bg.reference)
        self.assertEqual([], self._packets())

    def test_award_replacement_and_cancellation_do_not_leave_gate_stuck(self):
        self._start_single_ball_game()
        self.post_event('collect_firepower_bonus_10000')
        self.advance_time_and_run(0.5)
        self.post_event('collect_firepower_bonus_30000')
        self.advance_time_and_run(0.7)
        self.assertIn('award', self.bg.presentations)
        self.machine.modes['firepower_bonus'].stop()
        self.advance_time_and_run(0)
        self.assertNotIn('award', self.bg.presentations)

    def test_ball_end_bonus_next_ball_and_game_end(self):
        self._start_single_ball_game()
        first = self._assert_start(self._packets())
        self.machine.game.player.bonus_value = 10
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(0.2)
        self.assertEqual('stop', self._packets()[-1]['action'])
        self.advance_time_and_run(0.5)
        self.assertEqual([], self._packets())
        self.advance_time_and_run(5)
        next_ball = self._assert_start(self._packets())
        self.assertGreater(next_ball['cycle'], first['cycle'])
        test_firepower_multiball.plunge_without_scoring(self)
        self.machine.game.end_game()
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.game)
        self.assertEqual('stop', self._packets()[-1]['action'])
        self.hit_and_release_switch('s_spinner')
        self.assertEqual([], self._packets())
        self.post_event('firepower_background_sync')
        self.assertEqual('stop', self._packets()[-1]['action'])

    def _assert_stop_event(self, event):
        self._start_single_ball_game()
        self._packets()
        self.post_event(event)
        self.assertEqual('stop', self._packets()[-1]['action'])
        self.assertFalse(self.machine.modes['background_audio'].active)
        self.post_event('firepower_background_sync')
        self.assertEqual('stop', self._packets()[-1]['action'])

    def test_tilt_stops_background(self):
        self._assert_stop_event('tilt')

    def test_service_stops_background(self):
        self._assert_stop_event('service_mode_entered')

    def test_mode_teardown_stops_background(self):
        self._start_single_ball_game()
        self._packets()
        self.machine.modes['background_audio'].stop()
        self.advance_time_and_run(0)
        self.assertEqual('stop', self._packets()[-1]['action'])
