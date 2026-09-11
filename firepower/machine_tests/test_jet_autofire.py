"""Hardware-rule configuration and host scoring, not physical strength/heat."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from mpf.platforms.fast.fast_driver import FASTDriver
from mpf.platforms.fast.fast_switch import FASTSwitch
from machine_tests import test_firepower_multiball


class JetAutofireTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def test_rules_tuning_and_lifecycle(self):
        platform = self.machine.default_platform
        with patch.object(platform, 'set_pulse_on_hit_rule', wraps=platform.set_pulse_on_hit_rule) as install:
            self._start_single_ball_game()
        for n in range(1, 5):
            auto = self.machine.autofire_coils[f'pop_bumper_{n}']
            coil = self.machine.coils[f'c_pop_bumper_{n}']
            switch = self.machine.switches[f's_pop_bumper_{n}']
            self.assertIs(auto.config['coil'], coil)
            self.assertIs(auto.config['switch'], switch)
            self.assertTrue(auto._enabled)
            self.assertEqual('pulse_on_hit', platform.rules[(switch.hw_switch, coil.hw_driver)])
            calls = [call for call in install.call_args_list if call.args[1].hw_driver is coil.hw_driver]
            self.assertEqual(1, len(calls))
            settings, driver = calls[0].args
            self.assertIs(settings.hw_switch, switch.hw_switch)
            self.assertEqual(11, driver.pulse_settings.duration)
            self.assertTrue(driver.recycle)
            # Run the installed FAST conversion logic on the configured values.
            fake_driver = SimpleNamespace(platform_settings=coil.config['platform_settings'], log=Mock(), number=n)
            self.assertEqual('16', FASTDriver.get_recycle_ms_for_cmd(fake_driver, driver.recycle, driver.pulse_settings.duration))
            fake_switch = SimpleNamespace(communicator=SimpleNamespace(config=self.machine.config_validator.validate_config('fast_net', self.machine.config['fast']['net'])))
            debounce = FASTSwitch.reconcile_debounce(fake_switch, SimpleNamespace(debounce=switch.config['debounce']), switch.config['platform_settings'])
            self.assertEqual(('02', '02'), debounce)
            for other in range(1, 5):
                if other != n:
                    self.assertNotIn((switch.hw_switch, self.machine.coils[f'c_pop_bumper_{other}'].hw_driver), platform.rules)
        self.post_event('ball_will_end')
        for n in range(1, 5):
            auto = self.machine.autofire_coils[f'pop_bumper_{n}']
            self.assertFalse(auto._enabled)
            self.assertNotIn((auto.config['switch'].hw_switch, auto.config['coil'].hw_driver), platform.rules)

    def test_scoring_remains_single_award_per_activation(self):
        self._start_single_ball_game()
        for all_lit, award in ((0, 100), (1, 1000)):
            self.machine.game.player.jet_bumpers_all = all_lit
            for n in range(1, 5):
                before = self.machine.game.player.score
                self.hit_switch_and_run(f's_pop_bumper_{n}', 0.1)
                self.assertEqual(before + award, self.machine.game.player.score)
                self.advance_time_and_run(0.2)
                self.assertEqual(before + award, self.machine.game.player.score)
                self.release_switch_and_run(f's_pop_bumper_{n}', 0.1)
