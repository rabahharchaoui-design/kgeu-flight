# Crashfx item 5: what a crash into a structure costs. Medium (the harness tier) unless --tier.
# A, stalls (the real rAF loop, never stepFrame, WASTED on): after the warm-up, fly into a hangar (Cessna), the stadium
# (747), a downtown tower (F-16) and a house (Cessna) at speed from 200 m out; report the impact frame's CPU time (the
# tick: the breakup, the fire, the sound), the logger's stalls (frames over max(250 ms, 3x the median headless frame))
# with their tags, and the shader programs compiled in flight (must be 0).
# B, frame time during the fire against a normal crash: the same aircraft crashed into the ground at the same place (60 m
# short of the face, crashNow: the normal ground crash) and into the structure, 6 s on, through the crash camera; mean frame ms over 40 frames with
# a 1 px readback; ratio ground/structure (an fps ratio), floor 0.90. Two rounds, interleaved.
# Run: .venv/bin/python -u tests/crashfx_perf.py [--part a|b] [--tier low|medium|high] [--rounds 2]
import asyncio, os, sys, json, statistics
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15

ok = Checks()
K = 'window.__kgeu'
args = sys.argv[1:]
def opt(k, d): return args[args.index(k) + 1] if k in args else d
PART = opt('--part', 'ab')
TIER = opt('--tier', None)
ROUNDS = int(opt('--rounds', '2'))
OUT = opt('--out', '/tmp/crashfx_perf.json')

# aim the aircraft at a structure 200 m out (or `back`), level at `frac` of its height, at spd m/s; live loop
AIM = """([type,sel,ax,sg,back,frac,spd])=>{const K=window.__kgeu;K.pick(type);K.pickBase(K.baseOK(type,'kgeu')?'kgeu':'phx');K.start('runway');
  const S=K.STR.list,f=new Function('r','K','return '+sel),r=S.find(q=>f(q,K));
  const st=K.state();let lx=0,lz=0;if(ax==='x')lx=sg*(r.hx+back);else lz=sg*(r.hz+back);
  const x=r.x+lx*r.c+lz*r.s,z=r.z-lx*r.s+lz*r.c,y=r.y0+frac*(r.y1-r.y0)+2,d=new THREE.Vector3(r.x-x,0,r.z-z).normalize();
  st.pos.set(x,y,z);st.vel.copy(d).multiplyScalar(spd);st.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);st.onGround=false;st.gearDown=false;st.gearPos=0;st.w.set(0,0,0);st.airTime=5;
  st.throttle=st.power=0.7;return r.id;}"""
CASES = [('cessna', "r.name==='a hangar'", 'z', 1, 120, 0.5, 50, 'Cessna into a hangar'),
         ('b747', "r.name==='the stadium'", 'x', -1, 200, 0.45, 80, '747 into the stadium'),
         ('f16', "r.name==='a tower'&&r.y1>120", 'x', 1, 200, 0.5, 200, 'F-16 into a downtown tower'),
         ('cessna', "r.name==='a house'&&Math.hypot(r.x+2473,r.z+1767.5)<1", 'x', -1, 120, 0.5, 45, 'Cessna into a house')]

FRAME_MS = """(n)=>{const K=window.__kgeu,c=document.getElementById('gl'),gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
  K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
  const t0=performance.now();for(let i=0;i<n;i++){K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);}
  return (performance.now()-t0)/n;}"""

async def wait_warm(pg):
    await pg.wait_for_function(f"()=>{K}.warm()&&{K}.gfxBusy().preDone", timeout=420000)

