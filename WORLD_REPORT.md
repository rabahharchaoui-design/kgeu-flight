# World airports and traffic report (SESSION 4)

**Branch:** `world` off tag `pre-world` (master b415863), built 2026-10-01 to 2026-10-02.
**Rollback:** `git reset --hard pre-world` on master. The tag is pushed.
**Screenshots:** `overnight-screenshots/world/` (gitignored, on this machine): `traffic/`, `tcas/`, `regions/`, `ui/`, `tokyo/`, `paris/`, `rio/`, `lb/`, `final/`.
**Version:** `APP_VER` and `version.json` are `2026-10-02-world`. The app name, icon and manifest `start_url` are unchanged, so installed home screen apps update in place on their next launch.

## Verdict

ALL DONE. `world` is merged into master as **4e2598b** and pushed. GitHub Pages serves `APP_VER` `2026-10-02-world` (the automatic Pages build had not started three minutes after the push, so a build was requested through the API and finished a minute later). `tests/live_check.py` passes against the live site, and the three region JSONs, three map bins and the new radio clips all serve with 200. The leaderboard Worker `pfs-scores` is deployed (version bad11c95) with the three airport boards and the `apt` fame field; `/fame` answers with `apt: {RJTT, LFPG, SBRJ}`.

| Commit | Item |
|---|---|
| 58f95a5 | 4.1a AI traffic |
| 1afd5a9 | 4.1b TCAS |
| eadc38d | 4.5 data pipeline and region files |
| 3b8e484 | 4.6a region framework |
| (4.6b) | location picker, radio, per region map, credits |
| (4.2) | Tokyo Haneda |
| (4.3) | Paris CDG |
| (4.4) | Rio Santos Dumont |
| 82a8441 | airport boards, daily rotation, billboards, version bump |
| c8fbf27 | fixes from the full pass |

## Tests

- **Full pass:** the `tests/run_all.sh` list was run in foreground batches. Node suites pass (`orbit_test` keeps its known F-16 clockwise case). Every browser check passes after five fixes (arcade cards fitting on short screens, a `dailyRegion` test hook so Arizona tests pin the daily on days the rotation is elsewhere, pause sheet checks trimming scrolled location cards, the scorch check skipping rays that miss the disc). Known and not from this session, each verified to fail the same way on the `pre-world` worktree: `music_check`'s crossfade timing assertion on a loaded machine, `scorch_check`'s far crash speckle (about one run in six), and `scores_check` / `upgrade_check`'s callsign status timeout.
- **New checks:** `traffic_check`, `tcas_check`, `world_data_check`, `world_check` (every aircraft at every airport and start position, autoland on each home runway, water and terrain, traffic at each airport, the Arizona switch), `world_ui_check` (picker, resume across the reload, radio per region, maps, credits), `tokyo_check`, `paris_check`, `rio_check` (landmarks in the frustum from final and after takeoff, night materials, billboards), `world_lb_check` (boards, challenge end to end, daily rotation with a mocked date, fame on the billboard), plus `world_switch_check` and `region_fps_check` used for the gate below. All are in `run_all.sh` except the last two.
- **Frame rate:** same session A/B against a fresh `pre-world` worktree: `aircraft_fps.py` two rounds, every scenario 0.97 to 1.10 of baseline; `map_fps.py` 0.97 to 1.07; gate 0.90. Same build, headless rAF over 6 s: Glendale final 2.5, Tokyo 9.0 day / 9.3 night, Paris 10.3 / 9.8, Rio 11.3 / 11.3 (the new regions draw far fewer triangles than Arizona: 170k to 230k against 600k). The headless numbers are coarse; the phone is the real test.
- **Region switching:** rjtt, lfpg, sbrj, az, rjtt with real reloads: JS heap 36.8, 37.3, 30.8, 41.5, 38.8 MB, last over first 1.05 (gate 1.5), no errors, no failed requests.
- **TCAS:** a scripted head on conflict gives TA, then RA with the opposite sense on the intruder, then Clear of conflict, in Hard and Easy; nothing below 1,000 ft on final or on the ground.

## What was built, in plain English

