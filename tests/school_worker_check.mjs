// School1 item 9: may the Worker take the nine new lesson boards? It may not, and nothing in server/ changed.
// boardOf (server/src/boards.js) knows the six server lessons (lesson:first, steep, slow, stall, engine, pattern) in BOARDS
// and FAMILIES is empty, so lesson:climbs and the other new ids come back null, and /submit and /token refuse a board
// boardOf does not know (server/src/worker.js). The game keeps those nine boards on the device (LB.localAdd).
// Run: node tests/school_worker_check.mjs
import { readFileSync } from 'node:fs';
import { boardOf } from '../server/src/boards.js';
const fails = [];
const ok = (n, c, d) => { console.log((c ? '  ok   ' : '  FAIL ') + n + (d ? '  ' + d : '')); if (!c) fails.push(n); };
const neu = ['climbs', 'ground', 'landings', 'solo', 'short', 'soft', 'xwind', 'emerg', 'hood'].map(t => 'lesson:' + t);
const srv = ['first', 'steep', 'slow', 'stall', 'engine', 'pattern'].map(t => 'lesson:' + t);
ok('boardOf refuses every new lesson id (no BOARDS entry, no lesson: family)', neu.every(b => boardOf(b) === null), neu.map(b => b + '=' + JSON.stringify(boardOf(b))).join(' '));
ok('boardOf knows the six server lessons', srv.every(b => boardOf(b) !== null), srv.filter(b => boardOf(b) === null).join(' '));
const w = readFileSync(new URL('../server/src/worker.js', import.meta.url), 'utf8');
ok('/submit rejects an unknown board', /if \(!bd\) return reject\(c, 'unknown board'\)/.test(w));
ok('/token rejects an unknown board', /if \(!boardOf\(b\)\) return reject\(c, 'token for unknown board', 400\)/.test(w));
const h = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
ok('the game registers the nine as device local boards', neu.every(b => h.includes("'" + b.slice(7) + "'")) && /lesson:'\+[^\n]*local:1/.test(h));
console.log('\nschool_worker_check: ' + (fails.length ? 'FAILED\n  ' + fails.join('\n  ') : 'all passed'));
process.exit(fails.length ? 1 : 0);
