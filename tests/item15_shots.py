# Screenshot sequences for phone notes 0929, item 15 (cinematic explosions), at iPhone
# landscape (844x390, dsf 2). For a Hellfire impact on the range, an F-16 crash and a C-130
# crash: the flash (first frame), the fireball at 0.5 s, the smoke column at 3 s and 10 s,
# each from the player's view (the sensor for the Hellfire, the wreck camera for a crash)
# and from a world camera about 1 km out. The DOM white-out is hidden so the sprites show.
# Test/screenshot infra only. Run: .venv/bin/python tests/item15_shots.py [--night]
import asyncio, os, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

NIGHT = '--night' in sys.argv
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone0929', 'item15' + ('_night' if NIGHT else ''))
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'
TIMES = [('flash', 0.0), ('0_5s', 0.5), ('3s', 3.0), ('10s', 10.0)]


async def step(pg, secs, dt=1 / 30):
    await pg.evaluate("([n,dt])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);}", [max(1, round(secs / dt)), dt])


async def climb(pg, ft=150, limit=150):
    await pg.evaluate(f"()=>{K}.auto()")
    for _ in range(limit):
        await step(pg, 1.0)
        if await pg.evaluate(f"()=>{K}.state().agl*3.28084") >= ft: return True
    return False


async def shot(pg, name):
    await pg.evaluate(f"()=>{{{K}.stepFrame(0);const t=document.getElementById('toast');if(t)t.classList.remove('on');"
                      f"const f=document.getElementById('bigFlash');if(f)f.style.visibility='hidden';}}")
    await pg.wait_for_timeout(250)
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    fx = await pg.evaluate(f"()=>{{const f={K}.fx();return [f.quads,f.drawCalls,Math.round(f.smokeTop)]}}")
    print(f'wrote {os.path.relpath(path)}  quads {fx[0]} draw calls {fx[1]} smoke top {fx[2]} m')


async def far_cam(pg, c, dist=1000, h=120):
    """A world camera dist m from the site, h m up, looking at the column base."""
    await pg.evaluate(f"([x,y,z,d,h])=>{{const K={K};K.freeCam({{w:true,p:[x+d*0.8,y+h,z+d*0.6],t:[x,y+40,z],fov:38}});K.stepFrame(0);}}", [c[0], c[1], c[2], dist, h])


async def sequence(pg, label, c, near_fn=None):
    """Shots at each time point, from the player's view then from ~1 km. c: [x,y,z] of the site."""
    t_prev = 0.0
    for name, t in TIMES:
        if t > t_prev: await step(pg, t - t_prev); t_prev = t
        if near_fn: await near_fn()
        await pg.evaluate(f"()=>{K}.freeCam(null)")
        await shot(pg, f'{label}_{name}_near.png')
        await far_cam(pg, c)
        await shot(pg, f'{label}_{name}_1km.png')
    await pg.evaluate(f"()=>{K}.freeCam(null)")


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('{'night' if NIGHT else 'day'}');{K}.setRadioOn&&{K}.setRadioOn(false);}}")
        await pg.wait_for_function(f"()=>{K}.warm()", timeout=90000)

        # ---- Hellfire on the bunker: the sensor view, then 1 km ----
        await pg.evaluate(f"()=>{K}.mission('range')")
        await pg.wait_for_timeout(600)
        await step(pg, 1.0)
        await pg.evaluate("()=>{const s=window.__kgeu.state();s.windBase=270;s.windKt=12;s.gustAmp=0;}")
        await pg.evaluate("""()=>{const K=window.__kgeu,i=K.STRIKE.targets.findIndex(t=>t.kind==='bunker'&&!t.dead);
          K.pointAt(i);K.stepFrame(1/30,false,true);K.trackHere();K.fire();}""")
        # fly the missile in 1/60 s steps so the very first frame after impact is caught
        hit = await pg.evaluate("""()=>{const K=window.__kgeu;let n=0;while(K.STRIKE.missiles.length&&n++<9000)K.stepFrame(1/60,false,true);
          const o=K.fx();return o.active?[K.STRIKE.targets.find(t=>t.kind==='bunker').x,K.groundHeight(K.STRIKE.targets.find(t=>t.kind==='bunker').x,K.STRIKE.targets.find(t=>t.kind==='bunker').z),K.STRIKE.targets.find(t=>t.kind==='bunker').z]:null}""")
        print('hellfire impact at', hit)
        if hit:
            await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=1;}}")
            await sequence(pg, 'hellfire', hit)

        # ---- crashes: the wreck camera, then 1 km ----
        for t in ('f16', 'c130'):
            await pg.evaluate(f"()=>{{{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('runway');}}")
            await step(pg, 0.2)
            print(t, 'climbed:', await climb(pg))
            await pg.evaluate(f"()=>{{{K}.crashNow('Item 15 shot.');{K}.stepFrame(1/60,false,true);}}")
            c = await pg.evaluate(f"()=>{{const s={K}.state();return [s.pos.x,{K}.groundHeight(s.pos.x,s.pos.z),s.pos.z]}}")
            await sequence(pg, t + '_crash', c)
            await pg.wait_for_timeout(500)
            await pg.evaluate("()=>document.getElementById('cMenu').click()")
            await step(pg, 0.1)
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        print('page errors:', pg.errs[:5])
        await b.close()
    srv.shutdown()

asyncio.run(main())
