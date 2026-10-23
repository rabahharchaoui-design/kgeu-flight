# Stepstall 3: a step change costs no frame. Two parts.
#  A (held frames, every step): each check that flies a lesson, a tasking or a mission through its steps runs unchanged with
#    the step probe (tests/stepprobe.py through PFS_STEPPROBE): the first flight, climbs, ground reference, the circuits,
#    solo, short and soft field, crosswind, emergencies, the hood, pilotage, divert, night, solo cross country, the
#    checkride, the slow flight and pattern of school_cfi_check, the four taskings (OVERWATCH, LIFELINE, SHEPHERD,
#    FINDER), the drop zone and the dogfight. Every step change (the card's instruction, a tasking's stage, a mission
#    pill's step) is checked: its frame's work and the frame after it rendered under 50 ms headless, no shader program
#    linked, and nothing in the frame that belongs after it: no speechSynthesis call, no localStorage write, no fetch.
#  B (real frames, the rAF loop with the stall logger on): the pattern lesson (the owner's example) flown through its five
#    steps by pins set at the top of each frame (stepprobe's SP.pin), each tasking's stages forced in a frame
#    (__kgeu.tqStage), the airdrop's AIRDROP to TO CENTER and the short field's ASSAULT LANDING to ROLLOUT. Each step's
#    frame and the two after it must stay under 3x the leg's median frame (headless frames are ~300 ms, so 50 ms means
#    nothing there), with no compile in the leg, no speech call, storage write or fetch inside the step's frame; the
#    speech job must run after the frame (counted after it), and the stall logger must log nothing tagged in a step frame.
#  Schoolhud: A and B also fail on any read of window.speechSynthesis (the game must never touch it); A checks that each
#    step's new instruction is readable in the frame that changed it and that the top caption and the bottom task card
#    overlap nothing on the next frame. C: the layout at 568x320, 844x390, 932x430 and 390x844 (the pattern lesson's steps
#    with Dana, the OVERWATCH stages, the airdrop, the dogfight). D: B's pattern leg with the CPU throttled 4x and audio on
#    (Dana's clips decoded and played), the same frame budget.
# Page errors fail it. Usage: .venv/bin/python tests/stepstall_check.py [--part a|b|c|d, or several: abcd] [--only name,name] [--par 4]
#   [--out /tmp/stepstall/run] (A's records and the drivers' logs go there; B's to <out>/b.jsonl)
import asyncio, glob, json, os, statistics, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from stepprobe import PROBE

args = sys.argv[1:]
def opt(name, dflt):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return dflt
PART = opt('--part', 'abcd'); ONLY = [x for x in opt('--only', '').split(',') if x]; PAR = int(opt('--par', '4'))
OUT = opt('--out', '/tmp/stepstall/run')
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ok = Checks()
K = 'window.__kgeu'
STEPK = ('step', 'stage', 'mstep')

# ---------------- part A ----------------
DRIVERS = ['school_check', 'school_climbs_check', 'school_ground_check', 'school_landings_check', 'school_solo_check',
           'school_short_check', 'school_soft_check', 'school_xwind_check', 'school_emerg_check', 'school_hood_check',
           'school_xc_check', 'school_divert_check', 'school_night_check', 'school_soloxc_check', 'school_ride_check',
           'school_cfi_check', 'tasking_overwatch_check', 'tasking_lifeline_check', 'tasking_shepherd_check',
           'tasking_finder_check', 'dz_check', 'dogfight_check']

def run_drivers(names):
    os.makedirs(OUT, exist_ok=True)
    res = {}
    for i in range(0, len(names), PAR):
        batch = names[i:i + PAR]; procs = {}
        for n in batch:
            f = f'{OUT}/{n}.jsonl'
            if os.path.exists(f): os.remove(f)
            env = dict(os.environ, PFS_STEPPROBE=f)
            procs[n] = subprocess.Popen([os.path.join(ROOT, '.venv/bin/python'), '-u', f'tests/{n}.py'], cwd=ROOT, env=env,
                                        stdout=open(f'{OUT}/{n}.log', 'w'), stderr=subprocess.STDOUT)
        for n, p in procs.items():
            try: res[n] = p.wait(timeout=600)
            except subprocess.TimeoutExpired: p.kill(); res[n] = 'timeout'
            print(f'  driver {n}: exit {res[n]}', flush=True)
    return res

