// Callsign rules: 3 to 12 letters and digits, upper case. The profanity check runs
// here on the server (the game only mirrors it for a quick hint) and reads through
// leetspeak: digits and look-alike symbols map back to letters and repeated letters
// collapse, so SH1T, 5HIT and SHHIIT are all caught.
export function cleanCallsign(s) {
  const c = String(s || '').toUpperCase().trim();
  return /^[A-Z0-9]{3,12}$/.test(c) ? c : null;
}

const RESERVED = ['OHRABAH'];
const RESERVED_ALSO = ['ADMIN', 'ADMINISTRATOR', 'MODERATOR', 'SYSTEM', 'CREATOR', 'DEVELOPER', 'OFFICIAL', 'SUPPORT', 'ROOT', 'NULL', 'UNDEFINED', 'ANONYMOUS'];

// found anywhere in the name
const BAD_ANY = ['FUCK', 'FUK', 'FCUK', 'FUQ', 'SHIT', 'SHYT', 'CUNT', 'NIGG', 'NIGA', 'NIGR', 'NEGRO', 'FAGG', 'FAGOT', 'FAGS', 'DYKE', 'KIKE', 'SPIC', 'CHINK', 'GOOK', 'WETBACK', 'TRANNY',
  'RETARD', 'BITCH', 'BICH', 'WHORE', 'HOOKER', 'SLUT', 'PUSSY', 'PUSSI', 'COCK', 'DICKHEAD', 'DICKS', 'PENIS', 'VAGINA', 'BOOBS', 'BOOBIE', 'TITS', 'TITTY', 'ASSHOLE', 'ARSEHOLE', 'JACKASS', 'DUMBASS', 'BADASS', 'FATASS',
  'BASTARD', 'BOLLOCK', 'WANK', 'JIZZ', 'CUMSHOT', 'CUMMING', 'DILDO', 'BLOWJOB', 'HANDJOB', 'RIMJOB', 'ANAL', 'ANUS', 'RAPIST', 'RAPING', 'PEDO', 'PAEDO', 'MOLEST', 'INCEST', 'NAZI', 'HITLER', 'HEILH', 'KKK',
  'ISIS', 'JIHAD', 'TERRORIST', 'PORN', 'HENTAI', 'NUDES', 'MILF', 'ORGASM', 'SEXY', 'HORNY', 'BONER', 'ERECTION', 'SCROTUM', 'TESTICLE', 'SEMEN', 'SPERM', 'NUTSACK', 'SHAG', 'TWAT', 'PRICK', 'MOTHERF',
  'KILLYOU', 'SUICIDE'];
// real words that happen to contain one of the above; blanked out before the check
const ALLOW = ['COCKPIT', 'HABOOB', 'TORPEDO', 'PRICKLY', 'ANALOG', 'CANAL', 'BANAL', 'ANALYS', 'SPICE', 'SPICY', 'PEACOCK', 'HANCOCK', 'GAMECOCK', 'SCUNTHORPE',
  'URANUS', 'JANUS', 'THERAPIST', 'CONSPICU', 'SHAGGY', 'DICKENS', 'COCKATOO', 'COCKATIEL', 'WOODCOCK', 'MOSSSHAG'];
// the whole name, or the whole name less a trailing number
const BAD_EXACT = ['BOOB', 'KYS', 'ASS', 'ASSES', 'ARSE', 'CUM', 'SEX', 'RAPE', 'DICK', 'DIK', 'FAG', 'HOE', 'HOES', 'TIT', 'NUT', 'NUTS', 'PISS', 'POOP', 'CRAP', 'DAMN', 'HELL', 'GAY', 'JEW', 'NIG', 'KILL', 'DIE', 'SUCK', 'SUCKS', 'LOSER', 'IDIOT'];

const LEET = { '0': 'O', '1': 'I', '2': 'Z', '3': 'E', '4': 'A', '5': 'S', '6': 'G', '7': 'T', '8': 'B', '9': 'G' };
// every reading of the name worth checking: as typed, digits as letters (1 as I and as L),
// digits dropped, and each of those with runs of one letter squeezed to one
function readings(c) {
  const out = new Set([c]);
  const asI = c.replace(/[0-9]/g, d => LEET[d]), asL = c.replace(/[0-9]/g, d => d === '1' ? 'L' : LEET[d]);
  out.add(asI); out.add(asL); out.add(c.replace(/[0-9]/g, ''));
  out.add(asI.replace(/PH/g, 'F')); out.add(asI.replace(/CK/g, 'K')); out.add(asI.replace(/Q/g, 'K')); out.add(asI.replace(/X/g, 'CK'));
  for (const r of [...out]) out.add(r.replace(/(.)\1+/g, '$1'));
  return [...out];
}
export function nameProblem(raw) {
  const s = String(raw || '').trim().toUpperCase();
  if (s.length < 3) return 'too short';
  if (s.length > 12) return 'too long';
  if (!/^[A-Z0-9]+$/.test(s)) return 'letters and numbers only';
  const R = readings(s);
  for (const r of R) {
    if (RESERVED.includes(r)) return 'reserved';
  }
  for (const r of R) {
    if (RESERVED_ALSO.includes(r) || RESERVED_ALSO.includes(r.replace(/[0-9]+$/, ''))) return 'not available';
  }
  for (const r of R) {
    let q = r; for (const a of ALLOW) q = q.split(a).join('-');
    for (const w of BAD_ANY) if (q.includes(w)) return 'profanity';
    const bare = r.replace(/[0-9]+$/, '');
    if (BAD_EXACT.includes(r) || BAD_EXACT.includes(bare)) return 'profanity';
    // a bad word followed only by digits or repeated letters, like ASS69 or DICKK
    for (const w of BAD_EXACT) if (r.startsWith(w) && /^[0-9]*$/.test(r.slice(w.length))) return 'profanity';
  }
  return null;
}
