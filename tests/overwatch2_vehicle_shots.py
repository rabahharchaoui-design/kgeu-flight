# Overwatch2 item 4a: the OVERWATCH vehicles through the MQ-9B's sensor. For each seed (3, 34) and time of day (day,
# night): the tasking started (TASK.test.noBrief), AUTO's takeoff, the aircraft put 2.2 km off the compound at 3,000 ft
# on AUTO's orbit (as the compound and people shots), then the ball held on (a) the parked set (the target by the gate
# and its decoys) at NFOV and (b) on the target at UNFOV EZ 2X, in DTV and IR WHT; then the departure brought forward
# and, 25 s into its drive, (c) the moving target with its dust at NFOV and UNFOV EZ 2X, DTV and IR WHT (a point track).
# Shots: overnight-screenshots/overwatch2/item4/<seed>_<tod>_<mode>_<what>.png. Prints per shot the vehicles' levels
# and triangles, the frame's draw calls, the fleet's ms and progN; checks progN never rises from before taskStart and
# no page errors.
# Usage: PFS_TIER=medium .venv/bin/python -u tests/overwatch2_vehicle_shots.py [--seeds 3,34] [--tods day,night]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'overwatch2', 'item4')
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
# the ball's geo stare on the middle of the parked set (w.set) or a point track on the target (w.trk); [what, miss m]
AIM = f"""(w)=>{{const K={K},S=K.SENSOR,d=K.TASK.d,L=d.fleet.list,I=K.owPeople(),P=d.ppl,cp=K.R3().camera.position,ca=Math.cos(d.ang),sa=Math.sin(d.ang);
  // hidden behind a building or the wall from here (the ball's ground point only knows the terrain)
  const hid=v=>{{if(!I||!P)return false;const g=P.g.position,dx=cp.x-g.x,dz=cp.z-g.z,cx=dx*ca-dz*sa,cz=dx*sa+dz*ca,cy=cp.y-g.y,X=v.x-g.x,Z=v.z-g.z,ax=X*ca-Z*sa,az=X*sa+Z*ca,ay=v.y-g.y+0.9,D=Math.hypot(cx-ax,cy-ay,cz-az),hw=I.lay.hw,hd=I.lay.hd;
    for(let t=1.5;t<Math.min(D,150);t+=0.25){{const px=ax+(cx-ax)*t/D,py=ay+(cy-ay)*t/D,pz=az+(cz-az)*t/D;
      if(I.lay.bl.some(b=>px>b[0]&&px<b[2]&&pz>b[1]&&pz<b[3]&&py<b[5]+0.9))return true;
      const gy=P.surf(px,pz);if(((Math.abs(Math.abs(px)-hw)<0.35&&Math.abs(pz)<hd+0.4)||(Math.abs(Math.abs(pz)-hd)<0.35&&Math.abs(px)<hw+0.4))&&py<gy+3.2)return true;}}return false;}};
  if(w.trk){{S.geo=null;S.track=null;S.slewTo=null;S.tgt=d.veh;const sp=S.spot;return ['track '+d.veh.name,sp&&S.valid?Math.round(Math.hypot(sp.x-d.veh.x,sp.z-d.veh.z)):1e9];}}
  const V=w.one?[d.veh]:L.filter(v=>!v.moving),x=V.reduce((a,v)=>a+v.x,0)/V.length,z=V.reduce((a,v)=>a+v.z,0)/V.length,y=V.reduce((a,v)=>a+v.y,0)/V.length+0.8;
  S.tgt=null;S.track=null;S.slewTo=null;S.geo=new THREE.Vector3(x,y,z);const sp=S.spot,nh=V.filter(hid).length;
  return [V.map(v=>v.name).join(', ')+(nh?' ('+nh+' hidden)':''),sp&&S.valid&&!nh?Math.round(Math.hypot(sp.x-x,sp.z-z)):1e9];}}"""
