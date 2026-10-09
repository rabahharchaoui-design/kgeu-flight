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
        # today's daily may be at a world airport (the rotation): pin it to Arizona so it flies here (world_lb_check flies the world ones)
        assert await pg.evaluate(f"()=>{K}.dailyRegion('az')") == 'az'
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
        cards = await pg.evaluate("()=>[...document.querySelectorAll('#arcCards .mcard')].map(c=>({id:c.dataset.m,ico:!!c.querySelector('svg.ico'),stars:!!c.querySelector('.stars'),soon:!!c.querySelector('.soon'),t:c.querySelector('b').textContent}))")
        ok('featured Red Flag Dogfight is first, playable (no Coming soon)', cards[0]['id'] == 'dogfight' and not cards[0]['soon'] and cards[0]['t'] == 'Red Flag Dogfight', cards[:1])
        ok('ui1: then the daily, strike range, airdrop and short field cards, in that order', [c['id'] for c in cards[1:5]] == ['daily', 'range', 'drop', 'short'], [c['id'] for c in cards])
        ok('ui1: no 5 mile, 1 mile, dash or gun run card', not {'landing', 'landing1', 'dash', 'gunrun'} & {c['id'] for c in cards}, [c['id'] for c in cards])
        # tasking item 1: the five, then one Taskings group of four (the only group; no World airports group)
        grp = await pg.evaluate("()=>[...document.querySelectorAll('#arcCards .cgrp')].map(e=>e.textContent)")
        built = await pg.evaluate(f"()=>['overwatch','lifeline','shepherd','finder'].filter(t=>{K}.TASKS[t]).map(t=>'tk-'+t)")
        ok('ui1: no World airports group; tasking: one Taskings group after the five, a card per tasking', grp == (['Taskings'] if built else []) and [c['id'] for c in cards[5:]] == built, (grp, [c['id'] for c in cards]))
        cards = cards[:5]
        ok('every game card has an icon and a 1 to 3 star rating', all(c['ico'] and c['stars'] for c in cards))
        r = await pg.evaluate("()=>{const s=document.getElementById('sArc');const bad=[];[...s.querySelectorAll('#arcCards .mcard:not(.apt):not(.more)')].slice(0,5).forEach(e=>{const r=e.getBoundingClientRect();if(r.bottom>innerHeight+0.5||r.right>innerWidth+0.5)bad.push('off '+e.textContent.slice(0,12));if(r.height<43.5)bad.push('small')});return bad}")
        ok('the five Challenges cards fit one iPhone landscape screen (the Taskings group is below them)', not r, r)
        d1 = await pg.evaluate(f"()=>{K}.dailySpec()"); d2 = await pg.evaluate(f"()=>{K}.dailySpec()")
        ok('the daily challenge is the same all day', d1 == d2, d1)
        # landing challenge, flown by autoland so it finishes
        await pg.evaluate(f"()=>{K}.arcStart('landing')"); await pg.wait_for_timeout(900)   # ui1: the mode stays, its card went
        s = await pg.evaluate(f"()=>({{on:{K}.ARC.on,g:{K}.state().onGround,agl:Math.round({K}.state().agl),hud:document.getElementById('miss').classList.contains('on'),dest:{K}.dest()}})")
        ok('landing challenge starts in the air with the clock and the target runway', s['on'] and not s['g'] and s['agl'] > 300 and s['hud'] and s['dest'] == {'apt': 'Glendale', 'num': '1'}, s)
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(120):
            await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
            if await pg.evaluate(f"()=>{K}.state().onGround||{K}.state().crashed"): break
        # the results card waits for the aircraft to stop: run the rollout through
        await pg.wait_for_timeout(600)
        mid = await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')")
        ok('the results card is not up while the aircraft is still rolling', not mid)
        for _ in range(30):
            await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(120)
            if await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')"): break
        await pg.wait_for_timeout(500)
        res = await pg.evaluate("()=>({on:document.getElementById('arcOv').classList.contains('on'),stars:document.getElementById('aStars').textContent.length,title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText,letter:document.getElementById('aLetter').textContent,score:document.getElementById('aScore').textContent,btns:[...document.querySelectorAll('#arcOv .rBtns button')].map(b=>b.textContent),paused:window.__kgeu.paused()})")
        ok('the aircraft has stopped and the results card is up with the stats', res['on'] and res['stars'] == 3 and 'Time' in res['lines'] and 'Touchdown' in res['lines'], res)
        ok('it scores points, with a letter grade and a score line', 'points' in res['title'] and res['letter'] in 'ABCDF' and 'pts' in res['score'], (res['title'], res['letter'], res['score']))
        ok('CONTINUE and MAIN MENU, and the card pauses the challenge', res['btns'] == ['RETRY LANDING CHALLENGE', 'CONTINUE IN FREE FLIGHT', 'MAIN MENU'] and res['paused'], res['btns'])
        best = await pg.evaluate(f"()=>{K}.SCORE.best['arc:landing']")
        ok('best is saved to the records', best and best['pts'] > 0, best)
        await finger(pg, '#aHub'); await pg.wait_for_timeout(400)
        ok('MAIN MENU lands on the home screen', await pg.evaluate(f"()=>document.getElementById('menu').classList.contains('on')&&{K}.curScr()==='sHome'"))
        await pg.evaluate(f"()=>{K}.nav('sArc')"); await pg.wait_for_timeout(300)
        ok('ui1: still no landing challenge card after flying one', not await pg.evaluate("()=>!!document.querySelector('#arcCards [data-m=landing]')"))
        dname = await pg.evaluate("()=>document.querySelector('#arcCards [data-m=daily] b').textContent")
        ok("the daily card names today's airport and runway", dname == f"{d1['name']}, runway {d1['num']}", (dname, d1))
        if d1['region'] != 'az':   # today's daily is at a world airport: GO switches region (reload stubbed here; world_lb_check flies it)
            await pg.evaluate("()=>{window.__kgeuReload=()=>{window.__reloaded=(window.__reloaded||0)+1;};}")
        await finger(pg, '#arcCards [data-m="daily"]'); await pg.wait_for_timeout(900)
        s = await pg.evaluate(f"()=>({{on:{K}.ARC.on,kind:{K}.ARC.kind,type:{K}.state().type,rl:window.__reloaded||0,reg:localStorage.getItem('kgeuRegion'),res:JSON.parse(sessionStorage.getItem('kgeuResume')||'null')}})")
        if d1['region'] == 'az':
            ok("daily challenge flies today's aircraft", s['on'] and s['kind'] == 'daily' and s['type'] == d1['type'], (s, d1))
        else:
            ok(f"daily challenge at {d1['region']}: switches region with a daily resume", s['rl'] == 1 and s['reg'] == d1['region'] and ((s['res'] or {}).get('start') or {}).get('arc') == 'daily' and not s['on'], (s, d1))
            await pg.evaluate("()=>{localStorage.setItem('kgeuRegion','az');sessionStorage.removeItem('kgeuResume');}")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('arcade_check'))
asyncio.run(main())
