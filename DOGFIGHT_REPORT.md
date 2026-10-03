# DOGFIGHT_REPORT.md: Session 5, Red Flag Dogfight

Branch `dogfight`, rollback tag `pre-dogfight`. Build id `2026-10-03-dogfight` (`APP_VER` and `version.json`).
The "Red Flag Dogfight, coming soon" arcade card is now the real game.

## What shipped

**The fight (5.1).** ARCADE, Red Flag Dogfight: your F-16 over the Barry M. Goldwater Range against aggressor
F-16s in blue gray splinter camo. A run is four waves of 1, 2, 3 and 4 bandits (10 in all); every wave is a
round with its own 90 second clock. Clear the wave and the seconds left are banked. The run ends on a win
(all four waves), a clock running out, three hits (you eject), a crash, or 10 seconds outside the 12 nm range
(20 in Easy). Arizona only: from another region the card switches there first.

**Offense (5.2).** A green box on every bandit with its range, edge arrows for the ones off screen. Fox 2: hold
a bandit in the seeker circle, low growl while it searches, high steady tone and a glowing FOX 2 button on lock;
the missile flies for real (smoke trail, up to 12 s) and can be beaten by a hard break or flares. Gun: hold GUN,
tracers, a lead computing pipper, a heavy burst sound, inside about 800 m only. A kill is an explosion, smoke and
a falling jet, a "Splash one" call, and a slow motion kill cam on the last kill of each wave.

**Defense (5.3).** Radar warning: a soft ping while a bandit searches for you, fast beeps and amber pulsing
edges on lock, a continuous tone, red edges, "Missile launch" and a red arrow with clock position and distance
when a missile is in the air. FLARES (30): timed in the last 2.5 seconds they usually pull the missile away;
a hard break in the last 2 seconds can beat it too. Three hits and you eject. Hard deck 5,000 ft with
"Pull up"; busting it counts as one hit.

