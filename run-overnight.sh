#!/bin/zsh
# Overnight orchestrator loop for Pocket Flight Sim.
# Runs Fable as the boss, Opus as builder, Sonnet as tester, resuming after usage limit pauses.
# Stops starting new work between 07:00 and 21:59 so it cannot run away during the day.
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
  echo "=== run $n $(date) ===" >> "$LOG"
  if [ $n -eq 1 ]; then
    claude --model claude-fable-5-1 --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee -a "$LOG"
  else
    claude --continue --model claude-fable-5-1 --dangerously-skip-permissions -p "Continue as the orchestrator per PROMPT.md. Resume from PLAN.md at the first unchecked item above the STOP line. When everything above the STOP line is done, merged, pushed, and live, print exactly ALL DONE." 2>&1 | tee -a "$LOG"
  fi
  if grep -q "ALL DONE" "$LOG"; then
    echo "=== ALL DONE $(date) ===" >> "$LOG"; break
  fi
  echo "=== run $n ended $(date), sleeping 30 min before resuming ===" >> "$LOG"
  sleep 1800
done
echo "=== overnight loop finished $(date) ===" >> "$LOG"
