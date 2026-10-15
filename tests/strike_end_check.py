# Fix2 item 5: the strike range (MQ-9A) and the A-10 gun run grade only at the end of the run: every weapon spent and
# nothing still flying, all four targets destroyed, or the 10 minute range time out. Never at the first impact of a
# ripple. The card reads 'Targets N of 4', 'Accuracy (average miss)', 'Time', 'Ended'; 4 of 4 outscores 1 of 4.
# Cases (one fresh page each, all in sim time with stepFrame bursts):
#   A one shot, one hit: not graded, no card after 20 s more, the RANGE clock counting down (sensor and chase readouts)
#   B a salvo of four at target 0: not graded while any missile flies, graded at the last impact, 'Targets 1 of 4'
#   C four kills one by one: graded at the fourth impact, 'Targets 4 of 4', more points than B (and 80 or more)
#   D one hit, then the clock runs out: 'Ended time out', 'Targets 1 of 4'
#   E the A-10: a gun kill, the gun run dry, missiles at targets 1 and 2 and a ripple of two 60 m off target 3:
#     graded only after the last impact, 'Targets 3 of 4', the gun kill counted
# Run: .venv/bin/python tests/strike_end_check.py --case A   (A to E, or all; each case runs well under 100 s)
#      --shots also saves overnight-screenshots/fix2/item5/ (range_sensor_568, range_chase_844, card_844)
import asyncio, sys, os, json, time
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15, ROOT
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'fix2', 'item5')
SCORES = '/tmp/strike_end_scores.json'
STORE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
# in page helpers: step n sim frames (no render) until a condition holds; returns the frames taken or -1
HELP = """()=>{const K=window.__kgeu;window.__se={
  step:(n)=>{for(let i=0;i<n;i++)K.stepFrame(1/30,false,true);},
  until:(f,max)=>{for(let i=0;i<max;i++){if(f())return i;K.stepFrame(1/30,false,true);}return f()?max:-1;},
  card:()=>{const o=document.getElementById('arcOv'),r={};for(const g of o.querySelectorAll('.gl'))r[g.children[0].textContent]=g.children[1].textContent;
    return {on:o.classList.contains('on'),stats:r,title:(o.querySelector('h2,.t,b')||{}).textContent||''};}};}"""

def saveScore(k, v):
    d = {}
    try: d = json.load(open(SCORES))
    except Exception: pass
    d[k] = v; json.dump(d, open(SCORES, 'w'))

async def fresh(b, url, mission='range', vp=IPHONE_15):
    for k in range(3):   # the headless page now and then dies while it loads: try again
        try: pg = await page(b, url, vp=vp, storage=STORE); break
        except Exception as e:
            if k == 2: raise
            print('  (page load failed, retrying)', str(e)[:80])
    await pg.evaluate(f"()=>{K}.mission('{mission}')"); await pg.wait_for_timeout(1200)
    await pg.evaluate(HELP)
    return pg

async def aim(pg, i, off=0, wait=1800):
    # aim (re-aim each try: the orbit swings the ball past the gimbal at times)
    r = await pg.evaluate(f"""([i,off,wait])=>{{const K={K};let r=null;
      const n=__se.until(()=>{{r=K.strikeAim(i,off);return r.ok;}},wait);return Object.assign({{n:n}},r);}}""", [i, off, wait])
    return r

async def fire(pg):
    return await pg.evaluate(f"()=>{K}.strikeFire()")

async def until_impacts(pg, flying_le=0, max_frames=2400):
    return await pg.evaluate(f"([f,m])=>__se.until(()=>{K}.strike().flying<=f,m)", [flying_le, max_frames])

async def S(pg):
    return await pg.evaluate(f"()=>{K}.strike()")

async def card_after(pg, frames=180):
    await pg.evaluate(f"(n)=>__se.until(()=>__se.card().on,n)", frames)
    await pg.evaluate(f"()=>{K}.stepFrame(1/60)")
    return await pg.evaluate("()=>__se.card()")

def static_targets_js():
    return f"()=>{K}.STRIKE.targets.map((t,i)=>({{i:i,moving:!!t.moving,dead:!!t.dead,kind:t.kind}}))"

