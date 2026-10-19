#!/usr/bin/env python3
"""Pre-record the flight school instructors, Dana (the CFI) and Frank (the checkride examiner), for schoolhud item 1.

No speech engine runs in flight any more: every line the two say is played from clips made here with the macOS `say`
command, the same way tools/make_radio.py makes the tower. They sit beside the pilot, so the clips play dry (no radio
filter) through the game's voice queue.

How the lines are found (the harvest): every string literal the lesson code hands to a speaking function (cfi, dpe,
pilSay, cirSay, cirDepart, rideSay, divSay, say1, the dpe:/dpeSp:/line: options), plus the free literals in the lesson
flights (LESFLY to LESFLY.ride) and in cfiCue and dbSay, minus the ones inside a UI call (lesShow, gRange, toast...).
Each literal goes through the game's own cfiSp (digits to words, ft to feet) and is cut into pieces at sentence marks
(. ! ? : ;). A piece is one clip: whole sentences keep their natural reading. At run time the game cuts a line the same
way and covers each sentence with the fewest clips (cfiClips: whole sentences first, then the pieces either side of a
spliced-in value, then numbers word by word from n_* clips: "You are" + "six hundred fifty" + "feet high").

Voices: Dana is Nicky (Enhanced), a US female voice no other part of the game uses. Frank is Nathan (Enhanced), slower
and pitched down 8 percent, so he is not the dogfight wingman's voice (Nathan at 205, through the radio filter).

    python3 tools/make_cfi.py            # write radio/cfi/*.m4a and radio/cfi/voice.json
    python3 tools/make_cfi.py --list     # print the harvested pieces per voice and set, write nothing
    python3 tools/make_cfi.py --check    # report what is missing, write nothing

Sets: Dana's clips are grouped by lesson (the LESFLY entry a literal sits in) plus 'common' (the helpers, the numbers,
the debrief); the game decodes common plus the lesson's own set when the lesson starts and drops them when it ends, so a
phone never holds all of them decoded at once. Frank has one set, 'ride'.
"""
import hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'radio', 'cfi')
SRC = os.path.join(ROOT, 'index.html')

VOICES = {'d': ('Nicky (Enhanced)', 182, 1.0), 'f': ('Nathan (Enhanced)', 168, 0.92)}   # name, words a minute, pitch
GAIN = {'d': 0.0, 'f': 0.0}

SPEECH = {'cfi', 'dpe', 'coach2', 'pilSay', 'cirSay', 'cirDepart', 'rideSay', 'divSay', 'say1'}
FRANK_SINKS = {'dpe', 'rideSay'}
UI = {'lesShow', 'tutShow', 'gRange', 'gEvent', 'gEnd', 'toast', 'schSay', 'lockSay', 'resFill', 'rideTitle', 'L', 'say',
      'vqAdd', 'tqAsk', 'navSet', 'divOpen', 'lesAdd', 'warnFlash', 'cfiSp', 'replace', 'split', 'join', 'getElementById', '$',
      'querySelector', 'toLocaleString', 'toFixed', 'padStart', 'hM', 'hSay', 'h3', 'dev', 'gHold', 'gHoldEnd', 'lessonDef',
      'endorseSign', 'logbookAdd', 'runLog', 'certSet', 'hapPattern', 'setAttribute', 'add', 'remove', 'toggle', 'cirTwr',
      'pilBravoAsk', 'pilRbAsk', 'start', 'lesWX', 'push', 'includes', 'test', 'indexOf', 'find', 'filter', 'some', 'map'}
# function bodies whose literals are screen text, not speech
UI_FUNCS = {'navUI', 'navMap', 'divUI', 'pilAskLine', 'lesAim', 'grDraw', 'lesPylon', 'grSite', 'divOpen', 'divClose', 'emDraw',
            'rideTitle', 'certGet', 'certSet', 'tutPoint', 'patCall', 'cirTwr', 'pilBravoReq', 'pilRbAsk', 'navPlan', 'pilFix',
            'shRwy', 'lesWind', 'hoodOn', 'lesRestore', 'lesWX', 'lesNight', 'emOK', 'emField', 'uaGo', 'uaSet', 'rideSeed',
            'rideDraw', 'rideStart', 'rideRun', 'rideClean', 'navStamp', 'navShow', 'navPoint', 'navTick', 'navArrive', 'navHome',
            'navOff', 'navSet', 'divSet', 'cirInit', 'cirFinish', 'pilFinish', 'divArrive', 'pilArrive', 'divVec', 'divAsk'}
