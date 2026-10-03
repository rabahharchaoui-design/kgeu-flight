# Red Flag Dogfight defense (5.3): a bandit parked on our six searches, locks and launches (RWR none -> search ->
# lock -> launch, the red edges and the missile arrow), its missile takes real time and hits a jet flying straight,
# three hits are the eject and the results card says so, FLARES timed 1.5 s out (DF.test.decoy=1) decoy it (Good
# flares, 28 left), Easy's auto flares go twice a wave and not a third time, the hard deck (Pull up above it, one hit
# a second under it, then grace), no tower chatter in 60 s of fight, the subtitle strip and the wave card overlap
# nothing at 844x390 and 568x320, FLARES 60 pt or larger, no console errors.
# Run: .venv/bin/python tests/dogfight_defense_check.py
import asyncio, re, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
# the frame loop stays held: fixed 0.1 s sim steps, no real time frames in between (deterministic, and no draws)
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);}"
# step until cond (a JS expression over K and D) holds or max sim seconds pass; returns the sim seconds taken and a
# sample of probe (a JS expression) taken at sample seconds in
UNTIL = """([cond,max,probe,at])=>{const K=window.__kgeu,D=K.DF,s=K.state(),t0=s.time,f=new Function('K','D','return ('+cond+')'),pr=probe?new Function('K','D','return ('+probe+')'):null;
  let smp=null;for(let i=0;i<max*10;i++){K.stepFrame(0.1,false,true);if(pr&&smp===null&&s.time-t0>=at)smp=pr(K,D);if(f(K,D))break;}return {t:s.time-t0,smp:smp};}"""
TL = "(max)=>{const K=window.__kgeu,D=K.DF,s=K.state(),t0=s.time,tl={};D.bandits.forEach(b=>{b.rw=0;b.rwT=0;});for(let i=0;i<max*10;i++){K.stepFrame(0.1,false,true);if(!(D.rwr in tl))tl[D.rwr]=+D.waveT.toFixed(2);if(D.rwr==='launch')break;}tl.waveT=+D.waveT.toFixed(2);return tl;}"
# bandit i at d metres along our nose (off: radians, pi = straight behind), flying our heading and speed, straight and level
PLACE = """([i,d,off])=>{const K=window.__kgeu,s=K.state(),D=K.DF,b=D.bandits[i];D.test.hold=true;
  const q=s.quat.clone();if(off)q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),off));
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(q);b.p.copy(s.pos).addScaledVector(n,d);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);b.g.position.copy(b.p);return true;}"""
FOE = f"()=>{{const D={K}.DF,s={K}.state(),m=D.msl.find(m=>m.on&&m.foe);if(!m)return null;const dx=s.pos.x-m.p.x,dy=s.pos.y-m.p.y,dz=s.pos.z-m.p.z,R=Math.hypot(dx,dy,dz),vc=-(dx*(s.vel.x-m.v.x)+dy*(s.vel.y-m.v.y)+dz*(s.vel.z-m.v.z))/R;return {{R:R,tti:vc>1?R/vc:99,dec:m.dec}}}}"
ST = f"()=>{{const D={K}.DF;return {{hits:D.hits,dmg:D.dmg,on:D.on,done:D.done,why:D.why,ej:D.ej,rwr:D.rwr,saves:D.flareSaves,flares:D.flares,auto:D.autoLeft,calls:D.calls.slice(),last:D.lastCall,foe:D.msl.filter(m=>m.on&&m.foe).length}}}}"
FTY = "(ft)=>(ft-1071)/3.28084+1.5"

async def step(pg, secs):
    await pg.evaluate(STEP, int(round(secs * 10)))

async def until(pg, cond, mx, probe=None, at=0):
    return await pg.evaluate(UNTIL, [cond, mx, probe, at])

async def start(pg, quiet=True):
    await pg.evaluate(f"()=>{{const D={K}.DF;D.test.noBanditFire={'true' if quiet else 'false'};D.test.decoy=0;D.test.noDecoy=false;{K}.DF.test.noBrief=true;{K}.dfStart();}}")
    await pg.wait_for_timeout(400); await step(pg, 0.2)

