# Red Flag Dogfight on the leaderboards (5.5). iPhone landscape 844x390, the Worker stubbed (http://lb.test).
# (a) the eight boards df:score|kills|clear|guns:easy|hard are registered single mode in the 'Red Flag Dogfight' group and
#     listed on the Boards screen as separate entries ("Dogfight score (Hard)"), their rows carry no EASY/HARD chip.
# (b) Hard: no token under the briefing card; FIGHT'S ON asks for exactly one token, for df:score:hard. A won run sends one
#     submit to df:score:hard with the df block (kills, guns, hits, waves, won, clear, bank, flares, ach) and no path; the
#     results card shows the rank line, the personal bests line, "+150 XP  ACE" and the rank up from the stubbed answer.
# (c) abandoning a run (MAIN MENU) cancels its token: nothing is submitted. A run with no points and no kills is not sent.
# (d) Easy: the token and the submit go to df:score:easy (mode easy).
# (e) a forced dogfight daily (K.dailyKind('dogfight')): the card on ARCADE and MISSIONS, GO starts the seeded fight
#     (DF.daily, DF.seed the day, the same spawn twice), one token for 'daily', a submit to daily with score round(score/2)
#     and the df block; K.dailyRegion('az') still pins a landing daily.
# (f) no console errors.
# Usage: .venv/bin/python tests/dogfight_lb_check.py
import asyncio, sys, json, os
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, launch, IPHONE_15, Checks, finger, THREE, IGNORE, splash_gone

ok = Checks()
K = 'window.__kgeu'
WK = 'http://lb.test'
ME = 'HABOOB'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuType': 'f16', 'kgeuLBUrl': WK,
        'kgeuLB': json.dumps({'cs': ME, 'key': 'a' * 48, 'xp': 250})}
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
seen = []
ROWS = [{'r': 1, 'cs': 'VIPER', 'score': 1700, 'secs': 250, 'ac': 'f16', 'mode': 'hard', 'xp': 900, 'rank': 'Wingman', 'creator': False, 'when': 0}]


async def worker(route):
    req = route.request
    path = req.url[len(WK):].split('?')[0]
    if req.method == 'OPTIONS':
        return await route.fulfill(status=204, headers=CORS)
    body = {}
    try:
        body = json.loads(req.post_data or '{}')
    except Exception:
        pass
    seen.append((path, body.get('board'), body))
    sub = {'ok': True, 'rank': 3, 'total': 40, 'pb': True, 'top10': True, 'best': body.get('score'), 'xp': 400, 'gain': 60, 'rankName': 'Wingman',
           'df': {'kills': {'score': 10, 'rank': 1, 'total': 12, 'pb': True, 'top10': True}, 'clear': {'score': 250, 'rank': 14, 'total': 20, 'pb': True, 'top10': False}, 'guns': None},
           'ach': [{'id': 'ace', 'xp': 150}], 'achXp': 150}
    ans = {'/health': {'ok': True}, '/me': {'cs': ME, 'xp': 250, 'creator': False}, '/pool': {'tokens': []}, '/fame': {'day': 0, 'daily': None, 'top': []},
           '/token': {'token': 'tok.' + str(len(seen)), 't0': 0, 'day': 0}, '/submit': sub,
           '/board': {'board': 'x', 'mode': 'all', 'period': 'today', 'dir': 1, 'total': 1, 'rows': ROWS, 'me': None, 'ghost': None, 'now': 0, 'day': 0},
           '/ghost': {'ghost': None}}.get(path, {})
    await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps(ans))


async def newpage(b, url, storage):
    ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
    await ctx.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await ctx.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await ctx.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    await ctx.route(WK + '/**', worker)
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
                              + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    await pg.wait_for_timeout(500)
    return pg

STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);}"
UNTIL = """([cond,max])=>{const K=window.__kgeu,D=K.DF,f=new Function('K','D','return ('+cond+')');
  for(let i=0;i<max*10;i++){K.stepFrame(0.1,false,true);if(f(K,D))return true;}return false;}"""
CARD = "()=>({on:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText})"
calls = lambda kind: [x for x in seen if x[0] == kind]


async def start(pg, skill, brief=False, daily=False):
    await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.setSkill('{skill}');D.test.seed=null;D.test.hold=false;D.test.noBanditFire=true;D.test.noBrief={'false' if brief else 'true'};K.windSeed(7);K.dfStart({'{daily:1}' if daily else ''});}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(STEP, 2)