INFO = f"""()=>{{const K={K},I=K.owVeh(),ri=K.R3().renderer.info.render;return {{lods:I.list.map(v=>v.lod),tris:I.list.map(v=>v.tris[v.lod]),ms:I.ms,msMax:I.msMax,calls:ri.calls,prog:K.progN(),
  spd:I.list.map(v=>v.spd),dust:I.list.map(v=>v.dust)}}}}"""

async def shoot(pg, name, w, mode, zoom, worst):
    await pg.evaluate(f"([m,z])=>{{const K={K};K.setSensorMode(m);K.SENSOR.zoom=z;}}", [mode, zoom])
    r = await pg.evaluate(AIM, w); await adv(pg, 0.4)
    for _ in range(40):   # the airframe, a ridge or a building can hide them for a while in the orbit
        r = await pg.evaluate(AIM, w)
        if r and r[1] < 12 and not await pg.evaluate(f"()=>!!{K}.SENSOR.masked"): break
        await adv(pg, 1.5)
    r = await pg.evaluate(AIM, w); await frame(pg, 3); await frame(pg, 2)
    i = await pg.evaluate(INFO)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f"  {os.path.basename(path)}  [{r and r[0]}, miss {r and r[1]} m]  levels {i['lods']} tris {i['tris']}  frame calls {i['calls']}  fleet ms {i['ms']} (max {i['msMax']})  progN {i['prog']}  speeds {i['spd']}")
    worst.append(i['prog'])
    return i

async def run(b, url, seed, tod, st):
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
    for _ in range(120):
        if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
        await pg.wait_for_timeout(500)
    await pg.evaluate(f"()=>{K}.setTOD('{tod}')"); await pg.wait_for_timeout(800)
    n0 = await pg.evaluate(f"()=>{K}.progN()")
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}});const d={K}.TASK.d;d.dep=1e6;if(d.dcy)d.dcy.t=1e6;}}")
    n1 = await pg.evaluate(f"()=>{K}.progN()")
    await until(pg, SHOW, 30); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    await adv(pg, 10)
    await until(pg, f"()=>{{const K={K},s=K.state(),d=K.TASK.d,r=Math.hypot(s.pos.x-d.c.x,s.pos.z-d.c.z);return r>2100&&r<2700}}", 240, 2)
    await adv(pg, 6)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    names = await pg.evaluate(f"()=>{K}.owVeh().list.map(v=>v.name+(v.decoy?' (decoy)':' (target)'))")
    print(f'  seed {seed} {tod}: ' + ', '.join(names))
    worst = [n1]
    for mode in ('tv', 'irw'):
        md = 'dtv' if mode == 'tv' else 'irwht'
        await shoot(pg, f'{seed}_{tod}_{md}_parked_nfov.png', {'set': 1}, mode, 4, worst)
        await shoot(pg, f'{seed}_{tod}_{md}_target_unfov2x.png', {'one': 1}, mode, 6, worst)
    # the departure: the watch stage, the wheels move 2 s on; 25 s into the drive (the dust trail behind it)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.zoom=2;K.SENSOR.geo=null;K.SENSOR.tgt=K.TASK.d.bld;}}")
    if not await until(pg, f"()=>{K}.TASK.d.w0!=null", 20, 0.5): await pg.evaluate(f"()=>{K}.tqStage(2)")
    await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;d.dep=K.state().time-d.w0+2;if(d.ppl)d.ppl.tDep=null;}}")
    await until(pg, f"()=>{K}.TASK.d.veh.moving", 30, 0.1)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.geo=null;K.SENSOR.tgt=K.TASK.d.veh;}}")
    await adv(pg, 25)
    for mode in ('tv', 'irw'):
        md = 'dtv' if mode == 'tv' else 'irwht'
        await shoot(pg, f'{seed}_{tod}_{md}_moving_nfov.png', {'trk': 1}, mode, 4, worst)
        await shoot(pg, f'{seed}_{tod}_{md}_moving_unfov2x.png', {'trk': 1}, mode, 6, worst)
    n2 = await pg.evaluate(f"()=>{K}.progN()")
    ok(f'seed {seed} {tod}: no shader program linked in flight (before taskStart, after spawn, every shot, the departure)',
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
    return ok.done('overwatch2_vehicle_shots')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
