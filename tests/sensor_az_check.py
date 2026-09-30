# Sensor ball azimuth (Phone2 5): in the MQ-9 ball view the mini map shows a cone from the
# aircraft in the camera's look direction, and #shTR reads the true bearing plus left/right
# of the nose (Hard: CAM 237°T  R045  EL -30, Easy: plain words over three lines). Both
# follow a slew, a zoom and a lock; the cone goes away with the ball view. The readout must
# not sit on the map, shTL, the pause button or any button at 568x320, 667x375, 844x390
# and portrait 390x844. Screenshots (day, night, haboob at 844x390, day at 568x320) go to
# overnight-screenshots/phone2/item5/.
# Run: .venv/bin/python tests/sensor_az_check.py [--noshots]
import asyncio, sys, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone2', 'item5')
SHOTS = '--noshots' not in sys.argv
STORE = {'kgeuTut': '1', 'kgeuCoach': '3'}

HDG = "()=>{const e=new THREE.Euler().setFromQuaternion(window.__kgeu.state().quat,'YXZ');return ((-e.y*180/Math.PI)%360+360)%360;}"
LAYOUT = """()=>{const R=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
  const tr=R(document.getElementById('shTR')),bad=[];
  const hit=(a,b)=>a.x<b.x+b.w-0.5&&b.x<a.x+a.w-0.5&&a.y<b.y+b.h-0.5&&b.y<a.y+a.h-0.5;
  const els=[document.getElementById('map'),document.getElementById('shTL'),document.getElementById('shBL'),...document.querySelectorAll('#uiroot button')];
  for(const e of els){if(!e||e.closest('.overlay'))continue;const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden'||e.offsetParent===null)continue;
    const r=R(e);if(r.w<1||r.h<1)continue;if(hit(tr,r))bad.push(e.id||e.textContent.trim().slice(0,12));}
  const inside=tr.x>=0&&tr.y>=0&&tr.x+tr.w<=innerWidth&&tr.y+tr.h<=innerHeight;
  return {tr:[tr.x,tr.y,tr.w,tr.h].map(Math.round),bad:bad,inside:inside,text:document.getElementById('shTR').textContent};}"""


async def enter(pg, skill, tod='day'):
    await pg.evaluate(f"()=>{{{K}.setTOD('{tod}');{K}.setSkill('{skill}');{K}.pick('reaper');{K}.pickBase('luke');{K}.start('final');}}")
    await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('#bSensor').click()")
    await pg.wait_for_timeout(300)


async def step(pg, n=1):
    await pg.evaluate(f"()=>{{const k={K};for(let i=1;i<{n};i++)k.stepFrame(1/60,false,true);k.stepFrame(1/60);}}")


