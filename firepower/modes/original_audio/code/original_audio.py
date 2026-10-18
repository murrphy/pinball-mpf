"""Firepower-local sound commands; scoring and feature state remain owned by rules.

See audio/FIREPOWER_SOUND_MAP.md. This models the recovered common effect/score
queue, not the CPU, PIA or every original presentation. Unresolved paths retain
their existing assets/presentation rather than acquiring guessed replacements.
"""
from collections import deque
from mpf.core.mode import Mode


class OriginalAudio(Mode):
    TICK = 16 * 928 * 4 / 3579545
    SCORE_DELAYS = {5: 5, 10: 4, 11: 2}

    def mode_init(self):
        self.generation = 0
        self.serial = 0
        # FA0D clears BG flags, not SP1FLG. Normal balls/games retain SP1.
        self.spinner_stage = 0
        self.effects = deque()
        self.scores = deque()
        self.presentations = set()
        self.busy_until = 0.0
        self.last_power = None
        self.center_completion = False
        self.fire_completion = False
        self.new_game = False
        self.match_audio_active = False
        self.high_score_audio_active = False
        self.extra_ball_presentation = False
        self.shooter_occupied = False
        self.shooter_due = None
        self.shooter_remaining = None
        self.machine.events.add_handler("firepower_electronic_sync", self._sync)
        self.machine.events.add_handler("game_started", self._game_started)
        self.machine.events.add_handler("player_added", self._player_added)
        self.machine.events.add_handler("firepower_match_sound", self._match_sound)
        self.machine.events.add_handler("firepower_match_audio_stop", self._match_audio_stop)
        self.machine.events.add_handler("firepower_high_score_sound", self._high_score_sound)
        self.machine.events.add_handler("firepower_high_score_audio_stop", self._high_score_audio_stop)

    def mode_start(self, **kwargs):
        self.generation += 1
        self.effects.clear()
        self.scores.clear()
        self.presentations.clear()
        self.busy_until = 0.0
        self.last_power = None
        self.center_completion = False
        self.fire_completion = False
        # L-6 683D clears 015A each ball; 6D88 recognizes both edges using
        # the two-tick 0157 timer. This is independent of MPF ball accounting.
        self.shooter_occupied = False
        self.shooter_due = None
        self.shooter_remaining = None
        self._send("start")
        if self.new_game:
            self.new_game = False
            self._emit(25)
            self._wait(1)
        bindings = {
            "s_plunger_active": (self._shooter_changed, {}),
            "s_plunger_inactive": (self._shooter_changed, {}),
            "sw_side_bumper_active": (self._score_event, {"command": 5, "count": 5}),
            "s_left_slingshot_active": (self._score_event, {"command": 5}),
            "s_right_slingshot_active": (self._score_event, {"command": 5}),
            "s_top_target_active": (self._score_event, {"command": 11}),
            "s_spinner_active": (self._spinner, {}),
            "lane_change_off_hit": (self._lane, {"new": True}),
            "lane_change_on_hit": (self._lane, {"new": False}),
            "fire_qualifier_off_hit": (self._center, {"new": True}),
            "fire_qualifier_lit_hit": (self._center, {"new": False}),
            "circle_target_group_hit": (self._power, {}),
            "mltp_lanes_done": (self._fire_complete, {}),
            "firepower_extra_ball_collected": (self._extra_ball, {}),
            "circle_target_group_hit_complete": (self._unresolved_completion, {}),
            "fire_qualifier_lit_complete": (self._unresolved_completion, {"center": True}),
            "left_shield_qualifier_lit_complete": (self._unresolved_completion, {"center": True}),
            "right_shield_qualifier_lit_complete": (self._unresolved_completion, {"center": True}),
        }
        for event, (handler, settings) in bindings.items():
            self.add_mode_event_handler(event, handler, priority=1000, **settings)
        for number in range(1, 5):
            self.add_mode_event_handler(f"s_pop_bumper_{number}_active", self._jet,
                                        priority=1000, number=number)
        for side in ("left", "right"):
            self.add_mode_event_handler(f"s_{side}_return_lane_active", self._return,
                                        priority=1000)
            self.add_mode_event_handler(f"s_{side}_out_lane_active", self._score_event,
                                        command=11)
        for number in range(1, 4):
            self.add_mode_event_handler(f"balldevice_bd_lock{number}_ball_entered",
                                        self._hole, number=number)
            self.add_mode_event_handler(
                f"multiball_lock_firepower_lock_{number}_locked_ball", self._lock)
        for name in ("award", "release"):
            self.add_mode_event_handler(f"firepower_background_{name}_started",
                                        self._presentation, name=name, started=True)
            self.add_mode_event_handler(f"firepower_background_{name}_stopped",
                                        self._presentation, name=name, started=False)
        self._shooter_changed()

    def _match_sound(self, **kwargs):
        # A narrow post-ball ownership window; no gameplay queue is revived.
        if not self.machine.game or not self.machine.game.ending or self.active:
            return
        self.generation += 1
        self.serial = 0
        self.match_audio_active = True
        self._send("start")
        self._emit(0x1c) # token9C -> FC36 -> FD30 -> F843, no speech selector

    def _match_audio_stop(self, **kwargs):
        if self.match_audio_active:
            self.match_audio_active = False
            self._send("stop")

    def _high_score_sound(self, **kwargs):
        if not self.machine.game or not self.machine.game.ending or self.active:
            return
        self._match_audio_stop()
        self.generation += 1
        self.serial = 0
        self.high_score_audio_active = True
        self._send("start")
        self._emit(0x0f, after_speech=True)  # Speech returns raw0F before APPEAR begins.

    def _high_score_audio_stop(self, **kwargs):
        if self.high_score_audio_active:
            self.high_score_audio_active = False
            self._send("stop")

    def _shooter_changed(self, **kwargs):
        occupied = self.machine.switch_controller.is_active(self.machine.switches["s_plunger"])
        self.delay.remove("shooter_transition")
        self.shooter_due = None
        self.shooter_remaining = None
        if occupied == self.shooter_occupied:
            return
        self.shooter_remaining = 2 * self.TICK
        self._resume_shooter()

    def _resume_shooter(self):
        # 6B7A/6BC4 hold RAM7A during release; 63FD pauses 0157 until
        # 6C48 clears RAM7A. Ordinary lock replacements have no such gate.
        if self.shooter_remaining is None or "release" in self.presentations:
            return
        self.shooter_due = self.machine.clock.get_time() + self.shooter_remaining
        self.delay.reset(name="shooter_transition", ms=self.shooter_remaining * 1000,
                         callback=self._shooter_settled)

    def _shooter_settled(self):
        self.shooter_due = None
        self.shooter_remaining = None
        if not self._live():
            return
        occupied = self.machine.switch_controller.is_active(self.machine.switches["s_plunger"])
        if occupied == self.shooter_occupied:
            return
        self.shooter_occupied = occupied
        if not occupied:
            # 6DB2 -> 6252 -> 63AB -> 71CB: immediate token94, no 3A/70
            # sound gate and no queue replacement or new foreground wait.
            self._emit(20)

    def _live(self):
        game = self.machine.game
        return self.active and game and not game.ending and not game.tilted

    def _game_started(self, **kwargs):
        # The first game's ball_starting loads this mode after game_started.
        self.new_game = True

    def _player_added(self, num, **kwargs):
        if num > 1 and self._live():
            self._emit(29)
            self._wait(1)

    def _gate(self, ticks=16):
        return not self.presentations and self.busy_until - self.machine.clock.get_time() < ticks * self.TICK

    def _score_event(self, command, count=1, **kwargs):
        if self._live():
            self.scores.extend([command] * count)
            self._request_pump()

    def _return(self, **kwargs):
        self._score_event(11, 3 if self.machine.game.player.return_lanes_lit else 1)

    def _jet(self, number, **kwargs):
        if not self._live():
            return
        player = self.machine.game.player
        lit = player.jet_bumpers_all or (
            player.jet_bumper_pair_left and number in (
                (2, 3) if player.jet_bumper_diagonal else (1, 4)))
        if self._gate():
            self._emit(10)
            self._wait(4)
        else:
            self._score_event(10, 10 if lit else 1)

    def _spinner(self, **kwargs):
        if not self._live():
            return
        if not self.machine.game.player.spinner_lit:
            if self._gate():
                self._emit(10)
                self._wait(4)
            else:
                self._score_event(10)
        else:
            if self._gate(32):
                self._emit_spinner()
                self._wait(31)
            self._score_event(11)

    def _lane(self, new, **kwargs):
        if not self._live():
            return
        if new and not self.fire_completion:
            self._replace_effects()
            self.effects.append((9, 32))
        self._score_event(11)

    def _fire_complete(self, **kwargs):
        # Completion replaces the ordinary newly-lit-lane effect. Token 8D
        # couples speech and electronics; its speech asset remains unproven.
        self._replace_effects()
        self.fire_completion = True
        self.delay.reset(name="fire_completion", ms=0,
                         callback=self._clear_fire_completion)
        self._wait(128)

    def _clear_fire_completion(self):
        self.fire_completion = False

    def _unresolved_completion(self, center=False, **kwargs):
        # Original bank completion replaces its ordinary queued effect. Keep
        # the score queue, but do not substitute a normal hit for an unresolved
        # completion presentation (97/noise or 86/qualification).
        self._replace_effects()
        if center:
            # Shot groups may post completion before their hit event. Retain
            # replacement ownership through this event cascade, then clear it.
            self.center_completion = True
            self.delay.reset(name="center_completion", ms=0,
                             callback=self._clear_center_completion)

    def _clear_center_completion(self):
        self.center_completion = False

    def _center(self, new, **kwargs):
        if not self._live():
            return
        if new:
            self._replace_effects()
            if not self.center_completion:
                self.effects.extend([(16, 5)] * 10)
            self._score_event(11)
        elif self._gate():
            self._emit(10)
            self._wait(4)
            self._score_event(10, 9)
        else:
            self._score_event(10, 10)

    def _extra_ball(self, **kwargs):
        if not self._live():
            return
        self._replace_effects()
        self.extra_ball_presentation = True
        # 6EC4 FB -> table608D indexB=84; 6EC7 overrides57 to23.
        self.effects.extend([(4, 10)] * 23)
        self._request_pump()

    def _finish_extra_ball(self):
        if self.extra_ball_presentation:
            self.extra_ball_presentation = False
            # Original saved FA toggles lamp flag27 when queue completes/replaces.
            self.machine.events.post("firepower_extra_ball_presentation_finished")

    def _replace_effects(self):
        self._finish_extra_ball()
        self.effects.clear()

    def _power(self, shot, **kwargs):
        if not self._live() or self.machine.game.player.power_lit:
            return
        if self.last_power == shot and self.effects:
            return
        self.last_power = shot
        self._replace_effects()
        self.effects.extend([(2, 5)] * 10)
        self._score_event(11)

    def _hole(self, number, new_balls=0, **kwargs):
        if new_balls and not self.machine.game.player[f"lock_{number}_lit"]:
            self._score_event(11)

    def _lock(self, **kwargs):
        if not self._live():
            return
        held = sum(self.machine.ball_devices[f"bd_lock{n}"].balls for n in range(1, 4))
        if held < 3:
            self._replace_effects()
            self.effects.append((3, 96))
            self._request_pump()
        # Third capture belongs to the existing multiball release presentation.

    def _presentation(self, name, started, **kwargs):
        if started:
            self.presentations.add(name)
            if name == "release" and self.shooter_due is not None:
                self.shooter_remaining = max(
                    0, self.shooter_due - self.machine.clock.get_time())
                self.shooter_due = None
                self.delay.remove("shooter_transition")
        else:
            self.presentations.discard(name)
            if name == "release":
                self._resume_shooter()
            self.busy_until = self.machine.clock.get_time()
            self._request_pump()

    def _request_pump(self):
        # Drain nested shot/award events before selecting the foreground effect.
        self.machine.events.post("firepower_audio_flush", callback=self._pump)

    def _pump(self, **kwargs):
        if not self._live() or self.presentations:
            return
        remaining = self.busy_until - self.machine.clock.get_time()
        if remaining > 0.000001:
            self.delay.reset(name="audio_queue", ms=remaining * 1000, callback=self._pump)
            return
        if self.effects:
            command, ticks = self.effects.popleft()
        elif self.scores:
            self._finish_extra_ball()
            command = self.scores.popleft()
            ticks = self.SCORE_DELAYS[command]
        else:
            self._finish_extra_ball()
            return
        self._emit(command)
        self._wait(ticks)

    def _wait(self, ticks):
        self.busy_until = self.machine.clock.get_time() + ticks * self.TICK
        self.delay.reset(name="audio_queue", ms=ticks * self.TICK * 1000, callback=self._pump)

    def _emit_spinner(self):
        self.spinner_stage = self.spinner_stage % 31 + 1
        self._emit(18, stage=self.spinner_stage)

    def _emit(self, command, **settings):
        self.serial += 1
        self.machine.events.post("firepower_electronic_command", raw_command=command)
        self._send("play", raw_command=command, token=0x80 | command, **settings)

    def _send(self, action, **settings):
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.bcp_trigger_client(
                client, "firepower_electronic", action=action,
                generation=self.generation, serial=self.serial, **settings)

    def _sync(self, **kwargs):
        self._send("start" if self._live() else "stop")

    def mode_stop(self, **kwargs):
        self._finish_extra_ball()
        self.delay.clear()
        self.effects.clear()
        self.scores.clear()
        self.presentations.clear()
        self._send("stop")
