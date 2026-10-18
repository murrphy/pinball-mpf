"""Machine-lifetime coin lamps; no game/mode owns this driver."""
from unittest.mock import patch
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class CoinLampsTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def _assert_on(self):
        self.assertEqual("enabled", self.machine.coils["l_coin_lamps"].hw_driver.state)

    def test_startup_game_ball_bonus_and_game_end_do_not_retrigger(self):
        lamp = self.machine.coils["l_coin_lamps"]
        self._assert_on()
        self.assertTrue(self.machine.modes["attract"].active)
        self.assertEqual(0, lamp.get_and_verify_pulse_ms(None))
        self.assertEqual(1.0, lamp.get_and_verify_hold_power(None))
        with patch.object(lamp, "enable", wraps=lamp.enable) as enable, \
                patch.object(lamp, "disable", wraps=lamp.disable) as disable, \
                patch.object(lamp, "pulse", wraps=lamp.pulse) as pulse:
            self.advance_time_and_run(5)
            self._assert_on()
            self._start_single_ball_game()
            self._assert_on()
            self.machine.game.player.bonus_value = 2
            self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
            self.advance_time_and_run(5)
            self.assertEqual(2, self.machine.game.player.ball)
            self._assert_on()
            test_firepower_multiball.plunge_without_scoring(self)
            self.machine.game.end_game()
            self.machine.default_platform.add_ball_to_device(self.machine.ball_devices["bd_drain"])
            self.advance_time_and_run(5)
            self.assertFalse(self.machine.game)
            self._assert_on()
            enable.assert_not_called()
            disable.assert_not_called()
            pulse.assert_not_called()

    def test_service_entry_exit_and_reset_keep_driver_enabled(self):
        lamp = self.machine.coils["l_coin_lamps"]
        self._assert_on()
        with patch.object(lamp, "enable", wraps=lamp.enable) as enable, \
                patch.object(lamp, "disable", wraps=lamp.disable) as disable, \
                patch.object(lamp, "pulse", wraps=lamp.pulse) as pulse:
            self.machine.service.start_service()
            self.advance_time_and_run(1)
            self.assertTrue(self.machine.service.is_in_service())
            self._assert_on()
            self.machine.clock.loop.run_until_complete(self.machine.service.stop_service())
            self.advance_time_and_run(2)
            self.assertFalse(self.machine.service.is_in_service())
            self._assert_on()
            enable.assert_not_called()
            disable.assert_not_called()
            pulse.assert_not_called()
