# One-off screenshot script for phone notes 0929, item 19 (the pause sheet as the one
# hub: merged Restart/Apply, the Missions/Arcade/School/Boards/Menu nav row, quick tiles
# for Sound/Invert/Stick, and the 568x320 layout fix). Screenshots at four sizes, in free
# flight and inside a mission. Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item19_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item19')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'
SIZES = [
    (568, 320),
    (667, 375),
    (844, 390),
    (932, 430),
]

async def snap(pg, name):
    await pg.wait_for_timeout(150)
    await pg.screenshot(path=os.path.join(SHOTS, name))
    print('wrote', name)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for w, h in SIZES:
            vp = {'width': w, 'height': h}
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.wait_for_function(f"()=>{K}.warm()", timeout=30000)

            # free flight -> pause sheet
            await pg.evaluate(f"()=>{{{K}.openMenu();{K}.pick('cessna',1);{K}.start('runway');}}")
            await pg.wait_for_timeout(300)
            await finger(pg, '#bPause')
            await pg.wait_for_function("()=>document.getElementById('pauseOv').classList.contains('on')", timeout=5000)
            await snap(pg, f'{w}x{h}_freeflight.png')
            await finger(pg, '#pResume')
            await pg.wait_for_timeout(150)

            # a mission -> pause sheet
            await pg.evaluate(f"(s)=>{{{K}.openMenu();{K}.nav(s);}}", 'sMis')
            await pg.wait_for_timeout(250)
            await finger(pg, '#misCards .mcard[data-m=daily]')
            await pg.wait_for_timeout(300)
            await finger(pg, '#bPause')
            await pg.wait_for_function("()=>document.getElementById('pauseOv').classList.contains('on')", timeout=5000)
            await snap(pg, f'{w}x{h}_mission.png')

            await pg.close()

if __name__ == '__main__':
    asyncio.run(main())
