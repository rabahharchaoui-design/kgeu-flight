# Throwaway same-build comparison: rAF frames over 6 s for the Cessna on the 3 nm final
# at KGEU (Arizona, day) versus RJTT, LFPG and SBRJ (day and night). All in the current
# build only -- not an A/B against baseline, just a relative same-session reference table.
# Usage: .venv/bin/python tests/region_fps_check.py
import asyncio, json, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

K = 'window.__kgeu'
BASE_STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}

SCENARIOS = [
    ('kgeu_day', 'az', 'day'),
    ('rjtt_day', 'rjtt', 'day'),
    ('rjtt_night', 'rjtt', 'night'),
    ('lfpg_day', 'lfpg', 'day'),
    ('lfpg_night', 'lfpg', 'night'),
    ('sbrj_day', 'sbrj', 'day'),
    ('sbrj_night', 'sbrj', 'night'),
]

async def fps(pg, seconds=6.0, warm=2.0):
    await pg.wait_for_timeout(int(warm * 1000))
    await pg.evaluate("""()=>{window.__stop=1;window.__f=0;setTimeout(()=>{window.__stop=0;
      const t=()=>{if(window.__stop)return;window.__f++;requestAnimationFrame(t);};requestAnimationFrame(t);},60);}""")
    await pg.wait_for_timeout(int(seconds * 1000) + 60)
    return await pg.evaluate("()=>{window.__stop=1;return window.__f;}") / seconds

async def run_one(b, url, region, tod):
    storage = dict(BASE_STORAGE)
    if region != 'az':
        storage['kgeuRegion'] = region
    pg = await page(b, url, vp=IPHONE_15, storage=storage)
    if region != 'az':
        await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=20000)
    await pg.evaluate(f"()=>{{{K}.setTOD('{tod}');{K}.pick('cessna');{K}.pickPos('final');{K}.start('final');}}")
    await pg.wait_for_timeout(1500)
    f = await fps(pg)
    errs = list(pg.errs)
    await pg.context.close()
    return f, errs

async def main():
    srv, url = serve()
    out = {}
    errs_all = []
    async with async_playwright() as p:
        b = await launch(p)
        for name, region, tod in SCENARIOS:
            f, errs = await run_one(b, url, region, tod)
            out[name] = f
            errs_all += [f'{name}: {e}' for e in errs]
            print(f'{name:12s} {f:.2f} fps')
        await b.close()
    print('\nscenario      fps')
    for name, _, _ in SCENARIOS:
        print(f'{name:12s} {out[name]:.2f}')
    if errs_all:
        print('page errors:', errs_all[:5])
    print(json.dumps(out))

if __name__ == '__main__':
    asyncio.run(main())
