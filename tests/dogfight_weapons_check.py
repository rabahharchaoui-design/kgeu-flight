# Red Flag Dogfight offense (5.2): target boxes and an edge arrow, the Fox 2 seeker (search, then lock after
# the configured time), a missile with real flight time that kills (and a forced flare decoy that misses),
# FOX 2 without a lock fires nothing, the gun kills at 400 m and does nothing at 2 km, the kill call, the kill
# cam passing through stepFrame, the weapon buttons' size and layout, AUTO LAND/GEAR/BRAKE hidden in the fight.
# Run: .venv/bin/python tests/dogfight_weapons_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);}"
# bandit i at d metres along the nose (or off it by off radians, positive to the left), flying our way and speed: straight and level (test.hold)
PLACE = """([i,d,off])=>{const K=window.__kgeu,s=K.state(),D=K.DF,b=D.bandits[i];D.test.hold=true;
  const q=s.quat.clone();if(off)q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),off));
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(q);b.p.copy(s.pos).addScaledVector(n,d);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);return true;}"""
GUNHOLD = "(on)=>{const g=document.getElementById('bGun');g.dispatchEvent(new PointerEvent(on?'pointerdown':'pointerup',{pointerId:77,bubbles:true,pointerType:'touch',isPrimary:false}));}"

async def step(pg, secs):
    await pg.evaluate(STEP, int(round(secs * 10)))

def boxes_ok(r):
    ks = list(r.keys())
    for i in range(len(ks)):
        a = r[ks[i]]
        if ks[i] in ('fox', 'gun', 'flr') and min(a['w'], a['h']) < 60: return False, ks[i] + ' under 60'
        for j in range(i + 1, len(ks)):
            b = r[ks[j]]
            if a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']:
                if ks[i] in ('fox', 'gun', 'flr') or ks[j] in ('fox', 'gun', 'flr'): return False, ks[i] + ' overlaps ' + ks[j]
    return True, ''

LAYOUT = """()=>{const R=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,vis:getComputedStyle(e).display!=='none'&&e.offsetParent!==null}};
  const o={fox:R('#bFox'),gun:R('#bGun'),flr:R('#bFlr'),thr:R('#thr'),pause:R('#bPause'),stick:R('#stickZone'),view:R('#bCam')};
  o.pause.w=Math.max(o.pause.w,60);o.pause.h=Math.max(o.pause.h,60);o.stick.w=Math.max(o.stick.w,60);o.stick.h=Math.max(o.stick.h,60);o.thr.w=Math.max(o.thr.w,60);
  return {r:o,W:innerWidth,H:innerHeight,auto:!document.getElementById('bAuto').hidden,gear:!document.getElementById('bGear').hidden,brake:!document.getElementById('bBrake').hidden}}"""

