extends RefCounted
## Derived FA64 DAC model; see BONUS_AUDIO_SOURCE.md for validation and limits.
const MODEL_PATH = "res://audio/fa64_model.json"
const CLOCK_HZ: float = 895000.0
const SAMPLE_RATE: int = 48000
var waveform: Array

func _init() -> void:
	var model = JSON.parse_string(FileAccess.get_file_as_string(MODEL_PATH))
	waveform = model.waveform

static func relative_pitch(step: int) -> float:
	if step < 1 or step > 146:
		return 0.0
	return 64982.0 / (72 * (6 * (147 - step) + 25) + 110)

func dac_events(step: int) -> Array:
	var events: Array = []
	if step < 1 or step > 146:
		return events
	var period: int = 147 - step
	var first: int = 24353 if step == 1 else 6 * period + 180
	for index in range(576):
		events.append([first + index * (6 * period + 25) + (index / 72) * 110,
			waveform[index % 72]])
	return events

func render(step: int) -> AudioStreamWAV:
	var events = dac_events(step)
	if events.is_empty():
		return null
	var end_cycle: int = events[-1][0] + 89
	var frames: int = ceili(end_cycle * SAMPLE_RATE / CLOCK_HZ)
	var data = PackedByteArray()
	data.resize(frames * 2)
	var next_event: int = 0
	# Center the derived waveform's DC mean. The analog cabinet is not modeled.
	var held: float = 114.0
	for frame in range(frames):
		var start: float = frame * CLOCK_HZ / SAMPLE_RATE
		var finish: float = (frame + 1) * CLOCK_HZ / SAMPLE_RATE
		var cursor: float = start
		var area: float = 0.0
		# Integrate the DAC hold over each output frame, rather than point-sample it.
		while next_event < events.size() and events[next_event][0] < finish:
			var edge: float = maxf(cursor, events[next_event][0])
			area += (edge - cursor) * (held - 114.0)
			cursor = edge
			held = events[next_event][1]
			next_event += 1
		area += (finish - cursor) * (held - 114.0)
		var sample: int = clampi(roundi(area / (finish - start) * 200.0), -32768, 32767)
		data.encode_s16(frame * 2, sample)
	var result = AudioStreamWAV.new()
	result.format = AudioStreamWAV.FORMAT_16_BITS
	result.mix_rate = SAMPLE_RATE
	result.stereo = false
	result.loop_mode = AudioStreamWAV.LOOP_DISABLED
	result.data = data
	return result
