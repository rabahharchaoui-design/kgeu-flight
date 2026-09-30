# One-off check for phone notes 0929, item 2: confirm the warm-up (which now also
# prewarms the far-cull PARKED/TRAFFIC models via farWarm, see WARM_STEPS in
# index.html) runs with no console 'warm' warnings while the menu is up, and that
# window.__kgeu.warm() reports done. iPhone landscape 844x390, dsf 2, mobile, touch.
# Test-only; does not touch game code.
# Run: .venv/bin/python tests/warm_console_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks, IGNORE
ok = Checks()
K = 'window.__kgeu'

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        ctx = await b.new_context(viewport=IPHONE_15, is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = await ctx.new_page()
        msgs = []
        pg.on('console', lambda m: msgs.append((m.type, m.text)))
        pg.on('pageerror', lambda e: msgs.append(('pageerror', str(e))))
        from harness import THREE
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
        await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        await pg.goto(url)
        await pg.wait_for_function(f'()=>{K}', timeout=30000)
        await pg.wait_for_timeout(15000)   # sit on the menu while warm-up runs

        warm = await pg.evaluate(f"()=>{K}.warm && {K}.warm()")
        menu_up = await pg.is_visible('#hFly')
        warn_msgs = [t for typ, t in msgs if 'warm' in t.lower()]

        ok('menu is up after 15 s', menu_up)
        ok('window.__kgeu.warm() reports warm-up done', bool(warm), warm)
        ok("no console messages mentioning 'warm'", not warn_msgs, warn_msgs[:5])
        errs = [t for typ, t in msgs if typ in ('error', 'pageerror') and not any(k in t for k in IGNORE)]
        ok('no console errors', not errs, errs[:5])

        await pg.close()
    sys.exit(ok.done('warm_console_check'))

if __name__ == '__main__':
    asyncio.run(main())
