# Overwatch2 item 3: the people at the OVERWATCH compound. Seeds 3 (day) and 34 (night), a Hard run started straight
# into its flight (TASK.test.noBrief), the watch stage forced (tqStage) so the departure is rolled. Checks:
# 7 to 10 figures with the roles (two gate guards, a lookout, a two man patrol, a talking pair, a carrier), 3 to 5
# armed; LOD0 900 to 1,200 body triangles, LOD1 250 to 350, the rifle about 150; three draws (two LODs and the blobs);
# sampled every 0.5 s for 60 s: every planted foot on what it stands on within 0.1 m, nobody inside a wall or a
# building's footprint (the lookout on its roof), the rifle within 0.4 m of its hand (low ready) or the back (slung)
# with the muzzle 20 degrees or more below level; the patrol's loop at least 10 m outside the wall and clear; the planted
# foot's world speed under 0.15 m/s over each walk cycle; the skinning (every figure at LOD0) under 2.5 ms a frame; the
# departure: the boarders hidden, the gate open and the pickup moving at d.dep (its rolled time); the IR colours on in
# IR WHT; progN flat from before taskStart; no page errors.
# Run: timeout 540 .venv/bin/python -u tests/overwatch_people_check.py
import asyncio, os, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False
INFO = f"()=>{K}.owPeople()"

def inside_wall(f, lay):
    # the wall: a 0.35 m band on the rectangle (and its 0.62 m pilasters); a figure's centre within 0.3 m of it is in it
    hw, hd, x, z = lay['hw'], lay['hd'], f['lx'], f['lz']
    dx, dz = abs(abs(x) - hw), abs(abs(z) - hd)
    return (dx < 0.45 and abs(z) <= hd + 0.45) or (dz < 0.45 and abs(x) <= hw + 0.45)

def inside_bld(f, lay):
    if f['roof'] is not None: return False
    return any(b[0] - 0.05 < f['lx'] < b[2] + 0.05 and b[1] - 0.05 < f['lz'] < b[3] + 0.05 for b in lay['bl'])

