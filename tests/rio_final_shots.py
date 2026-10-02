# Verification screenshot script for the Rio Santos Dumont (SBRJ) review, item 4.4.
# Follows the paris_shots.py / rio_shots.py recipe: iPhone 15 landscape (844x390 @2x),
# chase camera, Hard, Cessna unless stated; re-pin pose and snapCam() every settle
# frame (an un-pinned stepFrame loop lets the aircraft drift off a close-in sightline);
# synchronous K.stepFrame renders. Verify-only: does not touch game code.
# Usage: .venv/bin/python tests/rio_final_shots.py
import asyncio, os, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

K = 'window.__kgeu'
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'rio'))
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'sbrj'}

# cx,cz: target point. brgDeg: compass bearing of the camera's position FROM the
# target. dist: metres out. y: absolute world altitude (Rio's field elevation is a
# few metres, so "N m altitude" and "N m AGL" are the same call here). hdgDeg: the
# aircraft's heading (0=north). n: settle frames, re-pinning pose each frame so wind
# drift never knocks a close-in landmark out of the chase-cam sightline.
PLACE = """([cx,cz,brgDeg,dist,y,hdgDeg,n])=>{const K=window.__kgeu,r=brgDeg*Math.PI/180,h=hdgDeg*Math.PI/180;
  const x=cx+dist*Math.sin(r),z=cz-dist*Math.cos(r),s=K.state();
  const pin=()=>{s.pos.set(x,y,z);s.vel.set(Math.sin(h)*55,0,-Math.cos(h)*55);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));if(s.w)s.w.set(0,0,0);
    s.onGround=false;s.crashed=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.5;s.flapIdx=0;s.ap=null;};
  pin();K.snapCam();for(let i=0;i<n;i++){pin();K.snapCam();K.stepFrame(1/60);}pin();K.snapCam();return {x,y,z};}"""

TAKEOFF_STEP = """(n)=>{const K=window.__kgeu;let s=K.state();
  for(let i=0;i<n&&!(s.crashed||(!s.onGround&&s.agl>=120));i++){K.stepFrame(1/30,false,true);s=K.state();}
  return {onGround:s.onGround,agl:Math.round(s.agl),crashed:s.crashed,why:s.crashReason};}"""


async def cam(pg, mode=0):
    await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)

async def shot(pg, name, settle_n=12):
    if settle_n:
        await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", settle_n)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)

async def go(pg, ac, pos):
    await pg.evaluate("([t,p])=>{const K=window.__kgeu;K.pick(t);K.pickPos(p);K.start(p);}", [ac, pos])

async def place(pg, c, brg, dist, y, hdg):
    await pg.evaluate(PLACE, [c[0], c[1], brg, dist, y, hdg, 12])
    await cam(pg, 0)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=30000)
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        pts = await pg.evaluate("""()=>{const K=window.__kgeu,R=K.RIO,bb=K.CITYBB.list[0];
          let north=R.arc.pts[0];for(const p of R.arc.pts)if(p.z<north.z)north=p;
          return {sug:R.lm.sugarloaf,cv:R.cv,bb:[R.bb.x,R.bb.z,bb.hdg],hc:R.hc,
            north:[north.x,north.z],rh:K.wframe().rh*180/Math.PI};}""")
        print('  landmark points:', pts)
        sug, cv, bb, hc, north = pts['sug'], pts['cv'], pts['bb'], pts['hc'], pts['north']

        # a: 3 mile final to 20L, day/night
        await go(pg, 'cessna', 'final'); await pg.wait_for_timeout(2000)
        await shot(pg, 'final3_day.png')
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await go(pg, 'cessna', 'final'); await pg.wait_for_timeout(2000)
        await shot(pg, 'final3_night.png')
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # b: 1 mile final, day
        await go(pg, 'cessna', 'final1'); await pg.wait_for_timeout(300)
        await shot(pg, 'final1_day.png')

        # c: C-130 takeoff from the runway, full throttle, capture at ~120 m AGL (Sugarloaf ahead left), day/night
        await go(pg, 'c130', 'runway'); await cam(pg, 0)
        await pg.evaluate(f"()=>{K}.auto()")
        land = None
        for _ in range(40):
            land = await pg.evaluate(TAKEOFF_STEP, 150)
            if land['crashed'] or (not land['onGround'] and land['agl'] >= 120):
                break
        print('  takeoff (day):', land)
        await shot(pg, 'takeoff_day.png')
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await go(pg, 'c130', 'runway'); await cam(pg, 0)
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(40):
            land = await pg.evaluate(TAKEOFF_STEP, 150)
            if land['crashed'] or (not land['onGround'] and land['agl'] >= 120):
                break
        print('  takeoff (night):', land)
        await shot(pg, 'takeoff_night.png')
        await pg.evaluate(f"()=>{K}.setTOD('day')")
        await go(pg, 'cessna', 'final')

        # d: 900 m NW of the Sugarloaf summit, 300 m altitude, heading at it (cable car / Urca in view if possible)
        await place(pg, sug, 315, 900, 300, 135)
        await shot(pg, 'sugarloaf_close.png', settle_n=0)

        # e: 400 m north of Christ, 720 m altitude, heading at it; night too
        await place(pg, cv, 0, 400, 720, 180)
        await shot(pg, 'cristo_close.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await place(pg, cv, 0, 400, 720, 180)
        await shot(pg, 'cristo_night.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # f: 300 m over the north end of Copacabana, looking south west along the beach; night too
        await place(pg, north, 0, 0, 300, 225)
        await shot(pg, 'copacabana.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await place(pg, north, 0, 0, 300, 225)
        await shot(pg, 'copacabana_night.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # g: 400 m over the bay 2 km north of the airport, looking east at the Niteroi bridge
        await place(pg, [0, 0], 0, 2000, 400, 90)
        await shot(pg, 'bay_bridge.png', settle_n=0)

        # h: the @OhRabah billboard, 40 m in front (along the way it faces), 20 m up, facing it
        await place(pg, bb[:2], bb[2], 40, 20, (bb[2] + 180) % 360)
        await shot(pg, 'billboard.png', settle_n=0)

        # i: ramp start, chase camera
        await go(pg, 'cessna', 'ramp'); await pg.wait_for_timeout(300); await cam(pg, 0)
        await shot(pg, 'ramp_day.png')

        # j: 1,000 m over the airport looking south (Centro, Sugarloaf, mountains)
        await place(pg, [0, 0], 0, 0, 1000, 180)
        await shot(pg, 'city_wide.png', settle_n=0)

        if pg.errs:
            print('  console errors:', pg.errs[:5])
        await b.close()

asyncio.run(main())
