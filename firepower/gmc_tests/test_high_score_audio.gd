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
	var server = root.get_node("MPF").server
	var speech = server.speech
	var electronic = server.electronic
	var decoded: Dictionary = speech.model.commands["0f_0"]
	var phrase: Dictionary = speech.model.phrases[decoded.phrase]
	var words := []
	for word in phrase.words:
		words.append(word.word)
	check(words == ["fire", "power", "mission", "accomplished"], "HSTD original full word sequence")
	check(decoded.returned_command == 15 and not phrase.interruptible, "Protected HSTD speech returns raw0F")
	speech.apply_command({"action": "start", "generation": 100, "serial": 1})
	electronic.apply_command({"action": "start", "generation": 100})
	speech.apply_command({"action": "request", "generation": 100, "serial": 2, "raw_command": 15})
	check(speech.playing and not electronic.playing, "HSTD begins with speech alone")
	check(digest(speech.stream.data) == phrase.pcm_sha256, "Existing HSTD speech PCM unchanged")
	electronic.apply_command({"action": "play", "generation": 100, "serial": 1, "raw_command": 15, "after_speech": true})
	check(not electronic.playing and not electronic.speech_continuation.is_empty(), "APPEAR waits for actual speech completion")
	await create_timer(phrase.duration + 0.8).timeout
	check(not speech.playing, "Complete HSTD speech finishes before APPEAR")
	check(electronic.playing and electronic.command == 15, "APPEAR uses established foreground player")
	check(electronic.bus == &"effects" and electronic.max_polyphony == 1, "Existing monophonic effects routing")
	check(electronic.pitch_scale == 1.0 and electronic.stream.loop_mode == AudioStreamWAV.LOOP_DISABLED, "Finite unscaled original noise routine")
	check(digest(electronic.stream.data) == "d8bd97ee373e20148de1c89f83cbc1f1536cf54e156c5264569d9b24506a9afc", "APPEAR PCM equals ROM execution, reference seed3C00")
	await create_timer(electronic.stream.get_length() + 0.2).timeout
	check(not electronic.playing, "APPEAR terminates naturally")
	speech.apply_command({"action": "request", "generation": 100, "serial": 3, "raw_command": 15})
	electronic.apply_command({"action": "play", "generation": 100, "serial": 2, "raw_command": 15, "after_speech": true})
	speech.apply_command({"action": "clear", "generation": 100, "serial": 4})
	check(not electronic.playing and electronic.speech_continuation.is_empty(), "Explicit speech cancellation drops pending APPEAR")
	# Ending/service cancellation clears both existing owners and rejects stale input.
	speech.apply_command({"action": "request", "generation": 100, "serial": 5, "raw_command": 15})
	electronic.apply_command({"action": "play", "generation": 100, "serial": 3, "raw_command": 15})
	speech.apply_command({"action": "clear", "generation": 100, "serial": 6})
	electronic.apply_command({"action": "stop", "generation": 100})
	check(not speech.playing and not electronic.playing and not speech.duck_active, "HSTD cancellation clears playback and duck")
	electronic.apply_command({"action": "play", "generation": 99, "serial": 99, "raw_command": 15})
	check(not electronic.playing, "Cancelled generation cannot restart HSTD")
	speech.reset_speech()
	electronic.reset_electronic()
	quit(1 if failures else 0)
