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
        # fix2 item 7: the footer scrolls with the Settings rows, under the last one (two columns of six
        # 44 px rows leave no room for a fixed footer at 667x375), so the credit is the last thing in the
        # rows' scroll box: swipe to the end and it sits at the bottom of the screen, 44 px, tappable
        r = await pg.evaluate("""()=>{const a=document.querySelector('#sSet .credit'),g=document.querySelector('#sSet .setGrid'),s=document.getElementById('sSet');
          g.scrollTop=1e4;const r=a.getBoundingClientRect(),G=g.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
          return {y:Math.round(r.bottom),H:innerHeight,h:r.height,gridBottom:Math.round(G.bottom),scroll:s.scrollHeight>s.clientHeight+1,hit:!!hit&&a.contains(hit)}}""")
        ok('Settings has it at the bottom (end of the rows), 44 px tall, the screen itself does not scroll, a tap reaches it',
           r['y'] > r['H'] - 60 and r['y'] <= r['gridBottom'] + 1 and r['h'] >= 44 and not r['scroll'] and r['hit'], r)
        async with pg.context.expect_page() as newp:
            await finger(pg, '#sSet .credit')
        np = await newp.value
        ok('tapping it opens youtube.com/@OhRabah in a new tab', np.url.rstrip('/') == URL_YT, np.url)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('credit_check'))
asyncio.run(main())
