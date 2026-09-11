"""Exercise the production bonus scheduler, scoring, lamps and ball-ending queue."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase


class BonusCollectTest(MpfMachineTestCase):
    def get_enable_plugins(self):
        return False

    def _collect(self, value, multiplier=1):
        for switch in ("s_trough1", "s_trough2", "s_trough3"):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self.player = self.machine.game.player
        self.player.bonus_value = value
        self.player.bonus_multiplier = multiplier
        self.advance_time_and_run(0.1)
        self.initial_score = self.player.score
        self.steps = []
        self.awards = []
        self.decrements = []
        self.released = []
        self.machine.events.add_handler(
            "bonus_collect_score_step", self._step, priority=10000)
        self.machine.events.add_handler("player_score", self._award)
        self.machine.events.add_handler("player_bonus_value", self._decrement)
        self.machine.events.post_queue(
            "ball_ending", callback=lambda **kwargs: self.released.append(True))
        self.advance_time_and_run(0)

    def _step(self, **kwargs):
        # No future cycle may be scheduled while a scoring step is processing.
        self.assertNotIn("bonus_cycle", self.machine.modes["bonus_collect"].delay.delays)
        self.steps.append((self.machine.clock.get_time(), self.player.bonus_value))

    def _award(self, change, **kwargs):
        self.awards.append((self.machine.clock.get_time(), change))

    def _decrement(self, change, **kwargs):
        if change < 0:
            self.decrements.append((self.machine.clock.get_time(), change))

    def _assert_lamps(self, value):
        for unit in range(1, 10):
            self.assertLightColor("l_bonus_{}".format(unit),
                                  "warm_white" if value % 10 >= unit else "black")
        self.assertLightColor("l_bonus_10", "warm_white" if 10 <= value < 20 or value >= 30 else "black")
        self.assertLightColor("l_bonus_20", "warm_white" if value >= 20 else "black")

    def test_steps_score_and_lamps_share_cadence(self):
        self._collect(12)
        self._assert_lamps(12)
        self.advance_time_and_run(0.079)
        self.assertEqual([], self.steps)
        self.assertEqual(self.initial_score, self.player.score)
        for remaining in range(11, -1, -1):
            self.advance_time_and_run(0.002)
            count = 12 - remaining
            self.assertEqual(count, len(self.steps))
            self.assertEqual(self.initial_score + count * 1000, self.player.score)
            self.assertEqual(remaining, self.player.bonus_value)
            self.assertFalse(self.released)
            # Lamp transitions finish within the logical 130ms step.
            self.advance_time_and_run(0.040)
            self._assert_lamps(remaining)
            self.advance_time_and_run(0.088)
            self.assertEqual(count, len(self.steps))
            self.assertEqual(self.initial_score + count * 1000, self.player.score)
        self.advance_time_and_run(0.002)
        self.assertEqual([True], self.released)
        self.assertFalse(self.machine.modes["bonus_collect"].active)
        self.assertEqual(12, len(self.awards))
        self.assertEqual(12, len(self.decrements))
        for step, award, decrement in zip(self.steps, self.awards, self.decrements):
            self.assertAlmostEqual(step[0], award[0])
            self.assertAlmostEqual(step[0], decrement[0])
            self.assertEqual(1000, award[1])
            self.assertEqual(-1, decrement[1])
        for previous, following in zip(self.steps, self.steps[1:]):
            self.assertAlmostEqual(0.13, following[0] - previous[0])

    def test_bonus_lamp_fades_over_40ms_within_one_step(self):
        self._collect(2)
        self.advance_time_and_run(0.100)  # 20ms into the first step's fade
        color = self.machine.lights["l_bonus_2"].get_color()
        self.assertGreater(color.red, 0)
        self.assertLess(color.red, 243)
        self.assertEqual(1, len(self.steps))
        self.assertEqual(1, self.player.bonus_value)
        self.assertEqual(self.initial_score + 1000, self.player.score)
        self.advance_time_and_run(0.021)  # fade complete, next step still pending
        self._assert_lamps(1)
        self.assertEqual(1, len(self.steps))
        self.advance_time_and_run(0.088)  # 129ms after the first step
        self.assertEqual(1, len(self.steps))
        self.assertEqual(self.initial_score + 1000, self.player.score)
        self.advance_time_and_run(0.002)
        self.assertEqual(2, len(self.steps))
        self.assertEqual(0, self.player.bonus_value)
        self.assertEqual(self.initial_score + 2000, self.player.score)

    def test_late_cycle_delivery_does_not_catch_up(self):
        self._collect(5)
        self.advance_time_and_run(0.081)
        mode = self.machine.modes["bonus_collect"]
        self.assertEqual(["bonus_cycle"], list(mode.delay.delays))
        # Hold delivery of the one pending callback for 500ms. This tests a
        # late scheduler callback, not actual FAST/GMC or CPU-load jitter.
        handle, _ = mode.delay.delays["bonus_cycle"]
        self.machine.clock.unschedule(handle)
        self.advance_time_and_run(0.5)
        self.assertEqual(1, len(self.steps))
        mode.delay.run_now("bonus_cycle")
        self.advance_time_and_run(0)
        self.assertEqual(2, len(self.steps))
        self.assertEqual(3, self.player.bonus_value)
        self.assertEqual(self.initial_score + 2000, self.player.score)
        self.assertEqual(["bonus_cycle"], list(mode.delay.delays))
        self.advance_time_and_run(0.129)
        self.assertEqual(2, len(self.steps))
        self.assertEqual(2, len(self.awards))
        self.assertEqual(2, len(self.decrements))
        self.advance_time_and_run(0.002)
        self.assertEqual(3, len(self.steps))
        self.assertAlmostEqual(0.13, self.steps[-1][0] - self.steps[-2][0])
        self.advance_time_and_run(1)
        self.assertEqual(5, len(self.steps))
        self.assertEqual([True], self.released)
        self.assertEqual({}, mode.delay.delays)

    def test_five_passes_preserve_current_maximum_and_total(self):
        self._collect(39, 5)
        self.advance_time_and_run(27)
        self.assertEqual(list(range(39, 0, -1)) * 5, [step[1] for step in self.steps])
        self.assertEqual(195, len(self.awards))
        self.assertEqual(195, len(self.decrements))
        self.assertTrue(all(change == 1000 for _, change in self.awards))
        self.assertTrue(all(change == -1 for _, change in self.decrements))
        self.assertEqual(self.initial_score + 195000, self.player.score)
        self.assertEqual(0, self.player.bonus_value)
        self.assertEqual(1, self.player.bonus_multiplier)
        self.assertEqual(0, self.player.bonus_collect_running)
        self.assertEqual([True], self.released)
        self.assertFalse(self.machine.modes["bonus_collect"].active)
        self._assert_lamps(0)

    def test_zero_bonus_releases_queue_without_award(self):
        self._collect(0, 5)
        self.advance_time_and_run(1)
        self.assertEqual([], self.steps)
        self.assertEqual([], self.awards)
        self.assertEqual([True], self.released)
        self.assertEqual(1, self.player.bonus_multiplier)
        self.assertFalse(self.machine.modes["bonus_collect"].active)
