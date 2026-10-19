# Overwatch2 item 2: the OVERWATCH compound through the MQ-9B's sensor. For each seed (3, 17, 34) and time of day (day,
# night): the time of day set in the menu, the tasking started (TASK.test.noBrief), AUTO's takeoff, then the aircraft
# put 2.2 km off the compound at 3,000 ft on AUTO's orbit, the ball view slewed onto the white building and locked; DTV
# and IR WHT at MFOV, MNFOV and NFOV, then the chase view. Shots: overnight-screenshots/overwatch2/item2/
# <seed>_<tod>_<mode>_<fov>.png. Prints per shot the compound's triangles (detail and simple set), its draw calls (its
# visible meshes and points), renderer.info.render and progN; checks progN never rises from before taskStart, the
# triangle and draw budgets (9,000 / 1,500, 10 draws) and no page errors.
# First 60 seeds rolled (budgets, the white building present and 18 m or more from the departing pickup).
# Usage: PFS_TIER=medium .venv/bin/python -u tests/overwatch2_compound_shots.py [--seeds 3,17,34] [--tods day,night] [--norolls]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'overwatch2', 'item2')
def arg(k, d): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SEEDS = [int(s) for s in arg('--seeds', '3,17,34').split(',')]
TODS = arg('--tods', 'day,night').split(',')
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False
SHOW = f"()=>{{const a={K}.task().ask;return !!(a&&a.shown)}}"
INFO = f"""()=>{{const K={K},g=K.TASK.d.cmp,U=g.userData,R3=K.R3(),ri=R3.renderer.info.render;let draws=0;
  g.traverse(o=>{{if((o.isMesh||o.isPoints)&&o.visible){{let p=o.parent,v=true;while(p){{if(!p.visible)v=false;p=p.parent;}}if(v)draws++;}}}});
  const cp=R3.camera.position,r=Math.hypot(cp.x-g.position.x,cp.y-g.position.y,cp.z-g.position.z);
  return {{tris:U.tris,lodTris:U.lodTris,full:U.full,draws:draws,calls:ri.calls,frameTris:ri.triangles,prog:K.progN(),cam:Math.round(r),nb:U.nb,W:U.W,D:U.D}}}}"""
FOVS = [(2, 'MFOV'), (3, 'MNFOV'), (4, 'NFOV')]
# how far the line of sight passes the white building's aim point (its roof centre), as LOCK measures it
CROSS = f"""()=>{{const K={K},S=K.SENSOR,L=S.los,p=S.spot,t=K.TASK.d.bld;if(!S.valid||!(L.y<-0.02))return 1e9;const k=(t.y+t.aimH-p.y)/L.y;
  return Math.hypot(t.x-(p.x+L.x*k),t.z-(p.z+L.z*k))}}"""

async def frame(pg, n=1):
    for _ in range(n): await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")