### 1. AI traffic (4.1)
Six to ten AI aircraft fly around you inside a 20 nm bubble, nothing is simulated outside it. In Arizona: generic white airliners (one of five tail colours, no airline names) land on 8/26 and depart 7L/25R at Sky Harbor, taxi to the terminal, wait, taxi out and leave; Cessnas fly left traffic at Glendale with touch and goes; two F-16s fly the overhead pattern at Luke (initial, break, downwind, perch, final) and taxi to the ramp; one or two helicopters roam over Phoenix. Everything is kinematic and cheap, with box stand ins beyond 6 km. Nav, strobe and beacon lights at night. Traffic goes around if you sit on its runway inside a mile, holds short while you are near, and never spawns within 1 km of you. The tower still calls traffic ("Traffic, two o'clock, three miles, Cessna, same altitude") with new clips for airliner, F-16 and helicopter. Traffic is off during missions, arcade games, lessons and the strike. The airfield plans are a small table, so each new region brings its own.

### 2. TCAS (4.1)
A round, semi transparent TCAS panel sits bottom right, left of the flight buttons (it hides under the six pack in the cockpit view and can be switched off in Settings under Flying). Symbols follow TCAS II: hollow white diamond for other traffic, filled white diamond for proximate (6 nm, 1,200 ft), amber circle for a Traffic Advisory (closest approach inside 40 s and 0.5 nm / 850 ft), red square for a Resolution Advisory (25 s, 0.3 nm / 600 ft), each with relative altitude in hundreds of feet and a climb or descend arrow. The same symbols are on the mini map and the full map. A TA says "Traffic, traffic"; an RA says "Climb, climb" or "Descend, descend" (the sense with the larger miss), paints a green band and a red band on the VS card and arcs on the six pack VSI, and the intruder manoeuvres the other way; "Clear of conflict" ends it. The cockpit voice is a dry macOS Daniel, not on the radio filter, and it interrupts tower lines. Easy gets plain English ("Plane nearby! Climb now!") and a big green arrow with CLIMB NOW / DESCEND NOW. Alerts are inhibited on the ground, below 1,000 ft AGL on final to your runway, and during missions and games.

### 3. Data pipeline (4.5)
`tools/build_region.py --region rjtt|lfpg|sbrj|all` runs at build time only and writes `assets/world/<id>.json` (231 to 339 KB) and `assets/map/<id>.bin` (107 to 485 KB). The live game never calls Overpass. Sources:
- **Runways:** OurAirports `runways.csv` and `airports.csv` (public domain): exact threshold coordinates, true headings, lengths, widths, displaced thresholds, elevations.
- **Airport and city features:** OpenStreetMap through the Overpass API (taxiways, aprons, terminals, gates, hangars, control tower, aerodrome outline, water, parks, main roads, long bridges, place names, named peaks, the street density grid). Raw responses are cached in `tools/.osm-cache/` (gitignored), so a rerun is offline.
- **Terrain:** Mapzen Terrarium tiles at zoom 12 (SRTM and Copernicus DEM derived, public on AWS), averaged into a 200 m grid (120 m for Rio) with a water mask from the sea level flood fill plus the OSM water polygons. Airports are flattened to the field elevation.
Settings credits now read "Map data © OpenStreetMap contributors", "Runways: OurAirports" and "Terrain: SRTM, Copernicus DEM via Mapzen".

### 4. Regions (4.6)
Each airport is a region, and only one is loaded at a time. The choice is saved (`kgeuRegion`) and the page reloads into it, so a switch costs one splash and the memory of the old region is gone with the page. The game keeps its "home runway frame": the region's main runway (RJTT 34R, LFPG 26L, SBRJ 20L) sits where Glendale's runway 1 used to, so the autoland, the approach guide, the grading and the landing scoring work unchanged. Arizona itself is untouched (every Arizona only block is behind one flag).

