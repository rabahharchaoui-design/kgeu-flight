# Overwatch2 item 7: the visual review set. For each seed and time of day: the tasking started (TASK.test.noBrief),
# AUTO's takeoff, the aircraft put 2.2 km off the compound at 3,000 ft on the orbit, the ball slewed onto the white
# building and locked; DTV and IR WHT at WFOV, MFOV and NFOV, then the chase view. Runs on this build and, copied into
# its tests folder, on the preoverwatch2 worktree (hooks it lacks are skipped) so the before and after sets match.
#   .venv/bin/python -u tests/overwatch2_final_shots.py [--seeds 3,17,34] [--tods day,night] [--out <dir>]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
def arg(k, d): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
OUT = arg('--out', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'overwatch2', 'item7', 'after'))
SEEDS = [int(s) for s in arg('--seeds', '3,17,34').split(',')]
TODS = arg('--tods', 'day,night').split(',')
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
FOVS = [(0, 'WFOV'), (2, 'MFOV'), (4, 'NFOV')]
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False
async def frame(pg, n=1):
    for _ in range(n): await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")
SHOW = f"()=>{{const a={K}.task().ask;return !!(a&&a.shown)}}"

async def run(b, url, seed, tod, st):
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
    if await pg.evaluate(f"()=>typeof {K}.owSlots==='function'"):
        for _ in range(120):
            if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
            await pg.wait_for_timeout(500)
    await pg.evaluate(f"()=>{K}.setTOD('{tod}')"); await pg.wait_for_timeout(800)
    prog = await pg.evaluate(f"()=>typeof {K}.progN==='function'?{K}.progN():null")
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}})}}")
    for _ in range(40):
        if await pg.evaluate(f"()=>!!{K}.TASK.d"): break
        await pg.wait_for_timeout(250)
    if await until(pg, SHOW, 30): await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    await adv(pg, 10)
    await until(pg, f"()=>{{const K={K},s=K.state(),d=K.TASK.d,r=Math.hypot(s.pos.x-d.c.x,s.pos.z-d.c.z);return r>2100&&r<2700}}", 240, 2)
    await adv(pg, 6)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.bld;}}"); await adv(pg, 2)
    await pg.evaluate(f"()=>{K}.sensorLock()"); await adv(pg, 0.5)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=K.TASK.d.bld;K.SENSOR.track=null;}}"); await adv(pg, 0.5)
    print(f'  seed {seed} {tod}: ball on', await pg.evaluate(f"()=>{K}.SENSOR.tgt&&{K}.SENSOR.tgt.name"), ' progN before', prog)
    for mode in ('tv', 'irw'):
        for z, name in FOVS:
            await pg.evaluate(f"([m,z])=>{{const K={K};K.setSensorMode(m);K.SENSOR.zoom=z;}}", [mode, z])
            await adv(pg, 0.6)
            for _ in range(20):
                if not await pg.evaluate(f"()=>{{const S={K}.SENSOR;return !!S.masked||!S.tgt}}"): break
                await adv(pg, 1); await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;if(!S.masked&&!S.tgt){{S.tgt=K.TASK.d.bld;S.track=null;}}}}"); await adv(pg, 1)
            await frame(pg, 3)
            path = os.path.join(OUT, f'{seed}_{tod}_{"dtv" if mode == "tv" else "irwht"}_{name}.png')
            await pg.screenshot(path=path, timeout=120000)
            p = await pg.evaluate(f"()=>typeof {K}.progN==='function'?{K}.progN():null")
            print(f'  {os.path.basename(path)}  progN {p}')
            if prog: ok(f'seed {seed} {tod} {mode} {name}: no program linked in flight', p['compiles'] <= prog['compiles'], (prog, p))
    await finger(pg, '#bSensor'); await adv(pg, 0.5)
    for _ in range(4):
        if await pg.evaluate(f"()=>{K}.camMode()") == 0: break
        await finger(pg, '#bSensor'); await adv(pg, 0.5)
    await frame(pg, 3)
    path = os.path.join(OUT, f'{seed}_{tod}_chase.png'); await pg.screenshot(path=path, timeout=120000)
    print(f'  {os.path.basename(path)}')
    ok(f'seed {seed} {tod}: no page errors', not pg.errs, pg.errs[:3])
    await pg.close()

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': os.environ.get('PFS_TIER', 'medium')}
    async with async_playwright() as p:
        b = await launch(p)
        for seed in SEEDS:
            for tod in TODS:
                await run(b, url, seed, tod, st)
        await b.close()
    srv.shutdown()
    sys.exit(ok.done("overwatch2_final_shots"))
asyncio.run(main())
