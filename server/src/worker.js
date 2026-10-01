// Pocket Flight Sim leaderboards: one Cloudflare Worker in front of one D1 database.
// The browser never touches the database. Every write comes through here and is
// checked: the device key, a single use signed run token, the board's legal range
// and shortest possible time, the flight path for races, and a rate limit. Anything
// refused is written to the flagged table with the reason, never dropped silently.
import { BOARDS, boardOf, AC_VMAX, RANKS, rankOf, xpFor } from './boards.js';
import { cleanCallsign, nameProblem } from './names.js';
import { RECOVERY_WORDS } from './words.js';

const ORIGINS = ['https://rabahharchaoui-design.github.io', 'http://localhost:8765'];
const HOUR = 3600e3, DAY = 24 * HOUR;
const SUBMITS_PER_HOUR = 30;
const QUEUE_MAX_AGE = DAY;            // a run queued offline stays valid this long
const TOKEN_MAX_AGE = 2 * DAY;        // a token must be spent within this
const POOL_PER_DAY = 12;              // offline pool tokens a player can draw per UTC day
const RENAME_EVERY = 30 * DAY;

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const cors = ORIGINS.includes(origin) ? {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
      'Vary': 'Origin'
    } : { 'Vary': 'Origin' };
    if (req.method === 'OPTIONS') return new Response(null, { status: ORIGINS.includes(origin) ? 204 : 403, headers: cors });
    const url = new URL(req.url);
    const ctx = { env, req, url, ip: req.headers.get('CF-Connecting-IP') || 'local', now: Date.now(), origin };
    let res;
    try {
      // writes only from the game's own pages; reads are public but still CORS locked
      if (req.method === 'POST' && !ORIGINS.includes(origin)) res = json({ error: 'origin' }, 403);
      else res = await route(ctx);
    } catch (e) {
      res = json({ error: 'server', detail: String(e && e.message || e).slice(0, 200) }, 500);
    }
    for (const [k, v] of Object.entries(cors)) res.headers.set(k, v);
    return res;
  }
};

async function route(c) {
  const p = c.url.pathname.replace(/\/+$/, '') || '/';
  const g = c.req.method === 'GET', po = c.req.method === 'POST';
  if (g && p === '/health') return json({ ok: true, now: c.now, day: dayOf(c.now) });
  if (g && p === '/name') return nameCheck(c);
  if (g && p === '/board') return board(c);
  if (g && p === '/fame') return fame(c);
  if (g && p === '/ghost') return ghost(c);
  if (g && p === '/ranks') return json({ ranks: RANKS, boards: Object.keys(BOARDS) });
  if (po) {
    const body = await c.req.json().catch(() => null);
    if (!body || typeof body !== 'object') return json({ error: 'body' }, 400);
    c.body = body;
    if (p === '/signup') return signup(c);
    if (p === '/restore') return restore(c);
    if (p === '/me') return me(c);
    if (p === '/rename') return rename(c);
    if (p === '/token') return token(c);
    if (p === '/pool') return pool(c);
    if (p === '/submit') return submit(c);
  }
  return json({ error: 'not found' }, 404);
}

// ---------------------------------------------------------------- helpers
function json(o, status = 200) {
  return new Response(JSON.stringify(o), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
}
function dayOf(ms) { const d = new Date(ms); return d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate(); }
function dayStart(ms) { const d = new Date(ms); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()); }
function weekStart(ms) { const s = dayStart(ms), wd = (new Date(s).getUTCDay() + 6) % 7; return s - wd * DAY; }   // Monday 00:00 UTC
const enc = new TextEncoder();
function b64u(bytes) { let s = ''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function unb64u(s) { s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; const b = atob(s), o = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) o[i] = b.charCodeAt(i); return o; }
async function hmac(secret, msg) {
  const k = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', k, enc.encode(msg)));
}
async function hashOf(env, s) { return b64u(await hmac(env.PEPPER || 'pepper', s)); }
function safeEq(a, b) { if (a.length !== b.length) return false; let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i); return r === 0; }
function randHex(n) { const a = new Uint8Array(n); crypto.getRandomValues(a); return [...a].map(x => x.toString(16).padStart(2, '0')).join(''); }
const normCode = s => String(s || '').toUpperCase().replace(/[^A-Z]+/g, ' ').trim();

