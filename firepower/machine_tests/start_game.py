from mpf.tests.MpfMachineTestCase import MpfMachineTestCase

class startgame(MpfMachineTestCase):
    def test_start_game(self):
        self.hit_switch_and_run("s_trough1", .1)
        self.hit_switch_and_run("s_trough2", .1)
        self.hit_switch_and_run("s_trough3", .1)

        self.advance_time_and_run(2)

        self.assertNumBallsKnown(3)

        self.assertFalse(self.machine.game)

        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(10)

        self.assertTrue(self.machine.game)

        self.assertEqual(1, self.machine.playfields["playfield"].available_balls)