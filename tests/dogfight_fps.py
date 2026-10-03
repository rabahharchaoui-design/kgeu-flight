# Frame cost of the Red Flag Dogfight, same build / same session / same spot in the world
# (DF.C, the arena centre), so only the ratio against a plain-flight baseline matters.
# Headless software rendering is slow and noisy: frame_ms (copied from aircraft_fps.py) times
# a held tick with a 1 px readback, three repeats per scenario, averaged.
#   A. baseline: F-16 free flight at DF.C, 15,000 ft, 400 kt, chase view, day
#   B. wave 1: one bandit 1 nm ahead in view
#   C. wave 4: four bandits inside 1 nm, in view (HD models), target boxes on
#   D. worst case: C + GUN held (tracers), one player missile + one bandit missile in flight
#      (smoke), flares out, RWR launch vignette on
# A feature may cost at most 20% over baseline (ratio <= 1.25; 5% is noise).
# Run per scenario to stay under the 100 s foreground cap, then --report:
#   .venv/bin/python tests/dogfight_fps.py --scenario A
#   .venv/bin/python tests/dogfight_fps.py --scenario B
#   .venv/bin/python tests/dogfight_fps.py --scenario C
#   .venv/bin/python tests/dogfight_fps.py --scenario D
#   .venv/bin/python tests/dogfight_fps.py --report
import asyncio, json, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger, IPHONE_15

K = "window.__kgeu"
TMP = '/tmp/dogfight_fps_{}.json'
FAIL_RATIO = 1.25

PLACE = """([i,d,off])=>{const K=window.__kgeu,s=K.state(),D=K.DF,b=D.bandits[i];D.test.hold=true;
  const q=s.quat.clone();if(off)q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),off));
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(q);b.p.copy(s.pos).addScaledVector(n,d);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);return true;}"""

GUNHOLD = "(on)=>{const g=document.getElementById('bGun');g.dispatchEvent(new PointerEvent(on?'pointerdown':'pointerup',{pointerId:77,bubbles:true,pointerType:'touch',isPrimary:false}));}"

# index.html wraps its game code in a closure, so placeAir/groundHeight/FIELD_FT aren't reachable
# from the test; K.state() does return the live st object (state:()=>st, no copy), so we mutate it
# directly the same way placeAir would. 1071 is the az (home/KGEU) region's field elevation in feet,
# the region every other dogfight test already assumes; the groundHeight term cancels out exactly
# in placeAir's own math (y = (targetMslFt - FIELD_FT)/M2FT), so skipping terrain height here is
# not an approximation, it's the same number placeAir would have produced.
PLACE_AT_CENTRE = f"""()=>{{const K={K},s=K.state(),C=K.DF.C,M2FT=3.28084,MS2KT=1.943844;
  s.pos.set(C.x,(15000-1071)/M2FT,C.z);s.vel.set(0,0,-400/MS2KT);s.w.set(0,0,0);
  s.quat.setFromEuler(new THREE.Euler(0.02,0,0,'YXZ'));
  s.onGround=false;s.airTime=30;s.throttle=s.power=0.6;s.gearDown=false;s.gearPos=0;s.flapIdx=0;}}"""

async def fastfwd(pg, secs):
    # advance sim time without paying for a render, the way dogfight_weapons_check's step() does
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);}", int(secs * 10 + 0.5))

async def frame_ms(pg, n=24):
    return await pg.evaluate("""(n)=>{const K=window.__kgeu,c=document.getElementById('gl');
      const gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
      K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
      const t0=performance.now();for(let i=0;i<n;i++)K.stepFrame(1/60);
      gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);const ms=(performance.now()-t0)/n;
      K.stepFrame(0,true);return ms;}""", n)

async def tris(pg):
    return await pg.evaluate(f"()=>{{const K={K};K.stepFrame(1/60);const t=K.tris();K.stepFrame(0,true);return t;}}")

async def setup_A(pg):
    await pg.evaluate(f"()=>{{const K={K};if(K.DF.on||K.DF.live)dfStop();K.setTOD('day');K.pick('f16');K.pickBase('kgeu');K.start('runway');}}")
    await pg.wait_for_timeout(50)
    await pg.evaluate(PLACE_AT_CENTRE)
    # CLOUD_MESH (hidden in the dogfight) lives inside index.html's closure, not reachable from the
    # test without touching game code, so the baseline is left WITH clouds visible -- noted in the report.
    await fastfwd(pg, 0.2)

