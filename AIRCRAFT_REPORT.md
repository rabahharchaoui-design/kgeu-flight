# Aircraft accuracy session

Branch `aircraft`, tagged rollback point `preaircraft` (pushed). One aircraft per commit,
merged to master as `79bedff` and live on GitHub Pages (verified, see the end).
The F-16 and C-130 were not touched; they were the quality bar.

| Commit | What |
|---|---|
| `8c25110` | Aircraft 1: Cessna 172S N8401L, rebuilt as an HD loft |
| `701bb96` | Aircraft 2: Pipistrel Alpha Trainer N502AT, rebuilt as an HD loft |
| `6778ca6` | Aircraft 3: MQ-9A Reaper AF 02 4002, gunmetal, reshaped |
| `5be2008` | Aircraft 4: MQ-9B SkyGuardian N190TC, gunmetal, reshaped |
| `1129d5d` | Fix: a negative frame step no longer throws in the traffic paths (pre-existing) |
| `bc60892` | Tests: `tests/aircraft_fps.py`, same-session A/B frame rate |

## How the models are built now

All four are built in `makeHD()` with the F-16's technique: lofted superellipse rings
and NACA sections (`AERO.loft`), with the MQ-9 panel-line skin. Two things are new:

- **Livery wrap** (`wrapLivery`, `liveryUV`): the Cessna and Alpha paint schemes are
  drawn as a paint shop draws them, a side view and a top view in metres. The drawing
  is then baked onto the fuselage texture by station and ring angle. Stripes, windows
  and registrations sit exactly on the skin, with nothing floating or buried. Fins
  read their own side's drawing, so lettering reads the right way round on both sides.
- **Drone markings** (`fusPatch`, `tailPatch`, `MAT.decalLit`): lit decals that follow
  the fuselage and the tail sections. They dim at night instead of glowing.

Triangles (F-16 = 7,988, C-130 = 11,196):

| Aircraft | Before | After |
|---|---|---|
| Cessna 172 | 1,340 (boxes) | 7,924 |
| Pipistrel Alpha | 1,342 (boxes) | 5,832 |
| MQ-9A | 8,824 | 10,386 |
| MQ-9B | 7,104 | 8,528 |

## Screenshots

All in `overnight-screenshots/aircraft/` (gitignored, like every screenshot folder):

- `before/`: all six types from the fixed angles before any change.
- `cessna172/`, `pipistrel/`, `mq9a/`, `mq9b/`:
  - `before_after.png`: before (left) against after (right), side, front, top and three quarter.
  - `<type>_sheet.png`: side, left, front, rear, three quarter and top, next to every photo in the ref folder.
  - `compare_*.png`: the game camera placed to match a reference photo, stacked over that photo.
  - `<type>_{day,night,haboob,cockpit,carousel}.png`: in the game at 844x390. Chase view airborne by day, at night and inside the haboob; the cockpit or nose camera; the menu carousel.

Tools: `tests/model_shots.py` (now reads the `refs/` folders and adds left, rear
and photo-matched angles) and `tests/aircraft_shots.py`.

## 1. Cessna 172 (N8401L)

**Reference:** `refs/cessna172/ref_c172.jpg`, the only photo in the folder. It is N6065M, a
172S at Daytona Beach: white, with the factory plum swoosh and no wheel fairings.

**What didn't match (before):** it was a box model. Box fuselage with a tube tail cone;
flat slab wing with no airfoil, taper or dihedral; the swept fin and long dorsal
missing; strut and gear legs were sticks; big white wheel pants, which the photo does
not have; no cowl shape, spinner or nose inlets; windows were one blue box; navy and
gold stripes instead of plum; the registration was a flat plate; no antennas or beacon.

**Now:**
- Proportions follow the photo: 8.28 m long, 11 m span, fin top at 2.72 m. The windshield slopes from the cowl onto the wing root.
- Wing: constant chord inboard, leading-edge taper outboard, NACA 2412 with 1.7 deg dihedral and washout, flap and aileron lines.
- Streamlined struts with end fairings; the long 172 dorsal running into a swept fin; a 3.45 m stabiliser.
- Gear: tubular spring main legs, oleo nose gear with forks and torque link. No wheel fairings, as in the photo.
- Cowl: nose bowl inlets, exhaust stub. White spinner and the existing McCauley two-blade prop.
- Detail: comm blades, belly antennas, GPS puck, pitot, red beacon on the fin cap, steps, brake calipers.
- Windows: windshield, door window, rear side window and the Omni-Vision rear window, lined up with the photo.
- Livery, measured off the photo: plum band and pinstripes from the cowl, the upsweep to the rear window, the two cut blades, the tail-cone lines onto the fin with the fin wedges. N8401L in 12 in italic plum where the photo carries its registration, plus a small "Skyhawk SP" script.
- Nav lights, strobes, beacon, landing and taxi lights moved to the new geometry.
- The cockpit eye moved to the left seat, under the roof.

