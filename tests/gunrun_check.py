# Planes2 item 2: the A-10 on the strike range. The mission starts the A-10 in the orbit over the Gila range in the
# targeting pod view with four stores on the pylons and the GUN button up (body.hogOn); the pod locks a target and FIRE
# launches a Maverick through the range's missile pool; GUN held with the pod locked inside 1,500 m, nose on, takes the
# target after 0.8 s and counts a hit; the run ends on the gun run card and board (arc:gunrun), not the Reaper's.
# Run: .venv/bin/python tests/gunrun_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        async def step(n, dt=1/30):
            await pg.evaluate("([n,dt])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(dt,false,true);window.__kgeu.stepFrame(1/60);}", [n, dt])
        await pg.evaluate(f"()=>{K}.mission('gunrun')"); await pg.wait_for_timeout(1500)
        info = await pg.evaluate(f"""()=>{{const K={K},s=K.state();return {{active:K.STRIKE.active,type:s.type,ap:s.ap?s.ap.mode:null,cam:K.camMode(),
          pylons:K.pylonsVisible(),hog:document.body.classList.contains('hogOn'),gun:getComputedStyle(document.getElementById('bGun')).display,
          fox:getComputedStyle(document.getElementById('bFox')).display,rounds:K.HOG.rounds,kt:Math.round(s.ias*1.94384)}};}}""")
        print('  start:', info)
        ok('the gun run starts the A-10 on the range', info['active'] and info['type'] == 'a10', str(info))
        ok('in the orbit, in the pod view, at the loiter speed', info['ap'] == 'orbit' and info['cam'] == 2 and 190 <= info['kt'] <= 250, str(info))
        ok('four Mavericks on the pylons', info['pylons'] == [True] * 4, str(info['pylons']))
        ok('GUN up, FOX hidden, 1,150 rounds', info['hog'] and info['gun'] != 'none' and info['fox'] == 'none' and info['rounds'] == 1150, str(info))
        # the gun: put the jet 900 m from a second truck, nose on, pod locked on it, and hold GUN
        idx2 = await pg.evaluate(f"()=>{K}.STRIKE.targets.findIndex(t=>t.kind==='truck'&&!t.moving)")
        await pg.evaluate(f"""(i)=>{{const K={K},s=K.state(),t=K.STRIKE.targets[i];s.ap=null;s.apW=null;
          const h=Math.atan2(t.x-(t.x-900),-(t.z-(t.z+0)));s.pos.set(t.x,t.y+260,t.z+900);const d=new THREE.Vector3(t.x-s.pos.x,t.y-s.pos.y,t.z-s.pos.z).normalize();
          s.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);s.vel.copy(d).multiplyScalar(110);s.w.set(0,0,0);K.pointAt(i);K.stepFrame(1/60);K.trackHere();
          K.DF.gunHeld=true;}}""", idx2)
        h0 = await pg.evaluate(f"()=>{K}.STRIKE.hits")
        await step(40)
        g = await pg.evaluate(f"""()=>{{const K={K};return {{hits:K.STRIKE.hits,gun:K.STRIKE.gun||0,rounds:Math.round(K.HOG.rounds),firing:K.HOG.firing,
          tr:K.DF.trM&&K.DF.trM.visible,lbl:document.getElementById('bGunN').textContent}};}}""")
        print('  gun:', g)
        ok('the gun fires: rounds down, tracers drawn, the count on the button', g['firing'] and g['rounds'] < 1150 and g['tr'] and int(g['lbl']) >= g['rounds'], str(g))
        ok('the locked truck inside 1,500 m is taken by the gun', g['hits'] == h0 + 1 and g['gun'] == 1, str(g))
        await pg.evaluate(f"()=>{{{K}.DF.gunHeld=false;}}"); await step(10)
        ok('released: the gun stops', not await pg.evaluate(f"()=>{K}.HOG.firing"))
        # back up over the range, level, for the Maverick: the pod locks a truck, FIRE sends one
        await pg.evaluate(f"""()=>{{const K={K},s=K.state(),R=K.RANGE;s.pos.set(R.x,K.groundHeight(R.x,R.z)+1500,R.z+2000);
          s.quat.set(0,0,0,1);s.vel.set(0,0,-110);s.w.set(0,0,0);K.snapCam();K.stepFrame(1/60);}}""")
        await step(5)
        idx = await pg.evaluate(f"()=>{K}.STRIKE.targets.findIndex(t=>t.kind==='truck'&&!t.moving&&!t.dead)")
        await pg.evaluate(f"(i)=>{K}.pointAt(i)", idx); await step(8)
        await pg.evaluate(f"()=>{K}.trackHere()")
        lock = await pg.evaluate(f"()=>{{const S={K}.SENSOR;return {{tgt:S.tgt?S.tgt.kind:null,valid:S.valid}};}}")
        ok('the pod locks the truck', lock['tgt'] == 'truck', str(lock))
        await pg.evaluate(f"()=>{K}.fire()"); await step(20)
        fired = await pg.evaluate(f"()=>({{shots:{K}.STRIKE.shots,inflight:{K}.STRIKE.missiles.length,pylons:{K}.pylonsVisible()}})")
        ok('FIRE launches a Maverick off a pylon', fired['shots'] == 1 and fired['inflight'] == 1 and fired['pylons'].count(False) == 1, str(fired))
        # the run ends: the rest of the range dies, the score is the gun run's, on its own card and board
        await pg.evaluate(f"()=>{{const K={K};for(const t of K.STRIKE.targets)if(!t.dead)t.dead=true;K.STRIKE.missiles.length=0;K.strikeScore();}}")
        await step(200)
        card = await pg.evaluate("""()=>{const o=document.getElementById('arcOv');return {on:o.classList.contains('on'),t:o.textContent.replace(/\\s+/g,' ').slice(0,160)};}""")
        print('  card:', card)
        ok('the results card is the gun run card', card['on'] and 'Gun run' in card['t'], str(card))
        rec = await pg.evaluate("()=>{const B=window.__kgeu.SCORE.best;return {a10:!!B.a10,reaper:!!B.reaper};}")
        ok('the record is filed under the A-10, not the Reaper', rec['a10'] and not rec['reaper'], str(rec))
        ok('no page errors', not pg.errs, pg.errs[:2])
        await b.close()
    sys.exit(ok.done('gunrun_check'))
asyncio.run(main())
