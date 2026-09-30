# One-off screenshot script for phone notes 0929, item 11 (trimSpawn hands-off finals).
# Confirms visually, at iPhone landscape (844x390, dsf 2, mobile, touch), chase view:
#   - C-130 in Hard on the 3 mile final at spawn (HUD altitude and VS visible)
#   - C-130 in Hard on the 3 mile final, 20 s later, hands off
#   - F-16 in Hard on the 1 mile final
# Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item11_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item11')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'


async def to_chase(pg):
    if await pg.evaluate(f"()=>{K}.camMode()") != 0:
        await pg.evaluate(f"()=>{{while({K}.camMode()!==0){{{K}.cycleCam();}}}}")


async def fly(pg, secs, dt=1 / 30):
    steps = max(1, round(secs / dt))
    await pg.evaluate("([n,dt])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);}", [steps, dt])


async def shot(pg, name):
    await pg.evaluate(f"()=>{{{K}.stepFrame(1/60,false,true);const t=document.getElementById('toast');if(t)t.classList.remove('on');}}")
    await pg.wait_for_timeout(300)
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print('wrote', path)


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.evaluate("()=>{window.WIND_FIX=[360,0]}")  # still air
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")  # Hard

        # ---- C-130, Hard, 3 mile final ----
        await pg.evaluate(f"()=>{{{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('final')}}")
        await to_chase(pg)
        st0 = await pg.evaluate(f"()=>{{const s={K}.state();return {{agl:s.agl*3.28084,vs:s.vel.y*196.85,ias:s.ias*1.943844,pitch:s.pitch}}}}")
        print('C-130 3mi at spawn:', st0)
        await shot(pg, 'c130_3mi_spawn_chase.png')

        await fly(pg, 20.0)
        st1 = await pg.evaluate(f"()=>{{const s={K}.state();return {{agl:s.agl*3.28084,vs:s.vel.y*196.85,ias:s.ias*1.943844,pitch:s.pitch}}}}")
        print('C-130 3mi +20s hands-off:', st1)
        await shot(pg, 'c130_3mi_plus20s_chase.png')

        # ---- F-16, Hard, 1 mile final ----
        await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('final1')}}")
        await fly(pg, 0.1)
        await to_chase(pg)
        stf = await pg.evaluate(f"()=>{{const s={K}.state();return {{agl:s.agl*3.28084,vs:s.vel.y*196.85,ias:s.ias*1.943844}}}}")
        print('F-16 1mi at spawn:', stf)
        await shot(pg, 'f16_1mi_spawn_chase.png')

        print('errs:', pg.errs[:5])
        await b.close()
    srv.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
