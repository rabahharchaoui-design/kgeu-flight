# Throwaway verification script for item 4.2 (Tokyo/RJTT landmarks). Two things:
#   1) a relative frame-cost comparison: Tokyo 3 nm final by day/night vs the same
#      Arizona (KGEU) scenario, counting rAF frames over 6 s the way
#      tests/aircraft_fps.py's fps() does. Headless software rendering quantises
#      rAF to a handful of steps (see aircraft_fps.py's own comment), so this is a
#      coarse relative flag, not an absolute number.
#   2) landmark screenshots: iPhone 15 landscape (844x390 @2x), Hard, Cessna unless
#      stated. Positions are computed from real scene coordinates (queried from
#      tokyo_tower/skytree/rainbow_tower_n/s Box3 centers, K.CITYBB, and
#      K.WORLD.data.landmarks for Shinjuku -- there's no dedicated Shinjuku mesh,
#      the five skyline clusters share one InstancedMesh named 'tokyo_skyline').
#      Bearing/heading convention matches the engine's own (wX/wZ, fr.rh): for a
#      compass bearing h in radians, x=sin(h), z=-cos(h), and a heading quaternion
#      is new THREE.Euler(0,-h,0,'YXZ'). The bay is south/south-east of the ARP;
#      the landmarks are north of it.
# Usage: .venv/bin/python tests/tokyo_shots.py [--fps-only|--shots-only]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

K = 'window.__kgeu'
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'tokyo'))
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'rjtt'}

DO_FPS = '--shots-only' not in sys.argv
DO_SHOTS = '--fps-only' not in sys.argv


# ---------------- part 1: frame cost ----------------

async def fps(pg, seconds=6.0, warm=2.0):
    await pg.wait_for_timeout(int(warm * 1000))
    await pg.evaluate("""()=>{window.__stop=1;window.__f=0;setTimeout(()=>{window.__stop=0;
      const t=()=>{if(window.__stop)return;window.__f++;requestAnimationFrame(t);};requestAnimationFrame(t);},60);}""")
    await pg.wait_for_timeout(int(seconds * 1000) + 60)
    return await pg.evaluate("()=>{window.__stop=1;return window.__f;}") / seconds

async def fps_scenario(b, url, region, tod):
    storage = dict(BASE) if region != 'az' else {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
    pg = await page(b, url, vp=IPHONE_15, storage=storage)
    if region != 'az':
        await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=20000)
    await pg.evaluate(f"()=>{{{K}.setTOD('{tod}');{K}.pick('cessna');{K}.pickPos('final');{K}.start('final');}}")
    await pg.wait_for_timeout(1000)
    f = await fps(pg)
    errs = list(pg.errs)
    await pg.context.close()
    return f, errs

async def run_fps(b, url):
    print('--- frame cost: Tokyo 3 nm final vs Arizona KGEU 3 nm final ---')
    out, errs = {}, []
    for label, region, tod in [('tokyo_day', 'rjtt', 'day'), ('tokyo_night', 'rjtt', 'night'),
                                ('az_day', 'az', 'day'), ('az_night', 'az', 'night')]:
        out[label], e = await fps_scenario(b, url, region, tod)
        errs += e
        print(f'  {label}: {out[label]:.2f} fps')
    ratio = out['tokyo_night'] / out['az_day'] if out['az_day'] else 0
    print(f"  tokyo_night / az_day = {ratio:.2f} ({'OK' if ratio >= 0.70 else 'FLAG: under 70% of Arizona day baseline'})")
    if errs:
        print('  page errors:', errs[:5])
    return out


# ---------------- part 2: screenshots ----------------

async def settle(pg, n=12):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)

async def cam(pg, mode=0):
    await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)

async def shot(pg, name):
    await settle(pg, 12)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)

async def go(pg, ac, pos):
    await pg.evaluate("([t,p])=>{const K=window.__kgeu;K.pick(t);K.pickPos(p);K.start(p);}", [ac, pos])

PLACE = """([cx,cz,brgDeg,dist,alt,hdgDeg])=>{const K=window.__kgeu,r=brgDeg*Math.PI/180,h=hdgDeg*Math.PI/180;
  const x=cx+dist*Math.sin(r),z=cz-dist*Math.cos(r),y=K.groundHeight(x,z)+alt;
  const s=K.state();s.pos.set(x,y,z);s.vel.set(Math.sin(h)*55,0,-Math.cos(h)*55);
  s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));if(s.w)s.w.set(0,0,0);
  s.onGround=false;s.crashed=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.5;s.flapIdx=0;s.ap=null;
  K.snapCam();return {x,y,z};}"""

TAKEOFF_STEP = """(n)=>{const K=window.__kgeu;let s=K.state();
  for(let i=0;i<n&&!(s.crashed||(!s.onGround&&s.agl>=150));i++){K.stepFrame(1/30,false,true);s=K.state();}
  return {onGround:s.onGround,agl:Math.round(s.agl),crashed:s.crashed,why:s.crashReason};}"""


async def place(pg, cx, cz, brg, dist, alt, hdg):
    r = await pg.evaluate(PLACE, [cx, cz, brg, dist, alt, hdg])
    await cam(pg, 0)
    return r