async function flag(c, reason, extra = {}) {
  const payload = JSON.stringify(Object.assign({}, c.body || {}, { path: undefined }, extra)).slice(0, 2000);
  await c.env.DB.prepare('INSERT INTO flagged(created,callsign,ip,board,reason,payload) VALUES(?,?,?,?,?,?)')
    .bind(c.now, (c.player && c.player.callsign) || (c.body && String(c.body.cs || '').slice(0, 20)) || null, c.ip,
      (c.body && String(c.body.board || '').slice(0, 40)) || null, reason, payload).run();
}
async function reject(c, reason, status = 400, extra) { await flag(c, reason, extra); return json({ error: 'rejected', reason }, status); }

// rate limit: at most n events of this kind per window for this subject
async function tooMany(c, kind, who, n, win = HOUR) {
  const r = await c.env.DB.prepare('SELECT COUNT(*) n FROM hits WHERE kind=? AND who=? AND ts>?').bind(kind, who, c.now - win).first();
  return r.n >= n;
}
function hit(c, kind, who) { return c.env.DB.prepare('INSERT INTO hits(kind,who,ts) VALUES(?,?,?)').bind(kind, who, c.now); }

async function auth(c) {
  const cs = cleanCallsign(c.body.cs), key = String(c.body.key || '');
  if (!cs || key.length < 32) return null;
  const p = await c.env.DB.prepare('SELECT * FROM players WHERE callsign=?').bind(cs).first();
  if (!p || p.banned) return null;
  if (!safeEq(p.key_hash, await hashOf(c.env, 'k:' + key))) return null;
  c.player = p;
  return p;
}
function pub(p) { return { cs: p.callsign, xp: p.xp, rank: rankOf(p.xp), creator: !!p.creator, created: p.created, renamed: p.renamed, renameAt: p.renamed ? p.renamed + RENAME_EVERY : 0 }; }

// ---------------------------------------------------------------- callsigns
async function nameCheck(c) {
  const raw = c.url.searchParams.get('cs') || '';
  if (await tooMany(c, 'name', c.ip, 400)) return json({ error: 'slow down' }, 429);
  await hit(c, 'name', c.ip).run();
  const cs = cleanCallsign(raw), why = nameProblem(raw);
  if (why === 'reserved') return json({ cs, free: false, reserved: true, reason: 'reserved' });
  if (why) return json({ cs, free: false, reason: why });
  const p = await c.env.DB.prepare('SELECT id FROM players WHERE callsign=?').bind(cs).first();
  return json({ cs, free: !p, reason: p ? 'taken' : null });
}

function recoveryCode() {
  const a = new Uint16Array(4); crypto.getRandomValues(a);
  return [...a].map(x => RECOVERY_WORDS[x % RECOVERY_WORDS.length]).join(' ');
}

async function signup(c) {
  const raw = String(c.body.cs || ''), cs = cleanCallsign(raw), key = String(c.body.key || '');
  if (await tooMany(c, 'signup', c.ip, 20)) return reject(c, 'signup rate', 429);
  await hit(c, 'signup', c.ip).run();
  if (key.length < 32 || key.length > 128) return json({ error: 'key' }, 400);
  const why = nameProblem(raw);
  let creator = 0;
  if (why === 'reserved') {
    const sec = String(c.body.secret || '');
    if (cs !== 'OHRABAH' || !c.env.OHRABAH_SECRET || !safeEq(sec, c.env.OHRABAH_SECRET)) return reject(c, 'reserved callsign without the secret', 403);
    creator = 1;
  } else if (why) {
    if (why === 'profanity') return reject(c, 'profanity: ' + cs, 400);
    return json({ error: 'name', reason: why }, 400);
  }
  if (await c.env.DB.prepare('SELECT id FROM players WHERE callsign=?').bind(cs).first()) return json({ error: 'name', reason: 'taken' }, 409);
  const code = recoveryCode();
  await c.env.DB.prepare('INSERT INTO players(callsign,key_hash,rec_hash,created,xp,creator) VALUES(?,?,?,?,0,?)')
    .bind(cs, await hashOf(c.env, 'k:' + key), await hashOf(c.env, 'r:' + normCode(code)), c.now, creator).run();
  const p = await c.env.DB.prepare('SELECT * FROM players WHERE callsign=?').bind(cs).first();
  return json(Object.assign(pub(p), { recovery: code }));
}

