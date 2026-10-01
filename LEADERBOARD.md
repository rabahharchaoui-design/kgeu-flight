# Pocket Flight Sim leaderboards

Global high scores for every task and game, a callsign per player, ranks, ghosts and a
daily challenge that is the same for everyone.

**Worker URL:** https://pfs-scores.rabahharchaoui.workers.dev
(Cloudflare Worker `pfs-scores`, D1 database `pfs-scores`, id `8309ccd1-9fea-4b56-818b-ef6717a352a5`,
account `5e3a0378ca904c898762cd431982c9e0`, workers.dev subdomain `rabahharchaoui`.)

The game has the URL in `index.html` (the `LB` module). The browser never touches the database:
every write goes through the Worker, which checks it, and every refusal lands in `flagged`.

## Files

| Path | What |
|---|---|
| `server/src/worker.js` | the Worker: routes, callsigns, tokens, submit checks, boards, ghosts, fame |
| `server/src/boards.js` | every board the server accepts, its limits, the aircraft speed limits, ranks and XP |
| `server/src/names.js` | callsign rules, reserved names, profanity and leetspeak check |
| `server/src/words.js` | the 256 words for recovery codes |
| `server/schema.sql` | the D1 tables |
| `server/test/api_test.mjs` | API test, local (`npm test` in `server/`) or live (`npm run test:live`) |
| `index.html`, section *leaderboards* | the `LB` module: boards, card, queue, ghosts, fame, paint |
| `version.json` | the build id the page checks on launch (keep equal to `APP_VER` in index.html) |
| `tests/scores_check.py` | end to end in the game against `wrangler dev` |
| `tests/lb_merge_check.py` | the one list board screen with a stubbed Worker: EASY/HARD chip per row fits at 568x320 to portrait |
| `tests/upgrade_check.py` | in place upgrade from the `prescores` build |
| `tests/scores_fps.py` | same-session frame rate A/B with a callsign, fame boards and a ghost |

Secrets on the Worker (set with `npx wrangler secret put NAME`, never in the repo): `PEPPER`
(hashes device keys and recovery codes; **changing it logs every device out**), `TOKEN_SECRET`
(signs run tokens), `OHRABAH_SECRET` (the reserved callsign; also in
`~/Developer/cc-test/chain/OHRABAH_SECRET.txt`, outside the repo, with the steps to claim it).

## Tables

- `players`: callsign (unique, upper case), key_hash (HMAC of the device key), rec_hash (HMAC of
  the recovery code), created, xp, creator (1 for OHRABAH), renamed (last change), banned.
- `scores`: board, player_id, callsign, mode (`easy`/`hard`), score, secs (run time), ac (aircraft),
  wx (time of day and wind, e.g. `night 40@8`), day (UTC yyyymmdd), created, token (unique).
- `ghosts`: score_id, board, mode, player_id, score, secs, ac, path (compressed), created.
  Top 10 per board and mode only, one per player.
- `flagged`: created, callsign, ip, board, reason, payload (the refused request, up to 2 KB).
- `tokens`: jti, player_id, board (`*` for an offline pool token), mode, t0, day, used.
- `hits`: rate limit log (kind, who, ts).

## Boards and score formulas

