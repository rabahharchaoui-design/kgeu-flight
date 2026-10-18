# Ramp start audit (item 8). For every (region, base, aircraft) combination below:
#   1. the ramp start position is paved, and every point on the taxiway-graph path from the
#      ramp to each runway end's nearest hold is paved (sampled every 5 m; needs the twg/
#      twgPath hooks -- split into 1a (ramp paved, works with today's code) and 1b (the full
#      path check, skipped with 'hook missing' until twg/twgPath land).
#   2. the start stand is clear: no AI aircraft within 40 m of the player at start.
#   3. pushback at an airline gate (737 @ phx, and 737 @ each world base): K.pushback()
#      returns true, and within 90 simulated seconds the aircraft moves back >= 20 m, its
#      heading changes >= 45 degrees, it stays on pavement, is not crashed, and PB.on ends
#      false. Needs the pushback()/PB hooks -- skipped with 'hook missing' until they land.
#   4. slow roll (6 m/s) toward the nearest unpaved point never crashes (works with today's
#      code: rolling off the pavement under 16 m/s does not trigger the 'ran off the pavement
#      at speed' crash in index.html ~line 3330). Looks for a stuck/rough-ground signal (a
#      state field, if one shows up, or a toast containing 'stuck'/'rough ground') and reports
#      whatever it finds -- there is no such signal yet.
#   5. the same at 40 m/s must NOT be exempt: today's code crashes any rollout off pavement
#      over 16 m/s, so this is expected to already fail safely (i.e. crash, which is a pass
#      for this check) with no new hooks.
#
# Hooks: window.__kgeu.twg(code), .twgPath(x0,z0,x1,z1), .pushback(), .PB are being added by
# the builders and are checked for presence (skipped with 'hook missing' when absent).
# Existing, used as-is: K.pick, K.pickBase, K.start('ramp'), K.state(), K.BASES, K.RWY_ENDS,
# K.isPaved, K.stepFrame. K.traffic() is named in the contract as existing, but as of this
# writing the game only exposes the AI list as K.tfcList() (see tests/traffic_ground_check.py)
# -- this test calls whichever of the two is present and reports a gap if neither is.
#
# Cases:
#   az (same scene, 3 bases): kgeu + cessna, luke + f16, phx + b737
#   world (--quick skips these): for each of rjtt, lfpg, sbrj, its one base with the cessna
#   and with the b737 (pushback only exercised for b737: "an airline gate")
#
# Usage: .venv/bin/python tests/ramp_check.py [--quick]
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

c = Checks()
STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}

AZ_CASES = [('az', 'kgeu', 'cessna', 'KGEU'), ('az', 'luke', 'f16', 'KLUF'), ('az', 'phx', 'b737', 'KPHX')]
WORLD_REGIONS = ['rjtt', 'lfpg', 'sbrj']

PHYS_DT = 0.25
PUSHBACK_SECONDS = 90
GRASS_SAFETY_STEPS = 2400   # 600 sim seconds, well past "10 s more" off pavement
GRASS_SETTLE_STEPS = 40     # 10 sim seconds at 0.25 dt

HOOKS_JS = """()=>({twg:typeof window.__kgeu.twg==='function', twgPath:typeof window.__kgeu.twgPath==='function',
  pushback:typeof window.__kgeu.pushback==='function', PB:('PB' in window.__kgeu),
  traffic:typeof window.__kgeu.traffic==='function', tfcList:typeof window.__kgeu.tfcList==='function'})"""

SETUP_JS = "([base,ac])=>{const K=window.__kgeu;K.pick(ac);K.pickBase(base);K.start('ramp');}"

RAMP_PAVED_JS = "()=>{const K=window.__kgeu,s=K.state();return {x:s.pos.x,z:s.pos.z,paved:K.isPaved(s.pos.x,s.pos.z)};}"

