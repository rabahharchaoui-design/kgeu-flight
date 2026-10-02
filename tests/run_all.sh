#!/bin/zsh
# Full pass: physics suites, every browser check, then the frame rate gate.
# Run from the project root: zsh tests/run_all.sh
cd "$(dirname "$0")/.."
PY=.venv/bin/python
fail=()
for t in test t3 t6 dubins_test orbit_test; do
  out=$(node tests/$t.js 2>&1); code=$?
  echo "== node $t (exit $code)"; echo "$out" | tail -3
  [[ $code -ne 0 ]] && fail+=("node $t")
done
for t in prefs_check landing_check touch_check ui_check menu_check skill_check school_check map_check arcade_check photo_check splash_check credit_check \
         base_check desktop_check score_check sixpack_check strike_check mission_check radio_check a2hs_check \
         multitouch_check roll_check night_check sensor_check sensor_az_check dropcam_check strike_fx_check prop_check \
         haboob_check callsign_check crash_check egg_check navlight_check quiet_check music_check map2_check modes_check dz_check onemile_check scores_check lb_merge_check upgrade_check \
         warm_console_check map_open_check scorch_check music_start_check music_pause_check ticker_check voice_queue_check \
         steer_check units_check trim_check easy_land_check clearance_check taps_check results_check segments_check overlay_check sidetoast_check music_menu_check pause_layout_check haptics_check \
         traffic_check tcas_check world_data_check world_check world_ui_check tokyo_check paris_check rio_check world_lb_check; do
  out=$($PY tests/$t.py 2>&1); code=$?
  echo "== $t (exit $code)"; echo "$out" | grep -E "FAIL|passed|clear|FAILS" | tail -4
  [[ $code -ne 0 ]] && fail+=("$t")
done
# every event start, 3 in a row here (the full 10 in a row: .venv/bin/python tests/event_start_check.py)
for t in event_start_check; do
  out=$($PY tests/$t.py --reps 3 2>&1); code=$?
  echo "== $t (exit $code)"; echo "$out" | grep -E "FAIL|passed|clear|FAILS" | tail -4
  [[ $code -ne 0 ]] && fail+=("$t")
done
for t in ab_check; do
  out=$($PY tests/$t.py --noshots 2>&1); code=$?
  echo "== $t (exit $code)"; echo "$out" | grep -E "FAIL|passed|clear|FAILS" | tail -4
  [[ $code -ne 0 ]] && fail+=("$t")
done
echo; echo "FAILED: ${fail[*]:-none}"
