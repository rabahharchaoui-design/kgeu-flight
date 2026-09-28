# Feature 10: the splash. Icon on sand with the title and a thin loading bar, then a
# fade into the home screen. Run: .venv/bin/python tests/splash_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, THREE, Checks
ok = Checks()
async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        ctx = await b.new_context(viewport={'width': 667, 'height': 375}, is_mobile=True, has_touch=True, device_scale_factor=2)
        await ctx.add_init_script("localStorage.setItem('kgeuOnboard','pilot')")
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        # hold three.js back a moment so the splash is caught while loading
        async def slow(r):
            await asyncio.sleep(1.2); await r.fulfill(body=THREE, content_type='application/javascript')
        await pg.route('**/three.min.js', slow)
        await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await pg.goto(url, wait_until='commit'); await pg.wait_for_timeout(500)
        s = await pg.evaluate("""()=>{const s=document.getElementById('splash');if(!s)return null;const cs=getComputedStyle(s),i=s.querySelector('img');
          return {vis:cs.display!=='none'&&cs.opacity==='1',bg:cs.backgroundColor,icon:i&&i.getAttribute('src'),title:s.querySelector('.spTitle').textContent,bar:!!s.querySelector('.spBar i'),
            cx:(()=>{const r=i.getBoundingClientRect();return Math.round(r.x+r.width/2)})()}}""")
        ok('splash shows while the game loads', s and s['vis'], s)
        ok('icon centred on sand, with the title and a loading bar',
           s and s['bg'] == 'rgb(246, 193, 119)' and s['icon'].endswith('icon-512.png') and s['title'] == 'Pocket Flight Sim' and s['bar'] and abs(s['cx'] - 333) < 3, s)
        await pg.wait_for_function("()=>document.getElementById('splash').classList.contains('done')", timeout=30000)
        op = await pg.evaluate("()=>getComputedStyle(document.getElementById('splash')).transitionDuration")
        ok('it fades rather than cuts', op != '0s', op)
        await pg.wait_for_function("()=>document.getElementById('splash').classList.contains('gone')", timeout=5000)
        ok('then the home screen is showing', await pg.is_visible('#hFly'))
        ok('no page errors', not errs, errs[:3])
        await b.close()
    sys.exit(ok.done('splash_check'))
asyncio.run(main())
