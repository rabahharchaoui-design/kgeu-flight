# Throwaway: region switching and memory. Start in Arizona, then switch regions with real
# reloads through K.pickRegion(id) in the order rjtt, lfpg, sbrj, az, rjtt (5 switches), each
# time waiting for __kgeu and WORLD.ready (Arizona is ready at once), start a free flight and
# step 5 s, then record performance.memory.usedJSHeapSize after a window.gc() (chromium is
# launched with --js-flags=--expose-gc so window.gc exists). Checks: no page errors, no failed
# requests beyond the harness IGNORE list, and the heap after the 5th switch is under 1.5x the
# heap after the 1st switch.
# Usage: .venv/bin/python tests/world_switch_check.py
import asyncio, json, sys
from playwright.async_api import async_playwright
from harness import serve, page, IPHONE_15, IGNORE

K = 'window.__kgeu'
BASE_STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
ORDER = ['rjtt', 'lfpg', 'sbrj', 'az', 'rjtt']

async def launch_with_gc(p):
    return await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl',
        '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader',
        '--js-flags=--expose-gc', '--enable-precise-memory-info'])

async def wait_ready(pg, region):
    await pg.wait_for_function(f'()=>{K}', timeout=30000)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=20000)

async def measure_heap(pg):
    return await pg.evaluate("""async()=>{if(window.gc)window.gc();await new Promise(r=>setTimeout(r,80));
      return {heap: performance.memory?performance.memory.usedJSHeapSize:null, gcAvail: !!window.gc};}""")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch_with_gc(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE_STORAGE))
        pg.failed = []
        pg.on('requestfailed', lambda r: pg.failed.append(r.url + ' ' + (r.failure or '')) if not any(k in (r.failure or '') for k in IGNORE) else None)
        pg.on('response', lambda r: pg.failed.append(f'{r.status} {r.url}') if r.status >= 400 and 'fonts' not in r.url else None)

        await wait_ready(pg, 'az')
        readings = []
        for i, rid in enumerate(ORDER, 1):
            async with pg.expect_navigation(timeout=30000):
                await pg.evaluate(f"()=>{K}.pickRegion('{rid}')")
            await wait_ready(pg, rid)
            # re-register listeners after navigation reset them
            pg.failed = pg.failed if hasattr(pg, 'failed') else []
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.start('runway');}}")
            await pg.wait_for_timeout(5000)
            h = await measure_heap(pg)
            readings.append((i, rid, h['heap'], h['gcAvail']))
            print(f"switch {i} ({rid}): heap={h['heap']} gc_available={h['gcAvail']}")

        errs = list(pg.errs)
        failed = list(pg.failed)
        await b.close()

    print('\n--- summary ---')
    for i, rid, heap, gcav in readings:
        mb = f'{heap/1e6:.2f} MB' if heap is not None else 'n/a'
        print(f'  switch {i} -> {rid:4s} heap {mb}')
    ok_errs = not errs
    ok_failed = not failed
    heap0 = readings[0][2]
    heap4 = readings[4][2]
    ok_heap = True if heap0 is None or heap4 is None else heap4 < 1.5 * heap0
    print(f"  page errors: {'none' if ok_errs else errs[:5]}")
    print(f"  failed requests: {'none' if ok_failed else failed[:5]}")
    if heap0 is not None and heap4 is not None:
        print(f"  heap ratio (switch5/switch1): {heap4/heap0:.3f} (gate < 1.5)")
    else:
        print('  heap unavailable (performance.memory not exposed)')
    fails = []
    if not ok_errs: fails.append('page errors')
    if not ok_failed: fails.append('failed requests')
    if not ok_heap: fails.append('heap growth >= 1.5x')
    print('\nworld_switch_check: ' + ('all passed' if not fails else 'FAILED ' + ', '.join(fails)))
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
