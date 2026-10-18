"""Actual FIRE/POWER insert ownership during the completed-pair celebration."""
from mpf.tests.MpfMachineTestCase import MpfMachineTestCase
from machine_tests import test_firepower_multiball


class FirepowerBonusLightsTest(MpfMachineTestCase):
    get_enable_plugins = test_firepower_multiball.FirepowerMultiballTest.get_enable_plugins
    _start_single_ball_game = test_firepower_multiball.FirepowerMultiballTest._start_single_ball_game

    def _group(self, name):
        return [self.machine.lights[f"l_{name}_lamp_{n}"] for n in range(1, 4)]

    def _assert_pair(self, fire, power):
        for lamp in self._group("fire"):
            self.assertEqual(fire, tuple(lamp.get_color()))
        for lamp in self._group("power"):
            self.assertEqual(power, tuple(lamp.get_color()))

    def _complete_fire(self):
        for letter in "fire":
            self.hit_and_release_switch(f"s_lane_{letter}")

    def _complete_power(self):
        for number in range(1, 4):
            self.hit_and_release_switch(f"s_power_{number}")

    def test_fire_alone_keeps_existing_steady_appearance(self):
        self._start_single_ball_game()
        self._complete_fire()
        self.advance_time_and_run(0.1)
        self.assertEqual(1, self.machine.game.player.fire_lit)
        self._assert_pair((255, 255, 255), (0, 0, 0))

    def test_power_alone_keeps_existing_steady_appearance(self):
        self._start_single_ball_game()
        self._complete_power()
        self.advance_time_and_run(0.1)
        self.assertEqual(1, self.machine.game.player.power_lit)
        self._assert_pair((0, 0, 0), (32, 64, 255))

    def test_both_completed_alternate_then_relinquish_all_insert_layers(self):
        self._start_single_ball_game()
        self._complete_power()
        self._complete_fire()
        player = self.machine.game.player
        self.assertEqual((0, 0), (player.fire_lit, player.power_lit))
        self.assertEqual(2, player.firepower_bonus_level)
        phases = (
            ((255, 0, 0), (0, 0, 0)),
            ((0, 0, 0), (0, 0, 0)),
            ((0, 0, 0), (0, 0, 255)),
            ((0, 0, 0), (0, 0, 0)),
        )
        for _ in range(4):  # MPF loops: 3 means initial pass plus three repeats.
            for fire, power in phases:
                self.advance_time_and_run(0.055)
                self._assert_pair(fire, power)
                self.advance_time_and_run(0.015)
        self.advance_time_and_run(0.05)
        self._assert_pair((0, 0, 0), (0, 0, 0))
        for lamp in self._group("fire") + self._group("power"):
            self.assertTrue(all(entry.key == "lane_change.light_player" for entry in lamp.stack))
        self.post_event("multiball_firepower_ended")
        self.advance_time_and_run(0.1)
        self._assert_pair((0, 0, 0), (0, 0, 0))

    def test_fire_first_then_power_also_clears_both_after_award(self):
        self._start_single_ball_game()
        self._complete_fire()
        self._complete_power()
        self.assertEqual((0, 0), (self.machine.game.player.fire_lit,
                                  self.machine.game.player.power_lit))
        self.advance_time_and_run(1.2)
        self._assert_pair((0, 0, 0), (0, 0, 0))
