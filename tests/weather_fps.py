# Frame rate for the weather session: the weather_shots.py scenes on two builds, back to back and
# alternating, so machine drift cancels. Headless software rendering runs at a few fps; only the ratio
# between the builds means anything. iPhone landscape, 2x. Only hooks the preweather build has.
#   .venv/bin/python tests/weather_fps.py <base_root> <new_root> [rounds] [row,row,...]   (the rows' keys; default all)
# Scenes (see weather_shots.py SCENES): scattered cumulus in the air and on final, the cockpit view,
# monsoon in the air and seen from altitude, monsoon at sunset on final, scattered at night, clear high
# wisps, a fly-through of a scattered cloud base, the haboob on final and at the wall.
# *_ms rows are wall time per held tick (sim + render, synced by a readback), as in aircraft_fps.py.
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aircraft_fps import fps, frame_ms
from weather_shots import serve, launch, open_page, setup

FLOOR = 0.90          # a scene may lose at most 10% against the base build
ROWS = [('scattered_air', 'scattered_day_air_chase', True),
        ('scattered_air_cockpit', 'scattered_day_air_cockpit', True),
        ('scattered_final', 'scattered_day_final_chase', True),
        ('monsoon_air', 'monsoon_day_air_chase', True),
        ('monsoon_high', 'monsoon_day_high_chase', True),
        ('monsoon_sunset_final', 'monsoon_sunset_final_chase', True),
        ('night_air', 'scattered_night_air_chase', True),
        ('clear_air', 'clear_day_air_chase', True),
        ('through', 'scattered_day_through', True),
        ('haboob_final', 'haboob_final_chase', True),
        ('haboob_wall', 'haboob_wall_chase', True)]

async def run(b, url):
    ctx, pg = await open_page(b, url)
    out = {}
    for key, scene, ms in ROWS:
        await setup(pg, scene)
        out[key] = await fps(pg)
        if ms: out[key + '_ms'] = await frame_ms(pg)
    errs = list(pg.errs)
    await ctx.close()
    return out, errs

async def main():
    base, new = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    if len(sys.argv) > 4:   # a subset of the rows, so a long A/B can be run in batches
        keep = sys.argv[4].split(','); ROWS[:] = [r for r in ROWS if r[0] in keep]
    ub, un = serve(os.path.abspath(base)), serve(os.path.abspath(new))
    acc = {'base': [], 'new': []}; errs = []
    async with async_playwright() as p:
        b = await launch(p)
        for r in range(rounds):
            for label, url in (('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub)):
                o, e = await run(b, url); acc[label].append(o); errs += [f'{label}: {x}' for x in e]
                print(label, json.dumps({k: round(v, 2) for k, v in o.items()}), flush=True)
        await b.close()
    mean = lambda L, k: sum(x[k] for x in L) / len(L)
    fails = []
    for k in acc['base'][0]:
        bb, nn = mean(acc['base'], k), mean(acc['new'], k)
        r = (bb / nn if nn else 1) if k.endswith('_ms') else (nn / bb if bb else 1)   # >1 is faster either way
        ok = r >= FLOOR
        print(f"  {'ok  ' if ok else 'FAIL'} {k}: base {bb:.2f} new {nn:.2f} ratio {r:.2f}")
        if not ok: fails.append(k)
    if errs:
        from collections import Counter
        print('page errors:', dict(Counter(errs)))
    print('weather_fps: ' + ('all passed' if not fails and not [e for e in errs if e.startswith('new')] else 'FAILED ' + ', '.join(fails)))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    asyncio.run(main())