async def kill_wave(pg, how):
    await pg.evaluate(f"(h)=>{{const D={K}.DF;D.bandits.slice().forEach((b,i)=>{{if(b.alive){K}.dfKill(b,Array.isArray(h)?h[i%h.length]:h);}});}}", how)


async def win(pg):
    for w in range(4):
        await pg.evaluate(STEP, 25)   # 2.5 s of wave clock used, so the clear time and secs are real
        await kill_wave(pg, ['fox2', 'gun'] if w == 1 else 'fox2')
        await pg.evaluate(UNTIL, ["D.gap<=0&&D.bandits.some(b=>b.alive)||!D.on", 10] if w < 3 else ["!D.on", 2])


async def settle(pg, secs=1.5):
    await pg.wait_for_timeout(int(secs * 1000))


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await newpage(b, url, BASE)

        # ---------------- (a) boards ----------------
        ids = [f'df:{k}:{m}' for m in ('hard', 'easy') for k in ('score', 'kills', 'clear', 'guns')]
        bd = await pg.evaluate(f"(ids)=>ids.map(id=>{{const B={K}.LB.BOARDS[id];return B&&[id,B.name,B.group,B.mode,B.dir,{K}.LB.ORDER.includes(id)]}})", ids)
        ok('(a) eight dogfight boards, single mode, in Red Flag Dogfight', all(x and x[2] == 'Red Flag Dogfight' and x[3] == x[0].split(':')[2] and x[5] for x in bd)
           and [x[1] for x in bd[:4]] == ['Dogfight score (Hard)', 'Dogfight kills (Hard)', 'Dogfight clear time (Hard)', 'Dogfight gun kills (Hard)']
           and bd[2][4] == -1 and bd[6][4] == -1 and bd[0][4] == 1, bd)
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen('df:kills:hard')}}"); await pg.wait_for_timeout(800)
        try: await pg.wait_for_selector('#lbRowsIn .lbRow', timeout=6000, state='attached')
        except Exception: pass
        lbt = await pg.evaluate("()=>[...document.querySelectorAll('#lbList [data-lbb]')].map(e=>e.dataset.lbb+'='+e.textContent)")
        bar = await pg.evaluate("()=>({mode:!document.getElementById('lbMode').hidden&&document.querySelector('[data-lbmode].sel').dataset.lbmode,stat:!document.getElementById('lbStat').hidden&&document.querySelector('[data-lbstat].sel').dataset.lbstat,sel:(document.querySelector('#lbList .sel')||{}).dataset})")
        ok('(a) ui1: the picker has one Red Flag Dogfight entry; the bar shows EASY/HARD (Hard) and the stat (Kills)',
           [x for x in lbt if 'Dogfight' in x] == ['df=Red Flag Dogfight'] and bar['mode'] == 'hard' and bar['stat'] == 'kills' and bar['sel'] and bar['sel']['lbb'] == 'df', (lbt, bar))
        rw = await pg.evaluate("()=>({n:document.querySelectorAll('#lbRowsIn .lbRow').length,chip:document.querySelectorAll('#lbRowsIn .modeTag').length,s:(document.querySelector('#lbRowsIn .lbRow .s')||{}).textContent,t:document.getElementById('lbTitle').textContent})")
        ok('(a) a dogfight board: rows without the EASY/HARD chip, kills formatted', rw['n'] == 1 and rw['chip'] == 0 and rw['s'] == '1,700 kills' and rw['t'] == 'Red Flag Dogfight, kills', rw)
        await pg.evaluate("()=>document.querySelector('[data-lbmode=easy]').click()"); await pg.wait_for_timeout(300)
        ez = await pg.evaluate("()=>[document.querySelector('[data-lbmode].sel').dataset.lbmode,document.getElementById('lbTitle').textContent]")
        ok('(a) ui1: the EASY chip switches to the Easy kills board', ez == ['easy', 'Red Flag Dogfight, kills'], ez)
        await pg.screenshot(path=os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'dogfight_lb_boards.png'))

        # ---------------- (b) a Hard win ----------------
        seen.clear()
        await start(pg, 'pilot', brief=True)
        t0 = calls('/token')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(600)
        t1 = calls('/token')
        ok("(b) no token under the briefing card; FIGHT'S ON asks for exactly one, for df:score:hard",
           not t0 and len(t1) == 1 and t1[0][1] == 'df:score:hard' and t1[0][2].get('mode') == 'hard', [(x[1], x[2].get('mode')) for x in t1])
        await pg.evaluate(f"()=>{{const A={K}.SCORE.ach;delete A.ace;}}")
        await win(pg)
        ok('(b) the run is won', await pg.evaluate(f"()=>{K}.DF.won&&{K}.DF.kills===10"))
        await pg.evaluate(UNTIL, ["document.getElementById('arcOv').classList.contains('on')", 8]); await settle(pg)
        sub = calls('/submit')
        sc = await pg.evaluate(f"()=>{K}.DF.sc")
        d = sub[0][2] if sub else {}
        df = d.get('df') or {}
        ok('(b) one submit to df:score:hard: the score, f16, the run time, no path', len(sub) == 1 and d.get('board') == 'df:score:hard' and d.get('mode') == 'hard'
           and d.get('score') == sc['score'] and d.get('ac') == 'f16' and d.get('secs', 0) >= 9 and 'path' not in d and d.get('token', '').startswith('tok.'), {k: v for k, v in d.items() if k not in ('key', 'df')})
        ok('(b) the df block: kills 10, guns 1, hits 0, waves 4, won, the clear time, bank, flares, ach with ace',
           df.get('kills') == 10 and df.get('guns') == 1 and df.get('hits') == 0 and df.get('waves') == 4 and df.get('won') is True and df.get('clear') == sc['clearT']
           and isinstance(df.get('bank'), int) and df['bank'] * 2 + 1000 + 100 + 250 == sc['score'] and df.get('flares') == 0 and 'ace' in df.get('ach', []) and 'guns' in df.get('ach', []), df)
        card = await pg.evaluate(CARD)
        ok('(b) the results card: the rank line #3 of 40 (TOP 10)', card['on'] and 'Leaderboard\n#3 of 40 +60 XP' in card['lines'] and 'TOP 10' in card['lines'], card['lines'])
        ok('(b) the results card: the personal bests line, "+150 XP  ACE", the rank up to Wingman',
           'Also: kills (TOP 10), clear time #14' in card['lines'] and '+150 XP ACE' in card['lines'] and 'Rank up\n' in card['lines'] and 'WINGMAN' in card['lines'], card['lines'])
        await pg.screenshot(path=os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'dogfight_lb_card.png'))
        await pg.evaluate("()=>document.getElementById('aHub').click()"); await pg.wait_for_timeout(300)

        # ---------------- (c) abandon, and an empty run ----------------
        seen.clear()
        await start(pg, 'pilot')
        await kill_wave(pg, 'fox2'); await pg.evaluate(STEP, 5)
        tk = calls('/token')
        await pg.evaluate(f"()=>{{{K}.openMenu();}}"); await pg.wait_for_timeout(300)
        runs = await pg.evaluate(f"()=>Object.keys({K}.LB.E.runs)")
        await settle(pg, 1)
        ok('(c) abandoned at the main menu: the token asked for, then dropped, nothing submitted', len(tk) == 1 and tk[0][1] == 'df:score:hard' and runs == [] and not calls('/submit'), (tk, runs))
        seen.clear()
        await start(pg, 'pilot')
        await pg.evaluate(f"()=>{{{K}.DF.t=0.3;}}"); await pg.evaluate(STEP, 30); await settle(pg, 1)
        ok('(c) a run with no points and no kills is not sent (its token dropped)', len(calls('/token')) == 1 and not calls('/submit') and await pg.evaluate(f"()=>Object.keys({K}.LB.E.runs).length===0"), seen)

        # ---------------- (d) Easy goes to its own board ----------------
        seen.clear()
        await start(pg, 'rookie')
        await kill_wave(pg, 'fox2'); await pg.evaluate(UNTIL, ["D.gap<=0&&D.bandits.some(b=>b.alive)||!D.on", 10])
        await pg.evaluate(f"()=>{{{K}.DF.t=0.5;}}"); await pg.evaluate(STEP, 30); await settle(pg)
        tk, sb = calls('/token'), calls('/submit')
        ok('(d) Easy: one token and one submit, both df:score:easy, mode easy, 1 kill', len(tk) == 1 and tk[0][1] == 'df:score:easy' and tk[0][2]['mode'] == 'easy'
           and len(sb) == 1 and sb[0][1] == 'df:score:easy' and sb[0][2]['mode'] == 'easy' and sb[0][2]['df']['kills'] == 1 and sb[0][2]['df']['won'] is False and sb[0][2]['df']['clear'] is None,
           [(x[0], x[1], x[2].get('mode')) for x in tk + sb])
        await pg.evaluate("()=>document.getElementById('aHub').click()"); await pg.wait_for_timeout(300)

        # ---------------- (e) the dogfight daily ----------------
        seen.clear()
        kinds = await pg.evaluate(f"()=>{{const K={K};const a=K.dailyKind('dogfight');K.dailyKind(null);K.dailyRegion('az');const b=K.dailySpec().kind;K.dailyRegion(null);return [a,b];}}")
        ok("(e) K.dailyKind('dogfight') forces it; K.dailyRegion('az') pins a landing daily", kinds == ['dogfight', 'landing'], kinds)
        await pg.evaluate(f"()=>{{const K={K};K.dailyRegion(null);K.dailyKind('dogfight');K.setSkill('pilot');K.openMenu();K.nav('sArc')}}"); await pg.wait_for_timeout(400)
        ca = await pg.evaluate("()=>document.querySelector('#arcCards .mcard[data-m=daily]').innerText")
        cm = ca   # ui1: one Challenges list, one daily card
        ok('(e) the daily card on CHALLENGES: Red Flag Dogfight, Barry M. Goldwater Range, F-16, the mode, the countdown',
           all('Red Flag Dogfight' in c and 'Barry M. Goldwater Range, F-16' in c and 'Hard mode' in c and 'Next in' in c for c in (ca, cm)), (ca, cm))
        await pg.screenshot(path=os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'dogfight_lb_daily_card.png'))
        await pg.evaluate(f"()=>{{const D={K}.DF;D.test.noBrief=true;D.test.noBanditFire=true;D.test.seed=null;}}")
        await finger(pg, '#arcCards .mcard[data-m="daily"]'); await pg.wait_for_timeout(500); await pg.evaluate(STEP, 1)
        s1 = await pg.evaluate(f"()=>{{const K={K},D=K.DF;return {{daily:D.daily,seed:D.seed,day:K.dailySpec().day,on:D.on,p:D.bandits.map(b=>[Math.round(b.p.x),Math.round(b.p.z)])}}}}")
        tk = calls('/token')
        ok('(e) GO starts the seeded fight: DF.daily, DF.seed the UTC day, one token for daily', s1['on'] and s1['daily'] and s1['seed'] == s1['day'] and len(tk) == 1 and tk[0][1] == 'daily', (s1, [x[1] for x in tk]))
        await kill_wave(pg, 'fox2'); await pg.evaluate(UNTIL, ["D.gap<=0&&D.bandits.some(b=>b.alive)||!D.on", 10])
        p2 = await pg.evaluate(f"()=>{K}.DF.bandits.map(b=>[Math.round(b.p.x),Math.round(b.p.z)])")
        await pg.evaluate(f"()=>{{{K}.DF.t=0.5;}}"); await pg.evaluate(STEP, 30); await settle(pg)
        sc = await pg.evaluate(f"()=>{K}.DF.sc")
        sb = calls('/submit')
        d = sb[0][2] if sb else {}
        ok('(e) one submit to daily: score = round(dogfight score / 2), the df block, no path', len(sb) == 1 and d.get('board') == 'daily' and d.get('score') == round(sc['score'] / 2) and sc['score'] > 0
           and d.get('df', {}).get('kills') == 1 and 'path' not in d and d.get('ac') == 'f16', ({k: v for k, v in d.items() if k != 'key'}, sc))
        dl = await pg.evaluate("()=>JSON.parse(localStorage.getItem('kgeuDaily')||'null')")
        card = await pg.evaluate(CARD)
        ok("(e) the day's attempt is marked, the card says Daily dogfight with the daily points", dl and dl.get('used') == 1 and 'Daily dogfight' in card['title'] and f"Daily points\n{round(sc['score'] / 2)}" in card['lines'], (dl, card))
        # the same fight again (the seed): the first wave spawns where it did, read at once after the start
        await pg.evaluate("()=>document.getElementById('aHub').click()"); await pg.wait_for_timeout(300)
        SP = f"()=>{{const K={K},D=K.DF;D.test.seed=null;K.dfStart({{daily:1}});return D.bandits.map(b=>[Math.round(b.p.x),Math.round(b.p.z)]).concat([[D.seed,0]])}}"
        s2 = await pg.evaluate(SP); s3 = await pg.evaluate(SP)
        s4 = await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.dfStart();return D.bandits.map(b=>[Math.round(b.p.x),Math.round(b.p.z)])}}")
        ok('(e) the daily fight is the same each time (seeded spawns), a regular run is not seeded', s2 == s3 and s2[-1][0] == s1['day'] and s4[0] != s2[0] and len(p2) == 2, (s2, s3, s4))
        await pg.evaluate(f"()=>{{{K}.dailyKind(null);{K}.openMenu();}}")
        ok('(f) no console errors', not pg.errs, pg.errs[:4])
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('dogfight_lb_check'))

asyncio.run(main())
