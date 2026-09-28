# Models report

**Branch:** `models`, three feature commits plus a `.gitignore` commit, merged to
`master`. **Rollback:** `git reset --hard pre-models`; the tag is pushed and
points at the commit `master` was on before this session.
**Screenshots:** `overnight-screenshots/models/`, four angles per aircraft plus
a contact sheet next to its reference photo. Gitignored like last night's, on
disk on this machine. **Reference photos:** `refs/`, gitignored; the four I
fetched for the aircraft you did not supply photos for are public domain USAF
or CC BY-SA Wikimedia Commons images, listed with authors and licences in
`refs/SOURCES.md`.

Regenerate the screenshots with `.venv/bin/python tests/model_shots.py
overnight-screenshots/models`. Every aircraft is photographed in the game, on
the runway, through a free camera test hook, so what you see is what the game
draws.

---

## 1. C-130H rebuilt

The old Hercules was seventeen boxes and cylinders. The new one is built the
way the F-16 is: superellipse fuselage rings lofted into one smooth indexed
surface, NACA-section wings and tails lofted the same way, vertex-colour paint
under the shared panel-line skin texture, and merged geometry wherever parts
share a material.

What is in it, against the reference photos:

- **Fuselage.** Twenty-one rings from the low radome tip to the tail cone. The
  radome sits below the centreline the way the real nose does, the roof climbs
  steeply to the flight deck, the cargo section is a constant squared-off
  section for 13 m, and the underside sweeps up at 18 degrees from the sponson
  end to the tail. The tail cone ends nearly at roof height, which is what puts
  the stabiliser where it is in the side photo.
- **Flight deck glazing.** An open sheet lofted from the fuselage rings between
  the sill and the eyebrow line, so the dark wrap-around windscreen follows the
  nose exactly, with four pillars. This needed a new `open` option on the loft
  helper; the F-16 and MQ-9 lofts are untouched by it.
- **Wing.** Straight leading edge, constant 4.88 m chord out to the outboard
  engines, then tapering on the trailing edge to 2.4 m at the tip, 15 percent
  thick at the root, 2 degrees of anhedral. Flap and aileron hinge lines top and
  bottom.
- **Engines.** Four lofted T56 nacelles whose tops run flush with the wing upper
  surface and which hang a metre below it, each with the chin oil-cooler scoop
  and a half-buried exhaust behind the trailing edge. Inboard nacelles run past
  the trailing edge, outboard ones stop at it, as in the top-view photo. A long
  pointed spinner and four broad square-tipped paddle blades per engine, merged
  into one mesh each, spinning about their own axis; the game swaps them for the
  blur disc once the engines are running.
- **External tanks** between the engines, on pylons.
- **Tail.** Fin lofted from a 7.3 m root to a 2.6 m tip, swept on both edges,
  with the dorsal fillet, rudder hinge, painted flash and cap stripe. Tapered
  stabiliser on the tail cone with elevator hinges.
- **Sponsons and gear.** Lofted blisters from station 11.8 to 19.8, two 1.42 m
  tandem mains each side half-buried in them, twin nose wheels under the flight
  deck. The gear group scales into the body for retraction like every other
  model.
- **Details.** Crew door, both paratroop doors and the ramp and cargo door
  outlines are strips that follow the fuselage curve; portholes, astrodome,
  blade antennas, pitot probes.
- **Markings.** U.S. AIR FORCE on both sides, star and bar on the aft fuselage
  and wings, USAF on the wing, the Kentucky fin flash, flag and serial (see the
  tail number section). Side markings are draped over the actual fuselage
  section so nothing is buried in the skin; the first pass had exactly that
  problem and it is why the star was invisible.

Paint is FS 36173-ish grey, a shade lighter underneath, darker radome.

Budget: 10,372 triangles in 70 meshes. The F-16 is 7,752 in 76, the MQ-9A
8,408 in 62, so the Hercules is the biggest model in the game by a third and
still well inside what an iPhone draws without noticing. It was 3.5 fps against
the old box model's 3.1 in a back-to-back run on the software-rendering
harness, so it costs nothing measurable.

