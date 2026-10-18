"""Actual Start light and underlying lamp-driver output across game lifecycle."""
from unittest.mock import patch
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class StartButtonLampTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins

    def _assert_lamp(self, flashing):
        self.advance_time_and_run(0.06)
        colors, driver_states = [], []
        for _ in range(40):
            self.advance_time_and_run(0.02)
            colors.append(tuple(self.machine.lights["l_start_button"].get_color()))
            driver_states.append(self.machine.coils["l_start_button"].hw_driver.state)
        self.assertIn((0, 0, 0), colors)
        self.assertIn("disabled", driver_states)
        if flashing:
            self.assertTrue(any(any(color) for color in colors))
            self.assertIn("enabled", driver_states)
        else:
            self.assertEqual({(0, 0, 0)}, set(colors))
            self.assertEqual({"disabled"}, set(driver_states))
            self.assertEqual([], self.machine.lights["l_start_button"].stack)

    def _start(self, players=1):
        for switch in ("s_trough1", "s_trough2", "s_trough3"):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self._assert_lamp(True)
        show = self.machine.modes["start_button_lamp"].flash
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)
        self.assertEqual(1, self.machine.ball_devices["bd_plunger_lane"].balls)
        self.assertIs(show, self.machine.modes["start_button_lamp"].flash)
        self._assert_lamp(True)
        for _ in range(players - 1):
            self.hit_and_release_switch("s_start_button")
            self.advance_time_and_run(0.1)
            self._assert_lamp(True)
        self.assertEqual(players, self.machine.game.num_players)

    def _launch(self):
        self.release_switch_and_run("s_plunger", 0.1)
        self.hit_and_release_switch("s_spinner")
        self.advance_time_and_run(0.3)
        self._assert_lamp(False)

    def _drain(self):
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
        self.advance_time_and_run(5)

    def test_first_launch_extra_ball_later_ball_and_next_game(self):
        self._start()
        self._launch()
        # Return to shooter later: an occupied/released switch cannot re-arm.
        self.hit_switch_and_run("s_plunger", 0.2)
        self._assert_lamp(False)
        self.release_switch_and_run("s_plunger", 0.2)
        self._assert_lamp(False)
        self.machine.game.player.extra_balls = 1
        self._drain()
        self.assertEqual(1, self.machine.game.player.ball)
        self._assert_lamp(False)
        self._launch()
        self._drain()
        self.assertEqual(2, self.machine.game.player.ball)
        self._assert_lamp(False)
        self._launch()
        self.machine.game.end_game()
        self._drain()
        self.assertFalse(self.machine.game)
        self._assert_lamp(True)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self._assert_lamp(True)
        self._launch()

    def test_four_players_before_launch_and_turn_transitions(self):
        self._start(4)
        for number in range(1, 5):
            self.assertEqual(number, self.machine.game.player.number)
            if number > 1:
                self._assert_lamp(False)
            self._launch()
            self._drain()
        self.assertEqual(2, self.machine.game.player.ball)
        self._assert_lamp(False)

    def test_launch_without_settled_shooter_entry(self):
        # Cabinet trace: short shooter contacts never satisfy entrance_count_delay,
        # then MPF confirms the skipped mechanical device on playfield activity.
        for switch in ("s_trough1", "s_trough2", "s_trough3"):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        entered = "balldevice_bd_plunger_lane_ball_entered"
        success = "balldevice_bd_plunger_lane_ball_eject_success"
        self.mock_event(entered)
        self.mock_event(success)
        with patch.object(self.machine.coils["c_trough_eject"], "pulse"):
            self.hit_and_release_switch("s_start_button")
            self.advance_time_and_run(0.3)
            self.release_switch_and_run("s_trough1", 0.1)
            for _ in range(4):
                self.hit_switch_and_run("s_plunger", 0.02)
                self.release_switch_and_run("s_plunger", 0.03)
            self._assert_lamp(True)
            self.advance_time_and_run(3)
            self.assertEventNotCalled(entered)
            self.assertEventNotCalled(success)
            self._assert_lamp(True)
            self.hit_and_release_switch("s_lane_e")
            self.advance_time_and_run(0.3)
            self.assertEventCalled(success)
            self.assertEventNotCalled(entered)
            self._assert_lamp(False)

    def test_unarmed_shooter_release_does_not_stop_attract_flash(self):
        self.advance_time_and_run(2)
        self.hit_and_release_switch("s_plunger")
        self.advance_time_and_run(0.1)
        self._assert_lamp(True)
