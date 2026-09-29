# Lag profile (phone notes 0929, item 2): the same scripted events on two builds, CPU throttled
# 4x (Chrome's CDP Emulation.setCPUThrottlingRate) on an iPhone landscape page (844x390, dsf 2),
# rounds alternating base/new so machine drift cancels. Math.random is seeded, so both builds
# fly the same thing.
#   .venv/bin/python tests/lag_profile.py <base_root> <new_root> [rounds] [--only base|new]
# Events: the Luke to Glendale dash (F-16, mission HUD, radio) and the 5 mile landing challenge
# (Cessna, arcade HUD), each with an explosion (fireball, smoke column, debris, fire) and a
# radio line with its subtitle going. The loop is held; each step runs two ticks of 1/60 s:
#   sim  = a tick with the render skipped: sim, HUD and DOM work in JS
#   tick = a full tick: the same plus three.js building and submitting the frame (CPU side)
# then a 1 px readback outside the timers, so the GPU never backs up into the next tick.
# Headless software GL: only the ratio between the builds means anything. With --only a
# single build is measured (one round per Bash call when a full run is too long).
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aircraft_fps import serve, THREE

K = 'window.__kgeu'
STEPS = 60
SEED = """(()=>{let s=12345;Math.random=()=>{s=(s*16807)%2147483647;return (s-1)/2147483646;};})();
localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');"""
EVENTS = {
    'dash':    ('sMis', '#misCards .mcard[data-m=dash]'),
    'landing': ('sArc', '#arcCards .mcard[data-m=landing]'),
}

MEASURE = """(n)=>{const K=window.__kgeu,c=document.getElementById('gl');
  const gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
  const s=K.state();K.explode(s.pos.x+320,s.pos.y,s.pos.z-260,{scale:1,debris:6,fireSec:30,secondary:2});
  K.say('Tower','Viper one, runway two one, cleared for takeoff, wind two four zero at eight');
  for(let i=0;i<6;i++){K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);}
  const sim=[],tick=[];let calls=0;const R=K.R3&&K.R3().renderer;
  for(let i=0;i<n;i++){
    let t0=performance.now();K.stepFrame(1/60,false,true);sim.push(performance.now()-t0);
    t0=performance.now();K.stepFrame(1/60);tick.push(performance.now()-t0);
    if(R)calls+=R.info.render.calls;
    gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);}
  K.stepFrame(0,true);
  return {sim:sim,tick:tick,calls:R?calls/n:null,running:K.running()};}"""

def stats(a):
    a = sorted(a); return sum(a) / len(a), a[min(len(a) - 1, int(len(a) * 0.95))]

async def run(b, url):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script(SEED)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}&&(!{K}.warm||{K}.warm())', timeout=90000); await pg.wait_for_timeout(1500)
    cdp = await ctx.new_cdp_session(pg)
    out = {}
    for name, (scr, sel) in EVENTS.items():
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
        await pg.evaluate(f"(a)=>{{{K}.openMenu();{K}.nav(a[0]);document.querySelector(a[1]).click();}}", [scr, sel])
        await pg.wait_for_timeout(1200)
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        r = await pg.evaluate(MEASURE, STEPS)
        if not r['running']: errs.append(f'{name}: not running')
        out[name] = r
    await ctx.close()
    return out, errs

async def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    if only: args = [a for a in args if a != only]
    base, new = args[0], args[1]
    rounds = int(args[2]) if len(args) > 2 else 1
    urls = {'base': serve(os.path.abspath(base)), 'new': serve(os.path.abspath(new))}
    acc = {'base': {}, 'new': {}}; errs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        for r in range(rounds):
            order = ['base', 'new'] if r % 2 == 0 else ['new', 'base']
            for label in order:
                if only and label != only: continue
                o, e = await run(b, urls[label]); errs += [f'{label}: {x}' for x in e]
                for ev, d in o.items():
                    A = acc[label].setdefault(ev, {'sim': [], 'tick': [], 'calls': []})
                    A['sim'] += d['sim']; A['tick'] += d['tick']
                    if d['calls'] is not None: A['calls'].append(d['calls'])
                    sm, tm = stats(d['sim']), stats(d['tick'])
                    print(f"{label} {ev}: sim mean {sm[0]:.2f} p95 {sm[1]:.2f}  tick mean {tm[0]:.2f} p95 {tm[1]:.2f} ms"
                          + (f"  draw calls {d['calls']:.0f}" if d['calls'] is not None else ''), flush=True)
        await b.close()
    print('\nCPU x4, ms per tick        base mean / p95      new mean / p95     new/base (mean)')
    for ev in EVENTS:
        for k in ('sim', 'tick'):
            B, N = acc['base'].get(ev, {}).get(k), acc['new'].get(ev, {}).get(k)
            bs = stats(B) if B else None; ns = stats(N) if N else None
            f = lambda s: f'{s[0]:7.2f} / {s[1]:7.2f}' if s else '      - /       -'
            ratio = f'{ns[0] / bs[0]:.2f}' if bs and ns else '-'
            print(f'  {ev:8} {k:5}          {f(bs)}    {f(ns)}    {ratio}')
    if errs: print('page errors:', errs[:5])
    print('lag_profile: done' + (' (with page errors)' if errs else ''))
    sys.exit(1 if errs else 0)

if __name__ == '__main__':
    asyncio.run(main())
