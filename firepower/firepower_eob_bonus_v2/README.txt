Firepower End-of-Ball Bonus V2
================================

Files included:

- modes/base/config/base.yaml
  Replacement for uploaded base.yaml. It removes start_bonus_collect from mode_base_started and adds queue_relay_player on ball_ending.

- modes/bonus_ladder/config/bonus_ladder.yaml
  Variable-driven static bonus lamp tracker for bonus_value 0..39.

- modes/bonus_collect/config/bonus_collect.yaml
  Custom end-of-ball countdown. Each timer tick scores 1000 and decrements bonus_value, so lamps and score move together.

- config_snippets/config_player_vars.yaml
  Merge these player_vars into main config.yaml.

Important wiring:

- base.yaml uses:

  queue_relay_player:
    ball_ending:
      post: start_bonus_collect
      wait_for: mode_bonus_collect_stopped

- bonus_collect starts on start_bonus_collect and stops on bonus_collect_done.
- mode_bonus_collect_stopped releases MPF's ball_ending queue.

Testing targets:

1. Bonus value 3, multiplier 1: score should add 3000 and lamps should count 3->0.
2. Bonus value 3, multiplier 2: score should add 6000 as two visible passes.
3. Bonus value 39, multiplier 5: score should add 195000 as five visible passes.

Do not leave any old start_mode_bonus_collect or start_bonus_collect entry under mode_base_started.
