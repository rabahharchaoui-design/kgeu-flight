# Overnight build report

**Branch:** `overnight`, nine feature commits, merged to `master`.
**Rollback:** `git reset --hard pre-overnight` — that tag is pushed and points at
the commit `master` was on before any of this.
**Screenshots:** `kgeu/overnight-screenshots/`, 78 of them. They are gitignored so
they do not bloat the repo; they are on disk on this machine.

Everything you asked for got built, including all three bonus items.

---

## What got built

### 1. C-130H Hercules

A fifth aircraft, not a fourth — the game already had four (C172, Alpha, F-16,
MQ-9). I read your "4th aircraft" as counting the three you name later in the
scoring section and left the Pipistrel Alpha alone.

50 t, 132 ft span, four Allison T56 turboprops, 162 m² wing. Heavy and slow and
stable by the numbers rather than by feel: a 20° bank limit against the F-16's
35°, sluggish autopilot rates, a 1.6 s spool, and a 45 s deceleration constant
that means you plan everything early. Rotates at 115 kt, approaches at 130.
Takes off in about 3,900 ft and autolands at 193 fpm in the headless physics
harness.

The airframe is procedural, in the same box-and-cylinder style as the other
non-HD models: high wing, four nacelles with props spun about their own axes,
upswept tail with the cargo ramp, six main wheels in tandem inside the sponsons.

**The engine sound is the part worth listening to.** A T56 is a constant-speed
prop: 1,020 prop rpm, four blades, so blade pass sits at 68 Hz no matter what the
power lever does. Power moves loudness and turbine whine, not pitch — which is
why a Herc sounds the same on the ramp and on the go. A second oscillator detuned
2.2% gives the beat that four unsynchronised engines actually make.

### 2. C-130 missions

A mission area 12.7 km due west of KGEU, past Luke, with its two map sections
claimed for desert the same way Luke and the stadium claim theirs.

**Airdrop.** A 150 m scoring circle painted as a bullseye with VS-17 panels on
the corners. The DROP button only arms between 500 and 1,500 ft, below 160 kt,
wings level. The bundle free-falls 0.7 s, opens a canopy, comes down at 6 m/s and
drifts with the real wind — so the wind that flight actually changes where it
lands. Scored on distance from the centre.

**Short field.** A 3,000 × 90 ft graded strip, landable from either end, scored
on how far past the threshold you touched and how much runway you used stopping.
Target is to touch in the first 500 ft and stop within 2,000.

Two things I found and fixed here. The runway 09 approach climbs into the White
Tank foothills from 3.5 km out, so the mission spawns you on 27 instead, which is
flat desert the whole way and faces Glendale. And the strip was completely
invisible at first because it sat at y=0.12, underneath the West Valley section
overlay at y=0.15.

### 3. Luke AFB and the spawn picker

**Luke was already in the right place.** Before moving anything I checked it
against the published ARPs, and it was 26 m out over a 4.43 nm baseline. So this
tightened rather than relocated: ARP to 1 m, runway 03 to its true heading of
042.6°, and both runways to published length — 03L/21R at 9,908 ft, 03R/21L at
10,013 ft, 1,001 ft apart. `tests/luke_check.js` asserts all of that against the
FAA numbers so it stays true.

The runways got real markings: threshold bar, piano keys, the runway number,
aiming points, centreline. They were invisible on the first attempt because
#c4c2bb concrete under #f1f1ec paint has no contrast left once the sun hits it;
the concrete is now mid-grey.

The F-16 starts at Luke, everything else at Glendale, and a two-button picker
sends any aircraft to either field. Picking an aircraft resets it to its home
field; choosing the other one sticks until you change aircraft. Ramp, runway and
three-mile final all work at both, and a taxiway now joins the Luke ramp to both
runways so a ramp start can actually reach one.

Navigation and autoland still target KGEU runway 1, unchanged. That is what makes
the Luke-to-Glendale run a thing you fly rather than a thing you press a button
for.

### 4. ATC radio

107 clips cut with `say`, trimmed of silence, mono AAC at 64 kbps, 1.7 MB total.
Regenerate with `python3 tools/make_radio.py`.

**Voices:** Samantha (Enhanced) for the controllers, Evan (Enhanced) for the
pilots. No Premium voices are installed on this machine — `say -v '?'` lists five
Enhanced en_US and nothing above that. I went female-tower against male-pilot
rather than two male voices because once both are squeezed into 300–3000 Hz two
male voices blur into each other and you lose track of who is talking.