def load(n):
    ev, ctl = [], []
    f = f'{OUT}/{n}.jsonl'
    if not os.path.exists(f): return ev, ctl
    for ln in open(f):
        try: r = json.loads(ln.split(' ', 1)[1])
        except Exception: continue
        if r.get('ctl'): ctl.append(r)
        elif 'kinds' in r: ev.append(r)
    return ev, ctl

def part_a():
    names = [n for n in DRIVERS if not ONLY or n in ONLY]
    print(f'[A] {len(names)} drivers, {PAR} at a time', flush=True)
    codes = run_drivers(names)
    # a driver that died on a page load under the parallel load: once more, alone
    for n in [n for n, c in codes.items() if c != 0]:
        log = open(f'{OUT}/{n}.log').read()
        if 'Timeout' in log or 'TargetClosed' in log or 'Target page' in log:
            print(f'  {n}: rerun alone', flush=True); codes.update(run_drivers([n]))
    worst, n_steps, cover = [], 0, {}
    for n in names:
        ev, ctl = load(n)
        steps = [r for r in ev if any(k in STEPK for k in r['kinds']) and not any('start' in k for k in r['kinds'])]
        cover[n] = len(steps); n_steps += len(steps)
        bad = []
        for r in steps:
            c, rc = r['c'], r.get('render', {}).get('c', {})
            if r['path'] == 'raf':   # a real frame between the driver's held batches: its gap is the driver's, its in-frame calls are the game's
                why = [w for w, x in ((f"{c['speak']} speak {c['cancel']} cancel {c['voices']} getVoices", c['speak'] + c['cancel'] + c['voices']),
                       ('storage ' + ','.join(c['lsKeys']), c['ls']), (f"{c['fetch']} fetch", c['fetch'] + c['beacon']), (f"{r['prog']} programs", r['prog'])) if x]
                if why: bad.append(f"real frame {'+'.join(r['kinds'])} '{(r['i'] or r['m'])[:40]}': {', '.join(why)}")
                continue
            ms, rms = r['ms'], r.get('render', {}).get('ms', 0)
            prog = r['prog'] + r.get('render', {}).get('prog', 0)
            sp = c['speak'] + c['cancel'] + c['voices'] + rc.get('speak', 0) + rc.get('cancel', 0) + rc.get('voices', 0)
            ls = c['ls'] + rc.get('ls', 0); fe = c['fetch'] + c['beacon'] + rc.get('fetch', 0)
            why = []
            if ms > 50: why.append(f'frame {ms} ms')
            if rms > 50: why.append(f'render {rms} ms')
            if prog: why.append(f'{prog} programs linked')
            if sp: why.append(f'{sp} speech calls')
            if ls: why.append('storage ' + ','.join(c['lsKeys'] + rc.get('lsKeys', [])))
            if fe: why.append(f'{fe} fetch')
            # schoolhud item 4: the next instruction readable in the frame the step completes, the caption and the card clear
            v = r.get('vis')
            if v is not None and not v.get('ok'): why.append(f'the new instruction not readable in its frame {v}')
            if r.get('lap'): why.append('overlap ' + '; '.join(r['lap'][:3]))
            worst.append((max(ms, rms), n, r['kinds'], r['i'] or r['m']))
            if why: bad.append(f"{'+'.join(r['kinds'])} '{(r['i'] or r['m'])[:40]}': {', '.join(why)}")
        ssr = max([r.get('ssr', 0) for r in ev + ctl] + [0])
        if ssr: bad.append(f'window.speechSynthesis read {ssr} times')
        nvis = sum(1 for r in steps if r.get('vis'))
        cm = statistics.median([x['ms'] for x in ctl]) if ctl else 0
        mx = max([r.get('ms', 0) for r in steps] + [0]); rmx = max([r.get('render', {}).get('ms', 0) for r in steps] + [0])
        ok(f'(A) {n}: {len(steps)} step changes ({sum(r["path"]=="raf" for r in steps)} on real frames), frame max {mx:.1f} ms, rendered {rmx:.1f} ms (quiet frames {cm:.1f} ms), nothing in the frame that belongs after it, no speechSynthesis at all, {nvis} instructions readable in their frame, the caption and the card overlapping nothing',
           len(steps) > 0 and not bad, (bad[:4], f'driver exit {codes.get(n)}'))
        if codes.get(n) not in (0, None): print(f'  note: {n} exited {codes.get(n)} (its own checks; see {OUT}/{n}.log)')
    worst.sort(reverse=True)
    print(f'  {n_steps} step changes in all; the five costliest: ' + '; '.join(f'{w[0]:.1f} ms {w[1]} {"+".join(w[2])} {w[3][:30]!r}' for w in worst[:5]))

