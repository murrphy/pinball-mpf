extends SceneTree
## Integration and real-mixer A/B using the production server and players.
var failures := 0
var serial := 0
var speech
var electronic
var taps := {}
var report := {"renders": []}

func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)

func send(raw: int) -> void:
	serial += 1
	speech.apply_command({"action": "request", "generation": 100, "serial": serial, "raw_command": raw})

func _initialize() -> void:
	call_deferred("run")

func rms(frames: PackedVector2Array, start: int, end: int) -> float:
	var energy := 0.0
	for i in range(start, mini(end, frames.size())):
		energy += frames[i].length_squared() / 2.0
	return linear_to_db(sqrt(energy / (mini(end, frames.size()) - start)))

func render(server, raw: int, duck: bool) -> Dictionary:
	server.on_disconnect()
	if not duck:
		speech.speech_active.disconnect(electronic.set_speech_active)
	await create_timer(0.4).timeout
	for tap in taps.values():
		tap.clear_buffer()
	speech.apply_command({"action": "start", "generation": 100, "serial": 0})
	serial = 0
	electronic.apply_command({"action": "start", "generation": 100})
	electronic.apply_command({"action": "play", "generation": 100, "serial": 1, "raw_command": 20})
	send(raw)
	var duration: float = speech.stream.get_length()
	var buffers := {}
	for name in taps:
		buffers[name] = PackedVector2Array()
	var deadline := Time.get_ticks_msec() + int((duration + 0.3) * 1000)
	while Time.get_ticks_msec() < deadline:
		await process_frame
		for name in taps:
			buffers[name].append_array(taps[name].get_buffer(taps[name].get_frames_available()))
	var row := {"raw": raw, "duck": duck, "buses": {}}
	var rate := AudioServer.get_mix_rate()
	for name in taps:
		var frames: PackedVector2Array = buffers[name]
		check(taps[name].get_discarded_frames() == 0 and frames.size() > rate, "Complete simultaneous mixer capture")
		var peak := 0.0
		for frame in frames:
			peak = maxf(peak, maxf(absf(frame.x), absf(frame.y)))
		row.buses[name] = {"rms_dbfs_100_to_600ms": rms(frames, int(rate * 0.1), int(rate * 0.6)), "sample_peak_dbfs": linear_to_db(peak)}
		FileAccess.open("/tmp/firepower-duck/%s_%s_%s.f32" % [raw, duck, name], FileAccess.WRITE).store_buffer(frames.to_byte_array())
	check(electronic.volume_db == electronic.VOLUME_DB, "Natural phrase end returns exact foreground gain")
	if not duck:
		speech.speech_active.connect(electronic.set_speech_active)
	return row

func envelope(duration_ms: int) -> Array:
	var trace := []
	var began := Time.get_ticks_usec()
	while Time.get_ticks_usec() - began < duration_ms * 1000:
		trace.append({"ms": (Time.get_ticks_usec() - began) / 1000.0, "volume_db": electronic.volume_db})
		await process_frame
	trace.append({"ms": (Time.get_ticks_usec() - began) / 1000.0, "volume_db": electronic.volume_db})
	return trace