## 2. Pipistrel Alpha Trainer (N502AT)

**Reference:** `refs/pipistrel/ref_alpha.jpg`, the only photo. It is N529AT, white with the
blue ALPHA Trainer scheme.

**What didn't match (before):** it was a box and lathe model. The pod was a plain
ellipsoid with a round blue canopy blob; slab wings; a thin rectangular fin; a green
accent stripe instead of blue; no door window shape; stick gear with black hubs;
the registration was a flat plate on a cylinder boom.

**Now:**
- Pod and boom: the pod follows the photo, with a short cowl, a steep windshield, and the cabin and wing well forward. A long, gently tapering boom runs to a broad T-tail with the stabiliser on top, plus a ventral strake and tail skid.
- Wing: high cantilever, constant chord centre, trailing-edge taper outboard, 2 deg dihedral.
- Windows: the big door window with its raked aft edge, and the windshield side window.
- Livery: the blue pinstripe from the cowl, the ALPHA Trainer band tapering down the boom, the slash along the window, the grey underline. Blue fin band with "Pipistrel" and the round badge. N502AT on the boom ahead of the fin, as in the photo.
- Gear: single spring main legs, a steerable nose leg, red hubs as in the photo. White spinner, two-blade prop.
- Lights and the cockpit eye moved to the new geometry.

## 3. MQ-9A Reaper (AF 02 4002)

**References:** `refs/mq9a/` (ref_mq9a.jpg, IMG_2866, IMG_2867, IMG_2868; the WEBP was
converted with sips into /tmp).

**What didn't match (before):** light grey instead of gunmetal. The SATCOM dome barely
stood proud of the fuselage. Small dorsal inlet (the photos show a prominent scoop).
Small ventral fin. No satcom mast or spine dome, no nose probes. Narrow main gear
track. The serial sat on the rear fuselage instead of the ventral fin. No tail code,
no star and bar, no unit badge, no tail tip bands.

**Now:**
- Paint: dark gunmetal #4A4E54 (`MAT.gunmetal`), matte with a slight metallic sheen.
  - The albedo is set a touch above #4A4E54 so the lit side measures about #4B4D51 on screen; the shaded side reads darker.
  - A faint emissive lift at dusk and night keeps the airframe readable against a dark sky.
- Shape: taller SATCOM dome, a bigger dorsal inlet with a dark mouth, a deeper swept ventral fin, a wider main gear track.
- Detail: the angled satcom mast and spine dome, nose probes, bare-metal spinner. Four Hellfires on the pylons are kept (the strike mission uses them).
- Markings, light grey on lit decals, placed as in the photos:
  - AF over 02, then 4002, on both sides of the ventral fin.
  - CH / 42 ATKS on both tail surfaces (from IMG_2866).
  - Red tip bands on the tail surfaces (ref_mq9a).
  - Star and bar on the aft fuselage and upper wings.
  - The unit badge by the wing root.
- The beacon moved forward of the enlarged inlet.

## 4. MQ-9B SkyGuardian (N190TC)

**References:** `refs/mq9b/` (IMG_2864, IMG_2865, and the two pasted N190TC images).

**What didn't match (before):**
- Light grey instead of gunmetal.
- Winglets curled round a large quarter circle; the photos show a tight bend into a straight, swept, dark blade.
- Dark nose, dark leading edges and dark tail tips that the photos don't show.
- The dark belly band and the dark engine bay panel of N190TC were missing.
- Two box blade antennas instead of the satcom mast and dome.
- Small spinner and small inlet.
- The wing root was too narrow.

**Now:** gunmetal like the A. What sets the B apart is kept and sharpened:
- The longer 24 m wing, broader at the root, ending in sharp dark winglets canted 15 deg outboard.
- The dark belly band, the dark ventral fin, and the dark engine bay panel with vents.
- A taller dome, the bigger dorsal inlet, the satcom mast and dome, nose probes.
- A large bare-metal spinner.
- A clean wing with pylon stubs only (the demonstrator flies clean).

N190TC is on the aft fuselage, and EXPERIMENTAL with the flag sits behind the dome,
both in light grey where the photos put them. The lights moved to the new winglets.

## Night and haboob

Both drones were checked from the chase view airborne:
- At night, the gunmetal airframe reads as a grey silhouette against the sky, with the nav lights at the tips.
- Inside the haboob, it is a crisp dark silhouette against the dust.
- See `mq9a/reaper_night.png`, `reaper_haboob.png`, `mq9b/mq9b_night.png`, `mq9b_haboob.png`.

## Decisions I made on my own (please check)

