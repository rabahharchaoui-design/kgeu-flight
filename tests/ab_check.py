# F-16 afterburner (3.6): throttle above 0.82 lights the burner. Nozzle petals open with a
# 0.25 s lag, a layered flame (outer, core, shock diamonds) grows with ab, and at night it
# lights the ground behind on the runway. Power spools with a 2.2 s time constant (physics
# untouched), so full burner takes ~8 s from military power and the flame dies ~3 s after
# the throttle comes back.
# Also writes screenshots to overnight-screenshots/ab/.
# Run: .venv/bin/python tests/ab_check.py [--noshots]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'ab')
K = 'window.__kgeu'
SHOT = '--noshots' not in sys.argv
REAR = "{p:[3.2,1.4,13.5],t:[0,0.1,7.6],fov:40}"
SIDE = "{p:[8,0.9,10.5],t:[0,0.1,10.2],fov:55}"
TAKEOFF = "{p:[6,9,34],t:[0,0,8],fov:50}"

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        ev = lambda js: pg.evaluate("()=>{" + js + "}")
        async def hold(thr, sec, brake=True):
            for i in range(int(sec * 4)):
                # brake: the brakes do not hold an F-16 at full power, so pin it on the runway
                await pg.evaluate("""([t,b,n])=>{const K=window.__kgeu,s=K.state(),P=window.__abPin||(window.__abPin=s.pos.clone());
                  for(let i=0;i<n;i++){s.throttle=t;s.brake=b;if(b){s.pos.copy(P);s.vel.set(0,0,0);}K.stepFrame(1/60,false,true);}if(!b)window.__abPin=null;}""", [thr, brake, 15])
        async def ab(): return await pg.evaluate(f"()=>{K}.ab()")
        async def snap(name, cam):
            await ev(f"{K}.freeCam({cam})")
            await pg.evaluate("()=>window.__kgeu.stepFrame(1/60,false,false)")
            await pg.screenshot(path=f'{SHOTS}/{name}.png')
            await ev(f"{K}.freeCam(null)")
        await ev(f"{K}.setSkill('pilot')")
        await ev(f"{K}.setTOD('day')")
        await ev(f"{K}.pick('f16');{K}.start('runway')"); await pg.wait_for_timeout(1200)
        vis = "()=>{const a=window.__kgeu.plane().ab;return !!a&&a.visible&&a.userData.fx.outer.visible}"
        await hold(0.7, 6)
        a = await ab()
        ok('military: ab 0, no flame, nozzle closed', a['ab'] == 0 and a['flameLen'] == 0 and a['petalDeg'] < 1 and not await pg.evaluate(vis), a)
        if SHOT: await snap('f16_mil_rear', REAR)
        await hold(1.0, 3)
        a3 = await ab()
        ok('3 s after full throttle: burner lit and growing', a3['ab'] > 0.3 and a3['flameLen'] > 2.5 and a3['petalDeg'] > 3, a3)
        await hold(1.0, 6)
        a = await ab()
        ok('full burner: ab > 0.95, flame > 5 m, petals > 8 deg', a['ab'] > 0.95 and a['flameLen'] > 5 and a['petalDeg'] > 8, a)
        ok('day: no ground glow', a['glow'] == 0, a)
        if SHOT:
            await snap('f16_ab_rear', REAR)
            await snap('f16_ab_side', SIDE)
        await hold(0.7, 1)
        a1 = await ab()
        ok('throttle back 1 s: petals closing', a1['petalDeg'] < a['petalDeg'] - 1, (a['petalDeg'], a1['petalDeg']))
        await hold(0.7, 0.5)
        a2 = await ab()
        ok('petals still closing', a2['petalDeg'] < a1['petalDeg'], (a1['petalDeg'], a2['petalDeg']))
        await hold(0.7, 2)
        a = await ab()
        ok('throttle back 3.5 s: flame gone', a['ab'] == 0 and a['flameLen'] == 0 and not await pg.evaluate(vis), a)
        # night
        await ev(f"{K}.setTOD('night')")
        await hold(1.0, 9)
        a = await ab()
        ok('night full burner on the runway: ground glow', a['glow'] > 0 and a['flameLen'] > 5 * 1.3, a)
        if SHOT: await snap('f16_ab_night_rear', REAR)
        await hold(1.0, 3, brake=False)
        a = await ab()
        ok('night takeoff roll: glow still on', a['glow'] > 0, a)
        if SHOT: await snap('f16_ab_night_takeoff', TAKEOFF)
        await ev(f"{K}.setTOD('day')")
        await hold(1.0, 0.5, brake=False)
        a = await ab()
        ok('day again: glow gone', a['glow'] == 0, a)
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('ab_check')

sys.exit(asyncio.run(main()))