// a new device takes over a callsign with its 4 word code; the old device key stops working
async function restore(c) {
  if (await tooMany(c, 'restore', c.ip, 10)) return reject(c, 'restore rate', 429);
  await hit(c, 'restore', c.ip).run();
  const cs = cleanCallsign(c.body.cs), key = String(c.body.key || ''), code = normCode(c.body.code);
  if (!cs || key.length < 32 || key.length > 128 || code.split(' ').length !== 4) return json({ error: 'bad request' }, 400);
  const p = await c.env.DB.prepare('SELECT * FROM players WHERE callsign=?').bind(cs).first();
  if (!p || p.banned || !safeEq(p.rec_hash, await hashOf(c.env, 'r:' + code))) return reject(c, 'restore: wrong code for ' + cs, 403);
  await c.env.DB.prepare('UPDATE players SET key_hash=? WHERE id=?').bind(await hashOf(c.env, 'k:' + key), p.id).run();
  return json(pub(p));
}

async function me(c) {
  const p = await auth(c);
  if (!p) return json({ error: 'auth' }, 401);
  return json(pub(p));
}

async function rename(c) {
  const p = await auth(c);
  if (!p) return reject(c, 'rename: bad key', 401);
  if (p.creator) return json({ error: 'name', reason: 'the creator callsign stays' }, 400);
  if (p.renamed && c.now - p.renamed < RENAME_EVERY) return json({ error: 'name', reason: 'too soon', renameAt: p.renamed + RENAME_EVERY }, 429);
  const raw = String(c.body.to || ''), cs = cleanCallsign(raw), why = nameProblem(raw);
  if (why === 'profanity') return reject(c, 'profanity on rename: ' + cs, 400);
  if (why) return json({ error: 'name', reason: why }, 400);
  if (await c.env.DB.prepare('SELECT id FROM players WHERE callsign=?').bind(cs).first()) return json({ error: 'name', reason: 'taken' }, 409);
  // old scores follow the new name
  await c.env.DB.batch([
    c.env.DB.prepare('UPDATE players SET callsign=?, renamed=? WHERE id=?').bind(cs, c.now, p.id),
    c.env.DB.prepare('UPDATE scores SET callsign=? WHERE player_id=?').bind(cs, p.id)
  ]);
  const q = await c.env.DB.prepare('SELECT * FROM players WHERE id=?').bind(p.id).first();
  return json(pub(q));
}

// ---------------------------------------------------------------- run tokens
async function sign(c, payload) {
  const body = b64u(enc.encode(JSON.stringify(payload)));
  return body + '.' + b64u(await hmac(c.env.TOKEN_SECRET || 'token', body));
}
async function verify(c, tok) {
  const [body, sig] = String(tok || '').split('.');
  if (!body || !sig) return null;
  if (!safeEq(sig, b64u(await hmac(c.env.TOKEN_SECRET || 'token', body)))) return null;
  try { return JSON.parse(new TextDecoder().decode(unb64u(body))); } catch (e) { return null; }
}

// at run start: a token for this board and mode, good once. The daily challenge has one
// official attempt per UTC day; after that the game is told to fly it as practice.
async function token(c) {
  const p = await auth(c);
  if (!p) return json({ error: 'auth' }, 401);
  const b = String(c.body.board || ''), mode = c.body.mode === 'easy' ? 'easy' : 'hard';
  if (!boardOf(b)) return reject(c, 'token for unknown board', 400);
  if (await tooMany(c, 'token', 'p:' + p.id, 240)) return json({ error: 'slow down' }, 429);
  const day = dayOf(c.now);
  if (b === 'daily') {
    const had = await c.env.DB.prepare("SELECT 1 FROM tokens WHERE player_id=? AND board='daily' AND day=? UNION SELECT 1 FROM scores WHERE player_id=? AND board='daily' AND day=?")
      .bind(p.id, day, p.id, day).first();
    if (had) return json({ practice: true, day });
  }
  const jti = randHex(12);
  await c.env.DB.batch([
    c.env.DB.prepare('INSERT INTO tokens(jti,player_id,board,mode,t0,day) VALUES(?,?,?,?,?,?)').bind(jti, p.id, b, mode, c.now, day),
    hit(c, 'token', 'p:' + p.id)
  ]);
  return json({ token: await sign(c, { j: jti, p: p.id, b, m: mode, t: c.now }), t0: c.now, day });
}

