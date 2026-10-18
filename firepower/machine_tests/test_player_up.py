"""Player Up lamps: production shows/lights and real game/ball lifecycles."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class PlayerUpTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins

    def _lamps(self):
        return [self.machine.lights[f"l_player_{n}_score_indicator"] for n in range(1, 5)]

    def _assert_indication(self, number, flashing):
        samples = []
        for _ in range(40):
            self.advance_time_and_run(0.02)
            colors = [lamp.get_color() for lamp in self._lamps()]
            for n, color in enumerate(colors, 1):
                if n != number:
                    self.assertEqual((0, 0, 0), tuple(color))
            samples.append(tuple(colors[number - 1]))
        self.assertTrue(any(any(color) for color in samples))
        if flashing:
            self.assertIn((0, 0, 0), samples)
        else:
            self.assertNotIn((0, 0, 0), samples)
            self.assertEqual(1, len(set(samples)))

    def _assert_attract_off(self):
        self.assertFalse(self.machine.game)
        self.assertTrue(self.machine.modes["attract"].active)
        self.assertFalse(self.machine.modes["player_up"].active)
        # Allow the existing 40 ms fade, then observe multiple flash periods.
        self.advance_time_and_run(0.05)
        for _ in range(50):
            self.advance_time_and_run(0.02)
            for lamp in self._lamps():
                self.assertEqual((0, 0, 0), tuple(lamp.get_color()))
                self.assertEqual([], lamp.stack)

    def _start(self, players=1):
        for switch in ("s_trough1", "s_trough2", "s_trough3"):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self._assert_attract_off()
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        for _ in range(players - 1):
            self.hit_and_release_switch("s_start_button")
            self.advance_time_and_run(0.1)
        self.assertEqual(players, self.machine.game.num_players)
        self.assertEqual(0, self.machine.game.player.score)

    def _score(self):
        if self.machine.switch_controller.is_active(self.machine.switches["s_plunger"]):
            self.release_switch_and_run("s_plunger", 0.1)
        self._assert_indication(self.machine.game.player.number, True)
        self.hit_and_release_switch("s_spinner")
        self.advance_time_and_run(0.1)
        self._assert_indication(self.machine.game.player.number, False)

    def _drain(self):
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
        self.advance_time_and_run(5)

    def test_single_player_non_scoring_extra_ball_and_attract_cleanup(self):
        self._start()
        self._assert_indication(1, True)
        for switch in ("s_flipper_left", "s_flipper_right"):
            self.hit_and_release_switch(switch)
        self.post_event("tilt_warning")
        self.advance_time_and_run(0.1)
        self._assert_indication(1, True)
        self._score()
        for _ in range(3):
            self.hit_and_release_switch("s_spinner")
            self.advance_time_and_run(0.1)
        self._assert_indication(1, False)
        # Exercise MPF's existing extra-ball lifecycle without adding award rules.
        self.machine.game.player.extra_balls = 1
        self._drain()
        self.assertEqual(1, self.machine.game.player.ball)
        self._assert_indication(1, True)
        self._score()
        self._drain()
        self.assertEqual(2, self.machine.game.player.ball)
        self._assert_indication(1, True)
        self._score()
        self.machine.game.end_game()
        self._drain()
        self._assert_attract_off()
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self._assert_indication(1, True)
        self._score()

    def test_game_ended_stops_active_flash(self):
        self._start()
        self._assert_indication(1, True)
        flash = self.machine.modes["player_up"].flash
        test_firepower_multiball.plunge_without_scoring(self)
        self.machine.game.end_game()
        self.advance_time_and_run(0.1)
        self.assertTrue(flash.stopped)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(5)
        self._assert_attract_off()

    def _multiplayer(self, players):
        self._start(players)
        for number in range(1, players + 1):
            self.assertEqual(number, self.machine.game.player.number)
            self._assert_indication(number, True)
            self._score()
            self._drain()
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(2, self.machine.game.player.ball)
        self._assert_indication(1, True)

    def test_two_players(self):
        self._multiplayer(2)

    def test_three_players(self):
        self._multiplayer(3)

    def test_four_players(self):
        self._multiplayer(4)
