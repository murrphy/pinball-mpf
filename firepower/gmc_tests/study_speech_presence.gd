extends "res://gmc_tests/test_speech_render.gd"
## Diagnostic sweeps; one production player, one serial DSP chain at a time.
func run() -> void:
	evaluating = true
	var server = root.get_node("MPF").server
	var voice := AudioServer.get_bus_index("voice")
	var owned := [server.speech.highpass, server.speech.presence, server.speech.compressor, server.speech.balance, server.speech.limiter]
	var variants := []
	if "--balance" in OS.get_cmdline_user_args():
		for value in [0.0, 3.0, 6.0]:
			variants.append(["balance_%d" % int(value), 200.0, 14.0, true, value])
	elif "--shaping" in OS.get_cmdline_user_args():
		variants = [["attack_2", 2000.0, 18.0, false, 0.0], ["attack_4", 4000.0, 18.0, false, 0.0], ["attack_8", 8000.0, 18.0, false, 0.0],
			["eq_2_makeup14", 2000.0, 14.0, true, 0.0], ["eq_2_makeup16", 2000.0, 16.0, true, 0.0], ["eq_2_makeup18", 2000.0, 18.0, true, 0.0], ["eq_fast_makeup16", 200.0, 16.0, true, 0.0]]
	else:
		for extra in [0.0, 2.0, 4.0, 6.0]:
			variants.append(["makeup_%d" % int(extra), 200.0, 18.0 + extra, false, 0.0])
	for variant in variants:
		server._sync_background()
		for bus_name in ["voice", "Master"]:
			var index := AudioServer.get_bus_index(bus_name)
			for slot in range(AudioServer.get_bus_effect_count(index) - 1, -1, -1):
				AudioServer.remove_bus_effect(index, slot)
		captures.clear()
		tap("raw", "voice")
		if variant[3]:
			AudioServer.add_bus_effect(voice, server.speech.highpass)
			AudioServer.add_bus_effect(voice, server.speech.presence)
		tap("input", "voice")
		var compressor := AudioEffectCompressor.new()
		compressor.threshold = -15.0
		compressor.ratio = 3.0
		compressor.attack_us = variant[1]
		compressor.release_ms = 80.0
		compressor.gain = variant[2]
		AudioServer.add_bus_effect(voice, compressor)
		tap("compout", "voice")
		var gain := AudioEffectAmplify.new()
		gain.volume_db = variant[4]
		AudioServer.add_bus_effect(voice, gain)
		tap("prelimit", "voice")
		var limiter := AudioEffectHardLimiter.new()
		limiter.ceiling_db = server.speech.SPEECH_LIMITER_CEILING_DB
		limiter.release = 0.05
		AudioServer.add_bus_effect(voice, limiter)
		tap("voice", "voice")
		tap("master", "Master")
		output_dir = "/tmp/firepower-speech-study/" + variant[0]
		DirAccess.make_dir_recursive_absolute(output_dir)
		report = {"baseline": false, "failures": 0, "renders": [], "mix_rate": AudioServer.get_mix_rate(),
			"buses": {"Master": {"gain_db": AudioServer.get_bus_volume_db(0)}},
			"settings": {"makeup_db": compressor.gain, "balance_db": gain.volume_db, "attack_us": compressor.attack_us, "eq": variant[3],
				"threshold_db": compressor.threshold, "ratio": compressor.ratio,
				"release_ms": compressor.release_ms, "limiter_db": limiter.ceiling_db}}
		for request in [["FIRE", 13], ["POWER", 26], ["FIRE_ONE", 24], ["TWO", 24], ["THREE", 24], ["MISSION_ACCOMPLISHED", 12]]:
			await record(server, request[0], request[1], true)
		report.failures = failures
		FileAccess.open(output_dir + "/report.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	for bus_name in ["voice", "Master"]:
		var index := AudioServer.get_bus_index(bus_name)
		for slot in range(AudioServer.get_bus_effect_count(index) - 1, -1, -1):
			AudioServer.remove_bus_effect(index, slot)
	for effect in owned:
		AudioServer.add_bus_effect(voice, effect)
	quit(1 if failures else 0)
