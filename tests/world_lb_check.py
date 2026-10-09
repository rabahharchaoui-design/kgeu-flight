# World airports on the leaderboards. iPhone landscape 844x390, Hard, the Worker stubbed (http://lb.test).
# (a) the boards apt:RJTT, apt:LFPG and apt:SBRJ are registered in the 'World airports' group and listed on the
#     Boards screen; ARCADE shows the three cards under the Arizona games, without the ARIZONA tag.
# (b) from Arizona, the Tokyo card (reload stubbed) saves kgeuRegion rjtt and a resume with arc 'apt'; after the
#     real reload the challenge is running (board apt:RJTT, airborne about 9 km from the 34R threshold, the HUD names
#     Tokyo Haneda runway 34R), and autoland flies it to the results card: 'Tokyo Haneda landing', points > 0.
# (c) the daily rotation with a shifted clock: all four regions in 12 days, the same spec for a day across page loads;
#     on a Paris day the daily card says Paris CDG, runway 26L on MISSIONS and ARCADE; GO saves a daily resume for
#     lfpg (reload stubbed) and marks nothing; after the real reload the daily runs at LFPG with the spec's time and
#     wind, and only then are kgeuDaily and the day's one token request made.
# (d) LB.fameApply at rjtt puts the champion on the city billboard (texture redrawn), null takes it off.
# (f) no console errors.
# Usage: .venv/bin/python tests/world_lb_check.py
import asyncio, sys, json, math, os
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, launch, IPHONE_15, Checks, finger, THREE, IGNORE, splash_gone

ok = Checks()
K = 'window.__kgeu'
WK = 'http://lb.test'
ME = 'HABOOB'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuType': 'cessna', 'kgeuLBUrl': WK,
        'kgeuLB': json.dumps({'cs': ME, 'key': 'a' * 48, 'xp': 100})}
STUB = "()=>{window.__kgeuReload=()=>{window.__reloaded=(window.__reloaded||0)+1;};}"
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
seen = []
FAME = {'day': 0, 'daily': None, 'top': [], 'apt': {'RJTT': {'cs': 'STUBACE', 'score': 1300, 'mode': 'hard'}, 'LFPG': None, 'SBRJ': None}}
# the clock, shifted by sessionStorage.__off ms (kept across reloads, so a page load stays on the chosen day)
DATE = """(()=>{const R=Date,off=()=>{try{return +(sessionStorage.getItem('__off')||0);}catch(e){return 0;}};
  class D extends R{constructor(...a){if(a.length)super(...a);else super(R.now()+off());}static now(){return R.now()+off();}}
  window.Date=D;})()"""


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
    seen.append((path, body.get('board')))
    ans = {'/health': {'ok': True}, '/me': {'cs': ME, 'xp': 100, 'creator': False}, '/pool': {'tokens': []}, '/fame': FAME,
           '/token': {'token': 'tok.' + str(len(seen)), 't0': 0, 'day': 0},
           '/submit': {'ok': True, 'rank': 1, 'total': 1, 'pb': True, 'top10': True, 'best': body.get('score'), 'xp': 150, 'gain': 50},
           '/board': {'board': 'apt:RJTT', 'mode': 'all', 'period': 'today', 'dir': 1, 'total': 0, 'rows': [], 'me': None, 'ghost': None, 'now': 0, 'day': 0},
           '/ghost': {'ghost': None}}.get(path, {})
    await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps(ans))


async def newpage(b, url, storage, off=0):
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
                              + f'sessionStorage.setItem("__off","{off}");'
                              + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    await ctx.add_init_script(DATE)
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    await pg.wait_for_timeout(300)
    return pg


async def after_reload(pg, cond, secs=120):
    for _ in range(secs * 4):
        try:
            if await pg.evaluate(cond):
                return True
        except Exception:
            pass
        await pg.wait_for_timeout(250)
    raise RuntimeError('timed out after the reload: ' + cond)


