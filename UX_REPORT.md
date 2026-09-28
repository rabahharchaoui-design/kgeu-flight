# Pocket Flight Sim: UX session report

The game is now **Pocket Flight Sim** (formerly KGEU Flight, briefly Haboob). This
session was built for iPhone players who are gamers, not pilots. It was done on
branch `ux` from tag `pre-ux`, one feature per commit, with a Playwright check at
iPhone landscape after each. Aircraft models, lighting and flight physics were not
touched. The `// PHYSICS-START` .. `// PHYSICS-END` block is byte for byte unchanged.

Live: https://rabahharchaoui-design.github.io/kgeu-flight/ (the repo and URL keep
the old name; renaming the GitHub repo would change the link).

## What changed, by commit

| # | Commit | What it does |
|---|---|---|
| 1 | Menu choices no longer reset each other | Every chip was wired to `pickType`, so Day, Sunset, Night or a base fell back to the Reaper and picking an aircraft forced its home base. Aircraft, base, time of day and start position are now independent and saved. Missions borrow an aircraft without overwriting your pick. |
| 2 | Landing grade no longer stops the flight | Rollout, braking, taxi and touch and goes carry on. The grade is a small badge top right ("B  Firm, left of centerline") for about 4 s. Tap it for the full card, and only then does the game pause. NEW RECORD works the same way. The last 10 breakdowns go to Records. |
| 3 | Touch controls, tilt removed | No tilt, motion prompt or calibration anywhere. Left thumb: a floating stick with ring and knob that springs back. Right edge: a throttle slider with BRAKE above it. Top right: Auto, gear, flaps, camera. Pause top centre. The lower right stays empty except for weapon and mission buttons. Stick sensitivity and invert pitch are in Settings. The layout check finds 0 overlaps at 667x375 (51 before), and also at 844x390 and 932x430. |
| 11 | Rebrand | New name, manifest, home screen name, icons (180, 192, 512, 1024, favicon) from `refs/haboob-icon.png`, share card, and the icon's palette. |
| 6 | Main menu rebuilt | Home, FLY flow, Missions, Settings, Controls help (the keyboard chart is hidden on touch). 44 px targets, safe areas, no scrolling. |
| — | Rename to Pocket Flight Sim | Title, manifest name, menu, splash and watermark use "Pocket Flight Sim"; short_name and home screen name are "Pocket Sim". Same icon, colours and file names. |
| 4 | Funnel and skill level | First launch asks New to flying or I'm a pilot. That choice replaces Easy flight. Rookie: plain labels (Speed, Height, Climbing, Direction), auto level, stall protection, auto throttle on takeoff, glowing hoops to the runway, auto gear and flaps, plain English radio subtitles. Pilot: KIAS, ALT, VS, HDG, no assists, full ATC, six pack. |
| 6b | Menu revisions | One FLY screen (carousel, chips, GO). A looping carousel. Compact Missions and Arcade cards with icons, stars and best score. A Change flight panel in the pause menu with Apply. |
| 5 + 6c | Flight school, lesson 1 | Home: big FLY plus FLIGHT SCHOOL, MISSIONS, ARCADE. Lesson 1 is the one minute first flight with arrows and a big Skip, launched automatically for rookies. Start here badge. Next lesson on every result. Replay from Settings. |
| 7 | New map | Heading-up mini map. Tap it for a full north-up map with every airport and landmark; pinch, drag, and tap a runway end to set a destination. Distance, bearing and time on the HUD, a big arrow for rookies, glowing hoops near the runway. |
| 8 | Arcade hub | Featured Red Flag Dogfight (coming soon), landing challenge against the clock, daily challenge, airdrop and strike range, each with stars and best score. |
| 9 | Photo mode | Camera in the pause menu. It freezes the frame, hides the HUD, and orbits and zooms by finger. SAVE shares a watermarked PNG through the iOS share sheet. |
| 10 | Splash | Icon on sand, title, thin loading bar, fade into home. |
| 12 | Creator credit | "Made by @OhRabah" with the YouTube play button on the splash and at the bottom of Settings; opens the channel in a new tab. |

