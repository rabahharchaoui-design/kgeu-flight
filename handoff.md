# Pocket Flight Sim (formerly KGEU Flight): handoff

Single file game in `index.html`. Checkpoints after each task: `index_task1.html`
through `index_task4.html`. Each task is one git commit.

## Live app

https://rabahharchaoui-design.github.io/kgeu-flight/

Public repo `rabahharchaoui-design/kgeu-flight`, GitHub Pages serving `master`
at `/`. Installable on an iPhone home screen: open in Safari, Share, Add to
Home Screen. It launches full screen with no browser bar.

Sharing it: the link carries Open Graph tags and `icons/share-card.png`, so a
text message renders it as a card rather than a bare URL. There is no way for a
link to install itself on either platform, so the menu carries a short Add to
Home Screen tip that appears only on an iPhone or iPad in Safari that has not
already installed it, and tells in-app browsers to open Safari first.

There is deliberately **no service worker**, so any push is live immediately.
The trade is that there is no offline play and no install prompt on Android.

Every change to the game gets committed and pushed, so the live app tracks the
repo. `tests/live_check.py` verifies the deployed URL end to end.

## Leaderboards

Global high scores, callsigns, ranks, ghosts and the worldwide daily challenge run through a
Cloudflare Worker and D1 database in `server/` (https://pfs-scores.rabahharchaoui.workers.dev).
Everything about it, every score formula and the admin commands are in `LEADERBOARD.md`.
When shipping a change to the game, bump `APP_VER` in index.html and `version.json` together.

## Running the tests

```
npm i three@0.128.0                       # once
python3 -m venv .venv                     # once, for the browser checks
.venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium

node tests/test.js          # takeoff, hold, autoland for all 3 aircraft
node tests/t3.js            # 36 random start autolands, prints "fails 0 / 36"
node tests/t6.js            # easy flight hands off landing and takeoff
node tests/dubins_test.js   # Dubins planner unit test, 500 random problems
node tests/orbit_test.js    # orbit autopilot, both directions, all 3 types
node tests/bench.js <label> # autoland timing benchmark, writes bench_<label>.json
node tests/cmp.js baseline <label>        # before and after table
node tests/bound.js         # theoretical lower bound on autoland time

.venv/bin/python tests/ui_check.py       # layout, overlap and tap size, 3 phone sizes
.venv/bin/python tests/tilt_check.py     # tilt steering
.venv/bin/python tests/strike_check.py   # range siting and a full engagement
.venv/bin/python tests/desktop_check.py  # Mac smoke test
.venv/bin/python tests/live_check.py     # the deployed https site, end to end
.venv/bin/python tests/a2hs_check.py     # Add to Home Screen tip shows only where it should
.venv/bin/python tests/scores_check.py   # leaderboards end to end against wrangler dev (localhost:8765)
.venv/bin/python tests/upgrade_check.py  # in place upgrade from the prescores build
.venv/bin/python tests/scores_fps.py <prescores_root> . 1   # frame rate A/B with leaderboards in play
.venv/bin/python tests/live_scores_check.py  # the deployed game and Worker, fresh profile, cleans up
(cd server && npm test && npm run test:live) # the Worker API, local then live
```

All of the above pass as of the Task 4 commit.

## State: all four tasks done

1. **Autoland**: Dubins shortest path planner to a per type final approach fix,
   replacing the base point nav phase.
2. **Tilt**: rewritten for iOS, with a test that drives synthetic sensor events.
3. **Phone controls**: thumb zone layout, More drawer, context buttons, flap and
   gear readouts, expo and camera feel. Automatic overlap check.
4. **Reaper strike**: live range, orbit autopilot, sensor ball, four missiles,
   scoring and radio.

## Known limitations

- **40 percent autoland target is below the physical floor.** `tests/bound.js`
  computes the shortest feasible Dubins route flown at the best constant speed,
  with no deceleration cost and an 18 s rollout: 237 s for the C172, 219 s for
  the MQ-9, 188 s for the F-16, against 40 percent targets of 192, 171 and 145 s.
  Dropped by the user; final result is 10.0, 10.8 and 1.8 percent faster than
  baseline on the random starts and 28, 8 and 12 percent from the hold.
- **Orbit autopilot, F-16 counter clockwise.** An F-16 at 300 kt has a 3.9 km
  turn radius. Joining a circle only twice that, from across it, turning against
  the orbit direction, it can settle into a stable orbit the wrong way round.
  `tests/orbit_test.js` reports this as KNOWN rather than failing. The Reaper,
  which is what actually uses the mode, holds the circle to within 35 m.
- **Tilt pitch sign is unverified on real hardware.** The roll axis is
  self consistent because the reading is relative to the calibration pose. The
  pitch axis depends on the vendor sign convention for
  `accelerationIncludingGravity`, which differs between iOS and the spec and
  cannot be checked in headless Chromium. The invert pitch toggle exists for
  exactly this. **Needs one check on a real iPhone.**

## Not verifiable without a real iPhone

- Whether `requestPermission` is actually granted from the Tilt button tap. The
  code calls both `DeviceOrientationEvent.requestPermission` and
  `DeviceMotionEvent.requestPermission` synchronously inside a `click` handler,
  and the Tilt button is excluded from the shared `pointerdown` `preventDefault`
  that could swallow the click. The test stubs the permission result.
- Whether pitch is the right way round (see above).
- Real device frame rate. Geometry is instanced or pooled and the hot loops do
  not allocate, but this has only been measured in headless Chromium.
- Whether the safe area insets and `visualViewport` offsets land correctly under
  a real notch and home indicator, and inside the Claude app header.
