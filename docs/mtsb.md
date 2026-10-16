# MTS-B sensor ball: public facts and the values the game uses

Pocket Flight Sim's MQ-9A and MQ-9B carry a sensor ball modelled on the Raytheon Multi-Spectral Targeting System,
MTS-B (AN/DAS-1). This sheet lists every value the sensor view uses, where it comes from, and which ones are
**approximations, not published**. Only public sources are used: manufacturer pages and brochures, US Air Force and
General Atomics fact sheets, reputable defence press. Nothing here claims to be exact, and the game is not a
procedures trainer. The code labels the same values in the `MTSB` table in `index.html`.

Confidence key: **Published** (a manufacturer or Air Force page states it), **Secondary** (a brochure copy or press
article quotes it; the original could not be opened from here), **Approximation** (not published; a plausible value
chosen for the game and kept consistent).

## 1. The turret

| Item | Public fact | Confidence | Game value | Source |
|---|---|---|---|---|
| Name | Multi-Spectral Targeting System B, AN/DAS-1 | Published | "MTS-B" | [Raytheon MTS page](https://www.rtx.com/raytheon/what-we-do/air/mts) |
| Mounting | Rotating ball under the nose of the MQ-9 | Published | Ball origin under the nose, as the existing models place it | [Air Force MQ-9 fact sheet](https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104470/mq-9-reaper/), [armedconflicts.com entry](https://www.armedconflicts.com/AN-DAS-1-MTS-B-Multi-Spectral-Targeting-System-t147035) |
| Diameter | 22 inch gimbal | Secondary | Not used by the simulation (the 3D models were built earlier) | [Wikipedia, MQ-9 Reaper](https://en.wikipedia.org/wiki/General_Atomics_MQ-9_Reaper), [GlobalSecurity, Predator B](https://www.globalsecurity.org/intell/systems/predatorb.htm) |
| Weight | Not found in any public source reachable for this sheet (the Compact MTS is quoted as a 12 inch turret under 60 lb; that is a different, smaller product) | Not published | Not used | [Unmanned Systems Technology, Compact MTS](https://www.unmannedsystemstechnology.com/2017/06/raytheon-unveils-lightweight-multi-spectral-targeting-system/) |
| Azimuth coverage | 360 degrees continuous | Secondary | Continuous, no stop: the ball can look straight behind the aircraft | Raytheon MTS-B brochure as reproduced on [Scribd](https://www.scribd.com/document/624081617/mts-b) (quoted by search; the page itself could not be opened) |
| Elevation coverage | +40 degrees up to -135 degrees down (45 degrees past straight down) | Secondary | +40 to -135 degrees, relative to the aircraft's belly plane | same brochure copy |
| Stabilisation | Gyro stabilised turret (all MTS variants) | Published in general terms | Inertial line of sight: with no input the picture holds still while the aircraft turns | [Raytheon MTS page](https://www.rtx.com/raytheon/what-we-do/air/mts) |
| Slew rate | Not published | Approximation | Thumb rate scaled by field of view: full deflection = 1.5 x the vertical field of view per second, capped at 60 deg/s (WFOV 51 -> capped 51 deg/s, NFOV 0.7 deg/s, UNFOV 0.12 deg/s); smoothed with 0.12 s acceleration and 0.10 s deceleration time constants | game choice |
| Track and geo slew rate limit | Not published | Approximation | 60 deg/s gimbal rate while a track or geo stare drives the ball | game choice |
| Slew to nose | Operator control; the exact preset angles are not published | Approximation | Azimuth 0, elevation -15 degrees, reached in about 0.6 s | game choice |

## 2. Sensors

| Sensor | Public fact | Confidence | Game mode | Source |
|---|---|---|---|---|
| Colour daylight TV | "color/monochrome daylight TV" | Published | **DTV**: colour picture | [Air Force MQ-9 fact sheet](https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104470/mq-9-reaper/) |
| Near or shortwave IR | The Air Force fact sheet lists a "shortwave infrared camera"; Wikipedia lists an image-intensified TV | Published | **NIR**: monochrome reflected light picture (vegetation bright, roads and roofs mid grey), noise stronger at night. The owner asked for NIR; the Air Force words it shortwave IR | Air Force fact sheet; [Wikipedia](https://en.wikipedia.org/wiki/General_Atomics_MQ-9_Reaper) |
| Thermal (mid wave) IR | "infrared sensor"; MTS-A and B are described as mid wave IR in trade press | Published (IR), Secondary (mid wave) | **IR WHT** (white hot) and **IR BLK** (black hot), the game's existing heat shader | Air Force fact sheet |
| Image fusion | "The full motion video from each of the imaging sensors can be viewed as separate video streams or fused" | Published | Not modelled as a separate mode (noted in the report) | [Air Force MQ-9 fact sheet](https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104470/mq-9-reaper/) |
| Laser rangefinder | "laser rangefinder/designator" | Published | **LASE**: one press measures the slant range; the range is shown with an L for 10 s, otherwise it is computed from the terrain and marked C | Air Force fact sheet |
| Laser designator | Designates for laser guided munitions (Hellfire, GBU-12) | Published | Strike range: the designator lases automatically while a missile is guided; status LTD ON | Air Force fact sheet |
| Laser illuminator | "laser illuminator" (an IR pointer) | Published | Shown as a status (LTM) only; not drawn | Air Force fact sheet |
| Laser code | Real codes are set per mission; no MQ-9 default is published | Approximation | CODE 1688, a generic four digit code (shown, never changes anything) | game choice |
| Automatic video tracker | "multimode video tracking"; the brochure lists centroid, area and feature tracking | Published (multimode), Secondary (the modes) | **PT TRK** (point, a centroid track on a vehicle), **AR TRK** (area, a correlation track on a ground patch), **GEO** (geo stare: the ball held on a coordinate by navigation, no video lock) | [Raytheon MTS page](https://www.rtx.com/raytheon/what-we-do/air/mts); brochure copy on Scribd |

## 3. Fields of view

Published for MTS-B (vertical x horizontal, degrees), from the brochure copy. The horizontal / vertical ratio is
4:3. The game sets the camera's vertical field of view to the published vertical angle; a phone screen is wider
than 4:3, so the thin corner brackets on the overlay mark the published 4:3 frame and the picture outside them is
extra width the real video does not have.

| Name (game label) | Published angle V x H | Confidence | Game vertical FOV | Notes |
|---|---|---|---|---|
| Wide (WFOV) | 34 x 45 | Secondary | 34 | |
| Medium wide (MWFOV) | 17 x 22 | Secondary | 17 | |
| Medium (MFOV) | 5.7 x 7.6 | Secondary | 5.7 | |
| Medium narrow (MNFOV) | 2.8 x 3.7 | Secondary | 2.8 | |
| Narrow (NFOV) | 0.47 x 0.63, TV and IR | Secondary | 0.47 | |
| Ultra narrow, TV (UNFOV) | 0.08 x 0.11 | Secondary | 0.08 (DTV and NIR) | NIR sharing the TV optics is an **approximation** |
| Ultra narrow, IR (UNFOV) | 0.23 x 0.31 | Secondary | 0.23 (IR WHT and IR BLK) | |
| Electronic zoom | 2:1 and 4:1 in the smallest fields of view | Secondary | EZ 2X and EZ 4X after UNFOV on the zoom ladder (0.04 and 0.02 TV, 0.115 and 0.0575 IR) | The brochure also allows e-zoom in NFOV; the game keeps one ladder and offers it only at the UNFOV end (**game simplification**) |
| Wide FOV in IR and NIR | Not listed separately from TV | Approximation | Same as TV | |

Easy mode keeps the five wider steps (WFOV to NFOV) and names them in plain words ("Zoom 3 of 5").

## 4. Symbology (generic, in the style of public MQ-9 full motion video)

Released MQ-9 video shows white monospace text in the corners and a gapped crosshair; exact layouts differ by
software version and are not published as a standard. The game's overlay is generic and makes no claim to match
any real ground control station. Every element:

| Element | Game content | Value source |
|---|---|---|
| Crosshair | Four arms with a centre gap, small range ticks; brackets for the published 4:3 frame; a dashed box showing what the next narrower field of view will frame (hidden at the narrowest) | geometry |
| Track gate | Square box on the tracked vehicle (point), larger dashed box (area), a diamond on the coordinate (geo) | tracker state |
| Sensor azimuth and elevation | AZ relative to the nose, R or L and degrees; EL relative to the belly plane; DEP, the depression below the horizon | computed from the gimbal |
| Slant range | RNG in nautical miles and feet, L when lased (10 s), C when computed | laser or terrain |
| Point of interest | Latitude and longitude (degrees, decimal minutes), MGRS (WGS84, 1 m), elevation in ft MSL | computed from the crosshair ground point (the game's terrain) |
| Aircraft | Heading (magnetic), altitude ft MSL, indicated airspeed in knots | flight model |
| North arrow and azimuth indicator | A small arrow pointing to true north in the picture; a dial with the aircraft symbol and a pointer and wedge for the ball's azimuth and field of view | computed |
| Sensor, field of view and zoom | DTV / NIR / IR WHT / IR BLK, field of view name and angle, EZ 2X / 4X | sensor state |
| UTC date and time | Today's date and a clock derived from the scene's time of day and the region's offset from UTC (Arizona UTC-7, Tokyo +9, Paris +2 in October, Rio -3) | game clock (**approximation**: the scene's sun sets the hour, not the phone's clock) |
| Laser status | LSR SAFE, LRF and the range, LTD ON while designating, CODE 1688 | laser state |
| Declutter | Full; level 1 (crosshair, gate, sensor and field of view, range, track); level 2 (crosshair and gate only) | operator |

## 5. Masking

The ball sits under the nose. Looking aft or up, the aircraft's own fuselage, wings, tail and (when down) the
landing gear block the view. The game draws the aircraft in the sensor view, so it blocks the picture where it
really would, and a ray test against the airframe flags MASK for the tracker: a point or area track breaks after
0.3 s masked (TRK LOST, MASK), a geo stare holds the coordinate and shows MASK until the line of sight clears. A
track also breaks when terrain hides the target, when the target leaves the field of view faster than the ball can
follow, past 20 km slant range (**approximation**), or when the target is destroyed.

## 6. What is not modelled

Image fusion as a separate mode, the illuminator's spot, focus and exposure controls, the tracker's feature mode as
a separate choice, real gimbal dynamics beyond the smoothing above, real laser codes and safety interlocks.
