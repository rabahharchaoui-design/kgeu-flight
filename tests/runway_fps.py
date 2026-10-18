# Runways item 9: frame rate on the runway and on final at the three Arizona airports, two builds back to
# back so machine drift cancels (headless software rendering: only the ratio means anything). The tier comes
# from PFS_TIER (kgeuTier in localStorage: low, medium, high); the harness's own auto tier is Low.
#   [PFS_TIER=medium] .venv/bin/python tests/runway_fps.py <base_root> <new_root> [rounds]
# Scenes: the Cessna at Glendale, the F-16 at Luke and the 737 at Sky Harbor, chase view by day, on the runway
# and on a 3 nm final. *_ms rows are wall time per held tick (sim + render) as in aircraft_fps.py.
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aircraft_fps import fps, frame_ms, serve, THREE

K = 'window.__kgeu'
FLOOR = 0.95          # item 9: no more than 5 percent slower than prerunways
SCENES = [('cessna', 'kgeu'), ('f16', 'luke'), ('b737', 'phx')]
TIER = os.environ.get('PFS_TIER', '')

async def run(b, url):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');"
                              + (f"localStorage.setItem('kgeuTier','{TIER}');" if TIER else ''))
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    out = {}
    for t, base in SCENES:
        await pg.evaluate(f"()=>{{{K}.setTOD('day');if({K}.setWX){{try{{{K}.setWX('clear');}}catch(e){{}}}}{K}.pick('{t}');{K}.pickBase('{base}');{K}.start('runway');let k=0;while({K}.camMode()!==0&&k++<5){K}.cycleCam();}}")
        await pg.wait_for_timeout(2500)
        out[f'{t}_{base}_runway'] = await fps(pg)
        out[f'{t}_{base}_runway_ms'] = await frame_ms(pg)
        await pg.evaluate(f"()=>{{{K}.start('final')}}"); await pg.wait_for_timeout(2500)
        out[f'{t}_{base}_final'] = await fps(pg)
        out[f'{t}_{base}_final_ms'] = await frame_ms(pg)
    await ctx.close()
    return out, errs

async def main():
    base, new = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    if len(sys.argv) > 4:   # a subset of the scenes by base (e.g. luke,phx), so two rounds fit one call
        keep = sys.argv[4].split(','); SCENES[:] = [s for s in SCENES if s[1] in keep]
    ub, un = serve(os.path.abspath(base)), serve(os.path.abspath(new))
    acc = {'base': [], 'new': []}; errs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        for r in range(rounds):
            for key, url in (('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub)):
                o, e = await run(b, url); acc[key].append(o); errs += e
        await b.close()
    med = lambda L: sorted(L)[len(L) // 2]
    B = {k: med([o[k] for o in acc['base']]) for k in acc['base'][0]}
    N = {k: med([o[k] for o in acc['new']]) for k in acc['new'][0]}
    print('tier', TIER or 'auto'); print('base', json.dumps(B)); print('new', json.dumps(N))
    bad = []
    for k in B:
        ratio = (B[k] / N[k]) if k.endswith('_ms') else (N[k] / B[k])   # ms: lower is better
        # the gate is on the tick times: the rAF counts at ~3 fps are quantised to a sixth of a frame (6 percent) over
        # the 6 s window and cannot resolve 5 percent, so they are printed for the record only
        gated = k.endswith('_ms')
        ok = ratio >= FLOOR or not gated
        print(f'  {"ok  " if ratio >= FLOOR else ("FAIL" if gated else "info")} {k}: base {B[k]:.2f} new {N[k]:.2f} ratio {ratio:.2f}')
        if not ok: bad.append(k)
    if errs: print('page errors:', errs[:5])
    print('runway_fps:', 'all passed' if not bad and not errs else 'FAILED ' + ' '.join(bad))
    sys.exit(1 if bad or errs else 0)

asyncio.run(main())
