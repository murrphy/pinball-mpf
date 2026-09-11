"""Replacement service must depend on real available balls, not lock identity."""
from unittest.mock import patch
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class LockCaptureOrdersTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def _exercise_order(self, order):
        self._start_single_ball_game()
        # Two target completions qualify all three before any capture.
        self.post_event("qualify_locks")
        self.post_event("qualify_locks")
        for number in (1, 2, 3):
            self.assertTrue(self.machine.multiball_locks[f"firepower_lock_{number}"].enabled)
        for event in ("multiball_firepower_started", "ball_search_started", "unexpected_ball_on_playfield"):
            self.mock_event(event)
        source = self.machine.ball_devices["bd_plunger_lane"]
        original_eject = type(source).eject
        with patch.object(type(source), "eject", autospec=True, side_effect=original_eject) as requests:
            for index, number in enumerate(order):
                trough = self.machine.ball_devices["bd_trough"]
                self.assertEqual(2 - index, trough.balls)
                self.assertEqual(2 - index, trough.available_balls)
                before = sum(call.args[0] is source for call in requests.call_args_list)
                self.machine.default_platform.add_ball_to_device(self.machine.ball_devices[f"bd_lock{number}"])
                self.advance_time_and_run(2)
                if index < 2:
                    self.assertEqual(before + 1, sum(call.args[0] is source for call in requests.call_args_list))
                    self.assertEqual(1, self.machine.ball_devices[f"bd_lock{number}"].balls)
                    if self.machine.switch_controller.is_active(self.machine.switches["s_plunger"]):
                        self.release_switch_and_run("s_plunger", 0.1)
                        self.hit_and_release_switch("s_spinner")
                        self.advance_time_and_run(1)
                    self.assertBallsOnPlayfield(1)
                    self.assertAvailableBallsOnPlayfield(1)
                    self.assertEqual(1, self.machine.game.balls_in_play)
                    self.assertEventNotCalled("multiball_firepower_started")
                else:
                    self.assertEqual(before, sum(call.args[0] is source for call in requests.call_args_list), "phantom fourth-ball request")
                self.assertNumBallsKnown(3)
        self.advance_time_and_run(3)
        self.assertEventCalled("multiball_firepower_started", 1)
        self.assertBallsOnPlayfield(3)
        self.assertEqual(3, self.machine.game.balls_in_play)
        for number in (1, 2, 3):
            self.assertEqual(0, self.machine.ball_devices[f"bd_lock{number}"].balls)
            self.assertEqual(0, self.machine.multiball_locks[f"firepower_lock_{number}"].locked_balls)
        self.assertEventNotCalled("ball_search_started")
        self.assertEventNotCalled("unexpected_ball_on_playfield")

    def test_order_123(self):
        self._exercise_order((1, 2, 3))

    def test_order_132(self):
        self._exercise_order((1, 3, 2))

    def test_order_213(self):
        self._exercise_order((2, 1, 3))

    def test_order_231(self):
        self._exercise_order((2, 3, 1))

    def test_order_312(self):
        self._exercise_order((3, 1, 2))

    def test_order_321(self):
        self._exercise_order((3, 2, 1))