# ---------------- part B ----------------
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchoolEasy': '0', 'kgeuTOD': 'day', **PLACED}
UV = "(u,v)=>{const K=window.__kgeu,R=K.rwyFrame().rh*Math.PI/180;return [Math.sin(R)*u+Math.cos(R)*v,-Math.cos(R)*u+Math.sin(R)*v]}"
# a pin at the top of every frame (before the game's tick): the speed, vertical speed, heading; the position once
PIN = """(o)=>{const K=window.__kgeu;window.__sp.pin=K=>{const s=K.state();if(!K.running()||K.paused()||s.crashed)return;s.windKt=0;s.gustAmp=0;
  if(o.x!=null){s.pos.x=o.x;s.pos.z=o.z;o.x=null;}
  if(o.agl!=null){s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+o.agl/3.28084+1.3;o.agl=null;}
  const h=o.hdg*Math.PI/180,V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225),vy=(o.vs||0)/196.85;
  s.vel.set(Math.sin(h)*V,vy,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(Math.atan2(vy,V)+0.04,-h,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;};}"""
UNPIN = "()=>{window.__sp.pin=null;}"
ONCE = "(js)=>{const f=new Function('K',js);window.__sp.pin=K=>{window.__sp.pin=null;f(K);};}"   # run once, at the top of the next frame

class B:
    def __init__(self, pg): self.pg, self.t0 = pg, 0
    async def leg_begin(self, name):
        print(f'\n[B {name}]', flush=True)
        self.name = name; self.prog0 = await self.pg.evaluate(f"()=>{K}.progN().compiles")
        self.ev0 = await self.pg.evaluate("()=>window.__sp.ev.length"); self.g0 = await self.pg.evaluate("()=>window.__sp.raf.gaps.length")
        await self.pg.evaluate(f"()=>{K}.stallsClear()")
    async def leg_end(self, want):
        pg = self.pg
        await pg.wait_for_timeout(1500)   # the last step's two frames after it
        prog = await pg.evaluate(f"()=>{K}.progN().compiles") - self.prog0
        ev = await pg.evaluate("(n)=>window.__sp.ev.slice(n).filter(r=>r.path==='raf')", self.ev0)
        gaps = await pg.evaluate("(n)=>window.__sp.raf.gaps.slice(n)", self.g0)
        stl = await pg.evaluate(f"()=>{K}.stalls().log")
        steps = [r for r in ev if any(k in STEPK for k in r['kinds']) and not any('start' in k for k in r['kinds'])]   # a flight's start (from the menu) is not a step
        med = statistics.median(gaps) if gaps else 0; thr = max(250, 3 * med)
        bad = []
        for r in steps:
            c, a = r['c'], r.get('ca', {})
            why = []
            if r['gap'] > thr: why.append(f"frame {r['gap']:.0f} ms")
            if any(x > thr for x in r['after']): why.append(f"after {r['after']}")
            if c['speak'] + c['cancel'] + c['voices']: why.append(f"{c['speak']} speak {c['cancel']} cancel {c['voices']} getVoices in the frame")
            if c['ls']: why.append('storage ' + ','.join(c['lsKeys']))
            if c['fetch'] + c['beacon']: why.append(f"{c['fetch']} fetch")
            if r['prog']: why.append(f"{r['prog']} programs")
            if r.get('stall') and any(t.split('+')[0] in ('prog', 'csmBuild', 'pmrem', 'hbTier') for t in r['stall']['tags']): why.append('stall ' + ' '.join(r['stall']['tags']))
            if why: bad.append(f"{'+'.join(r['kinds'])} {(r['i'] or r['m'])[:36]!r}: {', '.join(why)}")
        rec = {'leg': self.name, 'median': med, 'thr': thr, 'prog': prog, 'steps': [{'kinds': r['kinds'], 'what': (r['i'] or r['m'])[:60], 'gap': r['gap'], 'after': r['after'],
               'in': {k: r['c'][k] for k in ('speak', 'cancel', 'voices', 'ls', 'fetch', 'an', 'bcr', 'lay')}, 'post': {k: r.get('ca', {}).get(k, 0) for k in ('speak', 'cancel', 'ls')},
               'stall': r.get('stall')} for r in steps], 'stalls': stl}
        with open(f'{OUT}/b.jsonl', 'a') as f: f.write(json.dumps(rec) + '\n')
        for r in steps: print(f"  {'+'.join(r['kinds']):12s} {(r['i'] or r['m'])[:44]:44s} frame {r['gap']:6.0f} then {r['after']}  in-frame speak/cancel {r['c']['speak']}/{r['c']['cancel']} ls {r['c']['ls']}  after-frame speak/cancel {r.get('ca',{}).get('speak',0)}/{r.get('ca',{}).get('cancel',0)} ls {r.get('ca',{}).get('ls',0)}")
        ok(f'(B) {self.name}: {len(steps)} of at least {want} step changes, each frame and the two after it under {thr:.0f} ms (median {med:.0f}), {prog} compiles, nothing in the frame that belongs after it',
           len(steps) >= want and not bad and prog == 0, bad[:4])
        return steps

