"""Original semantic sound categories at the real MPF/GMC command boundary."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class OriginalAudioTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game
    _lock_ball = test_firepower_multiball.FirepowerMultiballTest._lock_ball

    @property
    def audio(self):
        return self.machine.modes['original_audio']

    def packets(self, name='firepower_electronic'):
        queue = self.machine.bcp.transport.get_named_client('local_display').send_queue
        packets = []
        while not queue.empty():
            command, payload = queue.get_nowait()
            if command == 'trigger' and (name is None or payload.get('name') == name):
                packets.append(payload)
        return packets

    def commands(self):
        return [p['raw_command'] for p in self.packets() if p['action'] == 'play']

    def start(self):
        self._start_single_ball_game()
        self.advance_time_and_run(3)
        self.packets()

    def shot(self, switch, seconds=3):
        self.hit_and_release_switch(switch)
        self.advance_time_and_run(seconds)
        return self.commands()

    def test_jets_lit_and_unlit_share_command_but_defer_different_counts(self):
        self.start()
        for lit in (0, 1):
            self.machine.game.player.jet_bumpers_all = lit
            for number in range(1, 5):
                self.assertEqual([10], self.shot(f's_pop_bumper_{number}'))
        self.post_event('firepower_background_award_started')
        self.machine.game.player.jet_bumpers_all = 1
        self.assertEqual([], self.shot('s_pop_bumper_1', 0.1))
        self.post_event('firepower_background_award_stopped')
        self.advance_time_and_run(2)
        self.assertEqual([10] * 10, self.commands())

    def test_spinner_lit_retrigger_and_state_survive_ball_mode_stop(self):
        self.start()
        self.assertEqual([10], self.shot('s_spinner'))
        self.post_event('light_spinner')
        self.hit_and_release_switch('s_spinner')
        packets = [p for p in self.packets() if p['action'] == 'play']
        self.assertEqual([(18, 1)], [(p['raw_command'], p['stage']) for p in packets])
        self.advance_time_and_run(0.1)
        self.hit_and_release_switch('s_spinner')
        packets = [p for p in self.packets() if p['action'] == 'play']
        self.assertEqual([(18, 2)], [(p['raw_command'], p['stage']) for p in packets])
        self.advance_time_and_run(2)
        self.assertEqual([11, 11], self.commands())
        self.audio.stop()
        self.advance_time_and_run(0)
        self.audio.start()
        self.advance_time_and_run(0)
        self.packets()
        self.assertEqual([18, 11], self.shot('s_spinner'))
        self.assertEqual(3, self.audio.spinner_stage)

    def test_fire_lane_new_and_already_lit(self):
        self.start()
        for letter in ('f', 'i', 'r'):
            self.assertEqual([9, 11], self.shot(f's_lane_{letter}'))
            self.assertEqual([11], self.shot(f's_lane_{letter}'))
        self.assertEqual([11], self.shot('s_lane_e'))

    def test_center_new_and_repeated(self):
        self.start()
        self.assertEqual([16] * 10 + [11], self.shot('s_arrow_1'))
        self.assertEqual([10] * 10, self.shot('s_arrow_1'))

    def test_power_new_and_same_target_during_effect(self):
        self.start()
        self.hit_and_release_switch('s_power_1')
        self.advance_time_and_run(0.1)
        self.hit_and_release_switch('s_power_1')
        self.advance_time_and_run(2)
        self.assertEqual([2] * 10 + [11], self.commands())

    def test_return_lanes_lit_score_sound_count_and_ordinary_rollovers(self):
        self.start()
        for side in ('left', 'right'):
            self.machine.game.player.return_lanes_lit = 0
            self.assertEqual([11], self.shot(f's_{side}_return_lane'))
            self.machine.game.player.return_lanes_lit = 1
            self.assertEqual([11] * 3, self.shot(f's_{side}_return_lane'))
            self.assertEqual([11], self.shot(f's_{side}_out_lane'))
        self.assertEqual([11], self.shot('s_top_target'))
        self.assertEqual([5], self.shot('s_left_slingshot'))
        self.assertEqual([5], self.shot('s_right_slingshot'))

    def test_lock_capture_uses_accounted_capture_and_keeps_speech_sequence(self):
        self.start()
        for number in (1, 2):
            self._lock_ball(number)
            self.assertIn(3, self.commands())
        self.packets()
        self._lock_ball(3)
        self.advance_time_and_run(9)
        packets = self.packets(None)
        commands = [p['raw_command'] for p in packets
                    if p.get('name') == 'firepower_electronic' and p['action'] == 'play']
        speech = [p['raw_command'] for p in packets
                  if p.get('name') == 'firepower_speech' and p['action'] == 'request'
                  and p['raw_command'] == 0x18]
        self.assertNotIn(3, commands)
        self.assertEqual([0x18] * 4, speech)
        self.assertTrue(self.machine.modes['firepower_multiball'].active)

    def test_unqualified_hole_uses_score_sound_without_lock_effect(self):
        self.start()
        self.post_event('balldevice_bd_lock1_ball_entered', new_balls=1)
        self.advance_time_and_run(1)
        self.assertEqual([11], self.commands())

    def test_completion_replaces_ordinary_effect_without_guessed_audio(self):
        self.start()
        for number in (1, 2):
            self.shot(f's_power_{number}')
        self.assertEqual([], self.shot('s_power_3'))
        for number in range(1, 6):
            self.shot(f's_arrow_{number}')
        self.assertEqual([11], self.shot('s_arrow_6'))

    def test_special_award_keeps_score_sound_without_unproven_speech(self):
        self.start()
        self.post_event('light_outlane_specials')
        self.advance_time_and_run(0)
        self.packets()
        self.hit_and_release_switch('s_left_out_lane')
        self.advance_time_and_run(5)
        packets = self.packets(None)
        commands = [p['raw_command'] for p in packets
                    if p.get('name') == 'firepower_electronic' and p['action'] == 'play']
        self.assertEqual([11], commands)
        self.assertFalse(any(p.get('name') == 'sounds_play' for p in packets))
        self.assertFalse(self.machine.game.player.special_lit)

    def test_bonus_boundary_cancels_queue_and_gameplay_switches_are_silent(self):
        self.start()
        self.hit_and_release_switch('s_arrow_1')
        self.commands()
        self.post_event('ball_will_end')
        packets = self.packets()
        self.assertEqual(['stop'], [p['action'] for p in packets])
        for switch in ('s_spinner', 's_power_1', 's_arrow_2', 's_lane_i', 's_pop_bumper_1'):
            self.hit_and_release_switch(switch)
        self.advance_time_and_run(3)
        self.assertEqual([], self.commands())

    def test_attract_all_categories_remain_silent(self):
        for switch in ('s_spinner', 's_power_1', 's_arrow_1', 's_lane_f', 's_pop_bumper_1',
                       's_lock_1', 's_star_1', 's_top_target', 's_left_return_lane',
                       's_left_out_lane', 's_plunger', 's_left_slingshot'):
            self.hit_and_release_switch(switch)
        self.advance_time_and_run(3)
        self.assertEqual([], self.commands())

    def test_game_start_and_added_player_follow_foreground_sequences(self):
        self._start_single_ball_game()
        self.assertIn(25, self.commands())
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(0.1)
        self.assertEqual([29], self.commands())

    def _serve_without_launch(self):
        for switch in ('s_trough1', 's_trough2', 's_trough3'):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(5)
        self.assertEqual(1, self.machine.ball_devices['bd_plunger_lane'].balls)
        self.assertTrue(self.audio.shooter_occupied)
        self.assertNotIn(20, self.commands())

    def test_launch_waits_for_stable_departure_and_precedes_first_playfield_hit(self):
        self._serve_without_launch()
        lamp_show = self.machine.modes['start_button_lamp'].flash
        self.assertIsNotNone(lamp_show)
        self.release_switch_and_run('s_plunger', 0.01)
        self.assertEqual([], self.commands())
        self.advance_time_and_run(0.03)
        packets = [p for p in self.packets() if p['action'] == 'play']
        self.assertEqual([(0x94, 0x14)], [(p['token'], p['raw_command']) for p in packets])
        # Lamp retains its separate accounted-eject boundary, which can lag
        # the original sound's shorter switch stabilization.
        self.assertIs(lamp_show, self.machine.modes['start_button_lamp'].flash)
        self.advance_time_and_run(0.1)
        self.assertEqual([], self.commands())
        self.assertEqual([10], self.shot('s_spinner'))
        self.assertFalse(self.machine.modes['start_button_lamp'].waiting_for_launch)
        self.assertIsNone(self.machine.modes['start_button_lamp'].flash)

    def test_shooter_bounce_and_unrecognized_contact_do_not_launch(self):
        self._serve_without_launch()
        self.release_switch_and_run('s_plunger', 0.01)
        self.hit_switch_and_run('s_plunger', 0.1)
        self.assertEqual([], self.commands())
        self.release_switch_and_run('s_plunger', 0.1)
        self.assertEqual([20], self.commands())
        self.hit_switch_and_run('s_plunger', 0.01)
        self.release_switch_and_run('s_plunger', 0.1)
        self.assertEqual([], self.commands())

    def test_return_to_shooter_launch_interrupts_without_replacing_queue(self):
        self.start()
        self.hit_switch_and_run('s_plunger', 0.1)
        self.hit_and_release_switch('s_arrow_1')
        self.assertEqual([16], self.commands())
        effects = list(self.audio.effects)
        scores = list(self.audio.scores)
        deadline = self.audio.busy_until
        self.release_switch_and_run('s_plunger', 0.04)
        self.assertEqual([20], self.commands())
        self.assertEqual(effects, list(self.audio.effects))
        self.assertEqual(scores, list(self.audio.scores))
        self.assertEqual(deadline, self.audio.busy_until)
        self.advance_time_and_run(2)
        self.assertEqual([16] * 9 + [11], self.commands())

    def test_extra_and_later_ball_launches_use_same_sound(self):
        self.start()
        self.machine.game.player.extra_balls = 1
        for expected_ball in (1, 2):
            self.machine.game.player.bonus_value = 0
            self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
            self.advance_time_and_run(5)
            self.assertEqual(expected_ball, self.machine.game.player.ball)
            self.assertTrue(self.audio.shooter_occupied)
            self.assertNotIn(20, self.commands())
            self.release_switch_and_run('s_plunger', 0.04)
            self.assertEqual([20], self.commands())
            self.hit_and_release_switch('s_spinner')
            self.advance_time_and_run(1)
            self.commands()

    def test_lock_replacement_launches_are_allowed_and_release_pauses_recognition(self):
        self.start()
        for number in (1, 2):
            self._lock_ball(number)
            # Actual replacement routing and launch, not a posted sound event.
            self.assertIn(20, self.commands())
        self._lock_ball(3)
        self.advance_time_and_run(3)
        self.assertNotIn(20, self.commands())  # release from locks is no shooter departure
        self.assertTrue(self.machine.modes['firepower_multiball'].active)
        self.hit_switch_and_run('s_plunger', 0.1)
        self.commands()
        self.post_event('firepower_background_release_started')
        self.release_switch_and_run('s_plunger', 0.1)
        self.assertEqual([], self.commands())
        self.assertTrue(self.audio.shooter_occupied)
        self.post_event('firepower_background_release_stopped')
        self.advance_time_and_run(0.04)
        self.assertEqual([20], self.commands())  # stable departure resumes after release

    def test_tilt_cancels_pending_launch(self):
        self._serve_without_launch()
        self.release_switch_and_run('s_plunger', 0.01)
        self.post_event('tilt')
        self.advance_time_and_run(0.1)
        self.assertEqual([], self.commands())
