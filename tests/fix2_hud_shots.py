# fix2 before/after shots: the C-130 airdrop HUD flown to the ONE MINUTE radio call
# (#atc visible) with the objective banner (#miss) up, at four sizes; the strike range
# HUD and the dogfight HUD at 844x390.
# The run-in placement and per-tick line correction are lifted from tests/dz_check.py's
# PLACE/steer helpers: 4,828 m (3 nm) before the drop zone's release point along the
# wind-aligned run-in line, 1,000 ft, 140 kt, with velocity re-aligned to the line and
# cross-track error zeroed every 0.5 s (0.36 throttle alone can't hold 140 kt in this
# configuration -- airspeed bleeds off and settles near 55 m/s before DZ.tRel starts
# falling through 60, confirmed by hand before writing this loop).
# Usage: .venv/bin/python tests/fix2_hud_shots.py <outdir> [airdrop|range|dogfight ...]
# Writes <outdir>/hud_airdrop_<size>.png, hud_range_844.png, hud_dogfight_844.png
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/fix2/before/hud')
MODES = args[1:] or ['airdrop', 'range', 'dogfight']
K = 'window.__kgeu'

SIZES = [{'width': 568, 'height': 320}, IPHONE_15, {'width': 932, 'height': 430}, {'width': 390, 'height': 844}]
if '--sizes' in sys.argv:
    want = sys.argv[sys.argv.index('--sizes') + 1].split(',')
    SIZES = [s for s in SIZES if f'{s["width"]}x{s["height"]}' in want]

PLACE_DZ = f"""()=>{{const K={K},D=K.DZ,s=K.state(),f=D.f,x=D.rel.x-f.x*4828,z=D.rel.z-f.z*4828,gh=K.groundHeight?K.groundHeight(x,z):0;
  const V=140/1.94384;s.pos.set(x,(gh||0)+305+2,z);s.vel.set(f.x*V,0,f.z*V);s.quat.setFromEuler(new THREE.Euler(0.03,-Math.atan2(f.x,-f.z),0,'YXZ'));
  s.w.set(0,0,0);s.throttle=s.power=0.36;s.flapIdx=1;s.trim=0.5;s.airTime=30;s.onGround=false;s.gearDown=false;s.gearPos=0;s.ap=null;}}"""
# dz_check's per-tick steer: snap cross-track to zero, keep velocity aligned to the run-in
# line, hold drop altitude -- 5 corrections of 15 skip-render steps (0.5 s) per call
STEER = f"""(n)=>{{const K={K},s=K.state(),D=K.DZ;for(let k=0;k<n;k++){{if(!K.MISS.dropped){{
    const f=D.f,dx=s.pos.x-D.rel.x,dz=s.pos.z-D.rel.z,c=-dx*f.z+dz*f.x,sp=Math.hypot(s.vel.x,s.vel.z);
    s.pos.x-=-f.z*c*0.5;s.pos.z-=f.x*c*0.5;s.vel.x=f.x*sp;s.vel.z=f.z*sp;
    s.quat.setFromEuler(new THREE.Euler(new THREE.Euler().setFromQuaternion(s.quat,'YXZ').x,-Math.atan2(f.x,-f.z),0,'YXZ'));}}
  for(let j=0;j<15;j++){{K.stepFrame(1/30,false,true);
    if(!K.MISS.dropped){{const gh=K.groundHeight(s.pos.x,s.pos.z);s.pos.y+=(gh+305-s.pos.y)*0.05;}}}}}}
  return {{c1:D.c1}};}}"""


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def airdrop_one(pg, size):
    await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.radioLog(true);{K}.mission('drop')}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(PLACE_DZ)
    # bulk-advance without drawing (headless software rendering is slow): the C-130
    # decelerates from 140 kt at this throttle/flap setting and DZ.tRel climbs before
    # falling back through 60 once airspeed settles, ~22 s of sim time in testing
    c1 = False
    for i in range(16):   # up to 40 s of sim time, 2.5 s slices
        st = await pg.evaluate(STEER, 5)
        c1 = st['c1']
        if c1:
            break
    # a few real (drawing) frames so #atc and #miss pick up the new state
    atc = miss = False
    for i in range(20):
        st = await pg.evaluate(f"()=>{{window.__kgeu.stepFrame(1/30);return {{atc:document.getElementById('atc').classList.contains('on'),miss:document.getElementById('miss').classList.contains('on')}};}}")
        atc, miss = st['atc'], st['miss']
        if atc and miss:
            break
    print(f'  airdrop {size["width"]}x{size["height"]}: one-minute call={c1} atc={atc} miss={miss}')
    await shot(pg, f'hud_airdrop_{size["width"]}x{size["height"]}.png')


async def range_shot(pg):
    await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.mission('range')}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{{for(let j=0;j<60;j++)window.__kgeu.stepFrame(1/30);}}")
    await shot(pg, 'hud_range_844.png')


async def dogfight_shot(pg):
    await pg.evaluate(f"()=>{{{K}.DF.test.noBrief=true;{K}.DF.test.noBanditFire=true;{K}.dfStart();}}")
    await pg.evaluate(f"()=>{{for(let j=0;j<40;j++)window.__kgeu.stepFrame(1/30);}}")
    await shot(pg, 'hud_dogfight_844.png')


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if 'airdrop' in MODES:
            for size in SIZES:
                pg = await page(b, url, vp=size, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
                await airdrop_one(pg, size)
                if pg.errs:
                    print(f'  page errors (airdrop {size["width"]}x{size["height"]}):', pg.errs[:5])
                await pg.context.close()
        if 'range' in MODES:
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await range_shot(pg)
            if pg.errs:
                print('  page errors (range):', pg.errs[:5])
            await pg.context.close()
        if 'dogfight' in MODES:
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await dogfight_shot(pg)
            if pg.errs:
                print('  page errors (dogfight):', pg.errs[:5])
            await pg.context.close()
        await b.close()
    srv.shutdown()

asyncio.run(main())
