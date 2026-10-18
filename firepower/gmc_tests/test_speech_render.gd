extends SceneTree
## Real mixer captures, not asset multiplication. Diagnostics live in /tmp.
var failures := 0
var captures := {}
var serial := 0
var output_dir := "/tmp/firepower-speech-after"
var baseline := false
var evaluating := false
var report := {}
const BEFORE_REPORT := "res://audio/speech_research/rendered_before.json"

func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)

func _initialize() -> void:
	baseline = "--baseline" in OS.get_cmdline_user_args()
	if baseline:
		output_dir = "/tmp/firepower-speech-before"
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output-dir="):
			output_dir = argument.trim_prefix("--output-dir=")
	call_deferred("run")

func tap(name: String, bus_name: String, position := -1) -> void:
	var effect := AudioEffectCapture.new()
	effect.buffer_length = 2.0
	AudioServer.add_bus_effect(AudioServer.get_bus_index(bus_name), effect, position)
	captures[name] = effect

func metrics(frames: PackedVector2Array, gain_db: float) -> Dictionary:
	var gain := db_to_linear(gain_db)
	var peak := 0.0
	var energies := []
	var counts := []
	var step := int(AudioServer.get_mix_rate() / 50.0)
	for start in range(0, frames.size(), step):
		var energy := 0.0
		var count := mini(step, frames.size() - start)
		for i in range(start, start + count):
			var sample := frames[i] * gain
			peak = maxf(peak, maxf(absf(sample.x), absf(sample.y)))
			energy += (sample.x * sample.x + sample.y * sample.y) / 2.0
		energies.append(energy / count)
		counts.append(count)
	var gate := maxf(pow(10.0, -50.0 / 10.0), float(energies.max()) * pow(10.0, -35.0 / 10.0)) if energies else 1.0
	var total := 0.0
	var active := 0
	for i in energies.size():
		if energies[i] >= gate:
			total += energies[i] * counts[i]
			active += counts[i]
	return {"peak_dbfs": linear_to_db(peak) if peak > 0 else -240.0,
		"active_rms_dbfs": linear_to_db(sqrt(total / active)) if active else -240.0,
		"active_frames": active, "captured_frames": frames.size()}

