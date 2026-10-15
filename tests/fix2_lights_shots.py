# fix2 before/after shots: chase view (default, from behind and slightly above) of each
# of the 11 flyable aircraft climbing out, at Sunset and Night, so the aft white light,
# strobes and wingtip nav lights show. Full frame plus a 2x nearest-neighbour crop of the
# aircraft; for the two MQ-9s an extra crop of the tail cone / pusher-prop region.
#
# Strobes flash off uTime (performance.now()) in the light shader with a 1.2 s period,
# phase 0 for every light, lit during the window t mod 1.2 in [0, 0.06) (see index.html's
# aclMat vertex shader). Rather than sample 6 live frames and hope one lands in that 60 ms
# window, this uses the test hook __kgeu.lightClock(t) (AL_TFREEZE) to freeze the light
# clock at t=0.03 s, which is always inside the lit window, before every shot -- the same
# effect ("keep the one where the strobe is on") but deterministic under slow headless
# rendering.
# Usage: .venv/bin/python tests/fix2_lights_shots.py <outdir> [type ...]
# Writes <outdir>/lights_<type>_{sunset,night}.png and _crop variants, plus
# lights_<mq9a|mq9b>_{sunset,night}_tailcrop.png for the two MQ-9s.
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/fix2/before/lights')
TYPES = args[1:] or ['mq9b', 'reaper', 'f16', 'c130', 'a10', 'b737', 'a320', 'b747', 'cessna', 'archer', 'alpha']
MQ9 = {'mq9b': 'mq9b', 'reaper': 'mq9a'}   # reaper's display name is MQ-9A

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

SETUP_CLIMB = """([kt,alt,pitchDeg])=>{const K=window.__kgeu,s=K.state();
  const V=kt/1.94384/Math.sqrt(1.097*Math.exp(-alt/9200)/1.225),pr=pitchDeg*Math.PI/180;
  s.pos.y=alt+K.groundHeight(s.pos.x,s.pos.z);s.quat.setFromEuler(new THREE.Euler(pr,0,0,'YXZ'));
  s.vel.set(0,V*Math.sin(pr),-V*Math.cos(pr));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.85;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60);return true;}"""


def crop2x(src, dst, cx_off=0, cy_off=0, half_w=180, half_h=100):
    if not HAVE_PIL:
        print('  (PIL unavailable, skipped crop)', dst)
        return
    im = Image.open(src)
    w, h = im.size
    cx, cy = w // 2 + cx_off, h // 2 + cy_off
    box = (cx - half_w, cy - half_h, cx + half_w, cy + half_h)
    c = im.crop(box)
    c = c.resize((c.width * 2, c.height * 2), Image.NEAREST)
    c.save(dst)
    print('  wrote', dst)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        K = 'window.__kgeu'

        async def step(n):
            await pg.evaluate("(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/60);}", n)

        async def cam(mode):
            await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)

        for t in TYPES:
            for tod in ['sunset', 'night']:
                await pg.evaluate(f"()=>{{{K}.setTOD('{tod}');{K}.pick('{t}');{K}.pickBase('luke');{K}.start('runway');}}")
                await pg.wait_for_timeout(300)
                await cam(0)
                await pg.evaluate(SETUP_CLIMB, [150, 600, 15])
                await step(24)
                await pg.evaluate("(t)=>window.__kgeu.lightClock(t)", 0.03)
                await step(1)
                full = os.path.join(OUT, f'lights_{t}_{tod}.png')
                await pg.screenshot(path=full, timeout=120000)
                print('  wrote', full)
                crop2x(full, os.path.join(OUT, f'lights_{t}_{tod}_crop.png'))
                if t in MQ9:
                    crop2x(full, os.path.join(OUT, f'lights_{MQ9[t]}_{tod}_tailcrop.png'), cy_off=20, half_w=150, half_h=100)
                await pg.evaluate("()=>window.__kgeu.lightClock(null)")
        if pg.errs:
            print('  page errors:', pg.errs[:5])
        else:
            print('  no console errors')
        await b.close()
    srv.shutdown()

asyncio.run(main())
