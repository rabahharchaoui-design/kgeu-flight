# Drop zone guidance report

**Branch:** `dz`, merged to `master`.
**Rollback:** `git reset --hard predz`. The tag is pushed.
**Screenshots:** `overnight-screenshots/dz/` (gitignored). Easy (`rookie_*`) and Hard (`pilot_*`) start views by day, at night and in the haboob, plus the edge chevron, the green light and the result card.

## What changed
- **Map.** The C-130 airdrop icon is on the full map and on the mini map. On the mini map it is pinned to the rim when the DZ is out of range. In Easy the waypoint and route are set to the DZ when the mission starts, and they clear as soon as the load is away. Hard only gets the map marker, as asked.
- **"Head for the red smoke."**
  - On screen, from the start until the DZ is on screen within 6 km, and for at least 6 s. It sits at the bottom centre, clear of the mission card and the haboob toast.
  - On the radio once, from Drop Zone Control. It shows in Easy and Hard.
- **Red smoke.** A thick column of red smoke about 1.1 km tall rises from the centre of the DZ. It drifts downwind as it rises, so its lean shows the wind direction. The drift is exaggerated slightly so a light wind still shows. It is drawn over the fog, so it reads from about 5 miles out and in the haboob. It thins out when the camera is inside it, so flying through does not fill the screen. At night there are six red flare pots and a wide red glow, and the smoke above them is lit red. The smoke shows in Easy and Hard.
- **Panels.** A letter A about 64 m tall in 27 orange panels marks the DZ. The bullseye is now pale so the letter reads against it.
- **Easy only:**
  - A faint run in line on the ground, into the wind, from 3 miles out to just past the centre.
  - Six glowing gates at drop height before the release point.
  - A floating DZ marker with the distance, and a red edge chevron when the DZ is off screen.
  - The run in is worked out again whenever the wind shifts by more than about 11 degrees or 6 kt, which matters in a haboob.
- **Jump lights, Easy and Hard.** Every 0.2 s the game predicts where a bundle released right now would land. It uses the same fall, canopy and drift as the real bundle.
  - The loadmaster says "One minute" about 60 s out and "Ten seconds" at 10 s. A red light comes on at 10 s.
  - At the release point you get a green light and "Green light, green light", and the DROP button pulses green.
  - Green means a release would land within 140 m of the centre in Easy (generous) or 60 m in Hard.
- **Drop window.** The "wings level and steady" check now uses a smoothed g. The haboob's buffet used to flicker the window open and shut.
- **Result.** The result card title now gives the distance from the centre. The LANDED card during the fall already showed it.

## Tests
- **`tests/dz_check.py`:** Easy and Hard, each by day, at night and inside a haboob. For each run it checks:
  - the route
  - the hint and the single radio call
  - the smoke's colour, height and lean
  - the letter
  - the flares at night
  - the line, gates, marker and chevron in Easy only
- It then flies the run in from 3 miles and drops on the green light. By day and at night every bundle lands inside the 150 m circle: Hard 30 to 60 m, Easy 90 to 140 m. The test also checks the call order and the result card.
- **The haboob is special.** The wind under the canopy changes as the dust front moves, so the test only checks that the drop on green is scored, not its accuracy. The one minute call can also be skipped when the release point jumps.
- **Full pass (`run_all.sh`):** all checks pass apart from the known F-16 clockwise orbit case.
  - `music_check` needed its baseline to wait for the new drop zone call, which ducks the music as intended.
- **Frame rate (`tests/map_fps.py`), `predz` against `dz` back to back:** every scenario is within noise, including the new drop scenarios by day (1.04), at night (0.95) and in the haboob (1.00).

## Known, not changed here
- On a mission, the mission card sits on top of the ATC subtitle at top centre. This predates this branch.

## Hand test on the iPhone
1. Start the airdrop by day in Easy. The hint should show, you should hear the call, and the red plume should be visible over the aircraft. Follow the route and the gates, listen for the calls, and drop on green. The pallet should land in the circle.
2. The same in Hard. There should be no line, gates, marker or chevron. The smoke and the jump lights alone should get you there.
3. Night: check the flare pots and the red glow.
4. Haboob: check that the smoke still shows through the dust, and that nothing stutters when you fly through the smoke column.