PATH_JS = """([code])=>{
  const K=window.__kgeu, s=K.state();
  const g=K.twg(code);
  if(!g) return {err:'twg('+code+') returned nothing'};
  // the stand itself must be a node of the graph (the owner's Haneda report was a pavement island: the old spot was
  // paved and a path from the NEAREST node would have passed): PR is the ramp start the game made
  if(K.PR&&(!K.PR.on||K.PR.n<0||Math.hypot(K.PR.x-s.pos.x,K.PR.z-s.pos.z)>5)) return {err:'ramp start is not a stand on the taxiway graph (PR '+JSON.stringify({on:K.PR.on,n:K.PR.n,dx:Math.round(K.PR.x-s.pos.x),dz:Math.round(K.PR.z-s.pos.z)})+')'};
  const ends=K.RWY_ENDS.filter(e=>e.rwy.code===code);
  const results=[];
  for(const e of ends){
    let best=null,bd=Infinity;
    for(const h of (g.holds||[])){const d=Math.hypot(h.x-e.x,h.z-e.z);if(d<bd){bd=d;best=h;}}
    if(!best){results.push({end:e.num,err:'no hold near this end'});continue;}
    const path=K.twgPath(s.pos.x,s.pos.z,best.x,best.z);
    if(!path){results.push({end:e.num,err:'twgPath returned null'});continue;}
    let bad=0,total=0;
    for(let i=0;i<path.length-1;i++){
      const x0=path[i][0],z0=path[i][1],x1=path[i+1][0],z1=path[i+1][1];
      const d=Math.hypot(x1-x0,z1-z0),n=Math.max(1,Math.round(d/5));
      for(let k=0;k<=n;k++){const t=k/n;total++;if(!K.isPaved(x0+(x1-x0)*t,z0+(z1-z0)*t))bad++;}
    }
    results.push({end:e.num,bad:bad,total:total,pts:path.length});
  }
  return {ends:results};
}"""

CLEAR_JS = """()=>{const K=window.__kgeu,s=K.state();
  const list=(typeof K.traffic==='function')?K.traffic():(typeof K.tfcList==='function'?K.tfcList():null);
  if(list==null) return {err:'no traffic hook (K.traffic/K.tfcList)'};
  const near=[];
  for(const o of list){const d=Math.hypot(o.x-s.pos.x,o.z-s.pos.z);if(d<40)near.push({id:o.id,type:o.type,d:Math.round(d)});}
  return {near:near,n:list.length};
}"""

PUSHBACK_JS = """([seconds,dt])=>{
  const K=window.__kgeu, s=K.state();
  const x0=s.pos.x,z0=s.pos.z;
  const e0=new THREE.Euler().setFromQuaternion(s.quat,'YXZ'), h0=e0.y;
  const ok=K.pushback();
  if(!ok) return {started:false};
  const nSteps=Math.round(seconds/dt);
  let moved=0,turn=0,crashed=false,i=0;
  for(;i<nSteps;i++){
    K.stepFrame(dt,false,true);
    if(s.crashed){crashed=true;break;}
    const d=Math.hypot(s.pos.x-x0,s.pos.z-z0);if(d>moved)moved=d;
    const e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');
    let dh=Math.abs(((e.y-h0+Math.PI)%(2*Math.PI))-Math.PI)*180/Math.PI;if(dh>turn)turn=dh;
    if(!(K.PB&&K.PB.on))break;
  }
  return {started:true,steps:i,moved:moved,turn:turn,crashed:crashed,
    pavedAtEnd:K.isPaved(s.pos.x,s.pos.z),pbOnAtEnd:!!(K.PB&&K.PB.on)};
}"""

GRASS_JS = """([speed,safetySteps,settleSteps,dt])=>{
  const K=window.__kgeu, s=K.state();
  const x0=s.pos.x,z0=s.pos.z;
  let target=null;
  for(let r=50;r<=400&&!target;r+=25){
    for(let a=0;a<8&&!target;a++){
      const ang=a*Math.PI/4,x=x0+Math.cos(ang)*r,z=z0+Math.sin(ang)*r;
      if(!K.isPaved(x,z))target={x:x,z:z};
    }
  }
  if(!target) return {err:'no unpaved point found within 400 m'};
  const dx=target.x-x0,dz=target.z-z0,L=Math.hypot(dx,dz)||1;
  s.vel.set(dx/L*speed,0,dz/L*speed);
  s.onGround=true;s.throttle=s.power=0;
  let offStep=null,steps=0;
  for(;steps<safetySteps;steps++){
    K.stepFrame(dt,false,true);
    if(s.crashed)break;
    if(offStep===null&&!K.isPaved(s.pos.x,s.pos.z))offStep=steps;
    if(offStep!==null&&steps-offStep>=settleSteps)break;
  }
  const body=document.body.textContent||'';
  const stuckText=/stuck|rough ground/i.test(body);
  const stuckField=(s.stuck!==undefined)?!!s.stuck:null;
  return {crashed:s.crashed,reason:s.crashReason,speed:Math.hypot(s.vel.x,s.vel.z),
    offStep:offStep,steps:steps,stuckText:stuckText,stuckField:stuckField,target:target};
}"""