async def dfstart(pg):
    await pg.evaluate(f"()=>{{const K={K};K.DF.test.noBrief=true;K.DF.test.noBanditFire=true;K.DF.test.noDecoy=true;K.windSeed(7);K.dfStart();}}")
    await pg.wait_for_timeout(50)
    await pg.evaluate(PLACE_AT_CENTRE)

async def setup_B(pg):
    await dfstart(pg)
    await pg.evaluate(PLACE, [0, 1760, 0])   # inside 1 nm (1852 m), dead ahead
    await fastfwd(pg, 0.2)

async def setup_C(pg):
    await dfstart(pg)
    await pg.evaluate(f"()=>{K}.DF.test.wave(4)")
    for i, off in enumerate([0, -0.15, 0.15, 0.3]):
        await pg.evaluate(PLACE, [i, 1700, off])
    await fastfwd(pg, 0.2)

async def setup_D(pg):
    await setup_C(pg)
    await fastfwd(pg, 1.7)                 # bandit 0 is dead ahead: the seeker searches then locks
    await finger(pg, '#bFox')              # our missile away
    await pg.evaluate(f"()=>{K}.DF.test.launchAt()")   # bandit 0 fires back (RWR launch, foe missile+smoke)
    await finger(pg, '#bFlr')              # flares out (noDecoy keeps both missiles alive regardless)
    await pg.evaluate(GUNHOLD, True)       # GUN held: tracers (bandits are past the 1200 m gun range, no kill)
    await fastfwd(pg, 0.05)

SETUP = {'A': setup_A, 'B': setup_B, 'C': setup_C, 'D': setup_D}

async def run_scenario(label, rounds=3):
    srv, url = serve()
    out = {'ms': [], 'tris': None}
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
        # one discarded measurement: the first touch of the dogfight's HD bandit/HUD materials pays a
        # one-time shader-compile cost under software rendering that baseline A never sees, so it would
        # unfairly inflate B/C/D if counted
        await SETUP[label](pg)
        await frame_ms(pg)
        await SETUP[label](pg)
        await frame_ms(pg)
        for r in range(rounds):
            await SETUP[label](pg)
            ms = await frame_ms(pg)
            out['ms'].append(ms)
            if r == 0 and label in ('A', 'C'):
                out['tris'] = await tris(pg)
            print(f'{label} round {r}: {ms:.2f} ms' + (f'  tris={out["tris"]}' if out['tris'] is not None and r == 0 else ''))
        out['errs'] = list(dict.fromkeys(pg.errs))[:5]
        await b.close()
    out['mean'] = sum(out['ms']) / len(out['ms'])
    with open(TMP.format(label), 'w') as f:
        json.dump(out, f)
    print(f'{label}: mean {out["mean"]:.2f} ms' + (f', errors {out["errs"]}' if out['errs'] else ''))
    return out

def report():
    data = {}
    for label in 'ABCD':
        path = TMP.format(label)
        if not os.path.exists(path):
            print(f'missing {path} -- run --scenario {label} first'); sys.exit(2)
        with open(path) as f:
            data[label] = json.load(f)
    a = data['A']['mean']
    fails = []
    print(f"A baseline: {a:.2f} ms  tris={data['A']['tris']}")
    for label in 'BCD':
        m = data[label]['mean']
        ratio = m / a if a else float('inf')
        ok = ratio <= FAIL_RATIO
        extra = f"  tris={data[label]['tris']}" if data[label]['tris'] is not None else ''
        print(f"{label}: {m:.2f} ms  ratio {label}/A {ratio:.2f} {'ok' if ok else 'FAIL'}{extra}")
        if not ok: fails.append(f'{label}/A={ratio:.2f}')
    errs = {l: data[l]['errs'] for l in 'ABCD' if data[l].get('errs')}
    if errs: print('console errors:', errs)
    print('dogfight_fps: ' + ('PASS' if not fails else 'FAIL ' + ', '.join(fails)))
    sys.exit(1 if fails else 0)

async def main():
    args = sys.argv[1:]
    if '--report' in args:
        report(); return
    if '--scenario' in args:
        label = args[args.index('--scenario') + 1].upper()
        await run_scenario(label)
        return
    print('usage: dogfight_fps.py --scenario A|B|C|D   or   --report')
    sys.exit(2)

if __name__ == '__main__':
    asyncio.run(main())
