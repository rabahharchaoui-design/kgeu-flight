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
         multitouch_check roll_check night_check sensor_check dropcam_check strike_fx_check prop_check \
         haboob_check callsign_check crash_check egg_check navlight_check quiet_check music_check map2_check modes_check; do
  out=$($PY tests/$t.py 2>&1); code=$?
  echo "== $t (exit $code)"; echo "$out" | grep -E "FAIL|passed|clear|FAILS" | tail -4
  [[ $code -ne 0 ]] && fail+=("$t")
done
for t in ab_check; do
  out=$($PY tests/$t.py --noshots 2>&1); code=$?
  echo "== $t (exit $code)"; echo "$out" | grep -E "FAIL|passed|clear|FAILS" | tail -4
  [[ $code -ne 0 ]] && fail+=("$t")
done
echo; echo "FAILED: ${fail[*]:-none}"
