# Music session report

## What shipped

22 tracks in the shuffled playlist (4 "Pocket Sim Original" AI tracks plus 18 curated
punk/rock tracks from `~/Downloads/pfs-music`), plus a 23rd track (`dogfight.m4a`) reserved
for the Red Flag Dogfight arcade mode's forced loop and left out of the shuffle.

Every track: silence-trimmed, the two over 3:30 cut to their strongest ~3:00 stretch by a
windowed RMS energy scan with edges snapped to a local energy minimum (a clean phrase break),
loudness-matched to -16 LUFS / -1.5 dBTP true peak (ffmpeg `loudnorm`, two-pass), and encoded
to 96kbps AAC in `assets/music/`. No source WAV/MP3 file and nothing from `pfs-music` was
committed — only the final `.m4a` files.

### Track list and final lengths

| File | Title | Length |
|---|---|---|
| main.m4a | Pocket Sim Original — Main Theme | 2:28 |
| school.m4a | Pocket Sim Original — Flight School | 2:30 |
| cruise.m4a | Pocket Sim Original — Cruise | 2:32 |
| dark.m4a | Pocket Sim Original — Dark Skies | 2:28 |
| afi-phoenix.m4a | AFI - The Day Of The Phoenix | 3:28 |
| afi-totalimmortal.m4a | AFI - Totalimmortal | 2:56 |
| badreligion-21st.m4a | Bad Religion - 21st Century Digital Boy | 2:48 |
| badreligion-punkrock.m4a | Bad Religion - Punk Rock Song | 2:27 |
| beastieboys-sabotage.m4a | Beastie Boys - Sabotage | 3:08 |
| descendents-suburbanhome.m4a | Descendents - Suburban Home | 1:40 |
| metallica-battery.m4a | Metallica - Battery | 3:00 (cut from 5:13, strongest stretch) |
| metallica-one.m4a | Metallica - One | 3:03 (cut from 7:10, strongest stretch) |
| millencolin-nocigar.m4a | Millencolin - No Cigar | 2:43 |
| nofx-linoleum.m4a | NOFX - Linoleum | 2:06 |
| offspring-jenniferlostthewar.m4a | The Offspring - Jennifer Lost The War | 2:35 |
| offspring-session.m4a | The Offspring - Session | 2:31 |
| pennywise-fighttillyoudie.m4a | Pennywise - Fight Till You Die | 2:26 |
| pennywise-society.m4a | Pennywise - Society | 3:24 |
| pennywise-timemarcheson.m4a | Pennywise - Time Marches On | 2:56 |
| rancid-journey.m4a | Rancid - Journey To The End Of The East Bay | 3:11 |
| suicidaltendencies-warinsidemyhead.m4a | Suicidal Tendencies - War Inside My Head | 3:26 |
| teenagebottlerocket-skateordie.m4a | Teenage Bottlerocket - Skate Or Die | 1:58 |
| dogfight.m4a (not in playlist.json; dogfight mode loop only) | Pocket Sim Original — Dogfight | 1:57 |

**Skipped from pfs-music: none.** All 18 files decoded cleanly and were all well over 60s.

## Judgment calls (things the brief left open)

- **"Label the 4 originals 'Pocket Sim Original'"** — since 4 tracks can't all share one
  identical display title without being indistinguishable in the toast/pause bar/credits,
  each got `"Pocket Sim Original — <cue name>"` (Main Theme / Flight School / Cruise / Dark
  Skies), so the label is present but the tracks stay identifiable.
- **Intro/outro trimming** — done by silence detection (ffmpeg `silencedetect`, -35dB/0.3s),
  not spoken-word/dialogue detection. All 18 pfs-music files are static-image "Lyrics" videos,
  not video skits with dialogue, so silence trimming was the safe fit; nothing needed the
  heavier spoken-word case.
- **dogfight.m4a's loop** — the raw AI track has a musical fade-out ending in near silence, so
  a plain trim would have left an audible level jump at the loop point (checked: -20dB → -64dB
  across the seam). Fixed with a 2s head/tail equal-power crossfade before normalizing, so the
  loop point now sits within ~1dB start to end. This track keeps no start/end fades otherwise,
  since fades would undo the crossfade smoothing.
- **Pause sheet layout** — the brief asks for "title with Previous, Play/Pause, and Next," which
  doesn't mention a volume slider. The pause sheet's music row is now that literal mini player
  (title + Prev + Play/Pause + Next); the volume slider stayed in Settings only, where it
  already lived. Play/Pause reuses the existing persistent Music On/Off preference (same fade
  behavior as before), rather than adding a second, non-persistent playback flag.
- **Settings > Music credits** — a full-screen list (mirrors the existing Controls Help screen)
  rather than an inline block in Settings, so a 23-item list doesn't force Settings to scroll or
  break the existing 667×375 fit/tap-target tests.
- **Prefetch/cache tuning** — the next track's download now only starts once ≤20s remain on the
  current one (previously it began immediately on track start); the decode cache now holds the
  10 most recently played tracks (previously only ever ~2). Both match the brief's items 9.

## Tests

- `tests/music_check.py` extended for the populated `playlist.json`, titles, `musicPrev()`,
  the pause mini player, and the new Settings credits screen — passes standalone and inside
  `tests/run_all.sh`.
- Full `tests/run_all.sh`: all checks pass except two **pre-existing** flakes, confirmed to
  reproduce identically on a clean `premusic` worktree with none of this session's changes:
  `orbit_test` (F-16 orbit-radius tolerance) and `dz_check` (Easy/Hard haboob drop-zone timing).
  Neither touches audio/music code; not investigated further.
- `tests/map_fps.py` same-session A/B against the `premusic` tag: every scenario at ratio
  0.98–1.03 (`map_fps: all passed`), so the new engine code (titles, toast, prefetch timing,
  cache cap) costs nothing measurable in render frame rate.

## iPhone-landscape hand test checklist

- [x] Music starts on the first tap (existing engine behavior, unchanged; verified via
      `music_check.py`'s "(b) playing on the home screen after a tap").
- [x] No track runs longer than 3:30 — longest final file is 3:28 (afi-phoenix.m4a).
- [x] Fades are clean — 1.5s equal-power crossfade unchanged; verified by
      `music_check.py`'s crossfade/equal-power assertions.
- [x] Shuffle has no repeats until every track has played once — unchanged queue logic,
      verified by `music_check.py`.
- [x] Only one or two tracks download at a time — prefetch now starts 20s before the current
      track ends rather than immediately; never precaches the folder.
- [x] No fps drop — `map_fps.py` A/B vs `premusic`, all scenarios flat (0.98–1.03x).
- [x] No console errors — `music_check.py` asserts zero page/console errors through the whole
      flow, including the new pause/credits screens.

No changes to app name, icon, or `manifest.json`'s `start_url`/`scope`.
