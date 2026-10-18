"""L-6 Match: deterministic phase, real game/ball queues, FAST and native credits."""
from types import SimpleNamespace
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from mpf.platforms.fast.fast_segment_display import FASTSegmentDisplay
from mpf.platforms.fast.communicators.seg import FastSegCommunicator
from machine_tests import test_firepower_multiball


class FirepowerMatchTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    @property
    def match(self):
        return self.machine.modes['firepower_match']

    @property
    def credits(self):
        return self.machine.modes['credits']

    def start(self, scores=(12340,), number=90):
        self._start_single_ball_game()
        for _ in scores[1:]:
            self.hit_and_release_switch('s_start_button')
            self.advance_time_and_run(0.1)
        for player, score in zip(self.machine.game.player_list, scores):
            player.score = score
        self.machine.game.player.bonus_value = 0
        self.advance_time_and_run(3)
        self.match.phase_source = lambda: number // 10 << 4
        self.packets()

    def packets(self):
        queue = self.machine.bcp.transport.get_named_client('local_display').send_queue
        rows=[]
        while not queue.empty():
            command,payload=queue.get_nowait()
            if command=='trigger': rows.append(payload)
        return rows

    def end(self, seconds=0.3):
        self.machine.game.end_game()
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(seconds)

    def wait_match(self):
        for _ in range(150):
            if self.match.match_number is not None:
                return
            self.advance_time_and_run(0.02)
        self.fail('Match did not begin after home collection')

    def unit_count(self):
        return self.machine.variables.get_machine_var('credit_units') or 0

    def lamp(self, on):
        self.advance_time_and_run(0.05)
        self.assertEqual(on, any(self.machine.lights['l_match'].get_color()))

    def payload(self):
        display=self.machine.segment_displays['credit_ball_display']
        commands=[]
        hw=FASTSegmentDisplay(4,None)
        hw.set_text(display._current_state.text,display._current_state.flashing,display._current_state.flash_mask)
        FastSegCommunicator._update_segs(SimpleNamespace(platform=SimpleNamespace(fast_segs=[hw]),send_and_forget=commands.append))
        return commands[0]

    def test_no_match_single_value_persists_through_attract_then_new_game_clears(self):
        self.start(number=90)
        self.end(1)
        self.assertFalse(self.machine.game)
        self.assertTrue(self.machine.modes['attract'].active)
        self.assertEqual(90,self.match.match_number)
        self.assertEqual([],self.match.winners)
        self.lamp(True)
        self.assertEqual('PA:1C,0  90 ',self.payload())
        self.advance_time_and_run(20)
        self.assertEqual('PA:1C,0  90 ',self.payload())
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)
        self.assertIsNone(self.match.match_number)
        self.lamp(False)
        self.assertEqual('1 ',self.machine.segment_displays['credit_ball_display'].text[3:5])

    def test_single_match_sound_before_credit_128_tick_wait_no_match_speech(self):
        self.start(scores=(12340,),number=40)
        before=self.unit_count()
        self.end(0.3)
        self.wait_match()
        self.assertTrue(self.match.running)
        self.assertEqual([1],self.match.winners)
        rows=self.packets()
        self.assertEqual([28],[p['raw_command'] for p in rows if p.get('name')=='firepower_electronic' and p.get('action')=='play'])
        self.assertFalse([p for p in rows if p.get('name')=='firepower_speech' and p.get('action')=='request'])
        self.assertEqual(before,self.unit_count())
        self.advance_time_and_run(1.7)
        self.assertEqual(before,self.unit_count())
        self.advance_time_and_run(0.5)
        self.assertEqual(before+self.credits.credit_units_per_game,self.unit_count())
        self.assertFalse(self.machine.game)
        self.assertEqual('PA:1C,1  40 ',self.payload())

    def test_every_player_and_multiple_matches_1_through_4(self):
        # Four players exercise all score positions; the tests below cover1/2/3.
        self.start(scores=(10020,20040,30020,40020),number=20)
        scores=[p.score for p in self.machine.game.player_list]
        self.end(0.3)
        self.wait_match()
        self.assertEqual([1,3,4],self.match.winners)
        self.assertEqual(scores,[p.score for p in self.machine.game.player_list])
        self.advance_time_and_run(4)
        self.assertEqual(3*self.credits.credit_units_per_game,self.unit_count())
        # HSTD now advertises on the highest player's display in attract.
        # Check the preserved final scores during its original-score phase.
        hstd = self.machine.modes['high_score_to_date']
        for _ in range(220):
            if not hstd.showing_high_score:
                break
            self.advance_time_and_run(0.01)
        self.assertFalse(hstd.showing_high_score)
        for i,score in enumerate(scores,1):
            self.assertEqual(score,self.machine.variables.get_machine_var(f'player{i}_score'))
            self.assertEqual(score,int(self.machine.segment_displays[f'player{i}_display'].text.replace(',','').strip()))

    def test_two_players_other_player_match_and_ones_digit_matters(self):
        self.start(scores=(10021,20020),number=20)
        self.end(3)
        self.assertEqual([2],self.match.winners)
        self.assertEqual(self.credits.credit_units_per_game,self.unit_count())

    def test_three_players_multiple_zero_match_credit_spacing(self):
        self.start(scores=(10000,20000,30090),number=0)
        timestamps=[]
        self.machine.events.add_handler('firepower_match_credit',lambda **kwargs: timestamps.append(self.machine.clock.get_time()))
        self.end(4)
        self.assertEqual([1,2],self.match.winners)
        self.assertEqual(2,len(timestamps))
        self.assertAlmostEqual(16*self.match.TICK,timestamps[1]-timestamps[0],places=5)
        self.assertEqual('PA:1C,2  00 ',self.payload())

    def test_max_credits_and_full_cap_still_show_match_and_sound(self):
        self.start(scores=(10090,20090,30090,40090),number=90)
        for _ in range(11): self.credits.add_credit(price_tiering=False)
        self.end(4)
        self.assertEqual(12*self.credits.credit_units_per_game,self.unit_count())
        self.assertEqual('PA:1C,12 90 ',self.payload())
        self.assertEqual([1,2,3,4],self.match.winners)

    def test_free_play_still_presents_match_without_adding_hidden_credits(self):
        self.start(scores=(10090,),number=90)
        self.credits.enable_free_play()
        before=self.unit_count()
        self.end(3)
        self.assertEqual([1],self.match.winners)
        self.assertEqual(before,self.unit_count())
        self.lamp(True)
        self.assertEqual('90',self.machine.segment_displays['credit_ball_display'].text[3:5])
        self.assertIn(28,[p.get('raw_command') for p in self.packets() if p.get('name')=='firepower_electronic'])

    def test_disabled_no_match_lamp_sound_credits_or_number(self):
        self.start(scores=(10000,),number=0)
        self.match.config['mode_settings']['function_26']=1
        self.end(1)
        self.assertFalse(self.machine.game)
        self.assertIsNone(self.match.match_number)
        self.lamp(False)
        self.assertEqual(0,self.unit_count())
        self.assertNotIn(28,[p.get('raw_command') for p in self.packets() if p.get('name')=='firepower_electronic'])

    def test_phase_range_timing_independent_of_scores(self):
        phase=self.match._timing_phase
        values=set()
        for _ in range(100):
            values.add(phase())
            self.advance_time_and_run(self.match.TICK*1.001)
        self.assertEqual({i<<4 for i in range(10)},values)

    def test_credit_updates_preserve_match_position_and_normal_ball_updates(self):
        self.start(number=90)
        self.credits.add_credit(price_tiering=False)
        self.advance_time_and_run(0.1)
        self.assertEqual('PA:1C,1  1  ',self.payload())
        self.end(1)
        self.credits.add_credit(price_tiering=False)
        self.advance_time_and_run(0.1)
        self.assertEqual('PA:1C,2  90 ',self.payload())

    def test_bonus_extra_ball_delay_and_future_high_score_hook(self):
        self.start(scores=(10040,),number=40)
        self.machine.game.balls_per_game=1
        self.machine.game.player.extra_balls=1
        self.machine.game.player.bonus_value=3
        self.machine.game.player.bonus_multiplier=2
        timeline=[]
        for event in ('bonus_collect_done','firepower_match_selected','firepower_high_score_check','game_ended','mode_attract_started'):
            self.machine.events.add_handler(event,lambda e=event,**kwargs: timeline.append(e))
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(4)
        self.assertTrue(self.machine.game)
        self.assertEqual(1,self.machine.game.player.ball)
        self.assertIsNone(self.match.match_number)
        self.assertNotIn('firepower_match_selected',timeline)
        self.release_switch_and_run('s_plunger',0.1)
        self.hit_and_release_switch('s_spinner')
        self.advance_time_and_run(1)
        self.machine.game.player.score=20040
        self.machine.game.player.bonus_value=0
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(4)
        expected=['firepower_match_selected','firepower_high_score_check','game_ended','mode_attract_started']
        self.assertEqual(expected,[e for e in timeline if e in expected])

    def test_service_cancels_pending_awards_and_clears_lamp_display(self):
        self.start(number=40)
        self.end(0.3)
        self.wait_match()
        self.post_event('service_mode_entered')
        self.advance_time_and_run(3)
        self.assertEqual(0,self.unit_count())
        self.assertFalse(self.match.running)
        self.assertIsNone(self.match.match_number)
        self.lamp(False)

    def test_fractional_credit_cap_never_exceeds_twelve(self):
        self.start(number=40)
        # Eleven whole credits plus one paid quarter =11.5 games.
        self.credits.clear_all_credits()
        for _ in range(11):
            self.credits.add_credit(price_tiering=False)
        self.hit_and_release_switch('s_coin_left')
        self.advance_time_and_run(0.1)
        self.assertEqual(23,self.unit_count())
        self.end(3)
        self.assertEqual(24,self.unit_count())
        self.assertEqual('PA:1C,12 40 ',self.payload())

    def test_high_score_queue_hook_preserves_rom_order(self):
        self.start(number=90)
        held=[]
        def hold(queue, **kwargs):
            queue.wait()
            held.append(queue)
        self.machine.events.add_handler('firepower_high_score_check',hold)
        self.end(1)
        self.assertEqual(1,len(held))
        self.assertTrue(self.machine.game)
        self.assertTrue(self.machine.game.ending)
        self.assertEqual(90,self.match.match_number)
        self.assertFalse(self.machine.modes['attract'].active)
        held[0].clear()
        self.advance_time_and_run(0.1)
        self.assertFalse(self.machine.game)
        self.assertTrue(self.machine.modes['attract'].active)

    def test_locked_ball_collection_finishes_before_match(self):
        self.start(number=90)
        self.post_event('qualify_lock_1')
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_lock1'])
        self.advance_time_and_run(2)
        if self.machine.switch_controller.is_active(self.machine.switches['s_plunger']):
            self.release_switch_and_run('s_plunger',0.1)
        self.hit_and_release_switch('s_spinner')
        self.advance_time_and_run(1)
        self.assertEqual(1,self.machine.ball_devices['bd_lock1'].balls)
        selected=[]
        self.machine.events.add_handler('firepower_match_selected',lambda **kwargs: selected.append(
            (self.machine.ball_devices['bd_lock1'].balls,self.machine.ball_controller.are_balls_collected('home'))))
        self.end(0.1)
        self.assertIsNone(self.match.match_number)
        # Smart virtual eject routes the held ball to the playfield; simulate
        # that ball's eventual drain without editing native counts or switches.
        self.advance_time_and_run(2)
        self.assertIsNone(self.match.match_number)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices['bd_drain'])
        self.advance_time_and_run(4)
        self.assertEqual([(0,True)],selected)
        self.assertFalse(self.machine.game)

    def test_unrestricted_starts_preserved_and_native_coin_ledger_active(self):
        self.assertTrue(self.credits.config['mode_settings']['unrestricted_starts'])
        self.assertEqual(0,self.unit_count())
        self.start(number=90)
        self.assertEqual(0,self.unit_count())
        self.hit_and_release_switch('s_coin_left')
        self.advance_time_and_run(0.1)
        self.assertEqual(1,self.unit_count())
        self.assertEqual(0,self.machine.variables.get_machine_var('credits_whole_num'))

    def test_full_credit_cap_still_gets_presentation_and_sound(self):
        self.start(number=40)
        for _ in range(12):
            self.credits.add_credit(price_tiering=False)
        self.end(3)
        self.assertEqual(24,self.unit_count())
        self.assertEqual([1],self.match.winners)
        self.assertIn(28,[p.get('raw_command') for p in self.packets() if p.get('name')=='firepower_electronic'])

    def test_stale_high_score_callback_cannot_change_next_game(self):
        self.start(number=90)
        held=[]
        def hold(queue, **kwargs):
            queue.wait()
            held.append(queue)
        key=self.machine.events.add_handler('firepower_high_score_check',hold)
        self.end(1)
        self.match._cancel()
        self.advance_time_and_run(0.2)
        self.assertFalse(self.machine.game)
        self.machine.events.remove_handler_by_key(key)
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)
        held[0].clear()
        self.advance_time_and_run(0.1)
        self.assertTrue(self.machine.game)
        self.assertFalse(self.machine.game.ending)
        self.assertIsNone(self.match.match_number)

    def test_opt_in_paid_start_policy_uses_native_credits(self):
        self.credits.config['mode_settings']['unrestricted_starts']=False
        self.credits.enable_credit_play(post_event=False)
        for switch in ('s_trough1','s_trough2','s_trough3'):
            self.hit_switch_and_run(switch,0.1)
        self.advance_time_and_run(2)
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(0.2)
        self.assertFalse(self.machine.game)
        self.credits.add_credit(price_tiering=False)
        self.hit_and_release_switch('s_start_button')
        self.advance_time_and_run(5)
        self.assertTrue(self.machine.game)
        self.assertEqual(0,self.unit_count())
