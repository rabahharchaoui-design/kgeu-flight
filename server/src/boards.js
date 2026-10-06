// Every leaderboard the server accepts, with the limits it checks. The game has the
// same list in index.html (LB.board(...)); tests/lb_boards_check.py keeps them in step.
//   dir      1 = higher is better, -1 = lower is better
//   min,max  the legal score range
//   minSecs  shortest possible run in seconds, anything faster is refused
//   time     the score is the run time itself
//   parMax   arcade points: score <= 1000 * min(1.5, parMax / secs)
//   ghost    a race or time trial: the flight path comes with the score
//   ref      the score that earns full performance XP (lower-is-better boards: [best, worst])
//   mode     a single mode board ('easy' or 'hard'): a run in the other mode is refused
const L = (minSecs) => ({ dir: 1, min: 0, max: 100, minSecs, ref: 100 });
export const BOARDS = {
  'lesson:first':   L(20),
  'lesson:steep':   L(10),
  'lesson:slow':    L(25),
  'lesson:stall':   L(3),
  'lesson:engine':  L(15),
  'lesson:pattern': L(45),
  'mission:short':  { dir: 1, min: 0, max: 1000, minSecs: 10, ref: 1000 },
  'mission:dash':   { dir: -1, min: 30, max: 3600, minSecs: 30, time: 1, ghost: 1, ref: [120, 300] },
  'daily':          { dir: 1, min: 0, max: 1500, minSecs: 20, parMax: 480, ghost: 1, ref: 1000 },
  'arc:landing':    { dir: 1, min: 0, max: 1500, minSecs: 20, parMax: 480, ghost: 1, ref: 1000 },
  'arc:landing1':   { dir: 1, min: 0, max: 1500, minSecs: 10, parMax: 180, ghost: 1, ref: 1000 },
  'arc:drop':       { dir: -1, min: 0, max: 3000, minSecs: 15, ref: [0, 150] },
  'arc:strike':     { dir: 1, min: 0, max: 100, minSecs: 15, ref: 100 },
  'arc:gunrun':     { dir: 1, min: 0, max: 100, minSecs: 15, ref: 100 },   // planes2: the A-10 on the same range
  'free:landing':   { dir: 1, min: 0, max: 100, minSecs: 8, ref: 100 },
  // world airports: the 5 mile landing challenge to the region's home runway (34R, 26L, 20L)
  'apt:RJTT':       { dir: 1, min: 0, max: 1500, minSecs: 20, parMax: 480, ghost: 1, ref: 1000 },
  'apt:LFPG':       { dir: 1, min: 0, max: 1500, minSecs: 20, parMax: 480, ghost: 1, ref: 1000 },
  'apt:SBRJ':       { dir: 1, min: 0, max: 1500, minSecs: 20, parMax: 480, ghost: 1, ref: 1000 },
};
// the Red Flag Dogfight: Easy and Hard are SEPARATE boards (mode: the only mode the board takes). A run is one
// submission to df:score:<mode> carrying its stats (df); the server checks it (dfProblem) and writes the kills, clear
// and guns rows itself (fan: only ever written by that fan out, never submitted directly).
for (const m of ['easy', 'hard']) {
  BOARDS['df:score:' + m] = { dir: 1, min: 0, max: 3000, minSecs: 20, ref: 1500, mode: m, df: 1 };
  BOARDS['df:kills:' + m] = { dir: 1, min: 0, max: 10, minSecs: 20, ref: 10, mode: m, fan: 'k' };
  BOARDS['df:clear:' + m] = { dir: -1, min: 45, max: 390, minSecs: 45, ref: [90, 360], mode: m, fan: 'c' };
  BOARDS['df:guns:' + m] =  { dir: 1, min: 0, max: 10, minSecs: 20, ref: 10, mode: m, fan: 'g' };
}
// the dogfight's caps (LEADERBOARD.md): 4 rounds of 90 s, 10 bandits, 3 hits; points 100 a kill (+100 by gun), 2 a
// second banked, 250 a win, -75 a hit. Achievement XP is given once per player, ever (table achs).
export const DF = { waves: 4, round: 90, kills: 10, hits: 3, perKill: 4, winSecs: 45, maxSecs: 4 * 90 + 30 };
export const DF_ACH_XP = { ace: 150, guns: 75, flaresave: 50, untouchable: 200 };
// a dogfight day for the daily challenge: the UTC day number (days since 1970-01-01) % 5 === 3
export const dfDay = ms => Math.floor(ms / 86400000) % 5 === 3;
// what is wrong with a dogfight run's stats (null: nothing). d: the df block; score: the run's dogfight points
// (the daily's points x 2 on a dogfight day, tol 2); secs: its fight time
export function dfProblem(d, score, secs, ac, tol = 1) {
  if (!d || typeof d !== 'object') return 'dogfight run without its stats';
  if (ac !== 'f16') return 'dogfight flown in ' + (ac || 'no aircraft') + ', not the F-16';
  const I = (v, lo, hi) => Number.isInteger(v) && v >= lo && v <= hi;
  const kills = d.kills, guns = d.guns, hits = d.hits, waves = d.waves, won = !!d.won, bank = +d.bank, flares = d.flares | 0;
  if (!I(kills, 0, DF.kills)) return 'dogfight kills ' + kills + ' not 0 to 10';
  if (!I(guns, 0, DF.kills)) return 'dogfight gun kills ' + guns + ' not 0 to 10';
  if (guns > kills) return 'more gun kills (' + guns + ') than kills (' + kills + ')';
  if (!I(hits, 0, DF.hits)) return 'dogfight hits ' + hits + ' not 0 to 3';
  if (!I(waves, 0, DF.waves)) return 'dogfight waves ' + waves + ' not 0 to 4';
  if (won && !(kills === DF.kills && waves === DF.waves && hits < DF.hits)) return 'a win needs 10 kills, 4 waves and under 3 hits';
  if (secs > DF.maxSecs) return 'dogfight of ' + Math.round(secs) + ' s, over ' + DF.maxSecs + ' s';
  if (secs < DF.perKill * kills) return kills + ' kills in ' + secs.toFixed(1) + ' s, faster than one a ' + DF.perKill + ' s';
  if (won && secs < DF.winSecs) return 'a win in ' + secs.toFixed(1) + ' s, under ' + DF.winSecs + ' s';
  // banked seconds: whole seconds up per cleared wave, so up to one more a wave
  if (!Number.isFinite(bank) || bank < 0 || bank > Math.max(0, DF.round * waves - DF.perKill * kills) + waves) return 'banked ' + d.bank + ' s, too many for ' + waves + ' waves and ' + kills + ' kills';
  const cap = Math.max(0, 100 * kills + 100 * guns + 2 * bank + (won ? 250 : 0) - 75 * hits);
  if (score > cap + tol) return 'dogfight score ' + score + ' over the ' + cap + ' its stats allow';
  if (d.clear != null) {
    const cl = +d.clear;
    if (!won) return 'clear time without a win';
    if (!Number.isFinite(cl) || cl < DF.winSecs || cl > secs + 1) return 'clear time ' + d.clear + ' s does not fit a ' + secs.toFixed(1) + ' s fight';
  } else if (won) return 'a win without its clear time';
  const ach = d.ach == null ? [] : d.ach;
  if (!Array.isArray(ach) || ach.length > 4) return 'bad achievement list';
  for (const a of ach) {
    if (!Object.prototype.hasOwnProperty.call(DF_ACH_XP, a)) return 'unknown achievement ' + String(a).slice(0, 20);
    if (a === 'ace' && kills < 5) return 'Ace claimed with ' + kills + ' kills';
    if (a === 'guns' && guns < 1) return 'Guns Kill claimed with no gun kill';
    if (a === 'untouchable' && !(won && hits === 0)) return 'Untouchable claimed without a clean win';
    if (a === 'flaresave' && flares < 1) return 'Flare Save claimed with no flares used';
  }
  return null;
}
// future modes register on the server in one line too, e.g.
//   BOARDS['race:red'] = { dir: 1, min: 0, max: 1000, minSecs: 30, ref: 1000 };
// and a whole family can share limits by prefix:
const FAMILIES = [
  // ['apt:', { dir: 1, min: 0, max: 100, minSecs: 20, ref: 100 }],
];
export function boardOf(id) {
  if (typeof id !== 'string' || id.length > 40) return null;
  if (Object.prototype.hasOwnProperty.call(BOARDS, id)) return BOARDS[id];
  for (const [pre, b] of FAMILIES) if (id.startsWith(pre) && /^[a-z0-9:_-]+$/i.test(id)) return b;
  return null;
}

