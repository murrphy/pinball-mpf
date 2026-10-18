extends "res://addons/mpf-gmc/scripts/bcp_server.gd"
## GMC's supported machine-local server override; no framework edits.

var background: AudioStreamPlayer
var bonus_audio: AudioStreamPlayer
var electronic: AudioStreamPlayer
var speech: AudioStreamPlayer

func _ready() -> void:
	super._ready()
	background = preload("res://audio/fp03_player.gd").new()
	background.name = "FP03Background"
	add_child(background)
	# MPF addresses local_display directly, so this needs no subscription handshake.
	registered_handlers["firepower_background"] = [background.apply_command]
	bonus_audio = preload("res://audio/bonus_player.gd").new()
	bonus_audio.name = "BonusAudio"
	add_child(bonus_audio)
	registered_handlers["firepower_bonus_audio"] = [bonus_audio.apply_command]
	electronic = preload("res://audio/electronic_player.gd").new()
	electronic.name = "OriginalElectronicAudio"
	add_child(electronic)
	electronic.foreground_active.connect(_mask_background)
	registered_handlers["firepower_electronic"] = [electronic.apply_command]
	speech = preload("res://audio/speech_player.gd").new()
	speech.name = "OriginalSpeech"
	speech.speech_active.connect(electronic.set_speech_active)
	add_child(speech)
	registered_handlers["firepower_speech"] = [speech.apply_command]

func _mask_background(active: bool) -> void:
	# Mask only audible output. FP03's timing, stage, tween and loop keep running.
	background.volume_db = -80.0 if active else background.VOLUME_DB

func on_message(message: Dictionary) -> Dictionary:
	if message.get("cmd") == "reset":
		# on_message runs on the BCP thread; all audio work belongs on the main thread.
		call_deferred("_sync_background")
	return message

func _sync_background() -> void:
	background.stop_background()
	bonus_audio.reset_bonus()
	electronic.reset_electronic()
	speech.reset_speech()
	send_event("firepower_background_sync", false)
	send_event("firepower_bonus_audio_sync", false)
	send_event("firepower_electronic_sync", false)
	send_event("firepower_speech_sync", false)

func on_disconnect() -> void:
	background.stop_background()
	bonus_audio.reset_bonus()
	electronic.reset_electronic()
	speech.reset_speech()
