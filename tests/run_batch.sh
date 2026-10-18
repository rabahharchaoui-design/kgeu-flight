#!/bin/zsh
# A slice of tests/run_all.sh that fits one foreground call: the named python checks (tests/<name>.py), each
# with its exit code and the FAIL/passed lines, and a FAILED summary. Extra args after -- go to every test.
#   zsh tests/run_batch.sh name1 name2 ... [-- args]
cd "$(dirname "$0")/.."
PY=.venv/bin/python
fail=()
names=()
extra=()
seen=0
for a in "$@"; do
  if [[ $a == "--" ]]; then seen=1; continue; fi
  if (( seen )); then extra+=("$a"); else names+=("$a"); fi
done
for t in "${names[@]}"; do
  t0=$(date +%s)
  out=$($PY tests/$t.py "${extra[@]}" 2>&1); code=$?
  echo "== $t (exit $code, $(( $(date +%s) - t0 )) s)"; echo "$out" | grep -E "FAIL|passed|clear|FAILS" | tail -4
  [[ $code -ne 0 ]] && fail+=("$t")
done
echo; echo "FAILED: ${fail[*]:-none}"