async def wait(pg, cond, sec):
    try: await pg.wait_for_function(cond, timeout=sec * 1000, polling=100); return True
    except Exception: return False

async def b_pattern(pg, T):
    # schoolhud: Dana's clips decoded on the menu first (a flight's 300 ms headless frames starve the decode), as the briefing does
    await pg.evaluate(f"()=>{K}.cfiPrep&&{K}.cfiPrep('pattern')")
    await wait(pg, f"()=>!{K}.CFIV||({K}.CFIV.want>0&&{K}.CFIV.got>={K}.CFIV.want)", 90)
    await T.leg_begin('pattern')
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('pattern',true,{{brief:false}});K.lesBriefSkip&&K.lesBriefSkip();}}")
    F = await pg.evaluate(f"()=>{K}.rwyFrame()")
    xz = lambda u, v: pg.evaluate(f"([u,v])=>({UV})(u,v)", [u, v])
    await pg.wait_for_timeout(1500)
    # the tower call (CALL), then each step in turn, pinned on the real loop
    if await wait(pg, f"()=>{K}.TASK.ask&&{K}.TASK.ask.shown", 30): await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    await pg.wait_for_timeout(1500)
    x, z = await xz(F['thr'] + 1300, 0)
    await pg.evaluate(PIN, {'x': x, 'z': z, 'agl': 760, 'kt': 74, 'vs': 600, 'hdg': F['rh']})
    await wait(pg, f"()=>{K}.LES.ph===1", 30); await pg.wait_for_timeout(2500)
    x, z = await xz(F['thr'] + 1500, 900)
    await pg.evaluate(PIN, {'x': x, 'z': z, 'agl': 2100 - F['field'], 'kt': 95, 'vs': 0, 'hdg': F['rh'] + 180})
    await wait(pg, f"()=>{K}.LES.ph===2", 30); await pg.wait_for_timeout(2500)
    if await wait(pg, f"()=>{K}.TASK.ask&&{K}.TASK.ask.shown", 15): await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    x, z = await xz(F['thr'] + 100, 900)
    await pg.evaluate(PIN, {'x': x, 'z': z, 'agl': 1000, 'kt': 80, 'vs': -400, 'hdg': F['rh'] - 90})
    await wait(pg, f"()=>{K}.LES.ph===3", 30); await pg.wait_for_timeout(2500)
    x, z = await xz(F['thr'] - 600, 0)
    await pg.evaluate(PIN, {'x': x, 'z': z, 'agl': 120, 'kt': 65, 'vs': -300, 'hdg': F['rh']})
    await pg.wait_for_timeout(1500)
    x, z = await xz(F['thr'] + F['aim'] + 60, 1)
    await pg.evaluate(ONCE, f"K.events.push({{type:'touchdown',fpm:180,paved:K.isPaved({x},{z}),x:{x},z:{z},ias:33,bank:0}});")
    await wait(pg, f"()=>{K}.LES.ph===4", 15); await pg.wait_for_timeout(2500)
    await pg.evaluate(UNPIN)
    st = await T.leg_end(4)
    sx = await pg.evaluate(f"()=>{K}.stepx?{K}.stepx():null")
    ok("(B) pattern: Dana's lines played from her clips (schoolhud), none missed, the step chime ready, no storage write waiting",
       bool(sx) and sx['cfi']['plays'] > 0 and sx['cfi']['miss'] == 0 and sx['chime'] and sx['ls']['pend'] == 0, sx)
    await pg.evaluate(f"()=>{{const K={K};if(K.LES.on)document.getElementById('lesQuit').click();}}")
    return st

