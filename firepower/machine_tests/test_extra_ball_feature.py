"""Real switches, native MPF extras and physical-ball lifecycles."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class ExtraBallFeatureTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def start(self, players=1):
        self._start_single_ball_game()
        for _ in range(players - 1):
            self.hit_and_release_switch('s_start_button')
            self.advance_time_and_run(0.2)
        self.advance_time_and_run(3)
        self.packets()

    @property
    def player(self):
        return self.machine.game.player

    @property
    def feature(self):
        return self.machine.modes['extra_ball_feature']

    def packets(self):
        queue = self.machine.bcp.transport.get_named_client('local_display').send_queue
        rows = []
        while not queue.empty():
            command, payload = queue.get_nowait()
            if command == 'trigger':
                rows.append(payload)
        return rows

    def fire(self):
        for letter in 'fire':
            self.hit_and_release_switch('s_lane_' + letter)
            self.advance_time_and_run(0.05)
        self.advance_time_and_run(1.1)

    def light(self):
        for _ in range(4):
            self.fire()
        self.assertEqual(5, self.player.bonus_multiplier)
        self.assertTrue(self.player.firepower_extra_ball_lit)

    def lamp(self, name, on):
        self.advance_time_and_run(0.05)
        self.assertEqual(on, any(self.machine.lights[name].get_color()), name)

    def again(self, on):
        for name in ('l_fire_again', 'l_fire_again_1', 'l_fire_again_2'):
            self.lamp(name, on)

    def collect(self):
        self.hit_and_release_switch('s_power_2')
        self.advance_time_and_run(0.1)
        self.assertTrue(self.player.firepower_extra_ball_collected)

    def drain(self, seconds=10):
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(seconds)

    def tilt(self):
        # Machine has no configured native tilt owner/switch. Exercise the
        # existing public tilt event and MPF Game.tilted boundary deterministically.
        self.machine.game.tilted = True
        self.post_event('tilt')

    def plunge(self):
        if self.machine.switch_controller.is_active(self.machine.switches['s_plunger']):
            self.release_switch_and_run('s_plunger', 0.1)
        self.hit_and_release_switch('s_spinner')
        self.advance_time_and_run(1)

    def test_single_center_hit_scores_1000_and_native_device_awards_once(self):
        self.start()
        self.light()
        before = self.player.score
        self.collect()
        self.assertEqual(1000, self.player.score - before)
        self.assertEqual(1, self.player.extra_ball_firepower_center_num_awarded)
        self.assertEqual(1, self.player.extra_balls)

    def test_5x_wrong_targets_score_and_lamp_presentation(self):
        self.start()
        for multiplier in (2, 3, 4):
            self.fire()
            self.assertEqual(multiplier, self.player.bonus_multiplier)
            self.assertFalse(self.player.firepower_extra_ball_lit)
        self.fire()
        self.lamp('l_extra_ball_arrow', True)
        for switch in ('s_power_1', 's_power_3'):
            self.hit_and_release_switch(switch)
            self.advance_time_and_run(0.1)
            self.assertEqual(0, self.player.extra_balls)
        before = self.player.score
        self.packets()
        self.collect()
        self.assertEqual(18000, self.player.score - before) # 1000 hit + 7000 bank + existing FIRE/POWER 10K
        self.assertEqual(1, self.player.extra_balls)
        self.assertEqual(1, self.player.firepower_extra_ball_earned_ball)
        self.again(True)
        self.lamp('l_extra_ball_arrow', True)
        rows = self.packets()
        self.assertIn(8, [p.get('raw_command') for p in rows if p.get('name') == 'firepower_speech'])
        self.advance_time_and_run(6)
        rows += self.packets()
        self.assertIn(4, [p.get('raw_command') for p in rows if p.get('name') == 'firepower_electronic'])
        self.lamp('l_extra_ball_arrow', False)
        self.assertEqual(0, self.player.power_lit) # existing combined award resets POWER
        self.assertEqual(2, self.player.firepower_bonus_level)

    def test_no_relight_or_second_third_collection_same_physical_ball(self):
        self.start()
        self.light()
        self.collect()
        self.advance_time_and_run(5)
        for _ in range(3):
            self.fire()
            self.hit_and_release_switch('s_power_2')
            self.advance_time_and_run(0.1)
            self.assertFalse(self.player.firepower_extra_ball_lit)
            self.assertEqual(1, self.player.extra_balls)
            self.assertEqual(1, self.player.firepower_extra_ball_earned_ball)

    def test_bonus_before_extra_and_reset_each_physical_ball(self):
        self.start()
        self.light()
        self.collect()
        self.advance_time_and_run(5)
        self.player.bonus_value = 2
        self.player.bonus_multiplier = 2
        score, ball = self.player.score, self.player.ball
        timeline = []
        self.machine.events.add_handler('mode_bonus_collect_started', lambda **kwargs: timeline.append(('bonus', self.player.extra_balls)))
        self.machine.events.add_handler('bonus_collect_done', lambda **kwargs: timeline.append(('done', self.player.extra_balls)))
        self.machine.events.add_handler('ball_started', lambda **kwargs: timeline.append(('extra', self.player.extra_balls)))
        self.drain(10)
        self.assertEqual([('bonus', 1), ('done', 1), ('extra', 0)], timeline)
        self.assertEqual(score + 4000, self.player.score)
        self.assertEqual(ball, self.player.ball)
        self.assertEqual(0, self.player.extra_balls)
        self.assertEqual(0, self.player.firepower_extra_ball_earned_ball)
        self.assertFalse(self.player.firepower_extra_ball_qualified)
        self.again(True)
        self.hit_and_release_switch('s_spinner')
        self.advance_time_and_run(0.1)
        self.again(False)
        self.light()
        self.collect()
        self.assertEqual(1, self.player.extra_balls)

    def test_lit_tilt_lost_awarded_survives_and_extra_itself_tilts(self):
        self.start()
        self.light()
        self.tilt()
        self.advance_time_and_run(0.2)
        self.lamp('l_extra_ball_arrow', False)
        self.hit_and_release_switch('s_power_2')
        self.assertEqual(0, self.player.extra_balls)
        self.drain(15)
        self.machine.game.tilted = False
        self.plunge()
        self.light()
        self.collect()
        ball = self.player.ball
        self.tilt()
        self.advance_time_and_run(0.2)
        self.assertEqual(1, self.player.extra_balls)
        self.drain(15)
        self.assertEqual(ball, self.player.ball)
        self.assertEqual(0, self.player.extra_balls)
        self.machine.game.tilted = False
        self.plunge()
        self.tilt()
        self.drain(15)
        self.assertEqual(ball + 1, self.player.ball)

    def test_multiplayer_isolation_and_same_player_extra_turn(self):
        self.start(2)
        self.light()
        self.collect()
        self.advance_time_and_run(5)
        self.drain()
        self.assertEqual(1, self.player.number)
        self.assertEqual(1, self.player.ball)
        self.hit_and_release_switch('s_spinner')
        self.drain()
        self.assertEqual(2, self.player.number)
        self.assertEqual(1, self.player.bonus_multiplier)
        self.assertEqual(0, self.player.extra_balls)
        self.assertEqual(0, self.player.firepower_extra_ball_earned_ball)
        self.assertFalse(self.player.firepower_extra_ball_lit)
        self.assertFalse(self.player.firepower_extra_ball_qualified)
        self.again(False)

    def test_four_player_native_turns_and_regular_ball_reset(self):
        self.start(4)
        self.light()
        self.collect()
        self.advance_time_and_run(5)
        self.drain()
        self.assertEqual((1, 1), (self.player.number, self.player.ball))
        for expected in (2, 3, 4, 1):
            self.plunge()
            self.drain()
            self.assertEqual(expected, self.player.number)
            self.assertEqual(0, self.player.extra_balls)
            self.assertEqual(0, self.player.firepower_extra_ball_earned_ball)
            self.assertFalse(self.player.firepower_extra_ball_lit)
            self.assertEqual(1, self.player.bonus_multiplier)
        self.assertEqual(2, self.player.ball)

    def test_exact_23_raw04_pulses_and_speech_order(self):
        self.start()
        self.light()
        self.advance_time_and_run(3)
        self.packets()
        self.collect()
        self.advance_time_and_run(4)
        rows = self.packets()
        sound = [p for p in rows if p.get('name') == 'firepower_electronic' and p.get('action') == 'play']
        self.assertEqual(23, sum(p.get('raw_command') == 4 for p in sound))
        voice_index = next(i for i,p in enumerate(rows) if p.get('name') == 'firepower_speech' and p.get('raw_command') == 8)
        effect_index = next(i for i,p in enumerate(rows) if p.get('name') == 'firepower_electronic' and p.get('raw_command') == 4)
        self.assertLess(voice_index, effect_index)
        self.lamp('l_extra_ball_arrow', False)

    def test_pending_two_cap_and_per_ball_guard(self):
        self.start()
        self.player.extra_balls = 2
        for _ in range(5):
            self.fire()
        self.assertFalse(self.player.firepower_extra_ball_lit)
        self.player.extra_balls = 0
        self.player.firepower_extra_ball_earned_ball = 2
        self.fire()
        self.assertFalse(self.player.firepower_extra_ball_lit)
        self.assertEqual(0, self.player.extra_balls)

    def test_disabled_and_prior_5x_adjustment(self):
        self.start()
        self.feature.config['mode_settings']['function_34'] = 10
        for _ in range(5):
            self.fire()
        self.assertFalse(self.player.firepower_extra_ball_lit)
        self.feature.config['mode_settings']['function_34'] = 11
        self.feature._fire(count=4)
        self.assertFalse(self.player.firepower_extra_ball_lit)
        self.fire()
        self.assertTrue(self.player.firepower_extra_ball_lit)

    def test_bonus_29_cap_and_presentation_replacement(self):
        self.start()
        self.light()
        self.collect()
        self.hit_and_release_switch('s_lane_f')
        self.advance_time_and_run(0.1)
        self.lamp('l_extra_ball_arrow', False)
        for _ in range(40):
            self.post_event('advance_end_of_ball_bonus')
        self.assertEqual(29, self.player.bonus_value)