The flight deck camera moved with the new frame (the model origin is now 3.05 m
above the wheels, the fuselage centreline, so the wheels touch at the same
y = -1.5 the other models use).

## 2. MQ-9B SkyGuardian

A sixth aircraft, `mq9b`, next to the MQ-9A in the picker, which is now three
buttons a row. Built as a separate builder from the Reaper's so the A is
unchanged, sharing its style:

- Fuselage 11.7 m against the A's 11.0, the SATCOM dome 10 cm taller and the
  nose a shade wider, dark radome.
- Sensor ball under the chin, a little further forward.
- 24 m wing. The flat wing runs to 11.1 m a side at 1.52 m root chord and 0.6 m
  tip, 2.4 degrees of dihedral; the last metre sweeps round a quarter circle
  into the upturned winglet, lofted as a continuation of the tip section. Dark
  de-icing boots on the leading edge and dark winglets, as in the photos.
- Larger Y tail with the ventral fin, dark tips. Pusher prop, three blades.
- The pair of blade antennas ahead of the wing, the spine inlet and exhausts.
- Clean wing with pylon stubs and no Hellfires; the demonstrator flies clean.
- N190TC draped large on the tail boom, EXPERIMENTAL by the nose.

6,688 triangles in 46 meshes.

**Flight feel.** The type table is the Reaper's with the wing changes: span
24 m, area 27.5 m², induced drag factor 0.016 against the Reaper's 0.022, mass
4,600 kg. In the physics harness it rotates at the same speed, holds the same
pattern, autolands at 108 fpm, and glides at an L/D of 13.3 against the
Reaper's 12.1 from the same idle-power test, so it floats further on final,
which the tips text warns about. It takes the Reaper's radio callsign shape
with four new clips ("Sky Guardian one niner zero tango charlie"), gets a
landing-grade row in the records screen, and the harness judges its frame rate
against the Reaper baseline until it has one of its own. The strike range and
orbit mode stay Reaper-only, as before.

## 3. Tail numbers

Every serial below was checked against at least one public web source before it
went on a model. The Cessna stays N8401L. The MQ-9B carries N190TC, read off the
reference photo.

| aircraft | painted | style on the tail | status |
|---|---|---|---|
| F-16C | AF 89 032, tail code AV, green 555 FS band | tactical: code large, small "AF" over "89", large "032" | verified |
| MQ-9A | AF 02-4002 | small stencil on the tail boom | verified |
| C-130H | AF 11231, KENTUCKY fin flash | AMC transport style: five digits the same size, base name in the flash | verified serial; flash text best effort |
| MQ-9B | N190TC | large civil registration on the aft fuselage, EXPERIMENTAL by the nose | from the reference photo |
| C172 | N8401L | unchanged | |

### F-16C 89-2032, Basher 52

On 2 June 1995 Capt. Scott O'Grady of the 555th Fighter Squadron, the Triple
Nickel, was patrolling the Bosnian no-fly zone out of Aviano when a Bosnian Serb
SA-6 fired from near Mrkonjić Grad broke his F-16C in half. He ejected, evaded
for six days on rainwater, grass and ants, and was pulled out on 8 June by
Marines of the 24th MEU flying off USS Kearsarge. The jet was 89-2032, a Block
40E built for the 70th TFS, passed through the Iowa Guard and the 526th FS, and
had worn the AV code since March 1994. It was the only F-16 the squadron lost
over the Balkans. The traffic F-16 pair that flies the Luke pattern uses the
same builder, so they carry the same fin for now.

- F-16.net airframe profile, "89-2032 (USAF 89032)", Block 40E, 555 FS AV from
  March 1994, written off 2 June 1995 to an SA-6, pilot O'Grady:
  https://www.f-16.net/aircraft-database/F-16/airframe-profile/2880/
- Aviation Safety Network record "General Dynamics F-16C Fighting Falcon 89-2032,
  Friday 2 June 1995": https://aviation-safety.net/wikibase/46497
- F-16.net 555th FS unit history, the O'Grady loss as the squadron's only Balkan
  F-16 loss: https://www.f-16.net/units_article149.html
