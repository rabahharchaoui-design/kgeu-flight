# Feature 8: the arcade hub and the landing challenge. Run: .venv/bin/python tests/arcade_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"
async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuType': 'cessna'})
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
        cards = await pg.evaluate("()=>[...document.querySelectorAll('#arcCards .mcard')].map(c=>({id:c.dataset.m,ico:!!c.querySelector('svg.ico'),stars:!!c.querySelector('.stars'),soon:!!c.querySelector('.soon'),t:c.querySelector('b').textContent}))")
        ok('featured Red Flag Dogfight, coming soon, is first', cards[0]['id'] == 'dogfight' and cards[0]['soon'] and cards[0]['t'] == 'Red Flag Dogfight', cards[:1])
        ok('airdrop, strike range, 5 and 1 mile landing challenges and daily challenge cards', sorted(c['id'] for c in cards[1:]) == ['daily', 'drop', 'landing', 'landing1', 'range'], [c['id'] for c in cards])
        ok('every game card has an icon and a 1 to 3 star rating', all(c['ico'] and c['stars'] for c in cards[1:]))
        r = await pg.evaluate("()=>{const s=document.getElementById('sArc');const bad=[];if(s.scrollHeight>s.clientHeight+1)bad.push('scrolls');s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(r.bottom>innerHeight+0.5||r.right>innerWidth+0.5)bad.push('off '+e.textContent.slice(0,12));if(r.height<43.5)bad.push('small')});return bad}")
        ok('arcade fits one iPhone landscape screen with no scrolling', not r, r)
        d1 = await pg.evaluate(f"()=>{K}.dailySpec()"); d2 = await pg.evaluate(f"()=>{K}.dailySpec()")
        ok('the daily challenge is the same all day', d1 == d2, d1)
        # landing challenge, flown by autoland so it finishes
        await finger(pg, '#arcCards [data-m="landing"]'); await pg.wait_for_timeout(900)
        s = await pg.evaluate(f"()=>({{on:{K}.ARC.on,g:{K}.state().onGround,agl:Math.round({K}.state().agl),hud:document.getElementById('miss').classList.contains('on'),dest:{K}.dest()}})")
        ok('landing challenge starts in the air with the clock and the target runway', s['on'] and not s['g'] and s['agl'] > 300 and s['hud'] and s['dest'] == {'apt': 'Glendale', 'num': '1'}, s)
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(120):
            await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
            if await pg.evaluate(f"()=>{K}.state().onGround||{K}.state().crashed"): break
        await pg.wait_for_timeout(3500)
        res = await pg.evaluate("()=>({on:document.getElementById('arcOv').classList.contains('on'),stars:document.getElementById('aStars').textContent.length,title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText})")
        ok('touchdown on the target ends it with a full results screen', res['on'] and res['stars'] == 3 and 'Time' in res['lines'], res)
        ok('it scores points', 'points' in res['title'], res['title'])
        best = await pg.evaluate(f"()=>{K}.SCORE.best['arc:landing']")
        ok('best is saved to the records', best and best['pts'] > 0, best)
        await finger(pg, '#aHub'); await pg.wait_for_timeout(400)
        em = await pg.evaluate("()=>document.querySelector('#arcCards [data-m=landing] .sc em').textContent")
        ok('the card shows the best score', 'pts' in em, em)
        await finger(pg, '#arcCards [data-m="daily"]'); await pg.wait_for_timeout(900)
        s = await pg.evaluate(f"()=>({{on:{K}.ARC.on,kind:{K}.ARC.kind,type:{K}.state().type}})")
        ok("daily challenge flies today's aircraft", s['on'] and s['kind'] == 'daily' and s['type'] == d1['type'], (s, d1))
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(200)
        await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(200)
        ok('coming soon does not start anything', await pg.evaluate("()=>document.getElementById('menu').classList.contains('on')"))
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('arcade_check'))
asyncio.run(main())
