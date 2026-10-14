# Gfxfix 2: where the stalls are. Real rAF loop only (never stepFrame), iPhone landscape 844x390 at 2x, Arizona.
# After the warm-up (splash gone, precompile queue and menu WARM steps done) the shader program count is the baseline;
# each leg then flies one scene on the live loop and reports the programs compiled late (their cache keys), the
# stalls the logger saw (frames over max(250, 3 x the median frame) with their tags), the AGL range and how often
# the near and mid shadow cascades switched. Headless frames are ~300 ms, so stall times mean little here; what
# counts is new programs and the tags.
#   .venv/bin/python tests/stall_check.py [root] [--tier medium|high] [--out /tmp/gfxfix/stalls_<tier>.json] [--gate] [--legs a,b]
# Legs: a takeoff (F-16, KGEU runway, traffic), b whitetanks (4,500 ft at 380 kt over the White Tanks, west then
# south), c explosion (explode() 300 m ahead) and missile (the MQ-9A strike range, a real Hellfire), d sunset,
# e haboob (wall at 4 km, inside, cockpit), f dogfight (one FOX 2), g tier (what a user does: the pause sheet's Main
# menu, Settings > Graphics to the other tier, wait for the warm-up to run again, fly; back to this tier the same way,
# fly, a dynamic scale step; then the battery guard: 31 s of thermalFeed at the 0.7 floor in flight must change nothing
# but GFX.pendingTier, which the menu applies after the flight, one tier down), h pause (the pause sheet and resume,
# on the tier g left).
# Programs are counted by __kgeu.progN().compiles (gfxfix item 3: every program id ever linked, so a compile and a
# dispose in the same leg still count).
# The headless loop runs the sim at about 0.3x (dt is capped at 0.1 s a frame), so on legs b, d and e a page timer
# tops up the ground track to the real speed and holds the altitude: the terrain rings and the cascades see the
# camera move the way they would at 60 fps.
# --gate: exit 1 on any program compiled in flight in any leg (g's compiles while the menu is up are fine and printed
# apart), on a stall outside the menu tagged prog, csmBuild, pmrem or hbTier, or on a failed battery guard case.
# Page errors always exit 1.
import asyncio, json, os, re, sys, time
from collections import Counter
from playwright.async_api import async_playwright