// offline pool: a few tokens not tied to a board, drawn while online and spent on runs
// flown without a connection. The run's own clock is all the server has for those.
async function pool(c) {
  const p = await auth(c);
  if (!p) return json({ error: 'auth' }, 401);
  const n = Math.max(0, Math.min(5, c.body.n | 0));
  const day = dayOf(c.now);
  const r = await c.env.DB.prepare("SELECT COUNT(*) n FROM tokens WHERE player_id=? AND board='*' AND day=?").bind(p.id, day).first();
  const k = Math.min(n, POOL_PER_DAY - r.n), out = [], st = [];
  for (let i = 0; i < k; i++) {
    const jti = randHex(12);
    st.push(c.env.DB.prepare("INSERT INTO tokens(jti,player_id,board,mode,t0,day) VALUES(?,?,'*','*',?,?)").bind(jti, p.id, c.now, day));
    out.push(await sign(c, { j: jti, p: p.id, b: '*', m: '*', t: c.now }));
  }
  if (st.length) await c.env.DB.batch(st);
  return json({ tokens: out });
}

// ---------------------------------------------------------------- ghosts
// path = {v:1, hz:5, o:[x,y,z] metres, n, z:1 if deflate-raw, d: base64 of little endian
// int16 frames [dx,dy,dz in 0.5 m, yaw,pitch,roll in pi/32767]}
async function decodePath(path) {
  if (!path || path.v !== 1 || path.hz !== 5 || !Array.isArray(path.o) || typeof path.d !== 'string' || path.d.length > 400000) return null;
  let bytes = unb64u(path.d);
  if (path.z) {
    const ds = new DecompressionStream('deflate-raw');
    const out = new Response(new Blob([bytes]).stream().pipeThrough(ds));
    bytes = new Uint8Array(await out.arrayBuffer());
  }
  if (bytes.length % 12) return null;
  const n = bytes.length / 12, dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (n !== path.n) return null;
  const pts = [];
  let x = +path.o[0], y = +path.o[1], z = +path.o[2];
  if (![x, y, z].every(Number.isFinite)) return null;
  for (let i = 0; i < n; i++) {
    x += dv.getInt16(i * 12, true) * 0.5; y += dv.getInt16(i * 12 + 2, true) * 0.5; z += dv.getInt16(i * 12 + 4, true) * 0.5;
    pts.push([x, y, z]);
  }
  return pts;
}
function pathProblem(pts, secs, ac) {
  if (!pts || pts.length < 2) return 'ghost path missing';
  const dur = (pts.length - 1) / 5;
  if (Math.abs(dur - secs) > Math.max(3, secs * 0.08)) return 'ghost path is ' + dur.toFixed(1) + ' s against a ' + secs.toFixed(1) + ' s run';
  const vmax = AC_VMAX[ac] || 600;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], v = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]) * 5;
    if (v > vmax) return 'ghost path at ' + Math.round(v) + ' m/s, over the ' + ac + ' limit of ' + vmax;
  }
  return null;
}