// fastest ground speed each aircraft can show in a flight path, m/s: VNE as true airspeed
// at altitude plus a strong tailwind, rounded up
export const AC_VMAX = { cessna: 130, alpha: 110, archer: 130, reaper: 180, mq9b: 180, c130: 240, f16: 580, a10: 300, b737: 300, a320: 300 };

export const RANKS = [
  { name: 'Nugget', xp: 0 },
  { name: 'Wingman', xp: 300 },
  { name: 'Flight Lead', xp: 1200 },
  { name: 'Instructor Pilot', xp: 3500 },
  { name: 'Weapons School', xp: 8000 },
  { name: 'Top Gun', xp: 16000 },
];
export function rankOf(xp) {
  let i = 0; while (i + 1 < RANKS.length && xp >= RANKS[i + 1].xp) i++;
  const n = RANKS[i + 1];
  return { i, name: RANKS[i].name, xp, next: n ? n.xp : null, nextName: n ? n.name : null };
}
// XP for one accepted run: 10 for flying it, up to 40 more for how good it was,
// x1.25 in Hard, +15 for a personal best, +25 for making the top 10
export function xpFor(bd, score, mode, pb, top10) {
  let q;
  if (Array.isArray(bd.ref)) { const [best, worst] = bd.ref; q = (worst - score) / (worst - best); }
  else q = score / bd.ref;
  q = Math.max(0, Math.min(1, q));
  return Math.round((10 + 40 * q) * (mode === 'hard' ? 1.25 : 1)) + (pb ? 15 : 0) + (top10 ? 25 : 0);
}