Each board is one ranked list for Easy and Hard together. A player's single best run on the
board, in either mode, counts once, and every row carries a small EASY (green) or HARD (red) chip
next to the score saying which mode that run was flown in. Rank and the pilot total (the board,
the "#n of m" end of run badge, personal best and top 10) are computed across both modes. Only the
display merges: runs are still submitted, token checked and stored per mode (`scores.mode`), a run
started in Easy is still refused as Hard, and ghosts are still kept per mode (Race the leader flies
the best ghost of either mode). A run counts as Easy if Easy was on at any moment of it (the
game's `runMode()`), including the first flight lesson's assists. Every board has Today (since
00:00 UTC), This week (since Monday 00:00 UTC) and All time.

| Board id | Name | Score | Better | Min run | Legal range | Ghost |
|---|---|---|---|---|---|---|
| `daily` | Daily challenge | arcade points | higher | 20 s | 0 to 1,500 | yes |
| `mission:short` | Short field landing (C-130) | points | higher | 10 s | 0 to 1,000 | |
| `mission:dash` | Luke to Glendale dash (F-16) | time, s | lower | 30 s | 30 to 3,600 | yes |
| `arc:landing` | Landing challenge, 5 mile | arcade points | higher | 20 s | 0 to 1,500 | yes |
| `arc:landing1` | Landing challenge, 1 mile | arcade points | higher | 10 s | 0 to 1,500 | yes |
| `arc:drop` | Airdrop accuracy (C-130) | metres | lower | 15 s | 0 to 3,000 | |
| `arc:strike` | Strike accuracy (MQ-9A) | points | higher | 15 s | 0 to 100 | |
| `lesson:first` | First flight | lesson score | higher | 20 s | 0 to 100 | |
| `lesson:steep` | Steep turns | lesson score | higher | 10 s | 0 to 100 | |
| `lesson:slow` | Slow flight | lesson score | higher | 25 s | 0 to 100 | |
| `lesson:stall` | Power off stall | lesson score | higher | 3 s | 0 to 100 | |
| `lesson:engine` | Engine failure | lesson score | higher | 15 s | 0 to 100 | |
| `lesson:pattern` | Pattern and touch and go | lesson score | higher | 45 s | 0 to 100 | |
| `free:landing` | Free flight landing | landing points | higher | 8 s | 0 to 100 | |

**Arcade points** (daily, 5 mile and 1 mile landing challenges), unchanged from the arcade:

    par    = round((start distance m + 2500) / (1.3 x approach speed m/s) + 25)   seconds
    points = round(1000 x min(1.5, par / your time) x G)
    G      = A 1.0, B 0.9, C 0.8, D 0.7 from the landing grade; F or the wrong runway scores nothing

The clock runs from the start in the air to the wheels touching the target runway. The server
also checks `points <= 1000 x min(1.5, parMax / time)` with parMax 480 s (5 mile and daily) and
180 s (1 mile), the slowest aircraft's par.

**Landing points** (free flight landings, and the grade inside arcade points), 0 to 100:

    sink      0-100 fpm 100, 150 88, 300 62, 500 30, 700+ 0
    centre    0-2 m off 100, 4 m 86, 8 m 58, 15 m 22, 25 m+ 0
    aim point 0-50 m 100, 150 m 80, 300 m 55, 600 m 20, 1000 m+ 0
    speed     0-3 kt off Vapp 100, 8 kt 76, 15 kt 46, 25 kt 12, 40 kt+ 0
    points  = round(0.35 sink + 0.20 centre + 0.25 aim + 0.20 speed)      (A 90+, B 80+, C 70+, D 60+)

A free flight landing is timed from the start of the flight (or the previous landing) and counts
only on a paved runway outside a mission, lesson, arcade game or strike.

**Short field landing** (new, it only had a letter before), 0 to 1,000:

    touchdown part  past the threshold: undershoot 0, 0-250 ft 400, 500 ft 300, 1000 ft 120, 1500 ft+ 0
    stop part       stopping distance: 0-1000 ft 600, 1500 ft 520, 2000 ft 380, 2600 ft 120, 3000 ft+ 0
    points = round(touchdown part + stop part)

**Luke to Glendale dash**: seconds from wheels up at Luke (15 m above the ground) to wheels down
at Glendale, lower is better. The score is the run time itself.

**Airdrop accuracy**: metres from the drop zone centre to where the bundle lands, lower is better.

**Strike accuracy**, 0 to 91 (the existing loiter and strike score):

    hits      20 per hit, 0 to 80
    accuracy  average miss 0-3 m 100, 8 m 80, 20 m 50, 45 m 20, 80 m+ 0
    on target seconds with the sensor locked on a live target: 0 0, 20 40, 45 75, 90+ 100
    points  = round(0.45 hits + 0.30 accuracy + 0.25 on target)

**Lessons**: the lesson's own 0 to 100 score (A 90+, B 80+, C 70+, D 60+). A failed lesson is not
submitted.

## The results card and its grades

Every run ends on one card (index.html, *the results card*): the letter grade, the score, the key
stats, the board line (rank, PERSONAL BEST or TOP 10 once the Worker answers; Sending, Saved,
Practice or Unranked otherwise), then CONTINUE and MAIN MENU. It slides in once the aircraft has
stopped, or 20 s into the rollout, or when the run ends in the air. Free flight landings and the
dash use a brief card that never pauses the game and goes on its own after 9 s; the grade badge
opens the same card as the details. Challenges, lessons, missions and the strike pause under it.

The letter on the card is meant to be fair in the same way on every board: A is a run a good pilot
is proud of, F is a run that did not count.

| Run | A | B | C | D | F |
|---|---|---|---|---|---|
| Landing (free flight, and the landing inside a challenge) | 90+ pts | 80+ | 70+ | 60+ | below, or off the paved runway |
| Landing challenges, daily | 1,000+ pts | 850+ | 700+ | 500+ | below, the wrong runway, or an F landing |
| Short field landing | touchdown in 500 ft and stopped in 1,500 ft | in 500 ft, stopped in 2,000 | stopped in 2,000 | stopped in 2,600 | longer |
| Airdrop | under 25 m | under 50 | under 100 | under 150 | outside the circle |
| Luke to Glendale dash | 2:30 or faster | 3:00 | 3:30 | 4:00 | slower |
| Strike range | 90+ pts | 80+ | 70+ | 60+ | below |
| Lessons | 90+ | 80+ | 70+ | 60+ | failed |

The challenge letter comes from the points, so a clean landing on par (1,000) is an A and a fast
run with a C landing (say 1.3 x par x 0.8 = 1,040) is one too; a D landing at par is a C. The
dash bands follow the 3 minute target on its card (the `dash` achievement).

Adding a board for a future mode is one line in the game and one in the server:

    LB.board('apt:KPHX', {name: 'Phoenix Sky Harbor landing', group: 'World airports'})    // index.html
    BOARDS['apt:KPHX'] = { dir: 1, min: 0, max: 100, minSecs: 20, ref: 100 };              // server/src/boards.js

then `LB.runStart('apt:KPHX')` when the run starts and `LB.runEnd('apt:KPHX', score)` when it ends.
Races add `ghost: 1` (and `go: () => ...` to start the run) on both sides. A whole family can
share limits with a prefix in `FAMILIES` in boards.js.

## Daily challenge

Seeded by the UTC date (`yyyymmdd`), so it is identical worldwide and turns over at 00:00 UTC
(17:00 in Arizona): the same aircraft, target runway, start point, distance and height, time of
day (day, sunset or night) and wind (direction and speed). Gusts stay random. It is the first
card on MISSIONS (and still on ARCADE) with a countdown to the next one.

One official attempt a day: the Worker hands out one daily token per player per UTC day; the
next request that day answers `practice`, the HUD says Practice and nothing is submitted. Offline,
the game remembers the day's attempt locally and uses a pool token; the server still refuses a
second daily score for that day. A run that is started counts as the attempt even if it is
abandoned.

## Ranks and XP

The server gives XP for every accepted run:

    XP = round((10 + 40 x q) x (1.25 in Hard, 1 in Easy)) + 15 for a personal best + 25 for the top 10
    q  = score / reference (100 for 0-100 boards, 1000 for arcade and short field),
         or for lower-is-better boards (worst - score) / (worst - best):
         airdrop best 0 m worst 150 m, dash best 120 s worst 300 s; clamped to 0..1

| Rank | XP |
|---|---|
| Nugget | 0 |
| Wingman | 300 |
| Flight Lead | 1,200 |
| Instructor Pilot | 3,500 |
| Weapons School | 8,000 |
| Top Gun | 16,000 |

The badge (a shield with chevrons, a star from Weapons School, star and chevron for Top Gun) shows
beside the callsign on every board row, on FLY, in Settings and on the leaderboard header.
OHRABAH also carries the gold CREATOR badge.

## Callsigns

3 to 12 letters and digits, upper case, checked live against the server while typing. The dice
mixes desert and aviation words (HABOOB, DUSTDEVIL, SIDEWINDER7, MESQUITE, SAGUARO, MONSOON...).
The server refuses profanity and slurs, read through leetspeak (0 O, 1 I or L, 3 E, 4 A, 5 S,
7 T, 8 B, 9 G, PH F, doubled letters squeezed, digits dropped), with an allow list for real words
(COCKPIT, HABOOB, TORPEDO...). OHRABAH (and its leetspeak forms) is reserved and needs the
secret; ADMIN, SYSTEM and similar are not available.

No email, no password: the device makes a random 48 hex digit key, keeps it in localStorage
(`kgeuLB`) and the server keeps only its HMAC. Signup shows a 4 word recovery code once (32 bits
from 256 words; restores are limited to 10 an hour per IP). Restore callsign on the card (or in
Settings) moves the callsign to the new device; the old device's key stops working and it is
told so on its next launch. A callsign can change once every 30 days in Settings; old scores follow
(they are joined by player id, and `scores.callsign` is rewritten too). OHRABAH cannot be renamed.

## Anti cheat

- A run token is requested when a run starts (board, mode, start time), HMAC signed, stored, and
  good once. No valid token, no score.
- Refused: a token for another player or board, a used or 48 h old token, a run started in Easy
  submitted as Hard, a run ending in the future or more than 24 h ago, a run shorter than the
  board's minimum (both the run's own clock and the wall time since its token), a score outside the
  board's range, a time trial whose score is not its time, arcade points too high for the time,
  an unknown aircraft.