FRANK_FUNCS = {'rideTaskLine', 'rideOpen', 'rideGrade', 'rideFinish'}
# words and phrases the code splices in from data (names, directions, the callsign), said by both
EXTRA = ['left', 'right', 'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest', 'point',
         'minute', 'minutes', 'mile', 'miles', 'knots', 'feet', 'degrees', 'meters', 'heading',
         'Glendale Tower', 'Skyhawk eight four zero one lima', 'Skyhawk zero one lima', 'Glendale', 'the stadium', 'Tolleson',
         'downtown Phoenix', 'Sky Harbor', 'Downtown', 'Stadium', 'Sky Harbor runway seven left', 'Glendale runway one',
         'State Farm Stadium', 'Downtown Phoenix', 'the details', 'the detail work']
NUMS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
        'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty', 'fifty', 'sixty',
        'seventy', 'eighty', 'ninety', 'hundred', 'thousand', 'niner']
NUMSET = set(NUMS) | {'point'}

# ---- the game's own number words (cfiSp, nWords), ported ----
NW1 = NUMS[:20]
NW10 = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
def nwords(n):
    n = round(abs(n))
    if n < 20: return NW1[n]
    if n < 100: return NW10[n // 10] + ('-' + NW1[n % 10] if n % 10 else '')
    if n < 1000: return NW1[n // 100] + ' hundred' + (' ' + nwords(n % 100) if n % 100 else '')
    if n < 10000 and n % 100 == 0 and n % 1000: return nwords(n // 100) + ' hundred'
    if n < 1e6: return nwords(n // 1000) + ' thousand' + (' ' + nwords(n % 1000) if n % 1000 else '')
    return str(n)
def cfisp(t):
    t = re.sub(r'\bft\b', 'feet', t); t = re.sub(r'\bkt\b', 'knots', t); t = re.sub(r'\bfpm\b', 'feet a minute', t)
    t = t.replace('°', ' degrees')
    return re.sub(r'\b\d[\d,]*\b', lambda m: nwords(int(m.group(0).replace(',', ''))), t)

# ---- the cut and the key: the game's cfiNorm and cfiCut are the same rules ----
def norm(s):
    s = s.lower().replace('’', "'")
    s = re.sub(r"[^a-z0-9']+", ' ', s)
    return ' '.join(w.strip("'") for w in s.split() if w.strip("'"))
def cut(t):
    """pieces of a spoken text at . ! ? : ; (a mark followed by a space or the end)"""
    out, cur = [], ''
    for i, ch in enumerate(t):
        cur += ch
        if ch in '.!?:;' and (i + 1 == len(t) or t[i + 1].isspace()):
            out.append(cur); cur = ''
    if cur.strip(): out.append(cur)
    return [p for p in out if norm(p)]

# ---- a small JS tokenizer: strings, comments, regex literals, identifiers, punctuation ----
REGEX_PREV = set('(,=:[!&|?{};+-*%<>~^') | {'return', 'typeof', 'case', 'in', 'of', 'new', 'delete', 'void'}
def tokens(src, a, b):
    i, out, prev = a, [], None
    while i < b:
        c = src[i]
        if c in ' \t\r\n': i += 1; continue
        if src.startswith('//', i): i = src.index('\n', i); continue
        if src.startswith('/*', i): i = src.index('*/', i) + 2; continue
        if c in '\'"':
            j, s = i + 1, ''
            while src[j] != c:
                if src[j] == '\\': s += {'n': '\n', 't': '\t'}.get(src[j + 1], src[j + 1]); j += 2
                else: s += src[j]; j += 1
            out.append(('str', s, i)); prev = 'str'; i = j + 1; continue
        if c == '/' and (prev is None or prev in REGEX_PREV):
            j, cls = i + 1, False
            while True:
                if src[j] == '\\': j += 2; continue
                if src[j] == '[': cls = True
                elif src[j] == ']': cls = False
                elif src[j] == '/' and not cls: break
                j += 1
            j += 1
            while src[j].isalpha(): j += 1
            out.append(('re', src[i:j], i)); prev = 're'; i = j; continue
        m = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*', src[i:i + 80])
        if m: w = m.group(0); out.append(('id', w, i)); prev = w if w in REGEX_PREV else 'id'; i += len(w); continue
        m = re.match(r'\d[\d.eE]*', src[i:i + 40])
        if m: out.append(('num', m.group(0), i)); prev = 'num'; i += len(m.group(0)); continue
        out.append(('p', c, i)); prev = c; i += 1
    return out

def assigned(T, k):
    """the name an expression holding token k is assigned to (x.note='a'+b: 'note'), or None"""
    j, d = k - 1, 0
    while j > 0:
        t = T[j][1]
        if t in (')', ']'): d += 1
        elif t in ('(', '['):
            if d == 0: return None
            d -= 1
        elif d == 0 and t in (';', '{', '}', ','): return None
        elif d == 0 and t == '=' and T[j - 1][1] not in ('=', '!', '<', '>') and T[j + 1][1] != '=': return T[j - 1][1]
        j -= 1
    return None

def harvest():
    src = open(SRC, encoding='utf-8').read()
    a = src.index('\nfunction cfiCue('); a2 = src.index('\nconst ENDORSE_NAME')
    b = src.index('\nconst LESFLY={'); b2 = src.index('\nLESFLY.ride={')
    regions = [(a, a2, True), (b, b2, True)]
    # outside the two regions only the speech calls count (the debrief's line in grade())
    g = src.index('\nfunction grade('); regions.insert(1, (g, src.index('\n}', g) + 2, False))
    found = []   # (voice, set, literal text, open left, open right)
    for (ra, rb, free) in regions:
        T = tokens(src, ra, rb)
        stack = []   # entries: [kind, name, depth]; kind 'call' (a paren) or 'fn' (a function body brace) or 'brace'
        lesson = None; les_depth = None
        for k, (ty, v, pos) in enumerate(T):
            if ty == 'p' and v == '(':
                name = T[k - 1][1] if k and T[k - 1][0] == 'id' else None
                if k > 1 and T[k - 2][1] == 'function': name = None   # a definition's parameter list
                stack.append(['call', name])
            elif ty == 'p' and v == ')':
                while stack and stack[-1][0] != 'call': stack.pop()
                if stack: stack.pop()
            elif ty == 'p' and v == '{':
                fn = None
                # function name(...){ : find the name before the parameter list
                j = k - 1
                if T[j][1] == ')':
                    d = 0
                    while j >= 0:
                        if T[j][1] == ')': d += 1
                        elif T[j][1] == '(':
                            d -= 1
                            if d == 0: break
                        j -= 1
                    if j >= 2 and T[j - 2][1] == 'function': fn = T[j - 1][1]
                    elif j >= 1 and T[j - 1][0] == 'id' and T[j - 1][1] not in ('if', 'for', 'while', 'switch', 'catch'): fn = T[j - 1][1]   # a method: start(S,d){
                # LESFLY entries: "  id:{" at the object's top level
                if ra == b and k >= 2 and T[k - 1][1] == ':' and T[k - 2][0] == 'id' and len([s for s in stack if s[0] != 'call']) == 1:
                    lesson = T[k - 2][1]; les_depth = len(stack) + 1
                stack.append(['fn' if fn else 'brace', fn])
            elif ty == 'p' and v == '}':
                while stack and stack[-1][0] == 'call': stack.pop()
                if stack: stack.pop()
                if les_depth is not None and len(stack) < les_depth: lesson = None; les_depth = None
            elif ty == 'str':
                calls = [s[1] for s in stack if s[0] == 'call' and s[1] in SPEECH | UI]
                fns = [s[1] for s in stack if s[0] == 'fn' and s[1]]
                inner = calls[-1] if calls else None
                # an option dpe: / dpeSp: / line: just before (o.dpe is Frank's, o.line pilHome's opening)
                key = T[k - 2][1] if k >= 2 and T[k - 1][1] == ':' else None
                opt = key in ('dpe', 'dpeSp', 'line', 'baseMsg') or (k >= 3 and T[k - 1][1] == '=' and T[k - 2][1] == 'baseMsg')
                if inner in UI and not opt: continue
                if key in ('detail', 'note', 'sub', 'k', 'name', 'short', 'say', 'title'): continue   # a screen label, or a fix's spoken name (EXTRA has those)
                # screen text: an assignment to .note, .textContent, .tdzX, .head, .title..., or a comparison (=== 'F')
                tgt = assigned(T, k)
                if tgt in ('note', 'textContent', 'tdzX', 'head', 'innerHTML', 'title', 'className', 'detail'): continue
                if k >= 2 and T[k - 1][1] == '=' and T[k - 2][1] in ('=', '!'): continue
                if k + 2 < len(T) and T[k + 1][1] in ('=', '!') and T[k + 2][1] == '=': continue
                if k >= 2 and T[k - 1][1] == '[' and T[k - 2][1] == '=' and ra == b and T[k - 3][1] == 'head': continue
                if any(f in UI_FUNCS for f in fns): continue
                speech = inner in SPEECH or opt
                if not speech:
                    if not free: continue
                    s = v.strip()
                    if not re.search(r'[A-Za-z]', s) or '<' in s or 'px' in s or '#' in s: continue
                    if not (' ' in s or re.search(r'[.!?]$', s)): continue
                    if re.match(r'^[a-z]+[A-Z]', s) or re.search(r'\b(var|function|rgba|translate)\b', s): continue
                frank = inner in FRANK_SINKS or key in ('dpe', 'dpeSp') or any(f in FRANK_FUNCS for f in fns)
                lo = k > 0 and T[k - 1][1] == '+'
                ro = k + 1 < len(T) and T[k + 1][1] == '+'
                found.append(('f' if frank else 'd', 'ride' if frank else (lesson or 'common'), v, lo, ro))
    return found

def pieces(text):
    """the clip texts of one literal: its sentence pieces, cfiSp'd, with their punctuation"""
    out = []
    for p in cut(cfisp(text)):
        q = p.strip().lstrip(',;: ').strip()
        if norm(q): out.append(q)
    return out

def manifest():
    m = {'d': {}, 'f': {}}           # voice -> key -> (text, set)
    def put(v, s, q):
        k = norm(q)
        if not k: return
        if k not in m[v]: m[v][k] = [q, s]
        elif m[v][k][1] != s: m[v][k][1] = 'common'   # used by two lessons: in the shared set
    for v, s, lit, lo, ro in harvest():
        for q in pieces(lit): put(v, s, q)
    names = re.findall(r"const RIDE_NAME=\{([^}]*)\}", open(SRC, encoding='utf-8').read())
    ride_names = re.findall(r":'([^']+)'", names[0]) if names else []
    for v in 'df':
        for q in EXTRA + NUMS: put(v, 'common' if v == 'd' else 'ride', q)
    src = open(SRC, encoding='utf-8').read()
    # the checkride's task names (rideName: RIDE_NAME, else the lesson's short name or name), said lower case after "First, "
    pool = re.findall(r"'([a-z]+)'", re.search(r"const RIDE_POOL=\[([^\]]*)\]", src).group(1)) + ['landings']
    for lid in pool:
        m2 = re.search(r"\{id:'" + lid + r"',name:'([^']+)'(?:,short:'([^']+)')?", src)
        if m2: ride_names.append(m2.group(2) or m2.group(1))
    for q in ride_names: put('f', 'ride', q); put('f', 'ride', q[0].lower() + q[1:])
    # dbSay's task: a task's tip, else its name lower cased ("Polish the touchdown zone."); the endorsements' names
    a0 = src.index('\nconst SCHOOL='); sch = src[a0:src.index('\n};', a0)]
    les = [(m3.start(), m3.group(1)) for m3 in re.finditer(r"\{id:'([a-z0-9]+)',name:'[^']*',(?:short:'[^']*',)?sub:", sch)]
    for i, (p0, lid) in enumerate(les):
        body = sch[p0:les[i + 1][0] if i + 1 < len(les) else len(sch)]
        tk = body[body.find('tasks:['):] if 'tasks:[' in body else ''
        for ob in re.findall(r"\{id:'[a-z0-9_]+',name:'[^']+'[^{}]*\}", tk):
            nm, tp = re.search(r"name:'([^']+)'", ob).group(1), re.search(r"tip:'([^']+)'", ob)
            for q in pieces(tp.group(1) if tp else nm[0].lower() + nm[1:]): put('d', lid, q)
    for q in ('solo', 'solo cross country'): put('d', 'common', q)
    return m

def cid(v, k): return v + '_' + hashlib.sha1((v + '|' + k).encode()).hexdigest()[:10]

TRIM = ('silenceremove=start_periods=1:start_silence=0.02:start_threshold=-50dB:detection=peak,areverse,'
        'silenceremove=start_periods=1:start_silence=0.02:start_threshold=-50dB:detection=peak,areverse')

def render(v, text, path, tmp):
    name, rate, pitch = VOICES[v]
    aiff = os.path.join(tmp, os.path.basename(path) + '.aiff')
    say = text[0].upper() + text[1:]
    subprocess.run(['say', '-v', name, '-r', str(rate), '-o', aiff, say], check=True)
    af = TRIM
    if pitch != 1.0: af = f'asetrate={round(22050 * pitch)},aresample=22050,atempo={1 / pitch:.4f},' + af
    af += ',loudnorm=I=-17:TP=-1.5:LRA=11,aresample=44100'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', aiff, '-af', af, '-ac', '1', '-c:a', 'aac', '-b:a', '48k', path], check=True)
    os.remove(aiff)

def main():
    m = manifest()
    if '--list' in sys.argv:
        for v in 'df':
            sets = {}
            for k, (q, s) in m[v].items(): sets.setdefault(s, []).append(q)
            for s in sorted(sets):
                print(f'== {v} {s}: {len(sets[s])}')
                for q in sorted(sets[s]): print('   ', q)
        print('total', {v: len(m[v]) for v in m})
        return 0
    want = {cid(v, k) for v in m for k in m[v]}
    if '--check' in sys.argv:
        miss = [c for c in want if not os.path.exists(os.path.join(OUT, c + '.m4a'))]
        print(f'{len(want)} clips in the manifest, {len(miss)} missing')
        return 1 if miss else 0
    for tool in ('say', 'ffmpeg'):
        if not shutil.which(tool): print(tool, 'not found', file=sys.stderr); return 2
    vl = subprocess.run(['say', '-v', '?'], capture_output=True, text=True).stdout
    for v, (name, _, _) in VOICES.items():
        if not any(l.startswith(name + ' ') for l in vl.splitlines()): print('voice not installed:', name, file=sys.stderr); return 2
    os.makedirs(OUT, exist_ok=True); tmp = os.path.join(OUT, '.tmp'); os.makedirs(tmp, exist_ok=True)
    force, made = '--force' in sys.argv, 0
    for v in 'df':
        for k, (q, s) in sorted(m[v].items()):
            p = os.path.join(OUT, cid(v, k) + '.m4a')
            if force or not os.path.exists(p): render(v, q, p, tmp); made += 1
    os.rmdir(tmp)
    for f in os.listdir(OUT):   # clips no line uses any more
        if f.endswith('.m4a') and f[:-4] not in want: os.remove(os.path.join(OUT, f))
    out = {'v': 1, 'voices': {v: VOICES[v][0] for v in VOICES}, 'd': {}, 'f': {}, 'sets': {}}
    for v in 'df':
        for k, (q, s) in sorted(m[v].items()):
            c = cid(v, k); out[v][k] = c; out['sets'].setdefault(v + ':' + s, []).append(c)
    json.dump(out, open(os.path.join(OUT, 'voice.json'), 'w'), separators=(',', ':'), sort_keys=True)
    tot = sum(os.path.getsize(os.path.join(OUT, c + '.m4a')) for c in want)
    print(f'{made} clip(s) rendered; {len(want)} clips ({len(m["d"])} Dana, {len(m["f"])} Frank), {tot / 1024:.0f} KB')
    for s, L in sorted(out['sets'].items()): print(f'  {s}: {len(L)}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
