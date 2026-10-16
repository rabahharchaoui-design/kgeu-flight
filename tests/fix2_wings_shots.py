# fix2 before/after shots: chase view of each aircraft climbing out of Luke, Day and
# Sunset, 600 m AGL, 15 degrees nose up, 150 kt. Full frame plus a 2x nearest-neighbour
# crop of the centre 360x200 (the aircraft). AI traffic (airliner, heli) skipped: those
# are path-driven TRAFFIC entries, not placeable via the player state/camera hooks this
# harness uses for the player aircraft.
# Usage: .venv/bin/python tests/fix2_wings_shots.py [<outdir>] [type ...] [--out <outdir>]
# Writes <outdir>/wings_<type>_{day,sunset}.png and _crop variants; for the two MQ-9s also the climb with the dynamic
# scale forced to 0.7 (fix2 item 9's split frame): wings_<type>_day07.png and _crop
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

argv = sys.argv[1:]
out_flag = None
if '--out' in argv:
    i = argv.index('--out')
    out_flag = argv[i + 1]
    del argv[i:i + 2]
for a in list(argv):
    if a.startswith('--out='):
        out_flag = a.split('=', 1)[1]
        argv.remove(a)
args = [a for a in argv if not a.startswith('--')]
if out_flag:
    args = [out_flag] + args
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/fix2/before/wings')
TYPES = args[1:] or ['mq9b', 'reaper', 'f16', 'c130', 'a10', 'b737', 'a320', 'b747', 'cessna', 'archer', 'alpha']

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


def crop2x(src, dst):
    if not HAVE_PIL:
        print('  (PIL unavailable, skipped crop)', dst)
        return
    im = Image.open(src)
    w, h = im.size
    box = (w // 2 - 180, h // 2 - 100, w // 2 + 180, h // 2 + 100)
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
            for tod in ['day', 'sunset'] + (['day07'] if t in ('mq9b', 'reaper') else []):
                sc = 0.7 if tod == 'day07' else 1
                tod_id = 'day' if tod == 'day07' else tod
                await pg.evaluate(f"()=>{{{K}.setTOD('{tod_id}');{K}.pick('{t}');{K}.pickBase('luke');{K}.start('runway');}}")
                await pg.wait_for_timeout(300)
                await cam(0)
                await pg.evaluate(SETUP_CLIMB, [150, 600, 15])
                await pg.evaluate("(s)=>window.__kgeu.setScale(s)", sc)
                await step(24)
                full = os.path.join(OUT, f'wings_{t}_{tod}.png')
                await pg.screenshot(path=full, timeout=120000)
                print('  wrote', full)
                crop2x(full, os.path.join(OUT, f'wings_{t}_{tod}_crop.png'))
                if sc != 1:
                    await pg.evaluate("()=>window.__kgeu.setScale(1)")
        if pg.errs:
            print('  page errors:', pg.errs[:5])
        else:
            print('  no console errors')
        await b.close()
    srv.shutdown()

asyncio.run(main())
