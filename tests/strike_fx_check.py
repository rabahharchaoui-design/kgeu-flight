# Strike 3.4: easier targets (bigger, spread, markers, NEXT TARGET, hot in IR) and the FX
# explosion system (fireball, smoke column with a cap that lingers and drifts downwind).
# Usage: .venv/bin/python tests/strike_fx_check.py [--shots]
# --shots also writes overnight-screenshots/strike/*.png
import asyncio, os, sys, math, re
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

OUT = os.path.abspath('overnight-screenshots/strike')
SHOTS = '--shots' in sys.argv
K = 'window.__kgeu'
chk = Checks()

async def step(pg, secs, dt=1/30, render=False):
    await pg.evaluate("([n,dt,r])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);if(r)K.stepFrame(1/60);}",
                      [max(1, round(secs/dt)), dt, render])

async def shot(pg, name):
    if not SHOTS: return
    await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);document.getElementById('toast').classList.remove('on');document.getElementById('bigFlash').style.visibility='hidden';}}")
    p = os.path.join(OUT, name); await pg.screenshot(path=p, timeout=120000); print('  wrote', p)
    await pg.evaluate("()=>{document.getElementById('bigFlash').style.visibility='';}")

async def marks(pg):
    return await pg.evaluate("""()=>({mk:[...document.querySelectorAll('#sensorHud .tgtMark.on')].filter(e=>e.offsetParent!==null).map(e=>e.className+'|'+e.textContent),
      ar:[...document.querySelectorAll('#sensorHud .tgtArrow.on')].filter(e=>e.offsetParent!==null).map(e=>e.textContent)})""")

FIRE_AT = """(kind)=>{const K=window.__kgeu,i=K.STRIKE.targets.findIndex(t=>t.kind===kind&&!t.dead);
  K.pointAt(i);K.stepFrame(1/30,false,true);K.trackHere();K.fire();return i;}"""

