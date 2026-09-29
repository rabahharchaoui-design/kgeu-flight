# Session 3 report: flight feel and visuals

**Branch:** `feel`, items 3.0 to 3.13 plus 3.END, merged to `master`.
**Rollback:** `git reset --hard pre-feel`. That tag is pushed and points at the commit `master` was on before any of this.
**Screenshots:** `overnight-screenshots/` (gitignored, on this machine): `ab/`, `haboob/`, `crash/`, `eggs/`, `navlights/before` and `navlights/after`, `music/`, plus `night/`, `sensor/`, `strike/`, `props/`, `roll/`, `controls/` and `dropcam/` from the first half of the session.

Items 3.0 to 3.5 were finished in the overnight run of 27 to 28 September. Items 3.6 to 3.13 were finished on the morning of 28 September; 3.11, 3.12 and 3.13 were added to the plan that morning.

---

## What changed, in plain English

### 3.0 Controls: real multi touch, no hidden menu
Every on screen button owns only the finger that started on it. You can hold the stick and tap gear, flaps, brake and camera at the same time. The More button is gone. Easy sees stick, throttle, camera, map and pause. Hard adds GEAR, FLAPS UP and DOWN with a flap readout, and BRAKE. Fixed gear aircraft have no GEAR button, the F-16 has no flaps buttons, drones get SENSOR, the C-130 gets DROP on airdrop missions.

### 3.1 Smooth rolls
Attitude and the chase camera are quaternions; the camera's up follows the aircraft's up. Rolls, barrel rolls and inverted flight no longer jerk. A late fix in this session: since 3.1 a frame slower than a quarter second dropped its time entirely, so a long stutter froze the flight. Time is now capped, not dropped.

### 3.2 Night lighting
Runway, taxiway, threshold, end, approach and beacon lights are small sharp points with a tight halo. Each aircraft has its real light fit: red left, green right, white tail, wingtip strobes, red beacon, F-16 formation strips, landing lights that come on below 1,000 ft with a pool on the runway. Night clouds are dark blue grey.

### 3.3 Cameras, sensor ball, drop camera
Tower and crowd views are gone. MQ-9A and MQ-9B have a sensor ball: DAY TV, IR white hot and black hot, drag to slew, pinch or buttons to zoom, LOCK, and an autopilot that orbits the point you are looking at until you move the stick. The C-130 gets a free look pad, a LOOK BACK ramp view and a camera that follows the pallet down.

### 3.4 Strike mission
Targets are bigger and marked with diamonds, edge arrows and distances, NEXT TARGET slews the ball (Easy auto locks). Explosions are a pooled system: fireball, rolling mushroom smoke that drifts with the wind, shockwave, debris, secondaries, night ground glow, white hot in IR.

### 3.5 Propellers
Painted twisted blades at idle that fade into a translucent blur disc at speed. Four blades on each C-130 engine, MQ-9 yellow stripes form a faint ring.

### 3.6 F-16 afterburner
Above 82 percent throttle the nozzle petals open (a morph target on the real petal mesh) and a layered flame appears: orange outer plume, blue white core, shock diamonds embedded in the core, a glow inside the nozzle. Military power shows only a faint heat haze. At night the flame is a third bigger, the nozzle warms slightly, and an orange pool lights the runway behind the jet on the takeoff roll. The engine sound gains a deep rumble and crackle. A partial attempt stashed the night before was reused and polished.

### 3.7 Haboob
A fourth weather chip beside Day, Sunset and Night on the fly screen and in the pause menu's Change flight panel. A 24 km wall of rolling orange brown dust starts 4.5 km south east of your start and moves north west at about 35 kt. As it reaches you: visibility drops to a few hundred metres, the sky goes orange, the sun becomes a dim disc, the wind swings to 150 at 35 with gusts, and you get vertical gusts and buffet. The tower calls "visibility one half mile in blowing dust" and you get a toast at 6 km (Easy gets a second plain one at 3 km). Switching weather in the pause menu spawns or removes the storm.

### 3.8 Callsign check
A sweep of 72 flights (every aircraft, base, start position and skill) found no wrong callsign. What you heard on the MQ-9 was the ambient "Viper 21 flight" chatter, which after the first flight of a session could play before your own tower call. Now every flight resets the chatter timer, chatter waits until your opening exchange is done, and two transmissions never overlap. Also fixed: the pattern "check wheels down, cleared to land" and "nice landing" calls always said Glendale Tower and runway 1, even at Luke; and the strike range "Rifle" and hit or miss calls had no recorded clips.