- Wikipedia, Scott O'Grady (unit, missile type, callsign Basher 52):
  https://en.wikipedia.org/wiki/Scott_O'Grady

The fin band is the squadron colour and text as best I could reconstruct it; no
text source described the 1995 band, so treat the green band and "555 FS" as
representative.

### MQ-9A 02-4002, the first Reaper in Afghanistan

02-4002 was one of the two pre-production YMQ-9s. It did the early weapons
testing, flew fourteen border missions for the Department of Homeland Security
in late 2003, and then became the first Reaper to deploy to Afghanistan, where
it logged 254 combat sorties and 3,266 combat hours in four years. It has been
on display at the National Museum of the United States Air Force in Dayton since
25 January 2010. The 09-4066 that was on the model before is also a real Reaper
serial (a 174th Attack Wing aircraft, New York Guard, written off in November
2013), but the museum airframe is the better documented story.

- General Atomics, "New MQ-9 Reaper exhibit opens at National Museum of the U.S.
  Air Force", serial 02-4002 and the history above:
  https://www.ga-asi.com/new-mq-9-reaper-exhibit-opens-at-national-museum-of-the-u-s-air-force
- Military Trader, the same exhibit and serial:
  https://www.militarytrader.com/museums/q-9-reaper-exhibit-opens
- Wikimedia Commons category "02-4002 (aircraft)", photographed at the museum:
  https://commons.wikimedia.org/wiki/Category:02-4002_(aircraft)

Serials that could not be used: the Reaper the Russian Su-27 brought down over
the Black Sea on 14 March 2023 and the ones the Houthis have shot down over
Yemen were never publicly identified by serial.

### C-130H 91-1231, Man o' War

Kentucky's 123rd Airlift Wing named all twelve of its Hercules after racehorses.
91-1231 was the 2,000th C-130 built, delivered new to Louisville in May 1992 and
christened Man o' War by Senator Wendell Ford. It flew 11,040 hours with the
165th Airlift Squadron, through Restore Hope in Somalia, Provide Promise over
Bosnia, hurricane relief at home, and Afghanistan and Iraq, went to the Delaware
Guard in 2021, and came back to Louisville on 22 September 2025 to be put on
static display in its original markings. The reference photo airframe, 74-1692,
turned out to be real but not an Alaska Guard jet: Joe Baugher's list has it at
Elmendorf in 1976 and with the Ohio Guard in 2019, and the Air Force accident
board names it as the Yokota aircraft in the 2016 Balikatan parachute fatality.
Man o' War has the better story.

- DVIDS, "Man o' War C-130 returns to 'Old Kentucky Home' for retirement",
  serial number 91-1231, 2,000th C-130, hours and units:
  https://www.dvidshub.net/news/555175/man-o-war-c-130-returns-old-kentucky-home-retirement
- Kentucky National Guard, the same release:
  https://ky.ng.mil/News/Article/4369981/man-o-war-c-130-returns-to-old-kentucky-home-for-retirement/
- Joe Baugher's 1991 USAF serial list, "1231 (MSN 382-5278) was 2000th Hercules
  and named 'Man O'War'", 165th AS Kentucky ANG:
  https://www.crouze.com/baugher/usaf_serials/1991.html
- Wikimedia Commons category "91-1231 (aircraft)":
  https://commons.wikimedia.org/wiki/Category:91-1231_(aircraft)

