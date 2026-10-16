# Weather item 3 frame cost: a single build table, not an A/B. Headless software rendering runs at a
# few fps and drifts between machines, so this compares each weather type against this same run's own
# clear leg rather than an absolute number. Modelled on weather_fps.py and graphics_fps.py (same fps()
# and frame_ms() from aircraft_fps.py, same serve/launch/open_page and fly() from graphics_shots.py) but
# one root only: a feature may cost at most 25% over the clear baseline (storm and the haboob, the two
# busiest types, 35%). iPhone landscape, 2x.
#   .venv/bin/python tests/weather_type_fps.py <root> [types] [--cockpit]
# For each type (default: clear,scattered,overcast,rain,storm,fog,gusty,haboob) the Cessna on 3 mile
# final to KGEU by day (fly('cessna','day','final')), then setWX(<type>), a 2.5 s settle (the haboob
# also haboobJump(500) if that hook exists, so the wall is in view), fps and frame_ms in the chase view,
# and with --cockpit also after one cycleCam(). clear is always measured first as the reference leg even
# when not asked for, so a batched call (e.g. rain,storm,fog) still has a same-run baseline to ratio against.
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aircraft_fps import fps, frame_ms
from graphics_shots import serve, launch, open_page, fly, K

ALL_TYPES = ['clear', 'scattered', 'overcast', 'rain', 'storm', 'fog', 'gusty', 'haboob']
FLOOR = {'storm': 1.35, 'haboob': 1.35}   # ms ratio to clear may not exceed this; every other type 1.25

def wx(t):
    s = f"{K}.setWX('{t}');"
    if t == 'haboob': s += f"if({K}.haboobJump){K}.haboobJump(500);"
    return s

async def js(pg, code):
    await pg.evaluate("(c)=>{(new Function(c))();}", code)

async def leg(pg, t, cockpit):
    await js(pg, fly('cessna', 'day', 'final'))
    await js(pg, wx(t))
    await pg.wait_for_timeout(2500)
    out = {'fps': await fps(pg), 'ms': await frame_ms(pg)}
    if cockpit:
        await js(pg, f"{K}.cycleCam();")
        await pg.wait_for_timeout(600)
        out['cockpit_fps'] = await fps(pg)
        out['cockpit_ms'] = await frame_ms(pg)
    return out

async def main():
    root = sys.argv[1]
    rest = sys.argv[2:]
    cockpit = '--cockpit' in rest
    pos = [a for a in rest if not a.startswith('--')]
    types = pos[0].split(',') if pos else list(ALL_TYPES)
    order = (['clear'] if 'clear' not in types else []) + types   # clear first, always, as the baseline leg
    url = serve(os.path.abspath(root))
    results = {}
    async with async_playwright() as p:
        b = await launch(p)
        ctx, pg = await open_page(b, url)
        for t in order:
            out = await leg(pg, t, cockpit)
            results[t] = out
            print(t, json.dumps({k: round(v, 2) for k, v in out.items()}), flush=True)
        errs = list(pg.errs)
        await ctx.close(); await b.close()

    base_ms, base_cms = results['clear']['ms'], results['clear'].get('cockpit_ms')
    fails = []
    print(f"{'type':10s} {'fps':>6s} {'ms':>7s} {'ratio':>6s}" + ('  cpit_fps  cpit_ms  cpit_ratio' if cockpit else ''))
    for t in order:
        o = results[t]
        ratio = o['ms'] / base_ms if base_ms else 1.0
        floor = FLOOR.get(t, 1.25)
        ok = ratio <= floor
        line = f"{t:10s} {o['fps']:6.2f} {o['ms']:7.2f} {ratio:6.2f}"
        if cockpit:
            cratio = o['cockpit_ms'] / base_cms if base_cms else 1.0
            ok = ok and cratio <= floor
            line += f"  {o['cockpit_fps']:8.2f} {o['cockpit_ms']:7.2f} {cratio:10.2f}"
        print(('  ok  ' if ok else '  FAIL') + ' ' + line)
        if not ok: fails.append(t)
    if errs:
        from collections import Counter
        print('page errors:', dict(Counter(errs)))
    print('weather_type_fps: ' + ('all passed' if not fails and not errs else 'FAILED ' + ', '.join(fails)))
    sys.exit(1 if fails or errs else 0)

if __name__ == "__main__":
    asyncio.run(main())
