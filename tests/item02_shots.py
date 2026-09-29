# One-off screenshot script for phone notes 0929, item 2 (general lag: far cull of
# parked planes/traffic under 1.5 px, HUD-on-change, cached PAPI canvas height, smoke
# trail skip, people pose skip, fewer per-frame allocations). Confirms the far-cull
# change (farAdd/farUpdate/farWarm, FAR_PX=1.5 in index.html) does not hide parked
# aircraft or traffic that should still be visible at normal viewing distances.
# iPhone landscape 844x390, dsf 2, mobile, touch. Test/screenshot infra only; does
# not touch game code.
# Run: .venv/bin/python tests/item02_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item02')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'

# Same "short final" placement convention as tests/night_shots.py: 1000 m from the
# runway threshold, 60 m AGL, nose on the extended centreline.
SHORT_FINAL = """([D,agl])=>{const K=window.__kgeu,s=K.state(),e=K.approachEnd();
  if(!e)return false;
  const dx=Math.sin(e.h),dz=-Math.cos(e.h),x=e.x-dx*D,z=e.z-dz*D,gh=K.groundHeight(x,z);
  s.pos.set(x,gh+1.5+agl,z);K.snapCam();K.stepFrame(1/60);return true;}"""

async def to_chase(pg):
    if await pg.evaluate(f"()=>{K}.camMode()") != 0:
        await pg.evaluate(f"()=>{{while({K}.camMode()!==0){K}.cycleCam();}}")

async def advance(pg, secs=1.5):
    n = round(secs * 60)
    await pg.evaluate(f"(n)=>{{for(let i=0;i<n;i++){K}.stepFrame(1/60);}}", n)

async def shot(pg, name):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print('wrote', path)
    return path

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.wait_for_function(f"()=>{K}.warm()", timeout=30000)

        # 1. short final to Glendale -- parked Cessnas must be visible on the ramp
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final');}}")
        await pg.wait_for_timeout(300)
        await to_chase(pg)
        okp = await pg.evaluate(SHORT_FINAL, [1000, 60])
        await advance(pg, 1.0)
        print('  short final placed:', okp)
        await shot(pg, '01_glendale_short_final.png')

        # 2. at Luke, on the runway
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.pick('f16');{K}.pickBase('luke');{K}.start('runway');}}")
        await pg.wait_for_timeout(300)
        await to_chase(pg)
        await advance(pg, 1.0)
        await shot(pg, '02_luke_runway.png')

        # 3. at night, in flight
        await pg.evaluate(f"()=>{{{K}.setTOD('night');{K}.pick('reaper');{K}.pickBase('kgeu');{K}.start('final');}}")
        await pg.wait_for_timeout(300)
        await to_chase(pg)
        await advance(pg, 1.5)
        await shot(pg, '03_night_flight.png')

        if pg.errs:
            print('console errors:', pg.errs[:5])
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        await pg.close()

if __name__ == '__main__':
    asyncio.run(main())
