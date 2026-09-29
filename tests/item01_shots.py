# One-off screenshot script for phone notes 0929, item 1 (controls/HUD vanish at event
# start). Takes the first frame after a real tap starts: a mission, an arcade game, a
# flight school lesson, and after pause -> Restart. iPhone landscape 844x390, dsf 2,
# mobile, touch. Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item01_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, finger

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item01')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'

async def snap(pg, name):
    await pg.wait_for_timeout(60)  # first frame after the tap
    await pg.screenshot(path=os.path.join(SHOTS, name))
    print('wrote', name)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.wait_for_function(f"()=>{K}.warm()", timeout=30000)

        # 1. a mission (daily), started by a real tap from the menu
        await pg.evaluate(f"(s)=>{{{K}.openMenu();{K}.nav(s);}}", 'sMis')
        await pg.wait_for_timeout(250)
        await finger(pg, '#misCards .mcard[data-m=daily]')
        await snap(pg, '01_mission.png')

        # 2. an arcade game (landing), started by a real tap from the menu
        await pg.evaluate(f"(s)=>{{{K}.openMenu();{K}.nav(s);}}", 'sArc')
        await pg.wait_for_timeout(250)
        await finger(pg, '#arcCards .mcard[data-m=landing]')
        await snap(pg, '02_arcade.png')

        # 3. a flight school lesson (first), started by a real tap from the menu
        await pg.evaluate(f"(s)=>{{{K}.openMenu();{K}.nav(s);}}", 'sSchool')
        await pg.wait_for_timeout(250)
        await finger(pg, '#school .lrow[data-l=first]')
        await snap(pg, '03_school.png')

        # 4. pause -> Restart, back into a free flight
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.pick('cessna',1);{K}.start('runway');}}")
        await pg.wait_for_timeout(300)
        await finger(pg, '#bPause')
        await pg.wait_for_function("()=>document.getElementById('pauseOv').classList.contains('on')", timeout=5000)
        await finger(pg, '#pRestart')
        await snap(pg, '04_pause_restart.png')

        await pg.close()

if __name__ == '__main__':
    asyncio.run(main())