ROWS = []   # (region, base, aircraft, check -> 'ok'|'FAIL'|'skip')


async def run_case(pg, region, base, aircraft, code, quick_pushback):
    row = {'region': region, 'base': base, 'ac': aircraft}
    hooks = await pg.evaluate(HOOKS_JS)

    # setup + check 1a (ramp paved)
    await pg.evaluate(SETUP_JS, [base, aircraft])
    await pg.wait_for_timeout(50)
    r1 = await pg.evaluate(RAMP_PAVED_JS)
    ok1a = c(f'{region}/{base}/{aircraft}: ramp start is paved', r1['paved'], r1)
    row['rampPaved'] = 'ok' if ok1a else 'FAIL'

    # check 1b (path to every runway end, needs twg + twgPath)
    if hooks['twg'] and hooks['twgPath']:
        r1b = await pg.evaluate(PATH_JS, [code])
        if 'err' in r1b:
            c(f'{region}/{base}/{aircraft}: taxi path to every runway end is paved', False, r1b['err'])
            row['path'] = 'FAIL'
        else:
            bad_ends = [e for e in r1b['ends'] if e.get('err') or e.get('bad')]
            ok = not bad_ends
            c(f'{region}/{base}/{aircraft}: taxi path to every runway end is paved', ok, bad_ends if bad_ends else None)
            row['path'] = 'ok' if ok else 'FAIL'
    else:
        print(f'  skip  {region}/{base}/{aircraft}: taxi path check (hook missing: twg/twgPath)')
        row['path'] = 'skip'

    # check 2 (clear stand)
    r2 = await pg.evaluate(CLEAR_JS)
    if 'err' in r2:
        c(f'{region}/{base}/{aircraft}: start stand clear of AI traffic', False, r2['err'])
        row['clear'] = 'FAIL(gap)'
    else:
        ok2 = not r2['near']
        c(f'{region}/{base}/{aircraft}: start stand clear of AI traffic (<40m)', ok2, r2['near'] if r2['near'] else None)
        row['clear'] = 'ok' if ok2 else 'FAIL'

    # check 3 (pushback) -- only for the 737 at an airline gate
    if quick_pushback and aircraft == 'b737':
        if hooks['pushback'] and hooks['PB']:
            await pg.evaluate(SETUP_JS, [base, aircraft])
            await pg.wait_for_timeout(50)
            r3 = await pg.evaluate(PUSHBACK_JS, [PUSHBACK_SECONDS, PHYS_DT])
            if not r3.get('started'):
                c(f'{region}/{base}/{aircraft}: pushback starts', False, r3)
                row['pushback'] = 'FAIL'
            else:
                ok3 = (r3['moved'] >= 20 and r3['turn'] >= 45 and r3['pavedAtEnd']
                       and not r3['crashed'] and not r3['pbOnAtEnd'])
                c(f'{region}/{base}/{aircraft}: pushback moves back >=20m, turns >=45deg, stays paved, PB.on ends false',
                  ok3, r3)
                row['pushback'] = 'ok' if ok3 else 'FAIL'
        else:
            print(f'  skip  {region}/{base}/{aircraft}: pushback check (hook missing: pushback/PB)')
            row['pushback'] = 'skip'
    else:
        row['pushback'] = 'n/a'

    # check 4: slow roll (6 m/s) onto grass never crashes
    await pg.evaluate(SETUP_JS, [base, aircraft])
    await pg.wait_for_timeout(50)
    r4 = await pg.evaluate(GRASS_JS, [6, GRASS_SAFETY_STEPS, GRASS_SETTLE_STEPS, PHYS_DT])
    if 'err' in r4:
        c(f'{region}/{base}/{aircraft}: slow (6 m/s) roll onto grass -- test setup', False, r4['err'])
        row['slow'] = 'FAIL(setup)'
    else:
        ok4 = not r4['crashed'] and (r4['speed'] < 2 or r4['stuckText'] or r4['stuckField'])
        c(f'{region}/{base}/{aircraft}: slow (6 m/s) roll onto grass never crashes', ok4, r4)
        row['slow'] = 'ok' if ok4 else 'FAIL'

    # check 5: fast roll (40 m/s) onto grass must NOT be exempt (crash or a damage flag)
    await pg.evaluate(SETUP_JS, [base, aircraft])
    await pg.wait_for_timeout(50)
    r5 = await pg.evaluate(GRASS_JS, [40, GRASS_SAFETY_STEPS, GRASS_SETTLE_STEPS, PHYS_DT])
    if 'err' in r5:
        c(f'{region}/{base}/{aircraft}: fast (40 m/s) roll onto grass -- test setup', False, r5['err'])
        row['fast'] = 'FAIL(setup)'
    else:
        dmg_field = (r5.get('stuckField') is True)
        ok5 = r5['crashed'] or dmg_field
        c(f'{region}/{base}/{aircraft}: fast (40 m/s) roll onto grass is NOT exempt (crash or damage flag)',
          ok5, {'crashed': r5['crashed'], 'reason': r5.get('reason'), 'dmg_field': dmg_field})
        row['fast'] = 'ok (crashed)' if r5['crashed'] else ('ok (damage flag)' if dmg_field else 'FAIL')

    ROWS.append(row)
    if not hooks['traffic'] and hooks['tfcList']:
        print(f'  note  {region}/{base}/{aircraft}: K.traffic() missing, used K.tfcList() instead (contract gap)')
    return hooks