async def b_task(pg, T, tid):
    await T.leg_begin('task:' + tid)
    await pg.evaluate(f"(id)=>{{const K={K};K.TASK.test.noBrief=true;K.taskStart(id,{{seed:7}});}}", tid)
    await pg.wait_for_timeout(1200)
    await pg.evaluate(f"()=>{{const K={K};if(K.TASK.brief&&K.taskGo)K.taskGo();}}")
    await pg.wait_for_timeout(2500)
    n = await pg.evaluate(f"()=>{K}.TASK.def.stages.length")
    if not await pg.evaluate(f"()=>!!{K}.tqStage"):   # a build before stepstall has no hook to force a stage
        print('  no __kgeu.tqStage in this build: skipped'); await pg.evaluate(f"()=>{K}.taskStop()"); return []
    for i in range(1, n):
        await pg.evaluate(ONCE, f"if(K.TASK.on)K.tqStage({i});")
        await pg.wait_for_timeout(2500)
    st = await T.leg_end(n - 1)
    await pg.evaluate(f"()=>{K}.taskStop()")
    return st

async def b_missions(pg, T):
    await T.leg_begin('mission:airdrop')
    await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop');}}"); await pg.wait_for_timeout(2500)
    await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z;}}")
    await wait(pg, f"()=>{K}.MISS.armed", 20)
    await pg.evaluate(ONCE, "K.missDrop();"); await pg.wait_for_timeout(3000)
    await T.leg_end(1)
    await T.leg_begin('mission:short field')
    await pg.evaluate(f"()=>{K}.start('short')"); await pg.wait_for_timeout(2500)
    await pg.evaluate(ONCE, "const s=K.state();s.vel.set(-60,0,0);const x=K.lzX(K.LZ.len/2-122,0),z=K.lzZ(K.LZ.len/2-122,0);K.missTouchdown({type:'touchdown',fpm:420,paved:true,x:x,z:z});")
    await pg.wait_for_timeout(3000)
    await T.leg_end(1)

