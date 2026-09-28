# Item 3.1 screenshots: chase-camera rolls and a loop, iPhone landscape (844x390).
# Pilot mode, F-16/C-130/Cessna at ~2000 m over Glendale (KGEU), full throttle.
# Reuses the same page hooks as tests/roll_check.py: __kgeu.state() to place the
# aircraft, __kgeu.snapCam(), __kgeu.touchIn for stick input, __kgeu.stepFrame(1/60)
# to advance frames. Unlike roll_check, stepFrame is called WITHOUT the skipRender
# flag so every step actually draws, since these are screenshots not a fast check.
# Usage: .venv/bin/python tests/roll_shots.py [outdir]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'overnight-screenshots/roll')
CRUISE_KT = {'f16': 420, 'c130': 250, 'cessna': 110}

# Place the aircraft `alt` metres over its current (Glendale) position, level, at
# cruise speed for its type, full throttle, gear up. Mirrors roll_check.py's SETUP.
SETUP = """([kt,alt])=>{const K=window.__kgeu,s=K.state();
  const V=kt/1.94384/Math.sqrt(1.097*Math.exp(-alt/9200)/1.225);
  s.pos.y=alt+K.groundHeight(s.pos.x,s.pos.z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=1;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60);return true;}"""

# Advance n frames holding the stick at (ail,elev), rendering every frame, and report
# the net roll (about the body -z/nose axis) and pitch (about the body x axis) over
# the whole span as a single delta quaternion. n is kept small per call (default 6
# frames = 0.1s) so the rotation within one call stays well under 180 deg and the
# axis-angle decomposition can't wrap.
ADV = """([n,ail,elev])=>{const K=window.__kgeu,s=K.state(),T=THREE;
  const q0=new T.Quaternion().copy(s.quat);
  K.touchIn.active=true;K.touchIn.ail=ail;K.touchIn.elev=elev;
  for(let i=0;i<n;i++){K.stepFrame(1/60);if(s.crashed)break;}
  const dq=q0.clone().invert().multiply(s.quat);
  if(dq.w<0){dq.x=-dq.x;dq.y=-dq.y;dq.z=-dq.z;dq.w=-dq.w;}
  const a=2*Math.acos(Math.min(1,dq.w)),sn=Math.sqrt(Math.max(1e-12,1-dq.w*dq.w));
  const roll=sn>1e-6?(-dq.z/sn*a)*180/Math.PI:0;
  const pitch=sn>1e-6?(dq.x/sn*a)*180/Math.PI:0;
  return {roll,pitch,crashed:!!s.crashed};}"""

RELEASE = "()=>{const K=window.__kgeu;K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;}"


async def setup(pg, t, alt=2000):
    await pg.evaluate("(t)=>{const K=window.__kgeu;K.pick(t);K.pickBase('kgeu');K.start('final');}", t)
    await pg.wait_for_timeout(600)
    if await pg.evaluate("()=>window.__kgeu.camMode()") != 0:
        await pg.evaluate("()=>{while(window.__kgeu.camMode()!==0)window.__kgeu.cycleCam();}")
    await pg.evaluate(SETUP, [CRUISE_KT.get(t, 150), alt])


async def drive_to(pg, axis, target_deg, ail, elev, chunk=0.1, max_sec=10.0):
    """Hold the stick and step frames in small chunks, summing |roll| or |pitch|,
    until the target angle is reached, the aircraft crashes, or max_sec elapses."""
    n = max(1, round(chunk * 60))
    total = elapsed = 0.0
    crashed = False
    while abs(total) < target_deg and elapsed < max_sec:
        m = await pg.evaluate(ADV, [n, ail, elev])
        total += m['roll'] if axis == 'roll' else m['pitch']
        elapsed += chunk
        if m['crashed']:
            crashed = True
            break
    await pg.evaluate(RELEASE)
    return total, crashed, elapsed


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path)
    print('  wrote', path)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15,
                         storage={'kgeuOnboard': 'pilot', 'kgeuType': 'f16', 'kgeuTut': '1', 'kgeuCoach': '3'})

        # F-16: roll through 90, then on to ~180 (inverted), then on to ~270.
        await setup(pg, 'f16')
        cum = 0.0
        for name, add in [('f16_roll_90.png', 90), ('f16_inverted.png', 90), ('f16_roll_270.png', 90)]:
            d, crashed, el = await drive_to(pg, 'roll', add, 1.0, 0.0, max_sec=6)
            cum += d
            print(f'{name}: +{d:.0f} deg (cumulative bank {cum:.0f} deg) in {el:.1f}s, crashed={crashed}')
            await shot(pg, name)
            if crashed:
                break

        # F-16: fresh level start, full pull to near the top of a loop (~180 deg pitch).
        await setup(pg, 'f16')
        d, crashed, el = await drive_to(pg, 'pitch', 178, 0.0, 1.0, max_sec=12)
        print(f'f16_loop_top.png: pitch {d:.0f} deg in {el:.1f}s, crashed={crashed}')
        await shot(pg, 'f16_loop_top.png')

        # C-130: 90 deg bank.
        await setup(pg, 'c130')
        d, crashed, el = await drive_to(pg, 'roll', 90, 1.0, 0.0, max_sec=8)
        print(f'c130_roll_90.png: {d:.0f} deg in {el:.1f}s, crashed={crashed}')
        await shot(pg, 'c130_roll_90.png')

        # Cessna: aim for inverted (180), settle for whatever it actually reaches.
        await setup(pg, 'cessna')
        d, crashed, el = await drive_to(pg, 'roll', 178, 1.0, 0.0, max_sec=15)
        print(f'cessna_inverted.png: {d:.0f} deg in {el:.1f}s, crashed={crashed} (target 180, reported as reached)')
        await shot(pg, 'cessna_inverted.png')

        # F-16 again, cockpit/nose camera, ~60 deg bank.
        await setup(pg, 'f16')
        await pg.evaluate("()=>window.__kgeu.cycleCam()")
        await pg.wait_for_timeout(200)
        d, crashed, el = await drive_to(pg, 'roll', 60, 1.0, 0.0, max_sec=5)
        print(f'f16_cockpit_bank.png: cam {await pg.evaluate("()=>window.__kgeu.camMode()")} {d:.0f} deg in {el:.1f}s, crashed={crashed}')
        await shot(pg, 'f16_cockpit_bank.png')

        if pg.errs:
            print('console errors:', pg.errs[:5])
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        await pg.context.close()
        await b.close()
    srv.shutdown()

asyncio.run(main())