1. **Cessna photo is not N8401L.** The only photo in `refs/cessna172` is N6065M, a 172S
   from Wikimedia (see `refs/SOURCES.md`), not your airplane. I matched its paint scheme,
   stripe colours, lack of wheel fairings and registration placement, and wrote N8401L
   there. If your airplane's scheme differs, drop photos of N8401L into
   `refs/cessna172` and the livery drawing (the `side()` function in `buildC172HD`)
   is quick to redo. I couldn't look N8401L up: the FAA registry refused the request.
2. **Pipistrel wing.** You wrote "low wing", but the photo in `refs/pipistrel` (and the
   real Alpha Trainer) has a high wing on the cabin roof with a T-tail. I followed the
   photo, since the brief says to match `refs/pipistrel`. The bubble canopy and slim
   fuselage are there. The photo shows N529AT; the model carries N502AT, as the game
   always has.
3. **MQ-9A tail markings.** No photo shows 02-4002 itself. I used the Creech CH /
   42 ATKS markings from IMG_2866 and laid the serial out the way the photos lay theirs
   out on the ventral fin: AF over the fiscal year, then 4002.
4. **The PEA school logo** on the Cessna photo's fin was left off. It is the flight
   school's branding, not a Cessna marking.
5. **Parked ramp Cessnas and the AI traffic Cessna** still use the old low-cost box
   model with their own liveries. Thirteen HD 172s on the ramp would cost about 100k
   triangles and hundreds of draw calls on the phone. The AI traffic MQ-9 uses the new
   gunmetal MQ-9A.
6. **Pre-existing bug fixed** (`1129d5d`): releasing a held test loop could hand `tick()` a
   negative frame step, which pushed an AI traffic path below 0 and threw every frame.
   The frame step is now clamped at zero. It reproduced identically on `preaircraft`.

## Tests

- **Full `tests/run_all.sh` list** (run in foreground batches): every check passes
  except `orbit_test`. That one fails identically on a clean `preaircraft` worktree
  (F-16 clockwise orbit, mean error 645 m of 7,865), a pre-existing failure already
  noted in MUSIC_REPORT.md.
- `tests/overnight_check.py` on the four types: spawns, no console errors, fps 96 to
  100% of the stored baseline.
- **Frame rate:** `tests/aircraft_fps.py`, measured back to back with alternating order
  against a fresh `preaircraft` worktree. Every scenario falls between 0.93 and 1.06 of
  preaircraft across both runs (floor 0.90), on both the rAF frame count and wall time
  per rendered frame:
  - each rebuilt aircraft on the runway and on final;
  - the Cessna cockpit (0.95 to 0.96, the smallest);
  - the MQ-9A at night;
  - the carousel.

  Headless software GL runs at about 3 fps, so this only catches gross regressions. The
  phone is the real test.
- **Console errors:** none on the branch or on the live site.

## Live

- Pushed `79bedff`; GitHub Pages built it in about 35 s.
- `tests/live_check.py` passes over https: every type spawns, no console errors, radio clips decode.
- The live site draws the new models; triangle counts match the branch exactly (7,924, 5,832, 10,386 and 8,528).
- No service worker, so home-screen installs pick up the new build in place.
- App name, icon and `manifest.json` (`start_url`, `scope`) are unchanged.

## iPhone hand test list

- [ ] Carousel: swipe through all six; the Cessna, Alpha, MQ-9A and MQ-9B show the new models turning.
- [ ] Cessna 172: plum swoosh, italic N8401L aft on both sides, no wheel pants, red beacon on the fin. Start on the runway, take off, land.
- [ ] Cessna cockpit view: left seat, cowl in the lower part of the view, six-pack in Hard, wing roots overhead. Check the view feels right on approach.
- [ ] Pipistrel Alpha: high wing, T-tail, blue ALPHA Trainer band. "Pipistrel" on the fin reads correctly from both sides. Red hubs, N502AT on the boom. Check the cockpit view too.
- [ ] MQ-9A: gunmetal, AF 02 4002 on the ventral fin, CH / 42 ATKS on the tails, star and bar. Fly the strike range: Hellfires, sensor ball, missiles.
- [ ] MQ-9B: long wing with dark canted winglets, N190TC aft, EXPERIMENTAL by the nose, landing on 1 mile final.
- [ ] Night: both drones still readable from the chase view, nav lights at the tips, strobes and beacons flashing on all four types.
- [ ] Haboob: fly each drone into the dust; the silhouette stays clear.
- [ ] Props: blades turn into the blurred disc on all four; the Cessna disc sits right in front of the cowl.
- [ ] Crash any of the four: the explosion and wreck camera behave as before.
- [ ] Frame rate on the phone: Cessna at the Glendale ramp, MQ-9B on 1 mile final, and the carousel all feel as smooth as before.
- [ ] Music, drop zone (C-130) and 1 mile final: unchanged.
- [ ] The installed home-screen app updates to the new models without reinstalling. Name and icon unchanged.
