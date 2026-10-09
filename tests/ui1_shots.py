# ui1 before / after screenshots: every menu screen, the boards (mocked Worker, 30 rows, you at #24) and the pause sheet.
#   .venv/bin/python tests/ui1_shots.py <tag> [--size WxH] [--root DIR]   -> overnight-screenshots/ui1/<tag>_<screen>_<WxH>.png
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness
from harness import launch, page, IPHONE_15
from ui1_mock import Mock
K = 'window.__kgeu'
TAG = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'shot'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'ui1')
SIZES = [IPHONE_15, {'width': 568, 'height': 320}]
if '--size' in sys.argv: w, h = sys.argv[sys.argv.index('--size') + 1].split('x'); SIZES = [{'width': int(w), 'height': int(h)}]
if '--root' in sys.argv: harness.ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])


async def shot(pg, name, vp):
    await pg.wait_for_timeout(500)
    await pg.screenshot(path=os.path.join(OUT, f'{TAG}_{name}_{vp["width"]}x{vp["height"]}.png'))


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = harness.serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in SIZES:
            m = Mock()
            st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuLessons': '{"first":"A"}'}
            st.update(m.storage())
            pg = await page(b, url, vp=vp, storage=st, pre=m.install)
            await pg.wait_for_timeout(800)
            scrs = await pg.evaluate("()=>[...document.querySelectorAll('#menu .scr')].map(e=>e.id)")
            for scr in scrs:
                if scr in ('sHelp', 'sCredits'): continue
                await pg.evaluate(f"(s)=>{{const K={K};K.openMenu();(K.tabGo||K.nav)(s)}}", scr)
                await shot(pg, scr, vp)
            await pg.evaluate(f"()=>{{const K={K};K.openMenu();K.LB.lbOpen('df:score:hard')}}"); await shot(pg, 'sLb_df', vp)
            await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}"); await pg.wait_for_timeout(600)
            await pg.evaluate(f"()=>{K}.togglePause()"); await shot(pg, 'pause', vp)
            await pg.context.close()
        await b.close()
    print(OUT)

asyncio.run(main())
