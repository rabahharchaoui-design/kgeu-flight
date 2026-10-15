// Tasking boards on the Worker (bugs1 item 1): boardOf (server/src/boards.js) takes the Taskings through the task: family,
// { dir: 1, min: 0, max: 100, minSecs: 120, ref: 100 }, so task:overwatch and the rest (and any new task:<id>) are known;
// /submit and /token still refuse a board boardOf does not know (server/src/worker.js). The game submits them as normal
// global boards (LB.runStart at ACCEPT, LB.runEnd at taskEnd).
// Run: node tests/tasking_worker_check.mjs
import { readFileSync } from 'node:fs';
import { boardOf } from '../server/src/boards.js';
const fails = [];
const ok = (n, c, d) => { console.log((c ? '  ok   ' : '  FAIL ') + n + (d ? '  ' + d : '')); if (!c) fails.push(n); };
const ids = ['overwatch', 'lifeline', 'shepherd', 'finder'].map(t => 'task:' + t);
const fam = { dir: 1, min: 0, max: 100, minSecs: 120, ref: 100 };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
ok('boardOf takes every Taskings id through the task: family', ids.every(b => same(boardOf(b), fam)), ids.map(b => b + '=' + JSON.stringify(boardOf(b))).join(' '));
ok('a made up task:nope resolves to the family too', same(boardOf('task:nope'), fam), JSON.stringify(boardOf('task:nope')));
ok('tasks:x is not the family', boardOf('tasks:x') === null, JSON.stringify(boardOf('tasks:x')));
const long = 'task:' + 'a'.repeat(41);
ok('task: plus 41 chars is refused (over 40)', boardOf(long) === null, JSON.stringify(boardOf(long)));
ok('a task: id with a bad character is refused', boardOf('task:a b') === null && boardOf('task:a/b') === null);
const w = readFileSync(new URL('../server/src/worker.js', import.meta.url), 'utf8');
ok('/submit rejects an unknown board', /if \(!bd\) return reject\(c, 'unknown board'\)/.test(w));
ok('/token rejects an unknown board', /if \(!boardOf\(b\)\) return reject\(c, 'token for unknown board', 400\)/.test(w));
ok('the ids fit the family pattern (40 chars, [a-z0-9:_-])', ids.every(b => b.length <= 40 && /^[a-z0-9:_-]+$/i.test(b)));
const h = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
ok('the game registers no device local board', !/local:1/.test(h));
console.log('\ntasking_worker_check: ' + (fails.length ? 'FAILED\n  ' + fails.join('\n  ') : 'all passed'));
process.exit(fails.length ? 1 : 0);
