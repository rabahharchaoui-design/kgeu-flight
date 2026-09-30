# One-off screenshot script for phone notes 0929, item 3 (map opens instantly, no
# flicker: pinned opening-view tiles, fmPrep builds ahead, mtEmpty skips out-of-data
# tiles, fmSize only resizes on real change, fmOpen draws once). Captures the very
# first composited frame after opening the full map in flight, the settled map a
# second later, and the map opened again after rotating to portrait. iPhone 15
# landscape 844x390 (and portrait 390x844), dsf 2, mobile, touch. Test/screenshot
# infra only; does not touch game code.
# Run: .venv/bin/python tests/item03_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item03')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'

async def shot(pg, name):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print('wrote', path)
    return path

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.wait_for_function(f"()=>{K}.warm()", timeout=30000)

        # in flight, short final into Glendale, cruising along
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final');}}")
        await pg.wait_for_timeout(2500)

        # open the map and grab the screenshot in the same turn as the open call so
        # it is the very first composited frame -- before any rAF gets to run.
        await pg.evaluate(f"()=>{K}.fmOpen()")
        await shot(pg, '01_open_first_frame.png')

        # the settled map, a second later, everything pumped
        await pg.wait_for_timeout(1000)
        await pg.evaluate(f"()=>{K}.fmFlush()")
        await shot(pg, '02_open_settled.png')
        await pg.evaluate(f"()=>{K}.fmClose()")
        await pg.wait_for_timeout(300)

        # rotate to portrait, then open the map there too
        await pg.set_viewport_size({'width': 390, 'height': 844})
        await pg.wait_for_timeout(1200)
        await pg.evaluate(f"()=>{K}.fmOpen()")
        await pg.wait_for_timeout(1000)
        await pg.evaluate(f"()=>{K}.fmFlush()")
        await shot(pg, '03_portrait_open.png')
        await pg.evaluate(f"()=>{K}.fmClose()")

        if pg.errs:
            print('console errors:', pg.errs[:5])
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        await pg.close()

if __name__ == '__main__':
    asyncio.run(main())
