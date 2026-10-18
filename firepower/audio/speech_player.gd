extends AudioStreamPlayer
signal speech_active(active: bool, immediate: bool)
var duck_active := false
## Independent CVSD path. Normal phrases mask IRQ; raw1B enables it at DE5C.
# Cabinet balance: +4 dB natural voice setting; use foreground duck for masking.
# Adjust only SPEECH_BALANCE_DB; the final limiter makes hot settings nonlinear.
const SPEECH_BALANCE_DB: float = 4.0
const SPEECH_VOLUME_DB: float = 1.0
const SPEECH_MAKEUP_DB: float = 14.0
const SPEECH_THRESHOLD_DB: float = -15.0
const SPEECH_RATIO: float = 3.0
const SPEECH_ATTACK_US: float = 200.0
const SPEECH_RELEASE_MS: float = 80.0
const SPEECH_CEILING_DB: float = -1.0
# Guard for measured resampling/intersample peaks above native sample peaks.
const SPEECH_LIMITER_CEILING_DB: float = -1.3
const SPEECH_LIMITER_RELEASE: float = 0.05
const SPEECH_LOW_CUT_HZ: float = 90.0
# Broad octave-band shoulders, no narrow telephone/sibilance boost.
const SPEECH_PRESENCE_GAINS_DB := [0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 4.0, 2.0, 0.0, 0.0]
var highpass: AudioEffectHighPassFilter
var presence: AudioEffectEQ10
var compressor: AudioEffectCompressor
var balance: AudioEffectAmplify
var limiter: AudioEffectHardLimiter
var model: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://audio/speech_model.json"))
var generation := -1
var serial := -1
var enabled := false
var state := 0
var irq_counter := 0
var command := -1
var phrase := ""
var interruptible := false
var pending := -1

func _ready() -> void:
	bus = &"voice"
	max_polyphony = 1
	volume_db = SPEECH_VOLUME_DB
	# The dedicated voice bus feeds Master; effects/music never traverse it.
	# Install once here so all tuning values stay with their production owner.
	var index := AudioServer.get_bus_index(bus)
	assert(AudioServer.get_bus_effect_count(index) == 0, "Speech DSP must have one owner")
	highpass = AudioEffectHighPassFilter.new()
	highpass.cutoff_hz = SPEECH_LOW_CUT_HZ
	highpass.db = AudioEffectFilter.FILTER_12DB
	highpass.resonance = 0.5
	presence = AudioEffectEQ10.new()
	for band in presence.get_band_count():
		presence.set_band_gain_db(band, SPEECH_PRESENCE_GAINS_DB[band])
	compressor = AudioEffectCompressor.new()
	compressor.threshold = SPEECH_THRESHOLD_DB
	compressor.ratio = SPEECH_RATIO
	compressor.attack_us = SPEECH_ATTACK_US
	compressor.release_ms = SPEECH_RELEASE_MS
	compressor.gain = SPEECH_MAKEUP_DB
	compressor.mix = 1.0
	balance = AudioEffectAmplify.new()
	balance.volume_db = SPEECH_BALANCE_DB
	limiter = AudioEffectHardLimiter.new()
	limiter.ceiling_db = SPEECH_LIMITER_CEILING_DB
	limiter.pre_gain_db = 0.0
	limiter.release = SPEECH_LIMITER_RELEASE
	AudioServer.add_bus_effect(index, highpass)
	AudioServer.add_bus_effect(index, presence)
	AudioServer.add_bus_effect(index, compressor)
	AudioServer.add_bus_effect(index, balance)
	AudioServer.add_bus_effect(index, limiter)
	finished.connect(_completed)

func apply_command(payload: Dictionary) -> void:
	var incoming := int(payload.get("generation", -1))
	var next_serial := int(payload.get("serial", -1))
	var action: String = payload.get("action", "stop")
	if incoming < generation or (incoming == generation and next_serial <= serial):
		return
	if action == "start":
		clear_speech()
		generation = incoming
		serial = next_serial
		enabled = true
		return
	if incoming != generation:
		return
	serial = next_serial
	if action == "cancel_release":
		if pending == 0x18:
			pending = -1
		if command == 0x18:
			stop()
			_completed()
		return
	if action == "stop" or action == "clear":
		clear_speech()
		if action == "stop":
			enabled = false
		return
	if action != "request" or not enabled:
		return
	var raw := int(payload.get("raw_command", -1))
	if raw < 0 or raw > 31:
		return
	if command >= 0 and not interruptible:
		pending = raw # one PIA input latch, never an unbounded phrase FIFO
		return
	_execute(raw)

func _set_duck(active: bool, immediate := false) -> void:
	if duck_active == active and not immediate:
		return
	duck_active = active
	speech_active.emit(active, immediate)

func _execute(raw: int) -> void:
	stop()
	stream = null
	command = -1
	phrase = ""
	irq_counter = (irq_counter + 1) & 255 # FBCA before random-table selection
	var selector := state if raw == 0x18 else (irq_counter & 15) if raw == 0x1b else 0
	var decoded: Dictionary = model.commands["%02x_%d" % [raw, selector]]
	if not decoded.speech:
		_set_duck(false)
		return
	state = int(decoded.next_state)
	phrase = decoded.phrase
	command = raw
	interruptible = raw == 0x1b
	stream = load("res://" + model.phrases[phrase].production_file)
	pitch_scale = 1.0
	_set_duck(true)
	play(0.0)

func _completed() -> void:
	command = -1
	phrase = ""
	stream = null
	if pending >= 0:
		var next := pending
		pending = -1
		_execute(next)
	else:
		_set_duck(false)

func clear_speech() -> void:
	_set_duck(false, true)
	stop()
	stream = null
	command = -1
	phrase = ""
	interruptible = false
	pending = -1

func reset_speech() -> void:
	clear_speech()
	enabled = false
	generation = -1
	serial = -1
	state = 0
	irq_counter = 0

func _exit_tree() -> void:
	clear_speech()
	# Remove only this controller's effects, preserving any diagnostic taps.
	var index := AudioServer.get_bus_index(bus)
	for slot in range(AudioServer.get_bus_effect_count(index) - 1, -1, -1):
		var effect := AudioServer.get_bus_effect(index, slot)
		if effect in [highpass, presence, compressor, balance, limiter]:
			AudioServer.remove_bus_effect(index, slot)
