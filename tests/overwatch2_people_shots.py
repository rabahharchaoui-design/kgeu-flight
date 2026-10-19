# Overwatch2 item 3: the people at the OVERWATCH compound through the MQ-9B's sensor. For each seed (3, 34) and time of
# day (day, night): the tasking started (TASK.test.noBrief), AUTO's takeoff, the aircraft put 2.2 km off the compound at
# 3,000 ft on AUTO's orbit (as overwatch2_compound_shots), then the ball held on (a) the armed gate guard, (b) the patrol
# pair mid walk, (c) the talking pair, (d) the carrier, (e) the roof lookout, in DTV and IR WHT at NFOV, plus UNFOV EZ 2X
# on a rifleman at the low ready (the gate guard, else whichever is in view: DTV), and (f) the boarding at the pickup 4 s before it leaves. Shots:
# overnight-screenshots/overwatch2/item3/<seed>_<tod>_<mode>_<who>.png. Prints per shot the people's triangles (LOD0 and
# LOD1 sets), their draw calls, the skinning ms, progN and the figures' LODs; checks progN never rises from before
# taskStart and no page errors.
# Usage: PFS_TIER=medium .venv/bin/python -u tests/overwatch2_people_shots.py [--seeds 3,34] [--tods day,night]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'overwatch2', 'item3')
def arg(k, d): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SEEDS = [int(s) for s in arg('--seeds', '3,34').split(',')]
TODS = arg('--tods', 'day,night').split(',')
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False
async def frame(pg, n=1):
    for _ in range(n): await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")
SHOW = f"()=>{{const a={K}.task().ask;return !!(a&&a.shown)}}"
# the ball's geo stare on a figure (its chest), or the middle of a pair; re-aimed each call as they walk
AIM = f"""(w)=>{{const K={K},S=K.SENSOR,I=K.owPeople();if(!I)return null;let L=I.figs.filter(f=>!f.hid&&(w.role?f.role===w.role:true));
  const P=K.TASK.d.ppl,cp=K.R3().camera.position,g=P.g.position,ca=Math.cos(P.ang),sa=Math.sin(P.ang),dx=cp.x-g.x,dz=cp.z-g.z,cx=dx*ca-dz*sa,cz=dx*sa+dz*ca,cy=cp.y-g.y,hw=I.lay.hw,hd=I.lay.hd;
  // hidden behind a building or the wall from here (the ball's ground point only knows the terrain)
  const hid=f=>{{const ax=f.lx,az=f.lz,ay=f.y-g.y+(w.dy==null?0.9:w.dy),D=Math.hypot(cx-ax,cy-ay,cz-az);
    for(let t=0.6;t<Math.min(D,120);t+=0.25){{const px=ax+(cx-ax)*t/D,py=ay+(cy-ay)*t/D,pz=az+(cz-az)*t/D;
      if(I.lay.bl.some(b=>px>b[0]&&px<b[2]&&pz>b[1]&&pz<b[3]&&py<b[5]+0.9))return true;
      const gy=P.surf(px,pz);if(((Math.abs(Math.abs(px)-hw)<0.35&&Math.abs(pz)<hd+0.4)||(Math.abs(Math.abs(pz)-hd)<0.35&&Math.abs(px)<hw+0.4))&&py<gy+3.2)return true;}}return false;}};
  if(w.ready){{L=I.figs.filter(f=>!f.hid&&f.armed==='ready');const c=L.find(f=>!hid(f));L=[c||L[0]];}}
  if(w.board)L=I.figs.filter(f=>f.board);if(!L.length)return null;if(w.one)L=[L[w.idx||0]];
  const x=L.reduce((a,f)=>a+f.x,0)/L.length,z=L.reduce((a,f)=>a+f.z,0)/L.length,y=L.reduce((a,f)=>a+f.y,0)/L.length+(w.dy==null?0.9:w.dy);
  S.tgt=null;S.track=null;S.slewTo=null;S.geo=new THREE.Vector3(x,y,z);const sp=S.spot;let m=sp&&S.valid?Math.hypot(sp.x-x,sp.z-z):1e9;
  if(L.some(hid))m=1e9;
  return [L.map(f=>f.role+' '+f.state+' lod'+f.lod).join(', '),Math.round(x),Math.round(z),m]}}"""
INFO = f"""()=>{{const K={K},I=K.owPeople(),R3=K.R3(),ri=R3.renderer.info.render;return {{tris:I.tris,draws:I.draws,ms:I.ms,msAvg:I.msAvg,msMax:I.msMax,calls:ri.calls,prog:K.progN(),
  lods:I.figs.map(f=>f.lod),n:I.n,armed:I.figs.filter(f=>f.armed).length}}}}"""
WHO = [('talk', {'role': 'talk'}), ('guard', {'role': 'guard', 'one': 1}), ('patrol', {'role': 'patrol'}), ('carrier', {'role': 'carry', 'one': 1}), ('lookout', {'role': 'lookout', 'one': 1})]