- Races and time trials send their flight path. It must last the submitted time (within 3 s or
  8 percent) and never move faster than the aircraft can (ground speed limits in `AC_VMAX`:
  Cessna 130, Alpha 110, MQ-9A and B 180, C-130 240, F-16 580 m/s).
- More than 30 submissions an hour per device or per IP are refused.
- The daily challenge counts once per player per UTC day.
- Every refusal is written to `flagged` with the reason and the request.

Offline pool tokens (5 kept on the device, at most 12 a day per player) let a run flown with no
connection count when it is sent later; for those the server has only the run's own clock.

## Offline

Everything flies without a connection. Finished runs wait in `kgeuLBQ` and go out on the next
launch, on the `online` event or within a minute of the connection coming back; runs older than
24 hours are dropped. The end of run badge says SAVED. The leaderboard screen shows a clean Offline
state. Fame on the billboard and hangar comes from the last fetch (`kgeuFame`).

## Ghosts

Races and time trials record position and attitude at 5 Hz from the moment the clock starts.
Format: `{v:1, hz:5, o:[x,y,z], n, z, d}`: `o` is the first point in metres, `d` is base64 of n
little endian frames of 6 int16 (dx, dy, dz in 0.5 m steps, then yaw, pitch, roll as angle/pi x
32767), deflate-raw compressed when `z` is 1: a few KB for a 3 minute run. The server
keeps the top 10 per board and mode. Race the leader (on the board screen) flies a translucent
copy of the leader's aircraft (the best ghost of either mode) with their callsign over it.