async def fly_missile(pg):
    for _ in range(80):
        if await pg.evaluate(f"()=>{K}.STRIKE.missiles.length") == 0: return True
        await step(pg, 0.25)
    return False

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.mission('range');}}")
        await pg.wait_for_timeout(800)
        await step(pg, 1.0, render=True)

        # ---------- targets: bigger, spread out, hot ----------
        tg = await pg.evaluate(f"""()=>{K}.STRIKE.targets.map(t=>({{k:t.kind,r:t.r,x:t.x,z:t.z,h:t.mesh.userData.heat,s:t.mesh.scale.x}}))""")
        chk('seven targets', len(tg) == 7, len(tg))
        chk('every hit radius is 14 m or more', all(t['r'] >= 14 for t in tg), [t['r'] for t in tg])
        chk('radii 14 truck, 16 hull, 20 bunker', all(t['r'] == {'truck':14,'hull':16,'bunker':20}[t['k']] for t in tg))
        dmin = min(math.hypot(a['x']-c['x'], a['z']-c['z']) for i, a in enumerate(tg) for c in tg[i+1:])
        chk('no two targets within 80 m', dmin >= 80, f'{dmin:.0f} m')
        chk('targets scaled up 1.6x', all(abs(t['s']-1.6) < 1e-6 for t in tg))
        chk('live targets are hot in IR (>= 0.7)', all(t['h'] >= 0.7 for t in tg), [t['h'] for t in tg])

        # ---------- markers ----------
        await pg.evaluate(f"()=>{{const K={K},i=K.STRIKE.targets.findIndex(t=>t.kind==='bunker');K.pointAt(i);}}")
        await step(pg, 0.1, render=True)
        m = await marks(pg)
        print('  markers:', m['mk'][:4], 'arrows', len(m['ar']))
        dist = re.compile(r'\d+(\.\d)? (k)?m')
        chk('a diamond marker with a distance on a target in view', any(dist.search(x) for x in m['mk']), m['mk'][:2])
        ov = await pg.evaluate("""()=>{const m=document.getElementById('shMid').getBoundingClientRect();
          return [...document.querySelectorAll('#sensorHud .tgtMark.on span')].filter(e=>e.offsetParent!==null).some(e=>{const r=e.getBoundingClientRect();
            return r.right>m.left&&r.left<m.right&&r.bottom>m.top&&r.top<m.bottom;});}""")
        chk('no marker label overlaps the centre text', not ov)
        await shot(pg, 'markers_day.png')
        await pg.evaluate(f"()=>{K}.setSensorMode('irw')"); await step(pg, 0.3, render=True)
        heat = await pg.evaluate(f"()=>{K}.STRIKE.targets.map(t=>t.mesh.userData.heat)")
        chk('IR heat on live targets >= 0.7', all(h >= 0.7 for h in heat), heat)
        await shot(pg, 'markers_ir.png')
        await pg.evaluate(f"()=>{K}.setSensorMode('tv')")
        # swing the ball right round, away from the range
        await pg.evaluate(f"""()=>{{const K={K},S=K.SENSOR,i=K.STRIKE.targets.findIndex(t=>t.kind==='bunker');K.pointAt(i);
          S.az=S.az>0?S.az-Math.PI:S.az+Math.PI;S.el=-0.25;}}""")
        await step(pg, 0.05, render=True)
        m2 = await marks(pg)
        chk('with the ball turned away, edge arrows show', len(m2['ar']) >= 1, f"{len(m2['ar'])} arrows, {len(m2['mk'])} diamonds")
        chk('edge arrows carry a distance', all(dist.search(x) for x in m2['ar']), m2['ar'][:2])

        # ---------- NEXT TARGET ----------
        nb = await pg.evaluate("()=>{const b=document.getElementById('bNext');return !!b&&!b.hidden&&b.offsetParent!==null}")
        chk('NEXT TARGET button in the strike dock', nb)
        near = """()=>{const K=window.__kgeu,S=K.SENSOR;let d=1e9;for(const t of K.STRIKE.targets)if(!t.dead)d=Math.min(d,Math.hypot(t.x-S.spot.x,t.z-S.spot.z));return S.valid?d:1e9;}"""
        d0 = await pg.evaluate(near)
        await pg.evaluate("()=>document.getElementById('bNext').click()")
        await step(pg, 1.5, render=True)
        d1 = await pg.evaluate(near)
        chk('NEXT TARGET slews the ball onto a target (Pilot)', d1 < 25 and d1 < d0, f'{d0:.0f} m -> {d1:.0f} m')
        chk('Pilot: NEXT TARGET does not lock', await pg.evaluate(f"()=>!{K}.SENSOR.tgt"))
        k1 = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;const t=K.STRIKE.targets.find(t=>!t.dead&&Math.hypot(t.x-S.spot.x,t.z-S.spot.z)<25);return t?K.STRIKE.targets.indexOf(t):-1}}")
        await pg.keyboard.press('n'); await step(pg, 1.5, render=True)
        k2 = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;const t=K.STRIKE.targets.find(t=>!t.dead&&Math.hypot(t.x-S.spot.x,t.z-S.spot.z)<25);return t?K.STRIKE.targets.indexOf(t):-1}}")
        chk('key N cycles to another target', k2 >= 0 and k2 != k1, f'{k1} -> {k2}')
        await pg.evaluate(f"()=>{K}.setSkill('rookie')")
        await pg.evaluate("()=>document.getElementById('bNext').click()")
        await step(pg, 0.3, render=True)
        rk = await pg.evaluate(f"()=>{{const S={K}.SENSOR;return S.tgt?S.tgt.kind:null}}")
        chk('Rookie: NEXT TARGET locks it', rk is not None, rk)
        await pg.evaluate(f"()=>{K}.sensorLock()"); await step(pg, 0.1, render=True)   # lock off for the hint
        txt = await pg.inner_text('#shMid')
        chk('Rookie hint: Tap NEXT TARGET, then FIRE', 'Tap NEXT TARGET, then FIRE' in txt, repr(txt))
        await pg.evaluate("()=>document.getElementById('bNext').click()"); await step(pg, 0.3, render=True)
        rm = await marks(pg)
        chk('Rookie labels use plain names', any('LOCK Truck' in x or 'LOCK Armour' in x or 'LOCK Bunker' in x for x in rm['mk']), rm['mk'][:3])
        await shot(pg, 'next_target_rookie.png')
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")

        # ---------- explosion on the bunker ----------
        await pg.evaluate("()=>{const s=window.__kgeu.state();s.windBase=270;s.windKt=12;s.gustAmp=0;}")
        await step(pg, 0.1, render=True)
        pre = await pg.evaluate(f"()=>{K}.fx()")   # draw calls with nothing going off
        await pg.evaluate(FIRE_AT, 'bunker')
        chk('missile reaches the bunker', await fly_missile(pg))
        f0 = await pg.evaluate(f"()=>{K}.fx()")
        print('  fx at impact:', {k: f0[k] for k in ('active','sprites','t','scale')})
        chk('bunker destroyed', await pg.evaluate(f"()=>{K}.STRIKE.targets.find(t=>t.kind==='bunker').dead"))
        chk('an explosion is running', f0['active'] >= 1 and f0['scale'] == 2, f0)
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=1;}}")
        await step(pg, max(0.02, 0.5-f0['t']), render=True)
        await shot(pg, 'explosion_0_5s.png')
        f1 = await pg.evaluate(f"()=>{K}.fx()")
        cap = await pg.evaluate(f"()=>{K}.fxCaps.FXQ_N")
        # item 15: every fire, smoke, spark and flame quad is an instance of one layer (one draw
        # call), plus the debris mesh and the four ground decals
        chk(f'quad budget holds (<= {cap} in the pool)', f1['sprites'] <= cap and f1['quads'] <= cap, (f1['sprites'], f1['quads']))
        # (the count can fall: the missile and the bunker's live mesh are gone by now)
        chk('the explosion adds at most 8 draw calls', f1['drawCalls'] - pre['drawCalls'] <= 8, f"{pre['drawCalls']} -> {f1['drawCalls']}")
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=0;}}")
        await step(pg, 2.5, render=True)
        await shot(pg, 'explosion_3s.png')
        f3 = await pg.evaluate(f"()=>{K}.fx()")
        await step(pg, 2.5)
        f5 = await pg.evaluate(f"()=>{K}.fx()")
        chk('smoke column rises over 5 s', f5['smokeTop'] > f1['smokeTop'] + 40 and f5['smokeTop'] > 100,
            f"{f1['smokeTop']:.0f} -> {f3['smokeTop']:.0f} -> {f5['smokeTop']:.0f} m")
        chk('column capped at 250 m * sqrt(scale)', f5['smokeTop'] <= 250*math.sqrt(2)+5, f"{f5['smokeTop']:.0f} m")
        # IR bloom and the IR column
        await pg.evaluate(f"()=>{{{K}.setSensorMode('irw');{K}.explode({K}.RANGE.x+200,{K}.groundHeight({K}.RANGE.x+200,{K}.RANGE.z+150),{K}.RANGE.z+150,{{scale:2,secondary:2,debris:12}});}}")
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,R=K.RANGE;S.tgt=null;S.track=new (S.spot.constructor)(R.x+200,K.groundHeight(R.x+200,R.z+150)+30,R.z+150);}}")
        await step(pg, 0.7, render=True)
        await shot(pg, 'explosion_ir.png')
        await pg.evaluate(f"()=>{K}.setSensorMode('tv')")
        # 40 s on: still smoke, and it has gone downwind
        await pg.evaluate(f"()=>{{{K}.SENSOR.track=null;}}")
        await step(pg, 35, dt=0.1)
        fl = await pg.evaluate("""()=>{const K=window.__kgeu,f=K.fx();return f;}""")
        # the newest slot is the IR one; check the bunker column by looking at all slots
        lg = await pg.evaluate("""()=>{const K=window.__kgeu;return K.fxSlots();}""")
        print('  slots at 40 s:', lg)
        bk = max(lg, key=lambda o: o['t'])
        w = bk['wind']; wl = math.hypot(w[0], w[2]) or 1
        along = (bk['mean'][0]*w[0] + bk['mean'][1]*w[2]) / wl
        chk('after 40 s the column still has smoke', bk['smokeN'] >= 3, bk['smokeN'])
        chk('the smoke has drifted downwind', along > 30, f'{along:.0f} m along the wind')
        chk('quad budget holds later on', fl['sprites'] <= cap, fl['sprites'])

        # ---------- night, and the chase view ----------
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await pg.evaluate(f"()=>{{const K={K},R=K.RANGE;K.explode(R.x-150,K.groundHeight(R.x-150,R.z-40),R.z-40,{{scale:2,secondary:2,debris:14,fireSec:120}});}}")
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,R=K.RANGE;S.tgt=null;S.track=new (S.spot.constructor)(R.x-150,K.groundHeight(R.x-150,R.z-40),R.z-40);}}")
        await step(pg, 0.6, render=True)
        await shot(pg, 'explosion_night.png')
        await pg.evaluate(f"()=>{K}.setTOD('day')")
        await pg.evaluate(f"()=>{{const K={K},R=K.RANGE;K.fxClear();K.explode(R.x+60,K.groundHeight(R.x+60,R.z+250),R.z+250,{{scale:2,secondary:1,debris:12}});}}")
        await step(pg, 6)
        cam = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),R=K.RANGE;while(K.camMode()!==0)K.cycleCam();
          const v=new THREE.Vector3(R.x+60,K.groundHeight(R.x+60,R.z+250)+110,R.z+250).sub(s.pos).applyQuaternion(s.quat.clone().invert());
          window.__fxT=v.toArray();K.freeCam({p:[0,5,24],t:v.toArray(),fov:45});return Math.round(Math.hypot(R.x+60-s.pos.x,R.z+250-s.pos.z));}""")
        print(f'  chase camera {cam} m from the column')
        await step(pg, 0.05, render=True)
        await shot(pg, 'chase_explosion.png')
        await step(pg, 6)
        await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),R=K.RANGE;
          const v=new THREE.Vector3(R.x+60,K.groundHeight(R.x+60,R.z+250)+150,R.z+250).sub(s.pos).applyQuaternion(s.quat.clone().invert());
          K.freeCam({p:[0,5,24],t:v.toArray(),fov:45});}""")
        await step(pg, 0.05, render=True)
        await shot(pg, 'chase_explosion_12s.png')
        await pg.evaluate(f"()=>{{{K}.freeCam(null);{K}.SENSOR.zoom=0;}}")
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        chk('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(chk.done('strike_fx_check'))

asyncio.run(main())
