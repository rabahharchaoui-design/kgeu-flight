# Map redesign report

**Branch:** `map`, nine feature commits, merged to `master`.
**Rollback:** `git reset --hard premap`. That tag is pushed and points at the commit `master` was on before any of this.
**Screenshots:** `overnight-screenshots/map/` (gitignored, on this machine), iPhone 14/15 landscape (844 x 390, 2x).

| File | What it shows |
|---|---|
| `full_open.png` | the full map as it opens: every airport, the aircraft, legend |
| `full_west.png`, `full_luke.png`, `full_phx.png`, `full_kgeu.png` | four more zoom levels, from the West Valley down to the Glendale runway |
| `legend_drop.png` | after tapping C-130 airdrop in the legend |
| `route_full.png`, `route_minimap.png` | a waypoint on the strike range, the route on both maps |
| `flight_minimap.png`, `minimap_haboob.png`, `full_haboob.png` | the mini map in flight, and both maps on a haboob day |

---

## What changed, in plain English

### 1. Base map
The full map is opaque now. The city is charcoal, the open desert around it a muted tan, water deep blue black, parks and golf courses faint green. The hills are real hillshade, lit from the north west, computed from the game's own terrain, so the White Tanks, the Estrellas and Camelback look like the hills you fly over. Where the city ends comes from how many streets OpenStreetMap has in each 250 m square.

### 2. Real roads
`tools/build_map_data.py` pulls the Phoenix metro roads, water, parks, golf courses and airport taxiways and aprons from OpenStreetMap through the Overpass API. It only runs at build time. It simplifies them and writes one compact file, `assets/map/phx.bin` (516 KB, about 450 KB gzipped). The live game only loads that file and never calls Overpass. Freeways are the thickest and brightest, in sand on a dark casing. Major roads come next, and local streets only fade in as you zoom. I-10, I-17, Loop 101, Loop 202 and Loop 303 get small shields: Interstates are a light shield, Loops an amber pill. Settings now credits "Map data © OpenStreetMap contributors".

### 3. Airports
Runways are drawn to scale as clean white strips, with centre line stripes when you zoom in close. OpenStreetMap taxiways are faint and aprons fainter. They are shifted to the game's own runway positions: KGEU by 10 m, Luke by 29 m and Sky Harbor by 148 m. Each airport has one label card: Glendale · KGEU, Luke AFB · KLUF, Sky Harbor · KPHX and Assault Strip · LZ. Cards are blue for civil and olive for military. Runway numbers only appear zoomed in, as one pill at each end out along the extended centre line.

### 4. Label collision
Every label and icon goes through one pass. The highest priority places first and tries a few spots around its anchor. If a label would overlap another label, an icon, the scale bar or any map button, it hides. The order is: player arrow, waypoint pin, airport cards, highlighted icons, the haboob, mission icons, landmarks, @OhRabah, shields, runway numbers, icon names, terrain names, then city names. `tests/map2_check.py` checks for overlaps at five zoom levels, and again with the haboob up.

### 5. Icon set
Every icon is original and drawn in code: a bold round badge in the game palette with a simple white glyph.
- Airport: an airliner seen from above.
- Military airfield: a delta jet.
- Landmark: a four point sparkle. Landmarks are State Farm Stadium, Camelback and Downtown Phoenix.
- C-130 airdrop: a canopy and pallet.
- Strike range: a crosshair.
- Race and time trial: a stopwatch, at the landing challenge start and today's daily challenge start.
- Flight school: a mortarboard, at the Glendale apron.
- Haboob: gusts. It only shows while one is active, and the dust is shaded on both maps.
- @OhRabah: an @ at each of the five placements (hangar, billboard, rooftop, flag, banner tow).

The player is a bright yellow heading arrow.

### 6. Legend
The legend is a panel on the right that lists each icon type, and it collapses to its header. Tapping a type pulses those icons (or airport cards) for a few seconds, lets them win any label collision, and flies the map to the nearest one.

### 7. Waypoint and route
Tap any runway end, airport card or icon to drop a waypoint. A pin marks it, and a bright cyan route line runs from the aircraft to it. The card at the bottom gives the name, the distance and the time at your ground speed: nm and m:ss for Hard, miles and minutes for Easy. It has a Clear button. The mini map draws the same line and pin, and the HUD destination readout works for any waypoint. The approach guide path still only appears for runway ends.

### 8. Controls
- Pinch to zoom and drag to pan, as before.
- Double tap zooms in two times where you tapped.
- A recenter button sits beside minus and plus.
- The scale bar picks a round distance.
- Panning stops at the edge of the mapped area.
- More detail comes in as you zoom: streets, taxiways, runway numbers, icon names and smaller towns.