async def land(pg):
    """autoland the running challenge, then run the rollout until the results card is up"""
    await pg.evaluate(f"()=>{K}.auto()")
    for _ in range(200):
        await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
        if await pg.evaluate(f"()=>{K}.state().onGround||{K}.state().crashed"):
            break
    for _ in range(40):
        await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(120)
        if await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')"):
            break
    await pg.wait_for_timeout(500)
    return await pg.evaluate("()=>({on:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent,score:document.getElementById('aScore').textContent,lines:document.getElementById('aLines').innerText})")


ARCCARDS = "()=>[...document.querySelectorAll('#arcCards .mcard')].map(c=>({id:c.dataset.m,name:c.querySelector('b').textContent,d:c.querySelector('.d').textContent,sc:c.querySelector('.sc').textContent,tag:!!c.querySelector('.azTag')}))"


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        # ---------------- (a) boards and the ARCADE cards, in Arizona ----------------
        print('\n--- Arizona ---')
        pg = await newpage(b, url, BASE)
        bd = await pg.evaluate(f"()=>['apt:RJTT','apt:LFPG','apt:SBRJ'].map(id=>{{const B={K}.LB.BOARDS[id];return B&&[id,B.name,B.group,!!B.ghost,typeof B.go,{K}.LB.ORDER.includes(id)]}})")
        ok('(a) apt:RJTT, apt:LFPG, apt:SBRJ registered in World airports, ghost boards with a go',
           bd == [['apt:RJTT', 'Tokyo Haneda landing', 'World airports', True, 'function', True], ['apt:LFPG', 'Paris CDG landing', 'World airports', True, 'function', True],
                  ['apt:SBRJ', 'Rio Santos Dumont landing', 'World airports', True, 'function', True]], bd)
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen()}}"); await pg.wait_for_timeout(600)
        lbt = await pg.evaluate("()=>[...document.querySelectorAll('#lbList h3, #lbList [data-lbb]')].map(e=>e.textContent).join('|')")
        ok('(a) ui1: the board picker has no World airports entries (their boards stay on the server)', 'World airports' not in lbt and 'Tokyo' not in lbt and 'Daily challenge' in lbt, lbt[-160:])
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(400)
        cards = await pg.evaluate(ARCCARDS)
        ok('(a) ui1 CHALLENGES: no World airports group and no airport cards (they are FLY destinations now)',
           not [c for c in cards if c['id'].startswith('apt:')] and not await pg.evaluate("()=>!!document.querySelector('#arcCards .cgrp')"), [c['id'] for c in cards])

        # ---------------- (b) the Tokyo landing challenge (no card since ui1, the mode stays): region switch, then the run ----------------
        await pg.evaluate(STUB)
        await pg.evaluate(f"()=>{K}.aptStart('rjtt')"); await pg.wait_for_timeout(300)
        k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),res:JSON.parse(sessionStorage.getItem('kgeuResume')||'null'),rl:window.__reloaded||0})")
        s0 = (k['res'] or {}).get('start') or {}
        ok('(b) aptStart(rjtt) from Arizona: kgeuRegion rjtt and a resume with arc apt, reloads', k['r'] == 'rjtt' and k['rl'] == 1 and s0.get('arc') == 'apt' and s0.get('type') == 'cessna', k)
        await pg.evaluate("()=>{delete window.__kgeuReload;location.reload();}")
        await after_reload(pg, f"()=>window.__kgeu&&{K}.REGION.id==='rjtt'&&{K}.WORLD.ready&&{K}.ARC.on&&{K}.running()")
        await pg.wait_for_timeout(400)
        s = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),e=K.RWY_ENDS.find(e=>e.num==='34R');
          return {{kind:K.ARC.kind,runs:Object.keys(K.LB.E.runs),g:s.onGround,agl:Math.round(s.agl),d:Math.round(Math.hypot(s.pos.x-e.x,s.pos.z-e.z)),dest:K.dest(),
            hud:document.getElementById('miss').classList.contains('on')&&document.getElementById('missS').textContent,toast:document.getElementById('toast').textContent,type:s.type,
            menu:document.getElementById('menu').classList.contains('on')}}}}""")
        ok('(b) after the real reload the Tokyo challenge runs: board apt:RJTT, airborne about 9 km from 34R',
           s['kind'] == 'apt' and 'apt:RJTT' in s['runs'] and not s['g'] and 700 < s['agl'] < 830 and 8500 < s['d'] < 9300 and s['dest'] == {'apt': 'Haneda', 'num': '34R'} and not s['menu'] and s['type'] == 'cessna', s)
        ok('(b) the HUD names Tokyo Haneda runway 34R', s['hud'] == 'Tokyo Haneda runway 34R' and s['toast'] == 'Tokyo Haneda landing: runway 34R. Go!', (s['hud'], s['toast']))
        # (d) the city billboard: the stub's champion arrived with the fame fetch
        c0 = await pg.evaluate(f"()=>({{champ:{K}.CITYBB.champ,n:{K}.CITYBB.list.length,fame:{K}.LB.E.fame&&{K}.LB.E.fame.apt}})")
        ok("(d) the fame answer's apt.RJTT champion is on Tokyo's city billboard", c0['champ'] == 'STUBACE' and c0['n'] >= 1, c0)
        r = await land(pg)
        ok('(b) autoland to the results card: Tokyo Haneda landing, points > 0', r['on'] and r['title'].startswith('Tokyo Haneda landing') and int(''.join(ch for ch in r['score'].split('pts')[0] if ch.isdigit()) or 0) > 0, r)
        ok('(b) the card carries the board line', 'Leaderboard' in r['lines'] or 'Sending' in r['lines'] or '#1' in r['lines'], r['lines'])
        await pg.wait_for_timeout(1500)
        best = await pg.evaluate(f"()=>{K}.SCORE.best['apt:RJTT']")
        ok('(b) the score is submitted to apt:RJTT and the best kept per board', ('/submit', 'apt:RJTT') in seen and ('/token', 'apt:RJTT') in seen and best and best['pts'] > 0, (best, [x for x in seen if x[0] in ('/token', '/submit')]))
        # (d) fameApply
        d = await pg.evaluate(f"""()=>{{const K={K},C=K.CITYBB,v0=C.ver,t0=C.list[0].tex.version;
          K.LB.fameApply({{day:20261002,daily:null,top:[],apt:{{RJTT:{{cs:'TESTPILOT',score:1200,mode:'hard'}},LFPG:null,SBRJ:null}}}});
          const a=[C.champ,C.ver>v0,C.list[0].tex.version>t0,JSON.parse(localStorage.getItem('kgeuFame')).apt.RJTT.cs];
          const v1=C.ver,t1=C.list[0].tex.version;K.LB.fameApply({{day:20261002,daily:null,top:[],apt:{{RJTT:null,LFPG:null,SBRJ:null}}}});
          return a.concat([C.champ,C.ver>v1,C.list[0].tex.version>t1]);}}""")
        ok('(d) LB.fameApply at rjtt: TESTPILOT on the billboard, texture redrawn, cached', d[:4] == ['TESTPILOT', True, True, 'TESTPILOT'], d)
        ok('(d) and null takes it back off (redrawn)', d[4:] == [None, True, True], d)
        ok('(a,b,d) no console errors', not pg.errs, pg.errs[:4])
        await pg.context.close()

        # ---------------- (c) the daily rotation ----------------
        print('\n--- daily rotation ---')
        seen.clear()
        pg = await newpage(b, url, BASE)
        scan = await pg.evaluate(f"()=>{{const out=[];for(let i=0;i<40;i++){{sessionStorage.setItem('__off',String(i*86400000));const d={K}.dailySpec();out.push([i,d.region,d.day,d.kind]);}}sessionStorage.setItem('__off','0');return out}}")
        ok('(c) every one of the four regions comes up in a 12 day scan', {x[1] for x in scan[:12]} == {'az', 'rjtt', 'lfpg', 'sbrj'}, [x[1] for x in scan[:12]])
        ok('(c) one spec a day: the 40 days are 40 different dates', len({x[2] for x in scan}) == 40)
        paris = next((x[0] for x in scan if x[1] == 'lfpg' and x[3] == 'landing'), None)   # not a dogfight day (one in five)
        ok('(c) a Paris day in the scan', paris is not None, scan[:12])
        ok('(c) one day in five is a dogfight day, the region draws unchanged', sum(x[3] == 'dogfight' for x in scan) == 8, [x[3] for x in scan[:10]])
        await pg.context.close()
        off = (paris or 0) * 86400000
        pg = await newpage(b, url, BASE, off)
        d1 = await pg.evaluate(f"()=>{K}.dailySpec()")
        await pg.evaluate("()=>location.reload()")
        await after_reload(pg, "()=>!!(window.__kgeu&&window.__kgeu.dailySpec)", 60)
        await splash_gone(pg); await pg.wait_for_timeout(300)
        d2 = await pg.evaluate(f"()=>{K}.dailySpec()")
        ok('(c) the same daily for the same day across two page loads', d1 == d2 and d1['region'] == 'lfpg', (d1, d2))
        cardq = "(s)=>{const c=document.querySelector(s);return {t:c.innerText,tag:!!c.querySelector('.azTag')}}"
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
        ca = await pg.evaluate(cardq, '#arcCards .mcard[data-m=daily]')
        cm = ca   # ui1: one Challenges list, one daily card
        wind = f"wind {d1['wdir']:03d} at {d1['wkt']}"
        ok('(c) the daily card on ARCADE and MISSIONS: Paris CDG, runway 26L, the time and wind, no ARIZONA tag',
           all('Paris CDG' in c['t'] and 'runway 26L' in c['t'] and d1['tod'] in c['t'] and wind in c['t'] and not c['tag'] for c in (ca, cm)), (ca, cm, wind))
        await pg.screenshot(path=os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world_lb_daily_card.png'))
        await pg.evaluate(STUB)
        await finger(pg, '#arcCards .mcard[data-m="daily"]'); await pg.wait_for_timeout(300)
        k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),res:JSON.parse(sessionStorage.getItem('kgeuResume')||'null'),rl:window.__reloaded||0,daily:localStorage.getItem('kgeuDaily')})")
        s0 = (k['res'] or {}).get('start') or {}
        tok0 = [x for x in seen if x == ('/token', 'daily')]
        ok('(c) GO on the Paris daily from Arizona: kgeuRegion lfpg, a resume with arc daily and region lfpg', k['r'] == 'lfpg' and k['rl'] == 1 and s0.get('arc') == 'daily' and s0.get('region') == 'lfpg', k)
        ok('(c) nothing counted yet: no kgeuDaily mark, no daily token asked for', k['daily'] is None and not tok0, (k['daily'], tok0))
        await pg.evaluate("()=>{delete window.__kgeuReload;location.reload();}")
        await after_reload(pg, f"()=>window.__kgeu&&{K}.REGION.id==='lfpg'&&{K}.WORLD.ready&&{K}.ARC.on&&{K}.running()")
        await pg.wait_for_timeout(1500)
        s = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),e=K.RWY_ENDS.find(e=>e.num==='26L');
          return {{kind:K.ARC.kind,type:s.type,tod:K.TOD().id,wdir:s.windBase,wkt:s.windKt,g:s.onGround,d:Math.round(Math.hypot(s.pos.x-e.x,s.pos.z-e.z)),dest:K.dest(),
            daily:JSON.parse(localStorage.getItem('kgeuDaily')||'null'),hud:document.getElementById('missS').textContent}}}}""")
        ok("(c) after the real reload the daily runs at LFPG: today's aircraft, time and wind, to 26L",
           s['kind'] == 'daily' and s['type'] == d1['type'] and s['tod'] == d1['tod'] and s['wdir'] == d1['wdir'] and s['wkt'] == d1['wkt'] and not s['g']
           and s['dest'] == {'apt': 'de Gaulle', 'num': '26L'} and s['hud'] == 'Paris CDG runway 26L', (s, d1))
        tok = [x for x in seen if x == ('/token', 'daily')]
        ok('(c) the attempt is counted once, at the start: kgeuDaily for the day, one daily token', s['daily'] == {'day': d1['day'], 'used': 1} and len(tok) == 1, (s['daily'], tok))
        ok('(c) no console errors', not pg.errs, pg.errs[:4])
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('world_lb_check'))

asyncio.run(main())
