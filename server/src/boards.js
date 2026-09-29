// Every leaderboard the server accepts, with the limits it checks. The game has the
// same list in index.html (LB.board(...)); tests/lb_boards_check.py keeps them in step.
//   dir      1 = higher is better, -1 = lower is better
//   min,max  the legal score range
//   minSecs  shortest possible run in seconds, anything faster is refused
//   time     the score is the run time itself
//   parMax   arcade points: score <= 1000 * min(1.5, parMax / secs)
//   ghost    a race or time trial: the flight path comes with the score
//   ref      the score that earns full performance XP (lower-is-better boards: [best, worst])
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
  'free:landing':   { dir: 1, min: 0, max: 100, minSecs: 8, ref: 100 },
};
// future modes register on the server in one line too, e.g.
//   BOARDS['apt:KPHX'] = { dir: 1, min: 0, max: 100, minSecs: 20, ref: 100 };
// and a whole family can share limits by prefix:
const FAMILIES = [
  // ['apt:', { dir: 1, min: 0, max: 100, minSecs: 20, ref: 100 }],
  // ['dogfight:', { dir: 1, min: 0, max: 1000, minSecs: 30, ref: 1000 }],
];
export function boardOf(id) {
  if (typeof id !== 'string' || id.length > 40) return null;
  if (Object.prototype.hasOwnProperty.call(BOARDS, id)) return BOARDS[id];
  for (const [pre, b] of FAMILIES) if (id.startsWith(pre) && /^[a-z0-9:_-]+$/i.test(id)) return b;
  return null;
}

// fastest ground speed each aircraft can show in a flight path, m/s: VNE as true airspeed
// at altitude plus a strong tailwind, rounded up
export const AC_VMAX = { cessna: 130, alpha: 110, reaper: 180, mq9b: 180, c130: 240, f16: 580 };

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