func run() -> void:
	var server = root.get_node("MPF").server
	speech = server.speech
	electronic = server.electronic
	await create_timer(0.2).timeout # allow startup frame/tween clock to settle
	check(speech.SPEECH_BALANCE_DB == 4.0, "Retain natural cabinet speech balance")
	check(electronic.volume_db == -3.0 and not electronic.speech_ducked, "No speech means original gain")
	var voice_gain: float = speech.volume_db
	var bonus_gain: float = server.bonus_audio.volume_db
	var background_gain: float = server.background.volume_db
	var bus_gains := []
	for i in AudioServer.bus_count:
		bus_gains.append(AudioServer.get_bus_volume_db(i))
	speech.apply_command({"action": "start", "generation": 100, "serial": 0})
	electronic.apply_command({"action": "start", "generation": 100})
	electronic.apply_command({"action": "play", "generation": 100, "serial": 1, "raw_command": 20})
	var playback = electronic.get_stream_playback()
	# FP03's pre-existing monophonic mask is already applied before speech begins.
	background_gain = server.background.volume_db
	send(0x18)
	report["attack_envelope"] = await envelope(60)
	check(electronic.volume_db == -8.0 and electronic.speech_ducked, "Speech ramps only foreground to -8 dB")
	check(electronic.get_stream_playback() == playback and electronic.command == 20 and electronic.serial == 1, "Ducking never interrupts/restarts electronic playback")
	check(speech.volume_db == voice_gain and speech.balance.volume_db == 4.0, "Speech gain/processing unchanged")
	check(server.bonus_audio.volume_db == bonus_gain and server.background.volume_db == background_gain, "FA64 and existing FP03 mask unchanged")
	for i in AudioServer.bus_count:
		check(AudioServer.get_bus_volume_db(i) == bus_gains[i], "No bus or Master attenuation")
	send(0x18) # protected phrase queues TWO in the original single input latch
	var until := Time.get_ticks_msec() + 1750
	while Time.get_ticks_msec() < until:
		await process_frame
		check(electronic.volume_db == -8.0, "Whole FIRE ONE and queued TWO stay continuously ducked")
	check(speech.state == 2 and speech.command == 0x18, "Original counting/latch timing retained")
	await create_timer(0.8).timeout
	check(electronic.volume_db == -3.0 and not electronic.speech_ducked, "Natural completion restores exact normal gain")
	send(0x0d)
	await create_timer(0.05).timeout
	speech._completed()
	report["release_envelope"] = await envelope(220)
	check(electronic.volume_db == -3.0, "Measured release ends at exact normal level")
	send(0x0d)
	await create_timer(0.05).timeout
	speech._completed() # deterministic completion starts a release
	await create_timer(0.03).timeout
	var during_release: float = electronic.volume_db
	send(0x0c)
	await process_frame
	check(electronic.volume_db <= during_release and electronic.speech_ducked, "New phrase reverses release without rising toward full level")
	await create_timer(0.05).timeout
	check(electronic.volume_db == -8.0, "Renewed phrase remains ducked")
	speech.clear_speech()
	check(electronic.volume_db == -3.0 and not electronic.speech_ducked, "Cancellation immediately restores gain")
	send(0x07)
	await create_timer(0.05).timeout
	server._sync_background()
	check(electronic.volume_db == -3.0 and not electronic.speech_ducked, "BCP reset cannot leave attenuation")
	# Measure actual simultaneous output with the same DSP in both A/B captures.
	DirAccess.make_dir_recursive_absolute("/tmp/firepower-duck")
	for name in ["effects", "voice", "Master"]:
		var tap := AudioEffectCapture.new()
		tap.buffer_length = 2.0
		AudioServer.add_bus_effect(AudioServer.get_bus_index(name), tap)
		taps[name] = tap
	for raw in [0x18, 0x0c]:
		var normal := await render(server, raw, false)
		var ducked := await render(server, raw, true)
		report.renders.append(normal)
		report.renders.append(ducked)
		var attenuation: float = ducked.buses.effects.rms_dbfs_100_to_600ms - normal.buses.effects.rms_dbfs_100_to_600ms
		check(absf(attenuation + 5.0) < 0.3, "Actual simultaneous foreground attenuation approximately 5 dB")
		check(absf(ducked.buses.voice.rms_dbfs_100_to_600ms - normal.buses.voice.rms_dbfs_100_to_600ms) < 0.3, "Actual simultaneous voice level unchanged")
	server.on_disconnect()
	check(electronic.volume_db == -3.0, "Disconnect restoration")
	for name in taps:
		var index := AudioServer.get_bus_index(name)
		AudioServer.remove_bus_effect(index, AudioServer.get_bus_effect_count(index) - 1)
	speech.apply_command({"action": "start", "generation": 100, "serial": 0})
	serial = 0
	send(0x0d)
	await create_timer(0.05).timeout
	speech.queue_free()
	await process_frame
	check(electronic.volume_db == -3.0 and not electronic.speech_ducked, "Speech controller teardown restores surviving foreground")
	report["failures"] = failures
	report["mix_rate"] = AudioServer.get_mix_rate()
	FileAccess.open("/tmp/firepower-duck/report.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	quit(1 if failures else 0)