// ---------------------------------------------------------------- submit
async function submit(c) {
  const B = c.body;
  const p = await auth(c);
  if (!p) return reject(c, 'submit: bad callsign or device key', 401);
  if (await tooMany(c, 'submit', 'p:' + p.id, SUBMITS_PER_HOUR) || await tooMany(c, 'submit', 'ip:' + c.ip, SUBMITS_PER_HOUR))
    return reject(c, 'over ' + SUBMITS_PER_HOUR + ' submissions an hour', 429);
  await c.env.DB.batch([hit(c, 'submit', 'p:' + p.id), hit(c, 'submit', 'ip:' + c.ip)]);

  const b = String(B.board || ''), bd = boardOf(b), mode = B.mode === 'easy' ? 'easy' : B.mode === 'hard' ? 'hard' : null;
  if (!bd) return reject(c, 'unknown board');
  if (!mode) return reject(c, 'bad mode');
  const score = +B.score, secs = +B.secs, when = +B.when || c.now;
  if (!Number.isFinite(score) || !Number.isFinite(secs)) return reject(c, 'score or time not a number');

  // the token: genuine, this player's, this board, unused, fresh
  const t = await verify(c, B.token);
  if (!t) return reject(c, 'no valid run token');
  if (t.p !== p.id) return reject(c, 'token belongs to another player');
  if (t.b !== b && t.b !== '*') return reject(c, 'token was issued for ' + t.b);
  if (t.m === 'easy' && mode === 'hard') return reject(c, 'run started in Easy, submitted as Hard');
  const row = await c.env.DB.prepare('SELECT * FROM tokens WHERE jti=?').bind(t.j).first();
  if (!row) return reject(c, 'token not on record');
  if (row.used) return reject(c, 'token already used');
  if (c.now - t.t > TOKEN_MAX_AGE) return reject(c, 'token expired');
  if (when > c.now + 5 * 60e3) return reject(c, 'run ends in the future');
  if (c.now - when > QUEUE_MAX_AGE) return reject(c, 'queued run older than 24 hours');
  if (t.b !== '*' && when < t.t - 5 * 60e3) return reject(c, 'run ended before its token was issued');

  // impossible results
  if (secs < bd.minSecs) return reject(c, 'run of ' + secs.toFixed(1) + ' s is under the ' + bd.minSecs + ' s minimum');
  if (secs > 4 * 3600) return reject(c, 'run over 4 hours');
  if (t.b !== '*' && (c.now - t.t) / 1000 < bd.minSecs - 2) return reject(c, 'submitted ' + ((c.now - t.t) / 1000).toFixed(1) + ' s after its token, under the ' + bd.minSecs + ' s minimum');
  if (score < bd.min || score > bd.max) return reject(c, 'score ' + score + ' outside ' + bd.min + ' to ' + bd.max);
  if (bd.time && Math.abs(score - secs) > 1) return reject(c, 'time score does not match the run time');
  if (bd.parMax && score > 1000 * Math.min(1.5, bd.parMax / secs) + 1) return reject(c, 'points too high for a ' + Math.round(secs) + ' s run');
  const ac = String(B.ac || '').slice(0, 12), wx = String(B.wx || '').slice(0, 40);
  if (!AC_VMAX[ac]) return reject(c, 'unknown aircraft');

  // races and time trials carry their flight path
  let pts = null;
  if (bd.ghost) {
    try { pts = await decodePath(B.path); } catch (e) { pts = null; }
    const why = pathProblem(pts, secs, ac);
    if (why) return reject(c, why);
  }

  // the daily challenge counts once a day
  const day = dayOf(when);
  if (b === 'daily') {
    const other = await c.env.DB.prepare("SELECT 1 FROM scores WHERE player_id=? AND board='daily' AND day=?").bind(p.id, day).first();
    if (other) return reject(c, 'second official daily attempt');
    if (t.b === '*') {
      const tk = await c.env.DB.prepare("SELECT 1 FROM tokens WHERE player_id=? AND board='daily' AND day=?").bind(p.id, day).first();
      if (tk) return reject(c, 'second official daily attempt');
    } else if (row.day !== day) return reject(c, 'daily token from another day');
  }

  const cmp = bd.dir > 0 ? '>' : '<', agg = bd.dir > 0 ? 'MAX' : 'MIN';
  // the boards merge Easy and Hard for display, so a personal best is against both modes
  const prev = await c.env.DB.prepare(`SELECT ${agg}(score) s FROM scores WHERE board=? AND player_id=?`).bind(b, p.id).first();
  const pb = prev.s === null || (bd.dir > 0 ? score > prev.s : score < prev.s);

  const ins = await c.env.DB.batch([
    c.env.DB.prepare('UPDATE tokens SET used=1 WHERE jti=? AND used=0').bind(t.j),
    c.env.DB.prepare('INSERT INTO scores(board,player_id,callsign,mode,score,secs,ac,wx,day,created,token) VALUES(?,?,?,?,?,?,?,?,?,?,?)')
      .bind(b, p.id, p.callsign, mode, score, secs, ac, wx, day, Math.min(when, c.now), t.j)
  ]);
  if (!ins[0].meta.changes) return reject(c, 'token already used');
  const sid = ins[1].meta.last_row_id;

  const rk = await rankFor(c, b, 0, pb ? score : prev.s);
  const top10 = pb && rk.rank <= 10;
  const gain = xpFor(bd, score, mode, pb, top10);
  await c.env.DB.prepare('UPDATE players SET xp=xp+? WHERE id=?').bind(gain, p.id).run();

  if (pts && top10) {
    const raw = JSON.stringify(B.path);
    await c.env.DB.prepare('INSERT OR REPLACE INTO ghosts(score_id,board,mode,player_id,score,secs,ac,path,created) VALUES(?,?,?,?,?,?,?,?,?)')
      .bind(sid, b, mode, p.id, score, secs, ac, raw, c.now).run();
    // only this player's best stays, and only the top 10 of the board
    await c.env.DB.prepare('DELETE FROM ghosts WHERE board=? AND mode=? AND player_id=? AND score_id<>?').bind(b, mode, p.id, sid).run();
    await c.env.DB.prepare(`DELETE FROM ghosts WHERE board=? AND mode=? AND score_id NOT IN (SELECT score_id FROM ghosts WHERE board=? AND mode=? ORDER BY score ${bd.dir > 0 ? 'DESC' : 'ASC'}, created ASC LIMIT 10)`)
      .bind(b, mode, b, mode).run();
  }
  const today = await rankFor(c, b, dayStart(c.now), null, p.id);
  return json({ ok: true, id: sid, board: b, mode, score, pb, best: pb ? score : prev.s, rank: rk.rank, total: rk.total,
    top10, today: today, xp: p.xp + gain, gain, rankName: rankOf(p.xp + gain).name });
}

