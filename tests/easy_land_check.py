# Easy hands-off landings (phone item 12): every aircraft, every runway end at Glendale and Luke
# (1, 19, 03L, 21R, 03R, 21L), from the 3 nm and the 1 nm final, in calm air and three seeded winds
# (10 kt crosswind from the left, from the right, and a 10 kt quartering tailwind, with the game's
# gusts), stick and throttle never touched. Clean = no crash, touchdown on the runway between the
# threshold and 914 m past it, under 300 fpm, no bounce, within 3 m of the centre line at touchdown
# and 4 m on the rollout, stopped on the runway. Prints the matrix of failures per aircraft and runway end.
# Runs the real physics block in node (tests/easy_land.js), so it takes seconds.
# Run: .venv/bin/python tests/easy_land_check.py [--rand N]   (N extra random game winds per cell)
# Downwind and base entries are not in it: Easy hands off only holds wings level until the aircraft is
# lined up, so there is nothing hands-off to test from there.
import os, subprocess, sys
from harness import Checks
ok = Checks()
HERE = os.path.dirname(os.path.abspath(__file__))

def run(args, show=True):
    p = subprocess.run(['node', os.path.join(HERE, 'easy_land.js')] + args, capture_output=True, text=True, timeout=500)
    if show: print(p.stdout.rstrip())
    if p.stderr.strip(): print(p.stderr.rstrip())
    return p

p = run([])
last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ''
ok('every aircraft lands clean hands off on every runway end, 3 and 1 nm, calm and 3 seeded winds',
   p.returncode == 0 and ' 0/' in last, last)
if '--rand' in sys.argv:
    n = sys.argv[sys.argv.index('--rand') + 1]
    p = run(['winds=calm', 'rand=' + n])
    last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ''
    ok(f'and in {n} random game winds per runway end', p.returncode == 0, last)
# the same seed flies the same air: two runs of one case agree exactly
a = run(['types=cessna', 'ends=19', 'finals=3', 'winds=R', 'v'], False).stdout
b = run(['types=cessna', 'ends=19', 'finals=3', 'winds=R', 'v'], False).stdout
ok('a seeded wind repeats exactly', a == b and len(a) > 200)
sys.exit(ok.done('easy_land_check'))
