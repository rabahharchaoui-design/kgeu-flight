# Owner report from Rio Santos Dumont: AI airliners taxi straight across the grass, then sit
# holding short forever and never take off. This test leaves the player parked on the runway
# (throttle 0) in free flight and runs the AI traffic (TFC) alone for a simulated 10 minutes
# (--minutes N, default 10; --quick = 2 minutes), sampling every sim 2 s, in each region: az
# (Glendale, free flight base 'kgeu'), rjtt (Haneda), lfpg (de Gaulle), sbrj (Santos Dumont).
# Model for region storage/start: tests/night_check.py (storage dict) plus kgeuRegion and the
# WORLD.ready wait, both from tests/rio_check.py and tests/runway_grade_check.py.
#
# Per region, at each 2 s sample of window.__kgeu.tfcList():
#   (a) PAVEMENT: every aircraft with onGround true must have K.isPaved true at its point or one
#       of 4 points 2 m around it (first 10 violations reported with state and position).
#   (b) HOLD: no aircraft stays in a state whose name contains 'hold' or 'lineup' for more than
#       180 sim seconds in a row.
#   (c) RUNWAY: no two AI aircraft are ever inside the same runway rectangle (window.__kgeu.RUNWAYS)
#       at the same sample, and no AI aircraft ever enters the player's own runway rectangle
#       (the player sits on it the whole test, so any AI entry onto it is a violation).
#   (d) PROGRESS: at least one AI departure (onGround -> airborne, or a transition to 'takeoff' or
#       'climb') and at least one AI arrival (airborne -> onGround) over the run, at airports that
#       have a traffic plan (checked against window.__kgeu.TFC.plans; all four regions do).
#
# Usage: .venv/bin/python tests/traffic_ground_check.py [region ...] [--minutes N] [--quick]
# With no region given, runs az, rjtt, lfpg, sbrj. Prints a summary table and fails on any
# violation; exits 0 only when every check in every region passed.
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

c = Checks()
STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
ALL_REGIONS = ['az', 'rjtt', 'lfpg', 'sbrj']
ROWS = []   # (region, samples, acTypes, offPave, longestHold, rwyConflicts, playerRwyViolN, departures, arrivals)

SAMPLE_DT = 2.0
HOLD_THRESH = 180

RUN_JS = """([simSeconds, sampleDt, holdThresh])=>{
  const K=window.__kgeu, physDt=0.25;
  const nSamples=Math.round(simSeconds/sampleDt), stepsPerSample=Math.round(sampleDt/physDt);
  const RWY=K.RUNWAYS;
  const st=K.state();
  function rectOf(r){const e=r.ends[0];return {x:r.x,z:r.z,dx:e.dx,dz:e.dz,hl:r.len/2,hw:r.wid/2};}
  function inside(rc,x,z,m){m=m||0;const ddx=x-rc.x,ddz=z-rc.z,along=ddx*rc.dx+ddz*rc.dz,across=ddz*rc.dx-ddx*rc.dz;
    return Math.abs(along)<=rc.hl+m&&Math.abs(across)<=rc.hw+m;}
  const rects=RWY.map(rectOf);
  function findRwy(x,z){for(let i=0;i<rects.length;i++)if(inside(rects[i],x,z,3))return i;return -1;}
  const playerIdx=findRwy(st.pos.x,st.pos.z);
  const playerRwy=playerIdx>=0?{apt:RWY[playerIdx].apt,code:RWY[playerIdx].code,num:RWY[playerIdx].num}:null;

  const sampleCounts=[],seenTypes=new Set();
  const holdStart={},holdFlagged={},pavedViol=[],rwyConflicts=[],playerRwyViol=[];
  let longestHold=0,offPaveSamples=0,simTime=0;
  const lastState={},lastGround={};
  const departures=new Set(),arrivals=new Set();
  // the game clamps a stepped frame's dt (about 0.1 s), so a sample is taken every sampleDt of the GAME clock, not of
  // the requested physDt: simSeconds really are sim seconds (runways item 6)
  const t0=K.state().time;
  for(let s=0;s<nSamples;s++){
    const tEnd=t0+(s+1)*sampleDt;let guard=0;
    while(K.state().time<tEnd&&guard++<400)K.stepFrame(physDt,false,true);
    simTime=K.state().time-t0;
    const L=K.tfcList();
    sampleCounts.push(L.length);
    for(const o of L){
      seenTypes.add(o.type);
      if(o.onGround){
        const pts=[[o.x,o.z],[o.x+2,o.z],[o.x-2,o.z],[o.x,o.z+2],[o.x,o.z-2]];
        const paved=pts.some(p=>K.isPaved(p[0],p[1]));
        if(!paved){offPaveSamples++;if(pavedViol.length<10)pavedViol.push({id:o.id,type:o.type,state:o.state,x:Math.round(o.x),z:Math.round(o.z)});}
      }
      const isHold=/hold|lineup/i.test(o.state);
      if(isHold){
        if(holdStart[o.id]==null)holdStart[o.id]=simTime;
        const dur=simTime-holdStart[o.id];
        if(dur>longestHold)longestHold=dur;
        if(dur>holdThresh&&!holdFlagged[o.id])holdFlagged[o.id]={id:o.id,type:o.type,state:o.state,dur:Math.round(dur)};
      } else holdStart[o.id]=null;
      // a violation here means an AI aircraft landing or lining up on the player's own runway: on the
      // ground, or in a ground/final-approach state over the rectangle, not just flying over it at
      // pattern altitude on an upwind or crosswind leg
      const landingLike=/final|rollout|lineup|hold|takeoff|touchgo/i.test(o.state);
      if(playerIdx>=0&&(o.onGround||landingLike)&&inside(rects[playerIdx],o.x,o.z)&&playerRwyViol.length<10)
        playerRwyViol.push({id:o.id,type:o.type,state:o.state,onGround:o.onGround,t:Math.round(simTime)});
      const wasG=lastGround[o.id],wasS=lastState[o.id];
      if(wasS!=null&&wasS!==o.state&&(o.state==='takeoff'||o.state==='climb'))departures.add(o.id);
      if(wasG===true&&o.onGround===false)departures.add(o.id);
      if(wasG===false&&o.onGround===true)arrivals.add(o.id);
      lastGround[o.id]=o.onGround;lastState[o.id]=o.state;
    }
    for(let a=0;a<L.length;a++){
      if(!L[a].onGround)continue;
      for(let b=a+1;b<L.length;b++){
        if(!L[b].onGround)continue;
        for(let ri=0;ri<rects.length;ri++){
          if(inside(rects[ri],L[a].x,L[a].z)&&inside(rects[ri],L[b].x,L[b].z)&&rwyConflicts.length<10)
            rwyConflicts.push({a:L[a].id,b:L[b].id,rwy:RWY[ri].apt+' '+RWY[ri].num,t:Math.round(simTime)});
        }
      }
    }
  }
  return {samples:sampleCounts.length,maxAc:sampleCounts.length?Math.max(...sampleCounts):0,
    minAc:sampleCounts.length?Math.min(...sampleCounts):0,acTypes:Array.from(seenTypes),
    offPaveSamples:offPaveSamples,pavedViol:pavedViol,
    longestHold:Math.round(longestHold),holdFlagged:Object.values(holdFlagged),
    rwyConflicts:rwyConflicts,playerRwy:playerRwy,playerRwyViol:playerRwyViol,
    departures:departures.size,arrivals:arrivals.size};
}"""


