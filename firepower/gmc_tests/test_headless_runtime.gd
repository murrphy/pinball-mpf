extends SceneTree
## Run through tools/godot-cabinet with DISPLAY and WAYLAND_DISPLAY unset.
var failures := 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	check(DisplayServer.get_name() == "headless", "Headless display required")
	check(AudioServer.get_driver_name() == "PulseAudio", "Real PulseAudio backend required; Dummy is a failure")
	check(not OS.has_environment("DISPLAY") and not OS.has_environment("WAYLAND_DISPLAY"), "Console environment required")
	var server = root.get_node("MPF").server
	check(server.get_script().resource_path == "res://audio/firepower_server.gd", "Configured Firepower GMC server")
	server.listen()
	check(server._server.is_listening(), "BCP port opened")
	var capture := AudioEffectCapture.new()
	var master := AudioServer.get_bus_index("Master")
	AudioServer.add_bus_effect(master, capture)
	var peaks := {}
	var generation := 100
	for command in [10, 20, 18]:
		generation += 1
		server.electronic.apply_command({"action":"start", "generation":generation})
		capture.clear_buffer()
		server.electronic.apply_command({"action":"play", "generation":generation, "serial":1, "raw_command":command, "stage":10})
		await create_timer(0.5).timeout
		peaks[str(command)] = peak(capture)
	# Fresh generation after the foreground cases.
	server.electronic.reset_electronic()
	capture.clear_buffer()
	server.background.apply_command({"action":"start", "cycle":100, "rate":0.85, "ramp_ms":0})
	await create_timer(3.5).timeout
	peaks["fp03"] = peak(capture)
	check(server.background.playing and is_equal_approx(server.background.pitch_scale, 0.85), "FP03 loops with native state/rate")
	server.background.stop_background()
	capture.clear_buffer()
	server.bonus_audio.apply_command({"action":"start", "cycle":100, "step":0})
	server.bonus_audio.apply_command({"action":"step", "cycle":100, "step":1})
	await create_timer(0.5).timeout
	peaks["fa64"] = peak(capture)
	server.bonus_audio.stop_bonus()
	capture.clear_buffer()
	server.speech.apply_command({"action":"start", "generation":100, "serial":1})
	server.speech.apply_command({"action":"request", "generation":100, "serial":2, "raw_command":15})
	await create_timer(1).timeout
	peaks["speech"] = peak(capture)
	check(AudioServer.get_bus_effect_count(AudioServer.get_bus_index("voice")) >= 5, "Production speech DSP loaded")
	for key in peaks:
		check(peaks[key] > 0.00001, "Actual mixer output for " + key)
	var report := {"display":DisplayServer.get_name(), "audio":AudioServer.get_driver_name(), "latency":AudioServer.get_output_latency(), "output":AudioServer.output_device, "peaks":peaks, "failures":failures}
	var path := OS.get_environment("FIREPOWER_RUNTIME_REPORT")
	if path.is_empty():
		path = "/tmp/firepower-headless-runtime.json"
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  "))
	file.close()
	server.on_disconnect()
	check(not server.speech.playing and not server.background.playing, "Disconnect clears active audio")
	AudioServer.remove_bus_effect(master, AudioServer.get_bus_effect_count(master) - 1)
	server.stop(true)
	quit(1 if failures else 0)

func peak(capture: AudioEffectCapture) -> float:
	var value := 0.0
	for frame in capture.get_buffer(capture.get_frames_available()):
		value = max(value, abs(frame.x), abs(frame.y))
	return value
