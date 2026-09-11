"""Logical display regression tests and installed FAST payload characterization.

These tests capture MPF's real encoder output; they do not emulate FAST firmware.
"""
from types import SimpleNamespace

from mpf.platforms.fast.fast_segment_display import FASTSegmentDisplay
from mpf.platforms.fast.communicators.seg import FastSegCommunicator
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class SegmentDisplaysTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def _payload(self, display):
        commands = []
        hardware = FASTSegmentDisplay(int(display.config["number"]), None)
        state = display._current_state
        hardware.set_text(state.text, state.flashing, state.flash_mask)
        transport = SimpleNamespace(platform=SimpleNamespace(fast_segs=[hardware]),
                                    send_and_forget=commands.append)
        FastSegCommunicator._update_segs(transport)
        return commands

    def _assert_score(self, number, score):
        display = self.machine.segment_displays["player{}_display".format(number)]
        self.assertEqual(7, len(display._current_state.text))
        self.assertEqual(str(score)[-1], chr(display._current_state.text[-1].char_code))
        self.assertEqual(score, int(display.text.replace(",", "").strip()))
        self.assertEqual({}, display._text_stack)
        return display

    def test_all_four_logical_widths_and_fast_payload_characterization(self):
        self._start_single_ball_game()
        for number in range(1, 5):
            display = self.machine.segment_displays["player{}_display".format(number)]
            display.add_text("12,345")
            self._assert_score(number, 12345)
            self.assertEqual("  12,345", display.text)
            # Embedded punctuation must not truncate the seven logical cells.
            address = "{:02X}".format((number - 1) * 7)
            self.assertEqual("PA:{},  12,345".format(address), self._payload(display)[0])
            display.add_text("1234567")
            self.assertEqual("PA:{},1234567".format(address), self._payload(display)[0])

    def test_real_ball_transition_flash_and_later_scores(self):
        self._start_single_ball_game()
        self.machine.game.player.score = 12345
        self.advance_time_and_run(0.01)
        display = self._assert_score(1, 12345)
        self.assertEqual("PA:00,  12,345", self._payload(display)[0])
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
        self.advance_time_and_run(5)
        self.assertEqual(2, self.machine.game.player.ball)
        colors = []
        for _ in range(40):
            self.advance_time_and_run(0.01)
            self.assertEqual(7, len(display._current_state.text))
            colors.append(display.text)
        self.assertIn("       ", colors)  # software show blanks all seven positions
        self.assertIn("  12,345", colors)
        self.machine.game.player.score = 12346
        self.advance_time_and_run(0.01)
        self._assert_score(1, 12346)
        self.assertEqual("PA:00,  12,346", self._payload(display)[0])
        self.advance_time_and_run(1)
        self._assert_score(1, 12346)  # scoreFlash really stopped
        self.machine.game.player.score = 123
        self.advance_time_and_run(0.01)
        self.assertEqual("PA:00,    123", self._payload(self._assert_score(1, 123))[0])
        self.assertEqual(6, len(self.machine.segment_displays["credit_ball_display"]._current_state.text))

    def test_later_game_score_refresh_restores_logical_digits_without_process_restart(self):
        self._start_single_ball_game()
        self.machine.game.player.score = 12345
        self.advance_time_and_run(0.01)
        self.machine.game.end_game()
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.game)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)
        self.assertEqual(0, self.machine.game.player.score)
        # The persistent player-added show is already running with the same
        # config, so it does not rewrite zero in the later game (separate finding).
        self._assert_score(1, 12345)
        self.machine.game.player.score = 123
        self.advance_time_and_run(0.01)
        display = self._assert_score(1, 123)
        self.assertEqual("PA:00,    123", self._payload(display)[0])

    def test_opt_in_trace_observes_without_changing_display(self):
        from unittest.mock import patch
        from diagnostics.display_trace import DisplayTrace
        from mpf.devices.segment_display.segment_display import SegmentDisplay
        original = SegmentDisplay._update_display
        self.addCleanup(setattr, SegmentDisplay, "_update_display", original)
        trace = DisplayTrace(self.machine, "test_display_trace")
        with patch.object(trace, "info_log") as log:
            trace._start()
            display = self.machine.segment_displays["player1_display"]
            display.add_text("12345")
            self.assertEqual("  12345", display.text)
            self.assertTrue(any("display_update" in call.args for call in log.call_args_list))
