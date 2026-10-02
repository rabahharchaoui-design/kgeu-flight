# Throwaway screenshot script for item 4.3 (Paris/LFPG landmarks). iPhone 15
# landscape (844x390 @2x), chase camera, Hard, Cessna unless stated. Modeled on
# tests/tokyo_shots.py's place/cam/shot recipe: synchronous K.stepFrame renders,
# a 12 frame settle before each capture, positions computed from real scene
# coordinates (K.PARIS.lm.*, K.CITYBB.list[0], K.wframe()).
# Usage: .venv/bin/python tests/paris_shots.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

K = 'window.__kgeu'
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'paris'))
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'lfpg'}


async def settle(pg, n=12):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)

async def cam(pg, mode=0):
    await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)

async def shot(pg, name, settle_n=12):
    if settle_n:
        await settle(pg, settle_n)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)

async def go(pg, ac, pos):
    await pg.evaluate("([t,p])=>{const K=window.__kgeu;K.pick(t);K.pickPos(p);K.start(p);}", [ac, pos])

# NOTE: a single K.snapCam() call followed by a plain stepFrame loop lets the
# aircraft drift (no pilot input, crosswind torque) by 10-15 degrees of heading
# within 0.2s, which knocks the chase camera off a close-in landmark sightline
# even though the landmark itself is correctly built and geometrically in the
# frustum (checked directly with Box3 + THREE.Frustum during triage). Re-pinning
# pose and calling snapCam() every settle frame removes that drift.
PLACE_PIN = """([cx,cz,brgDeg,dist,alt,hdgDeg,n])=>{const K=window.__kgeu,r=brgDeg*Math.PI/180,h=hdgDeg*Math.PI/180;
  const x=cx+dist*Math.sin(r),z=cz-dist*Math.cos(r),y=K.groundHeight(x,z)+alt;
  const s=K.state();
  const pin=()=>{s.pos.set(x,y,z);s.vel.set(Math.sin(h)*55,0,-Math.cos(h)*55);
    s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));if(s.w)s.w.set(0,0,0);
    s.onGround=false;s.crashed=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.5;s.flapIdx=0;s.ap=null;};
  pin();K.snapCam();
  for(let i=0;i<n;i++){pin();K.snapCam();K.stepFrame(1/60);}
  pin();K.snapCam();
  return {x,y,z};}"""

TAKEOFF_STEP = """(n)=>{const K=window.__kgeu;let s=K.state();
  for(let i=0;i<n&&!(s.crashed||(!s.onGround&&s.agl>=150));i++){K.stepFrame(1/30,false,true);s=K.state();}
  return {onGround:s.onGround,agl:Math.round(s.agl),crashed:s.crashed,why:s.crashReason};}"""


