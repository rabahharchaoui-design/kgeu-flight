// Tasking item 1: may the Worker take the Taskings boards as they are? It may not, and nothing in server/ changed.
// boardOf (server/src/boards.js) knows only BOARDS and FAMILIES (empty), so task:overwatch and the rest come back null,
// and /submit and /token refuse a board boardOf does not know (server/src/worker.js). The game keeps these four boards
// on the device (LB.localAdd). The ids already fit a one line family, ['task:', {...}], if the Worker ever takes them.
// Run: node tests/tasking_worker_check.mjs
import { readFileSync } from 'node:fs';
import { boardOf } from '../server/src/boards.js';
const fails = [];
const ok = (n, c, d) => { console.log((c ? '  ok   ' : '  FAIL ') + n + (d ? '  ' + d : '')); if (!c) fails.push(n); };
const ids = ['overwatch', 'lifeline', 'shepherd', 'finder'].map(t => 'task:' + t);
ok('boardOf refuses every Taskings id (no BOARDS entry, no task: family)', ids.every(b => boardOf(b) === null), ids.map(b => b + '=' + JSON.stringify(boardOf(b))).join(' '));
const w = readFileSync(new URL('../server/src/worker.js', import.meta.url), 'utf8');
ok('/submit rejects an unknown board', /if \(!bd\) return reject\(c, 'unknown board'\)/.test(w));
ok('/token rejects an unknown board', /if \(!boardOf\(b\)\) return reject\(c, 'token for unknown board', 400\)/.test(w));
ok('the ids fit the family pattern the Worker would need (40 chars, [a-z0-9:_-])', ids.every(b => b.length <= 40 && /^[a-z0-9:_-]+$/i.test(b)));
console.log('\ntasking_worker_check: ' + (fails.length ? 'FAILED\n  ' + fails.join('\n  ') : 'all passed'));
process.exit(fails.length ? 1 : 0);