func record(server, label: String, raw: int, is_speech: bool, selector := -1) -> void:
	server.speech.reset_speech()
	server.electronic.reset_electronic()
	await create_timer(0.4).timeout # let dynamics release without truncating the capture
	for capture in captures.values():
		capture.clear_buffer()
	var player = server.speech if is_speech else server.electronic
	serial += 2
	player.apply_command({"action": "start", "generation": serial, "serial": 1})
	if is_speech:
		if label == "TWO":
			player.state = 1
		elif label == "THREE":
			player.state = 2
		if selector >= 0:
			if raw == 0x18:
				player.state = selector
			elif raw == 0x1b:
				player.irq_counter = (selector - 1) & 255
	player.apply_command({"action": "request" if is_speech else "play", "generation": serial, "serial": 2, "raw_command": raw})
	check(player.playing, "Production command actually starts " + label)
	check(player.volume_db == (1.0 if baseline else player.SPEECH_VOLUME_DB) if is_speech else player.volume_db == -3.0, "Live production player gain: " + label)
	var result := {"label": label, "category": "speech" if is_speech else "electronic", "raw": raw,
		"player_gain_db": player.volume_db, "player_path": str(player.get_path()),
		"bus": str(player.bus), "pitch_scale": player.pitch_scale,
		"stream_path": player.stream.resource_path, "duration": player.stream.get_length(), "taps": {}}
	var buffers := {}
	for name in captures:
		buffers[name] = PackedVector2Array()
	var deadline := Time.get_ticks_msec() + int((player.stream.get_length() + 0.25) * 1000)
	while Time.get_ticks_msec() < deadline:
		await process_frame
		for name in captures:
			var count: int = captures[name].get_frames_available()
			if count:
				buffers[name].append_array(captures[name].get_buffer(count))
	for name in captures:
		var frames: PackedVector2Array = buffers[name]
		check(frames.size() > 0 and captures[name].get_discarded_frames() == 0, "Complete actual mixer capture: " + label + "/" + name)
		var gain_db := AudioServer.get_bus_volume_db(0) if name == "master" else 0.0
		var measured := metrics(frames, gain_db)
		check(measured.active_frames > 0 if name == "master" or is_speech else true, "Non-silent production output: " + label + "/" + name)
		result.taps[name] = measured
		var file := FileAccess.open(output_dir + "/" + label + "_" + name + ".f32", FileAccess.WRITE)
		file.store_buffer(frames.to_byte_array())
		if is_speech and not baseline and name in ["voice", "master"]:
			check(float(measured.peak_dbfs) <= player.SPEECH_CEILING_DB + 0.001, "Rendered speech below limiter ceiling: " + label + "/" + name)
		if not baseline and not evaluating and name == "master" and is_speech:
			var previous: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BEFORE_REPORT))
			for before in previous.renders:
				if before.label == label:
					check(measured.active_rms_dbfs > before.taps.master.active_rms_dbfs + 5.0, "Material active RMS improvement: " + label)
		if not baseline and name == "master" and not is_speech:
			var previous: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BEFORE_REPORT))
			for before in previous.renders:
				if before.label == label:
					check(absf(measured.peak_dbfs - before.taps.master.peak_dbfs) < 0.05 and absf(measured.active_rms_dbfs - before.taps.master.active_rms_dbfs) < 0.25, "Electronic rendered level unchanged: " + label)
	if is_speech and not baseline:
		# Godot's predictive limiter adds a uniform 2 ms lookahead. Positive
		# gain reduction must preserve sample order and zero-crossing timing.
		var before_limit: PackedVector2Array = buffers.prelimit
		var after_limit: PackedVector2Array = buffers.voice
		var delay := int(ceil(AudioServer.get_mix_rate() * 0.002)) + 1
		var matches := 0
		var compared := 0
		for i in mini(before_limit.size(), after_limit.size() - delay):
			if absf(before_limit[i].x) > 0.0001:
				compared += 1
				if signf(before_limit[i].x) == signf(after_limit[i + delay].x):
					matches += 1
		check(compared > 0 and float(matches) / compared > 0.999, "Limiter preserves waveform timing apart from uniform lookahead: " + label)
		result["limiter_delay_frames"] = delay
	report.renders.append(result)
	FileAccess.open(output_dir + "/report.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))

func run() -> void:
	DirAccess.make_dir_recursive_absolute(output_dir)
	var server = root.get_node("MPF").server
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--balance-db="):
			server.speech.balance.volume_db = float(argument.trim_prefix("--balance-db="))
	var buses := {}
	for name in ["voice", "effects", "music", "Master"]:
		var index := AudioServer.get_bus_index(name)
		buses[name] = {"gain_db": AudioServer.get_bus_volume_db(index), "send": str(AudioServer.get_bus_send(index)), "effects": []}
		for slot in AudioServer.get_bus_effect_count(index):
			buses[name].effects.append(AudioServer.get_bus_effect(index, slot).get_class())
	var voice_effects: Array = buses.voice.effects
	check(voice_effects == ["AudioEffectHighPassFilter", "AudioEffectEQ10", "AudioEffectCompressor", "AudioEffectAmplify", "AudioEffectHardLimiter"] or (baseline and voice_effects.is_empty()), "Production voice effect routing")
	# Allows reproducible bypass A/B after the historical no-DSP capture.
	# This is test-only; the production controller never bypasses effects.
	if baseline:
		for slot in AudioServer.get_bus_effect_count(AudioServer.get_bus_index("voice")):
			AudioServer.set_bus_effect_enabled(AudioServer.get_bus_index("voice"), slot, false)
	for name in ["effects", "music", "Master"]:
		check(buses[name].effects.is_empty(), "No speech DSP on " + name)
	var speech_players := 0
	for node in server.get_children():
		if node.get_script() == server.speech.get_script():
			speech_players += 1
	check(speech_players == 1, "One production speech controller, no duplicated player")
	report = {"baseline": baseline, "driver": AudioServer.get_driver_name(), "mix_rate": AudioServer.get_mix_rate(),
		"buses": buses, "speech_players": speech_players, "renders": [],
		"method": "Actual AudioEffectCapture stereo float32; voice tap after DSP before voice fader; Master tap before Master fader, metrics include that fader mathematically."}
	if not baseline:
		report["settings"] = {"player_db": server.speech.volume_db, "makeup_db": server.speech.compressor.gain,
			"balance_db": server.speech.balance.volume_db, "low_cut_hz": server.speech.highpass.cutoff_hz,
			"presence_gains_db": server.speech.SPEECH_PRESENCE_GAINS_DB,
			"threshold_db": server.speech.compressor.threshold, "ratio": server.speech.compressor.ratio,
			"attack_us": server.speech.compressor.attack_us, "release_ms": server.speech.compressor.release_ms,
			"limiter_db": server.speech.limiter.ceiling_db, "limiter_release_s": server.speech.limiter.release}
	tap("voice", "voice")
	tap("master", "Master")
	if not baseline:
		tap("prelimit", "voice", 4)
		tap("compout", "voice", 3)
		tap("input", "voice", 2)
		tap("raw", "voice", 0)
	for request in [["FIRE", 13], ["POWER", 26], ["FIRE_ONE", 24], ["TWO", 24], ["THREE", 24], ["MISSION_ACCOMPLISHED", 12]]:
		await record(server, request[0], request[1], true)
	if "--all-phrases" in OS.get_cmdline_user_args() and not baseline:
		var seen := {}
		for rendered in report.renders:
			seen[rendered.stream_path] = true
		for key in server.speech.model.commands:
			var command: Dictionary = server.speech.model.commands[key]
			if not command.speech:
				continue
			var path: String = "res://" + server.speech.model.phrases[command.phrase].production_file
			if path in seen:
				continue
			seen[path] = true
			var parts: PackedStringArray = key.split("_")
			await record(server, command.phrase, parts[0].hex_to_int(), true, int(parts[1]))
		check(seen.size() == 23, "Actual mixer capture covers all 23 speech phrases")
	for request in [["SCORING", 5], ["JET", 10], ["LAUNCH", 20]]:
		await record(server, request[0], request[1], false)
	server._sync_background()
	check(not server.speech.playing and server.speech.stream == null, "Capture cleanup preserves production cleanup")
	# Include actual DSP output in the disconnect check, after mixer/lookahead
	# buffers drain. A stopped phrase must not leave persistent voice audio.
	server.speech.apply_command({"action": "start", "generation": 9999, "serial": 1})
	server.speech.apply_command({"action": "request", "generation": 9999, "serial": 2, "raw_command": 13})
	await create_timer(0.1).timeout
	server.on_disconnect()
	await create_timer(0.3).timeout
	captures.voice.clear_buffer()
	await create_timer(0.1).timeout
	var tail: PackedVector2Array = captures.voice.get_buffer(captures.voice.get_frames_available())
	check(tail.size() > 0 and metrics(tail, 0.0).active_frames == 0, "Disconnect leaves actual speech bus silent")
	if not baseline:
		await check_latency(server.speech)
	for name in ["voice", "Master"]:
		var index := AudioServer.get_bus_index(name)
		for slot in range(AudioServer.get_bus_effect_count(index) - 1, -1, -1):
			if AudioServer.get_bus_effect(index, slot) in captures.values():
				AudioServer.remove_bus_effect(index, slot)
	if baseline:
		for slot in AudioServer.get_bus_effect_count(AudioServer.get_bus_index("voice")):
			AudioServer.set_bus_effect_enabled(AudioServer.get_bus_index("voice"), slot, true)
	report["failures"] = failures
	FileAccess.open(output_dir + "/report.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	quit(1 if failures else 0)

func check_latency(player) -> void:
	# A diagnostic native-rate impulse measures actual EQ/filter/limiter
	# latency without touching a phrase asset or adding another player.
	var impulse := AudioStreamWAV.new()
	impulse.format = AudioStreamWAV.FORMAT_16_BITS
	impulse.mix_rate = int(AudioServer.get_mix_rate())
	var pcm := PackedByteArray()
	pcm.resize(impulse.mix_rate / 5 * 2)
	pcm.encode_s16(1024, 8192)
	impulse.data = pcm
	for capture in captures.values():
		capture.clear_buffer()
	player.stream = impulse
	player.play()
	await create_timer(0.3).timeout
	var input: PackedVector2Array = captures.raw.get_buffer(captures.raw.get_frames_available())
	var output: PackedVector2Array = captures.voice.get_buffer(captures.voice.get_frames_available())
	var in_peak := 0
	var out_peak := 0
	for i in input.size():
		if absf(input[i].x) > absf(input[in_peak].x):
			in_peak = i
	for i in output.size():
		if absf(output[i].x) > absf(output[out_peak].x):
			out_peak = i
	var latency := 1000.0 * (out_peak - in_peak) / AudioServer.get_mix_rate()
	check(input.size() > 0 and output.size() > 0 and latency >= 0.0 and latency < 4.0, "Actual voice DSP impulse peak latency below 4 ms")
	report["impulse_peak_latency_ms"] = latency
	player.reset_speech()
