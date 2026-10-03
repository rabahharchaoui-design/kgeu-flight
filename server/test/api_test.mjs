// End to end test of the leaderboard Worker.
//   node test/api_test.mjs                  starts `wrangler dev` on a fresh local D1, tests, stops it
//   node test/api_test.mjs https://...      runs the same checks against a deployed Worker (live:
//                                           uses the real OHRABAH secret from ../../chain only if asked,
//                                           and deletes every test player it made at the end)
import { spawn, execSync } from 'node:child_process';
import { rmSync, readFileSync, existsSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

const LIVE = process.argv[2] || '';
const BASE = LIVE || 'http://127.0.0.1:8787';
const ORIGIN = 'http://localhost:8765';
const here = new URL('..', import.meta.url).pathname;
let fails = 0, dev = null;
const ok = (n, c, d = '') => { console.log((c ? '  ok   ' : '  FAIL ') + n + (d ? '  ' + d : '')); if (!c) fails++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const key = () => randomBytes(24).toString('hex');
const tag = () => 'T' + randomBytes(4).toString('hex').toUpperCase().slice(0, 7);   // test callsigns: T + 7 hex
// local only: wrangler dev runs with DEV_DFDAY=1, so this header says whether the daily is a dogfight day ('0': a landing
// day, whatever the real date; '1': a dogfight day). Live, the real UTC day decides (realDf).
let dfHdr = '0';
const realDf = Math.floor(Date.now() / 864e5) % 5 === 3;
async function call(path, body, origin = ORIGIN) {
  const hd = Object.assign({ Origin: origin }, LIVE ? {} : { 'x-pfs-dfday': dfHdr });
  const r = await fetch(BASE + path, body ? { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, hd), body: JSON.stringify(body) }
    : { headers: hd });
  let j = null; try { j = await r.json(); } catch (e) { }
  return { s: r.status, j: j || {}, h: r.headers };
}
// the game's path encoding: 5 Hz frames of int16 [dx,dy,dz in 0.5 m, yaw, pitch, roll]
async function encPath(pts) {
  const buf = new DataView(new ArrayBuffer(pts.length * 12));
  let px = pts[0][0], py = pts[0][1], pz = pts[0][2];
  pts.forEach((p, i) => {
    const dx = Math.round((p[0] - px) * 2), dy = Math.round((p[1] - py) * 2), dz = Math.round((p[2] - pz) * 2);
    px += dx / 2; py += dy / 2; pz += dz / 2;
    buf.setInt16(i * 12, dx, true); buf.setInt16(i * 12 + 2, dy, true); buf.setInt16(i * 12 + 4, dz, true);
  });
  const cs = new CompressionStream('deflate-raw');
  const z = new Uint8Array(await new Response(new Blob([buf.buffer]).stream().pipeThrough(cs)).arrayBuffer());
  return { v: 1, hz: 5, o: pts[0].slice(0, 3), n: pts.length, z: 1, d: Buffer.from(z).toString('base64') };
}
const line = (secs, v) => Array.from({ length: Math.round(secs * 5) + 1 }, (_, i) => [1000 + i * v / 5, 300, -2000]);

async function startDev() {
  rmSync(here + '.wrangler/state', { recursive: true, force: true });
  execSync('npx wrangler d1 execute pfs-scores --local --file=schema.sql', { cwd: here, stdio: 'ignore' });
  dev = spawn('npx', ['wrangler', 'dev', '--port', '8787', '--ip', '127.0.0.1', '--var', 'DEV_DFDAY:1'], { cwd: here, stdio: 'ignore', detached: true });
  for (let i = 0; i < 60; i++) { try { const r = await fetch(BASE + '/health'); if (r.ok) return; } catch (e) { } await sleep(500); }
  throw new Error('wrangler dev did not start');
}
function stopDev() { if (dev) { try { process.kill(-dev.pid, 'SIGTERM'); } catch (e) { } dev = null; } }
function sql(q) {
  const out = execSync(`npx wrangler d1 execute pfs-scores ${LIVE ? '--remote' : '--local'} --json --command ${JSON.stringify(q)}`, { cwd: here, encoding: 'utf8' });
  return JSON.parse(out)[0].results;
}

const made = [], T0 = Date.now();
async function signup(cs, extra = {}) { const k = key(); const r = await call('/signup', Object.assign({ cs, key: k }, extra)); if (r.s === 200) made.push(r.j.cs); return Object.assign(r, { key: k }); }
async function tokenFor(me, board, mode = 'hard') { return (await call('/token', { cs: me.cs, key: me.key, board, mode })).j; }

async function main() {
  if (!LIVE) await startDev();
  console.log('Worker at ' + BASE);
  const h = await call('/health');
  ok('health', h.s === 200 && h.j.ok);
  ok('CORS allows the game origin', h.h.get('access-control-allow-origin') === ORIGIN);
  const bad = await call('/health', null, 'https://evil.example');
  ok('CORS gives nothing to another origin', !bad.h.get('access-control-allow-origin'));
  ok('POST from another origin is refused', (await call('/signup', { cs: 'NOPE123', key: key() }, 'https://evil.example')).s === 403);

  // ---- signup and name checks
  const A = tag(), B = tag();
  ok('name is free before signup', (await call('/name?cs=' + A)).j.free === true);
  const sa = await signup(A.toLowerCase());
  ok('signup returns the callsign upper cased', sa.s === 200 && sa.j.cs === A, JSON.stringify(sa.j));
  ok('signup returns a 4 word recovery code', /^[A-Z]+ [A-Z]+ [A-Z]+ [A-Z]+$/.test(sa.j.recovery || ''), sa.j.recovery);
  ok('new player is a Nugget with 0 XP', sa.j.xp === 0 && sa.j.rank && sa.j.rank.name === 'Nugget');
  ok('name is taken after signup', (await call('/name?cs=' + A)).j.free === false);
  ok('second signup of the same name refused', (await signup(A)).s === 409);
  for (const [n, want] of [['AB', 'too short'], ['ABCDEFGHIJKLM', 'too long'], ['HAB-OOB', 'letters and numbers only']])
    ok('name rule: ' + n, (await call('/name?cs=' + encodeURIComponent(n))).j.reason === want);
  for (const n of ['FUCKER', 'SH1T', '5HIT', 'FUUUCK', 'B1TCH', 'A55', 'N1GGA', 'PHUCK', 'DICK69', 'C0CK'])
    ok('profanity refused: ' + n, (await call('/name?cs=' + n)).j.reason === 'profanity');
  for (const n of ['HABOOB', 'DUSTDEVIL', 'SIDEWINDER7', 'MESQUITE', 'SAGUARO', 'MONSOON', 'COCKPIT', 'TORPEDO', 'PASSAGE', 'CUMULUS'])
    ok('clean word allowed: ' + n, (await call('/name?cs=' + n)).j.reason !== 'profanity');
  const pr = await signup('F4GG0T');
  ok('profanity signup refused by the server', pr.s === 400 && pr.j.reason === 'profanity: F4GG0T', JSON.stringify(pr.j));

  // ---- the reserved name
  ok('OHRABAH shows as reserved', (await call('/name?cs=ohrabah')).j.reserved === true);
  ok('0HRABAH (leet) is reserved too', (await call('/name?cs=0HRABAH')).j.free === false);
  ok('OHRABAH without the secret refused', (await signup('OHRABAH')).s === 403);
  ok('OHRABAH with a wrong secret refused', (await signup('OHRABAH', { secret: 'guess' })).s === 403);
  if (!LIVE) {
    const cr = await signup('OHRABAH', { secret: 'dev-ohrabah-secret' });
    ok('OHRABAH with the secret claimed, creator flag set', cr.s === 200 && cr.j.creator === true, JSON.stringify(cr.j));
    ok('OHRABAH cannot be claimed twice', (await signup('OHRABAH', { secret: 'dev-ohrabah-secret' })).s === 409);
  }

  // ---- recovery
  const me = { cs: A, key: sa.key };
  ok('/me with the device key', (await call('/me', me)).j.cs === A);
  ok('/me with a wrong key refused', (await call('/me', { cs: A, key: key() })).s === 401);
  const nk = key();
  ok('restore with a wrong code refused', (await call('/restore', { cs: A, key: nk, code: 'VIPER DUST MESA NINE' })).s === 403 || sa.j.recovery === 'VIPER DUST MESA NINE');
  const rs = await call('/restore', { cs: A, key: nk, code: sa.j.recovery.toLowerCase().replace(/ /g, '  ') });
  ok('restore with the right code (any case, any spacing)', rs.s === 200 && rs.j.cs === A, JSON.stringify(rs.j));
  ok('old device key stops working after a restore', (await call('/me', me)).s === 401);
  me.key = nk;
  ok('new device key works', (await call('/me', me)).j.cs === A);

  // ---- token flow and a genuine score
  const t1 = await tokenFor(me, 'lesson:stall');
  ok('token issued', !!t1.token, JSON.stringify(t1));
  await sleep(3200);
  const s1 = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 88, secs: 3.5, ac: 'cessna', wx: 'day', when: Date.now(), token: t1.token }, me));
  ok('genuine score accepted', s1.s === 200 && s1.j.ok, JSON.stringify(s1.j));
  ok('first score is a PB and rank #1 of 1', s1.j.pb === true && s1.j.rank === 1 && s1.j.total === 1);
  ok('XP awarded (Hard, PB, top 10)', s1.j.gain === Math.round((10 + 40 * 0.88) * 1.25) + 15 + 25, 'gain ' + s1.j.gain);
  const s1b = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 90, secs: 3.5, ac: 'cessna', wx: 'day', when: Date.now(), token: t1.token }, me));
  ok('the same token twice is refused', s1b.s === 400 && s1b.j.reason === 'token already used', JSON.stringify(s1b.j));

  // ---- fake scores
  const nt = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 99, secs: 30, ac: 'cessna', when: Date.now() }, me));
  ok('score without a token refused', nt.s === 400 && nt.j.reason === 'no valid run token');
  const t2 = await tokenFor(me, 'lesson:stall');
  const forged = t2.token.slice(0, -3) + (t2.token.endsWith('AAA') ? 'BBB' : 'AAA');
  ok('forged token signature refused', (await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 50, secs: 30, ac: 'cessna', when: Date.now(), token: forged }, me))).j.reason === 'no valid run token');
  await sleep(3200);
  ok('score above the board max refused', (await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 101, secs: 30, ac: 'cessna', when: Date.now(), token: t2.token }, me))).j.reason === 'score 101 outside 0 to 100');
  const t3 = await tokenFor(me, 'lesson:pattern');
  const fast = await call('/submit', Object.assign({ board: 'lesson:pattern', mode: 'hard', score: 95, secs: 60, ac: 'cessna', when: Date.now(), token: t3.token }, me));
  ok('run submitted faster than possible after its token refused', fast.j.reason && fast.j.reason.startsWith('submitted '), JSON.stringify(fast.j));
  const t4 = await tokenFor(me, 'lesson:pattern');
  ok('token for another board refused', (await call('/submit', Object.assign({ board: 'lesson:steep', mode: 'hard', score: 95, secs: 60, ac: 'cessna', when: Date.now(), token: t4.token }, me))).j.reason === 'token was issued for lesson:pattern');
  const t5 = await tokenFor(me, 'lesson:stall', 'easy');
  await sleep(3200);
  ok('Easy run submitted as Hard refused', (await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 50, secs: 4, ac: 'cessna', when: Date.now(), token: t5.token }, me))).j.reason === 'run started in Easy, submitted as Hard');
  const t6 = await tokenFor(me, 'arc:landing1');
  await sleep(10500);
  const tooHigh = await call('/submit', Object.assign({ board: 'arc:landing1', mode: 'hard', score: 1400, secs: 200, ac: 'f16', when: Date.now(), token: t6.token, path: await encPath(line(200, 60)) }, me));
  ok('arcade points too high for the run time refused', tooHigh.j.reason === 'points too high for a 200 s run', JSON.stringify(tooHigh.j));

  // ---- ghosts: a good path, a path that does not match the time, a path too fast for the aircraft
  const pool = (await call('/pool', Object.assign({ n: 5 }, me))).j.tokens || [];
  ok('offline pool tokens issued', pool.length === 5);
  const g1 = await call('/submit', Object.assign({ board: 'arc:landing1', mode: 'hard', score: 900, secs: 40, ac: 'cessna', wx: 'day', when: Date.now() - 3600e3, token: pool[0], path: await encPath(line(40, 40)) }, me));
  ok('race with a good ghost path accepted (queued an hour, pool token)', g1.s === 200 && g1.j.ok, JSON.stringify(g1.j));
  const g2 = await call('/submit', Object.assign({ board: 'arc:landing1', mode: 'hard', score: 900, secs: 40, ac: 'cessna', when: Date.now(), token: pool[1], path: await encPath(line(20, 40)) }, me));
  ok('ghost path shorter than the run time refused', (g2.j.reason || '').startsWith('ghost path is 20.0 s'), JSON.stringify(g2.j));
  const g3 = await call('/submit', Object.assign({ board: 'arc:landing1', mode: 'hard', score: 900, secs: 40, ac: 'cessna', when: Date.now(), token: pool[2], path: await encPath(line(40, 200)) }, me));
  ok('ghost path over the aircraft speed limit refused', (g3.j.reason || '').includes('over the cessna limit'), JSON.stringify(g3.j));
  const g4 = await call('/submit', Object.assign({ board: 'arc:landing1', mode: 'hard', score: 900, secs: 40, ac: 'cessna', when: Date.now(), token: pool[3] }, me));
  ok('race without a ghost path refused', g4.j.reason === 'ghost path missing');
  const g5 = await call('/submit', Object.assign({ board: 'arc:landing1', mode: 'hard', score: 900, secs: 40, ac: 'cessna', when: Date.now() - 25 * 3600e3, token: pool[4], path: await encPath(line(40, 40)) }, me));
  ok('queued run older than 24 hours refused', g5.j.reason === 'queued run older than 24 hours');
  const gh = await call('/ghost?b=arc:landing1&m=hard');
  ok('leader ghost served with callsign and path', gh.j.ghost && gh.j.ghost.cs === A && gh.j.ghost.path.n === 201, JSON.stringify(gh.j).slice(0, 120));

  // ---- a second player, the board, ranks, daily once a day
  const sb = await signup(B); const you = { cs: B, key: sb.key };
  const tb = await tokenFor(you, 'lesson:stall');
  await sleep(3200);
  const sB = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 70, secs: 5, ac: 'alpha', wx: 'night', when: Date.now(), token: tb.token }, you));
  ok('second player ranked #2 of 2', sB.j.rank === 2 && sB.j.total === 2, JSON.stringify(sB.j));
  const bd = await call('/board?b=lesson:stall&m=hard&p=all&cs=' + B);
  ok('board lists both, best first', bd.j.rows.length >= 2 && bd.j.rows[0].score >= bd.j.rows[1].score);
  ok('board carries my row and rank', bd.j.me && bd.j.me.cs === B && bd.j.me.r === 2 && bd.j.total === 2, JSON.stringify(bd.j.me));
  ok('board rows carry the rank badge', !!bd.j.rows[0].rank);
  ok('today and week tabs answer', (await call('/board?b=lesson:stall&m=hard&p=today')).j.rows.length === 2 && (await call('/board?b=lesson:stall&m=hard&p=week')).j.rows.length === 2);
  ok('board rows carry their mode', bd.j.rows.every(r => r.mode === 'hard') && bd.j.me.mode === 'hard', JSON.stringify(bd.j.rows.map(r => r.mode)));

  // ---- one list per board: Easy and Hard merge for display, each player's best run once
  const te1 = await tokenFor(you, 'lesson:stall', 'easy'), te2 = await tokenFor(me, 'lesson:stall', 'easy');
  await sleep(3200);
  const eB = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'easy', score: 95, secs: 4, ac: 'alpha', wx: 'day', when: Date.now(), token: te1.token }, you));
  ok('Easy run beating my Hard best is a PB, #1 of 2 across both modes', eB.s === 200 && eB.j.pb === true && eB.j.rank === 1 && eB.j.total === 2, JSON.stringify(eB.j));
  const eA = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'easy', score: 60, secs: 4, ac: 'cessna', wx: 'day', when: Date.now(), token: te2.token }, me));
  ok('Easy run under my Hard best is no PB, best stays the Hard one', eA.s === 200 && eA.j.pb === false && eA.j.best === 88 && eA.j.rank === 2 && eA.j.total === 2, JSON.stringify(eA.j));
  const mb = await call('/board?b=lesson:stall&p=all&cs=' + B);
  ok('merged board: each player once, total counts them once', mb.j.rows.length === 2 && mb.j.total === 2 && new Set(mb.j.rows.map(r => r.cs)).size === 2, JSON.stringify(mb.j.rows));
  ok('merged board: best row per player with its mode', mb.j.rows[0].cs === B && mb.j.rows[0].score === 95 && mb.j.rows[0].mode === 'easy'
    && mb.j.rows[1].cs === A && mb.j.rows[1].score === 88 && mb.j.rows[1].mode === 'hard', JSON.stringify(mb.j.rows));
  ok('merged board: my row is my best across modes', mb.j.me && mb.j.me.r === 1 && mb.j.me.score === 95 && mb.j.me.mode === 'easy', JSON.stringify(mb.j.me));
  ok('merged board: the m parameter is ignored', JSON.stringify((await call('/board?b=lesson:stall&m=easy&p=all')).j.rows) === JSON.stringify((await call('/board?b=lesson:stall&m=hard&p=all')).j.rows) && mb.j.mode === 'all');
  ok('merged board: today tab merges too', (await call('/board?b=lesson:stall&p=today')).j.rows.length === 2);
  ok('scores stay stored per mode', sql(`SELECT mode FROM scores WHERE callsign IN ('${A}','${B}') AND board='lesson:stall' ORDER BY mode`).map(r => r.mode).join() === 'easy,easy,hard,hard');
  const d1 = await tokenFor(you, 'daily');
  ok('first daily token is official', !!d1.token && !d1.practice);
  const d2 = await tokenFor(you, 'daily');
  ok('second daily token of the day is practice', d2.practice === true && !d2.token);
  const ta = await tokenFor(me, 'apt:RJTT');
  ok('world airport token issued (apt:RJTT)', !!ta.token, JSON.stringify(ta));
  await sleep(20500);
  const sa1 = await call('/submit', Object.assign({ board: 'apt:RJTT', mode: 'hard', score: 1100, secs: 95, ac: 'cessna', wx: 'night 40@8', when: Date.now(), token: ta.token, path: await encPath(line(95, 40)) }, me));
  ok('world airport run accepted (apt:RJTT)', sa1.s === 200 && sa1.j.ok && sa1.j.rank === 1, JSON.stringify(sa1.j));
  const ba = await call('/board?b=apt:RJTT&p=all&cs=' + A);
  ok('apt:RJTT board lists it', ba.j.rows && ba.j.rows.length === 1 && ba.j.rows[0].cs === A && ba.j.rows[0].score === 1100 && ba.j.me && ba.j.me.r === 1, JSON.stringify(ba.j.rows));
  ok('apt:RJTT points too high for the time refused', (await call('/submit', Object.assign({ board: 'apt:RJTT', mode: 'hard', score: 1500, secs: 400, ac: 'cessna', when: Date.now(), token: (await call('/pool', Object.assign({ n: 1 }, me))).j.tokens[0], path: await encPath(line(400, 40)) }, me))).j.reason === 'points too high for a 400 s run');
  const landDay = !(LIVE && realDf);
  if (landDay) {
  const ds = await call('/submit', Object.assign({ board: 'daily', mode: 'hard', score: 800, secs: 90, ac: 'f16', wx: 'day', when: Date.now(), token: d1.token, path: await encPath(line(90, 100)) }, you));
  ok('official daily attempt accepted', ds.s === 200, JSON.stringify(ds.j));
  const yp = (await call('/pool', Object.assign({ n: 1 }, you))).j.tokens[0];
  ok('second daily score of the day refused', (await call('/submit', Object.assign({ board: 'daily', mode: 'hard', score: 900, secs: 90, ac: 'f16', when: Date.now(), token: yp, path: await encPath(line(90, 100)) }, you))).j.reason === 'second official daily attempt');
  }
  const fm = await call('/fame');
  ok('fame: today\'s daily #1 and the top 3 by XP', (!landDay || (fm.j.daily && fm.j.daily.cs === B)) && fm.j.top.length >= 2, JSON.stringify(fm.j));
  ok('fame: the world airport champions (apt.RJTT, nobody yet at LFPG and SBRJ)', fm.j.apt && fm.j.apt.RJTT && fm.j.apt.RJTT.cs === A && fm.j.apt.RJTT.score === 1100 && fm.j.apt.RJTT.mode === 'hard'
    && 'LFPG' in fm.j.apt && 'SBRJ' in fm.j.apt && (LIVE || (fm.j.apt.LFPG === null && fm.j.apt.SBRJ === null)), JSON.stringify(fm.j.apt));

  // ---- rename: old scores follow, once per 30 days
  const C = tag();
  const rn = await call('/rename', Object.assign({ to: C }, you));
  ok('rename accepted', rn.s === 200 && rn.j.cs === C, JSON.stringify(rn.j));
  made.push(C);
  you.cs = C;
  const bd2 = await call('/board?b=lesson:stall&m=hard&p=all&cs=' + C);
  ok('old scores follow the new name', bd2.j.rows.some(r => r.cs === C) && !bd2.j.rows.some(r => r.cs === B));
  ok('second rename inside 30 days refused', (await call('/rename', Object.assign({ to: tag() }, you))).s === 429);
  const rp = await call('/rename', Object.assign({ to: 'SH1THEAD' }, me));
  ok('rename to a profane name refused', rp.s === 400 && rp.j.reason === 'profanity on rename: SH1THEAD', JSON.stringify(rp.j));

  // ---- the Red Flag Dogfight: Easy and Hard boards, one submission a run fanned out, caps, achievement XP, the daily
  sql(`DELETE FROM hits WHERE kind='submit' AND ts>=${T0}`);   // the 30 an hour per IP: this section is a fresh hour's worth
  const DG = tag(), sd = await signup(DG), dg = { cs: DG, key: sd.key };
  const E2 = tag(), se = await signup(E2), eg = { cs: E2, key: se.key };
  const tH = await tokenFor(dg, 'df:score:hard'), tE = await tokenFor(dg, 'df:score:easy', 'easy');
  dfHdr = '1'; const dd = await tokenFor(eg, 'daily'); dfHdr = '0';
  const tWait = Date.now();
  ok('dogfight tokens issued (df:score:hard, df:score:easy) and a daily one', !!tH.token && !!tE.token && !!dd.token, JSON.stringify([tH, tE, dd]).slice(0, 200));
  const dp = (await call('/pool', Object.assign({ n: 5 }, dg))).j.tokens || [];
  const dfs = (o, sc, secs, extra = {}) => Object.assign({ board: 'df:score:hard', mode: 'hard', score: sc, secs, ac: 'f16', wx: 'day 0@0', when: Date.now(), df: o }, extra, dg);
  const win = { kills: 10, guns: 3, hits: 0, waves: 4, won: true, clear: 250.3, bank: 110, flares: 4, ach: ['ace', 'guns', 'untouchable', 'flaresave'] };
  const xp0 = (await call('/me', dg)).j.xp;
  const w1 = await call('/submit', dfs(win, 1770, 251, { token: dp[0] }));
  ok('a legal Hard win accepted on df:score:hard, #1', w1.s === 200 && w1.j.ok && w1.j.board === 'df:score:hard' && w1.j.rank === 1, JSON.stringify(w1.j));
  ok('the answer carries the fan out: kills, clear and guns ranks and personal bests', w1.j.df && w1.j.df.kills.rank === 1 && w1.j.df.kills.pb && w1.j.df.kills.score === 10
    && w1.j.df.clear && w1.j.df.clear.score === 250.3 && w1.j.df.clear.pb && w1.j.df.guns && w1.j.df.guns.score === 3, JSON.stringify(w1.j.df));
  const wantAch = 150 + 75 + 200 + 50, runXp = Math.round((10 + 40) * 1.25) + 15 + 25;
  ok('achievements give their XP the first time (Ace 150, Guns Kill 75, Untouchable 200, Flare Save 50)', w1.j.ach && w1.j.ach.length === 4 && w1.j.achXp === wantAch
    && w1.j.ach.find(a => a.id === 'ace').xp === 150 && w1.j.ach.find(a => a.id === 'untouchable').xp === 200, JSON.stringify(w1.j.ach));
  ok('the run XP once (ref 1,500, Hard, PB, top 10), plus the achievements', w1.j.gain === runXp && w1.j.xp === xp0 + runXp + wantAch, JSON.stringify([w1.j.gain, w1.j.xp, xp0]));
  const rows = sql(`SELECT board, score, token FROM scores WHERE callsign='${DG}' ORDER BY board`);
  const jt = rows.find(r => r.board === 'df:score:hard').token;
  ok('four rows: score, kills, clear, guns on the run token id plus :k :c :g', rows.length === 4 && JSON.stringify(rows.map(r => [r.board, r.score, r.token.replace(jt, 'J')]))
    === JSON.stringify([['df:clear:hard', 250.3, 'J:c'], ['df:guns:hard', 3, 'J:g'], ['df:kills:hard', 10, 'J:k'], ['df:score:hard', 1770, 'J']]), JSON.stringify(rows));
  ok('the same token twice is refused (dogfight)', (await call('/submit', dfs(win, 1770, 251, { token: dp[0] }))).j.reason === 'token already used');
  const w2 = await call('/submit', dfs({ kills: 6, guns: 0, hits: 1, waves: 2, won: false, clear: null, bank: 40, flares: 2, ach: ['ace'] }, 600 + 80 - 75, 150, { token: dp[1] }));
  ok('a second run: Ace again gives no XP, no clear or guns row, kills is no PB', w2.s === 200 && w2.j.ach.length === 0 && w2.j.achXp === 0 && w2.j.df.clear === null && w2.j.df.guns === null
    && w2.j.df.kills.pb === false && w2.j.df.kills.best === 10, JSON.stringify(w2.j));
  ok('the fan out boards list the run (df:kills:hard, df:clear:hard)', (await call('/board?b=df:kills:hard&p=all&cs=' + DG)).j.me.score === 10 && (await call('/board?b=df:clear:hard&p=all')).j.rows[0].score === 250.3);
  const dbad = async (o, sc, secs, extra) => (await call('/submit', dfs(o, sc, secs, Object.assign({ token: dp[2] }, extra || {})))).j.reason || '';
  const g = { kills: 2, guns: 0, hits: 0, waves: 1, won: false, clear: null, bank: 60, flares: 0, ach: [] };
  ok('refused: wrong mode for the board', await dbad(g, 300, 60, { mode: 'easy' }) === 'wrong mode for this board');
  ok('refused: guns over kills', await dbad(Object.assign({}, g, { guns: 3 }), 300, 60) === 'more gun kills (3) than kills (2)');
  ok('refused: too fast for the kills', await dbad(Object.assign({}, g, { kills: 8, bank: 0 }), 300, 30) === '8 kills in 30.0 s, faster than one a 4 s');
  ok('refused: score over the formula cap', await dbad(g, 400, 60) === 'dogfight score 400 over the 320 its stats allow');
  ok('refused: a win with 9 kills', await dbad(Object.assign({}, win, { kills: 9 }), 1600, 251) === 'a win needs 10 kills, 4 waves and under 3 hits');
  ok('refused: a clear time without a win', await dbad(Object.assign({}, g, { clear: 100 }), 300, 120) === 'clear time without a win');
  ok('refused: not the F-16', await dbad(g, 300, 60, { ac: 'cessna' }) === 'dogfight flown in cessna, not the F-16');
  ok('refused: an inconsistent achievement (Ace with 2 kills)', await dbad(Object.assign({}, g, { ach: ['ace'] }), 300, 60) === 'Ace claimed with 2 kills');
  ok('refused: no stats', await dbad(undefined, 300, 60) === 'dogfight run without its stats');
  ok('refused: a direct submission to a fan out board', (await dbad(g, 2, 60, { board: 'df:kills:hard' })).startsWith('the dogfight writes df:kills:hard'));
  ok('refused: banked seconds the waves cannot hold', await dbad(Object.assign({}, g, { bank: 85 }), 250, 60) === 'banked 85 s, too many for 1 waves and 2 kills');
  // real tokens: the wall time since the token must cover the shortest fight the stats allow
  const tooSoon = await call('/submit', dfs({ kills: 3, guns: 0, hits: 0, waves: 1, won: false, clear: null, bank: 60, flares: 0, ach: [] }, 400, 60, { board: 'df:score:easy', mode: 'easy', token: tE.token }));
  ok('refused: submitted too soon after its token', (tooSoon.j.reason || '').startsWith('submitted '), JSON.stringify(tooSoon.j));
  await sleep(Math.max(0, 23500 - (Date.now() - tWait)));
  const soon5 = await call('/submit', dfs({ kills: 5, guns: 0, hits: 0, waves: 2, won: false, clear: null, bank: 40, flares: 0, ach: [] }, 580, 60, { board: 'df:score:easy', mode: 'easy', token: tE.token }));
  ok('refused: 5 kills submitted 23 s after the token (a 40 s fight at least)', (soon5.j.reason || '').endsWith('under the 40 s that fight needs'), JSON.stringify(soon5.j));
  const e1 = await call('/submit', dfs({ kills: 2, guns: 1, hits: 0, waves: 1, won: false, clear: null, bank: 60, flares: 0, ach: ['guns'] }, 420, 40, { board: 'df:score:easy', mode: 'easy', token: tE.token }));
  ok('an Easy run goes to df:score:easy (and its own kills and guns boards)', e1.s === 200 && e1.j.board === 'df:score:easy' && e1.j.mode === 'easy' && e1.j.rank === 1 && e1.j.df.guns.pb && e1.j.ach.length === 0, JSON.stringify(e1.j));
  const ez = await call('/board?b=df:kills:easy&p=all&cs=' + DG);
  ok('the Easy kills board has it, the Hard one is separate', ez.j.rows.length === 1 && ez.j.rows[0].score === 2 && ez.j.rows[0].mode === 'easy' && (await call('/board?b=df:kills:hard&p=all')).j.rows.every(r => r.mode === 'hard'), JSON.stringify(ez.j.rows));
  const hEz = await call('/submit', dfs({ kills: 3, guns: 0, hits: 0, waves: 1, won: false, clear: null, bank: 60, flares: 0, ach: [] }, 420, 40, { board: 'df:score:easy', mode: 'easy', token: tH.token }));
  ok('a run started Hard that went Easy goes to the Easy board on its Hard token', hEz.s === 200 && hEz.j.board === 'df:score:easy', JSON.stringify(hEz.j));
  // the daily on a dogfight day (forced locally with the header): needs df, capped at half the formula (+2)
  if (!LIVE) {
    dfHdr = '1';
    const dsub = (sc, o, extra = {}) => call('/submit', Object.assign({ board: 'daily', mode: 'hard', score: sc, secs: 40, ac: 'f16', wx: 'day', when: Date.now(), token: dd.token, df: o }, extra, eg));
    const three = { kills: 3, guns: 0, hits: 0, waves: 1, won: false, clear: null, bank: 60, flares: 0, ach: [] };
    ok('dogfight day: a daily without df refused', (await dsub(200, undefined)).j.reason === 'the daily is a dogfight today: its stats are missing');
    ok('dogfight day: a daily over half the formula refused', (await dsub(300, three)).j.reason === 'dogfight score 600 over the 420 its stats allow');
    const dok = await dsub(210, three);
    ok('dogfight day: the daily accepted (no flight path), no fan out', dok.s === 200 && dok.j.board === 'daily' && !dok.j.df && Array.isArray(dok.j.ach), JSON.stringify(dok.j));
    dfHdr = '0';
    ok('a landing day: a daily carrying df refused', (await dsub(210, three, { token: 'x.y' })).j.reason === 'dogfight stats on a landing daily');
  } else if (realDf) ok('live dogfight day: a daily without df refused', (await call('/submit', Object.assign({ board: 'daily', mode: 'hard', score: 200, secs: 40, ac: 'f16', when: Date.now(), token: 'x.y' }, eg))).j.reason === 'the daily is a dogfight today: its stats are missing');
  else ok('live landing day: a daily carrying df refused', (await call('/submit', Object.assign({ board: 'daily', mode: 'hard', score: 200, secs: 40, ac: 'f16', when: Date.now(), token: 'x.y', df: { kills: 1 } }, eg))).j.reason === 'dogfight stats on a landing daily');
  ok('flagged: the dogfight refusals are on record', ['wrong mode for this board', 'more gun kills (3) than kills (2)', 'clear time without a win'].every(r => sql(`SELECT reason FROM flagged WHERE created>=${T0} AND callsign='${DG}'`).some(x => x.reason === r)));

  // ---- rate limit: 30 submissions an hour per device
  if (!LIVE) {
  let last = null;
  for (let i = 0; i < 31; i++) last = await call('/submit', Object.assign({ board: 'lesson:stall', mode: 'hard', score: 1, secs: 5, ac: 'cessna', when: Date.now(), token: 'x.y' }, you));
  ok('31st submission in an hour refused as rate limited', last.s === 429 && last.j.reason.startsWith('over 30'), JSON.stringify(last.j));
  }

  // ---- every refusal is on record
  const fl = sql(`SELECT reason FROM flagged WHERE created>=${T0} AND callsign IN ('${A}','${B}','${C}','F4GG0T','OHRABAH')`);
  const reasons = fl.map(r => r.reason);
  for (const want of ['no valid run token', 'token already used', 'score 101 outside 0 to 100', 'ghost path missing'].concat(landDay ? ['second official daily attempt'] : []).concat(['profanity: F4GG0T', 'reserved callsign without the secret', 'profanity on rename: SH1THEAD']))
    ok('flagged: ' + want, reasons.includes(want));
  ok('scores table has the callsign, mode, run time, aircraft, weather, token',
    sql(`SELECT * FROM scores WHERE callsign='${A}' AND board='lesson:stall' AND mode='hard'`).every(r => r.mode === 'hard' && r.secs === 3.5 && r.ac === 'cessna' && r.wx === 'day' && r.token));
  ok('players table stores only hashes', sql(`SELECT key_hash, rec_hash FROM players WHERE callsign='${A}'`).every(r => r.key_hash !== nk && !r.rec_hash.includes(' ')));

  if (LIVE) {
    const ids = sql(`SELECT id FROM players WHERE callsign IN (${made.map(c => "'" + c + "'").join(',')})`).map(r => r.id).join(',') || '0';
    sql(`DELETE FROM achs WHERE player_id IN (${ids}); DELETE FROM ghosts WHERE player_id IN (${ids}); DELETE FROM scores WHERE player_id IN (${ids}); DELETE FROM tokens WHERE player_id IN (${ids}); DELETE FROM players WHERE id IN (${ids}); DELETE FROM flagged WHERE created>=${T0} AND callsign IN (${made.concat(['F4GG0T', 'OHRABAH']).map(c => "'" + c + "'").join(',')}); DELETE FROM hits WHERE ts>=${T0}`);
    console.log('  cleaned up test players ' + made.join(' '));
  }
}
main().catch(e => { console.log('  FAIL crashed: ' + (e.stack || e)); fails++; }).finally(() => {
  stopDev();
  console.log(fails ? fails + ' FAILS' : 'all passed');
  process.exit(fails ? 1 : 0);
});