async def part_b():
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(f'{OUT}/b.jsonl'): os.remove(f'{OUT}/b.jsonl')
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        async def pre(ctx): await ctx.add_init_script(PROBE)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE, pre=pre)
        await pg.evaluate(f"()=>{K}.initAudio&&{K}.initAudio()")
        await pg.wait_for_function(f"()=>{K}.boot().pre.done&&{K}.warm()", timeout=240000, polling=250)
        await pg.wait_for_timeout(500)
        # the stall logger at 3x the median flight frame (stall_check's rule)
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('runway');}}"); await pg.wait_for_timeout(1500)
        await pg.evaluate(f"()=>{K}.fpsReset()"); ms = []
        for _ in range(3):
            await pg.wait_for_timeout(1000); ms.append((await pg.evaluate(f"()=>{K}.fpsStats()")).get('ms') or 0)
        thr = max(250, round(3 * sorted(ms)[1])); await pg.evaluate(f"(t)=>{K}.stallsThr(t)", thr)
        print(f'median flight frame {sorted(ms)[1]:.0f} ms, stall threshold {thr} ms', flush=True)
        T = B(pg)
        await b_pattern(pg, T)
        for tid in ('overwatch', 'lifeline', 'shepherd', 'finder'): await b_task(pg, T, tid)
        await b_missions(pg, T)
        ok('(B) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()

# ---------------- part C (schoolhud item 4): the layout at four sizes ----------------
# On held frames at 568x320, 844x390, 932x430 and 390x844 (iPhone insets): the pattern lesson's steps (the lesson's own tick
# writes each instruction as its phase moves on) with Dana's lines on the air, the OVERWATCH stages (tqStage) with mission
# control's, the airdrop's AIRDROP to TO CENTER with the Loadmaster's and the dogfight's wave pill with SENTRY's. At every
# step: the new instruction readable in the frame that changed it (in the DOM, on screen, at least half opaque), and the top
# caption and the bottom task card overlap nothing (each other, the buttons, the stick ring, the throttle, the readouts, the
# map, the TCAS panel); a few frames later the same with the caption up. No speechSynthesis read at all.
SIZES_C = [(568, 320, (0, 47, 47, 21)), (844, 390, (0, 47, 47, 21)), (932, 430, (0, 59, 59, 21)), (390, 844, (47, 0, 0, 34))]
SETSAFE = """([t,l,r,b])=>{const s=document.documentElement.style;s.setProperty('--saT',t+'px');s.setProperty('--saL',l+'px');s.setProperty('--saR',r+'px');s.setProperty('--saB',b+'px');
  if(window.layoutCtl)layoutCtl(true);}"""
GEO = """(k)=>{const SP=window.__sp,s={les:window.__kgeu.LES.on||'',i:window.__kgeu.LES.on?document.getElementById('lesI').textContent:'',m:document.getElementById('miss').classList.contains('on')?document.getElementById('missT').textContent:''};
  const v=SP.visOf(s),l=SP.lapOf(),a=document.getElementById('atc'),d=document.querySelector('#dfSub.on span');return {vis:v,lap:l,cap:!!(a.classList.contains('on')||d),ssr:SP.ssr};}"""

async def c_step(pg, tag, js, want_cap=True):
    """js makes the step happen; one rendered frame; then the checks, and again after six frames"""
    r0 = await pg.evaluate(f"()=>{{const K={K};{js};K.stepFrame(1/30);return 0}}")
    g = await pg.evaluate(GEO, 0)
    # the step's own frame lays nothing out (stepstall): a dock that changed with the stage moves the card's band on the next one
    await pg.evaluate(f"()=>{K}.stepFrame(1/30)")
    g1 = await pg.evaluate(GEO, 0)
    ok(f'(C) {tag}: the new instruction readable in its frame; the next frame, the caption and the card clear', bool(g['vis'] and g['vis']['ok']) and not g1['lap'], (g, g1['lap']))
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<6;i++)K.stepFrame(1/30);K.hudFit();K.stepFrame(1/30);}}")
    g2 = await pg.evaluate(GEO, 0)
    ok(f'(C) {tag}: six frames on, still readable and clear' + (' with the caption up' if want_cap else ''), bool(g2['vis'] and g2['vis']['ok']) and not g2['lap'] and (g2['cap'] or not want_cap), g2)
    return g2

async def part_c():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        async def pre(ctx): await ctx.add_init_script(PROBE)
        for (w, h, sa) in SIZES_C:
            pg = await page(b, url, vp={'width': w, 'height': h}, storage=BASE, pre=pre)
            await pg.evaluate("()=>document.body.classList.add('portraitok')")
            await pg.evaluate(SETSAFE, list(sa))
            await pg.wait_for_function("()=>window.__sp&&window.__sp.visOf", timeout=20000)
            tg = f'{w}x{h}'
            # the pattern lesson: airborne past 700 ft, then each phase in turn (the tick writes the instruction), Dana with it
            await pg.evaluate(f"()=>{{const K={K};K.startLesson('pattern',true,{{brief:false}});K.lesBriefSkip&&K.lesBriefSkip();for(let i=0;i<8;i++)K.stepFrame(1/30);}}")
            for ph, line in ((1, 'Turn crosswind now. Level off at 2,100.'), (2, 'You are 250 feet high. Ease the power back a touch.'), (3, 'Turn base, then final. Aim for the numbers.')):
                await c_step(pg, f'{tg} pattern step {ph}', f"const s=K.state();s.onGround=false;K.LES.ph={ph};K.cfi('{line}')")
            await pg.evaluate(f"()=>{{const K={K};if(K.LES.on)document.getElementById('lesQuit').click();K.stepFrame(1/30);}}")
            # OVERWATCH: each stage, with a mission control line (the stage's own radio)
            for _ in range(120):   # overwatch2: the compound's site slots are scanned off the frame once the map data is in
                if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
                await pg.wait_for_timeout(500)
            await pg.evaluate(f"()=>{{const K={K};K.TASK.test.noBrief=true;K.taskStart('overwatch',{{seed:7}});}}"); await pg.wait_for_timeout(600)
            for _ in range(40):
                if await pg.evaluate(f"()=>!!{K}.TASK.d"): break
                await pg.wait_for_timeout(250)
            await pg.evaluate(f"()=>{{const K={K};if(K.TASK.brief&&K.taskGo)K.taskGo();for(let i=0;i<6;i++)K.stepFrame(1/30);}}")
            n = await pg.evaluate(f"()=>{K}.TASK.def.stages.length")
            for i in range(1, n):
                await c_step(pg, f'{tg} OVERWATCH stage {i + 1}', f"K.tqStage({i});K.say('Mission control','Shadow 1, mission control, copy, continue.',[])")
            await pg.evaluate(f"()=>{K}.taskStop()")
            # the airdrop: in the window, the drop, TO CENTER with the Loadmaster's line
            await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop');for(let i=0;i<6;i++)K.stepFrame(1/30);const s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z;}}")
            await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<40&&!K.MISS.armed;i++)K.stepFrame(1/30,false,true);}}")
            await c_step(pg, f'{tg} airdrop TO CENTER', "K.missDrop();K.vqAdd({who:'Loadmaster',kind:'crew',text:'Load clear.',clips:[]},{front:1})")
            # the dogfight: the wave pill and SENTRY's picture call
            await pg.evaluate(f"()=>{{const K={K};K.DF.test.noBrief=true;K.DF.test.noBanditFire=true;K.dfStart();}}")
            for i in range(25):
                if await pg.evaluate(f"()=>{{const K={K};for(let j=0;j<4;j++)K.stepFrame(1/30);K.hudFit();return !!document.querySelector('#dfSub.on span')}}"): break
            g = await pg.evaluate(GEO, 0)
            ok(f'(C) {tg} dogfight: the wave pill readable, SENTRY up top, both clear', bool(g['vis'] and g['vis']['ok']) and not g['lap'] and g['cap'], g)
            ok(f'(C) {tg}: no speechSynthesis read, no page errors', g['ssr'] == 0 and not pg.errs, (g['ssr'], pg.errs[:3]))
            await pg.context.close()
        await b.close()
    srv.shutdown()

