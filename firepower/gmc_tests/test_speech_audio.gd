extends SceneTree
var failures := 0
var serial := 0
var speech

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func digest(bytes: PackedByteArray) -> String:
	var hash := HashingContext.new()
	hash.start(HashingContext.HASH_SHA256)
	hash.update(bytes)
	return hash.finish().hex_encode()

func send(action: String, raw := -1) -> void:
	serial += 1
	speech.apply_command({"action": action, "generation": 1, "serial": serial, "raw_command": raw})

func words(key: String) -> Array:
	var result := []
	for word in speech.model.phrases[speech.model.commands[key].phrase].words:
		result.append(word.word)
	return result

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var server = root.get_node("MPF").server
	speech = server.speech
	check(speech.bus == &"voice" and speech.max_polyphony == 1, "Dedicated monophonic CVSD path")
	check(speech.SPEECH_VOLUME_DB == 1.0 and speech.volume_db == speech.SPEECH_VOLUME_DB, "Centralized production speech pre-gain")
	check(server.electronic.volume_db == -3.0, "Electronic foreground gain unchanged")
	check(server.background.VOLUME_DB == -3.0 and server.background.volume_db == -3.0, "FP03 gain unchanged")
	check(server.bonus_audio.volume_db == -3.0, "FA64 bonus gain unchanged")
	for bus_name in ["voice", "effects", "music", "Master"]:
		var index := AudioServer.get_bus_index(bus_name)
		var expected := -0.0438385 if bus_name in ["voice", "Master"] else 0.0
		check(abs(AudioServer.get_bus_volume_db(index) - expected) < 0.00001, "Existing bus gain preserved: " + bus_name)
		check(AudioServer.get_bus_effect_count(index) == (5 if bus_name == "voice" else 0), "Speech-only bus processing: " + bus_name)
	var voice := AudioServer.get_bus_index("voice")
	var chain := [speech.highpass, speech.presence, speech.compressor, speech.balance, speech.limiter]
	for slot in chain.size():
		check(AudioServer.get_bus_effect(voice, slot) == chain[slot] and AudioServer.is_bus_effect_enabled(voice, slot), "Production voice chain ownership/order/enabling")
	check(not AudioServer.is_bus_bypassing_effects(voice), "Production speech DSP is enabled")
	check(is_equal_approx(speech.balance.volume_db, speech.SPEECH_BALANCE_DB), "Centralized cabinet speech/sound balance")
	check(speech.highpass.cutoff_hz == speech.SPEECH_LOW_CUT_HZ and speech.highpass.db == AudioEffectFilter.FILTER_12DB, "Gentle speech-only low cut")
	for band in speech.presence.get_band_count():
		check(is_equal_approx(speech.presence.get_band_gain_db(band), speech.SPEECH_PRESENCE_GAINS_DB[band]), "Broad centralized presence curve")
	check(AudioServer.get_bus_send(voice) == &"Master", "Voice effects feed existing Master")
	check(speech.compressor.gain == speech.SPEECH_MAKEUP_DB and speech.compressor.threshold == speech.SPEECH_THRESHOLD_DB and speech.compressor.ratio == speech.SPEECH_RATIO, "Centralized compression and makeup")
	check(speech.compressor.attack_us == speech.SPEECH_ATTACK_US and speech.compressor.release_ms == speech.SPEECH_RELEASE_MS and speech.compressor.mix == 1.0 and speech.compressor.sidechain == &"", "Speech dynamics have no electronic sidechain")
	check(is_equal_approx(speech.limiter.ceiling_db, speech.SPEECH_LIMITER_CEILING_DB) and speech.limiter.pre_gain_db == 0.0 and is_equal_approx(speech.limiter.release, speech.SPEECH_LIMITER_RELEASE), "Speech-only peak ceiling")
	check(server.electronic.bus == &"effects" and server.bonus_audio.bus == &"effects" and server.background.bus == &"music", "Other players bypass speech DSP")
	for source in speech.model.phrases.values():
		var path: String = "res://" + source.production_file
		check(FileAccess.get_sha256(path) == source.wav_sha256, "Authentic phrase asset identity")
		var stream: AudioStreamWAV = load(path)
		check(stream.format == AudioStreamWAV.FORMAT_16_BITS and stream.mix_rate == 48000, "Lossless native 48k speech")
		check(digest(stream.data) == source.pcm_sha256, "Importer preserves the ROM-derived PCM")
		check(abs(stream.get_length() - source.duration) < 1.0 / 48000.0, "Firmware return timing preserved to one frame")
	# Clipping/loudness now require actual effect processing, covered by
	# test_speech_render.gd rather than multiplying asset PCM by player gain.
	check(words("07_0") == ["you", "are", "destroyed"], "Tilt phrase")
	check(words("08_0") == ["you", "one", "one", "mission"], "Literal ONE/WON extra-ball samples")
	check(words("0c_0") == ["mission", "accomplished"], "Collected Special phrase")
	check(words("0f_0") == ["fire", "power", "mission", "accomplished"], "High-score fallthrough")
	check(words("18_0") == ["fire", "one"] and words("18_1") == ["two"] and words("18_2") == ["three"], "Stateful release vocabulary")
	var fire_one: Dictionary = speech.model.phrases[speech.model.commands["18_0"].phrase]
	check(int(fire_one.words[1].cycle) == 592488, "ONE firmware onset includes FIRE playback, no guessed .25s spacing")
	var enemy: Dictionary = speech.model.phrases[speech.model.commands["0e_0"].phrase]
	check(int(enemy.words[0].cycle) == 58532 and int(enemy.words[1].cycle) == 690825, "Explicit 0040 pre-speech delay and chained DESTROYED timing")
	check(words("1b_8") == ["you", "one", "fire", "power", "destroyed"], "Random table delay/fallthrough")
	speech.reset_speech()
	send("start")
	send("request", 0x18)
	check(speech.state == 1 and speech.command == 0x18 and speech.playing, "First request starts FIRE ONE")
	check(speech.volume_db == speech.SPEECH_VOLUME_DB and speech.bus == &"voice" and speech.pitch_scale == 1.0, "Phrase playback retains live production gain, routing and speed")
	var first = speech.get_stream_playback()
	send("request", 0x18)
	check(speech.pending == 0x18 and speech.state == 1 and speech.get_stream_playback() == first, "Protected phrase defers selector advancement")
	send("request", 20)
	check(speech.pending == 20, "Ordinary sound overwrites the same pending PIA latch")
	send("request", 0x18)
	await create_timer(fire_one.duration + 0.5).timeout
	check(speech.state == 2 and speech.command == 0x18 and speech.pending == -1, "Natural completion consumes latest request, speaking TWO (state=%s command=%s pending=%s playing=%s)" % [speech.state, speech.command, speech.pending, speech.playing])
	await create_timer(1.2).timeout
	send("request", 20)
	check(speech.state == 2 and not speech.playing, "Non-speech does not reset state02")
	send("request", 0x18)
	check(speech.state == 0 and words("18_2") == ["three"], "Third accepted selector speaks THREE then wraps")
	send("clear")
	send("request", 0x0d)
	first = speech.get_stream_playback()
	send("request", 0x1e)
	speech.apply_command({"action": "request", "generation": 1, "serial": serial, "raw_command": 0x07})
	check(speech.pending == 0x1e and speech.get_stream_playback() == first, "Duplicate packet cannot replace pending speech")
	speech.apply_command({"action": "clear", "generation": 0, "serial": 9999})
	check(speech.playing, "Old generation cannot clear current phrase")
	send("clear")
	check(not speech.playing and speech.pending == -1 and speech.stream == null, "Explicit lifecycle cleanup overrides phrase protection")
	send("request", 0x18)
	send("request", 0x18)
	send("cancel_release")
	check(not speech.playing and speech.pending == -1, "Ending multiball cancels current and pending release counts")
	# Replay the accepted input pattern recovered from the foreground. A selected
	# phrase resets02; then prelude18 is followed by83, first release18/17/14.
	send("request", 0x0d)
	send("clear")
	send("request", 0x18)
	check(speech.phrase == speech.model.commands["18_0"].phrase, "Prelude starts FIRE ONE")
	send("request", 3)
	await create_timer(41.0 * 16.0 * 928.0 * 4.0 / 3579545.0).timeout
	send("request", 0x18)
	send("request", 0x17)
	await create_timer(40.0 * 16.0 * 928.0 * 4.0 / 3579545.0).timeout
	send("request", 0x14)
	await create_timer(0.5).timeout
	check(speech.state == 1 and not speech.playing and speech.pending == -1, "First release request is overwritten: no premature TWO")
	send("request", 0x18)
	check(speech.phrase == speech.model.commands["18_1"].phrase, "Second release executes TWO")
	send("request", 0x17)
	await create_timer(0.664).timeout
	send("request", 0x14)
	await create_timer(0.5).timeout
	check(speech.state == 2 and not speech.playing, "Electronic inputs preserve second selector")
	send("request", 0x18)
	check(speech.phrase == speech.model.commands["18_2"].phrase and speech.state == 0, "Third release executes THREE and wraps")
	send("clear")
	speech.irq_counter = 1
	send("request", 0x1b)
	check(speech.phrase == speech.model.commands["1b_2"].phrase and speech.interruptible, "FBCA increments before random selector")
	send("request", 20)
	check(not speech.playing and speech.command == -1, "DE5C random speech is interruptible even by ordinary electronics")
	server.electronic.apply_command({"action": "start", "generation": 1})
	server.electronic.apply_command({"action": "play", "generation": 1, "serial": 1, "raw_command": 18, "stage": 1})
	var electronic_playback = server.electronic.get_stream_playback()
	send("request", 0x07)
	check(speech.playing and server.electronic.playing and server.electronic.get_stream_playback() == electronic_playback, "Speech has independent output and never changes electronic playback")
	send("stop")
	send("request", 0x0d)
	check(not speech.playing, "Stopped owner rejects future speech")
	server._sync_background()
	check(not speech.enabled and speech.generation == -1 and speech.pending == -1, "BCP reset cleans speech state without replay")
	speech.apply_command({"action": "start", "generation": 2, "serial": 1})
	speech.apply_command({"action": "request", "generation": 2, "serial": 2, "raw_command": 0x0d})
	server.on_disconnect()
	check(not speech.playing and speech.state == 0, "Disconnect cleans voice and selector")
	print("Speech controller failures: ", failures)
	quit(1 if failures else 0)
