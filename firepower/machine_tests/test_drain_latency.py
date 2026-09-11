"""Simulated drain timing; physical travel and FAST transport need verification."""
from unittest.mock import patch
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class DrainLatencyTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game
    _lock_ball = test_firepower_multiball.FirepowerMultiballTest._lock_ball

    def _trace(self):
        self.trace = []
        for event in ('balldevice_bd_drain_ball_enter', 'balldevice_bd_drain_ball_entered',
                      'balldevice_bd_drain_ball_eject_attempt', 'balldevice_bd_drain_ejecting_ball'):
            self.machine.events.add_handler(event, self._record, label=event)
        driver = self.machine.coils['c_drain_eject'].hw_driver
        original = type(driver).pulse

        def pulse(instance, *args, **kwargs):
            if instance is driver:
                self._record('coil')
            return original(instance, *args, **kwargs)
        self.patcher = patch.object(type(driver), 'pulse', pulse)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _record(self, label, **kwargs):
        self.assertLessEqual(self.machine.ball_devices["bd_drain"].balls, 1)
        self.trace.append((label, self.machine.clock.get_time()))

    def test_single_drain_clears_before_bonus_finishes(self):
        self._start_single_ball_game()
        self.machine.game.player.bonus_value = 39
        self.machine.game.player.bonus_multiplier = 5
        self._trace()
        start = self.machine.clock.get_time()
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(0.8)
        pulses = [t for label, t in self.trace if label == 'coil']
        print('DRAIN_TIMELINE', [(label, round(t-start, 4)) for label, t in self.trace])
        self.assertEqual(1, len(pulses))
        self.assertLessEqual(pulses[0] - start, 0.060)
        self.assertTrue(self.machine.modes['bonus_collect'].active)
        self.advance_time_and_run(2)
        self.assertEqual(3, self.machine.ball_devices['bd_trough'].balls)
        self.assertEqual(0, self.machine.ball_devices['bd_drain'].balls)
        self.assertEqual(1, sum(label == 'coil' for label, _ in self.trace))
        self.advance_time_and_run(27)
        self.assertEqual(2, self.machine.game.player.ball)

    def test_rapid_multiball_drains(self):
        self._start_single_ball_game()
        for number in (1, 2, 3):
            self._lock_ball(number)
        self.assertBallsOnPlayfield(3)
        self._trace()
        drain = self.machine.ball_devices['bd_drain']
        self.machine.default_platform.add_ball_to_device(drain)
        self.advance_time_and_run(0.2)
        self.assertEqual(1, sum(label == 'coil' for label, _ in self.trace))
        self.assertFalse(self.machine.switch_controller.is_active(self.machine.switches['s_drain']))
        self.machine.default_platform.add_ball_to_device(drain)
        self.advance_time_and_run(3)
        self.assertEqual(2, sum(label == 'coil' for label, _ in self.trace))
        self.assertEqual(0, drain.balls)
        self.assertEqual(2, self.machine.ball_devices['bd_trough'].balls)
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.assertBallsOnPlayfield(1)
        self.assertNumBallsKnown(3)

    def test_short_switch_bounce_is_not_counted(self):
        self._start_single_ball_game()
        self._trace()
        self.hit_switch_and_run('s_drain', 0.02)
        self.release_switch_and_run('s_drain', 0.1)
        self.assertEqual([], self.trace)
        self.assertEqual(0, self.machine.ball_devices['bd_drain'].balls)
        self.assertEqual(1, self.machine.game.balls_in_play)
