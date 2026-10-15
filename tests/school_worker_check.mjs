// School boards on the Worker (bugs1 item 1): boardOf (server/src/boards.js) knows the six first lessons (lesson:first,
// steep, slow, stall, engine, pattern) by their own BOARDS entries, which win over the family, and every other lesson
// (school1, school2, the checkride lesson:ride) through the lesson: family { dir: 1, min: 0, max: 100, minSecs: 60,
// ref: 100 }. /submit and /token still refuse a board boardOf does not know (server/src/worker.js). The game registers
// none of them as a device board.
// Run: node tests/school_worker_check.mjs
import { readFileSync } from 'node:fs';
import { boardOf } from '../server/src/boards.js';
const fails = [];
const ok = (n, c, d) => { console.log((c ? '  ok   ' : '  FAIL ') + n + (d ? '  ' + d : '')); if (!c) fails.push(n); };
const neu = ['climbs', 'ground', 'landings', 'solo', 'short', 'soft', 'xwind', 'emerg', 'hood',
  'night', 'pilotage', 'soloxc', 'divert', 'ride'].map(t => 'lesson:' + t);
const srv = { first: 20, steep: 10, slow: 25, stall: 3, engine: 15, pattern: 45 };
const fam = { dir: 1, min: 0, max: 100, minSecs: 60, ref: 100 };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
ok('boardOf takes every new lesson id through the lesson: family (minSecs 60)', neu.every(b => same(boardOf(b), fam)), neu.filter(b => !same(boardOf(b), fam)).map(b => b + '=' + JSON.stringify(boardOf(b))).join(' '));
ok('the six server lessons keep their own BOARDS entries', Object.entries(srv).every(([k, s]) => { const b = boardOf('lesson:' + k); return b && b.minSecs === s && b.max === 100; }),
  Object.keys(srv).map(k => k + '=' + JSON.stringify(boardOf('lesson:' + k))).join(' '));
ok('lessons: (no colon after lesson) is not the family', boardOf('lessons:x') === null);
const w = readFileSync(new URL('../server/src/worker.js', import.meta.url), 'utf8');
ok('/submit rejects an unknown board', /if \(!bd\) return reject\(c, 'unknown board'\)/.test(w));
ok('/token rejects an unknown board', /if \(!boardOf\(b\)\) return reject\(c, 'token for unknown board', 400\)/.test(w));
const h = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
ok('the game knows the new lesson ids', neu.every(b => h.includes("'" + b.slice(7) + "'")));
ok('the game registers no device local board (no local:1 left)', !/local:1/.test(h));
console.log('\nschool_worker_check: ' + (fails.length ? 'FAILED\n  ' + fails.join('\n  ') : 'all passed'));
process.exit(fails.length ? 1 : 0);