// rank of a best score among every player's best on this board since `since`, Easy and Hard
// together (each player's single best run across both modes counts once)
async function rankFor(c, b, since, best, pid) {
  const bd = boardOf(b), agg = bd.dir > 0 ? 'MAX' : 'MIN', cmp = bd.dir > 0 ? '>' : '<';
  let mode = null;
  if (best === null || best === undefined) {
    if (!pid) return { rank: 0, total: 0 };
    // SQLite returns `mode` from the row that holds the MAX or MIN
    const r = await c.env.DB.prepare(`SELECT ${agg}(score) s, mode FROM scores WHERE board=? AND created>=? AND player_id=?`).bind(b, since, pid).first();
    best = r.s; mode = r.mode;
  }
  const r = await c.env.DB.prepare(`WITH bb AS (SELECT player_id, ${agg}(score) s FROM scores WHERE board=? AND created>=? GROUP BY player_id)
    SELECT (SELECT COUNT(*) FROM bb WHERE s ${cmp} ?) + 1 AS rank, (SELECT COUNT(*) FROM bb) AS total`).bind(b, since, best === null ? 0 : best).first();
  return { rank: best === null ? 0 : r.rank, total: r.total, best, mode };
}

// ---------------------------------------------------------------- reads
// one list per board: each player's best run across Easy and Hard, the row carries its mode.
// Submission, tokens and checks stay per mode; only the display merges. `m` is ignored.
async function board(c) {
  const q = c.url.searchParams, b = q.get('b') || '', bd = boardOf(b);
  if (!bd) return json({ error: 'unknown board' }, 404);
  const per = q.get('p') === 'today' ? 'today' : q.get('p') === 'week' ? 'week' : 'all';
  const since = per === 'today' ? dayStart(c.now) : per === 'week' ? weekStart(c.now) : 0;
  const agg = bd.dir > 0 ? 'MAX' : 'MIN', ord = bd.dir > 0 ? 'DESC' : 'ASC';
  // SQLite returns the other columns from the row that holds the MAX or MIN
  const rows = (await c.env.DB.prepare(`SELECT s.player_id, ${agg}(s.score) score, s.secs, s.ac, s.mode, s.created, p.callsign cs, p.xp, p.creator
      FROM scores s JOIN players p ON p.id=s.player_id WHERE s.board=? AND s.created>=? AND p.banned=0
      GROUP BY s.player_id ORDER BY score ${ord}, s.created ASC LIMIT 50`).bind(b, since).all()).results;
  let r = 0, last = null;
  const out = rows.map((x, i) => { if (x.score !== last) { r = i + 1; last = x.score; }
    return { r, cs: x.cs, score: x.score, secs: x.secs, ac: x.ac, mode: x.mode === 'easy' ? 'easy' : 'hard', xp: x.xp, rank: rankOf(x.xp).name, creator: !!x.creator, when: x.created }; });
  const cnt = await c.env.DB.prepare('SELECT COUNT(DISTINCT player_id) n FROM scores WHERE board=? AND created>=?').bind(b, since).first();
  let meRow = null;
  const cs = q.get('cs') ? String(q.get('cs')).toUpperCase() : '';
  if (cs) {
    const p = await c.env.DB.prepare('SELECT id,callsign,xp,creator FROM players WHERE callsign=?').bind(cs).first();
    if (p) {
      const rk = await rankFor(c, b, since, null, p.id);
      if (rk.best !== null && rk.best !== undefined) meRow = { r: rk.rank, cs: p.callsign, score: rk.best, mode: rk.mode === 'easy' ? 'easy' : 'hard', xp: p.xp, rank: rankOf(p.xp).name, creator: !!p.creator };
    }
  }
  const gh = bd.ghost ? await c.env.DB.prepare(`SELECT g.score, g.ac, p.callsign cs FROM ghosts g JOIN players p ON p.id=g.player_id WHERE g.board=? ORDER BY g.score ${ord}, g.created ASC LIMIT 1`).bind(b).first() : null;
  return json({ board: b, mode: 'all', period: per, dir: bd.dir, total: cnt.n, rows: out, me: meRow, ghost: gh || null, now: c.now, day: dayOf(c.now) });
}

