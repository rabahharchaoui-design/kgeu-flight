# Item 3.2 screenshots: night lighting. Chase-camera views of the C-130 on final
# to Luke, the Cessna on final to Glendale (both at a normal 3 mile final and
# repositioned to short final), the F-16 on the Luke ramp, and side/rear model
# shots of every aircraft airborne at night, all at iPhone landscape (844x390).
#
# Reuses tests/harness.py (iPhone 15 viewport, device scale 2, software GL) and
# the same test hooks as tests/roll_shots.py / tests/model_shots.py:
#   __kgeu.pick / pickBase / start   to set up a flight
#   __kgeu.state()                   to hand-place the aircraft
#   __kgeu.snapCam() + stepFrame(1/60)  to hold the render loop and advance it
#     deterministically (every step renders here, since these are screenshots,
#     not a fast check -- see roll_shots.py's note on the same pattern)
#   __kgeu.freeCam                   for the fixed side/rear viewpoints, camera
#     offsets given in the aircraft body frame (see model_shots.py)
#   __kgeu.approachEnd()             the runway end the aircraft is lined up
#     with, used to place "short final" without reaching into the private
#     per-base fin() geometry
#
# Usage: .venv/bin/python tests/night_shots.py [label]
# label defaults to 'after'; writes overnight-screenshots/night/<label>_<name>.png
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

LABEL = sys.argv[1] if len(sys.argv) > 1 else 'after'
OUT = os.path.abspath('overnight-screenshots/night')

# Cruise speeds (kt) used to place each type in stable level flight for the
# airborne model shots -- not exact vcruise, just fast enough not to stall.
CRUISE_KT = {'f16': 420, 'c130': 250, 'cessna': 110, 'alpha': 90, 'reaper': 120, 'mq9b': 120}
# span, length (m), from TYPES in index.html -- used only to size camera offsets.
DIMS = {
    'cessna': (11, 8.3), 'alpha': (10.5, 6.5), 'f16': (9.96, 15),
    'reaper': (20.1, 13), 'mq9b': (24, 11.7), 'c130': (40.4, 29.8),
}
TYPES6 = ['cessna', 'alpha', 'f16', 'reaper', 'mq9b', 'c130']

# Place the aircraft `alt` metres over its current (x,z) position, level, at
# cruise speed for its type, full throttle, gear up. Mirrors roll_shots.py's SETUP.
SETUP_ALT = """([kt,alt])=>{const K=window.__kgeu,s=K.state();
  const V=kt/1.94384/Math.sqrt(1.097*Math.exp(-alt/9200)/1.225);
  s.pos.y=alt+K.groundHeight(s.pos.x,s.pos.z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=1;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60);return true;}"""

# Reposition onto short final: D metres from the runway threshold, `agl` metres
# up, nose on the extended centreline. Uses __kgeu.approachEnd() rather than the
# base's private fin() geometry so it works the same at both fields.
SHORT_FINAL = """([D,agl])=>{const K=window.__kgeu,s=K.state(),e=K.approachEnd();
  if(!e)return false;
  const dx=Math.sin(e.h),dz=-Math.cos(e.h),x=e.x-dx*D,z=e.z-dz*D,gh=K.groundHeight(x,z);
  s.pos.set(x,gh+1.5+agl,z);K.snapCam();K.stepFrame(1/60);return true;}"""


async def to_chase(pg):
    if await pg.evaluate("()=>window.__kgeu.camMode()") != 0:
        await pg.evaluate("()=>{while(window.__kgeu.camMode()!==0)window.__kgeu.cycleCam();}")


async def advance(pg, secs=2.0):
    n = round(secs * 60)
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)


async def shot(pg, name):
    # Software rendering under headless Chromium can be slow enough after a batch
    # of stepFrame calls that the default 30s screenshot timeout trips; give it room.
    path = os.path.join(OUT, f'{LABEL}_{name}')
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)
    return path


async def setup(pg, t, base, mode):
    await pg.evaluate("([t,b,m])=>{const K=window.__kgeu;K.pick(t);K.pickBase(b);K.start(m);}", [t, base, mode])
    await pg.wait_for_timeout(200)
    await to_chase(pg)
    await pg.evaluate("()=>window.__kgeu.stepFrame(1/60)")


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    written = []
    missing = []
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15,
                         storage={'kgeuOnboard': 'pilot', 'kgeuType': 'c130', 'kgeuTut': '1', 'kgeuCoach': '3'})

        for hook in ['setTOD', 'pickBase', 'pick', 'start', 'state', 'snapCam', 'stepFrame', 'freeCam', 'approachEnd', 'groundHeight', 'camMode', 'cycleCam']:
            ok = await pg.evaluate("(h)=>typeof window.__kgeu[h]==='function'", hook)
            if not ok: missing.append(hook + ' (missing)')
        has_ramp = await pg.evaluate("()=>!!document.querySelector('.pick[data-pos=\"ramp\"]')")
        if not has_ramp: missing.append('ramp start chip (missing)')

        await pg.evaluate("()=>window.__kgeu.setTOD('night')")

        # --- Luke: C-130 on 3 mile final, chase view ---
        await setup(pg, 'c130', 'luke', 'final')
        await advance(pg, 2.0)
        written.append(await shot(pg, 'luke_final.png'))

        okp = await pg.evaluate(SHORT_FINAL, [1000, 60])
        if not okp: missing.append('approachEnd returned null (luke c130 final)')
        await advance(pg, 1.0)
        written.append(await shot(pg, 'luke_short_final.png'))

        # --- Glendale: Cessna into Glendale, chase view ---
        await setup(pg, 'cessna', 'kgeu', 'final')
        await advance(pg, 2.0)
        written.append(await shot(pg, 'kgeu_final.png'))

        okp = await pg.evaluate(SHORT_FINAL, [1000, 60])
        if not okp: missing.append('approachEnd returned null (kgeu cessna final)')
        await advance(pg, 1.0)
        written.append(await shot(pg, 'kgeu_short_final.png'))

        # --- Luke ramp: F-16, looking at the field ---
        await setup(pg, 'f16', 'luke', 'ramp')
        await advance(pg, 1.0)
        written.append(await shot(pg, 'luke_ramp.png'))

        # --- Side/rear model shots, airborne at night, 500 m ---
        for t in TYPES6:
            span, length = DIMS[t]
            await setup(pg, t, 'kgeu', 'runway')
            await pg.evaluate(SETUP_ALT, [CRUISE_KT[t], 500])
            await advance(pg, 0.5)
            await pg.evaluate("(c)=>window.__kgeu.freeCam(c)",
                               {'p': [-span * 1.5, 0, 0], 't': [0, 0, 0], 'fov': 34})
            await advance(pg, 0.3)
            written.append(await shot(pg, f'{t}_side.png'))
            await pg.evaluate("(c)=>window.__kgeu.freeCam(c)",
                               {'p': [0, length * 0.30, length * 1.5], 't': [0, 0, 0], 'fov': 34})
            await advance(pg, 0.3)
            written.append(await shot(pg, f'{t}_rear.png'))
            await pg.evaluate("()=>window.__kgeu.freeCam(null)")

        if pg.errs:
            print('console errors:', pg.errs[:5])
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        await pg.context.close()
        await b.close()
    srv.shutdown()

    print(f'\n{len(written)} screenshots written to {OUT}')
    if missing:
        print('missing/unexpected hooks:', '; '.join(sorted(set(missing))))
    else:
        print('all hooks present')


asyncio.run(main())
