# One-off screenshot script for phone notes 0929, item 4 (crash scorch z-fighting).
# Confirms visually, at iPhone landscape (844x390, dsf 2, mobile, touch):
#   - the scorch after a runway crash, from chase distance
#   - the same scorch from about 1 km out
#   - the aircraft shadow on the ground while taxiing (must sit under the aircraft,
#     not float or clip)
# Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item04_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item04')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'


async def step(pg, secs, dt=1 / 30, render=False):
    await pg.evaluate("([n,dt,r])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);if(r)K.stepFrame(1/60);}",
                       [max(1, round(secs / dt)), dt, render])


async def to_chase(pg):
    if await pg.evaluate(f"()=>{K}.camMode()") != 0:
        await pg.evaluate(f"()=>{{while({K}.camMode()!==0){K}.cycleCam();}}")


async def climb(pg, ft=150, limit=150):
    await pg.evaluate(f"()=>{K}.auto()")
    t = 0
    while t < limit:
        await step(pg, 1.0)
        t += 1
        if await pg.evaluate(f"()=>{K}.state().agl*3.28084") >= ft:
            return True
    return False


async def shot(pg, name):
    await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);const t=document.getElementById('toast');if(t)t.classList.remove('on');"
                       f"const f=document.getElementById('bigFlash');if(f)f.style.visibility='hidden';}}")
    await pg.wait_for_timeout(300)
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print('wrote', path)


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);}}")

        # ---- crash on the runway: chase, then ~1 km out ----
        await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('runway');}}")
        await step(pg, 0.2)
        got = await climb(pg, ft=150)
        print('climbed to 150 ft:', got)
        crashed = await pg.evaluate(f"()=>{K}.crashNow('Item 4 scorch shot.')")
        print('crashNow:', crashed)
        await step(pg, 4.0)
        sc = await pg.evaluate(f"()=>{{const s={K}.fxScorch();return s.length?{{x:s[0].position.x,z:s[0].position.z}}:null}}")
        print('scorch:', sc)

        await to_chase(pg)
        await step(pg, 0.1, render=True)
        await shot(pg, 'scorch_crash_chase.png')

        # camera about 1 km out, elevated, looking straight at the crash/scorch site.
        # freeCam offsets are in the aircraft's body frame, so convert the world
        # offset we actually want through the inverse of the aircraft's quaternion.
        await pg.evaluate(f"""()=>{{const K={K},s=K.state();
          const qi=s.quat.clone().invert();
          const camW=new THREE.Vector3(650,240,-950).applyQuaternion(qi);
          K.freeCam({{p:[camW.x,camW.y,camW.z],t:[0,0,0],fov:35}});}}""")
        await step(pg, 0.1, render=True)
        await shot(pg, 'scorch_crash_1km.png')
        await pg.evaluate(f"()=>{K}.freeCam(null)")

        # ---- aircraft shadow while taxiing (rolling on the ground, pre-liftoff) ----
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway');}}")
        await step(pg, 0.2)
        await to_chase(pg)
        await pg.evaluate(f"()=>{K}.auto()")
        await step(pg, 2.0)
        st = await pg.evaluate(f"()=>{{const s={K}.state();return {{onGround:s.onGround,agl:s.agl,gs:Math.hypot(s.vel.x,s.vel.z)}}}}")
        print('taxi state:', st)
        await step(pg, 0.1, render=True)
        await shot(pg, 'taxi_shadow.png')

        print('errs:', pg.errs[:5])
        await b.close()
    srv.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