async def run_region(region, cases, quick_pushback):
    srv, url = serve()
    is_az = region == 'az'
    storage = dict(STORAGE)
    if not is_az:
        storage['kgeuRegion'] = region
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=storage)
        if not is_az:
            await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=60000)
            await pg.wait_for_timeout(1000)
        hooks = None
        for base, aircraft, code in cases:
            hooks = await run_case(pg, region, base, aircraft, code, quick_pushback)
        c(f'{region}: no console errors', not pg.errs, pg.errs[:5])
        await b.close()
    srv.shutdown()
    return hooks


def parse_args(argv):
    return '--quick' in argv


async def main():
    quick = parse_args(sys.argv[1:])
    print('ramp_check: ' + ('--quick (az only)' if quick else 'az + world regions'))

    print('\n== az ==')
    hooks = await run_region('az', [(b, ac, code) for (_, b, ac, code) in AZ_CASES], quick_pushback=True)

    if not quick:
        for region in WORLD_REGIONS:
            print(f'\n== {region} ==')
            code = region.upper()
            # no airliner is based at Santos Dumont (the long runway rule, TYPES.minRwy 2,400 m against its 1,323 m:
            # picking one there reloads the game into another region), so its second case is the C-130 at a cargo stand
            cases = [(region, 'cessna', code), (region, 'c130' if region == 'sbrj' else 'b737', code)]
            await run_region(region, cases, quick_pushback=True)

    print('\n%-6s %-6s %-8s %10s %6s %8s %6s %6s' % ('region', 'base', 'aircraft', 'rampPaved', 'path', 'clear', 'slow', 'fast'))
    for r in ROWS:
        print('%-6s %-6s %-8s %10s %6s %8s %6s %6s  pushback=%s' %
              (r['region'], r['base'], r['ac'], r['rampPaved'], r['path'], r['clear'], r['slow'], r['fast'], r['pushback']))

    if hooks is not None and not (hooks['twg'] and hooks['twgPath']):
        print('\ncontract gap: window.__kgeu.twg/twgPath not present yet -- check 1 (taxi path) skipped')
    if hooks is not None and not (hooks['pushback'] and hooks['PB']):
        print('contract gap: window.__kgeu.pushback/PB not present yet -- check 3 (pushback) skipped')
    if hooks is not None and not hooks['traffic']:
        print('contract gap: window.__kgeu.traffic() not present; using window.__kgeu.tfcList() instead')

    sys.exit(c.done('ramp_check'))


asyncio.run(main())