async def run_shots(b, url):
    os.makedirs(OUT, exist_ok=True)
    print('--- screenshots ---')
    pg = await page(b, url, vp=IPHONE_15, storage=BASE)
    await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=30000)
    await pg.evaluate(f"()=>{K}.setTOD('day')")

    pts = await pg.evaluate("""()=>{const K=window.__kgeu,S=K.R3().scene,B=new THREE.Box3(),o={};
      for(const n of ['tokyo_tower','skytree','rainbow_tower_n','rainbow_tower_s']){
        const g=S.getObjectByName(n);B.setFromObject(g);o[n]=[(B.min.x+B.max.x)/2,(B.min.z+B.max.z)/2];}
      const fr=K.wframe();o.APC=[-fr.woff[0],-fr.woff[1]];o.fujiBrg=K.TKY.fujiBrg;
      const bb=K.CITYBB.list[0];o.bb=[bb.x,bb.z,bb.hdg];
      const land=K.WORLD.data.landmarks,sj=land.find(l=>l.id==='shinjuku');o.shinjuku=[sj.x-fr.woff[0],sj.z-fr.woff[1]];
      return o;}""")
    print('  landmark points:', pts)
    tower, skytree = pts['tokyo_tower'], pts['skytree']
    bridge = [(pts['rainbow_tower_n'][0] + pts['rainbow_tower_s'][0]) / 2, (pts['rainbow_tower_n'][1] + pts['rainbow_tower_s'][1]) / 2]
    apc, fujiBrg, bb, shinjuku = pts['APC'], pts['fujiBrg'], pts['bb'], pts['shinjuku']

    # a: 3 nm final, day/night
    await go(pg, 'cessna', 'final'); await pg.wait_for_timeout(2000)
    await shot(pg, 'final3_day.png')
    await pg.evaluate(f"()=>{K}.setTOD('night')")
    await go(pg, 'cessna', 'final'); await pg.wait_for_timeout(2000)
    await shot(pg, 'final3_night.png')
    await pg.evaluate(f"()=>{K}.setTOD('day')")

    # b: 1 nm final, day/night
    await go(pg, 'cessna', 'final1'); await pg.wait_for_timeout(300)
    await shot(pg, 'final1_day.png')
    await pg.evaluate(f"()=>{K}.setTOD('night')")
    await go(pg, 'cessna', 'final1'); await pg.wait_for_timeout(300)
    await shot(pg, 'final1_night.png')
    await pg.evaluate(f"()=>{K}.setTOD('day')")

    # c: F-16 takeoff, day/night, full throttle to ~150 m AGL
    await go(pg, 'f16', 'runway'); await cam(pg, 0)
    await pg.evaluate(f"()=>{K}.auto()")
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

    # d: Tokyo Tower, 600 m SE at 200 m, heading at it (NW)
    await go(pg, 'cessna', 'final')
    await place(pg, tower[0], tower[1], 135, 600, 200, 315)
    await shot(pg, 'tower_close.png')
    await pg.evaluate(f"()=>{K}.setTOD('night')")
    await place(pg, tower[0], tower[1], 135, 600, 200, 315)
    await shot(pg, 'tower_night.png')
    await pg.evaluate(f"()=>{K}.setTOD('day')")

    # e: Skytree, 900 m SE at 400 m, heading at it (NW)
    await place(pg, skytree[0], skytree[1], 135, 900, 400, 315)
    await shot(pg, 'skytree_close.png')

    # f: Rainbow Bridge, 800 m south at 300 m, looking north
    await place(pg, bridge[0], bridge[1], 180, 800, 300, 0)
    await shot(pg, 'bridge_close.png')

    # g: Shinjuku at night, 500 m above, 300 m north of the cluster, looking south at the towers
    await pg.evaluate(f"()=>{K}.setTOD('night')")
    await place(pg, shinjuku[0], shinjuku[1], 0, 300, 500, 180)
    await shot(pg, 'shinjuku_night.png')

    # city wide at night: 1,200 m over the bay, looking at the city. The modelled
    # water for RJTT is east of the ARP (see tests/world_check.py's own "water 3 km
    # east of the ARP" check), not south -- due south of the ARP at this distance
    # reads as land (isWater false), so "over the bay" uses east instead; the
    # landmarks are north/NNW of the ARP, so heading ~340 still looks back at the
    # skyline from out over the water.
    water = await pg.evaluate("(p)=>window.__kgeu.isWater(p[0]+3000,p[1])", apc)
    print('  east point is water:', water)
    await place(pg, apc[0], apc[1], 90, 3000, 1200, 340)
    await shot(pg, 'city_night_wide.png')
    await pg.evaluate(f"()=>{K}.setTOD('day')")

    # h: the billboard, filling a good part of the frame, facing it. The board is an
    # 18x5 m sign only ~13 m tall; at the literal "150 m / 30 m" spec it is
    # technically inside the camera frustum (checked) but visually a negligible dark
    # sliver against the haze -- too small and too far below the chase camera's
    # near-level sightline to read. Closer in and lower gets the stated "filling a
    # good part of the frame" result while keeping the same facing-it geometry.
    rh = await pg.evaluate("()=>window.__kgeu.wframe().rh*180/Math.PI")
    await place(pg, bb[0], bb[1], bb[2], 40, 20, rh)
    await shot(pg, 'billboard.png')

    # i: ramp start, day, chase (terminal look)
    await go(pg, 'cessna', 'ramp'); await pg.wait_for_timeout(300); await cam(pg, 0)
    await shot(pg, 'ramp_day.png')

    # j: 1,000 m over the airport, heading 309 (toward Fuji), day
    await go(pg, 'cessna', 'final')
    await place(pg, apc[0], apc[1], 0, 0, 1000, fujiBrg)
    await shot(pg, 'fuji_wide.png')

    if pg.errs:
        print('  console errors:', pg.errs[:5])
    await pg.context.close()


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if DO_FPS:
            await run_fps(b, url)
        if DO_SHOTS:
            await run_shots(b, url)
        await b.close()

asyncio.run(main())
