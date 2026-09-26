extends AudioStreamPlayer
## One machine-local FP03 stream. Rules and target-rate tuning live in MPF.

const SOURCE = "res://sounds/fx/FP03.wav"
const VOLUME_DB: float = -3.0
var cycle: int = -1
var rate_tween: Tween

func _ready() -> void:
	bus = &"music"
	max_polyphony = 1
	volume_db = VOLUME_DB
	# Duplicate the resource, not the audio file: do not change shared import state.
	var wav = (load(SOURCE) as AudioStreamWAV).duplicate() as AudioStreamWAV
	wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
	wav.loop_begin = 0
	# The uncompressed import preserves all source frames, without trimming.
	wav.loop_end = roundi(wav.get_length() * wav.mix_rate)
	stream = wav

func apply_command(payload: Dictionary) -> void:
	var action: String = payload.get("action", "stop")
	if action == "stop":
		stop_background()
		return
	var target: float = float(payload["rate"])
	if not is_finite(target) or target <= 0:
		return
	var incoming_cycle: int = int(payload["cycle"])
	if action == "start":
		# Repeated snapshots cannot layer or restart the same running cycle.
		if not playing or incoming_cycle != cycle:
			stop_background()
			cycle = incoming_cycle
			pitch_scale = target
			play(0.0)
			return
	elif action != "rate":
		return
	if not playing or incoming_cycle != cycle:
		return
	if rate_tween:
		rate_tween.kill()
	var seconds: float = float(payload["ramp_ms"]) / 1000.0
	if seconds <= 0:
		pitch_scale = target
	else:
		rate_tween = create_tween()
		rate_tween.tween_property(self, "pitch_scale", target, seconds)

func stop_background() -> void:
	if rate_tween:
		rate_tween.kill()
		rate_tween = null
	stop()
	cycle = -1

func _exit_tree() -> void:
	stop_background()