async def layout(pg, label):
    L = await pg.evaluate(LAYOUT)
    r = {k: v for k, v in L['r'].items()}
    good, why = boxes_ok(r)
    inside = all(v['x'] >= 0 and v['y'] >= 0 and v['x'] + v['w'] <= L['W'] + 0.5 and v['y'] + v['h'] <= L['H'] + 0.5 for k, v in r.items() if k in ('fox', 'gun', 'flr'))
    ok(f'{label}: FOX 2, GUN and the FLARES slot 60 pt or larger, on screen, overlapping nothing (throttle, pause, stick, VIEW)',
       good and inside and r['fox']['vis'] and r['gun']['vis'], why or {k: (round(v['x']), round(v['y']), round(v['w']), round(v['h'])) for k, v in r.items()})
    ok(f'{label}: FOX 2 is the biggest (about 84), GUN about 72, 12 px apart', r['fox']['w'] >= 80 and 68 <= r['gun']['w'] < r['fox']['w'] and
       abs((r['fox']['x'] - (r['gun']['x'] + r['gun']['w'])) - 12) < 1.5, (r['fox']['w'], r['gun']['w'], r['fox']['x'] - r['gun']['x'] - r['gun']['w']))
    return L

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
        await pg.evaluate(f"()=>{K}.dfStart()"); await pg.wait_for_timeout(500); await step(pg, 0.3)
        L = await layout(pg, '844x390')
        ok('in the dogfight AUTO LAND, GEAR and BRAKE are hidden, VIEW stays', not L['auto'] and not L['gear'] and not L['brake'] and L['r']['view']['vis'], L)
        cfg = await pg.evaluate(f"()=>{K}.DF.cfg()")
        ok('DF.cfg(): Hard seeker 6 deg, lock 1.5 s, 6 missiles; the buttons say x6 and 510',
           cfg['seek'] == 6 and cfg['lock'] == 1.5 and cfg['fox'] == 6 and await pg.evaluate("()=>document.getElementById('bFoxN').textContent==='x6'&&document.getElementById('bGunN').textContent==='510'"), cfg)
        # the box on a bandit in view, an arrow for one behind and to the left
        await pg.evaluate(PLACE, [0, 1500, 0]); await step(pg, 0.2)
        h = await pg.evaluate("()=>({box:[...document.querySelectorAll('#dfHud .dfBox.on')].map(e=>e.innerText),arr:document.querySelectorAll('#dfHud .dfArr.on').length,seek:!!document.querySelector('#dfHud .dfSeek.on')})")
        ok('a green box on the bandit in view with its range in nm, no arrow, the seeker circle up', len(h['box']) == 1 and 'nm' in h['box'][0] and h['arr'] == 0 and h['seek'], h)
        await pg.evaluate(PLACE, [0, 1500, 2.4]); await step(pg, 0.6)
        h = await pg.evaluate("()=>{const a=document.querySelector('#dfHud .dfArr.on');if(!a)return null;const r=a.getBoundingClientRect();return {x:r.x,y:r.y,W:innerWidth,H:innerHeight,box:document.querySelectorAll('#dfHud .dfBox.on').length,t:a.innerText}}")
        ok('a bandit behind on the left: no box, an edge arrow on the left with its range', h and h['box'] == 0 and h['x'] < h['W'] / 2 and 'nm' in h['t'], h)
        # the seeker: search, then lock after 1.5 s
        await pg.evaluate(PLACE, [0, 1500, 0]); await step(pg, 0.5)
        s1 = await pg.evaluate(f"()=>({{st:{K}.DF.seek.state,t:{K}.DF.seek.t}})")
        await step(pg, 1.3)
        s2 = await pg.evaluate(f"()=>({{st:{K}.DF.seek.state,glow:document.getElementById('bFox').classList.contains('lock'),box:!!document.querySelector('#dfHud .dfBox.on.lk')}})")
        ok('a bandit 1.5 km dead ahead: the seeker searches (growl) first', s1['st'] == 'search' and s1['t'] < 1.5, s1)
        ok('after the lock time it locks (tone): the box red, FOX 2 glowing', s2['st'] == 'lock' and s2['glow'] and s2['box'], s2)
        # FOX 2: a missile with real flight time that kills
        await pg.evaluate(f"()=>{{{K}.DF.test.noDecoy=true;}}")
        await finger(pg, '#bFox')
        f = await pg.evaluate(f"()=>({{shots:{K}.DF.shots,fox:{K}.DF.fox,on:{K}.DF.msl.filter(m=>m.on).length,call:{K}.DF.lastCall,n:document.getElementById('bFoxN').textContent}})")
        ok('FOX 2 launches one missile, 5 left, the Fox two call', f['shots'] == 1 and f['fox'] == 5 and f['on'] == 1 and f['call'] == 'Fox two', f)
        t, alive = 0.0, True
        while t < 12 and alive:
            await step(pg, 0.1); t += 0.1
            alive = await pg.evaluate(f"()=>{K}.DF.bandits[0].alive")
        k = await pg.evaluate(f"()=>({{kills:{K}.DF.kills,call:{K}.DF.lastCall,atc:document.getElementById('atc').innerText,kc:{K}.DF.kc,t:{K}.DF.t,dim:document.body.classList.contains('dfKc')}})")
        ok('the missile takes more than 1 s of sim time and kills', not alive and t > 1.0, round(t, 1))
        ok('the kill counts and the call says Splash one', k['kills'] == 1 and k['call'] == 'Splash one' and 'Splash one' in k['atc'], k)
        ok('the last kill of the wave starts the kill cam (HUD dimmed)', k['kc'] > 0 and k['dim'], k)
        t0 = k['t']
        await step(pg, 1.0)
        mid = await pg.evaluate(f"()=>({{kc:{K}.DF.kc,t:{K}.DF.t,gap:{K}.DF.gap}})")
        ok('during the kill cam the wave clock holds', mid['kc'] > 0 and abs(mid['t'] - t0) < 1e-6 and mid['gap'] >= 3.99, mid)
        await step(pg, 2.0)
        mid = await pg.evaluate(f"()=>({{kc:{K}.DF.kc,dim:document.body.classList.contains('dfKc')}})")
        ok('stepFrame passes through the kill cam: it ends after 2.5 s, normal speed back', mid['kc'] == 0 and not mid['dim'], mid)
        await step(pg, 4.5)
        w = await pg.evaluate(f"()=>({{wave:{K}.DF.wave,n:{K}.DF.bandits.length}})")
        ok('the next wave follows', w['wave'] == 2 and w['n'] == 2, w)
        # a forced decoy misses
        await pg.evaluate(f"()=>{{const D={K}.DF;D.test.noDecoy=false;D.test.decoy=1;}}")
        await pg.evaluate(PLACE, [1, 7000, 1.4])
        await pg.evaluate(PLACE, [0, 1500, 0]); await step(pg, 1.9)
        lk = await pg.evaluate(f"()=>{K}.DF.seek.state")
        await finger(pg, '#bFox')
        shots = await pg.evaluate(f"()=>{K}.DF.shots")
        await step(pg, 6)
        d = await pg.evaluate(f"()=>({{alive:{K}.DF.bandits[0].alive,kills:{K}.DF.kills,on:{K}.DF.msl.filter(m=>m.on).length,fl:{K}.DF.flr.filter(f=>f.on).length,shots:{K}.DF.shots}})")
        ok('a forced flare decoy (DF.test.decoy=1): the missile misses and self destructs', lk == 'lock' and shots == 2 and d['alive'] and d['kills'] == 1 and d['on'] == 0, (lk, d))
        # FOX 2 without a lock: nothing fires, a click and No lock
        await pg.evaluate(f"()=>{{const D={K}.DF;D.test.decoy=0;}}")
        await pg.evaluate(PLACE, [0, 1500, 2.8]); await step(pg, 0.6)
        await finger(pg, '#bFox')
        n = await pg.evaluate(f"()=>({{shots:{K}.DF.shots,fox:{K}.DF.fox,noLock:{K}.DF.noLock,side:document.getElementById('sideToast').innerText,on:{K}.DF.msl.filter(m=>m.on).length}})")
        ok('FOX 2 without a lock fires nothing and says No lock', n['shots'] == 2 and n['fox'] == 4 and n['noLock'] == 1 and 'NO LOCK' in n['side'].upper() and n['on'] == 0, n)
        # the gun at 2 km: rounds go, the bandit is untouched
        await pg.evaluate(PLACE, [0, 2000, 0])
        await pg.evaluate(GUNHOLD, True); await step(pg, 1.0)
        g = await pg.evaluate(f"()=>({{r:{K}.DF.rounds,hp:{K}.DF.bandits[0].hp,firing:{K}.DF.firing,held:document.getElementById('bGun').classList.contains('held'),call:{K}.DF.lastCall,trc:{K}.DF.trc.filter(t=>t.on).length}})")
        await pg.evaluate(GUNHOLD, False); await step(pg, 0.1)
        ok('holding GUN fires: rounds go down, tracers fly, the Guns call', g['firing'] and g['held'] and 380 < g['r'] < 430 and g['trc'] > 5 and g['call'].startswith('Guns'), g)
        ok('at 2 km the gun does nothing', g['hp'] == 1, g)
        # the gun at 400 m: a gun kill
        await pg.evaluate(PLACE, [0, 400, 0]); await step(pg, 0.1)
        pip = await pg.evaluate("()=>!!document.querySelector('#dfHud .dfPip.on')")
        await pg.evaluate(GUNHOLD, True); await step(pg, 0.8)
        g = await pg.evaluate(f"()=>({{alive:{K}.DF.bandits[0].alive,gk:{K}.DF.gunKills,kills:{K}.DF.kills,r:{K}.DF.rounds,n:document.getElementById('bGunN').textContent}})")
        await pg.evaluate(GUNHOLD, False); await step(pg, 0.1)
        ok('the pipper shows on a bandit inside 1 nm', pip)
        ok('holding GUN on a bandit 400 m ahead kills it: a gun kill, rounds down', not g['alive'] and g['gk'] == 1 and g['kills'] == 2 and g['r'] < 400 and g['n'] == str(int(-(-g['r'] // 1))), g)
        ok('the gun stops with the finger', not await pg.evaluate(f"()=>{K}.DF.firing"))
        # real multi touch: the left thumb on the stick, a finger holding GUN, another tapping FOX 2
        await pg.evaluate(PLACE, [1, 1500, 2.8]); await pg.evaluate(f"()=>{{{K}.DF.rounds=200;}}"); await step(pg, 0.6)
        cdp = await pg.context.new_cdp_session(pg)
        async def touch(kind, pts):
            await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [{'x': x, 'y': y, 'id': i, 'radiusX': 4, 'radiusY': 4, 'force': 1} for i, (x, y) in pts]})
        C = "(s)=>{const r=document.querySelector(s).getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}"
        z, gc, fc = await pg.evaluate(C, '#stickZone'), await pg.evaluate(C, '#bGun'), await pg.evaluate(C, '#bFox')
        f1 = (z[0], z[1]); await touch('touchStart', [(1, f1)]); await pg.wait_for_timeout(60)
        f1 = (z[0] + 70, z[1]); await touch('touchMove', [(1, f1)]); await pg.wait_for_timeout(60)
        await touch('touchStart', [(1, f1), (2, tuple(gc))]); await pg.wait_for_timeout(60)
        nl0 = await pg.evaluate(f"()=>{K}.DF.noLock")
        await touch('touchStart', [(1, f1), (2, tuple(gc)), (3, tuple(fc))]); await pg.wait_for_timeout(60)
        await touch('touchEnd', [(3, tuple(fc))]); await pg.wait_for_timeout(60)
        await step(pg, 0.3)
        mt = await pg.evaluate(f"()=>({{ail:{K}.touchIn.ail,gun:{K}.DF.gunHeld,firing:{K}.DF.firing,noLock:{K}.DF.noLock,r:{K}.DF.rounds}})")
        await touch('touchEnd', [(2, tuple(gc))]); await pg.wait_for_timeout(60)
        mt2 = await pg.evaluate(f"()=>({{ail:{K}.touchIn.ail,gun:{K}.DF.gunHeld}})")
        await touch('touchEnd', [(1, f1)]); await pg.wait_for_timeout(60)
        ok('multi touch: stick held, GUN held and firing, FOX 2 tapped (No lock) all at once', mt['ail'] > 0.5 and mt['gun'] and mt['firing'] and mt['noLock'] == nl0 + 1 and mt['r'] < 200, mt)
        ok('multi touch: GUN lets go with its finger, the stick still held', not mt2['gun'] and mt2['ail'] > 0.5, mt2)
        # 568x320
        await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400); await step(pg, 0.2)
        await layout(pg, '568x320')
        await pg.set_viewport_size({'width': 932, 'height': 430}); await pg.wait_for_timeout(400); await step(pg, 0.2)
        await layout(pg, '932x430')
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        # free flight: the buttons come back, the weapons go
        await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('runway')}}"); await pg.wait_for_timeout(800); await step(pg, 0.3)
        ff = await pg.evaluate("()=>({auto:!document.getElementById('bAuto').hidden,gear:!document.getElementById('bGear').hidden,brake:!document.getElementById('bBrake').hidden,w:getComputedStyle(document.getElementById('dfW')).display,hud:getComputedStyle(document.getElementById('dfHud')).display,on:document.body.classList.contains('dfOn')})")
        ok('back in free flight AUTO LAND, GEAR and BRAKE return, the weapons and boxes are gone', ff['auto'] and ff['gear'] and ff['brake'] and ff['w'] == 'none' and ff['hud'] == 'none' and not ff['on'], ff)
        tk = await pg.evaluate(f"()=>{{const M={K}.MUSIC;M.titles=Object.create(null);return {K}.musicTitle('dogfight.m4a')}}")
        ok('the ticker title for dogfight.m4a survives a playlist load: Pocket Sim Original — Dogfight', tk == 'Pocket Sim Original — Dogfight', tk)
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('dogfight_weapons_check'))
asyncio.run(main())
