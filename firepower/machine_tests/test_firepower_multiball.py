"""Characterization tests for Firepower's three physical-ball multiball."""

from mpf.tests.MpfMachineTestCase import MpfMachineTestCase


class FirepowerMultiballTest(MpfMachineTestCase):
    """Exercise production configuration on MPF's smart-virtual platform."""

    def get_enable_plugins(self):
        """The media controller is not required for machine-side rule tests."""
        return False

    def _start_single_ball_game(self):
        for switch in ("s_trough1", "s_trough2", "s_trough3"):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self.assertNumBallsKnown(3)

        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)
        # The shooter lane is a mechanical eject. Simulate the player plunge.
        if self.machine.switch_controller.is_active(self.machine.switches["s_plunger"]):
            self.release_switch_and_run("s_plunger", 1)
        self.hit_and_release_switch("s_spinner")
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.assertBallsOnPlayfield(1)

    def _lock_ball(self, number):
        self.post_event("qualify_lock_{}".format(number))
        lock_device = self.machine.ball_devices["bd_lock{}".format(number)]
        self.machine.default_platform.add_ball_to_device(lock_device)
        self.advance_time_and_run(2)
        if self.machine.switch_controller.is_active(self.machine.switches["s_plunger"]):
            self.release_switch_and_run("s_plunger", 0.1)
            self.hit_and_release_switch("s_spinner")
            self.advance_time_and_run(1)

    def test_machine_has_exactly_three_balls(self):
        self.assertEqual(3, self.machine.config["machine"]["balls_installed"])
        self.assertEqual(3, self.machine.config["machine"]["min_balls"])

    def test_physical_locks_are_one_ball_devices(self):
        for number in (1, 2, 3):
            device = self.machine.ball_devices["bd_lock{}".format(number)]
            switches = device.ball_count_handler.counter.config["ball_switches"]
            self.assertEqual(1, len(switches))

    def test_first_two_locks_replace_the_captured_ball(self):
        self._start_single_ball_game()
        for number, trough_remaining in ((1, 1), (2, 0)):
            self._lock_ball(number)
            self.assertEqual(1, self.machine.ball_devices[f"bd_lock{number}"].balls)
            self.assertEqual(trough_remaining, self.machine.ball_devices["bd_trough"].balls)
            self.assertBallsOnPlayfield(1)
            self.assertEqual(1, self.machine.game.balls_in_play)
            self.assertNumBallsKnown(3)

    def test_third_lock_does_not_request_a_fourth_ball(self):
        config = self.machine.modes["lock_qualification"].config["multiball_locks"]
        self.assertEqual(0, config["firepower_lock_3"]["balls_to_replace"])

    def test_multiball_uses_all_three_physical_locks(self):
        config = self.machine.modes["firepower_multiball"].config["multiballs"]["firepower"]
        self.assertEqual(
            ["bd_lock1", "bd_lock2", "bd_lock3"],
            [device.name for device in config["ball_locks"]],
        )

    def test_multiball_has_no_default_shoot_again(self):
        config = self.machine.modes["firepower_multiball"].config["multiballs"]["firepower"]
        self.assertEqual(0, config["shoot_again"].evaluate([]))

    def test_release_show_is_connected_to_multiball_start(self):
        config = self.machine.modes["firepower_multiball"].config
        show_player = config.get("show_player", {})
        self.assertIn("multiball_firepower_started", show_player)
        self.assertEqual(
            ["firepower_multiball_release"],
            [str(show_key).split("-", 1)[0]
             for show_key in show_player["multiball_firepower_started"]],
        )

    def test_release_callouts_are_fire_one_two_three(self):
        show = self.machine.shows["firepower_multiball_release"]
        callouts = []
        for step in show.show_steps:
            for event in step.get("events", []):
                if event.startswith("play_") and event.endswith("_sound"):
                    callouts.append(event)
        self.assertEqual(
            ["play_fire_sound", "play_one_sound", "play_two_sound", "play_three_sound"],
            callouts,
        )

    def test_release_presentation_does_not_control_physical_ejects(self):
        self._start_single_ball_game()
        speech_events = []

        for event in ("play_fire_sound", "play_one_sound", "play_two_sound",
                      "play_three_sound"):
            self.machine.events.add_handler(
                event,
                lambda spoken_event=event, **kwargs: speech_events.append(spoken_event),
            )
        for number in (1, 2, 3):
            self.mock_event("eject_firepower_lock_{}".format(number))

        self._lock_ball(1)
        self._lock_ball(2)
        self._lock_ball(3)
        self.advance_time_and_run(3)

        self.assertEqual(
            ["play_fire_sound", "play_one_sound", "play_two_sound", "play_three_sound"],
            speech_events,
        )
        self.assertEqual(1, speech_events.count("play_fire_sound"))
        for number in (1, 2, 3):
            self.assertEventNotCalled("eject_firepower_lock_{}".format(number))
            self.assertEqual(0, self.machine.ball_devices["bd_lock{}".format(number)].balls)
        self.assertBallsOnPlayfield(3)

    def test_three_lock_sequence_starts_one_three_ball_multiball(self):
        self._start_single_ball_game()
        self.mock_event("multiball_firepower_started")
        self.mock_event("balldevice_bd_trough_ball_eject_attempt")
        self.mock_event("ball_search_started")
        self.mock_event("unexpected_ball_on_playfield")

        self._lock_ball(1)
        self.assertEqual(1, self.machine.ball_devices["bd_lock1"].balls)
        self.assertEqual(1, self.machine.multiball_locks["firepower_lock_1"].locked_balls)
        self.assertBallsOnPlayfield(1)
        first_replacements = self._events["balldevice_bd_trough_ball_eject_attempt"]
        self.assertGreater(first_replacements, 0)

        self._lock_ball(2)
        self.assertEqual(1, self.machine.ball_devices["bd_lock2"].balls)
        self.assertEqual(1, self.machine.multiball_locks["firepower_lock_2"].locked_balls)
        self.assertBallsOnPlayfield(1)
        second_replacements = self._events["balldevice_bd_trough_ball_eject_attempt"]
        self.assertGreater(second_replacements, first_replacements)

        self._lock_ball(3)
        self.assertEventCalled("multiball_firepower_started", 1)
        self.assertEqual(second_replacements,
                         self._events["balldevice_bd_trough_ball_eject_attempt"])

        for number in (1, 2, 3):
            self.assertEqual(0, self.machine.ball_devices["bd_lock{}".format(number)].balls)
            self.assertEqual(
                0,
                self.machine.multiball_locks["firepower_lock_{}".format(number)].locked_balls,
            )
        self.assertEqual(3, self.machine.game.balls_in_play)
        self.assertBallsOnPlayfield(3)
        self.assertNumBallsKnown(3)
        self.assertEventNotCalled("ball_search_started")
        self.assertEventNotCalled("unexpected_ball_on_playfield")