### 9. Mini map
The mini map is the same rounded square in the top left corner, the spot it had before, clear of the controls and the view ahead. It is heading up with you in the centre. It now draws from the same cached tiles as the full map (roads, city, desert, hills, water), plus white runways, the route line, traffic, a 2 nm ring, north, and the yellow arrow.

### 10. Performance
- Everything under the labels is drawn once into 256 px tiles at power of two zoom levels. Panning and pinching only composite cached canvases, and labels are redrawn on top.
- A coarser cached tile stands in while a new one renders, with a 10 ms budget per frame, or 4 ms per mini map tick.
- Memory is bounded: at most 32 tiles (32 MB at 2x). Closing the map trims the cache to the 10 tiles the mini map needs. At most 6 spare canvases are pooled, and the rest are released.
- The 3D scene is not drawn under the opaque full map, so the map runs at display rate.
- The base raster (576 x 464, hillshade plus land cover) is built once when the data arrives, in about 18 ms on a Mac.

### 11. Upgrade
There is no service worker, so installed home screen apps pick up the new page and `assets/map/phx.bin?v=1` on their next launch. The app name, icon and manifest `start_url` are unchanged.

---

## Tests

- **Full pass (`zsh tests/run_all.sh`):** every node suite and all 38 browser checks pass, including the new `map2_check`. The one exception is `orbit_test`, where the F-16 clockwise orbit case fails. That case fails the same way on `premap` (mean error 645 m of 7,865), so it is not new.
- **`tests/map2_check.py`** checks:
  - the data file loads: every road class, water, parks, golf, taxiways, the urban grid, and all five shields
  - no label, icon, button or scale bar overlap at five zoom levels, plus a haboob view
  - runway numbers show only close in
  - the legend lists every type, and a tap highlights that type and pans to it
  - tapping the strike range icon sets a waypoint, and the pin, route card, mini map route line and Clear button all work
  - double tap zoom and recenter
  - the haboob gets a legend row, an icon and a dust area
  - no console errors
- **`tests/map_check.py`** (the older map test) still passes: tapping Luke 21R, the HUD readout, the guide path and one tap clear.
- **Frame rate (`tests/map_fps.py`):** a fresh `premap` worktree and this branch, run back to back three times in alternating order. Headless software rendering, so only the ratios mean anything:

| scenario | premap | map | ratio |
|---|---|---|---|
| flying with the mini map | 2.50 | 2.50 | 1.00 |
| inside a haboob (C-130) | 2.50 | 2.44 | 0.98 |
| C-130 crash | 2.50 | 2.56 | 1.02 |
| full map open | 2.44 | 60.17 | 24.6 |
| full map while panning | 2.50 | 60.00 | 24.0 |

  The full map jumps because the 3D scene is no longer drawn under it.

---

## Notes and limits
- The 3D world's city is procedural: its section grid and two freeways were placed by hand in earlier sessions. The map shows the real OpenStreetMap roads, so near Glendale the real Loop 101 and I-10 on the map sit close to, but not exactly on, the 3D freeways. Airports, landmarks, the river and the terrain do line up, because they share the same coordinate frame.
- Sky Harbor in the game sits 148 m off its OpenStreetMap position. Its taxiways were moved to match the game runways, but the streets around it were not, so a street can pass under the end of a runway on the map.
- Map data is fixed at build time. To refresh it, run `python3 tools/build_map_data.py --refetch`. The Overpass responses are cached in `tools/.osm-cache/`, which is gitignored.
- `DecompressionStream` inflates the city density grid. It needs iOS 16.4 or later. On older systems the map still works, but everything outside the parks and water is drawn as desert.

## Hand test on the iPhone
1. Open the map from the mini map in flight. It should be opaque, easy to read in sunlight, and every label crisp with nothing overlapping.
2. Pinch in and out quickly around Sky Harbor. Tiles should sharpen within a frame or two, with no stutter, and runway numbers 07L, 07R and 08 should appear only when close and never stack.
3. Double tap somewhere. It should zoom in there. Tap recenter.
4. Tap each legend row. The icons should pulse and the map should fly to the nearest one. Collapse and expand the legend.
5. Tap an icon (the strike range) and a runway end (Luke 21R). Check the pin, the cyan route, and the distance and time card. Close the map and check that the mini map shows the same route. Clear it.
6. Fly into a haboob with the mini map up, then crash the C-130 with the map closed. Both should hold 60 fps.
7. Settings: the OpenStreetMap credit sits at the bottom right and nothing scrolls.
