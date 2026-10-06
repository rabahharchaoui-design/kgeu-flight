# Propellers (3.5): blades at idle, blurred disc at full power, rate follows power.
# Also writes close-ups to overnight-screenshots/props/.
# Run: .venv/bin/python tests/prop_check.py [--noshots]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'props')
K = 'window.__kgeu'
BLADES = {'cessna': 2, 'archer': 2, 'alpha': 2, 'reaper': 3, 'mq9b': 3, 'c130': 4}
# prop hub in the aircraft frame (x, y, z; nose is -z) and a camera offset from it
HUB = {'cessna': ([0, -0.13, -3.2], 3.2), 'archer': ([0, 0.0, -2.42], 3.0), 'alpha': ([0, -0.52, -2.82], 2.8), 'reaper': ([0, 0.13, 5.9], 3.8),
       'mq9b': ([0, 0.14, 6.2], 3.8), 'c130': ([-4.85, 1.6, -11.2], 7.5)}
SHOT = '--noshots' not in sys.argv

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        ev = lambda js: pg.evaluate("()=>{" + js + "}")
        async def step(n, dt=1/60):
            await pg.evaluate("([n,dt])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(dt,false,true);}", [n, dt])
        async def snap(name, cam):
            await ev(f"{K}.freeCam({cam})")
            await pg.evaluate("()=>window.__kgeu.stepFrame(1/60,false,false)")
            await pg.screenshot(path=f'{SHOTS}/{name}.png')
            await ev(f"{K}.freeCam(null)")
        await ev(f"{K}.setSkill('pilot')")
        for t, n in BLADES.items():
            print('--', t)
            await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
            await ev(f"{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('runway')"); await pg.wait_for_timeout(1200)
            await ev(f"const s={K}.state();s.throttle=0;s.brake=true;")
            await step(180)
            await ev(f"{K}.state().throttle=0")
            await step(1)
            a = await pg.evaluate(f"()=>{K}.prop()")
            ok(f'{t} idle: blades showing, no disc, turning', a['bladeOpacity'] >= 0.9 and a['discOpacity'] <= 0.1 and a['rate'] > 0, a)
            ok(f'{t} blade count {n}', a['blades'] == n, a['blades'])
            h, d = HUB[t]; x, y, z = h
            front = 1 if t in ('reaper', 'mq9b') else -1       # pushers: look from behind
            q = f"{{p:[{x + d * 0.55},{y + d * 0.25},{z + front * d}],t:[{x},{y},{z}],fov:40}}"
            if t == 'c130': q = "{p:[-15,3.5,-26],t:[-7,1.8,-11],fov:40}"
            if SHOT: await snap(f'{t}_idle', q)
            await ev(f"const s={K}.state();s.throttle=1;s.brake=true;")
            for i in range(6):
                await ev(f"{K}.state().throttle=1;{K}.state().brake=true"); await step(60)
            f = await pg.evaluate(f"()=>{K}.prop()")
            ok(f'{t} full: disc up, blades gone, faster', f['discOpacity'] >= 0.5 and f['bladeOpacity'] <= 0.1 and f['rate'] >= a['rate'], (f, a['rate']))
            if SHOT:
                await snap(f'{t}_full', q)
                if t == 'reaper':
                    await snap('reaper_ring_rear', f"{{p:[{x},{y + 0.3},{z + 4.2}],t:[{x},{y},{z}],fov:40}}")
                if t == 'c130':
                    await snap('c130_full_side', "{p:[-30,3,-22],t:[-6,2,-8],fov:40}")
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('prop_check')

sys.exit(asyncio.run(main()))
