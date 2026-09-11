"""Insert colors and temporary per-cap jet impact ownership."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class CosmeticLightingTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def test_lock_color_matches_lit_fire_lanes(self):
        self._start_single_ball_game()
        for letter in 'fir':
            self.hit_and_release_switch(f's_lane_{letter}')
        self.advance_time_and_run(0.05)
        reference = self.machine.lights['l_lane_f'].get_color()
        self.assertEqual((243, 195, 95), tuple(reference.rgb))
        for letter in 'fire':
            self.assertEqual(reference, self.machine.lights[f'l_lane_{letter}'].config['default_on_color'])
        for n in range(1, 4):
            self.post_event(f'qualify_lock_{n}')
            self.advance_time_and_run(0.05)
            self.assertLightColor(f'l_lock_{n}_arrow', reference)

    def test_return_lanes_blue_and_award_consumed_on_either_side(self):
        self._start_single_ball_game()
        for side in ('left', 'right'):
            with self.subTest(side=side):
                before = self.machine.game.player.score
                self.hit_and_release_switch(f's_{side}_return_lane')
                self.assertEqual(before + 1000, self.machine.game.player.score)
                for n in range(1, 4):
                    self.hit_and_release_switch(f's_power_{n}')
                self.assertEqual(1, self.machine.game.player.return_lanes_lit)
                self.advance_time_and_run(0.05)
                self.assertLightColor('l_left_return_lane_3000_when_lit', 'blue')
                self.assertLightColor('l_right_return_lane_3000_when_lit', 'black')
                self.advance_time_and_run(0.25)
                self.assertLightColor('l_left_return_lane_3000_when_lit', 'black')
                self.assertLightColor('l_right_return_lane_3000_when_lit', 'blue')
                before = self.machine.game.player.score
                self.hit_and_release_switch(f's_{side}_return_lane')
                self.advance_time_and_run(0.05)
                self.assertEqual(before + 3000, self.machine.game.player.score)
                self.assertEqual(0, self.machine.game.player.return_lanes_lit)
                for lane in ('left', 'right'):
                    self.assertLightColor(f'l_{lane}_return_lane_3000_when_lit', 'black')

    def test_insert_colors_and_special_consumption(self):
        self._start_single_ball_game()
        for n in range(1, 4):
            self.post_event(f'qualify_lock_{n}')
            self.advance_time_and_run(0.05)
            self.assertLightColor(f'l_lock_{n}_arrow', 'warm_white')
        self.post_event('light_outlane_specials')
        self.advance_time_and_run(0.05)
        self.assertEqual(1, self.machine.game.player.special_lit)
        self.assertLightColor('l_left_outlane_special', 'red')
        self.advance_time_and_run(0.25)
        self.assertLightColor('l_right_outlane_special', 'red')
        self.hit_and_release_switch('s_right_out_lane')
        self.advance_time_and_run(0.1)
        self.assertEqual(0, self.machine.game.player.special_lit)
        self.assertLightColor('l_left_outlane_special', 'black')
        self.assertLightColor('l_right_outlane_special', 'black')

    def test_each_cap_flashes_and_releases_on_repeated_hits(self):
        self._start_single_ball_game()
        # A lower-priority nonblack owner proves removal restores ownership.
        for n in range(1, 5):
            for led in range(1, 9):
                self.machine.lights[f'l_jetbumper_{n}_{led}'].color('red', priority=300, key='test_underlay', fade_ms=0)
        for n in range(1, 5):
            self.hit_switch_and_run(f's_pop_bumper_{n}', 0.01)
            for other in range(1, 5):
                for led in range(1, 9):
                    self.assertLightColor(f'l_jetbumper_{other}_{led}', 'white' if other == n else 'red')
            self.release_switch_and_run(f's_pop_bumper_{n}', 0.04)
            self.hit_switch_and_run(f's_pop_bumper_{n}', 0.01)
            self.advance_time_and_run(0.03)
            self.assertLightColor(f'l_jetbumper_{n}_1', 'white')
            self.release_switch_and_run(f's_pop_bumper_{n}', 0.1)
            for led in range(1, 9):
                light = self.machine.lights[f'l_jetbumper_{n}_{led}']
                self.assertLightColor(light.name, 'red')
                self.assertFalse(any(entry.priority > 300 for entry in light.stack))
