extends SceneTree
## Run headlessly with --script res://gmc_tests/test_fp03.gd.
var failures: int = 0
var finished_count: int = 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	# Exercise the real controller created by the configured GMC server override.
	var mpf = root.get_node("MPF")
	var player = mpf.server.background
	var player_id = player.get_instance_id()
	var original_children = mpf.server.get_child_count()
	var bus_volumes: Array[float] = []
	for index in range(AudioServer.bus_count):
		bus_volumes.append(AudioServer.get_bus_volume_db(index))
	check(player.stream is AudioStreamWAV, "Production FP03 must use WAV")
	check(player.stream.format == AudioStreamWAV.FORMAT_16_BITS, "WAV import must preserve PCM")
	check(player.stream.loop_mode == AudioStreamWAV.LOOP_FORWARD, "Native forward loop")
	check(player.SOURCE == "res://sounds/fx/FP03.wav", "Permanent production source")
	check(FileAccess.get_sha256(player.SOURCE) == "83c5c331d7208725b280e8df64c2394ddd31d4e53c79923f3485c617f7d03677", "Physically approved production WAV")
	var pcm_hash = HashingContext.new()
	pcm_hash.start(HashingContext.HASH_SHA256)
	pcm_hash.update(player.stream.data)
	check(pcm_hash.finish().hex_encode() == "26472ba369cd90caf35c46433412db5e5f01e22abf05eb1e428d393c9dd11506", "Imported PCM matches approved loop")
	var expected_frames = 135496
	check(player.stream.loop_begin == 0 and player.stream.loop_end == expected_frames, "Full production frame loop")
	check(player.stream.data.size() == expected_frames * 2, "Uncompressed mono source frames")
	check(player.stream.mix_rate == 22050 and not player.stream.stereo, "Source rate/channels unchanged")
	check(is_equal_approx(player.volume_db, -3.0), "FP03-only attenuation")
	check(player.finished.get_connections().is_empty(), "No finished/restart handler")
	player.finished.connect(func(): finished_count += 1)
	check(not player.playing, "FP03 must be silent before a start command")
	var start = {"action": "start", "cycle": 1, "rate": 0.85, "ramp_ms": 150}
	player.apply_command(start)
	await create_timer(0.1).timeout
	check(player.playing and player.stream.loop_mode == AudioStreamWAV.LOOP_FORWARD, "FP03 must loop")
	check(player.bus == &"music" and player.max_polyphony == 1, "One background on the music bus")
	check(is_equal_approx(player.pitch_scale, 0.85), "Start rate")
	var playback = player.get_stream_playback()
	var position = player.get_playback_position()
	player.apply_command(start)
	check(player.get_stream_playback() == playback, "Repeated start must not replace playback")
	player.apply_command({"action": "rate", "cycle": 1, "rate": 1.1, "ramp_ms": 150})
	player.rate_tween.pause()
	player.rate_tween.custom_step(0.05)
	check(player.pitch_scale > 0.85 and player.pitch_scale < 1.1, "Rate must interpolate")
	player.apply_command({"action": "rate", "cycle": 1, "rate": 1.25, "ramp_ms": 150})
	player.rate_tween.pause()
	player.rate_tween.custom_step(0.2)
	await create_timer(0.2).timeout
	check(is_equal_approx(player.pitch_scale, 1.25), "Target rate applied")
	check(player.get_stream_playback() == playback, "Rate changes must preserve live playback")
	check(player.get_playback_position() > position, "Position must continue through rate changes")
	# ROM stages 32-36 drop into a common slow region without a new stream.
	for stage in range(32, 37):
		player.apply_command({"action": "rate", "cycle": 1, "stage": stage, "rate": 0.85, "ramp_ms": 150})
		player.rate_tween.pause()
		player.rate_tween.custom_step(0.2)
		check(is_equal_approx(player.pitch_scale, 0.85), "Slow-region rate applied")
		check(player.get_stream_playback() == playback, "Slow states preserve playback")
	player.apply_command({"action": "rate", "cycle": 1, "stage": 1, "rate": 0.85, "ramp_ms": 150})
	check(player.get_stream_playback() == playback, "36 to 1 wrap preserves playback")
	# Observe two actual native wraps (no seek/restart between them). Change pitch
	# shortly before the first boundary and after it, then hold across the second.
	var changed_before_wrap = false
	var wraps = 0
	var previous_position = player.get_playback_position()
	var deadline = Time.get_ticks_msec() + 20000
	while wraps < 2 and Time.get_ticks_msec() < deadline:
		await process_frame
		check(player.playing, "Playback must never stop at loop boundary")
		check(player.get_instance_id() == player_id, "Same player across loops")
		check(player.get_stream_playback() == playback, "Same playback across loops")
		var current_position = player.get_playback_position()
		if not changed_before_wrap and current_position >= player.stream.get_length() - 0.3:
			changed_before_wrap = true
			player.apply_command({"action": "rate", "cycle": 1, "rate": 1.1, "ramp_ms": 150})
		if current_position < previous_position - 0.5:
			wraps += 1
			check(is_equal_approx(player.pitch_scale, 1.1 if wraps == 1 else 1.25), "Pitch survives wrap")
			if wraps == 1:
				player.apply_command({"action": "rate", "cycle": 1, "rate": 1.25, "ramp_ms": 150})
				check(is_equal_approx(player.pitch_scale, 1.1), "Post-loop change starts without pitch jump")
		previous_position = current_position
	check(wraps == 2, "Observe two natural loop boundaries")
	check(finished_count == 0, "Native looping must not emit finished")
	check(mpf.server.get_child_count() == original_children, "No second FP03 player")
	check(is_equal_approx(player.volume_db, -3.0), "Attenuation survives loops")
	for index in range(AudioServer.bus_count):
		check(is_equal_approx(AudioServer.get_bus_volume_db(index), bus_volumes[index]), "Bus volumes unchanged")
	player.apply_command({"action": "stop"})
	check(not player.playing and player.rate_tween == null, "Stop clears playback and tween")
	player.apply_command({"action": "rate", "cycle": 1, "rate": 1.25, "ramp_ms": 150})
	check(not player.playing, "Rate command cannot start stopped playback")
	start.cycle = 2
	player.apply_command(start)
	check(is_equal_approx(player.pitch_scale, 0.85), "New cycle resets rate")
	mpf.server.on_disconnect()
	check(not player.playing, "Disconnect stops background")
	print("FP03 GMC checks complete: %d failures" % failures)
	quit(1 if failures else 0)