## Fame in the world

Fetched once per launch and cached: today's daily #1 (Hard first) is lettered under the @OhRabah
billboard by State Farm Stadium, and the all time top 3 by XP are painted on the KGEU hangar next
to the @OhRabah hangar banner. The player's callsign is painted small on the F-16 canopy rail and
on the nose of every other aircraft.

## Updating the app

There is no service worker. On launch the page fetches `version.json` past every cache; if it
differs from `APP_VER` in index.html it reloads once (only on the Pages origin, only before a
flight starts). **When shipping a change, bump `APP_VER` and `version.json` together.**
localStorage keys are never renamed or cleared by an update.

## Commands

All from `server/` (`cd ~/Developer/cc-test/kgeu/server`). `--remote` is the live database.

```sh
# who is logged in
npx wrangler whoami

# deploy the Worker after a change, and apply schema changes
npx wrangler deploy
npx wrangler d1 execute pfs-scores --remote --file=schema.sql

# tests: local wrangler dev (fresh local D1), then the live Worker (cleans up after itself)
npm test
npm run test:live

# view scores: a board's top 20 as the game shows it (all time, best per player across both modes)
npx wrangler d1 execute pfs-scores --remote --command "SELECT p.callsign, MAX(s.score) best, s.mode, COUNT(*) runs FROM scores s JOIN players p ON p.id=s.player_id WHERE s.board='arc:landing' GROUP BY s.player_id ORDER BY best DESC LIMIT 20"
#   (for lower-is-better boards, arc:drop and mission:dash, use MIN(s.score) and ORDER BY best ASC)

# the latest 50 scores anywhere
npx wrangler d1 execute pfs-scores --remote --command "SELECT created, board, mode, callsign, score, secs, ac, wx FROM scores ORDER BY id DESC LIMIT 50"

# one player's runs
npx wrangler d1 execute pfs-scores --remote --command "SELECT board, mode, score, secs, ac, datetime(created/1000,'unixepoch') at FROM scores WHERE callsign='HABOOB' ORDER BY id DESC"

# refused submissions
npx wrangler d1 execute pfs-scores --remote --command "SELECT datetime(created/1000,'unixepoch') at, callsign, ip, board, reason FROM flagged ORDER BY id DESC LIMIT 50"

# delete a cheater: ban (hidden from boards and fame, their key stops working) and remove their runs
npx wrangler d1 execute pfs-scores --remote --command "UPDATE players SET banned=1, xp=0 WHERE callsign='CHEATER'; DELETE FROM ghosts WHERE player_id=(SELECT id FROM players WHERE callsign='CHEATER'); DELETE FROM scores WHERE player_id=(SELECT id FROM players WHERE callsign='CHEATER')"
#   to remove them completely (and free the callsign) also run:
npx wrangler d1 execute pfs-scores --remote --command "DELETE FROM tokens WHERE player_id=(SELECT id FROM players WHERE callsign='CHEATER'); DELETE FROM players WHERE callsign='CHEATER'"
#   unban:
npx wrangler d1 execute pfs-scores --remote --command "UPDATE players SET banned=0 WHERE callsign='CHEATER'"

# delete one bad score (its id from the queries above)
npx wrangler d1 execute pfs-scores --remote --command "DELETE FROM ghosts WHERE score_id=123; DELETE FROM scores WHERE id=123"

# reset a board (both modes; add AND mode='hard' for one). XP already earned stays.
npx wrangler d1 execute pfs-scores --remote --command "DELETE FROM ghosts WHERE board='arc:landing'; DELETE FROM scores WHERE board='arc:landing'"

# reset today's daily challenge
npx wrangler d1 execute pfs-scores --remote --command "DELETE FROM ghosts WHERE board='daily' AND score_id IN (SELECT id FROM scores WHERE board='daily' AND day=CAST(strftime('%Y%m%d','now') AS INTEGER)); DELETE FROM scores WHERE board='daily' AND day=CAST(strftime('%Y%m%d','now') AS INTEGER); DELETE FROM tokens WHERE board='daily' AND day=CAST(strftime('%Y%m%d','now') AS INTEGER)"

# players by XP
npx wrangler d1 execute pfs-scores --remote --command "SELECT callsign, xp, creator, banned, datetime(created/1000,'unixepoch') joined FROM players ORDER BY xp DESC LIMIT 50"

# housekeeping: old rate limit rows and spent tokens
npx wrangler d1 execute pfs-scores --remote --command "DELETE FROM hits WHERE ts < (strftime('%s','now')-86400)*1000; DELETE FROM tokens WHERE t0 < (strftime('%s','now')-3*86400)*1000"

# rotate the OHRABAH secret (then update ~/Developer/cc-test/chain/OHRABAH_SECRET.txt)
npx wrangler secret put OHRABAH_SECRET

# live logs
npx wrangler tail pfs-scores
```

The HTTP API, for reference: `GET /health`, `GET /name?cs=`, `GET /board?b=&p=today|week|all&cs=`
(answers `{board, mode:'all', period, dir, total, rows:[{r, cs, score, secs, ac, mode, xp, rank, creator, when}],
me:{r, cs, score, mode, ...}, ghost, now, day}`: one row per player, their best across Easy and Hard, `mode` is
`easy` or `hard`; `total` counts each player once; an `m` parameter is ignored),
`GET /ghost?b=` (the best ghost of either mode; `m` ignored), `GET /fame`, `GET /ranks`, `POST /signup {cs,key[,secret]}`,
`POST /restore {cs,key,code}`, `POST /me {cs,key}`, `POST /rename {cs,key,to}`,
`POST /token {cs,key,board,mode}`, `POST /pool {cs,key,n}`,
`POST /submit {cs,key,token,board,mode,score,secs,ac,wx,when[,path]}`. CORS and POSTs are
limited to `https://rabahharchaoui-design.github.io` and `http://localhost:8765`.
