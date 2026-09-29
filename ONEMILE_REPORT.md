# 1 mile final report

**Branch:** `onemile`, merged to `master`.
**Rollback:** `git reset --hard pre1mile`. The tag is pushed.
**Screenshots:** `overnight-screenshots/onemile/` (gitignored):
- the fly screen at 844 px wide and the pause sheet at 667 px wide, both with the new chip
- an Easy C-130 on 1 mile final, and landed
- a Hard F-16 at Luke
- the arcade screen and a 1 mile challenge result

## What changed
- **1 mi final start.** A new chip sits between Ramp and 3 mi final, on the fly screen and in the pause sheet's Change flight panel. It works for every aircraft at Glendale and Luke.
  - The aircraft starts 1 nm out on the runway centre line, on the 3 degree path (about 318 ft above the field), at exactly that aircraft's approach speed, indicated.
  - Easy starts gear down with landing flaps.
  - Hard is set up the way the 3 mile final is: gear down, approach flaps. I first tried gear up for Hard, but the C-130 and MQ-9s then balloon away, and that isn't a usable start.
  - It flies as a normal final: the tower clears you to land and you get a landing grade. Restart and Again bring you back to 1 mile, and the choice is saved.
- **1 mile landing challenge.** A new arcade card sits beside the 5 mile landing challenge. You start lined up 1 nm out on runway 1, on the path, at approach speed, and race the clock. It has its own best score, `arc:landing1`, on the card and in Records.
  - To keep the arcade on one iPhone SE screen, the featured Red Flag card now takes one grid cell. The six cards sit three rows by two.
- **refs photos.** `refs/cessna172`, `refs/pipistrel`, `refs/mq9a` and `refs/mq9b` are in `.gitignore`. `refs/` already was, and no refs file has ever been committed.

## Tests
- **`tests/onemile_check.py`** covers:
  - the chips at 844 and 667 px: four 44 px targets, the screen still fits, the choice is saved, the summary text, and the choice survives a reload
  - GO, the pause sheet and Restart
  - all 6 aircraft × 2 bases × Easy and Hard: within 60 m of 1 nm out, 280 to 350 ft, on the centre line and heading, within 10 kt of approach speed, and the right gear and flaps
  - 10 s hands off, in the same still air as a 3 mile start of the same aircraft: glide path deviation and distance off the centre line no worse than from 3 miles
  - the arcade card sits beside the 5 mile one, the start geometry, and a finished 1 mile run scoring under its own best
- **Full pass:** everything passes apart from the known F-16 clockwise orbit case. `arcade_check` and `menu_check` were updated for the sixth card and the fourth start chip.
- **Frame rate:** flat against a `pre1mile` worktree.

## Found, not changed here
- **Hard C-130 on final.** The Hard C-130 rises about 400 ft in the first 10 s hands off, from 3 miles and from 1 mile alike, so its final trim (finalPitch, finalThr, finalTrim) is too nose high. It needs a retune in a later session.
- **Easy landing hands off.** Easy does not land every aircraft by itself: from 3 miles the Reaper and C-130 touch down short, and from 1 mile the F-16 and C-130 run off the end. That was already true before this branch.

## Hand test on the iPhone
1. Pick 1 mi final on the fly screen, press GO, and fly each aircraft down at Glendale and at Luke, in Easy and in Hard.
2. Pause, then Restart. You should be back on 1 mile final.
3. Arcade: play the 1 mile landing challenge. Its best score should be separate from the 5 mile one.