async def case_A(b, url, shots):
    pg = await fresh(b, url)
    s0 = await S(pg)
    ok('A: the range opens with 10 minutes on the clock', s0['active'] and s0['limit'] == 600 and s0['left'] > 595 and not s0['cleared'], str(s0))
    a = await aim(pg, 0); ok('A: target 0 locked and in range', a['ok'], str(a))
    ok('A: one missile away', await fire(pg))
    n = await until_impacts(pg); s1 = await S(pg)
    ok('A: the missile comes down and kills target 0', n >= 0 and s1['hits'] == 1 and s1['flying'] == 0, f'{n} frames {s1}')
    ok('A: one hit does not grade the run', not s1['cleared'] and s1['ended'] == '', str(s1))
    await pg.evaluate("()=>__se.step(600)")
    s2 = await S(pg); c = await pg.evaluate("()=>__se.card()")
    ok('A: no results card 20 s after the hit', not c['on'] and not s2['cleared'], str(c))
    ok('A: the range clock counts down', s2['left'] < s1['left'] - 19, f"{s1['left']:.1f} -> {s2['left']:.1f}")
    await pg.evaluate(f"()=>{K}.stepFrame(1/60)")
    mid = await pg.evaluate("()=>document.getElementById('shMid').textContent")
    ok('A: the sensor view shows RANGE m:ss on the MSL line', 'MSL 3' in mid and 'RANGE 9:' in mid, repr(mid))
    await chase_check(pg, 'A')
    ok('A: no page errors', not pg.errs, pg.errs[:2])
    await pg.close()

async def chase_check(pg, tag, shot=None):
    # leave the sensor view for the chase view, read the chip
    await pg.evaluate(f"()=>{{const K={K};let n=0;while(K.camMode()!==0&&n++<6)K.cycleCam();K.stepFrame(1/60);K.stepFrame(1/60);}}")
    r = await pg.evaluate("""()=>{const e=document.getElementById('hRng'),b=e.getBoundingClientRect();
      return {txt:e.textContent,vis:getComputedStyle(e).display!=='none'&&b.width>0,l:b.left,r:b.right,t:b.top,b:b.bottom,W:innerWidth,H:innerHeight,
        cam:window.__kgeu.camMode(),lo:e.classList.contains('lo'),num:getComputedStyle(e).fontVariantNumeric}}""")
    ok(f'{tag}: chase view shows the RANGE chip', r['vis'] and r['txt'].startswith('RANGE ') and r['cam'] == 0, str(r))
    ok(f'{tag}: the chip stays out of the middle third', r['r'] < r['W'] / 3, str(r))
    ok(f'{tag}: tabular numerals', 'tabular-nums' in r['num'], r['num'])
    if shot: await pg.screenshot(path=shot)
    return r

async def case_B(b, url, shots):
    pg = await fresh(b, url)
    a = await aim(pg, 0); ok('B: target 0 locked and in range', a['ok'], str(a))
    fired = 0
    for k in range(4):
        fired += 1 if await fire(pg) else 0
        await pg.evaluate("()=>__se.step(7)")       # four shots inside one second
    s0 = await S(pg)
    ok('B: a ripple of four is allowed', fired == 4 and s0['shots'] == 4, str(s0))
    dim = await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);return document.getElementById('bFire').classList.contains('dim');}}")
    ok('B: FIRE is dim with no missiles left', dim)
    mid = await pg.evaluate("()=>document.getElementById('shMid').textContent")
    ok('B: the counter shows missiles left: MSL 0', 'MSL 0' in mid, repr(mid))
    n = await until_impacts(pg, 3); s1 = await S(pg)
    ok('B: first impact kills target 0', n >= 0 and s1['hits'] == 1, f'{n} {s1}')
    ok('B: not graded while missiles fly', not s1['cleared'] and s1['flying'] > 0, str(s1))
    n = await until_impacts(pg, 0); s2 = await S(pg)
    ok('B: graded once the last missile is down (weapons spent)', n >= 0 and s2['cleared'] and s2['flying'] == 0 and s2['ended'] == 'spent', str(s2))
    c = await card_after(pg)
    ok('B: the card shows Targets 1 of 4, Ended weapons spent', c['on'] and c['stats'].get('Targets', '').startswith('1 of 4') and c['stats'].get('Ended') == 'weapons spent', str(c))
    ok('B: the card shows accuracy and time', 'Accuracy (average miss)' in c['stats'] and 'Time' in c['stats'], str(c['stats']))
    ok('B: no page errors', not pg.errs, pg.errs[:2])
    saveScore('B', s2['pts'])
    print('  B pts', s2['pts'])
    await pg.close()
    return s2['pts']