### 3.9 Crash explosions
Every crash explodes through the strike explosion pool, sized per aircraft. Cessna and Alpha: medium fireball, burning wreck, black column. MQ-9s: medium fireball, both wings break off, the body stays with its V tail. F-16: big fast fireball and a trail of burning pieces along the impact path. C-130: four fuel tank fireballs in sequence along the wing, a huge black mushroom, nose, centre wing and tail sections, a wide debris field, secondaries, a fire that burns for 90 s. All crashes: camera shake, a boom that arrives a beat later at distance, night ground glow. The camera settles upwind of the wreck, clear of the smoke. The full screen crash sheet is replaced by a small reason line at impact and a compact card after 3 s with RETRY (same start) and MENU.

### 3.10 @OhRabah easter eggs
The official YouTube icon, drawn from the same path as the credits link, unstretched and unrecoloured, beside the handle: a banner on a Glendale hangar (the second box hangar on the ramp), a two post billboard just west of the State Farm Stadium lot facing west (lit at night, seen out the left window on right downwind and ahead right on final to runway 1), a rooftop sign on the tallest downtown block (lit at night), a small rippling flag 40 m off the drop zone strip, and a Cessna towing an @OhRabah banner around a 3 km loop east of Glendale at about 1,500 ft. It has nav lights and the tower calls it "a banner tow plane" in advisories. Nothing on Luke, nothing on the military aircraft.

### 3.11 Nav lights readable at night
The steady red, green and white lights have a crisp core with a soft halo, a minimum on screen size, and sit at about half the strobe peak. The red and green cones fade gradually past 110 degrees instead of snapping off, the white tail light is brighter, and each wingtip has a faint coloured glow so the chase view behind still sees red left and green right. They also show at sunset. Before and after shots for all six aircraft are in `overnight-screenshots/navlights/`.

### 3.12 Quiet menus
No radio on the home screen or any menu. Radio lines only play while flying. Pausing, opening the menu, going home or backgrounding the app fades a call out over about a tenth of a second instead of cutting it. A pending clearance still plays after Resume.

### 3.13 Music system (code only)
A shuffled playlist player. Drop `.m4a` files in `assets/music/` and list them in `assets/music/playlist.json` (GitHub Pages cannot list a folder, so the list is the manifest). Every track plays once before any repeats, with 1.5 s crossfades. `dogfight.m4a` will loop in the Red Flag Dogfight. Music plays on home, menus, Flight School, missions and arcade; in free flight only if "In free flight" is on (off by default). It dips under radio calls. Settings has Music on/off, a volume slider, Next song and the free flight toggle; the pause sheet has Music on/off, volume and Next song. All saved. With the folder empty it stays silent with no errors. Tracks load lazily after the first tap.

---

## Full pass

`zsh tests/run_all.sh` now covers the session 3 checks too (multitouch, roll, night, sensor, drop camera, strike fx, props, afterburner, haboob, callsign, crash, easter eggs, nav lights, quiet menus, music). 43 Playwright scripts and 5 node suites.

| Result | Scripts |
|---|---|
| Pass | everything except the rows below |
| Known, pre existing | `orbit_test.js` F-16 clockwise orbit radius (documented before this session) |
| Flaky, pass on rerun alone | `school_check.py` (timing), `arcade_check.py` (records rows when run inside the full batch) |
| Fixed during 3.END | `a2hs_check.py` and `live_check.py` had hardcoded paths to the old `~/Desktop` location; now repo relative |

No console errors on any aircraft, on the menus, or with the empty music playlist.

## Frame rate

Same session, back to back: a fresh baseline from a `pre-feel` worktree, then the `feel` branch, iPhone landscape, headless software rendering. Gate: 80 percent of baseline.

| Aircraft | pre-feel | feel | Ratio |
|---|---|---|---|
| Cessna 172 | 3.2 | 3.2 | 100% |
| F-16 | 3.1 | 3.2 | 104% |
| MQ-9A | 3.2 | 3.1 | 96% |
| MQ-9B | judged against the MQ-9A (new since the tag) | 3.2 | 96% |
| C-130 | 3.1 | 3.2 | 104% |

Flat within noise. Headless rendering is CPU bound at about 300 ms a frame regardless of scene, so this gate only catches gross regressions; the phone is the real test (hand test item 17). `tests/overnight_fps.json` now holds the fresh pre-feel numbers.

---

## iPhone hand test list

Do these on the phone in landscape, iOS Safari. The harness cannot reach a real phone, so these are the things only you can judge.