async def run(b, url, seed, tod, st):
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
    for _ in range(120):
        if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
        await pg.wait_for_timeout(500)
    await pg.evaluate(f"()=>{K}.setTOD('{tod}')"); await pg.wait_for_timeout(800)
    n0 = await pg.evaluate(f"()=>{K}.progN()")
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}})}}")
    n1 = await pg.evaluate(f"()=>{K}.progN()")
    await until(pg, SHOW, 30); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    # the orbit captures (it can swing out first): on it, 2.1 to 2.7 km out, the compound abeam inside the turn
    await adv(pg, 10)
    await until(pg, f"()=>{{const K={K},s=K.state(),d=K.TASK.d,r=Math.hypot(s.pos.x-d.c.x,s.pos.z-d.c.z);return r>2100&&r<2700}}", 240, 2)
    await adv(pg, 6)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.bld;}}"); await adv(pg, 2)
    await pg.evaluate(f"()=>{K}.sensorLock()"); await adv(pg, 0.5)
    lock = await pg.evaluate(f"()=>{K}.SENSOR.tgt&&{K}.SENSOR.tgt.name")
    if lock != 'the white building':   # LOCK takes the nearer target, measured at its height: at 12 degrees down the ground
        # spot lies 20 m past the building and a pickup there wins (item 1's lock logic); the shots hold the building
        print(f'  note: LOCK took {lock}; the ball held on the white building for the shots')
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=K.TASK.d.bld;K.SENSOR.track=null;}}"); await adv(pg, 0.5)
    ok(f'seed {seed} {tod}: the ball on the white building', await pg.evaluate(f"()=>{K}.SENSOR.tgt&&{K}.SENSOR.tgt.name") == 'the white building')
    print(f'  seed {seed} {tod}: progN before taskStart {n0}  after spawn {n1}')
    worst = n1
    for mode in (() if '--lockonly' in sys.argv else ('tv', 'irw')):
        for z, name in FOVS:
            await pg.evaluate(f"([m,z])=>{{const K={K};K.setSensorMode(m);K.SENSOR.zoom=z;}}", [mode, z])
            await adv(pg, 0.6)
            for _ in range(20):   # the airframe can mask the ball for a moment in the orbit: wait it out and re-lock
                m = await pg.evaluate(f"()=>{{const S={K}.SENSOR;return !!S.masked||!S.tgt}}")
                if not m: break
                await adv(pg, 1); await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;if(!S.masked&&!S.tgt){{S.tgt=K.TASK.d.bld;S.track=null;}}}}"); await adv(pg, 1)
            await frame(pg, 3)
            i = await pg.evaluate(INFO)
            path = os.path.join(OUT, f'{seed}_{tod}_{"dtv" if mode == "tv" else "irwht"}_{name}.png')
            await pg.screenshot(path=path, timeout=120000)
            print(f"  {os.path.basename(path)}  tris {i['tris']} (simple {i['lodTris']}) full {i['full']} draws {i['draws']}  frame calls {i['calls']} tris {i['frameTris']}  progN {i['prog']}  cam {i['cam']} m  {i['nb']} buildings {i['W']}x{i['D']}")
            worst = i['prog']
            ok(f'seed {seed} {tod} {mode} {name}: detail set within 3.5 km, under 9,000 triangles (simple set under 1,500), 10 draws at most',
               i['full'] and i['tris'] < 9000 and i['lodTris'] < 1500 and i['draws'] <= 10, i)
    # LOCK from three bearings 120 degrees apart round the orbit: the cross on the white building (its aim point, the roof's
    # centre, where the slew ends) must lock the building, never the pickup by the gate
    got = []
    for brg in (30, 150, 270):
        await pg.evaluate(f"""()=>{{const K={K},s=K.state(),d=K.TASK.d,a={brg}*Math.PI/180;
          s.pos.x=d.c.x+Math.sin(a)*2400;s.pos.z=d.c.z-Math.cos(a)*2400;}}""")
        await adv(pg, 2)
        for _ in range(8):
            # the cross put on it the way a finished slew leaves it: a geo stare on its aim point (the roof's centre)
            await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,t=K.TASK.d.bld;S.tgt=null;S.track=null;S.slewTo=null;S.geo=new THREE.Vector3(t.x,t.y+t.aimH,t.z);}}")
            await adv(pg, 1)
            if os.environ.get('OWDBG'): print('   cross', round(await pg.evaluate(CROSS), 1))
            if not await pg.evaluate(f"()=>!!{K}.SENSOR.masked") and await pg.evaluate(CROSS) < 3: break
            await adv(pg, 2)   # masked by the airframe, or past the gimbal while the orbit turns back: a moment later
        miss = await pg.evaluate(CROSS)
        await pg.evaluate(f"()=>{K}.sensorLock()"); await adv(pg, 0.2)
        r = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,s=K.state(),d=K.TASK.d;return [S.tgt&&S.tgt.name,Math.round((Math.atan2(s.pos.x-d.c.x,-(s.pos.z-d.c.z))*180/Math.PI+360)%360),Math.round(Math.hypot(d.bld.x-d.veh.x,d.bld.z-d.veh.z)),!!S.masked]}}")
        got.append(r + [round(miss, 1)])
    print(f'  seed {seed} {tod} LOCK from three bearings [lock, bearing from the compound, building to pickup m, masked, cross miss m]:', got)
    ok(f'seed {seed} {tod}: LOCK on the cross takes the white building from three bearings', all(g[0] == 'the white building' for g in got), got)
    await finger(pg, '#bSensor'); await adv(pg, 0.5)
    for _ in range(4):
        if await pg.evaluate(f"()=>{K}.camMode()") == 0: break
        await finger(pg, '#bSensor'); await adv(pg, 0.5)
    await frame(pg, 3)
    i = await pg.evaluate(INFO)
    path = os.path.join(OUT, f'{seed}_{tod}_chase_wide.png'); await pg.screenshot(path=path, timeout=120000)
    print(f"  {os.path.basename(path)}  draws {i['draws']}  progN {i['prog']}  cam {i['cam']} m")
    n2 = i['prog']
    ok(f'seed {seed} {tod}: no shader program linked in flight (before taskStart, after spawn, ball view DTV and IR, chase)',
       n1['max'] <= n0['max'] and n2['max'] <= n0['max'] and n2['compiles'] <= n0['compiles'] and worst['compiles'] <= n0['compiles'], (n0, n1, worst, n2))
    ok(f'seed {seed} {tod}: no page errors', not pg.errs, pg.errs[:3])
    await pg.close()