args = sys.argv[1:]
def opt(name, dflt):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return dflt
TIER = opt('--tier', 'medium')
OUT = opt('--out', f'/tmp/gfxfix/stalls_{TIER}.json')
ONLY = opt('--legs', '')   # a comma list of leg names to run alone (iteration; the full run is the reference)
GATE = '--gate' in args
if GATE: args.remove('--gate')
ROOT = os.path.abspath(args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['PFS_TIER'] = TIER   # graphics_shots builds INIT from it at import (kgeuTier in localStorage)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graphics_shots import serve, launch, K, CAM0, UNMAP, INIT, fly, air, hbj, THREE   # noqa: E402
from harness import IGNORE   # noqa: E402

EXPLAINED = ('prog', 'tex', 'rt', 'pr', 'tier', 'csmBuild', 'pmrem', 'hbTier')
GATE_TAGS = ('prog', 'csmBuild', 'pmrem', 'hbTier')
GATED_LEGS = ('takeoff', 'whitetanks', 'explosion', 'sunset', 'haboob', 'dogfight', 'tier', 'pause')
PROG = f"()=>{K}.progN().compiles"

# page side: every 100 ms the AGL under the aircraft and under the camera and the cascade mask; with pace on, the
# ground track topped up to the real speed and the altitude held
SAMPLER = """()=>{const K=window.__kgeu;if(window.__aglT)clearInterval(window.__aglT);
  window.__aglLog=[];window.__pace=window.__pace||null;let lt=performance.now(),lp=null;
  window.__aglT=setInterval(()=>{const s=K.state(),c=K.camPos(),now=performance.now(),dt=(now-lt)/1000;lt=now;
    const P=window.__pace;
    if(P&&K.running()&&!K.paused()&&!s.crashed){const vx=s.vel.x,vz=s.vel.z,v=Math.hypot(vx,vz);
      if(lp&&v>1){const mv=Math.hypot(s.pos.x-lp[0],s.pos.z-lp[1]),need=v*dt-mv;
        if(need>0&&need<v){s.pos.x+=vx/v*need;s.pos.z+=vz/v*need;}}
      s.pos.y=P.y;s.vel.y=0;}
    lp=[s.pos.x,s.pos.z];
    window.__aglLog.push([s.pos.y-K.groundHeight(s.pos.x,s.pos.z),c[1]-K.groundHeight(c[0],c[2]),K.csm().act|0]);},100);}"""
AGL_READ = """()=>{const L=window.__aglLog||[];window.__aglLog=[];
  if(!L.length)return {n:0};let mn=1e9,mx=-1e9,cmn=1e9,cmx=-1e9,nf=0,mf=0;
  for(let i=0;i<L.length;i++){const a=L[i];mn=Math.min(mn,a[0]);mx=Math.max(mx,a[0]);cmn=Math.min(cmn,a[1]);cmx=Math.max(cmx,a[1]);
    if(i){const d=a[2]^L[i-1][2];if(d&1)nf++;if(d&2)mf++;}}
  return {n:L.length,min:Math.round(mn),max:Math.round(mx),cam_min:Math.round(cmn),cam_max:Math.round(cmx),near_flips:nf,mid_flips:mf}}"""
# who uses the new programs: the scene's objects whose material's current program has one of these cache keys
# (object name or its parent's, the material's type and name); a program no live object holds says 'gone'
OWNERS = f"""(keys)=>{{const R={K}.R3(),r=R.renderer,out={{}};const want=new Set(keys);
  R.scene.traverse(o=>{{const M=o.material?(Array.isArray(o.material)?o.material:[o.material]):[];
    for(const m of M){{const p=r.properties.get(m),pr=p&&p.currentProgram;if(!pr||!want.has(pr.cacheKey))continue;
      const k=pr.cacheKey,a=out[k]=out[k]||[];const nm=(o.name||(o.parent&&o.parent.name)||o.type)+' '+m.type+(m.name?' '+m.name:'');
      if(a.length<4&&a.indexOf(nm)<0)a.push(nm);}}}});
  return keys.map(k=>out[k]?out[k].join(' | '):'gone');}}"""
PACE_ON = f"()=>{{const s={K}.state();window.__pace={{y:s.pos.y}};}}"
PACE_OFF = "()=>{window.__pace=null;}"

async def js(pg, body):
    return await pg.evaluate("(js)=>(new Function(js))()", body)

async def tap(pg, sel):
    r = await pg.evaluate("(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}", sel)
    if r: await pg.touchscreen.tap(r[0], r[1])
    return bool(r)

def short(k): return k if len(k) <= 80 else k[:80]
def base_tag(t): return re.split(r'[+ ]', t, maxsplit=1)[0]

class Run:
    def __init__(self, pg):
        self.pg, self.legs, self.cons = pg, {}, []
        self.prog, self.keys = 0, []

    async def leg(self, name, body):
        pg = self.pg
        print(f'\n[{name}]', flush=True)
        await pg.evaluate(f"(n)=>{K}.stallMark(n)", name)
        await pg.evaluate(AGL_READ)
        self.cons = []
        t0 = time.time()
        note = {}
        try:
            note = await body(pg) or {}
        except Exception as e:
            note = {'error': str(e).splitlines()[0]}; pg.errs.append(f'{name}: {note["error"]}')
            print('  leg error:', note['error'])
        wall = time.time() - t0
        prog = await pg.evaluate(PROG)
        keys = await pg.evaluate(f"()=>{K}.progList()")
        new = [k for k in keys if k not in set(self.keys)]
        menu_c = note.pop('menu_compiles', 0) if isinstance(note, dict) else 0
        own = await pg.evaluate(OWNERS, new) if new else []
        st = await pg.evaluate(f"()=>{K}.stalls()")
        await pg.evaluate(f"()=>{K}.stallsClear()")
        agl = await pg.evaluate(AGL_READ)
        crashed = await pg.evaluate(f"()=>!!{K}.state().crashed")
        rec = {'wall_s': round(wall, 1), 'prog_before': self.prog, 'prog_after': prog, 'compiles': prog - self.prog, 'menu_compiles': menu_c,
               'flight_compiles': prog - self.prog - menu_c, 'new_keys': [short(k) for k in new], 'new_owners': own,
               'stalls': st['log'], 'stall_count': st['count'], 'console': list(self.cons),
               'agl': {'min': agl.get('min'), 'max': agl.get('max'), 'cam_min': agl.get('cam_min'), 'cam_max': agl.get('cam_max')},
               'near_flips': agl.get('near_flips', 0), 'mid_flips': agl.get('mid_flips', 0), 'crashed': crashed, 'note': note}
        self.legs[name] = rec
        self.prog, self.keys = prog, keys
        print(f'  {wall:.1f} s wall, compiles {rec["prog_before"]} -> {prog} ({rec["flight_compiles"]} in flight, {menu_c} in the menu; {len(new)} new keys), {st["count"]} stalls'
              + (', CRASHED' if crashed else '') + (f', {note}' if note else ''))
        for k, o in zip(new, own): print('    new:', short(k), '\n         used by:', o)
        for r in st['log']: print(f'    stall {r["gap"]} ms tick {r["tick"]} {r["scene"]} {r["tier"]} {r["scale"]} {" ".join(r["tags"])}')
        if agl.get('n'): print(f'  agl {agl["min"]}..{agl["max"]} m (camera {agl["cam_min"]}..{agl["cam_max"]}), near cascade flips {rec["near_flips"]}, mid {rec["mid_flips"]}')
        return rec

# ---------- the legs ----------
THR = {'med': 0, 'thr': 1000}
async def leg_takeoff(pg):
    await js(pg, fly('f16', 'day', 'runway') + f"{K}.TFC.auto=true;")
    await pg.evaluate(f"()=>{K}.fpsReset()")
    ms = []
    for _ in range(3):
        await pg.wait_for_timeout(1000); ms.append((await pg.evaluate(f"()=>{K}.fpsStats()")).get('ms') or 0)
    THR['med'] = sorted(ms)[1]; THR['thr'] = max(250, round(3 * THR['med']))
    await pg.evaluate(f"(t)=>{K}.stallsThr(t)", THR['thr'])
    print(f'  median flight frame {THR["med"]:.0f} ms (samples {ms}), stall threshold {THR["thr"]} ms', flush=True)
    # full power: the takeoff roll on the live loop
    await js(pg, f"{K}.setThr(1);")
    await pg.wait_for_timeout(27000)
    return await pg.evaluate(f"()=>({{traffic:{K}.TFC.list.length,ias_kt:Math.round({K}.state().ias*1.944),onGround:{K}.state().onGround}})")

# 5 km east of the White Tanks' east edge (centre x -23200, z -6900, half width 6500), 4,500 ft MSL, heading 270 at 380 kt
WT_X, WT_Z = -23200 + 6500 + 5000, -6900
async def leg_whitetanks(pg):
    await js(pg, air(WT_X, WT_Z, 4500, 270, 380))
    await pg.evaluate(PACE_ON)
    await pg.wait_for_timeout(1000); await pg.evaluate(AGL_READ)   # the samples from the runway before the jump do not count
    await pg.wait_for_timeout(39000)
    await pg.evaluate(f"()=>{K}.stallMark('whitetanks:180')")
    await js(pg, air('s.pos.x', 's.pos.z', 4500, 180, 380))
    await pg.evaluate(PACE_ON)
    await pg.wait_for_timeout(30000)
    await pg.evaluate(PACE_OFF)
    return await pg.evaluate(f"()=>{{const s={K}.state();return {{x:Math.round(s.pos.x),z:Math.round(s.pos.z)}}}}")

async def leg_explosion(pg):
    await js(pg, f"const K={K},s=K.state(),n=new THREE.Vector3(0,0,-1).applyQuaternion(s.quat).multiplyScalar(300).add(s.pos);"
                 "K.explode(n.x,n.y,n.z,{scale:1,air:true,smokeSec:5,debris:4,boomDelay:0});")
    await js(pg, air('s.pos.x', 's.pos.z', 4500, 90, 380))   # back east, away from the range's rock
    await pg.wait_for_timeout(15000)
    # the missile: the MQ-9A strike range (the only live hook that launches a real missile outside a dogfight)
    await pg.evaluate(f"()=>{K}.stallMark('missile')")
    await pg.evaluate(f"()=>{K}.mission('range')")
    await pg.wait_for_timeout(3000)
    await pg.evaluate(f"()=>{K}.pointAt({K}.STRIKE.targets.findIndex(t=>t.kind==='bunker'))")
    await pg.wait_for_timeout(1500)
    await pg.evaluate(f"()=>{K}.trackHere()")
    await pg.wait_for_timeout(1000)
    await pg.evaluate(f"()=>{K}.fire()")
    await pg.wait_for_timeout(15000)
    return await pg.evaluate(f"()=>({{shots:{K}.STRIKE.shots,inflight:{K}.STRIKE.missiles.length,valid:{K}.SENSOR.valid,hit:{K}.STRIKE.targets.filter(t=>t.dead).length}})")

async def leg_sunset(pg):
    await js(pg, fly('f16', 'day', 'runway'))
    await pg.wait_for_timeout(1500)
    await js(pg, air(-8000, 0, 3000, 270, 300))
    await pg.evaluate(PACE_ON)
    await pg.wait_for_timeout(1000)
    await pg.evaluate(f"()=>{{{K}.stallMark('sunset:tod');{K}.setTOD('sunset');}}")
    await pg.wait_for_timeout(22500)
    await pg.evaluate(PACE_OFF)

async def leg_haboob(pg):
    await js(pg, air('s.pos.x', 's.pos.z', 3000, 90, 300))   # back east over the valley, clear of the White Tanks
    await pg.evaluate(PACE_ON)
    await pg.evaluate(f"()=>{{{K}.stallMark('haboob:tod');{K}.setTOD('haboob');}}")
    await pg.wait_for_timeout(300)
    await js(pg, hbj(4000))
    await pg.wait_for_timeout(10000)
    await pg.evaluate(f"()=>{K}.stallMark('haboob:inside')")
    await js(pg, hbj(-1000))
    await pg.wait_for_timeout(10000)
    await pg.evaluate(f"()=>{{{K}.stallMark('haboob:cockpit');{K}.cycleCam();}}")
    cam = await pg.evaluate(f"()=>{K}.camMode()")
    await pg.wait_for_timeout(9500)
    await pg.evaluate(PACE_OFF)
    await js(pg, CAM0)
    return {'hb': await pg.evaluate(f"()=>{K}.haboob().on"), 'cockpit_cam': cam}

# bandit 0 1,500 m dead ahead, straight and level our way (as tests/dogfight_weapons_check.py places it)
PLACE = f"""()=>{{const K={K},s=K.state(),D=K.DF,b=D.bandits[0];if(!b)return false;D.test.hold=true;
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(s.quat);b.p.copy(s.pos).addScaledVector(n,1500);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);return true;}}"""
async def leg_dogfight(pg):
    await js(pg, f"{UNMAP}{K}.setTOD('day');{K}.DF.test.seed=1;{K}.DF.test.noBrief=true;{K}.DF.test.noDecoy=true;{K}.dfStart();{CAM0}")
    await pg.wait_for_timeout(3000)
    t0 = time.time(); lock = False
    if await pg.evaluate(PLACE):
        while time.time() - t0 < 15:
            await pg.wait_for_timeout(500)
            if await pg.evaluate(f"()=>{K}.DF.seek&&{K}.DF.seek.state==='lock'"): lock = True; break
            await pg.evaluate(PLACE)
    if lock:
        await pg.evaluate(f"()=>{K}.stallMark('dogfight:fox')")
        await tap(pg, '#bFox')
    await pg.wait_for_timeout(max(1000, 37000 - (time.time() - t0) * 1000))
    await pg.evaluate(f"()=>{{{K}.DF.test.hold=false;}}")
    return await pg.evaluate(f"()=>({{on:{K}.DF.on,lock:{str(lock).lower()},shots:{K}.DF.shots,kills:{K}.DF.kills,msl_on:{K}.DF.msl.filter(m=>m.on).length}})")

# the flight's pause sheet, its Main menu; the compiles the menu's warm-up run costs (fine) returned
WARM_DONE = f"()=>{K}.boot().pre.done&&{K}.warm()"
# two frames: after a start, how long the first flight frames take (the GPU sync is the game's own: the requeued
# precompile queue ends on a pixel read back in the menu, boot().pre.syncMs)
RAF2 = "()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(performance.now()))))"
async def settle(pg):
    t0 = time.time(); await pg.evaluate(RAF2); return time.time() - t0
async def to_menu(pg):
    await tap(pg, '#bPause'); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>document.getElementById('pMenu').click()")
    await pg.wait_for_timeout(600)
async def menu_tier(pg, tier):
    c0 = await pg.evaluate(PROG); t0 = time.time()
    await pg.evaluate(f"(t)=>{{{K}.stallMark('tier:'+t);{K}.tabGo('sSet');{K}.GFX.setTier(t);}}", tier)
    await pg.wait_for_function(f"()=>{K}.boot().pre.done", timeout=240000, polling=250); t1 = time.time() - t0
    await pg.wait_for_function(WARM_DONE, timeout=240000, polling=250)
    t2 = time.time() - t0; sync = await pg.evaluate(f"()=>{K}.boot().pre.syncMs")
    print(f'  menu: {tier}, pre.done after {t1:.1f} s (GPU sync {sync} ms), WARM.done after {t2:.1f} s', flush=True)
    await pg.wait_for_timeout(800)
    return await pg.evaluate(PROG) - c0
async def tier_fly(pg, ms):
    t0 = time.time(); await js(pg, fly('f16', 'day', 'runway')); t1 = time.time() - t0
    t2 = await settle(pg)
    print(f'  start() {t1:.1f} s, the first two flight frames {t2:.1f} s', flush=True)
    await pg.wait_for_timeout(1500)
    await js(pg, air(-8000, 0, 3000, 270, 300))
    await pg.wait_for_timeout(ms)
# the battery guard: in flight it may only set pendingTier (and its cheap measures); the menu applies it
THERM = f"""()=>{{const K={K},G=K.GFX,t0=G.tier;G.setScale(0.7);K.stallMark('thermal');
  for(let i=0;i<1860;i++)K.thermalFeed(30,30,1/60);
  return {{tier0:t0,tier:G.tier,pending:G.pendingTier,on:G.thermS.on,scale:G.scale}};}}"""
STALL_TAGS = f"()=>{K}.stalls().log.filter(r=>!/^menu/.test(r.scene)).map(r=>r.tags.join(' '))"
async def leg_tier(pg):
    other = 'high' if TIER != 'high' else 'medium'
    note = {'menu_compiles': 0, 'flight': {}}
    for tier in (other, TIER):
        await to_menu(pg)
        note['menu_compiles'] += await menu_tier(pg, tier)
        c0 = await pg.evaluate(PROG)
        await tier_fly(pg, 9000)
        if tier == TIER:
            for sc in (0.85, 1):
                await pg.evaluate(f"(s)=>{{{K}.stallMark('scale:'+s);{K}.GFX.setScale(s);}}", sc)
                await pg.wait_for_timeout(3000)
        note['flight'][tier] = await pg.evaluate(PROG) - c0
    # the battery guard, on this tier
    await tier_fly(pg, 2000)
    c0 = await pg.evaluate(PROG); n0 = len(await pg.evaluate(STALL_TAGS))
    th = await pg.evaluate(THERM)
    await pg.wait_for_timeout(4000)
    tags = (await pg.evaluate(STALL_TAGS))[n0:]
    th['flight_compiles'] = await pg.evaluate(PROG) - c0
    th['bad_tags'] = [t for t in tags if any(base_tag(x) in ('csmBuild', 'prog', 'hbTier', 'rt') for x in t.split(' '))]
    want = {'medium': 'low', 'high': 'medium'}.get(TIER)
    c1 = await pg.evaluate(PROG)
    await to_menu(pg)
    await pg.wait_for_timeout(500)
    await pg.wait_for_function(WARM_DONE, timeout=240000, polling=250)
    await pg.wait_for_timeout(800)
    note['menu_compiles'] += await pg.evaluate(PROG) - c1
    after = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,pending:{K}.GFX.pendingTier,pre:{K}.boot().pre.done,override:{K}.GFX.override}})")
    th['after_menu'] = after
    th['ok'] = (th['tier'] == th['tier0'] == TIER and th['pending'] == want and th['on'] and not th['bad_tags']
                and th['flight_compiles'] == 0 and after['tier'] == want and after['pending'] is None and after['pre'])
    note['thermal'] = th
    # leg h flies on the tier the guard left
    await tier_fly(pg, 1500)
    return note