## Test results

Full pass (`zsh tests/run_all.sh`), then the frame rate gate, all on this Mac in
headless Chromium at iPhone landscape sizes (667x375, 844x390, 932x430).

| Check | Result |
|---|---|
| Every aircraft spawns (Cessna, F-16, MQ-9A, MQ-9B, C-130; Alpha in the carousel and school) | pass |
| Menu choices never reset each other, and survive a reload (`prefs_check`) | pass |
| A full landing keeps rolling after touchdown, no pause; the badge fades; touch and go (`landing_check`) | pass |
| Thumb stick and throttle fly the aircraft, no motion permission or listeners anywhere (`touch_check`) | pass |
| Zero control overlaps at 667x375, 844x390, 932x430, including stick down, flap picker, badge, destination, strike and airdrop (`ui_check`) | pass (51 overlaps before) |
| Every menu screen fits with no scrolling and 44 px targets; FLY then GO is two taps; the carousel loops; Change flight in pause (`menu_check`) | pass |
| Funnel and Rookie/Pilot (`skill_check`); Flight school, lesson 1 flown end to end with the real stick and throttle (`school_check`) | pass |
| Map opens, pinch, drag, sets a destination, HUD readout, guide path, clears (`map_check`) | pass |
| Arcade, photo mode, splash, credit (`arcade_check`, `photo_check`, `splash_check`, `credit_check`) | pass |
| Older suites: physics `test`, `t3` (0 / 36 fails), `t6`, `dubins_test`; base, desktop, score, six pack, strike, mission, radio, Add to Home Screen | pass |
| `orbit_test` | 1 fail: "f16 cw holds the radius". This failed before this session too (it's in the pre-overnight notes), and the physics is byte for byte unchanged |
| No console errors | pass, in every check above |
| No fps regression | pass. Measured back to back on this machine: pre-ux 3.2 / 3.1 / 3.1 / 3.4 / 3.1 fps, ux 3.1 / 3.2 / 3.2 / 3.2 / 3.1 (Cessna, F-16, MQ-9A, MQ-9B, C-130), 96 to 104 percent, within the 1/8 fps resolution of the sample. Headless Chromium renders in software, so only the ratio means anything; real iPhone frame rate is still unmeasured |
| Live site after push (`live_check`) | pass: all 47 checks on the deployed https site. The title and manifest read Pocket Flight Sim, the home screen name is Pocket Sim, icons resolve, FLY then GO starts a flight, auto takeoff runs, every aircraft spawns, all 111 radio clips decode, no errors |

Along the way, the older tests were updated for the new UI: they start past
the first launch screen, find controls where they now live, and expect the base
to stay put when the aircraft changes (bug 1). `tilt_check.py` was deleted
along with tilt. `tests/overnight_fps.json` holds the fresh same-machine
baseline.

## Hand test list for your iPhone

Do these in Safari first, then again from the Home Screen icon (the installed app
uses the manifest and the new icon).

**First launch**
1. Delete the old home screen icon, clear Safari website data for the site (Settings, Safari, Advanced, Website Data), then open the link. You should see the sand splash with the icon, the title, a thin loading bar and "Made by @OhRabah" at the bottom. It fades into "How do you want to fly?"
2. Tap **New to flying**. Lesson 1 should start at once: Cessna, Glendale runway 1, an arrow pointing at the throttle.
3. Follow it: slide the throttle to FULL, pull the stick toward you, let go, make one right turn, let go, fly through the glowing hoops, hands off, hold BRAKE. You should get a result card with a big **Next lesson: Steep turns**. Note roughly how long it took (target: about a minute).
4. Add to Home Screen from the Share sheet. Check that the icon is the new one and the name reads **Pocket Sim**.

**Controls (the most important part)**
5. From home: **FLY**, then **GO**. It should be two taps.
6. Put your left thumb anywhere on the left third. The stick should appear under your thumb, move smoothly, and spring back when you let go. Nothing but controls should sit under either thumb.
7. Slide the throttle on the right edge up and down, and tap IDLE, CLIMB and FULL. Hold BRAKE while taxiing.
8. **Pitch direction:** pulling the stick down (toward you) should raise the nose. If it feels backwards, check that Settings, Pitch: Invert pitch is Off. Try the Stick sensitivity slider at Low and High.
9. Top right: gear (not shown on fixed-gear planes), flaps (tap for the notch picker) and camera. Pause is top centre.
10. Confirm no motion or orientation permission prompt appears anywhere.

**Landing**
11. Fly any aircraft onto a runway. The flight should keep rolling, with a small grade badge top right that fades after about 4 seconds. Tap one before it fades: the full card opens and the game pauses. **Keep flying** resumes.
12. Do a touch and go: after touchdown, full throttle, fly away.

**Menu choices**
13. On the FLY screen, pick an aircraft, then change Base, Time and Start in every combination. The aircraft must never change. Close and reopen the app: all four picks should be remembered.
14. Swipe the carousel right past the last aircraft; it should wrap to the first. Do the same with the arrows. The models should turn slowly.
15. Pause in flight. Use the **Change flight** panel to pick another aircraft, time and start, then tap **Apply**. The flight should restart immediately, and the main menu should show the same choices.

**Map**
16. Tap the mini map (top left, heading up). The full map should open over the paused game. Pinch to zoom, drag to pan. Glendale, Luke, Sky Harbor, the White Tanks, State Farm Stadium and Camelback should all be there.
17. Tap a runway end, for example Luke 21R, then close. The HUD should show distance, bearing and time; as a Rookie you should see a big arrow. Near the runway, glowing hoops should appear. Tap the readout to clear it.

**Skill levels**
18. Settings, Skill: switch to Pilot. The readouts should say KIAS, ALT, VS, HDG, and the radio should show no plain-English line. In the Cessna, the cockpit camera should show the six pack. Switch back to Rookie: you should see "Tower says: …" subtitles and plain labels.

**Arcade, missions, photo**
19. Arcade: play the landing challenge (starts 5 miles out, clock at top). The results screen should show stars and points, and the card should then show your best. Try the daily challenge.
20. Missions: short field landing and the Luke to Glendale dash each start directly.
21. Pause, **Photo**: drag to orbit, pinch to zoom, tap **SAVE**. The iOS share sheet should open. Save to Photos and check the small "Pocket Flight Sim" watermark in the corner.
22. Settings: tap "Made by @OhRabah". The channel should open in a new tab.

**Layout**
23. On the notch side and the home indicator side, nothing should be clipped in either landscape direction. No menu screen should scroll.

## Known limits and notes

- **Pitch direction is the one thing to feel on a real phone.** Pulling the stick toward you raises the nose, the same as the old stick. If it feels wrong, Settings has Invert pitch.
- **The share sheet can only be confirmed on the iPhone.** Photo SAVE calls the Web Share API synchronously inside the tap, which Safari requires. The test stubs `navigator.share`. On a browser without it, the PNG downloads instead.
- **Lesson 1 took about 70 simulated seconds** in the test, which flies it with coarse inputs. A real player may be a little quicker or slower than the one minute target.
- **Trim** is no longer on a touch button (the old More drawer is gone). Rookie doesn't need it, and on a Mac Y and H still work.
- **The old first flight coach** (the prompts that pointed at Auto T/O) is gone. Lesson 1 replaces it, as one learning path.
- **Records reset** still takes two taps and erases the new landing history and arcade bests too.
- **Red Flag Dogfight** is a placeholder card that only says it is coming soon.
- **Sky Harbor** is on the map and can be a destination, but the landing grade and the arcade only score Glendale, Luke and the assault strip. That is unchanged grading code.
- **Fourth time of day**: the Time row has an empty slot ready for the next session to fill.
- The repo and URL still say `kgeu-flight`. Renaming the GitHub repo would change the link you've shared, so I left it.
- To run everything: `zsh tests/run_all.sh`, then `.venv/bin/python tests/overnight_check.py ux`.