async def case_C(b, url, shots, bpts):
    pg = await fresh(b, url)
    tg = await pg.evaluate(static_targets_js())
    order = [t['i'] for t in tg if not t['moving']]
    kills = 0
    for j, i in enumerate(order):
        if kills == 4: break
        a = await aim(pg, i, 0, 900)
        if not a['ok']: print('  skip target', i, a); continue
        await fire(pg); n = await until_impacts(pg); s = await S(pg)
        kills = s['hits']
        if kills < 4:
            ok(f'C: not graded after kill {kills}', not s['cleared'], str(s))
    s = await S(pg)
    ok('C: four kills grade the run at the fourth impact (all targets destroyed)', s['hits'] == 4 and s['cleared'] and s['ended'] == 'all', str(s))
    c = await card_after(pg)
    ok('C: the card shows Targets 4 of 4, Ended all targets destroyed', c['on'] and c['stats'].get('Targets', '').startswith('4 of 4') and c['stats'].get('Ended') == 'all targets destroyed', str(c))
    if bpts is None:
        try: bpts = json.load(open(SCORES)).get('B')
        except Exception: bpts = None
    ok('C: 4 of 4 scores in the top tier (80 or more)', s['pts'] is not None and s['pts'] >= 80, str(s['pts']))
    if bpts is not None: ok('C: 4 of 4 outscores the 1 of 4 salvo (B)', s['pts'] > bpts, f"C {s['pts']} B {bpts}")
    else: print('  (B not run yet: no B score to compare)')
    print('  C pts', s['pts'], c['stats'])
    ok('C: no page errors', not pg.errs, pg.errs[:2])
    if shots:
        os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, 'card_844.png'))
    await pg.close()

async def case_D(b, url, shots):
    pg = await fresh(b, url)
    a = await aim(pg, 0); await fire(pg); await until_impacts(pg); s0 = await S(pg)
    ok('D: one hit, not graded', s0['hits'] == 1 and not s0['cleared'], str(s0))
    # the last minute turns the clock amber
    await pg.evaluate(f"()=>{K}.strikeClock({K}.strike().left-45)")
    await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
    lo = await pg.evaluate("()=>{const e=document.querySelector('#shMid .rngT');return e?{t:e.textContent,lo:e.classList.contains('lo'),c:getComputedStyle(e).color}:null}")
    ok('D: amber under 60 s', lo and lo['lo'] and lo['t'].startswith('RANGE 0:4'), str(lo))
    if shots:
        os.makedirs(SHOTS, exist_ok=True)
        await chase_check(pg, 'D', os.path.join(SHOTS, 'range_chase_844_amber.png'))
    done = await pg.evaluate(f"()=>{K}.strikeClock(600)"); s1 = await S(pg)
    ok('D: the time out grades the run', done and s1['cleared'] and s1['ended'] == 'time' and s1['left'] == 0, str(s1))
    c = await card_after(pg)
    ok("D: the card shows 'Ended time out' and 'Targets 1 of 4'", c['on'] and c['stats'].get('Ended') == 'time out' and c['stats'].get('Targets', '').startswith('1 of 4'), str(c))
    ok('D: no page errors', not pg.errs, pg.errs[:2])
    await pg.close()

