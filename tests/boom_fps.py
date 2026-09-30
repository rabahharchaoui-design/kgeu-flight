# Explosion cost (phone notes 0929, item 15): the frame cost of the cinematic explosion
# against the same scene with nothing going off, on this build and on the base build, with
# the CPU throttled 4x through CDP. iPhone landscape 844x390 at 2x, F-16 parked on the
# Glendale runway in the chase view, a C-130 sized burst (scale 2.6, three secondaries,
# 20 debris pieces, a burning wreck) 180 m ahead. Per tick over the 3 s after it goes off:
#   js  = wall time of the tick (sim + three.js draw submission), no readback
#   ms  = the same tick synced with a 1 px readback, so the software rasteriser's fill is in
# and the draw call count. Two control and two explosion windows, interleaved (the effect is
# cleared between), so machine drift cancels. Asserts on the new build: the extra js is under
# 5 ms mean and no tick spikes more than 5 ms over the no-explosion p95; the extra full-frame
# ms (median) is no more than 5 ms over what the base build's explosion costs, or over 0 when
# the base reads negative (software GL fill is nothing like the phone's, and machine load
# moves a 350 ms frame by more than the effect; only the difference between the two effects
# means anything), and the p90 of the explosion ticks after the first is likewise within 5 ms
# of the base's (the first tick of a window is the rasteriser building its pipelines, the same
# on both builds); the extra draw calls are at most 8 (the quad layer, the debris mesh, four
# decals). Per-tick series and the raw max spikes go to tests/boom_fps.json.
# Headless software GL runs at a few fps, and another test on the machine skews the timing;
# treat a pure timing miss as suspect and run it again.
#   .venv/bin/python tests/boom_fps.py [<base_root>] [--commit 8ee48e7] [--ticks 90]
# Without <base_root> a scratch worktree of --commit is made and removed afterwards.
import asyncio, json, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, IPHONE_15, Checks
from aircraft_fps import serve as serve_root

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
K = 'window.__kgeu'
ok = Checks()
args = [a for a in sys.argv[1:] if not a.startswith('--')]
COMMIT = sys.argv[sys.argv.index('--commit') + 1] if '--commit' in sys.argv else '8ee48e7'
TICKS = int(sys.argv[sys.argv.index('--ticks') + 1]) if '--ticks' in sys.argv else 90
DT = 1 / 30

TICK = """([n,dt,boom])=>{const K=window.__kgeu,c=document.getElementById('gl'),gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
  const js=[],ms=[],calls=[];
  if(boom){const s=K.state(),f=new THREE.Vector3(0,0,-1).applyQuaternion(s.quat),x=s.pos.x+f.x*180,z=s.pos.z+f.z*180;
    K.explode(x,K.groundHeight(x,z),z,{scale:2.6,secondary:3,debris:20,fireSec:90,smokeSec:90});}
  for(let i=0;i<n;i++){const t0=performance.now();K.stepFrame(dt);const t1=performance.now();
    gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);const t2=performance.now();
    js.push(t1-t0);ms.push(t2-t0);calls.push(K.drawCalls?K.drawCalls():-1);}
  return {js:js,ms:ms,calls:calls};}"""