async def shoot(pg, name, w, mode, zoom, worst):
    await pg.evaluate(f"([m,z])=>{{const K={K};K.setSensorMode(m);K.SENSOR.zoom=z;}}", [mode, zoom])
    r = await pg.evaluate(AIM, w); await adv(pg, 0.4)
    for _ in range(30):   # the airframe, a ridge, a building or the wall can hide them for a while in the orbit: wait until the ball's ground point is by them
        r = await pg.evaluate(AIM, w)
        if r and r[3] < 9 and not await pg.evaluate(f"()=>!!{K}.SENSOR.masked"): break
        await adv(pg, 1.5)
    r = await pg.evaluate(AIM, w); await frame(pg, 3); r = await pg.evaluate(AIM, w); await frame(pg, 2)
    i = await pg.evaluate(INFO)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f"  {os.path.basename(path)}  [{r and r[0]}]  people tris LOD0 {i['tris'][0]} LOD1 {i['tris'][1]} draws {i['draws']}  skin ms {i['ms']} (avg {i['msAvg']}, max {i['msMax']})  frame calls {i['calls']}  progN {i['prog']}  lods {i['lods']}")
    worst.append(i['prog'])
    return i

async def run(b, url, seed, tod, st):
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
    for _ in range(120):
        if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
        await pg.wait_for_timeout(500)
    await pg.evaluate(f"()=>{K}.setTOD('{tod}')"); await pg.wait_for_timeout(800)
    n0 = await pg.evaluate(f"()=>{K}.progN()")
    # the departure held while the figures are shot (waiting out ridges and the airframe takes a while), then rolled 20 s
    # ahead for the boarding (the real timing is overwatch_people_check's and tasking_overwatch_check's)
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}});{K}.TASK.d.dep=1e6;}}")
    n1 = await pg.evaluate(f"()=>{K}.progN()")
    await until(pg, SHOW, 30); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    await adv(pg, 10)
    await until(pg, f"()=>{{const K={K},s=K.state(),d=K.TASK.d,r=Math.hypot(s.pos.x-d.c.x,s.pos.z-d.c.z);return r>2100&&r<2700}}", 240, 2)
    await adv(pg, 6)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    i0 = await pg.evaluate(f"()=>{K}.owPeople()")
    print(f'  seed {seed} {tod}: {i0["n"]} people, {sum(1 for f in i0["figs"] if f["armed"])} armed: ' + ', '.join(f"{f['role']}{'*' if f['armed'] else ''}" for f in i0['figs']))
    worst = [n1]
    for who, w in WHO:
        for mode in ('tv', 'irw'):
            await shoot(pg, f'{seed}_{tod}_{"dtv" if mode == "tv" else "irwht"}_{who}.png', w, mode, 4, worst)
    await shoot(pg, f'{seed}_{tod}_dtv_guard_unfov2x.png', {'ready': 1, 'dy': 1.0}, 'tv', 6, worst)
    # the boarding: the watch stage (the ball on the white building), then 4 s before the wheels move
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.zoom=2;K.SENSOR.geo=null;K.SENSOR.tgt=K.TASK.d.bld;}}")
    if not await until(pg, f"()=>{K}.TASK.d.w0!=null", 20, 0.5): await pg.evaluate(f"()=>{K}.tqStage(2)")
    ok(f'seed {seed} {tod}: the watch stage began', await pg.evaluate(f"()=>{K}.TASK.d.w0!=null"))
    await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;d.dep=K.state().time-d.w0+20;d.ppl.tDep=null;}}")
    await until(pg, f"()=>{{const d={K}.TASK.d;return {K}.state().time>=d.w0+d.dep-4.3}}", 120, 0.1)
    for mode in ('tv', 'irw'):
        await shoot(pg, f'{seed}_{tod}_{"dtv" if mode == "tv" else "irwht"}_boarding.png', {'board': 1, 'dy': 0.6}, mode, 4, worst)
    b2 = await pg.evaluate(f"()=>{K}.owPeople().figs.filter(f=>f.board).map(f=>[f.board,f.state,f.hid])")
    print(f'  boarders at dep-4: {b2}')
    await until(pg, f"()=>{K}.TASK.d.veh.moving", 30, 0.1)
    b3 = await pg.evaluate(f"()=>{{const I={K}.owPeople();return [I.figs.filter(f=>f.board).map(f=>f.hid),I.gate]}}")
    ok(f'seed {seed} {tod}: the boarders hidden and the gate open when the pickup moves', all(b3[0]) and b3[1] is not None and b3[1] > 0.5, b3)
    n2 = await pg.evaluate(f"()=>{K}.progN()")
    ok(f'seed {seed} {tod}: no shader program linked in flight (before taskStart, after spawn, every shot)',
       all(w['max'] <= n0['max'] and w['compiles'] <= n0['compiles'] for w in worst + [n2]), (n0, worst[-1], n2))
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
    return ok.done('overwatch2_people_shots')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