The FLY screen and the pause sheet's Change flight panel have a LOCATION picker grouped by region: ARIZONA (Glendale, Luke AFB), JAPAN (Tokyo Haneda), FRANCE (Paris CDG), BRAZIL (Rio Santos Dumont), each a small card with a one line description. Haboob only shows in Arizona. Every aircraft flies everywhere, from the Runway, the Ramp (facing the terminal), the 3 mile final and the 1 mile final. Missions, the arcade games, flight school and the strike stay in Arizona: their cards carry an ARIZONA tag elsewhere and tapping one flies you back there and starts it. Tower calls use new clips: "Tokyo Tower", "de Gaulle Tower", "Santos Dumont Tower", every runway number, and a little generic chatter per region (made up callsigns, no airlines). The mini map and the full map show the region's runways, taxiways, aprons, roads, water, places, peaks, landmarks and traffic; runway numbers appear close in and tapping any runway end sets the destination.

### 5. Tokyo Haneda (4.2)
Runways out in Tokyo Bay with water on three sides, all four runways with markings and lights, the terminals from the OSM outlines with window bands and jet bridges. Landmarks: Tokyo Tower (orange and white lattice, lit orange at night), Tokyo Skytree (lit blue purple), the Rainbow Bridge (lit white, 58 cable lights), Shinjuku, Marunouchi, Shiodome, Shinagawa and Odaiba towers (lit windows), neon ground glow and 3,000 street lights at night. Airliners land 34L/34R in a north flow and 22/23 in a south flow, and depart 05/34R or 16L/16R.

### 6. Paris Charles de Gaulle (4.3)
The four parallel runways, the curved terminals and Terminal 1's drum. Landmarks at their true positions 20 to 25 km south west: the Eiffel Tower lit gold at night and sparkling with 500 white lights for the first five minutes of every hour (real clock), the Arc de Triomphe on its round plaza, Sacré-Cœur on Montmartre (the grid already carries the hill at 127 m), Notre-Dame on the Île de la Cité, La Défense with the Grande Arche on the historical axis, the Seine with six bridges, a Haussmann core of cream boxes with zinc roofs. Airliners land 27R/26L and depart 27L/26R in the usual west flow, the reverse in an east flow.

### 7. Rio Santos Dumont (4.4)
The short runway on Guanabara Bay. Sugarloaf (396 m), Morro da Urca (220 m) and Corcovado (710 m) are raised to their real heights with granite caps, the cable car has two spans with cabins that move, Christ the Redeemer is floodlit at night on Corcovado, Copacabana is a 3.4 km crescent of sand with the wavy promenade and a hotel row, Centro has its office towers and a Museum of Tomorrow pier, hillside clusters of small warm coloured houses, boats and two ferries on the bay, and the Niterói bridge rises to 72 m in the middle. After takeoff on 20L the Sugarloaf is ahead left of the nose.

### 8. Leaderboards, daily, billboards
Three new boards, each one list for Easy and Hard with the mode chip: `apt:RJTT` Tokyo Haneda landing, `apt:LFPG` Paris CDG landing, `apt:SBRJ` Rio Santos Dumont landing. Each is the 5 mile landing challenge to the home runway with the arcade points formula (par = (start distance + 2,500 m) / (1.3 x approach speed) + 25 s; points = 1,000 x min(1.5, par / time) x the landing grade factor; server legal range 0 to 1,500, 20 s minimum, parMax 480 s), documented in `LEADERBOARD.md`. They appear on ARCADE under "World airports" and on the Boards screen. The daily challenge now draws its region from the four each UTC day (same for everyone); a daily in another region switches you there on GO, and the one attempt a day is counted only when the run starts. The Worker's `/fame` returns each airport's all time #1, and each city's @OhRabah billboard shows "TOKYO #1 <CALLSIGN>" (Paris and Rio likewise, "COULD BE YOU" until someone flies it).

## Moved closer than real life, or not to scale
- **Mount Fuji:** the real summit is about 98 km from Haneda on bearing 258, beyond the fog. It is drawn at 42 km on bearing 309 (56 km closer and swung 51 degrees north) so it sits ahead on final and 25 degrees left of the nose after takeoff, fog free and washed toward the haze.
- **Eiffel Tower:** true position, scaled 1.6x (528 m) and drawn without fog so it reads from the CDG final 23 km away. **La Défense** towers are 1.3x taller for the same reason. Everything else in Paris is at true position and scale.
- **Christ the Redeemer** faces the airport rather than its real heading so the arms read from the final. The Rio mountains were lifted to their real heights (the 120 m terrain grid flattened them).
- **Tokyo and Rio billboards** sit 2.6 nm and 0.75 nm from the thresholds, the Paris one 2.5 nm, all on land just off the extended centreline.
- **Water:** the Copacabana bay was missing from the mask and was added by hand (261 cells); the Seine islands were cut back out of the water by hand.

