"""Exercise the production bonus scheduler, scoring, lamps and ball-ending queue."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase


class BonusCollectTest(MpfMachineTestCase):
    def get_enable_plugins(self):
        return False

    def _collect(self, value, multiplier=1, earn_multiplier=False, advance_bonus=0):
        for switch in ("s_trough1", "s_trough2", "s_trough3"):
            self.hit_switch_and_run(switch, 0.1)
        self.advance_time_and_run(2)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(5)
        self.player = self.machine.game.player
        if earn_multiplier:
            for count in range(1, multiplier):
                self.machine.events.post("mltp_lanes_done", count=count)
            self.advance_time_and_run(0.1)
        self.player.bonus_value = value
        for _ in range(advance_bonus):
            self.machine.events.post("advance_end_of_ball_bonus")
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
        self.assertLightColor("l_bonus_10", "warm_white" if 10 <= value < 20 else "black")
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
            # Lamp transitions finish within the logical 66.368ms step.
            self.advance_time_and_run(0.040)
            self._assert_lamps(remaining)
            self.advance_time_and_run(0.024368)
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
            self.assertAlmostEqual(0.066368, following[0] - previous[0])

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
        self.advance_time_and_run(0.024368)  # 65.368ms after the first step
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
        self.advance_time_and_run(0.065368)
        self.assertEqual(2, len(self.steps))
        self.assertEqual(2, len(self.awards))
        self.assertEqual(2, len(self.decrements))
        self.advance_time_and_run(0.002)
        self.assertEqual(3, len(self.steps))
        self.assertAlmostEqual(0.066368, self.steps[-1][0] - self.steps[-2][0])
        self.advance_time_and_run(1)
        self.assertEqual(5, len(self.steps))
        self.assertEqual([True], self.released)
        self.assertEqual({}, mode.delay.delays)

    def test_five_passes_preserve_legal_maximum_and_total(self):
        # Earn through the production increment guard before ball ending.
        self._collect(0, 5, earn_multiplier=True, advance_bonus=50)
        self.assertEqual(29, self.player.bonus_value)
        self._assert_lamps(29)
        self.advance_time_and_run(12)
        self.assertEqual(list(range(29, 0, -1)) * 5, [step[1] for step in self.steps])
        self.assertEqual(145, len(self.awards))
        self.assertEqual(145, len(self.decrements))
        self.assertTrue(all(change == 1000 for _, change in self.awards))
        self.assertTrue(all(change == -1 for _, change in self.decrements))
        self.assertEqual(self.initial_score + 145000, self.player.score)
        for index, (previous, following) in enumerate(zip(self.steps, self.steps[1:]), 1):
            self.assertAlmostEqual(0.165448 if index % 29 == 0 else 0.066368,
                                   following[0] - previous[0], places=7)
        packets = self._audio_packets()
        self.assertEqual(list(range(1, 146)),
                         [p["step"] for p in packets if p["action"] == "step"])
        self.assertEqual("stop", packets[-1]["action"])
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

    def _audio_packets(self):
        queue = self.machine.bcp.transport.get_named_client("local_display").send_queue
        packets = []
        while not queue.empty():
            command, payload = queue.get_nowait()
            if command == "trigger" and payload.get("name") == "firepower_bonus_audio":
                packets.append(payload)
        return packets

    def _assert_passes_and_audio(self, multiplier):
        self._collect(29, multiplier)
        self.advance_time_and_run(12)
        self.assertEqual(list(range(29, 0, -1)) * multiplier,
                         [step[1] for step in self.steps])
        self.assertEqual(29 * multiplier, len(self.awards))
        self.assertEqual(29 * multiplier, len(self.decrements))
        self.assertEqual(self.initial_score + 29000 * multiplier, self.player.score)
        for index, (previous, following) in enumerate(zip(self.steps, self.steps[1:]), 1):
            expected = 0.165448 if index % 29 == 0 else 0.066368
            self.assertAlmostEqual(expected, following[0] - previous[0], places=7)
        packets = self._audio_packets()
        self.assertEqual("start", packets[0]["action"])
        self.assertEqual(0, packets[0]["step"])
        self.assertEqual("stop", packets[-1]["action"])
        self.assertEqual(list(range(1, 29 * multiplier + 1)),
                         [p["step"] for p in packets if p["action"] == "step"])
        self.assertEqual(1, len({p["cycle"] for p in packets}))
        self.advance_time_and_run(2)
        self.machine.events.post("s_spinner_active")
        self.advance_time_and_run(0)
        self.assertEqual([], self._audio_packets())
        self.assertEqual([True], self.released)

    def test_one_pass_audio(self):
        self._assert_passes_and_audio(1)

    def test_two_pass_audio(self):
        self._assert_passes_and_audio(2)

    def test_three_pass_audio(self):
        self._assert_passes_and_audio(3)

    def test_four_pass_audio(self):
        self._assert_passes_and_audio(4)

    def test_five_pass_audio(self):
        self._assert_passes_and_audio(5)

    def test_audio_stop_and_sync_dont_replay_steps(self):
        self._collect(12, 3)
        self.advance_time_and_run(0.081)
        self._audio_packets()
        self.machine.events.post("firepower_bonus_audio_sync")
        self.advance_time_and_run(0)
        sync = self._audio_packets()
        self.assertEqual(["start"], [p["action"] for p in sync])
        self.assertEqual(1, sync[0]["step"])
        self.machine.modes["bonus_collect"].stop()
        self.advance_time_and_run(0)
        self.assertEqual(["stop"], [p["action"] for p in self._audio_packets()])
        self.assertEqual({}, self.machine.modes["bonus_collect"].delay.delays)
        self.advance_time_and_run(2)
        self.assertEqual(1, len(self.steps))
        self.assertEqual([], self._audio_packets())

    def _assert_multiplier_display(self, level):
        for number in range(2, 6):
            lamp = self.machine.lights[f"l_bonus_multiplier_{number}x"]
            self.assertEqual(40, lamp.default_fade_ms)
            if number == level:
                self.assertLightColor(lamp.name, "warm_white")
            else:
                self.assertLightColor(lamp.name, "black")

    def _assert_multiplier_countdown(self, multiplier):
        self._collect(3, multiplier, earn_multiplier=True)
        self._assert_multiplier_display(multiplier)
        self.advance_time_and_run(0.079)
        for pass_index in range(multiplier):
            level = multiplier - pass_index
            # Two ordinary steps must not consume the displayed multiplier.
            for _ in range(2):
                self.advance_time_and_run(0.002)
                self._assert_multiplier_display(level)
                self.assertEqual(multiplier, self.player.bonus_multiplier)
                self.advance_time_and_run(0.064368)
            self._assert_multiplier_display(level)
            if level > 1:
                lamp = self.machine.lights[f"l_bonus_multiplier_{level}x"]
                before = lamp.get_color().red
            self.advance_time_and_run(0.002)  # final step of this pass
            self.assertEqual(3 * (pass_index + 1), len(self.steps))
            self.assertEqual(self.initial_score + len(self.steps) * 1000, self.player.score)
            self.assertEqual(len(self.steps), len(self.awards))
            self.assertEqual(len(self.steps), len(self.decrements))
            self.assertEqual(multiplier, self.player.bonus_multiplier)
            packets = self._audio_packets()
            self.assertEqual(len(self.steps), [p['step'] for p in packets
                                              if p['action'] == 'step'][-1])
            if level > 1:
                entry = next(entry for entry in lamp.stack
                             if entry.key == "bonus_collect_multiplier")
                self.assertAlmostEqual(self.steps[-1][0], entry.start_time)
                self.assertAlmostEqual(0.040, entry.dest_time - entry.start_time)
                self.advance_time_and_run(0.019)  # half of the off fade
                self.assertGreater(lamp.get_color().red, 0)
                self.assertLess(lamp.get_color().red, before)
                self.advance_time_and_run(0.021)
                self.assertLightColor(lamp.name, "black")
                self._assert_multiplier_display(level - 1)
                self.assertEqual(3, self.player.bonus_value)  # base restored
                self._assert_lamps(3)
                self.advance_time_and_run(0.123448)  # 1ms before next pass
                self.assertEqual(3 * (pass_index + 1), len(self.steps))
            else:
                self.advance_time_and_run(0.040)
                self._assert_multiplier_display(1)
                self._assert_lamps(0)
        self.advance_time_and_run(0.2)
        self.assertEqual([True], self.released)
        self.assertEqual(1, self.player.bonus_multiplier)
        # Normal ball-start initialization must remove any earned/display state.
        self.machine.events.post_queue("ball_starting", callback=lambda **kwargs: None)
        self.advance_time_and_run(0)
        self.machine.events.post("ball_started")
        self.advance_time_and_run(0.1)
        self._assert_multiplier_display(1)
        for number in range(2, 6):
            lamp = self.machine.lights[f"l_bonus_multiplier_{number}x"]
            self.assertFalse(any(entry.key == "bonus_collect_multiplier" for entry in lamp.stack))
        self.machine.events.post("mltp_lanes_done", count=1)
        self.advance_time_and_run(0.1)
        self.assertEqual(2, self.player.bonus_multiplier)
        self._assert_multiplier_display(2)

    def test_multiplier_lamps_1x(self):
        self._assert_multiplier_countdown(1)

    def test_multiplier_lamps_2x(self):
        self._assert_multiplier_countdown(2)

    def test_multiplier_lamps_3x(self):
        self._assert_multiplier_countdown(3)

    def test_multiplier_lamps_4x(self):
        self._assert_multiplier_countdown(4)

    def test_multiplier_lamps_5x(self):
        self._assert_multiplier_countdown(5)