# ---------------- part D (schoolhud item 4): the step frames on a phone class CPU ----------------
# Part B's pattern leg on the real rAF loop with the CPU throttled 4x (DevTools Emulation.setCPUThrottlingRate) and audio
# on: an AudioContext, Dana's clips decoded, her lines played as clips at each step. The same budget as B (each step's frame
# and the two after it under 3x the leg's median, no compile, nothing in the frame that belongs after it) and no
# speechSynthesis read; the frame times are printed for the record.
async def part_d():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        async def pre(ctx): await ctx.add_init_script(PROBE)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE, pre=pre)
        await pg.evaluate(f"()=>{K}.initAudio&&{K}.initAudio()")
        await pg.wait_for_function(f"()=>{K}.boot().pre.done&&{K}.warm()", timeout=240000, polling=250)
        await pg.evaluate(f"()=>{K}.cfiPrep('pattern')")
        await wait(pg, f"()=>{K}.CFIV.want>0&&{K}.CFIV.got>={K}.CFIV.want", 90)
        cdp = await pg.context.new_cdp_session(pg)
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        print('CPU throttled 4x', flush=True)
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('runway');}}"); await pg.wait_for_timeout(3000)
        await pg.evaluate(f"()=>{K}.fpsReset()"); ms = []
        for _ in range(3):
            await pg.wait_for_timeout(2000); ms.append((await pg.evaluate(f"()=>{K}.fpsStats()")).get('ms') or 0)
        thr = max(250, round(3 * sorted(ms)[1])); await pg.evaluate(f"(t)=>{K}.stallsThr(t)", thr)
        print(f'median flight frame {sorted(ms)[1]:.0f} ms at 4x, stall threshold {thr} ms', flush=True)
        T = B(pg)
        st = await b_pattern(pg, T)
        pl = await pg.evaluate(f"()=>({{plays:{K}.CFIV.plays,miss:{K}.CFIV.miss.length,ssr:window.__sp.ssr,actx:{K}.actx&&{K}.actx.state}})")
        ok("(D) 4x CPU, audio on: Dana's lines played as clips, none missed, no speechSynthesis read", pl['plays'] > 0 and pl['miss'] == 0 and pl['ssr'] == 0, pl)
        ok('(D) no page errors', not pg.errs, pg.errs[:3])
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
        await b.close()
    srv.shutdown()

if 'b' in PART: asyncio.run(part_b())
if 'c' in PART: asyncio.run(part_c())
if 'd' in PART: asyncio.run(part_d())
if 'a' in PART: part_a()
sys.exit(ok.done('stepstall_check'))