ROLL = """(sd)=>{const K=window.__kgeu;K.taskStop();const t0=performance.now();K.TASK.test.noBrief=true;K.taskStart('overwatch',{seed:sd});const ms=performance.now()-t0,d=K.TASK.d,g=d.cmp,U=g.userData;
  let n=0;g.traverse(o=>{if((o.isMesh||o.isPoints)&&o!==U.lod&&(o!==U.lights||K.TOD().night)&&(o!==U.apron||U.k>0))n++;});
  return {sd:sd,tris:U.tris,lod:U.lodTris,draws:n,nb:U.nb,W:U.W,D:U.D,white:d.bld.name,bp:Math.round(Math.hypot(d.bld.x-d.veh.x,d.bld.z-d.veh.z)),ms:Math.round(ms),objs:K.TASK.objs.length}}"""

async def rolls(b, url, st):
    # 60 seeds: every compound inside the budgets, its white building there and clear of the departing pickup
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
    for _ in range(120):
        if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
        await pg.wait_for_timeout(500)
    R = [await pg.evaluate(ROLL, sd) for sd in range(1, 61)]
    await pg.evaluate(f"()=>{K}.taskStop()")
    print('  60 rolls: triangles', min(r['tris'] for r in R), 'to', max(r['tris'] for r in R), ' simple set to', max(r['lod'] for r in R),
          ' draws to', max(r['draws'] for r in R), ' buildings', sorted({r['nb'] for r in R}), ' white building to pickup', min(r['bp'] for r in R), 'm or more',
          ' taskStart worst', max(r['ms'] for r in R), 'ms')
    ok('60 seeds: under 9,000 triangles (simple set under 1,500), 10 draws at most by day, one to three buildings, three objects',
       all(r['tris'] < 9000 and r['lod'] < 1500 and r['draws'] <= 10 and 1 <= r['nb'] <= 3 and r['objs'] == 3 for r in R), [r for r in R if not (r['tris'] < 9000 and r['draws'] <= 10)][:3])
    ok('60 seeds: the white building is there, 18 m or more from the departing pickup (LOCK takes the nearer)', all(r['white'] == 'the white building' and r['bp'] >= 18 for r in R), [r for r in R if r['bp'] < 18][:3])
    ok('no page errors (rolls)', not pg.errs, pg.errs[:3])
    await pg.close()

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': os.environ.get('PFS_TIER', 'medium')}
    async with async_playwright() as p:
        b = await launch(p)
        if '--norolls' not in sys.argv: await rolls(b, url, st)
        for seed in SEEDS:
            for tod in TODS:
                await run(b, url, seed, tod, st)
        await b.close()
    srv.shutdown()
    return ok.done('overwatch2_compound_shots')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