async def run(b, url, seed, tod, st):
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
    for _ in range(120):
        if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
        await pg.wait_for_timeout(500)
    await pg.evaluate(f"()=>{K}.setTOD('{tod}')"); await pg.wait_for_timeout(800)
    n0 = await pg.evaluate(f"()=>{K}.progN()")
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}})}}")
    i = await pg.evaluate(INFO)
    roles = [f['role'] for f in i['figs']]; armed = [f for f in i['figs'] if f['armed']]
    print(f'  seed {seed} {tod}: {i["n"]} people: ' + ', '.join(f"{f['role']}{'(' + f['armed'] + ')' if f['armed'] else ''}{'(' + f['prop'] + ')' if f['prop'] else ''} {f['H']} m" for f in i['figs']))
    print(f'  triangles: LOD0 {i["tris"][0]} LOD1 {i["tris"][1]} (bodies {[f["body"][0] for f in i["figs"]]} / {[f["body"][1] for f in i["figs"]]}, rifle {max(f["rifTris"][0] for f in i["figs"])} / {max(f["rifTris"][1] for f in i["figs"])}), draws {i["draws"]}')
    ok(f'seed {seed}: 7 to 10 figures with two gate guards, the lookout, a two man patrol, the talking pair and the carrier; 3 to 5 armed',
       7 <= i['n'] <= 10 and roles.count('guard') == 1 and roles.count('guard2') == 1 and roles.count('lookout') == 1 and roles.count('patrol') == 2
       and roles.count('talk') == 2 and roles.count('carry') == 1 and 3 <= len(armed) <= 5 and sum(1 for f in i['figs'] if f['board']) == 3, (roles, len(armed)))
    ok(f'seed {seed}: LOD0 bodies 900 to 1,200 triangles, LOD1 250 to 350, the rifle about 150 (60 at LOD1); three draws (two at night: no blobs)',
       all(900 <= f['body'][0] <= 1200 and 250 <= f['body'][1] <= 350 for f in i['figs']) and all(140 <= f['rifTris'][0] <= 160 for f in armed) and i['draws'] == (2 if tod == 'night' else 3),
       [(f['role'], f['body']) for f in i['figs']])
    ok(f'seed {seed}: figures are not sensor targets (TASK.tgts unchanged)', await pg.evaluate(f"()=>{K}.TASK.tgts.map(t=>t.name).join()") == 'the white building,the white pickup')
    ok(f'seed {seed}: the patrol loop at least 10 m outside the wall, clear of every obstacle',
       all(max(abs(p[0]) - i['lay']['hw'], abs(p[1]) - i['lay']['hd']) >= 10 for p in i['loop'])
       and await pg.evaluate(f"()=>{{const P={K}.TASK.d.ppl,N=P.N,L=P.pat.path.pts;for(let k=0;k+1<L.length;k++){{const a=L[k],b=L[k+1],n=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/0.2);for(let j=0;j<=n;j++){{const x=a[0]+(b[0]-a[0])*j/n,z=a[1]+(b[1]-a[1])*j/n,c=Math.floor((x-N.x0)/N.c)+Math.floor((z-N.z0)/N.c)*N.nx;if(N.bk[c])return false;}}}}return true}}"),
       min(max(abs(p[0]) - i['lay']['hw'], abs(p[1]) - i['lay']['hd']) for p in i['loop']))
    # the flight: AUTO's takeoff, then the watch forced; every figure at LOD0 for the timing, the sensor view on (DTV)
    # (IR switched on at Luke links a PointsMaterial variant on the build before this item too: the orbit, as the shots)
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    await adv(pg, 8)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.bld;}}"); await adv(pg, 1)
    for mode in ('irw', 'tv'):
        await pg.evaluate(f"()=>{K}.setSensorMode('{mode}')"); await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")
    await pg.evaluate(f"()=>{{{K}.owPeopleLod(0);{K}.tqStage(2);}}"); await adv(pg, 0.5)
    d = await pg.evaluate(f"()=>{{const d={K}.TASK.d;return {{w0:d.w0,dep:d.dep,tDep:{K}.owPeople().tDep,t:{K}.state().time}}}}")
    print(f'  the watch began at {d["w0"]:.1f} s, the pickup leaves {d["dep"]:.1f} s later')
    # IR WHT (before the departure: the pickup's dust puffs link a PointsMaterial variant in IR on the build before this item too)
    await pg.evaluate(f"()=>{K}.setSensorMode('irw')"); await adv(pg, 0.3); await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")
    gr = await pg.evaluate("()=>{const P=window.__kgeu.TASK.d.ppl,M=P.lod[0],f=P.figs.find(f=>!f.hid),o=f.r[0]*3,a=M.col.array;let mn=1,mx=0;for(let i=0;i<f.D.lod[0].v;i++){mn=Math.min(mn,a[o+i*3]);mx=Math.max(mx,a[o+i*3]);}return [+mn.toFixed(2),+mx.toFixed(2),M.m.userData.heat,M.m.userData.irVar]}")
    ok(f'seed {seed}: IR WHT draws the figures with their heat greys (rifle 0.3 to skin 0.85: greys {gr[0]} to {gr[1]})', (await pg.evaluate(INFO))['ir'] and 0.2 <= gr[0] and 0.78 <= gr[1] <= 0.86, gr)
    await pg.evaluate(f"()=>{K}.setSensorMode('tv')"); await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")
    bad = {'ground': [], 'wall': [], 'bld': [], 'rifle': []}; ms = []; fsmax = {}; states = set()
    for k in range(120):
        await adv(pg, 0.5)
        i = await pg.evaluate(INFO)
        ms.append(i['ms'])
        for f in i['figs']:
            if f['hid']: continue
            states.add(f['state'])
            if f['state'].startswith('board'): continue   # sitting into the cab: the feet leave the ground
            if not f['onGround']: bad['ground'].append((k, f['role'], f['feet'], f['planted']))
            if inside_wall(f, i['lay']): bad['wall'].append((k, f['role'], f['lx'], f['lz']))
            if inside_bld(f, i['lay']): bad['bld'].append((k, f['role'], f['lx'], f['lz']))
            if f['rifle'] and not (f['rifle']['pitch'] <= -20 and f['rifle']['d'] <= 0.4): bad['rifle'].append((k, f['role'], f['rifle']))
            if f['fsMax'] is not None: fsmax[f['id']] = (f['role'], f['fsMax'], f['fsN'])
        if await pg.evaluate(f"()=>{K}.TASK.d.veh.moving"): break
    print(f'  {k + 1} samples; states seen: {sorted(states)}')
    print(f'  planted foot speed, worst walk cycle per walker (m/s, cycles): {list(fsmax.values())}')
    msm = sorted(ms); print(f'  skinning ms (all at LOD0): median {msm[len(msm) // 2]}, worst {msm[-1]}')
    ok(f'seed {seed}: every planted foot on its ground within 0.1 m, every sample', not bad['ground'], bad['ground'][:4])
    ok(f'seed {seed}: nobody inside a wall or a building (the lookout on its roof)', not bad['wall'] and not bad['bld'], (bad['wall'][:3], bad['bld'][:3]))
    ok(f'seed {seed}: the rifle within 0.4 m of its hand or back, the muzzle 20 degrees or more below level, every sample', not bad['rifle'], bad['rifle'][:3])
    ok(f'seed {seed}: the planted foot moves under 0.15 m/s over every walk cycle (bones, after the IK)', fsmax and all(v[1] < 0.15 for v in fsmax.values()) and sum(v[2] for v in fsmax.values()) >= 10, fsmax)
    ok(f'seed {seed}: the skinning and animation of every figure at LOD0 under 2.5 ms a frame (median and 95th)', msm[len(msm) // 2] < 2.5 and msm[int(len(msm) * 0.95)] < 2.5, msm[-5:])
    ok(f'seed {seed}: walk, carry or box, patrol, ready, guard, talk and listen all seen',
       all(any(s.endswith('/' + w) for s in states) for w in ('walk', 'patrol', 'ready', 'guard', 'talk', 'listen')) and any(s.endswith('/carry') or s.endswith('/box') for s in states), sorted(states))
    # the departure
    await until(pg, f"()=>{K}.TASK.d.veh.moving", 90, 0.1)
    r = await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d,I=K.owPeople();return {{dt:d.depT-d.w0,dep:d.dep,b:I.figs.filter(f=>f.board).map(f=>[f.board,f.hid,f.boarded]),gate:I.gate,gateGo:I.gateGo,g2:I.figs.find(f=>f.role==='guard2')}}}}")
    print(f'  departure: wheels at {r["dt"]:.2f} s (rolled {r["dep"]:.2f}), boarders {r["b"]}, gate {r["gate"]}, gate guard at ({r["g2"]["lx"]}, {r["g2"]["lz"]}) {r["g2"]["state"]}')
    ok(f'seed {seed}: the pickup moves at its rolled time, the driver, passenger and armed man boarded and hidden, the gate open (its guard there)',
       abs(r['dt'] - r['dep']) < 0.25 and all(x[1] for x in r['b']) and sum(1 for x in r['b'] if x[2]) >= 2 and r['gate'] > 0.5 and r['gateGo'], r)
    await adv(pg, 3)
    n2 = await pg.evaluate(f"()=>{K}.progN()")
    ok(f'seed {seed} {tod}: no shader program linked in flight (DTV, IR, the people)', n2['max'] <= n0['max'] and n2['compiles'] <= n0['compiles'], (n0, n2))
    await pg.evaluate(f"()=>{{{K}.owPeopleLod(null);{K}.taskStop();}}"); await adv(pg, 0.2)
    left = await pg.evaluate("()=>{let n=0;window.__kgeu.R3().scene.traverse(o=>{if(o.name==='owPeople'||(o.name||'').startsWith('ow_people')||o.name==='ow_blobs')n++;});return n}")
    ok(f'seed {seed}: nothing left behind after taskStop', left == 0 and await pg.evaluate(f"()=>{K}.owPeople()") is None, left)
    ok(f'seed {seed}: no page errors', not pg.errs, pg.errs[:3])
    await pg.close()

async def main():
    srv, url = serve()
    st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': os.environ.get('PFS_TIER', 'medium')}
    async with async_playwright() as p:
        b = await launch(p)
        for seed, tod in ((3, 'day'), (34, 'night')):
            await run(b, url, seed, tod, st)
        await b.close()
    srv.shutdown()
    return ok.done('overwatch_people_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
