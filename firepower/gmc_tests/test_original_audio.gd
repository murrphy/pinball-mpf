extends SceneTree
var failures := 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func digest(bytes: PackedByteArray) -> String:
	var hash := HashingContext.new()
	hash.start(HashingContext.HASH_SHA256)
	hash.update(bytes)
	return hash.finish().hex_encode()

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var mpf = root.get_node("MPF")
	var player = mpf.server.electronic
	var background = mpf.server.background
	var bonus = mpf.server.bonus_audio
	check(player.max_polyphony == 1 and player.bus == &"effects", "One electronic foreground voice")
	for state in player.renderer.model.states:
		var result: Dictionary = player.renderer.dac_events(int(state.stage))
		var bytes := PackedByteArray()
		bytes.resize(result.events.size() * 5)
		for index in range(result.events.size()):
			bytes.encode_u32(index * 5, result.events[index][0])
			bytes[index * 5 + 4] = result.events[index][1]
		check(digest(bytes) == state.dac_sha256, "SP1 exact DAC schedule state %s" % state.stage)
		check(result.cycles == int(state.cycles), "SP1 exact return cycle")
		var stream: AudioStreamWAV = player.renderer.render(int(state.stage))
		check(stream.loop_mode == AudioStreamWAV.LOOP_FORWARD and stream.loop_begin > 0, "One initialization then native VARI loop")
		check(stream.mix_rate == 48000 and stream.format == AudioStreamWAV.FORMAT_16_BITS, "SP1 PCM format")
	for source in player.sources.effects:
		var path: String = "res://" + source.production_file
		check(FileAccess.get_sha256(path) == source.wav_sha256, "ROM-derived WAV identity")
		var stream: AudioStreamWAV = load(path)
		check(stream.format == AudioStreamWAV.FORMAT_16_BITS, "Lossless import")
		check(digest(stream.data) == source.pcm_sha256, "Imported PCM equals derived source")
	background.apply_command({"action": "start", "cycle": 1, "rate": 0.85, "ramp_ms": 0})
	var background_playback = background.get_stream_playback()
	player.apply_command({"action": "start", "generation": 1})
	player.apply_command({"action": "play", "generation": 1, "serial": 1, "raw_command": 18, "stage": 1})
	await create_timer(0.05).timeout
	check(player.playing and player.spinner_stage == 1 and player.pitch_scale == 1.0, "SP1 playback")
	check(background.playing and background.get_stream_playback() == background_playback and background.volume_db == -80.0, "Foreground masks sound without changing FP03 playback")
	var first = player.get_stream_playback()
	player.apply_command({"action": "play", "generation": 1, "serial": 1, "raw_command": 18, "stage": 2})
	check(player.get_stream_playback() == first and player.spinner_stage == 1, "Duplicate packet is idempotent")
	player.apply_command({"action": "play", "generation": 1, "serial": 2, "raw_command": 18, "stage": 2})
	check(player.get_stream_playback() != first and player.spinner_stage == 2, "Accepted spinner command interrupts/restarts")
	# Exercise the actual existing voice bus alongside electronic audio.
	mpf.media.sound.play_sounds({"settings": {"fire": {"bus": "voice"}}, "context": "audio_test"})
	check(player.playing and mpf.media.sound.buses.voice.channels[0].playing, "Speech has independent playback")
	player.apply_command({"action": "play", "generation": 1, "serial": 3, "raw_command": 5})
	check(player.command == 5 and player.stream.loop_mode == AudioStreamWAV.LOOP_DISABLED, "Finite command interrupts continuous spinner")
	await create_timer(player.stream.get_length() + 0.5).timeout
	check(not player.playing and is_equal_approx(background.volume_db, background.VOLUME_DB), "Natural completion resumes existing background (playing=%s, volume=%s)" % [player.playing, background.volume_db])
	player.apply_command({"action": "play", "generation": 1, "serial": 4, "raw_command": 18, "stage": 31})
	await create_timer(1.0).timeout
	check(player.playing and player.spinner_stage == 31, "Spinner remains continuous through natural loop wraps")
	var spinner_playback = player.get_stream_playback()
	player.apply_command({"action": "play", "generation": 1, "serial": 5, "raw_command": 20})
	check(player.command == 20 and player.playing and player.get_stream_playback() != spinner_playback, "Launch TURBO interrupts existing electronic foreground")
	check(player.stream.loop_mode == AudioStreamWAV.LOOP_DISABLED and player.pitch_scale == 1.0, "Launch is an unscaled finite one-shot")
	check(digest(player.stream.data) == "6434460405224cb3561f64382ac7ec57691a6359af5a69e5272bb4ae8a5aeb6d", "Launch PCM matches original F8D1 execution with seed3C00")
	check(background.get_stream_playback() == background_playback and background.volume_db == -80.0, "Launch uses existing foreground masking")
	var launch_playback = player.get_stream_playback()
	player.apply_command({"action": "play", "generation": 1, "serial": 6, "raw_command": 10})
	check(player.command == 10 and player.get_stream_playback() != launch_playback, "Next scoring sound interrupts launch in the same voice")
	player.apply_command({"action": "play", "generation": 1, "serial": 7, "raw_command": 4})
	check(player.playing and player.command == 4, "Extra Ball GW04 uses existing monophonic foreground")
	check(digest(player.stream.data) == "ddd3c4e4be5835855f6c8a0bf07cfac522fc6efabce869e79246568d89c489c9", "Extra Ball PCM matches original FE76/FAEE")
	var mission_speech = mpf.server.speech
	mission_speech.apply_command({"action": "start", "generation": 1, "serial": 1})
	mission_speech.apply_command({"action": "request", "generation": 1, "serial": 2, "raw_command": 8})
	check(mission_speech.playing and mission_speech.phrase == mission_speech.model.commands["08_0"].phrase, "Award starts existing YOU WON ONE MISSION phrase")
	var mission_playback = mission_speech.get_stream_playback()
	player.apply_command({"action": "play", "generation": 1, "serial": 8, "raw_command": 4})
	check(player.command == 4 and mission_speech.get_stream_playback() == mission_playback, "GW04 retrigger retains independent speech")
	player.apply_command({"action": "play", "generation": 1, "serial": 9, "raw_command": 10})
	check(player.command == 10, "Scoring interrupts GW04 in same electronic voice")
	mission_speech.clear_speech()
	player.apply_command({"action": "play", "generation": 1, "serial": 10, "raw_command": 28})
	check(player.playing and player.command == 28, "Match raw1C uses original electronic foreground")
	check(player.stream.loop_mode == AudioStreamWAV.LOOP_DISABLED and player.pitch_scale == 1.0, "Match is a finite unscaled VARI3")
	check(digest(player.stream.data) == "827c5affe80c5f8dff4859a4ab08ebf458d83b98f8b4bcad31852a93a20b9828", "Match PCM matches FD30/F843 ROM execution")
	check(not mission_speech.model.commands["1c_0"].speech and not mission_speech.playing, "Match raw1C has no speech selector")
	player.apply_command({"action": "stop", "generation": 1})
	check(not player.playing and player.stream == null, "Cleanup clears foreground stream")
	bonus.apply_command({"action": "start", "cycle": 1, "step": 0})
	bonus.apply_command({"action": "step", "cycle": 1, "step": 1})
	check(bonus.playing and not player.playing, "Bonus owns electronic sound after gameplay boundary")
	bonus.reset_bonus()
	player.apply_command({"action": "play", "generation": 0, "serial": 99, "raw_command": 5})
	check(not player.playing, "Old generation cannot restart audio")
	player.reset_electronic()
	check(not player.enabled and player.generation == -1, "Disconnect/reset state")
	background.stop_background()
	mpf.media.sound.stop_all(0)
	quit(0 if failures == 0 else 1)