async def place(pg, cx, cz, brg, dist, alt, hdg):
    r = await pg.evaluate(PLACE_PIN, [cx, cz, brg, dist, alt, hdg, 12])
    await cam(pg, 0)
    return r


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=30000)
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        pts = await pg.evaluate("""()=>{const K=window.__kgeu,P=K.PARIS;const bb=K.CITYBB.list[0];
          return {eiffel:P.lm.eiffel,arc:P.lm.arc,sacre_coeur:P.lm.sacre_coeur,notre_dame:P.lm.notre_dame,
            grande_arche:P.lm.grande_arche,bb:[bb.x,bb.z,bb.hdg],rh:K.wframe().rh*180/Math.PI,axis:P.axis};}""")
        print('  landmark points:', pts)
        eiffel, arc, sc, nd, ga, bb, rh = pts['eiffel'], pts['arc'], pts['sacre_coeur'], pts['notre_dame'], pts['grande_arche'], pts['bb'], pts['rh']
        # the Arc's historical axis (Grande Arche -> Arc direction); approach from
        # beyond the Arc along that same axis so the vault opening and both pylons
        # read correctly, instead of an angle oblique to the monument's own walls
        import math
        ax = pts['axis']
        arc_brg = math.degrees(math.atan2(ax[0], -ax[1])) % 360
        arc_hdg = (arc_brg + 180) % 360

        # a: 3 nm final to 26L, day/night
        await go(pg, 'cessna', 'final'); await pg.wait_for_timeout(2000)
        await shot(pg, 'final3_day.png')
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await go(pg, 'cessna', 'final'); await pg.wait_for_timeout(2000)
        await shot(pg, 'final3_night.png')
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # b: 1 mile final, day
        await go(pg, 'cessna', 'final1'); await pg.wait_for_timeout(300)
        await shot(pg, 'final1_day.png')

        # c: F-16 takeoff from the runway, full throttle, capture at ~150 m AGL, day/night
        await go(pg, 'f16', 'runway'); await cam(pg, 0)
        await pg.evaluate(f"()=>{K}.auto()")
        land = None
        for _ in range(40):
            land = await pg.evaluate(TAKEOFF_STEP, 150)
            if land['crashed'] or (not land['onGround'] and land['agl'] >= 150):
                break
        print('  takeoff (day):', land)
        await shot(pg, 'takeoff_day.png')
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await go(pg, 'f16', 'runway'); await cam(pg, 0)
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(40):
            land = await pg.evaluate(TAKEOFF_STEP, 150)
            if land['crashed'] or (not land['onGround'] and land['agl'] >= 150):
                break
        print('  takeoff (night):', land)
        await shot(pg, 'takeoff_night.png')
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # d: Eiffel Tower, 700 m SE at 250 m, heading at it (NW), day/night/sparkle
        await go(pg, 'cessna', 'final')
        await place(pg, eiffel[0], eiffel[1], 135, 700, 250, 315)
        await shot(pg, 'eiffel_close.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await place(pg, eiffel[0], eiffel[1], 135, 700, 250, 315)
        await shot(pg, 'eiffel_night.png', settle_n=0)
        await pg.evaluate("()=>{window.__kgeu.PARIS.forceSparkle=true;}")
        await settle(pg, 6)
        await place(pg, eiffel[0], eiffel[1], 135, 700, 250, 315)
        await shot(pg, 'eiffel_sparkle.png', settle_n=0)
        await pg.evaluate("()=>{window.__kgeu.PARIS.forceSparkle=null;}")
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # e: Arc de Triomphe, 250 m out along its own historical axis at 60 m,
        # heading back at it (so the vault and both pylons are square to the camera)
        await place(pg, arc[0], arc[1], arc_brg, 250, 60, arc_hdg)
        await shot(pg, 'arc_close.png', settle_n=0)

        # f: Sacre-Coeur, south at 150 m, looking at it (north), should sit on a hill.
        # NOTE: the literal "500 m / 150 m" spec puts the dome directly behind our
        # own aircraft's tail in the chase view (confirmed: Box3+Frustum check shows
        # the dome IS geometrically in view at 500/150, it's just hidden behind the
        # ownship model at that exact distance/altitude) -- closer and a bit lower
        # clears our own tail and shows the dome sitting on its hill.
        await place(pg, sc[0], sc[1], 180, 300, 80, 0)
        await shot(pg, 'sacrecoeur_close.png', settle_n=0)

        # g: La Defense cluster and the Grande Arche, 1.2 km east at 200 m, looking west, day/night
        await place(pg, ga[0], ga[1], 90, 1200, 200, 270)
        await shot(pg, 'defense_close.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await place(pg, ga[0], ga[1], 90, 1200, 200, 270)
        await shot(pg, 'defense_night.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # h: 300 m above the Seine, 600 m west of Notre-Dame, looking east along the river
        await place(pg, nd[0], nd[1], 270, 600, 300, 90)
        await shot(pg, 'seine_notredame.png', settle_n=0)

        # i: 1,500 m over the Arc looking south east over the city, day/night
        await place(pg, arc[0], arc[1], 0, 0, 1500, 135)
        await shot(pg, 'city_wide_day.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await place(pg, arc[0], arc[1], 0, 0, 1500, 135)
        await shot(pg, 'city_wide_night.png', settle_n=0)
        await pg.evaluate(f"()=>{K}.setTOD('day')")

        # j: the @OhRabah billboard filling the frame, 40 m in front, 20 m up, facing it
        await place(pg, bb[0], bb[1], bb[2], 40, 20, rh)
        await shot(pg, 'billboard.png', settle_n=0)

        # k: ramp start chase camera at CDG (Terminal 1 drum area if visible)
        await go(pg, 'cessna', 'ramp'); await pg.wait_for_timeout(300); await cam(pg, 0)
        await shot(pg, 'ramp_day.png')

        if pg.errs:
            print('  console errors:', pg.errs[:5])
        await b.close()

asyncio.run(main())
