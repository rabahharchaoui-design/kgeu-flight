# Screenshots of every place the Easy / Hard mode shows. iPhone landscape.
# Run: .venv/bin/python tests/modes_shots.py <subdir>
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, IPHONE_SE, ROOT
K = "window.__kgeu"
OUT = os.path.join(ROOT, 'overnight-screenshots', 'modes', sys.argv[1] if len(sys.argv) > 1 else 'after')
async def main():
    os.makedirs(OUT, exist_ok=True); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp, tag in ((IPHONE_15, '844'), (IPHONE_SE, '667')):
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
            await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(600); await pg.screenshot(path=f'{OUT}/fly_{tag}.png')
            await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(400); await pg.screenshot(path=f'{OUT}/settings_{tag}.png')
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}"); await pg.wait_for_timeout(1200)
            await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(600); await pg.screenshot(path=f'{OUT}/pause_{tag}.png')
            await pg.context.close()
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuTut': '1'})
        await pg.wait_for_timeout(600); await pg.screenshot(path=f'{OUT}/funnel_844.png')
        await b.close()
asyncio.run(main())
