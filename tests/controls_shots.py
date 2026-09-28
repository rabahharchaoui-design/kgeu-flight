# One-off screenshot script for PLAN item 3.0 (multi touch + right-hand button
# column). Not part of run_all.sh. Gets into a real flight past the menus using
# the same localStorage seeding + window.__kgeu API the other checks use, then
# screenshots the full page. Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/controls_shots.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, IPHONE_SE

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'controls')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'

async def enter(pg, skill, t, mode='final'):
    await pg.evaluate(f"()=>{{{K}.setSkill('{skill}');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('{mode}');}}")
    await pg.wait_for_timeout(2000)

async def shot(b, url, name, skill, t, vp=IPHONE_15, mode='final'):
    pg = await page(b, url, vp=vp, storage={'kgeuOnboard': skill, 'kgeuType': t, 'kgeuTut': '1', 'kgeuCoach': '3'})
    await enter(pg, skill, t, mode)
    await pg.screenshot(path=os.path.join(SHOTS, name))
    print('wrote', name)
    return pg

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        pg = await shot(b, url, 'rookie_cessna.png', 'rookie', 'cessna'); await pg.close()
        pg = await shot(b, url, 'rookie_reaper.png', 'rookie', 'reaper'); await pg.close()
        pg = await shot(b, url, 'pilot_cessna.png', 'pilot', 'cessna'); await pg.close()
        pg = await shot(b, url, 'pilot_f16.png', 'pilot', 'f16'); await pg.close()
        pg = await shot(b, url, 'pilot_c130.png', 'pilot', 'c130'); await pg.close()
        pg = await shot(b, url, 'pilot_mq9b.png', 'pilot', 'mq9b'); await pg.close()

        # pilot_c130_stick: finger held on the stick zone, second finger holding BRAKE, via CDP touch
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuType': 'c130', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await enter(pg, 'pilot', 'c130')
        cdp = await pg.context.new_cdp_session(pg)
        z = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}")
        br = await pg.evaluate("()=>{const r=document.getElementById('bBrake').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}")
        f1 = (z[0] + 80, z[1])
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [
            {'x': z[0], 'y': z[1], 'id': 1, 'radiusX': 4, 'radiusY': 4, 'force': 1}]})
        await pg.wait_for_timeout(60)
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [
            {'x': f1[0], 'y': f1[1], 'id': 1, 'radiusX': 4, 'radiusY': 4, 'force': 1}]})
        await pg.wait_for_timeout(60)
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [
            {'x': f1[0], 'y': f1[1], 'id': 1, 'radiusX': 4, 'radiusY': 4, 'force': 1},
            {'x': br[0], 'y': br[1], 'id': 2, 'radiusX': 4, 'radiusY': 4, 'force': 1}]})
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(SHOTS, 'pilot_c130_stick.png'))
        print('wrote pilot_c130_stick.png')
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': [
            {'x': f1[0], 'y': f1[1], 'id': 1, 'radiusX': 4, 'radiusY': 4, 'force': 1}]})
        await pg.close()

        # pilot_c130_airdrop: C-130 airdrop mission running, DROP button visible
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuType': 'c130', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.pick('c130');{K}.start('drop');}}")
        await pg.wait_for_timeout(2000)
        await pg.screenshot(path=os.path.join(SHOTS, 'pilot_c130_airdrop.png'))
        print('wrote pilot_c130_airdrop.png')
        await pg.close()

        # pilot_c130_se at 667x375
        pg = await shot(b, url, 'pilot_c130_se.png', 'pilot', 'c130', vp=IPHONE_SE); await pg.close()

        await b.close()

asyncio.run(main())
