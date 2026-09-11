"""Lock presentation tests using real smart-virtual ball captures."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class LockLampsTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game
    _lock_ball = test_firepower_multiball.FirepowerMultiballTest._lock_ball

    def _shows(self):
        return self.machine.show_player._get_instance_dict("lock_qualification")

    def _blinking(self, number):
        light = self.machine.lights["l_lock_{}_arrow".format(number)]
        colors = []
        for _ in range(10):
            self.advance_time_and_run(0.1)
            colors.append(light.get_color())
        self.assertIn(light.config["default_on_color"], colors)
        self.assertIn((0, 0, 0), [tuple(color.rgb) for color in colors])

    def _steady(self, number):
        self.assertNotIn("lock_{}_ready_show".format(number), self._shows())
        self.assertIn("lock_{}_locked_show".format(number), self._shows())
        for _ in range(6):
            self.advance_time_and_run(0.1)
            self.assertLightColor("l_lock_{}_arrow".format(number), self.machine.lights["l_lock_{}_arrow".format(number)].config["default_on_color"])

    def test_capture_and_requalification(self):
        self._start_single_ball_game()
        for number in (1, 2, 3):
            self.post_event("qualify_lock_{}".format(number))
            self.assertIn("lock_{}_ready_show".format(number), self._shows())
            self._blinking(number)
        self._lock_ball(1)
        self._steady(1)
        self._blinking(2)
        self._blinking(3)
        self.post_event("qualify_lock_1")
        self._steady(1)

    def test_second_lock_capture_stops_blink(self):
        self._start_single_ball_game()
        self._lock_ball(2)
        self._steady(2)
        self.post_event("qualify_lock_2")
        self._steady(2)

    def test_held_lamp_survives_next_ball(self):
        self._start_single_ball_game()
        self._lock_ball(1)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
        self.advance_time_and_run(8)
        self.assertEqual(2, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.ball_devices["bd_lock1"].balls)
        self._steady(1)

    def test_all_locks_capture_and_multiball_clears_shows(self):
        self._start_single_ball_game()
        # Capture 3 before the final lock so its steady state is observable.
        for number in (3, 1):
            self._lock_ball(number)
            self._steady(number)
        self._lock_ball(2)
        self.assertTrue(self.machine.multiballs["firepower"].balls_live_target)
        for number in (1, 2, 3):
            self.assertNotIn("lock_{}_ready_show".format(number), self._shows())
            self.assertNotIn("lock_{}_locked_show".format(number), self._shows())
            self.assertLightColor("l_lock_{}_arrow".format(number), "black")
            self.assertEqual(0, self.machine.ball_devices["bd_lock{}".format(number)].balls)