async def leg_pause(pg):
    ok = await tap(pg, '#bPause')
    await pg.wait_for_timeout(5000)
    p = await pg.evaluate(f"()=>{K}.paused()")
    await pg.evaluate(f"()=>{K}.stallMark('pause:resume')")
    await pg.evaluate("()=>document.getElementById('pResume').click()")
    await pg.wait_for_timeout(10000)
    return {'tapped': ok, 'paused': p, 'resumed': not await pg.evaluate(f"()=>{K}.paused()")}

LEGS = [('takeoff', leg_takeoff), ('whitetanks', leg_whitetanks), ('explosion', leg_explosion), ('sunset', leg_sunset),
        ('haboob', leg_haboob), ('dogfight', leg_dogfight), ('tier', leg_tier), ('pause', leg_pause)]

async def main():
    T0 = time.time()
    url = serve(ROOT)
    async with async_playwright() as p:
        b = await launch(p)
        ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page(); pg.errs = []
        run = Run(pg)
        pg.on('pageerror', lambda e: pg.errs.append(str(e)))
        def on_console(m):
            if m.type == 'error' and not any(k in m.text for k in IGNORE): pg.errs.append(m.text)
            if m.text.startswith('[stall]'): run.cons.append(m.text)
        pg.on('console', on_console)
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000)
        await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=60000)
        # the warm-up: the precompile queue (boot().pre.done) and the menu's WARM steps (warm(), WARM.done; warmTimes().total set with it)
        await pg.wait_for_function(f"()=>{K}.boot().pre.done&&{K}.warm()&&{K}.warmTimes().total>0", timeout=90000, polling=250)
        await pg.wait_for_timeout(2000)
        tier = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,override:{K}.GFX.override}})")
        run.prog = prog0 = await pg.evaluate(PROG)
        run.keys = await pg.evaluate(f"()=>{K}.progList()")
        await pg.evaluate(f"()=>{K}.stallsClear()")
        # the threshold comes from flight frames (the menu draws no world, its frames say nothing): 1,000 ms until the
        # takeoff leg has flown 3 s, then max(250, 3 x the median of three 1 s means of fpsStats().ms)
        await pg.evaluate(f"()=>{K}.stallsThr(1000)")
        print(f'stall_check: tier {tier}, warm-up done {time.time()-T0:.0f}s, {prog0} programs compiled so far', flush=True)
        await pg.evaluate(SAMPLER)
        for name, fn in LEGS:
            if ONLY and name not in ONLY.split(','): continue
            await run.leg(name, fn)
        heap = await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576*10)/10:null")
        errs = list(pg.errs)
        await ctx.close(); await b.close()

    legs = run.legs
    by_tag = Counter(); expl = rest = 0; gate_fail = []
    for n, L in legs.items():
        for r in L['stalls']:
            tags = [base_tag(t) for t in r['tags'] if t not in r.get('marks', [])]
            by_tag.update(tags)
            if any(t in EXPLAINED for t in tags): expl += 1
            else: rest += 1
            if n in GATED_LEGS and not str(r.get('scene', '')).startswith('menu') and any(t in GATE_TAGS for t in tags):
                gate_fail.append(f'{n}: stall tagged {" ".join(r["tags"])}')
    gated_new = sum(legs[n]['flight_compiles'] for n in GATED_LEGS if n in legs)
    if gated_new: gate_fail.append(f'{gated_new} programs compiled in flight')
    th = legs.get('tier', {}).get('note', {}).get('thermal')
    if th is not None and not th.get('ok'): gate_fail.append(f'battery guard case failed: {th}')
    totals = {'prog0': prog0, 'prog_end': run.prog, 'compiles': run.prog - prog0, 'flight_compiles': gated_new,
              'menu_compiles_tier': legs.get('tier', {}).get('menu_compiles', 0),
              'stalls': sum(len(L['stalls']) for L in legs.values()), 'explained': expl, 'unexplained': rest,
              'by_tag': dict(by_tag.most_common()), 'thr': THR['thr'], 'median_ms': THR['med'], 'tier': TIER, 'heapMB': heap,
              'wall_s': round(time.time() - T0)}
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    json.dump({'legs': legs, 'totals': totals, 'errors': errs}, open(OUT, 'w'), indent=1)

    print(f'\n{"leg":<11} {"wall s":>6} {"flight":>6} {"menu":>5} {"stalls":>6}  top tags   (compiles: new program ids)')
    for n, L in legs.items():
        c = Counter(base_tag(t) for r in L['stalls'] for t in r['tags'] if t not in r.get('marks', []))
        print(f'{n:<11} {L["wall_s"]:>6.1f} {L["flight_compiles"]:>6} {L["menu_compiles"]:>5} {len(L["stalls"]):>6}  ' + ', '.join(f'{k} {v}' for k, v in c.most_common(5)))
    if th is not None: print('battery guard:', th)
    print(f'compiles {prog0} -> {run.prog} (+{run.prog - prog0}; in flight {gated_new}, in the tier leg\'s menu {totals["menu_compiles_tier"]}), stalls {totals["stalls"]}: '
          f'{expl} explained ({"/".join(EXPLAINED)}), {rest} other; threshold {THR["thr"]} ms; wall {totals["wall_s"]} s')
    print('json:', OUT)
    for e in errs: print('  page error:', e)
    if GATE:
        for g in gate_fail: print('  GATE:', g)
    code = 1 if errs or (GATE and gate_fail) else 0
    print('stall_check: ' + ('FAILED' if code else 'done'))
    sys.exit(code)

if __name__ == '__main__':
    asyncio.run(main())