**Voices (5.4).** 62 clips from the macOS say pipeline (451 KB): the cockpit warning voice is Samantha
(Enhanced), calm and dry; the wingman "Viper 2" is Nathan (Enhanced) and the AWACS controller "Sentry" is
Noelle (Enhanced), both through the radio filter. Sentry gives real picture calls built from parts ("Sentry, two
bandits, west, five miles, angels fifteen"). A briefing card before every run says "Sound on for the full
experience"; the first tap sets `navigator.audioSession.type = "playback"` so sound plays with the silent
switch on, and on an iPhone without that API the card adds "Turn off silent mode". Tower chatter is silent
during the fight.

**Controls, modes, scoring (5.5).** Stick and throttle unchanged. FOX 2 (84 pt), GUN (72 pt, hold) and FLARES
(64 pt) sit in the lower right, left of the throttle; AUTO LAND, GEAR and BRAKE hide during the fight.

| | Easy | Hard |
|---|---|---|
| Seeker circle / lock time | 11 degrees / 0.8 s | 6 degrees / 1.5 s |
| Missiles | 10 | 6 |
| Bandits | 0.8 speed, 0.75 g, 5 s to lock you, one missile in the air | full speed, 3 s to lock, two missiles in the air |
| Flares | 85 percent when timed, 2 auto flares per wave | 65 percent when timed, none automatic |
| Flying | 80 degree bank and about 5.5 g in the fight (60 elsewhere) | speed bleeds in turns, 9 G limit, grey vision above 7.5 g |
| Subtitles | plain English | brevity only |

Score: 100 a kill, 200 a gun kill, 2 per banked second, 250 for the win, minus 75 per hit. Stars at 300, 900
and 1,500. Achievements: Ace (5 kills in a run), Guns Kill, Flare Save, Untouchable (win with no hits).
Surprise touches: the wingman calls "Tally one!" at the first sighting, a bandit that hits you does a victory
roll, and a close gun kill always gets "Good kill!".

## The extra instructions

1. **Music.** The dogfight always plays `assets/music/dogfight.m4a` on loop (`MUSIC.forced`); Prev and Next do
   nothing during the fight, and the normal playlist returns after it.
2. **Map.** Red Flag Dogfight is a round badge icon (two crossing jets, the MAP_REPORT.md icon style) over a
   "Barry M. Goldwater Range" label, with a legend row; tapping it sets a waypoint.
3. **Leaderboards.** Eight boards registered with the `LB.board` hook and in `server/src/boards.js`, Easy and
   Hard separate: `df:score`, `df:kills`, `df:clear` (fastest time to clear all bandits, wins only) and
   `df:guns` (guns only kills), each `:easy` and `:hard`. Every run asks for one run token at FIGHT'S ON and
   sends one submission; the Worker checks it and writes the kills, clear and guns rows itself. Anti cheat
   caps: score 0 to 3,000 and never above what the kills, gun kills, banked seconds, win and hits allow; at
   most 10 kills, gun kills not above kills, at most one kill per 4 s, a win needs 10 kills, 4 waves and 45 s;
   F-16 only; achievements must fit the stats. Achievements give rank XP once per player: Ace 150, Guns Kill
   75, Flare Save 50, Untouchable 200 (new `achs` table). The Daily Challenge is a dogfight every fifth UTC
   day (next: 2026-10-07, 10-12, 10-17), the same seeded fight worldwide, scored as half the dogfight score
   on the `daily` board. The Worker is deployed and the `achs` table is on the live database.
4. **Upgrade in place.** No change to the app name, icons, `manifest.json` or `start_url`. No localStorage key
   was renamed or cleared; new keys only (`arc:dogfight:hard`, `arc:dogfight:easy`).

## Decisions made without asking

- **Where the range is.** The real range lies beyond the built Arizona map, so the arena centre is the
  southwest corner of the drawn world: 16.9 nm from Luke on a bearing of 220.
- **"Rounds of 90 seconds with waves of 1 to 4."** Read as four waves, each with its own 90 second clock,
  which gives the "clear all bandits" board a finish line (10 bandits).
- **Hard deck.** Busting it costs one of the three hits in both modes (not an instant loss), with 6 s to climb.
- **Hard break.** Pure guidance never let the player out turn the missile, so there is a rule: needing more
  than the missile's g limit for 0.25 s in the last 2 s makes it overshoot (5.5 g in Hard, 4 g in Easy).
- **Easy bank limit.** Easy normally stops at 60 degrees of bank, which made a 180 take 40 s or more. In the
  fight only it is 80 degrees (a 180 takes about 17 s). Free flight Easy is unchanged.
- **Clouds** are hidden during the fight: seen from above at 15,000 ft they looked like flat white patches.
- **Kill rate caps** were loosened from one kill per 8 s to one per 4 s so a fast honest run is never refused.
- **Daily dogfight days** are a fixed rule (UTC day number mod 5 is 3) so no other day's draw changed.
- The end of run rank badge says "Dogfight (Hard)" to stay short.

## Tests

New: `dogfight_check`, `dogfight_weapons_check`, `dogfight_defense_check`, `dogfight_voice_check`,
`dogfight_modes_check` (with a seeded bot that plays both modes), `dogfight_lb_check`, `lb_boards_check`, all in
`tests/run_all.sh`; `tests/dogfight_shots.py` (screenshots in `overnight-screenshots/dogfight/`) and
`tests/dogfight_fps.py`. The server test `server/test/api_test.mjs` has the dogfight cases.

Full pass (the `run_all.sh` list, run in foreground batches): everything passes except three things that fail
the same way on `pre-dogfight`:

- `orbit_test`: the F-16 clockwise orbit case (known).
- `music_check`: the crossfade timing step (known flake).
- `scores_check`: the leetspeak profanity step times out (fails identically on the `pre-dogfight` worktree).

`splash_check` failed once when run in parallel with four others and passes alone. `npm test` in `server/`
passes. `npm run test:live` fails 10 `lesson:stall` checks because that live board now has real players on it
(the test expects an empty board); it left nothing behind.

Bot results (seeded): Easy reaches wave 4 with 9 kills and no hits; Hard gets 2 to 4 kills and is not shot
down in the first minute. Easy may be on the easy side.

**Frame rate.** Same session A/B against a `pre-dogfight` worktree (`aircraft_fps.py`, two rounds, order
swapped): frame time ratios 0.96 to 1.03 outside the dogfight, apart from first scenario warm up noise.
Inside the dogfight (`dogfight_fps.py`, same build, same spot): free flight with clouds 314 ms per frame, one
bandit 212 ms, four close bandits 228 ms, worst case (four bandits, gun firing, two missiles with smoke,
flares, launch warning) 311 ms. Four close bandits add about 11,300 triangles (2 percent). Headless software
rendering only shows ratios; the phone is the real test, see below.

## iPhone hand test

Sound
1. Flip the silent switch ON, open ARCADE, Red Flag Dogfight, tap FIGHT'S ON. You should still hear the
   music, tones and voices. If not, the card should have said "Turn off silent mode".
2. The dogfight song plays from the start and loops; pause and resume keeps it; Prev and Next do nothing;
   after MAIN MENU the normal playlist is back.
3. Voices: Sentry (radio) gives the picture call at each wave, Viper 2 (radio) calls Fox two, Splash, Tally,
   and the calm female cockpit voice says Missile launch, Pull up, Bingo. No tower chatter. Voices never talk
   over each other, and the cockpit voice cuts in first.
4. Gun: a heavy buzz while GUN is held, stopping the moment you let go.

Lock tone feel
5. Put a bandit in the circle: low growl, then a high steady tone after about 1.5 s (Hard) or under a second
   (Easy), box amber then red, FOX 2 ring pulsing. Is the growl too quiet or too annoying? Does the lock tone
   drop cleanly when he leaves the circle?
6. Radar warning: soft ping, then fast beeps with amber edges, then the continuous tone with red edges. Can
   you tell the three apart without looking? Are the red edges too strong on the phone?

Weapon button reach
7. With your right thumb resting on the throttle, reach FOX 2, GUN and FLARES without shifting your grip.
   Hold GUN while steering with the left thumb and tap FOX 2 with another finger.
8. No accidental throttle changes when stabbing FLARES in a hurry, and no accidental VIEW taps.

Difficulty
9. Easy: can a first time player win a wave or two? Do the auto flares and plain English prompts help? Is it
   too easy (the test bot clears most of it)?
10. Hard: do turns bleed speed, does the grey vision come in near 9 g and clear when you ease off, do bandits
    get on your six and shoot? Is a win possible but hard?
11. Beat one missile with flares (tap about a second and a half before impact) and one with a hard break.
12. Dive under 5,000 ft: "Pull up", then a hit against you. Take three hits: "Eject" and the results card.

Everything else
13. Kill cam on the last kill of a wave: smooth, and control comes back cleanly.
14. Frame rate with four bandits, missiles, smoke and flares on screen at once: any stutter?
15. Results card: score, stars, rank line, "+150 XP ACE" the first time. Boards, Red Flag Dogfight: eight
    boards, Easy and Hard separate.
16. The map: the Red Flag Dogfight icon southwest of Luke over "Barry M. Goldwater Range".
17. Existing install: open the home screen app; it should reload once to the new build with your callsign,
    records and settings intact.
18. On 2026-10-07 (UTC) the Daily Challenge should be the dogfight.
