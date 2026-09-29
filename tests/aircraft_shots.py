# Aircraft session screenshots: each type in the game at iPhone landscape (844x390).
# Chase view airborne by day, at night and inside the haboob, the cockpit (or nose
# camera) view on the runway, and the menu carousel with the type selected.
# Usage: .venv/bin/python tests/aircraft_shots.py <outdir> [type ...]
# Writes <outdir>/<type>_{day,night,haboob,cockpit,carousel}.png
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/aircraft/scenes')
TYPES = args[1:] or ['cessna', 'alpha', 'reaper', 'mq9b']
CRUISE_KT = {'f16': 420, 'c130': 250, 'cessna': 105, 'alpha': 90, 'reaper': 120, 'mq9b': 120}
SETUP_ALT = """([kt,alt])=>{const K=window.__kgeu,s=K.state();
  const V=kt/1.94384/Math.sqrt(1.097*Math.exp(-alt/9200)/1.225);
  s.pos.y=alt+K.groundHeight(s.pos.x,s.pos.z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60);return true;}"""

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        K = 'window.__kgeu'
        async def step(n):
            await pg.evaluate("(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/60);}", n)
        async def shot(name):
            await pg.screenshot(path=f'{OUT}/{name}.png', timeout=120000)
        async def cam(mode):
            await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)
        for t in TYPES:
            for tod in ['day', 'night', 'haboob']:
                await pg.evaluate(f"()=>{{{K}.setTOD('{tod}');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('runway');}}")
                await pg.wait_for_timeout(300); await cam(0)
                if tod == 'haboob':
                    await pg.evaluate(f"()=>{K}.haboobJump(-600)"); await step(3)
                await pg.evaluate(SETUP_ALT, [CRUISE_KT[t], 300])
                await step(90)
                await shot(f'{t}_{tod}')
            await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.start('runway');}}")
            await pg.wait_for_timeout(300); await cam(1); await step(20)
            await shot(f'{t}_cockpit')
            await cam(0)
            # the menu carousel on the Fly screen
            await pg.evaluate(f"()=>{{{K}.openMenu&&{K}.openMenu();}}")
            await pg.wait_for_timeout(300)
            await pg.evaluate("()=>{const b=document.getElementById('hFly');if(b)b.click();}")
            await pg.wait_for_timeout(300)
            await pg.evaluate(f"()=>{K}.pick('{t}')")
            await pg.evaluate("()=>{for(let i=0;i<40;i++)window.__kgeu.stepFrame(1/30);}")
            await pg.wait_for_timeout(600)
            await shot(f'{t}_carousel')
            await pg.evaluate("()=>{const m=document.getElementById('menu');if(m)m.classList.remove('on','see3d');}")
        if pg.errs: print('console errors:', pg.errs[:5])
        else: print('no console errors')
        await b.close()
    srv.shutdown()

asyncio.run(main())
