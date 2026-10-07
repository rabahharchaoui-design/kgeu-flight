#!/bin/zsh
# Overnight orchestrator loop for Pocket Flight Sim.
# Runs Fable as the boss, Opus as builder, Sonnet as tester, resuming after usage limit pauses.
# Stops starting new work between 07:00 and 21:59 so it cannot run away during the day.
# Launch with the Mac plugged in so it cannot sleep mid run:
#   caffeinate -is ./run-overnight.sh        (overnight)
#   caffeinate -is ./run-overnight.sh now    (ignore the daytime stop hours)
cd "$(dirname "$0")"
FORCE="$1"   # pass "now" to ignore the daytime stop hour
LOG=overnight-loop.log
MAX=40
n=0
echo "=== overnight loop started $(date) ===" >> "$LOG"
while [ $n -lt $MAX ]; do
  n=$((n+1))
  H=$(date +%H)
  if [ "$FORCE" != "now" ] && [ "$H" -ge 7 ] && [ "$H" -lt 22 ]; then
    echo "=== stop hour reached $(date), not starting new work ===" >> "$LOG"; break
  fi
  # Each run's output goes to its own file so ALL DONE from an earlier night
  # (which stays in the appended log forever) can never end tonight's loop early.
  OUT=".run-$n.out"
  echo "=== run $n $(date) ===" >> "$LOG"
  if [ $n -eq 1 ]; then
    claude --model claude-fable-5-1 --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee "$OUT"
  else
    claude --continue --model claude-fable-5-1 --dangerously-skip-permissions -p "Continue as the orchestrator per PROMPT.md. Resume from PLAN.md at the first unchecked item above the STOP line. When everything above the STOP line is done, merged, pushed, and live, print exactly ALL DONE on a line by itself." 2>&1 | tee "$OUT"
  fi
  cat "$OUT" >> "$LOG"
  # Match ALL DONE only as its own line (allowing markdown bold or a trailing period),
  # so a sentence like "I will print ALL DONE when finished" does not stop the loop.
  if grep -qE '^[[:space:]*]*ALL DONE[.!]?[[:space:]*]*$' "$OUT"; then
    rm -f "$OUT"
    echo "=== ALL DONE $(date) ===" >> "$LOG"; break
  fi
  rm -f "$OUT"
  echo "=== run $n ended $(date), sleeping 30 min before resuming ===" >> "$LOG"
  sleep 1800
done
echo "=== overnight loop finished $(date) ===" >> "$LOG"