async def part_a(b, url, st0, res):
    pg = await page(b, url, vp=IPHONE_15, storage=st0)
    await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);}}")
    await wait_warm(pg)
    tier = await pg.evaluate(f"()=>{K}.GFX.tier")
    print('  tier', tier)
    for t, sel, ax, sg, back, frac, spd, label in CASES:
        await pg.evaluate(AIM, [t, sel, ax, sg, back, frac, spd])
        await pg.evaluate(f"()=>{{{K}.stepFrame(0,true);}}")   # the live loop
        await pg.wait_for_timeout(2500)   # settle: the start's own frames (the terrain rings round the new spot load on)
        p0 = await pg.evaluate(f"()=>{{{K}.stallsClear();return {K}.progN().compiles;}}")
        await pg.wait_for_function(f"()=>{K}.state().crashed", timeout=240000, polling=50)
        tc = await pg.evaluate("()=>performance.now()/1000-1")   # the impact (to a frame or so): stalls from here on are the crash's
        await pg.wait_for_timeout(7000)   # the impact, the breakup, WASTED and the fire for a few seconds of real time
        r = await pg.evaluate(f"""()=>{{const K=window.__kgeu,S=K.stalls(),F=K.boot().ft.fly,ms=F.map(e=>e[1]).filter(v=>v!=null).sort((a,b)=>a-b),cpu=F.map(e=>e[0]);
          return {{log:S.log.map(e=>({{ms:e.gap,tags:(e.tags||[]).join(' '),cpu:e.tick,t:e.t}})),thr:S.thr,median:ms[ms.length>>1]||0,cpuMax:Math.max(...cpu),cpuMed:cpu.slice().sort((a,b)=>a-b)[cpu.length>>1],
            prog:K.progN().compiles,cfx:K.cfx(),sf:K.sf(),fxq:K.fxqN()}}}}""")
        r['prog0'] = p0
        thr = max(250, 3 * r['median'])
        big = [e for e in r['log'] if e['ms'] and e['ms'] > thr and (e['t'] >= tc or 'crash' in e['tags'])]
        print(f"  {label}: impact breakup {r['cfx']['ms']} ms, CPU tick max {r['cpuMax']:.0f} ms (median {r['cpuMed']:.0f}), frame median {r['median']:.0f} ms, "
              f"stalls over {thr:.0f} ms: {len(big)} {big[:3]}, programs compiled {r['prog'] - p0}, FX quads {r['fxq']['count']}")
        res['a_' + label] = r
        ok(f'{label}: no shader program compiled in flight', r['prog'] == p0, r['prog'] - p0)
        ok(f'{label}: the breakup builds in well under 250 ms ({r["cfx"]["ms"]} ms headless)', r['cfx']['ms'] < 120)
        ok(f'{label}: no stall from the impact (no frame over max(250, 3x median) headless)', not big, big)
        await pg.evaluate(f"()=>{{{K}.stepFrame(0);}}")   # hold the loop again for the next aim
    errs = [e for e in pg.errs]
    ok('A: no console errors', not errs, errs[:3])
    await pg.context.close()

async def part_b(b, url, st0, res):
    pg = await page(b, url, vp=IPHONE_15, storage=st0)
    await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);{K}.WST.off=true;}}")
    await wait_warm(pg)
    rows = {}
    for rnd in range(ROUNDS):
        for t, sel, ax, sg, back, frac, spd, label in CASES[:3]:
            for kind in ('ground', 'structure'):
                if kind == 'ground':
                    # the normal ground crash at the same place: in the air 60 m short of the face, crashNow (no structure hit)
                    await pg.evaluate(AIM, [t, sel, ax, sg, 60, frac, spd])
                    await pg.evaluate("()=>{const K=window.__kgeu;K.stepFrame(1/60,false,true);K.crashNow('Test crash.');}")
                else:
                    await pg.evaluate(AIM, [t, sel, ax, sg, 40, frac, spd])
                    await pg.evaluate("()=>{const K=window.__kgeu,s=K.state();let n=0;while(!s.crashed&&n<600){K.stepFrame(1/60,false,true);n++;}}")
                # 6 s on; then the same fixed camera for both (off the face, looking at it): the view is the same, only the
                # crash differs
                await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<180;i++)K.stepFrame(1/30,false,i%10!==9);}")
                await pg.evaluate("""([sel,ax,sg,d])=>{const K=window.__kgeu,S=K.STR.list,f=new Function('r','K','return '+sel),r=S.find(q=>f(q,K));
                  let lx=0,lz=0;if(ax==='x')lx=sg*(r.hx+d);else lz=sg*(r.hz+d);const x=r.x+lx*r.c+lz*r.s,z=r.z-lx*r.s+lz*r.c,y=(r.y0+r.y1)/2;
                  K.freeCam({w:true,p:[x+(z-r.z)*0.3,y+25,z-(x-r.x)*0.3],t:[r.x,y+10,r.z],fov:55});}""", [sel, ax, sg, 90 if t == 'cessna' else 220])
                ms = await pg.evaluate(FRAME_MS, 40)
                await pg.evaluate(f"()=>{K}.freeCam(null)")
                rows.setdefault((label, kind), []).append(ms)
                print(f"  round {rnd+1} {label} {kind}: {ms:.1f} ms")
    for t, sel, ax, sg, back, frac, spd, label in CASES[:3]:
        g, s = statistics.mean(rows[(label, 'ground')]), statistics.mean(rows[(label, 'structure')])
        ratio = g / s
        res['b_' + label] = {'ground_ms': g, 'structure_ms': s, 'fps_ratio': ratio}
        ok(f'{label}: frame rate during the fire within 10 percent of a normal crash (fps ratio {ratio:.2f}, {g:.0f} ms vs {s:.0f} ms)', ratio >= 0.90)
    await pg.context.close()

async def main():
    srv, url = serve()
    st0 = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
    if TIER: st0['kgeuTier'] = TIER
    res = {}
    async with async_playwright() as p:
        b = await launch(p)
        if 'a' in PART: await part_a(b, url, st0, res)
        if 'b' in PART: await part_b(b, url, st0, res)
        await b.close()
    srv.shutdown()
    json.dump(res, open(OUT, 'w'), indent=1, default=str)
    ok.done('crashfx_perf')
    sys.exit(1 if ok.fails else 0)

asyncio.run(main())