// the best ghost on the board, Easy or Hard (`m` is ignored)
async function ghost(c) {
  const q = c.url.searchParams, b = q.get('b') || '', bd = boardOf(b);
  if (!bd || !bd.ghost) return json({ error: 'no ghosts on this board' }, 404);
  const ord = bd.dir > 0 ? 'DESC' : 'ASC';
  const g = await c.env.DB.prepare(`SELECT g.score, g.secs, g.ac, g.path, p.callsign cs, p.creator FROM ghosts g JOIN players p ON p.id=g.player_id WHERE g.board=? ORDER BY g.score ${ord}, g.created ASC LIMIT 1`).bind(b).first();
  if (!g) return json({ ghost: null });
  return json({ ghost: { cs: g.cs, creator: !!g.creator, score: g.score, secs: g.secs, ac: g.ac, path: JSON.parse(g.path) } });
}

// fame in the world: today's daily #1 on the billboard, the top 3 by XP on the hangar wall
async function fame(c) {
  const day = dayOf(c.now);
  const d = await c.env.DB.prepare(`SELECT p.callsign cs, s.score, s.mode FROM scores s JOIN players p ON p.id=s.player_id
    WHERE s.board='daily' AND s.day=? AND p.banned=0 ORDER BY (s.mode='hard') DESC, s.score DESC, s.created ASC LIMIT 1`).bind(day).first();
  const top = (await c.env.DB.prepare('SELECT callsign cs, xp, creator FROM players WHERE banned=0 AND xp>0 ORDER BY xp DESC, created ASC LIMIT 3').all()).results;
  return json({ day, daily: d || null, top: top.map(x => ({ cs: x.cs, xp: x.xp, rank: rankOf(x.xp).name, creator: !!x.creator })) });
}
