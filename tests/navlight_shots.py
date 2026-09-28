# Item 3.11 screenshots: aircraft nav (position) lights at night.
# For each of the 6 types on the 3 mile final at Glendale at night (gear as the
# final start sets it), three shots:
#   <type>_chase.png  the real chase camera, exactly as played (no freeCam)
#   <type>_side.png   free camera 25 m off the left wingtip, a little ahead so the
#                     red light is inside its cone
#   <type>_front.png  free camera 35 m ahead of the aircraft, slightly below
# plus a sunset chase shot for the cessna and the f16 (<type>_sunset_chase.png).
# __kgeu.freeCam takes offsets in the aircraft frame (nose -Z, right +X, up +Y) and
# applies the aircraft's world position and quaternion (plane().g) itself, so the
# same offsets frame every type; the wingtip distance comes from that type's own
# light layer (plane().lights), so the side camera clears every span.
# Usage: .venv/bin/python tests/navlight_shots.py [before|after]
# writes overnight-screenshots/navlights/<label>/
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

LABEL = sys.argv[1] if len(sys.argv) > 1 else 'after'
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'navlights', LABEL))
TYPES6 = ['cessna', 'alpha', 'f16', 'reaper', 'mq9b', 'c130']
# the outermost light's |x| in the aircraft frame (the wingtip nav lights)
TIP = """()=>{const L=window.__kgeu.plane().lights;if(!L)return 5;const a=L.pts.geometry.attributes.position;
  let m=0;for(let i=0;i<a.count;i++)m=Math.max(m,Math.abs(a.getX(i)));return m;}"""


async def advance(pg, secs):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", round(secs * 60))


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def setup(pg, t, tod):
    await pg.evaluate("([t,d])=>{const K=window.__kgeu;K.freeCam(null);K.setTOD(d);K.pick(t);K.pickBase('kgeu');K.start('final');}", [t, tod])
    await pg.wait_for_timeout(200)
    await pg.evaluate("()=>{const K=window.__kgeu;while(K.camMode()!==0)K.cycleCam();K.snapCam();K.stepFrame(1/60);}")
    await advance(pg, 1.5)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        for t in TYPES6:
            await setup(pg, t, 'night')
            await shot(pg, f'{t}_chase.png')
            tip = await pg.evaluate(TIP)
            # 25 m off the left tip, ~30 deg ahead of abeam: inside the red light's cone
            await pg.evaluate("(c)=>window.__kgeu.freeCam(c)",
                              {'p': [-tip - 21.7, 1.5, -12.5], 't': [0, 0, 0], 'fov': 50 if tip < 12 else 65})
            await advance(pg, 0.1)
            await shot(pg, f'{t}_side.png')
            await pg.evaluate("(c)=>window.__kgeu.freeCam(c)",
                              {'p': [0, -4, -35], 't': [0, 0, 0], 'fov': 45 if tip < 12 else 70})
            await advance(pg, 0.1)
            await shot(pg, f'{t}_front.png')
            await pg.evaluate("()=>window.__kgeu.freeCam(null)")
        for t in ['cessna', 'f16']:
            await setup(pg, t, 'sunset')
            await shot(pg, f'{t}_sunset_chase.png')
        if pg.errs: print('console errors:', pg.errs[:5])
        await pg.evaluate("()=>{window.__kgeu.setTOD('day');window.__kgeu.stepFrame(0,true);}")
        await pg.context.close()
        await b.close()
    srv.shutdown()


asyncio.run(main())