Style: Air Mobility Command transports carry no two-letter code; the base or
state name sits in the fin flash and the number is painted as five digits the
same size (source for the convention:
https://migflug.com/afterburner/air-force-fin-markings-tail-codes-explained/).
So the fin reads KENTUCKY over AF 11231. I could not find a text source for the
exact colour and lettering of the Kentucky flash, so that part is representative.

### MQ-9B N190TC

N190TC is the General Atomics SkyGuardian demonstrator in the second reference
photo, a civil registered airframe flown under an experimental certificate, which
is why it carries a big N number on the aft fuselage and EXPERIMENTAL by the
nose instead of a USAF serial. Taken from the photo, as asked.

## 4. Screenshots

`overnight-screenshots/models/<type>_{side,front,top,quarter}.png` for all six
aircraft, and `<type>_sheet.png` with the four game shots in a column beside the
reference photo or photos. The C-130 sheet uses four of your eight photos, the
MQ-9B sheet both of yours, and the other four use the fetched public-domain or
CC photos in `refs/`. `tris.json` in the same folder has the triangle and mesh
count of each model as the game draws it:

| model | triangles | meshes |
|---|---|---|
| C-130H | 10,540 | 70 |
| MQ-9A | 8,408 | 62 |
| F-16C | 7,988 | 76 |
| MQ-9B | 6,688 | 46 |
| Pipistrel Alpha | 1,118 | 29 |
| Cessna 172 | 1,024 | 31 |

## 5. Test pass

Everything was run from the `models` branch before the merge. iOS Safari is the
target, and as before none of this reaches a real iPhone; it is headless
Chromium at 844x390 with software rendering, so the absolute frame rates mean
nothing and only ratios within one session do.

**Frame rate.** The baseline stored at the start of the session turned out to be
worthless: the untouched Cessna measured 4.2 fps at 6 pm and 3.1 to 3.4 fps every
run after, so the machine, not the game, drifted. The final pass therefore
re-measured the `pre-models` tag from its own worktree and the `models` branch
back to back, in that order, on a quiet machine:

| | pre-models | models |
|---|---|---|
| Cessna | 3.1 | 3.1 |
| F-16 | 3.6 | 3.8 |
| MQ-9A | 3.2 | 3.1 |
| MQ-9B | (none) | 3.2 |
| C-130 | 3.2 | 3.1 |

The stored baseline in `tests/overnight_fps.json` is now that fresh pre-models
measurement. An earlier A/B of just the C-130 commit gave 3.1 old against 3.5
new. The lofted models are not slower than the boxes they replaced.

**All six aircraft spawn, no console errors**, on the harness and on the model
screenshot run.

**Other checks, models branch:** luke_check, landmark_check, dubins_test (500 of
500), t6, radio_check, score_check, sixpack_check, strike_check, a2hs_check,
desktop_check all pass. mission_check passed on two of three runs; the one
failure, "drop window arms in the band", did not reproduce on either tree when
rerun, so it is a timing flake in the test and not a regression. ui_check is
the same pre-existing 667x375 overlap report as last night, identical count on
both trees. orbit_test and t3 were not rerun; both were already flagged as
broken or flaky in last night's report.

**Physics harness, MQ-9B:** takes off on Auto T/O, holds, autolands from a
three-mile final at 108 fpm, and glides at L/D 13.3 against the Reaper's 12.1.

## 6. What to look at on the phone

- **C-130 from the chase camera and the flight deck.** The flight deck camera
  moved with the new origin; it should sit behind the windscreen looking over
  the nose. If it is inside the roof or under the floor, the numbers are one
  line in the type table (`cam1`).
- **Prop blur.** Four discs at 2.05 m radius fade in when the engines run. If
  they read as grey plates rather than a blur, the disc opacity is the game's
  shared 0.3.
- **MQ-9B on final.** It is meant to float. If it floats too far to be fun,
  raise `k` from 0.016 toward the Reaper's 0.022.
- **Fin markings.** The F-16's AV code and serial are now draped over the fin
  aerofoil; the old flat decal was partly inside the fin, which is why LF and
  the serial were faint. Check they read from both sides.
- **The picker.** Six buttons, three a row. Check it fits on the SE.

## 7. Left out or uncertain

- No text source describes the 555th FS fin band as worn in 1995 or the
  Kentucky ANG flash; the colours and band text are representative, the serials
  are not.
- The two traffic F-16s in the Luke pattern share the player jet's builder, so
  they also wear 89-2032. Different serials for them would need the builder to
  take the marking as an option, which it now can (`opt.marks` on the C-130
  builder is the pattern) but I did not wire it for the traffic.
- The SkyGuardian does not get the strike range or the orbit mode. It flies
  clean, as the demonstrator does, and nothing in the brief asked for it.
- The old box-built `buildC130` stays in the file as the fallback the game
  uses if the HD module fails to build, the same arrangement the F-16 and
  Reaper already had.
