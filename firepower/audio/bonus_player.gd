extends AudioStreamPlayer
## One monophonic finite FA64 voice, scoped to a bonus collection generation.
var renderer = preload("res://audio/fa64_renderer.gd").new()
var cycle: int = -1
var step: int = 0
var collecting: bool = false

func _ready() -> void:
	bus = &"effects"
	max_polyphony = 1
	volume_db = -3.0

func apply_command(payload: Dictionary) -> void:
	var action: String = payload.get("action", "stop")
	var incoming_cycle: int = int(payload.get("cycle", -1))
	if action == "stop":
		if incoming_cycle >= cycle:
			stop_bonus()
			cycle = incoming_cycle
		return
	if action == "start":
		if incoming_cycle <= cycle:
			return
		stop_bonus()
		cycle = incoming_cycle
		step = int(payload.get("step", 0))
		collecting = true
		return
	if action != "step" or not collecting or incoming_cycle != cycle:
		return
	var incoming_step: int = int(payload.get("step", 0))
	if incoming_step <= step:
		return
	step = incoming_step
	stop()
	# Fixed instruction gaps and first-trigger initialization forbid uniform
	# pitch_scale resampling. Render the exact per-step DAC schedule instead.
	pitch_scale = 1.0
	stream = renderer.render(step)
	if stream:
		play(0.0)

func stop_bonus() -> void:
	stop()
	stream = null
	collecting = false

func reset_bonus() -> void:
	# A new MPF process starts its generation counter from zero.
	stop_bonus()
	cycle = -1
	step = 0

func _exit_tree() -> void:
	stop_bonus()
