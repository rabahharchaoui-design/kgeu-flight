# Throwaway screenshots for the world region framework (item 4.5/4.6). iPhone 15
# landscape (844x390, device scale 2), Hard mode (kgeuOnboard=pilot), Cessna unless
# stated. Follows the start recipe in tests/world_check.py: seed localStorage with
# kgeuRegion before load, wait for window.__kgeu.WORLD.ready, then pick/pickPos/start.
#
# There is no dedicated top-down camera in this build (only Chase, Nose camera and
# the Sensor ball on the Reaper/MQ-9B -- see hasBall() in index.html), so the
# "overhead" shot always uses the prescribed fallback: the aircraft placed 800 m
# above the field, 2 km south of the ARP, heading north, in the normal chase view.
#
# Usage: .venv/bin/python tests/world_region_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'regions'))
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}

# place the aircraft 800 m above the field, 2 km south of the ARP, heading north,
# straight and level, in the normal (chase) camera -- the overhead fallback
PLACE_OVERHEAD = """()=>{const K=window.__kgeu,o=K.wframe().woff,ax=-o[0],az=-o[1];
  const gy=K.groundHeight(ax,az),x=ax,z=az+2000,y=gy+800;
  const s=K.state();s.pos.set(x,y,z);s.quat.set(0,0,0,1);s.vel.set(0,0,-30);if(s.w)s.w.set(0,0,0);
  s.onGround=false;s.crashed=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.5;s.flapIdx=0;s.ap=null;
  K.snapCam();
  return {x:x,y:y,z:z,gy:gy};}"""

# step the sim (no render, fast) until airborne and ~150 m AGL, a crash, or the cap
TAKEOFF_STEP = """(n)=>{const K=window.__kgeu;let s=K.state();
  for(let i=0;i<n&&!(s.crashed||(!s.onGround&&s.agl>=150));i++){K.stepFrame(1/30,false,true);s=K.state();}
  return {onGround:s.onGround,agl:Math.round(s.agl),crashed:s.crashed,why:s.crashReason};}"""


async def cam(pg, mode):
    await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)


async def settle(pg, n=4):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)


async def shot(pg, name):
    # force a synchronous render right before capture: headless software rendering
    # paces its real rAF loop very slowly (~3 fps), so a short wait_for_timeout can
    # leave the canvas showing a stale frame from before the last start()/setTOD().
    # 12 frames of 1/60 s = 200 ms sim time, comfortably past the HUD's own 80 ms
    # (hudT=0.08 in index.html) refresh throttle, so the instrument text (KIAS,
    # ALT, VS, the AUTO banner) can't still be showing the previous aircraft/mode.
    await settle(pg, 12)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def go(pg, ac, pos):
    await pg.evaluate("([t,p])=>{const K=window.__kgeu;K.pick(t);K.pickPos(p);K.start(p);}", [ac, pos])


async def region_shots(b, url, rid):
    print(f'\n--- {rid} ---')
    storage = dict(BASE)
    if rid != 'az':
        storage['kgeuRegion'] = rid
    pg = await page(b, url, vp=IPHONE_15, storage=storage)
    if rid != 'az':
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=20000)
        r = await pg.evaluate("()=>({ready:window.__kgeu.WORLD.ready,err:window.__kgeu.WORLD.err})")
        print('  WORLD.ready', r)

    if rid == 'az':
        await go(pg, 'cessna', 'runway')
        await pg.wait_for_timeout(1000)
        await cam(pg, 0)
        await shot(pg, 'az_runway_day.png')
        if pg.errs: print('  console errors:', pg.errs[:5])
        await pg.context.close()
        return

    # a: runway, day, chase, after 1 s
    await go(pg, 'cessna', 'runway')
    await pg.wait_for_timeout(1000)
    await cam(pg, 0)
    await shot(pg, f'{rid}_runway_day.png')

    # b: ramp, day, chase (shows the terminal ahead)
    await go(pg, 'cessna', 'ramp')
    await pg.wait_for_timeout(300)
    await cam(pg, 0)
    await shot(pg, f'{rid}_ramp_day.png')

    # c: 3 nm final, day, default camera, after 2 s
    await go(pg, 'cessna', 'final')
    await pg.wait_for_timeout(2000)
    await shot(pg, f'{rid}_final_day.png')

    # d: 1 nm final, day, default camera
    await go(pg, 'cessna', 'final1')
    await pg.wait_for_timeout(300)
    await shot(pg, f'{rid}_final1_day.png')

    # e: runway, F-16, full throttle, stepped to ~150 m AGL, default camera
    await go(pg, 'f16', 'runway')
    await cam(pg, 0)
    await pg.evaluate(f"()=>{K}.auto()")   # autoSmart(): on the ground with no ap -> takeoff mode, full throttle
    land = None
    for _ in range(40):
        land = await pg.evaluate(TAKEOFF_STEP, 150)
        if land['crashed'] or (not land['onGround'] and land['agl'] >= 150):
            break
    print('  takeoff state:', land)
    await settle(pg, 4)
    await shot(pg, f'{rid}_takeoff_day.png')

    # f: final and ramp at night
    await pg.evaluate(f"()=>{K}.setTOD('night')")
    await go(pg, 'cessna', 'final')
    await pg.wait_for_timeout(2000)
    await shot(pg, f'{rid}_final_night.png')
    await go(pg, 'cessna', 'ramp')
    await pg.wait_for_timeout(300)
    await cam(pg, 0)
    await shot(pg, f'{rid}_ramp_night.png')
    await pg.evaluate(f"()=>{K}.setTOD('day')")

    # g: overhead fallback -- 800 m above the field, 2 km south of the ARP, heading
    # north, chase camera, so the whole airport is visible
    await go(pg, 'cessna', 'final')
    place = await pg.evaluate(PLACE_OVERHEAD)
    print('  overhead placed at', place)
    await cam(pg, 0)
    await settle(pg, 6)
    await shot(pg, f'{rid}_overhead.png')

    if pg.errs:
        print('  console errors:', pg.errs[:5])
    await pg.context.close()


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for rid in ['rjtt', 'lfpg', 'sbrj', 'az']:
            await region_shots(b, url, rid)
        await b.close()
    srv.shutdown()


asyncio.run(main())