## Known gaps and judgement calls
- Region switching is a page reload with a saved choice, not an in place swap. It is the safest way to guarantee one region in memory at a time in an 850 KB single file; the splash shows once per switch.
- The Arc de Triomphe reads as a block from the air; the Seine's edges follow the 200 m terrain grid; Paris landmarks are small from the CDG final (13 px tower) because they are at their true distance.
- Terminals are extruded OSM outlines with a window band, not modelled buildings.
- Pre-existing and left alone: the Phoenix map stores its water, park, golf and apron polygons as 2 points (a Douglas-Peucker bug on closed rings); fixing it changes `phx.bin`, so it is noted for a later map pass. The F-16 clockwise orbit case in `orbit_test` fails on master too.
- The headless harness cannot measure iPhone cost of the new night lights (3,000 points per city) and the window shader; see the hand test.
- The daily rotation from one rng draw is uneven over a year (az 91, rjtt 77, lfpg 87, sbrj 110 days); it is deterministic and shared, which is what matters.

## iPhone hand test
1. **Upgrade in place:** open the installed app. It should reload once to `2026-10-02-world` with the same name and icon.
2. **Picker:** on FLY, swipe the LOCATION row and tap Tokyo Haneda. Expect "Loading Tokyo…" under the splash, then FLY with Tokyo selected and no Haboob chip. Start the Cessna and the F-16 from Runway, Ramp (facing the terminal), 3 mi final and 1 mi final.
3. **Tokyo:** 3 mi final to 34R by day and at night. Tokyo Tower and the Skytree ahead left, Fuji on the horizon, water under you; the tower says "Tokyo Tower … runway three four right". Pass the @OhRabah board on the Ota bank. Watch the frame rate at night (3,000 street lights and lit windows).
4. **Paris:** 3 mi final to 26L, look far left for the Eiffel Tower and La Défense. Fly the 25 km to Paris, under the tower's first platform, round the Arc. At night in the first five minutes of an hour the tower sparkles.
5. **Rio:** C-130 from the runway: Sugarloaf ahead left after rotation. Fly round Christ, then land back on 20L (4,340 ft). Copacabana and the favelas at night.
6. **Traffic:** at Glendale, 6 to 10 dots on the mini map; Cessnas in the pattern, the F-16 break at Luke, an airliner landing at Sky Harbor. Sit on runway 1 and watch a Cessna go around. Listen for traffic advisories.
7. **TCAS:** Hard, above 1,000 ft. Start a conflict from Safari Web Inspector with `__kgeu.TCAS.tcasConflict('headon')` (or fly near Sky Harbor arrivals). "Traffic, traffic", then "Climb, climb" or "Descend, descend" with the green and red bands on VS, follow it, then "Clear of conflict". Repeat in Easy for the arrow and plain English. The panel must not sit over any button; Settings > Flying > TCAS switches it off.
8. **Maps:** full map at each region, pinch to the runway numbers, tap an end to set the destination, traffic symbols on both maps.
9. **Arcade and boards:** ARCADE, scroll down, fly Tokyo Haneda landing in Hard and in Easy. Results card with the rank line, Boards shows the World airports group. After a Rio run your callsign should appear on the Rio board as RIO #1 next launch.
10. **Daily:** the card names today's airport; if it is not where you are, GO switches you there. Only one official attempt is counted.
11. **Music:** free flight at Tokyo, press Play in the pause sheet. The shuffle plays and continues across tracks; Next and Prev work; it stays silent on the menus.
12. **Pause sheet:** swipe the location row, pick Paris CDG, Apply: the flight restarts at Paris. From Tokyo open MISSIONS: the cards carry ARIZONA and the airdrop switches back and starts.
13. **Performance watch list:** Tokyo at night, the Paris sparkle, the Rio hillside clusters. Note any screen that drops under 60 fps.