Lines are stitched from parts — callsign, facility, wind, runway, clearance are
all separate clips:

> Herky 71, Luke Tower, wind 080 at 9, runway 03L, cleared for takeoff.

Callsigns follow the aircraft (Skyhawk 8401L, Viper 1, Reaper 8401L, Herky 71,
Pipistrel 502AT), the tower and runway follow the field, and clearances now get a
**pilot readback in the other voice**, which is the thing that makes it sound like
a real exchange rather than an announcement.

Playback goes through a 300–3000 Hz band pass, a light tanh drive, a squelch
click at each end of the transmission, and a carrier hiss underneath it. The
chain is built by one function so `tests/radio_check.py` can render a test tone
through the *real* filters in an OfflineAudioContext and measure the result: 60 Hz
comes back at 3.5% of the passband, 12 kHz at 3.0%, 800 Hz at 95.7%.

Radio volume slider and an on/off toggle in the menu, both saved. `T` toggles it.

### 5. Scores, records, pilot log, achievements

Landings are graded A–F out of 100: sink rate 35%, distance from the aim point
25%, centreline offset 20%, airspeed against that type's Vapp 20%. The card shows
each component with its own score, so a B tells you *which part* cost you.

Grading works on whichever runway the wheels actually touched — Glendale runway
1, either Luke runway, or the C-130 assault strip — with the aim point 1,000 ft
in from the threshold in each case.

Per-aircraft records, each ranked on what matters to that aeroplane:

| | ranked on |
|---|---|
| C172, Alpha | landing grade |
| F-16 | Luke to Glendale time, with peak G |
| MQ-9 | loiter score: hits 45%, average miss 30%, time with the ball locked on a live target 25% |
| C-130 | airdrop distance, and short-field stopping distance |

Pilot log across every aircraft: total airborne time, landings, best streak of B
or better. Five achievements. A NEW RECORD banner when a best falls. A records
screen off the menu, and a reset that takes two taps because it erases everything
on the device.

### 6. Sunset and night flying (bonus)

Three presets rather than a running clock, because the point is to fly an
approach into a low sun or onto a lit runway. Each sets the sky gradient, fog
colour and distance, sun colour, angle and intensity, and the hemisphere light.
Saved between sessions.

Runway lighting already existed but vanished at any real distance. What reads at
night is a new additive Points layer at the same positions and colours — white
edges, green thresholds, red ends, blue taxiway — one draw call each for Glendale
and for **Luke, which had no lights at all before**. Stars come out on a fixed dome.

This is also what makes the Night Landing achievement reachable; `isNight()` was
written against a time of day that did not exist yet.

### 7. Six-pack instrument panel (bonus)

Airspeed, attitude, altimeter, turn coordinator, heading, vertical speed — drawn
on a canvas over the scene in the cockpit view of the C172 and the Alpha. Pointer
events pass through so the floating stick still works where the panel overlaps
it. The Cessna already carried N8401L on both sides of the tail.

**The test for this earned its keep.** `tests/sixpack_check.py` reads the drawn
pixels rather than trusting the drawing code, because a needle that is 180° out
still looks like a working instrument in a screenshot. It found three real bugs:

- The airspeed and VSI needles were both **180° out**.
- The airspeed scale started at the upper right instead of the lower left, so the
  whole dial was a quarter turn from where an ASI puts its low end.
- The altimeter had a needle turning **once per 100 ft**, which no altimeter has.
  It is now a proper three-pointer: 1,000 / 10,000 / 100,000 ft per turn.

### 8. Landmarks (bonus)

Four of the five already existed, and already accurately: State Farm Stadium 71 m
out, the White Tank Mountains 37 m, Camelback 96 m, the downtown Phoenix skyline
77 m from their real positions relative to KGEU. `tests/landmark_check.js` now
asserts that against published coordinates.

Sky Harbor was the one missing. Built at 28.6 km ESE, placed to 2 m: three
parallel runways at published lengths, centrelines, the two parallel taxiways,
Terminals 3 and 4 with their concourses, and the tower. Its runways are paved, so
landing there works rather than counting as an off-field landing.

---

## What got skipped, and why

**Nothing you asked for was skipped.** Four required features and all three bonus
items are in. Three things are worth knowing about:

**Sky Harbor sits in open desert, not in the city.** The West Valley section
generator only covers 15.5 km from KGEU, which is why the downtown skyline is out
there on its own too. Extending that grid would cost frame rate for scenery you
fly past at altitude, so I left it.

**The flight-school instructor still uses speech synthesis.** Its lines are built
at runtime from measured numbers ("slow to 55 knots") and cannot be pre-recorded.
It deliberately bypasses the radio filter — the instructor is sitting beside you,
not transmitting, so a plain voice is right there anyway. Every actual radio line
is pre-recorded.

**The 30 fps gate could not be applied as written.** Headless Chromium rasterises
in software, and the *existing, unmodified* game already ran at 3–11 fps there. An
absolute 30 fps threshold would have failed every feature including the ones I did
not write. Instead the harness stores a per-aircraft baseline and fails anything
costing more than 20% of it. Nothing came close — frame rate is flat at 3.2–3.6
across all five aircraft, unchanged from baseline. **Real-device frame rate is
still unmeasured.** See the hand-test list.

---

## Things that were already broken

I checked these against the `pre-overnight` tag before blaming my own work. All
three fail identically on the old code:

- **`tests/orbit_test.js`** — "f16 cw holds the radius" fails deterministically,
  645 m of 7,865, on both branches. The handoff notes only flag the
  counter-clockwise case as known.
- **`tests/ui_check.py`** — 51 overlap reports and an overall FAIL at 667×375
  (iPhone SE landscape), identical count on both branches. My new elements
  contribute none of them.
- **`tests/t3.js`** is flaky, not broken. It randomises wind per run and does not
  seed it. Over ten runs: baseline had failures in 3 runs, the overnight branch in
  1. `createState` already has a `WIND_FIX` hook that would make it deterministic
  — worth wiring up some time.

The handoff's claim that everything passed as of the Task 4 commit is stale.

---

## What went live

Merged to `master` and pushed, so **<https://rabahharchaoui-design.github.io/kgeu-flight/>**
is running all of the above. There is still no service worker, so it is live
immediately with no cache to clear.

Verified after the push by loading the deployed URL in a real browser: page loads,
no console errors, all five aircraft spawn, radio clips fetch and decode from the
live host.

The page now pulls 1.7 MB of audio in the background after you first tap Start.
Lines that play before their clips land show text and click the squelch, which is
a fine degraded mode, but **on a slow connection the first minute may be quieter
than it should be.**

---

## Please test these by hand on the phone

I could not check any of this in headless Chromium.

**Radio sound** — the one I am least able to verify. Does it read as a radio or as
a text reader? Specifically:
- Is the squelch click at each end of a transmission at the right level, or does
  it snap?
- Is the carrier hiss audible under the voice, or is it either inaudible or
  hissy?
- Does the pilot readback land far enough after the clearance to sound like a
  reply rather than an interruption?
- Tower and pilot are a woman and a man. Can you tell them apart instantly?
- The radio volume slider is in the menu. Does its range feel right, or is it all
  bunched at one end?

**C-130 feel** — the numbers are right; whether it *feels* like a Herc is your
call.
- Does it feel heavy and deliberate, or just sluggish and annoying?
- 20° of bank is a deliberate limit. Does it read as "this is a transport", or as
  "the controls are broken"?
- The engine note should not change pitch when you move the throttle, only
  loudness and whine. Does that read as right, or as a bug?
- Try the airdrop: fly west from Glendale at 1,000 ft, find the orange bullseye,
  DROP. And the short field: it is a small strip and it comes up fast.

**Landing grades**
- Fly a landing you think is a solid B and see whether the card agrees. If the
  grades feel harsh or generous, the weights are one line each in `gradeLanding`.
- The "from the aim point" component is the one most likely to feel wrong — it
  wants you 1,000 ft in from the threshold.
- Land at Luke and at the assault strip too; all three should grade.

**Also worth a look**
- **Night.** Pick Night in the menu, start on a three-mile final. The runway
  lights are the whole point. Also try Luke at night.
- **Six-pack.** Pick the C172, press View until you are in the cockpit. Check the
  gauges agree with the HUD numbers — I fixed three needle bugs and want a second
  opinion.
- **Frame rate.** Genuinely unmeasured on real hardware. The C-130 with four prop
  discs and Night with two extra glow layers are the most likely to cost
  something.
- **Tilt pitch direction.** Still unverified from before — unrelated to this work,
  but still open.