def p95(v, q=0.95): s = sorted(v); return s[min(len(s) - 1, int(len(s) * q))]
def mean(v): return sum(v) / len(v)
def median(v): s = sorted(v); return s[len(s) // 2]

async def run(b, url, label):
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
    cdp = await pg.context.new_cdp_session(pg)
    await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
    await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);}}")
    try: await pg.wait_for_function(f"()=>{K}.warm()", timeout=120000)
    except Exception: print(f'  {label}: warm-up did not finish, measuring anyway')
    await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('runway');while({K}.camMode()!==0){K}.cycleCam();}}")
    await pg.evaluate("([n,dt])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt);}", [30, DT])   # settle the camera
    ctrl = {'js': [], 'ms': [], 'calls': []}; boom = {'js': [], 'ms': [], 'calls': []}; fx = None
    for w in range(2):
        for k, d in (('ctrl', ctrl), ('boom', boom)):
            r = await pg.evaluate(TICK, [TICKS, DT, k == 'boom'])
            for f in d: d[f] += r[f]
            if k == 'boom':
                fx = await pg.evaluate(f"()=>{{const f={K}.fx();return {{active:f.active,sprites:f.sprites,quads:f.quads}}}}")
                await pg.evaluate(f"()=>{{if({K}.fxReset){K}.fxReset();else {K}.fxClear();}}")
                await pg.evaluate("([n,dt])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt);}", [10, DT])
    await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
    errs = list(pg.errs)
    await pg.context.close()
    late = [v for i, v in enumerate(boom['ms']) if i % TICKS > 0]
    r = {'js_ctrl': mean(ctrl['js']), 'js_boom': mean(boom['js']), 'js_p95_ctrl': p95(ctrl['js']), 'js_max_boom': max(boom['js']),
         'ms_ctrl': median(ctrl['ms']), 'ms_boom': median(boom['ms']), 'ms_p95_ctrl': p95(ctrl['ms']), 'ms_max_boom': max(boom['ms']), 'ms_p90_boom': p95(late, 0.9), 'ms_p90_ctrl': p95(ctrl['ms'], 0.9),
         'calls_ctrl': max(ctrl['calls']), 'calls_boom': max(boom['calls']), 'fx': fx, 'errs': errs, 'series': {'ctrl': ctrl, 'boom': boom}}
    r['js_extra'] = r['js_boom'] - r['js_ctrl']; r['js_spike'] = r['js_max_boom'] - r['js_p95_ctrl']
    r['ms_extra'] = r['ms_boom'] - r['ms_ctrl']; r['ms_spike'] = r['ms_max_boom'] - r['ms_p95_ctrl']; r['ms_p90_extra'] = r['ms_p90_boom'] - r['ms_p90_ctrl']
    top = sorted(range(len(boom['ms'])), key=lambda i: -boom['ms'][i])[:3]
    print(f"  {label}: js {r['js_ctrl']:.1f} -> {r['js_boom']:.1f} ms (extra {r['js_extra']:+.1f}, spike {r['js_spike']:+.1f} over p95)  "
          f"frame median {r['ms_ctrl']:.0f} -> {r['ms_boom']:.0f} ms (extra {r['ms_extra']:+.0f}, p90 extra {r['ms_p90_extra']:+.0f}, max spike {r['ms_spike']:+.0f} at ticks {[(i % TICKS, round(boom['ms'][i])) for i in top]})  "
          f"draw calls {r['calls_ctrl']} -> {r['calls_boom']}  fx {fx}")
    return r

async def main():
    base_root = args[0] if args else None; tmp = None
    if not base_root:
        tmp = tempfile.mkdtemp(prefix='kgeu-base-')
        subprocess.run(['git', 'worktree', 'add', '--detach', tmp, COMMIT], cwd=ROOT, check=True, capture_output=True)
        base_root = tmp
    try:
        srv, url_new = serve()
        url_base = serve_root(os.path.abspath(base_root))
        async with async_playwright() as p:
            b = await launch(p)
            new = await run(b, url_new, 'new ')
            base = await run(b, url_base, 'base')
            await b.close()
        srv.shutdown()
    finally:
        if tmp: subprocess.run(['git', 'worktree', 'remove', '--force', tmp], cwd=ROOT, capture_output=True)
    ok('new: extra JS per tick under 5 ms mean (4x CPU throttle)', new['js_extra'] < 5, f"{new['js_extra']:+.2f} ms (base {base['js_extra']:+.2f})")
    ok('new: no JS spike over 5 ms above the no-explosion p95', new['js_spike'] < 5, f"{new['js_spike']:+.2f} ms (base {base['js_spike']:+.2f})")
    ok('new: extra full-frame ms (median) within 5 ms of the base explosion', new['ms_extra'] <= max(base['ms_extra'], 0) + 5, f"new {new['ms_extra']:+.1f} base {base['ms_extra']:+.1f}")
    ok('new: full-frame p90 (after the first tick) within 5 ms of the base explosion', new['ms_p90_extra'] <= max(base['ms_p90_extra'], 0) + 5, f"new {new['ms_p90_extra']:+.1f} base {base['ms_p90_extra']:+.1f} (max spikes new {new['ms_spike']:+.0f} base {base['ms_spike']:+.0f})")
    ok('new: at most 8 extra draw calls', 0 <= new['calls_boom'] - new['calls_ctrl'] <= 8, f"{new['calls_ctrl']} -> {new['calls_boom']} (base {base['calls_ctrl']} -> {base['calls_boom']})")
    ok('new: the explosion ran', new['fx']['active'] >= 1, new['fx'])
    ok('no page errors', not new['errs'], new['errs'][:3])
    out = os.path.join(ROOT, 'tests', 'boom_fps.json')
    json.dump({'new': new, 'base': base, 'ticks': TICKS, 'commit': COMMIT}, open(out, 'w'), indent=1)
    sys.exit(ok.done('boom_fps'))

asyncio.run(main())