1. **Multi touch, Hard mode.** Hold the stick in a turn and tap GEAR, FLAPS UP, FLAPS DOWN, BRAKE and VIEW one after another. Each must work while the turn continues.
2. **Button layout.** Easy in the Cessna: stick, throttle, camera, map, pause only. Hard in the F-16: GEAR and BRAKE, no flaps buttons. Hard in the Cessna and Alpha: flaps, no GEAR. MQ-9: SENSOR. C-130 on the airdrop mission: DROP. No More button anywhere.
3. **F-16 rolls, Hard mode.** Full aileron rolls, a barrel roll, a loop, and a stretch of inverted flight. No jerk, no camera flip.
4. **Night flight.** Night, Cessna, 3 mile final at Glendale: sharp runway edge and threshold lights, no dome glows, the landing light pool on the runway below 1,000 ft.
5. **Nav lights (3.11).** Same night flight in the chase view: red glow on the left tip, green on the right, a bright white tail light. Repeat in the F-16 and the C-130. Then Sunset: still visible.
6. **Afterburner at night.** F-16, Night, runway at Luke. Hold full throttle with the brake on: the nozzle opens, the flame grows with shock diamonds, the runway behind lights orange, the engine rumbles and crackles. Release the brake and watch the pool follow on the roll. Back to 80 percent: petals close, flame gone within about 3 s, haze only.
7. **Sensor ball.** MQ-9B at 10,000 ft: SENSOR, drag to slew, zoom, MODE through DAY TV, IR white hot, IR black hot, LOCK on Luke. "AUTOPILOT ENGAGED" and an orbit. Leave the view, move the stick: tone and "AUTOPILOT OFF".
8. **Strike run.** Arcade, strike range: markers, NEXT TARGET, a hit with the big fireball and mushroom column, a secondary on the bunker. Look at it in IR.
9. **C-130 airdrop with the look back camera.** Drag the LOOK pad around, tap LOOK BACK, drop, follow the pallet down, see the distance from centre, camera returns.
10. **Dust storm.** Haboob, Cessna, Glendale ramp. The wall on the south east horizon. Take off and fly at it: the toast, the tower's blowing dust call at about 3 km, the wall towering as you get close, then orange murk, a dim sun, gusts and bumps, and the wind readout swinging to 150 at 35. Turn around and fly out the front. Then pause, switch to Day, Apply: the storm is gone. Switch back: it respawns.
11. **Crash, C-130.** Fly into the ground: four fireballs, the black mushroom, the fuselage in three pieces, a wide debris field, the boom, shake, then the RETRY and MENU card after 3 s not covering the fire. RETRY puts you back where that flight started. Try it at night for the ground glow.
12. **Crash, F-16.** High speed into the desert: the big fast fireball and the burning trail along the path. Then the Cessna and an MQ-9 (wings off, body stays).
13. **Callsigns (3.8).** Start any aircraft, pause, switch to the MQ-9A at Luke on the runway, Apply. The first thing you hear must be "Reaper 8401L, Luke Tower … cleared for takeoff" and your readback. Viper 21 chatter only after that. Fly a Luke pattern in the F-16: "Luke Tower … runway 03L, check wheels down, cleared to land".
14. **Quiet menus (3.12).** Sit on the home screen and each menu for a minute: silence. Start a flight, pause during the tower call: it fades, not cuts. Resume: the readback follows. Open Main menu mid call: fade, then silence.
15. **Music (3.13).** With the folder empty: no errors, nothing plays. Then put two or three .m4a files in `assets/music/`, list them in `playlist.json`, reload: tap the home screen and music starts. Next song crossfades. Start a mission: music dips when the tower talks. Free flight: silent until "In free flight" is on. Check the pause sheet controls and that settings survive a reload. Confirm the very first tap on the home screen starts audio on iOS (a `pointerup` listener does it; a `touchend` was avoided to keep the multi touch rules).
16. **Finding each @OhRabah.** Taxi past the second box hangar at Glendale. Fly right downwind at Glendale and look left for the billboard near the stadium, then again at night. Night, fly toward downtown for the rooftop sign. Watch for the banner tow Cessna circling east of Glendale at about 1,500 ft. C-130 to the assault strip for the flag.
17. **Frame rate.** Watch for stutter in the C-130 crash, inside the haboob with the wall in view, and the afterburner at night with the ground pool. These are the three heaviest scenes.

## Known gaps and notes

- Headless frame rate is software rendered at about 3 fps for every build, so the fps gate can only catch large regressions. The phone is the real test (item 17).
- `school_check.py` is flaky on timing (lesson 1 sometimes takes 95 to 105 s of simulated time instead of about 60) and on the first run after a cold start; it passes on rerun. Same on master.
- The banner on the tow plane reads correctly from both sides rather than mirrored on one side as a real banner would.
- The hangar banner has a little self light by day because that hangar face is in shade.
- The C-130 wreck pieces retire at about 58 s while the fire burns to 90 s.
- Listing a missing music file logs a 404 line in the console (the browser's own message); the game itself stays silent and error free.
