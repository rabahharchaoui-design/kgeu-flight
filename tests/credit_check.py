# Feature 12: creator credit on the splash and at the bottom of Settings.
# Run: .venv/bin/python tests/credit_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, THREE, Checks, finger
ok = Checks()
URL_YT = 'https://www.youtube.com/@OhRabah'
async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # on the splash, caught while loading
        ctx = await b.new_context(viewport={'width': 667, 'height': 375}, is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        async def slow(r):
            await asyncio.sleep(1.0); await r.fulfill(body=THREE, content_type='application/javascript')
        await pg.route('**/three.min.js', slow); await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await pg.goto(url, wait_until='commit'); await pg.wait_for_timeout(400)
        c = await pg.evaluate("""()=>{const a=document.querySelector('#splash .credit');if(!a)return null;const p=a.querySelectorAll('svg path');
          return {href:a.href,target:a.target,rel:a.rel,text:a.textContent.trim(),red:p[0].getAttribute('fill'),tri:p[1].getAttribute('fill'),h:a.getBoundingClientRect().height}}""")
        ok('splash credit reads Made by @OhRabah with the red play button',
           c and c['text'] == 'Made by @OhRabah' and c['red'].upper() == '#FF0000' and c['tri'].upper() == '#FFFFFF', c)
        ok('it opens the channel in a new tab', c and c['href'] == URL_YT and c['target'] == '_blank' and 'noopener' in c['rel'], c)
        await ctx.close()
        # at the bottom of Settings, and a real tap opens a new tab
        pg = await page(b, url, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.route('https://www.youtube.com/**', lambda r: r.fulfill(body='<title>yt</title>', content_type='text/html'))
        await pg.evaluate("()=>window.__kgeu.nav('sSet',true)"); await pg.wait_for_timeout(200)
        r = await pg.evaluate("()=>{const a=document.querySelector('#sSet .credit'),r=a.getBoundingClientRect(),s=document.getElementById('sSet');return {y:r.bottom,H:innerHeight,h:r.height,scroll:s.scrollHeight>s.clientHeight+1}}")
        ok('Settings has it at the bottom, 44 px tall, no scrolling', r['y'] > r['H'] - 60 and r['h'] >= 44 and not r['scroll'], r)
        async with pg.context.expect_page() as newp:
            await finger(pg, '#sSet .credit')
        np = await newp.value
        ok('tapping it opens youtube.com/@OhRabah in a new tab', np.url.rstrip('/') == URL_YT, np.url)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('credit_check'))
asyncio.run(main())
