extends SceneTree
var failures: int = 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func digest(data: PackedByteArray) -> String:
	var hash = HashingContext.new()
	hash.start(HashingContext.HASH_SHA256)
	if not data.is_empty():
		hash.update(data)
	return hash.finish().hex_encode()

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var mpf = root.get_node("MPF")
	var player = mpf.server.bonus_audio
	var background = mpf.server.background
	var renderer = player.renderer
	var checks = JSON.parse_string(FileAccess.get_file_as_string("res://audio/bonus_research/dac_checks.json"))
	for stage in range(1, 148):
		var bytes = PackedByteArray()
		for event in renderer.dac_events(stage):
			var offset = bytes.size()
			bytes.resize(offset + 5)
			bytes.encode_u32(offset, int(event[0]))
			bytes[offset + 4] = int(event[1])
		check(digest(bytes) == checks[str(stage)], "ROM DAC values/timing stage %d" % stage)
	var pcm_checks = JSON.parse_string(FileAccess.get_file_as_string("res://audio/bonus_research/render_checks.json"))
	for stage in pcm_checks:
		var audio = renderer.render(int(stage))
		check(audio.data.size() == int(pcm_checks[stage].frames) * 2, "Rendered length " + stage)
		check(digest(audio.data) == pcm_checks[stage].sha256, "Independent integrated PCM " + stage)
	check(is_equal_approx(renderer.relative_pitch(1), 1.0), "Initial pitch")
	check(is_equal_approx(renderer.relative_pitch(145), 23.4253785), "Final valid original pitch")
	check(renderer.render(147) == null, "Exhausted period is silent")
	check(not player.playing and not player.collecting, "Silent in attract")
	var children = mpf.server.get_child_count()
	background.apply_command({"action": "start", "cycle": 900, "rate": 0.85})
	var background_playback = background.get_stream_playback()
	player.apply_command({"action": "step", "cycle": 1, "step": 1})
	check(not player.playing, "Step cannot activate bonus outside collection")
	player.apply_command({"action": "start", "cycle": 1, "step": 0})
	check(not player.playing and player.collecting, "Start arms without playing")
	player.apply_command({"action": "step", "cycle": 1, "step": 1})
	var first_stream = player.stream
	check(player.playing and player.max_polyphony == 1 and player.bus == &"effects", "One bonus voice")
	player.apply_command({"action": "step", "cycle": 1, "step": 1})
	check(player.stream == first_stream, "Duplicate counted step cannot retrigger")
	player.apply_command({"action": "step", "cycle": 1, "step": 29})
	player.stop() # Simulate a finished burst/pass pause without changing eligibility.
	player.apply_command({"action": "step", "cycle": 1, "step": 30})
	check(player.step == 30 and player.playing, "Pitch continues across a silent pass pause")
	check(player.pitch_scale == 1.0, "Timing model replaces uniform pitch resampling")
	check(mpf.server.get_child_count() == children, "No accumulating players")
	check(background.get_stream_playback() == background_playback, "FP03 playback unaffected")
	player.apply_command({"action": "stop", "cycle": 1})
	check(not player.playing and player.stream == null, "Completion cleans up")
	player.apply_command({"action": "start", "cycle": 1})
	player.apply_command({"action": "step", "cycle": 1, "step": 31})
	check(not player.playing and not player.collecting, "Stale commands cannot revive bonus")
	player.apply_command({"action": "start", "cycle": 2})
	player.apply_command({"action": "step", "cycle": 2, "step": 1})
	player.apply_command({"action": "stop", "cycle": 1})
	check(player.playing, "Old stop cannot terminate a new collection")
	mpf.server.on_disconnect()
	check(not player.playing and not player.collecting, "Disconnect stops bonus")
	player.apply_command({"action": "start", "cycle": 3})
	player.apply_command({"action": "step", "cycle": 3, "step": 2})
	mpf.server._sync_background()
	check(not player.playing and not player.collecting, "Reset stops bonus pending fresh sync")
	player.apply_command({"action": "start", "cycle": 1})
	player.apply_command({"action": "step", "cycle": 1, "step": 1})
	check(player.playing, "New MPF process may restart generation numbering after reset")
	player.stop_bonus()
	# Measure the entire former 39x5 range, including the exhausted tail.
	var trace = FileAccess.open("/tmp/firepower-fa64-full-range.csv", FileAccess.WRITE)
	trace.store_line("step,period,relative_cycle_pitch,cycle_hz,pitch_scale,source_ms,effective_ms,rms_pcm,next_trigger_ms")
	for stage in range(1, 196):
		var audio = renderer.render(stage)
		var rms: float = 0.0
		var duration: float = 0.0
		if audio:
			duration = audio.get_length() * 1000.0
			for offset in range(0, audio.data.size(), 2):
				var value: float = audio.data.decode_s16(offset)
				rms += value * value
			rms = sqrt(rms / (audio.data.size() / 2))
		check((audio != null) == (stage <= 146), "Full former range cutoff %d" % stage)
		var hz = renderer.relative_pitch(stage) * 895000.0 / 64982.0
		trace.store_line("%d,%d,%.9f,%.9f,1,%.6f,%.6f,%.3f,%.6f" % [
			stage, 147 - stage if audio else 0, renderer.relative_pitch(stage),
			hz, duration, duration, rms, 165.448 if stage % 39 == 0 and stage < 195 else 66.368])
	trace.close()
	# Exercise every actual player command at the unchanged legal 29x5 cadence.
	player.apply_command({"action": "start", "cycle": 1000})
	for stage in range(1, 146):
		player.apply_command({"action": "step", "cycle": 1000, "step": stage})
		check(player.step == stage and player.playing and player.stream != null,
			"Legal maximum has a playable burst at %d" % stage)
		check(player.pitch_scale == 1.0, "No pitch clamp/resampling at %d" % stage)
		var audio = player.stream
		var energy: float = 0.0
		var active_frames: int = 0
		for offset in range(0, audio.data.size(), 2):
			var value: float = audio.data.decode_s16(offset)
			energy += value * value
			if absf(value) > 100.0:
				active_frames += 1
		check(sqrt(energy / (audio.data.size() / 2)) > 1000.0,
			"Nontrivial PCM RMS at %d" % stage)
		check(active_frames > 480, "Over 10ms of active PCM at %d" % stage)
		var period: int = 147 - stage
		check(renderer.dac_events(stage)[1][0] - renderer.dac_events(stage)[0][0]
			== 6 * period + 25, "ROM period progression at %d" % stage)
		await create_timer(0.165448 if stage % 29 == 0 and stage < 145 else 0.066368).timeout
	player.apply_command({"action": "stop", "cycle": 1000})
	check(not player.playing and player.stream == null, "Legal maximum stops cleanly")
	print("FA64 bonus audio checks: %d failures" % failures)
	quit(1 if failures else 0)