async def run_region(region, sim_seconds):
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        storage = dict(STORAGE)
        is_az = region == 'az'
        if not is_az:
            storage['kgeuRegion'] = region
        pg = await page(b, url, vp=IPHONE_15, storage=storage)
        if not is_az:
            await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=60000)
            await pg.wait_for_timeout(1500)
        base = 'kgeu' if is_az else region
        await pg.evaluate("([b])=>{const K=window.__kgeu;K.pick('cessna');K.pickBase(b);K.start('runway');}", [base])
        await pg.wait_for_timeout(300)
        # make sure the player really is parked: zero throttle, zero speed, brakes on
        await pg.evaluate("()=>{const K=window.__kgeu,s=K.state();s.throttle=s.power=0;s.vel.set(0,0,0);s.brake=true;}")
        has_plan = await pg.evaluate("()=>window.__kgeu.TFC.plans.some(p=>p.type==='airliner')")
        r = await pg.evaluate(RUN_JS, [sim_seconds, SAMPLE_DT, HOLD_THRESH])
        c(f'{region}: no console errors', not pg.errs, pg.errs[:5])
        await b.close()
    srv.shutdown()

    pave_ok = c(f'{region}: every onGround aircraft stays on paved ground', r['offPaveSamples'] == 0,
                r['pavedViol'] if r['pavedViol'] else None)
    hold_ok = c(f'{region}: no aircraft holds/lines up for more than {HOLD_THRESH} sim seconds straight',
                not r['holdFlagged'], r['holdFlagged'])
    rwy_ok = c(f'{region}: no two AI aircraft share a runway rectangle', not r['rwyConflicts'], r['rwyConflicts'])
    player_ok = c(f"{region}: no AI aircraft enters the player's runway ({r['playerRwy']})",
                   not r['playerRwyViol'], r['playerRwyViol'][:10])
    if has_plan:
        prog_ok = c(f'{region}: at least one AI departure and one arrival over the run',
                     r['departures'] >= 1 and r['arrivals'] >= 1, (r['departures'], r['arrivals']))
    else:
        print(f'  [{region}] no airliner traffic plan: skipping the departure/arrival check')
        prog_ok = True

    ROWS.append((region, r['samples'], ','.join(sorted(r['acTypes'])), r['offPaveSamples'], r['longestHold'],
                 len(r['rwyConflicts']), len(r['playerRwyViol']), r['departures'], r['arrivals'],
                 pave_ok and hold_ok and rwy_ok and player_ok and prog_ok))


def parse_args(argv):
    minutes = 2 if '--quick' in argv else 10
    regions = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--minutes':
            minutes = float(argv[i + 1]); i += 2; continue
        if a == '--quick':
            i += 1; continue
        regions.append(a); i += 1
    return regions or ALL_REGIONS, minutes


async def main():
    regions, minutes = parse_args(sys.argv[1:])
    sim_seconds = minutes * 60
    print(f'traffic_ground_check: {minutes} sim minutes per region, sampling every {SAMPLE_DT} s')
    for region in regions:
        print(f'\n== {region} ==')
        await run_region(region, sim_seconds)

    print('\n%-6s %8s %-24s %9s %12s %6s %7s %5s %5s' %
          ('region', 'samples', 'aircraft', 'offPave', 'longestHold', 'rwy', 'plrRwy', 'dep', 'arr'))
    for region, samples, types, offpave, longest, rwy, plr, dep, arr, ok in ROWS:
        flag = '' if ok else '  <-- FAIL'
        print('%-6s %8d %-24s %9d %12d %6d %7d %5d %5d%s' %
              (region, samples, types, offpave, longest, rwy, plr, dep, arr, flag))
    sys.exit(c.done('traffic_ground_check'))


asyncio.run(main())