async def case_E(b, url, shots):
    pg = await fresh(b, url, 'gunrun')
    s0 = await S(pg); ok('E: the gun run is on', s0['active'], str(s0))
    # the gun: the jet 900 m from target 0, nose on, the pod locked, GUN held (gunrun_check's set up)
    await pg.evaluate(f"""()=>{{const K={K},s=K.state(),t=K.STRIKE.targets[0];s.ap=null;s.apW=null;
      s.pos.set(t.x,t.y+260,t.z+900);const d=new THREE.Vector3(t.x-s.pos.x,t.y-s.pos.y,t.z-s.pos.z).normalize();
      s.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);s.vel.copy(d).multiplyScalar(110);s.w.set(0,0,0);K.strikeAim(0,0);K.stepFrame(1/60);
      K.DF.gunHeld=true;}}""")
    n = await pg.evaluate(f"()=>__se.until(()=>{K}.strike().hits>=1,60)")
    await pg.evaluate(f"()=>{{{K}.DF.gunHeld=false;__se.step(3);}}")
    s1 = await S(pg)
    ok('E: the gun takes target 0', n >= 0 and s1['hits'] == 1 and s1['gun'] == 1, str(s1))
    ok('E: a gun kill does not grade the run', not s1['cleared'], str(s1))
    # run the gun dry (a short last burst: only the last rounds left)
    await pg.evaluate(f"()=>{{const K={K};K.HOG.rounds=4;K.DF.gunHeld=true;__se.step(6);K.DF.gunHeld=false;__se.step(2);}}")
    s2 = await S(pg); r = await pg.evaluate(f"()=>{K}.HOG.rounds")
    ok('E: gun dry, missiles left: not graded', r <= 0 and not s2['cleared'], f'{r} {s2}')
    async def level():
        await pg.evaluate(f"""()=>{{const K={K},s=K.state(),R=K.RANGE;s.pos.set(R.x,K.groundHeight(R.x,R.z)+1500,R.z+2500);
          s.quat.set(0,0,0,1);s.vel.set(0,0,-110);s.w.set(0,0,0);K.snapCam();K.stepFrame(1/60);}}""")
    for i in (1, 2):
        await level(); a = await aim(pg, i, 0, 300)
        ok(f'E: target {i} locked', a['ok'], str(a))
        await fire(pg); await until_impacts(pg); s = await S(pg)
        ok(f'E: missile at target {i} down, not graded', s['flying'] == 0 and not s['cleared'], str(s))
    await level(); a = await aim(pg, 3, 60, 300); ok('E: ground point 60 m off target 3', a['ok'], str(a))
    await fire(pg); await pg.evaluate("()=>__se.step(6)"); await fire(pg)
    s = await S(pg); ok('E: the last two away as a ripple', s['shots'] == 4 and s['flying'] == 2, str(s))
    n = await until_impacts(pg, 1); s = await S(pg)
    ok('E: Winchester but one missile flying: not graded', n >= 0 and s['flying'] == 1 and not s['cleared'], str(s))
    n = await until_impacts(pg, 0); s = await S(pg)
    ok('E: graded at the last impact', n >= 0 and s['cleared'] and s['ended'] == 'spent', str(s))
    c = await card_after(pg)
    ok("E: the card shows 'Targets 3 of 4' with the gun kill", c['on'] and c['stats'].get('Targets', '').startswith('3 of 4') and '1 by gun' in c['stats'].get('Targets', ''), str(c))
    ok('E: no page errors', not pg.errs, pg.errs[:2])
    ok('E: the gun run card', 'Gun run' in await pg.evaluate("()=>document.getElementById('arcOv').textContent"))
    await pg.close()

async def shots_case(p, url):
    # the readouts at 568x320 (sensor) and 844x390 (chase), plus 844 sensor and 568 chase; a browser each
    os.makedirs(SHOTS, exist_ok=True)
    for vp, nm in (({'width': 568, 'height': 320}, '568'), (IPHONE_15, '844')):
        b = await launch(p)
        pg = await fresh(b, url, vp=vp)
        await aim(pg, 0); await pg.evaluate("()=>__se.step(30)")
        await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);{K}.stepFrame(1/60);}}")
        await pg.wait_for_timeout(200)
        r = await pg.evaluate("""()=>{const e=document.querySelector('#shMid .rngT'),b=e.getBoundingClientRect(),d=document.getElementById('dock').getBoundingClientRect();
          return {t:e.textContent,l:b.left,r:b.right,W:innerWidth,dockL:d.left}}""")
        ok(f'{nm}: sensor RANGE readout clear of the button dock', r['r'] < r['dockL'] and r['l'] > 0, str(r))
        await pg.screenshot(path=os.path.join(SHOTS, f'range_sensor_{nm}.png'))
        await chase_check(pg, nm, os.path.join(SHOTS, f'range_chase_{nm}.png'))
        await b.close()

async def main():
    args = sys.argv[1:]
    case = args[args.index('--case') + 1].upper() if '--case' in args else 'ALL'
    shots = '--shots' in args
    srv, url = serve()
    async with async_playwright() as p:
        t0 = time.time(); bpts = None
        # a fresh browser for every case: headless Chromium with SwiftShader does not survive a second context
        for k, fn in (('A', case_A), ('B', case_B), ('C', case_C), ('D', case_D), ('E', case_E)):
            if case not in (k, 'ALL'): continue
            b = await launch(p)
            r = await (fn(b, url, shots, bpts) if k == 'C' else fn(b, url, shots))
            if k == 'B': bpts = r
            await b.close()
        if case == 'SHOTS' or (shots and case == 'ALL'): await shots_case(p, url)
        print(f'  ({time.time()-t0:.0f} s)')
    sys.exit(ok.done('strike_end_check'))
asyncio.run(main())
