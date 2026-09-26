extends "res://addons/mpf-gmc/scripts/bcp_server.gd"
## GMC's supported machine-local server override; no framework edits.

var background: AudioStreamPlayer

func _ready() -> void:
	super._ready()
	background = preload("res://audio/fp03_player.gd").new()
	background.name = "FP03Background"
	add_child(background)
	# MPF addresses local_display directly, so this needs no subscription handshake.
	registered_handlers["firepower_background"] = [background.apply_command]

func on_message(message: Dictionary) -> Dictionary:
	if message.get("cmd") == "reset":
		# on_message runs on the BCP thread; all audio work belongs on the main thread.
		call_deferred("_sync_background")
	return message

func _sync_background() -> void:
	background.stop_background()
	send_event("firepower_background_sync", false)

func on_disconnect() -> void:
	background.stop_background()