def ovl(a, b):
    return a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']

RECTS = """()=>{const R=s=>{const e=document.querySelector(s);if(!e)return null;const c=getComputedStyle(e);if(c.display==='none'||c.visibility==='hidden'||e.offsetParent===null&&c.position!=='fixed')return null;
    const r=e.getBoundingClientRect();return r.width<1?null:{x:r.x,y:r.y,w:r.width,h:r.height}};
  return {sub:R('#dfSub span'),fox:R('#bFox'),gun:R('#bGun'),flr:R('#bFlr'),view:R('#bCam'),hint:R('#stickHint'),thr:R('#thr'),card:R('#miss'),cardT:R('#missT'),cardS:R('#missS'),
    seek:R('#dfHud .dfSeek.on b'),hud:R('#hud'),pause:R('#bPause'),tk:R('#tk'),map:R('#map'),subOn:document.getElementById('dfSub').classList.contains('on'),W:innerWidth,H:innerHeight}}"""

async def layout(pg, label):
    await pg.evaluate(f"()=>{K}.dfCall('launch')"); await step(pg, 0.2)
    r = await pg.evaluate(RECTS)
    s = r['sub']
    others = [k for k in ('fox', 'gun', 'flr', 'view', 'hint', 'thr', 'card', 'seek', 'hud', 'pause', 'tk', 'map') if r[k]]
    hit = [k for k in others if ovl(s, r[k])] if s else ['no subtitle']
    ok(f'{label}: the subtitle shows in the bottom strip on one line, overlapping nothing (buttons, VIEW, stick, throttle, card, seeker, gauges)',
       s and r['subOn'] and not hit and s['h'] < 30 and s['y'] + s['h'] > r['H'] * 0.75 and r['seek'] is not None, {'hit': hit, 'sub': s, 'seek': r['seek']})
    c = r['card']
    bad = [k for k in ('hud', 'pause', 'tk', 'map') if r[k] and ovl(c, r[k])]
    ok(f'{label}: the wave card is one line each (no wrap) and overlaps no gauge, pause or ticker',
       c and not bad and r['cardT']['h'] < 24 and r['cardS']['h'] < 22, {'bad': bad, 'card': c, 'hud': r['hud'], 'tk': r['tk']})
    f = r['flr']
    fb = [k for k in ('fox', 'gun', 'view', 'thr', 'sub') if r[k] and ovl(f, r[k])]
    ok(f'{label}: FLARES 60 pt or larger, on screen, overlapping nothing', f and min(f['w'], f['h']) >= 60 and not fb and f['x'] + f['w'] <= r['W'] and f['y'] + f['h'] <= r['H'], (f, fb))

# 5.4 A1: the edge arrows ride a track clear of the HUD. Three bandits at 3, 6 and 9 o'clock and a missile at 6
# o'clock: every arrow and its label clear of every piece of furniture, none on another, the missile's at the bottom
ARROWS = """()=>{const u=document.getElementById('uiroot').getBoundingClientRect(),R=e=>{if(typeof e==='string')e=document.querySelector(e);if(!e)return null;const c=getComputedStyle(e);
    if(c.display==='none'||c.visibility==='hidden')return null;const r=e.getBoundingClientRect();return r.width<1?null:{x:r.x,y:r.y,w:r.width,h:r.height}};
  const f={};for(const [k,s] of [['map','#map'],['hud','#hud'],['pause','#bPause'],['card','#miss'],['tk','#tk'],['stick','#stickHint'],['view','#bCam'],['fox','#bFox'],['gun','#bGun'],['flr','#bFlr'],['thr','#thr']]){const r=R(s);if(r)f[k]=r;}
  const sb=document.getElementById('dfSub').getBoundingClientRect();f.strip={x:sb.x,y:sb.bottom-28,w:sb.width,h:28};
  const a=[...document.querySelectorAll('#dfHud .dfArr.on')].map(e=>({k:'g',b:R(e.firstChild),t:R(e.lastChild),txt:e.innerText}));
  const m=document.querySelector('#dfHud .dfMw.on');if(m)a.push({k:'r',b:R(m.firstChild),t:R(m.lastChild),txt:m.innerText,vis:m.classList.contains('vis')});
  return {f:f,a:a,W:innerWidth,H:innerHeight}}"""