async def set_az(pg, deg):
    await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.track=null;S.tgt=null;S.slewTo=null;S.az={deg}*Math.PI/180;}}")
    await step(pg)


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(STORE, kgeuOnboard='pilot'))
        await enter(pg, 'pilot')
        ok('Hard: in the ball view', await pg.evaluate(f"()=>{K}.camMode()===2&&{K}.sensorMode()"))

        await set_az(pg, 45)
        h = await pg.evaluate(HDG)
        tr = await pg.inner_text('#shTR'); c = await pg.evaluate(f"()=>{K}.sensorCone()")
        fov = (await pg.evaluate(f"()=>{K}.sensor()"))['fov']
        brg = f"{round(h+45) % 360:03d}"
        ok('az +45: readout shows the true bearing', tr.startswith(f'CAM {brg}°T'), f'{tr!r} hdg {h:.1f}')
        ok('az +45: readout shows R045 and EL', '  R045  EL -' in tr, repr(tr))
        ok('az +45: cone on, rel 45', c['on'] and abs(c['rel']-45) < 0.1, c)
        ok('az +45: cone bearing is heading + 45', abs(((c['brgT']-(h+45)) + 180) % 360 - 180) < 0.2, c)
        ok('cone half angle is FOV/2 (at least 4)', c['half'] == max(4, fov/2), f"{c['half']} fov {fov}")
        sens = await pg.evaluate(f"()=>{{const S={K}.SENSOR,s={K}.state();return S.valid?Math.hypot(S.spot.x-s.pos.x,S.spot.z-s.pos.z):-1;}}")
        exp = min(5500, max(2000, sens)) if sens >= 0 else 3000
        ok('cone length is the ground distance to the spot (clamped), else 3 km', abs(c['len']-exp) < 2, f"{c['len']} vs {exp:.0f}")

        await pg.evaluate(f"()=>{{{K}.SENSOR.el=-0.08;}}"); await step(pg)
        c = await pg.evaluate(f"()=>{K}.sensorCone()")
        sens = await pg.evaluate(f"()=>{{const S={K}.SENSOR,s={K}.state();return S.valid?Math.hypot(S.spot.x-s.pos.x,S.spot.z-s.pos.z):-1;}}")
        exp = min(5500, max(2000, sens)) if sens >= 0 else 3000
        ok('shallow look: the cone reaches out to the spot', c["len"] > 2000 and abs(c['len']-exp) < 2, f"{c['len']} vs {exp:.0f}")
        await pg.evaluate(f"()=>{{{K}.SENSOR.el=-0.6;}}")
        await set_az(pg, -90)
        tr = await pg.inner_text('#shTR'); c = await pg.evaluate(f"()=>{K}.sensorCone()")
        ok('az -90: readout shows L090', ' L090 ' in tr, repr(tr))
        ok('az -90: cone rel -90', abs(c['rel']+90) < 0.1, c)

        await set_az(pg, 0)
        ok('az 0: readout shows R000', ' R000 ' in await pg.inner_text('#shTR'))

        h0 = (await pg.evaluate(f"()=>{K}.sensorCone()"))['half']
        await pg.evaluate("()=>document.querySelector('#bZoom').click()"); await step(pg)
        h1 = (await pg.evaluate(f"()=>{K}.sensorCone()"))['half']
        ok('zoom in: the cone narrows', h1 < h0, f'{h0} -> {h1}')
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=0;}}")

        # lock a point, fly on: the readout follows the tracked azimuth
        await set_az(pg, 30)
        await pg.evaluate(f"()=>{{{K}.SENSOR.el=-0.7;}}"); await step(pg)
        await pg.evaluate(f"()=>{K}.trackHere()")
        a0 = (await pg.evaluate(f"()=>{K}.sensor()"))['az']
        await step(pg, 240)
        s1 = await pg.evaluate(f"()=>{K}.sensor()"); tr = await pg.inner_text('#shTR'); c = await pg.evaluate(f"()=>{K}.sensorCone()")
        rel = round(s1['az'])
        want = ('L' if rel < 0 else 'R') + f'{abs(rel):03d}'
        ok('locked: the track holds', s1['lock'], s1)
        ok('locked: the azimuth moves as the aircraft flies', abs(s1['az']-a0) > 2, f"{a0} -> {s1['az']}")
        ok('locked: readout follows the tracked azimuth', f' {want} ' in tr, f'{tr!r} want {want}')
        ok('locked: cone follows too', abs(c['rel']-s1['az']) < 0.1, c)

        if SHOTS:
            os.makedirs(OUT, exist_ok=True)
            await set_az(pg, 60); await pg.evaluate(f"()=>{{{K}.SENSOR.el=-0.2;}}"); await step(pg, 10)
            await pg.screenshot(path=os.path.join(OUT, 'day_minimap.png'), clip={'x': 0, 'y': 0, 'width': 120, 'height': 120}, timeout=120000)
            await pg.screenshot(path=os.path.join(OUT, 'day_844x390_hard.png'), timeout=120000)

        # Easy words
        await enter(pg, 'rookie')
        await set_az(pg, 45)
        h = await pg.evaluate(HDG); tr = await pg.inner_text('#shTR')
        lines = tr.split('\n')
        ok('Easy: plain words over three lines', len(lines) == 3 and lines[0] == f'Camera {round(h+45) % 360}°'
           and lines[1] == '45° right of the nose' and lines[2].endswith('° down'), repr(tr))
        await set_az(pg, -20)
        ok('Easy: left of the nose', '20° left of the nose' in await pg.inner_text('#shTR'))
        await set_az(pg, 0)
        ok('Easy: straight ahead', 'straight ahead' in await pg.inner_text('#shTR'))

        # leave the ball view: the cone goes
        await pg.evaluate("()=>document.querySelector('#bCam').click()"); await step(pg)
        c = await pg.evaluate(f"()=>{K}.sensorCone()")
        ok('VIEW leaves the ball view, the cone is off', await pg.evaluate(f"()=>{K}.camMode()") != 2 and not c['on'], c)

        if SHOTS:
            for tod in ('night', 'haboob'):
                await enter(pg, 'pilot', tod)
                if tod == 'haboob': await pg.evaluate(f"()=>{K}.haboobJump(1500)")
                await set_az(pg, -60); await pg.evaluate(f"()=>{{{K}.SENSOR.el=-0.2;}}"); await step(pg, 30)
                await pg.screenshot(path=os.path.join(OUT, f'{tod}_844x390_hard.png'), timeout=120000)
                await pg.screenshot(path=os.path.join(OUT, f'{tod}_minimap.png'), clip={'x': 0, 'y': 0, 'width': 120, 'height': 120}, timeout=120000)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # layout at the small, middle and large phones, and portrait, Easy and Hard
        for (w, hh) in ((568, 320), (667, 375), (844, 390), (390, 844)):
            for skill in ('pilot', 'rookie'):
                q = await page(b, url, vp={'width': w, 'height': hh}, storage=dict(STORE, kgeuOnboard=skill))
                if hh > w: await q.evaluate("()=>document.body.classList.add('portraitok')")
                await enter(q, skill)
                await set_az(q, -137); await q.evaluate(f"()=>{{{K}.SENSOR.el=-1.2;}}"); await step(q)
                L = await q.evaluate(LAYOUT)
                ok(f'{w}x{hh} {"Hard" if skill == "pilot" else "Easy"}: readout clear of the map, shTL, pause and buttons, on screen',
                   not L['bad'] and L['inside'], L)
                if SHOTS and (w, hh) in ((568, 320), (390, 844)):
                    await q.screenshot(path=os.path.join(OUT, f'day_{w}x{hh}_{skill}.png'), timeout=120000)
                ok(f'{w}x{hh} {skill}: no page errors', not q.errs, q.errs[:3])
                await q.context.close()
        await b.close()
    sys.exit(ok.done('sensor_az_check'))

asyncio.run(main())
