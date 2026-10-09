// Arsenal item 5: the real leaderboard Worker (server/, not changed) against the game's new dogfight submission. Starts
// `wrangler dev` on a fresh local D1 (port 8787, like server/test/api_test.mjs; run it alone), signs a test player up and
// submits Hard dogfight runs with the arsenal fields in the df block (lo, mult, pts, srm, mrm, msh, mk, lr):
//   (a) the base points with the new fields: accepted, the score row is the base, the kills fan out as before
//   (b) the same run's multiplied points as the score: refused by dfProblem's cap (why the game sends the base)
//   (c) a run with no arsenal fields (an older build): accepted as before
// Run: node tests/arsenal_worker_check.mjs     (takes about 40 s: the Worker wants 24 s between a token and a 3 kill run)
import { spawn, execSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

const BASE = 'http://127.0.0.1:8787', ORIGIN = 'http://localhost:8765';
const here = new URL('../server/', import.meta.url).pathname;
let fails = 0, dev = null;
const ok = (n, c, d = '') => { console.log((c ? '  ok   ' : '  FAIL ') + n + (d ? '  ' + d : '')); if (!c) fails++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const key = () => randomBytes(24).toString('hex');
async function call(path, body) {
  const hd = { Origin: ORIGIN, 'x-pfs-dfday': '0' };
  const r = await fetch(BASE + path, body ? { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, hd), body: JSON.stringify(body) } : { headers: hd });
  let j = null; try { j = await r.json(); } catch (e) { }
  return { s: r.status, j: j || {} };
}
async function startDev() {
  rmSync(here + '.wrangler/state', { recursive: true, force: true });
  execSync('npx wrangler d1 execute pfs-scores --local --file=schema.sql', { cwd: here, stdio: 'ignore' });
  dev = spawn('npx', ['wrangler', 'dev', '--port', '8787', '--ip', '127.0.0.1', '--var', 'DEV_DFDAY:1'], { cwd: here, stdio: 'ignore', detached: true });
  for (let i = 0; i < 60; i++) { try { const r = await fetch(BASE + '/health'); if (r.ok) return; } catch (e) { } await sleep(500); }
  throw new Error('wrangler dev did not start');
}
function stopDev() { if (dev) { try { process.kill(-dev.pid, 'SIGTERM'); } catch (e) { } dev = null; } }
function sql(q) {
  const out = execSync(`npx wrangler d1 execute pfs-scores --local --json --command ${JSON.stringify(q)}`, { cwd: here, encoding: 'utf8' });
  return JSON.parse(out)[0].results;
}

async function main() {
  await startDev();
  const cs = 'T' + randomBytes(4).toString('hex').toUpperCase().slice(0, 7), k = key();
  const su = await call('/signup', { cs, key: k });
  ok('a test player signs up', su.s === 200, JSON.stringify(su.j).slice(0, 120));
  const me = { cs, key: k };
  const tok = async () => (await call('/token', { cs, key: k, board: 'df:score:hard', mode: 'hard' })).j.token;
  const t1 = await tok(), t2 = await tok(), t3 = await tok();
  ok('three df:score:hard tokens', !!t1 && !!t2 && !!t3);
  // a LIGHT + HALF run: 3 missile kills (one by MRM), one wave cleared with 50 s banked, no hits: 300 + 100 = 400 base, x1.15 = 460
  const stats = { kills: 3, guns: 0, hits: 0, waves: 1, won: false, clear: null, bank: 50, flares: 2, ach: [], brk: 1, ov: 0 };
  const arsenal = { lo: 'light/half', mult: 1.15, pts: 460, srm: 4, mrm: 0, msh: 0, mk: 0, lr: 0 };
  const run = (score, df, token) => Object.assign({ board: 'df:score:hard', mode: 'hard', score, secs: 60, ac: 'f16', wx: 'day 0@0', when: Date.now(), df, token }, me);
  console.log('  waiting 25 s (the Worker wants 24 s between the token and a 3 kill run)');
  await sleep(25000);
  const a = await call('/submit', run(400, Object.assign({}, stats, arsenal), t1));
  ok('(a) the base points (400) with the arsenal fields in the df block: accepted', a.s === 200 && a.j.ok && a.j.score === 400 && a.j.board === 'df:score:hard', JSON.stringify(a.j).slice(0, 200));
  ok('(a) the kills fan out as before (df.kills 3)', a.j.df && a.j.df.kills && a.j.df.kills.score === 3, JSON.stringify(a.j.df));
  const rows = sql(`SELECT board, score FROM scores WHERE callsign='${cs}' ORDER BY board`);
  ok('(a) the stored rows: df:kills:hard 3 and df:score:hard 400 (the base)', JSON.stringify(rows) === JSON.stringify([{ board: 'df:kills:hard', score: 3 }, { board: 'df:score:hard', score: 400 }]), JSON.stringify(rows));
  const b = await call('/submit', run(460, Object.assign({}, stats, arsenal), t2));
  ok('(b) the multiplied points (460) as the score: refused by the stats cap (why the game sends the base)', b.s === 400 && /over the 400 its stats allow/.test(b.j.reason || b.j.error || JSON.stringify(b.j)), JSON.stringify(b.j).slice(0, 200));
  const c = await call('/submit', run(400, stats, t3));
  ok('(c) a run without the arsenal fields (an older build): accepted', c.s === 200 && c.j.ok, JSON.stringify(c.j).slice(0, 200));
}
main().catch(e => { console.log('  FAIL ' + e.message); fails++; }).finally(() => {
  stopDev();
  console.log('\narsenal_worker_check: ' + (fails ? 'FAILED (' + fails + ')' : 'all passed'));
  process.exit(fails ? 1 : 0);
});
