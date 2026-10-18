extends RefCounted
## FA3C/SP1 derived VARI schedule, verified against original 6800 execution.
const CLOCK = 895000.0
const RATE = 48000
var model: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://audio/spinner_model.json"))

func dac_events(stage: int) -> Dictionary:
	if stage < 1 or stage > 31:
		return {}
	var state: Dictionary = model.states[stage - 1]
	var low: int = state.low_period
	var clock: int = state.first_dac_cycle
	var events: Array = [[clock, 255]]
	clock += 14
	var high := 1
	var value := 255
	for sweep in range(24):
		clock += 4 + 9
		var remaining := 1152
		value ^= 255
		events.append([clock, value])
		var counter: int = low if low else 256
		var side := 0
		while remaining:
			clock += 8
			remaining -= 1
			if remaining == 0:
				break
			clock += 6
			counter -= 1
			if counter == 0:
				if side == 0:
					clock += 6
					value ^= 255
					events.append([clock, value])
					clock += 3
					counter = high if high else 256
					side = 1
				else:
					clock += 4 + 9
					value ^= 255
					events.append([clock, value])
					counter = low if low else 256
					side = 0
		clock += 8
		if value < 128:
			clock += 2
			value ^= 255
		clock += 7
		events.append([clock, value])
		clock += 27
		high = (high + 24) & 255
		if high == 65:
			clock += 12
			break
	return {"events": events, "cycles": clock}

func render(stage: int) -> AudioStreamWAV:
	var schedule := dac_events(stage)
	if schedule.is_empty():
		return null
	var events: Array = schedule.events
	# RTS is included; BRA + JSR (13 cycles) precedes each repeated VARI call.
	var frames := int(ceil((schedule.cycles + 13) * RATE / CLOCK))
	var pcm := PackedByteArray()
	pcm.resize(frames * 2)
	var index := 0
	var held := 128
	for frame in range(frames):
		var start := frame * CLOCK / RATE
		var finish := (frame + 1) * CLOCK / RATE
		var cursor := start
		var area := 0.0
		while index < events.size() and events[index][0] < finish:
			var edge: float = max(cursor, events[index][0])
			area += (edge - cursor) * (held - 128)
			cursor = edge
			held = events[index][1]
			index += 1
		area += (finish - cursor) * (held - 128)
		var sample := int(clamp(round(area / (finish - start) * 200), -32768, 32767))
		pcm.encode_s16(frame * 2, sample)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = RATE
	stream.stereo = false
	stream.data = pcm
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_begin = int(round((events[0][0] - 8) * RATE / CLOCK))
	stream.loop_end = frames
	return stream
