"""Verify real MPF sound-player commands at the GMC/BCP boundary."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class GameplaySoundsTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def _sound_commands(self):
        queue = self.machine.bcp.transport.get_named_client('local_display').send_queue
        sounds = []
        while not queue.empty():
            command, payload = queue.get_nowait()
            if command == 'trigger' and payload.get('name') == 'sounds_play':
                sounds.extend((name, settings['bus']) for name, settings in payload['settings'].items())
            elif command == 'trigger' and payload.get('name') == 'firepower_electronic' and payload['action'] == 'play':
                sounds.append((payload['raw_command'], 'effects'))
        return sounds

    def _exercise_switches(self, playing):
        cases = [('s_pop_bumper_1', [10]), ('s_lane_f', [9, 11]),
                 ('s_spinner', [10]), ('s_left_upper_bumper', [5] * 5),
                 ('s_arrow_1', [16] * 10 + [11]), ('s_plunger', [])]
        for switch, sounds in cases:
            with self.subTest(switch=switch, playing=playing):
                self.advance_time_and_run(3)
                self._sound_commands()
                self.mock_event(f'{switch}_active')
                self.hit_and_release_switch(switch)
                self.advance_time_and_run(3)
                self.assertEventCalled(f'{switch}_active', 1)
                self.assertEqual([(sound, 'effects') for sound in sounds] if playing else [], self._sound_commands())

    def test_switch_sounds_follow_game_lifecycle(self):
        self.assertFalse(self.machine.game)
        self.assertTrue(self.machine.modes['attract'].active)
        self._exercise_switches(False)
        self._start_single_ball_game()
        self._exercise_switches(True)
        self.machine.game.player.bonus_value = 0
        # This test checks legacy attract audio; Match-specific sound has its
        # own deterministic coverage, so select a non-winning phase here.
        self.machine.modes['firepower_match'].phase_source = lambda: 0x90
        self.machine.game.end_game()
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.game)
        self.assertTrue(self.machine.modes['attract'].active)
        self.assertEqual([('FP11', 'effects')], self._sound_commands())
        self._exercise_switches(False)

    def test_attract_start_keeps_intentional_audio(self):
        self.assertFalse(self.machine.game)
        self.assertEqual([('FP11', 'effects')], self._sound_commands())
