extends AudioStreamPlayer
## One Firepower electronic foreground voice; speech stays on GMC's voice bus.
signal foreground_active(active: bool)
# Only this player is attenuated; FA64 shares effects and must stay independent.
const VOLUME_DB: float = -3.0
const SPEECH_EFFECTS_DUCK_DB: float = -5.0
const SPEECH_DUCK_ATTACK_MS: float = 15.0
const SPEECH_DUCK_RELEASE_MS: float = 150.0
var speech_ducked := false
var duck_tween: Tween
var renderer = preload("res://audio/spinner_renderer.gd").new()
var generation := -1
var serial := -1
var enabled := false
var command := -1
var spinner_stage := 0
var speech_continuation: Dictionary = {}
var sources: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://audio/l6_effect_sources.json"))

func _ready() -> void:
	bus = &"effects"
	max_polyphony = 1
	volume_db = VOLUME_DB
	finished.connect(_completed)

func set_speech_active(active: bool, immediate := false) -> void:
	if immediate:
		speech_continuation = {}
	elif not active and not speech_continuation.is_empty():
		var next := speech_continuation
		speech_continuation = {}
		if enabled:
			_play_payload(next)
	if active == speech_ducked and not immediate:
		return
	speech_ducked = active
	if duck_tween:
		duck_tween.kill()
		duck_tween = null
	var target := VOLUME_DB + (SPEECH_EFFECTS_DUCK_DB if active else 0.0)
	if immediate:
		volume_db = target
		return
	var duration := SPEECH_DUCK_ATTACK_MS if active else SPEECH_DUCK_RELEASE_MS
	duck_tween = create_tween()
	duck_tween.tween_property(self, "volume_db", target, duration / 1000.0)

func apply_command(payload: Dictionary) -> void:
	var incoming: int = int(payload.get("generation", -1))
	var action: String = payload.get("action", "stop")
	if incoming < generation:
		return
	if action == "start":
		if incoming > generation:
			stop_electronic()
			serial = -1
		generation = incoming
		enabled = true
		return
	if action == "stop":
		generation = incoming
		enabled = false
		stop_electronic()
		return
	var incoming_serial: int = int(payload.get("serial", -1))
	if action != "play" or not enabled or incoming != generation or incoming_serial <= serial:
		return
	serial = incoming_serial
	speech_continuation = {}
	if payload.get("after_speech", false) and speech_ducked:
		# HSTD alone returns from protected speech into APPEAR. Keep one
		# continuation on this same player until the actual phrase completes.
		speech_continuation = payload.duplicate()
		return
	_play_payload(payload)

func _play_payload(payload: Dictionary) -> void:
	var next_command: int = int(payload.get("raw_command", -1))
	var next_stream: AudioStream = null
	if next_command == 18:
		var stage: int = int(payload.get("stage", 0))
		next_stream = renderer.render(stage)
		if next_stream:
			spinner_stage = stage
	else:
		for source in sources.effects:
			if int(source.raw) == next_command:
				next_stream = load("res://" + source.production_file)
				break
	if not next_stream:
		return
	stop()
	command = next_command
	pitch_scale = 1.0
	stream = next_stream
	foreground_active.emit(true)
	play(0.0)

func _completed() -> void:
	command = -1
	stream = null
	foreground_active.emit(false)

func stop_electronic() -> void:
	speech_continuation = {}
	stop()
	_completed()

func reset_electronic() -> void:
	stop_electronic()
	set_speech_active(false, true)
	enabled = false
	generation = -1
	serial = -1

func _exit_tree() -> void:
	stop_electronic()
	set_speech_active(false, true)
