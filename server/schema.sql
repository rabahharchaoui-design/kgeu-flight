-- Pocket Flight Sim leaderboards, Cloudflare D1 (SQLite).
-- Apply: npx wrangler d1 execute pfs-scores --remote --file=schema.sql
CREATE TABLE IF NOT EXISTS players(
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  callsign  TEXT NOT NULL UNIQUE,          -- 3 to 12 of A-Z 0-9, always upper case
  key_hash  TEXT NOT NULL,                 -- HMAC-SHA256(pepper, device key); the key itself is never stored
  rec_hash  TEXT NOT NULL,                 -- HMAC-SHA256(pepper, 4 word recovery code)
  created   INTEGER NOT NULL,              -- ms since epoch
  xp        INTEGER NOT NULL DEFAULT 0,
  creator   INTEGER NOT NULL DEFAULT 0,    -- 1 for the reserved OHRABAH callsign
  renamed   INTEGER NOT NULL DEFAULT 0,    -- ms of the last callsign change, 0 = never
  banned    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS scores(
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  board     TEXT NOT NULL,
  player_id INTEGER NOT NULL,
  callsign  TEXT NOT NULL,                 -- kept in step with players.callsign on a rename
  mode      TEXT NOT NULL,                 -- 'easy' or 'hard'
  score     REAL NOT NULL,
  secs      REAL NOT NULL,                 -- run time
  ac        TEXT,                          -- aircraft id
  wx        TEXT,                          -- weather: time of day and wind
  day       INTEGER NOT NULL,              -- UTC yyyymmdd the run was flown
  created   INTEGER NOT NULL,              -- ms, when the run ended
  token     TEXT NOT NULL UNIQUE           -- the run token id, used once
);
CREATE INDEX IF NOT EXISTS scores_bm ON scores(board, mode, created);
CREATE INDEX IF NOT EXISTS scores_p ON scores(player_id);
CREATE TABLE IF NOT EXISTS ghosts(
  score_id  INTEGER PRIMARY KEY,
  board     TEXT NOT NULL,
  mode      TEXT NOT NULL,
  player_id INTEGER NOT NULL,
  score     REAL NOT NULL,
  secs      REAL NOT NULL,
  ac        TEXT,
  path      TEXT NOT NULL,                 -- compressed flight path, see LEADERBOARD.md
  created   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ghosts_bm ON ghosts(board, mode);
CREATE TABLE IF NOT EXISTS flagged(
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  created   INTEGER NOT NULL,
  callsign  TEXT,
  ip        TEXT,
  board     TEXT,
  reason    TEXT NOT NULL,
  payload   TEXT
);
CREATE TABLE IF NOT EXISTS tokens(
  jti       TEXT PRIMARY KEY,
  player_id INTEGER NOT NULL,
  board     TEXT NOT NULL,                 -- '*' for an offline pool token
  mode      TEXT NOT NULL,
  t0        INTEGER NOT NULL,
  day       INTEGER NOT NULL,
  used      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS tokens_pb ON tokens(player_id, board, day);
CREATE TABLE IF NOT EXISTS hits(
  kind      TEXT NOT NULL,
  who       TEXT NOT NULL,
  ts        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS hits_k ON hits(kind, who, ts);
-- achievements that gave rank XP (the dogfight's Ace, Guns Kill, Flare Save, Untouchable): once per player, ever
CREATE TABLE IF NOT EXISTS achs(
  player_id INTEGER NOT NULL,
  ach       TEXT NOT NULL,
  created   INTEGER NOT NULL,
  PRIMARY KEY(player_id, ach)
);