async def arrows(pg, label):
    await start(pg)
    await pg.evaluate(f"()=>{K}.DF.test.wave(3)")
    for i, off in ((0, 3.14159), (1, -1.5708), (2, 1.5708)):
        await pg.evaluate(PLACE, [i, 3000 if i == 0 else 2000, off])
    await pg.evaluate(f"()=>{K}.DF.test.launchAt()"); await step(pg, 0.2)
    r = await pg.evaluate(ARROWS)
    hits = []
    for x in r['a']:
        for part in ('b', 't'):
            if not x[part]: continue
            hits += [(x['k'], x['txt'], part, k) for k, fr in r['f'].items() if ovl(x[part], fr)]
            if x[part]['x'] < 0 or x[part]['y'] < 0 or x[part]['x'] + x[part]['w'] > r['W'] or x[part]['y'] + x[part]['h'] > r['H']: hits.append((x['k'], part, 'off screen'))
    pairs = []
    for i in range(len(r['a'])):
        for j in range(i + 1, len(r['a'])):
            for p1 in ('b', 't'):
                for p2 in ('b', 't'):
                    a, b2 = r['a'][i][p1], r['a'][j][p2]
                    if a and b2 and ovl(a, b2): pairs.append((r['a'][i]['txt'], r['a'][j]['txt']))
    g = [x for x in r['a'] if x['k'] == 'g']; m = next((x for x in r['a'] if x['k'] == 'r'), None)
    ok(f'{label}: three bandit arrows and the missile arrow, each with its label', len(g) == 3 and m and not m['vis'] and all(x['t'] for x in r['a']) and re.match(r"^(5|6|7) o'clock", m['txt'] or ''), [(x['k'], x['txt']) for x in r['a']])
    ok(f'{label}: no arrow or label on the gauges, map, pause, wave card, ticker, stick, VIEW, weapons, throttle or call strip', not hits, hits[:6])
    ok(f'{label}: no two arrows or labels overlap (the green one makes way for the red)', not pairs, pairs[:4])
    ok(f'{label}: the missile at 6 o\'clock rides the bottom of the track, above the call strip', m and m['b']['y'] + m['b']['h'] / 2 > r['H'] * 0.6 and m['b']['y'] + m['b']['h'] <= r['f']['strip']['y'], m and m['b'])
    return r

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
        # ---- no tower chatter in 60 s of fight (and a forced chatter line is dropped too) ----
        await start(pg)
        await pg.evaluate(f"()=>{{{K}.radioLog(true);{K}.vqLog(true);}}")
        seen = set()
        for _ in range(12):
            await step(pg, 5)
            seen.add(await pg.evaluate("()=>{const a=document.getElementById('atc');return a.classList.contains('on')&&getComputedStyle(a).display!=='none'?a.innerText:''}"))
        await pg.evaluate(f"()=>{K}.chatNow()"); await step(pg, 1)
        lg = await pg.evaluate(f"()=>{{const F=w=>w!=='VIPER 2'&&w!=='SENTRY'&&w!=='COCKPIT';return {{radio:{K}.radioLog(false).filter(l=>F(l.who)).map(l=>l.text),vq:{K}.vqLog(false).filter(l=>F(l.who)).map(l=>l.text),on:{K}.DF.on}}}}")   # 5.4: the fight's own calls do play
        ok('60 sim seconds of dogfight: no tower or chatter line plays, no tower subtitle shows', lg['on'] and not lg['radio'] and not lg['vq'] and seen <= {''}, (lg, seen))
        # ---- the subtitle strip, the wave card and FLARES at 844x390 and 568x320 ----
        await layout(pg, '844x390')
        await arrows(pg, '844x390')
        await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400); await step(pg, 0.2)
        await layout(pg, '568x320')
        await arrows(pg, '568x320')
        # Easy's launch line fits the 568 strip on one line, no ellipsis
        await pg.evaluate(f"()=>{{{K}.setSkill('rookie');{K}.DF.subAge=9;{K}.dfCall('launch');}}")
        ez = await pg.evaluate("()=>{const s=document.querySelector('#dfSub span');return {t:s.textContent,fit:s.scrollWidth<=s.clientWidth+1,h:s.getBoundingClientRect().height}}")
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        ok('568x320: the Easy launch subtitle fits the strip on one line without an ellipsis', ez['t'] == 'Missile! Tap FLARES, turn hard!' and ez['fit'] and ez['h'] < 30, ez)
        await pg.set_viewport_size({'width': 932, 'height': 430}); await pg.wait_for_timeout(400); await step(pg, 0.2)
        await layout(pg, '932x430')
        await arrows(pg, '932x430')
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        # ---- RWR: a bandit parked 1.5 km on our six (Hard: lock after 3 s, launch 2 to 4 s later, none in a wave's first 8 s) ----
        await start(pg, quiet=False)
        await pg.evaluate(PLACE, [0, 1500, 3.14159])
        tl = await pg.evaluate(TL, 16)
        ok('a bandit on our six: RWR goes search, then lock (after the 3 s lock time), then launch (not before 8 s into the wave)',
           list(tl.keys())[:3] == ['search', 'lock', 'launch'] and tl['lock'] - tl['search'] >= 2.85 and tl['launch'] >= 7.95, tl)
        sv = await pg.evaluate(f"""()=>{{const m=document.querySelector('#dfHud .dfMw.on');return {{vig:document.getElementById('dfVig').className,arrow:m?m.innerText:'',vis:m?m.classList.contains('vis'):null,last:{K}.DF.lastCall,shots:{K}.DF.eShots}}}}""")
        ok('the launch: red pulsing edges, a red arrow with the clock and range (6 o\'clock), the Missile launch call',
           sv['vig'] == 'launch' and re.match(r"^(5|6|7) o'clock \d+\.\d nm$", sv['arrow'] or '') and sv['last'] == 'Missile launch' and sv['shots'] == 1, sv)
        u = await until(pg, "D.hits>0||!D.msl.some(m=>m.on&&m.foe)", 10, "document.getElementById('dfVig').className", 0.3)
        t, vig_mid = u['t'], u['smp']
        s = await pg.evaluate(ST)
        ok('the missile takes over 1 s and hits a jet flying straight: hits 1, the We\'re hit call', s['hits'] == 1 and s['dmg'] == 1 and t > 1.0 and s['last'] == "We're hit!", (round(t, 1), s))
        ok('the edges stay red while it flies', vig_mid == 'launch', vig_mid)
        # ---- three hits: the eject, the results card with the reason ----
        await step(pg, 2.2)
        for n in (2, 3):
            await pg.evaluate(PLACE, [0, 1500, 3.14159]); await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
            await until(pg, "D.hits>=%d||!D.msl.some(m=>m.on&&m.foe)" % n, 8)
            s = await pg.evaluate(ST)
            if n == 2:
                ok('the second hit: hits 2, black smoke and less g (DF.dmg 2)', s['hits'] == 2 and s['dmg'] == 2 and not s['done'], s)
                await step(pg, 2.2)
        w = await pg.evaluate("()=>document.getElementById('warn').textContent")
        await step(pg, 2.5); await pg.wait_for_timeout(300)
        r = await pg.evaluate(f"()=>({{why:{K}.DF.why,ej:{K}.DF.ej,on:{K}.DF.on,card:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText,crash:document.body.classList.contains('crashOn'),plane:{K}.plane().g.visible}})")
        ok('the third hit is the eject: EJECT EJECT, the jet gone, the run over', s['hits'] == 3 and 'EJECT' in w and r['ej'] and not r['on'] and r['why'] == 'hits' and not r['plane'], (s, w, r))
        ok('the results card (not the crash card) says shot down, you ejected, hits 3 of 3', r['card'] and not r['crash'] and 'shot down, you ejected' in r['title'].lower() and '3 of 3' in r['lines'], (r['title'], r['lines']))
        # ---- FLARES at 1.5 s to go with DF.test.decoy=1: no hit, Good flares, 28 left ----
        await start(pg)
        await pg.evaluate(f"()=>{{{K}.DF.test.decoy=1;}}")
        await pg.evaluate(PLACE, [0, 3500, 3.14159]); await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
        await until(pg, "(()=>{const m=D.msl.find(m=>m.on&&m.foe),s=K.state();if(!m)return true;const dx=s.pos.x-m.p.x,dy=s.pos.y-m.p.y,dz=s.pos.z-m.p.z,R=Math.hypot(dx,dy,dz),vc=-(dx*(s.vel.x-m.v.x)+dy*(s.vel.y-m.v.y)+dz*(s.vel.z-m.v.z))/R;return vc>1&&R/vc<=1.55;})()", 8)
        f = await pg.evaluate(FOE)
        await finger(pg, '#bFlr')
        f2 = await pg.evaluate(FOE)
        await step(pg, 4)
        s = await pg.evaluate(ST)
        ok('FLARES tapped 1.5 s out (decoy forced): the missile goes for them, no hit, flareSaves 1, 28 flares, Good flares',
           f and 1.2 <= f['tti'] <= 1.6 and f2 and f2['dec'] and s['hits'] == 0 and s['saves'] == 1 and s['flares'] == 28 and s['foe'] == 0 and 'flaresave' in s['calls'] and
           await pg.evaluate("()=>document.getElementById('bFlrN').textContent==='28'"), (f, f2, s))
        # ---- Easy: auto flares twice a wave, then not a third time ----
        await pg.evaluate(f"()=>{K}.setSkill('rookie')")
        await start(pg)
        res = []
        for n in range(3):
            await pg.evaluate(PLACE, [0, 2500, 3.14159]); await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
            if n == 0: ez = await pg.evaluate(f"()=>{K}.DF.lastCall")
            await until(pg, "!D.msl.some(m=>m.on&&m.foe)", 9)
            s = await pg.evaluate(ST)
            res.append({'hits': s['hits'], 'auto': s['auto'], 'nAuto': s['calls'].count('autoflare'), 'flares': s['flares']})
            await step(pg, 2.2)
        ok('Easy launch subtitle in plain English', ez == 'Missile! Tap FLARES, turn hard!', ez)
        ok('Easy: the jet flares by itself at the first two missiles (no hits), the third gets through',
           [x['nAuto'] for x in res] == [1, 2, 2] and [x['hits'] for x in res] == [0, 0, 1] and res[1]['auto'] == 0, res)
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        # ---- the hard deck ----
        await start(pg)
        await pg.evaluate(f"([y])=>{{const s={K}.state();s.pos.y=y;s.vel.y=-12;}}", [await pg.evaluate(FTY, 5700)])
        await step(pg, 0.3)
        d1 = await pg.evaluate(f"()=>({{w:document.getElementById('warn').textContent,calls:{K}.DF.calls.slice(),hits:{K}.DF.hits}})")
        ok('under 6,000 ft and descending: HARD DECK 5,000 flashes and Pull up is called, no hit yet', 'HARD DECK 5,000' in d1['w'] and 'pullup' in d1['calls'] and d1['hits'] == 0, d1)
        y48 = await pg.evaluate(FTY, 4800)
        hold = f"([y])=>{{const s={K}.state();s.pos.y=y;s.vel.y=Math.min(s.vel.y,0);}}"
        for _ in range(4):
            await pg.evaluate(hold, [y48]); await step(pg, 0.4)
        d2 = await pg.evaluate(ST)
        for _ in range(8):
            await pg.evaluate(hold, [y48]); await step(pg, 0.4)
        d3 = await pg.evaluate(ST)
        ok('over 1 s under 5,000 ft: one hit, the hard deck call, no explosion damage', d2['hits'] == 1 and d2['dmg'] == 0 and d2['last'].startswith('Hard deck'), d2)
        ok('then 6 s of grace: still one hit 3 s later', d3['hits'] == 1, d3)
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('dogfight_defense_check'))
asyncio.run(main())
