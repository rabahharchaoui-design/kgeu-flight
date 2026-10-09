# Phone2 item 2: the FLY screen groups the starts as FREE FLIGHT (Runway, Ramp: do anything, a
# brief grade card on any landing) and SEGMENTS (3 mi final, 1 mi final: short scored starts that
# end in the results card). Same grouping on the pause sheet. Fits 844x390 and 568x320 with no
# scrolling and 44 px chips. A segment's landing opens the full results card (paused); a free
# flight landing the brief one. Run: .venv/bin/python tests/segments_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone2', 'item2')
GROUPS = """(root)=>[...document.querySelectorAll(root+' .frow.starts .grp.cap')].map(g=>({cap:g.querySelector('.gcap').textContent,
  chips:[...g.querySelectorAll('.chip')].map(c=>({t:c.textContent.trim(),pos:c.dataset.pos,w:c.getBoundingClientRect().width,h:c.getBoundingClientRect().height,
    y:c.getBoundingClientRect().y})),capY:g.querySelector('.gcap').getBoundingClientRect().bottom}))"""
S = "()=>{const s=window.__kgeu.state();return {g:s.onGround,v:Math.hypot(s.vel.x,s.vel.z),crash:s.crashed}}"

async def land(pg, pos, seg=True):
    await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.pickPos('{pos}');K.start('{pos}');K.RES.segDone={'false' if seg else 'true'};}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{K}.auto()")
    for _ in range(90):
        await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
        st = await pg.evaluate(S)
        if st['g'] or st['crash']: break
    for _ in range(40):
        await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(100)
        if await pg.evaluate("()=>document.getElementById('landOv').classList.contains('on')"): break
    await pg.wait_for_timeout(400)
    return await pg.evaluate("()=>{const o=document.getElementById('landOv');return {on:o.classList.contains('on'),brief:o.classList.contains('brief'),title:o.querySelector('.sub').textContent,paused:window.__kgeu.paused()}}")

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in (IPHONE_15, {'width': 568, 'height': 320}, {'width': 390, 'height': 844}):
            W = vp['width']
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(500)
            g = await pg.evaluate(GROUPS, '#sFly')
            ok(f'{W}: two named groups, FREE FLIGHT and SEGMENTS', [x['cap'] for x in g] == ['Free flight', 'Segments'], [x['cap'] for x in g])
            ok(f'{W}: free flight is Runway and Ramp, segments are 3 mi and 1 mi final',
               [c['pos'] for c in g[0]['chips']] == ['runway', 'ramp'] and [c['pos'] for c in g[1]['chips']] == ['final', 'final1'], g)
            ok(f'{W}: every chip is 44 px and the caption sits over its chips', all(c['h'] >= 44 and c['w'] >= 56 and c['y'] >= x['capY'] - 1 for x in g for c in x['chips']),
               [(c['t'], round(c['w']), round(c['h'])) for x in g for c in x['chips']])
            fit = await pg.evaluate("()=>{const s=document.getElementById('sFly'),r=document.getElementById('bGo').getBoundingClientRect();return s.scrollHeight<=s.clientHeight+1&&r.right<=innerWidth&&r.bottom<=innerHeight&&r.height>=44}")
            ok(f'{W}: the fly screen fits with GO on screen', fit)
            no_nest = await pg.evaluate("()=>document.querySelectorAll('#menu .scr').length")
            ok(f'{W}: no new menu screen (ui1: eight, Missions folded into Challenges)', no_nest == 8, no_nest)
            await pg.screenshot(path=f'{SHOTS}/after_fly_{W}x{vp["height"]}.png')
            await finger(pg, '#sFly [data-pos="final"]'); await pg.wait_for_timeout(200)
            line = await pg.evaluate("()=>document.getElementById('sumLine').textContent")
            ok(f'{W}: the summary line names the segment', 'segment on 3 mile final' in line, line)
            # the pause sheet mirrors it
            await pg.evaluate(f"()=>{K}.start('runway')"); await pg.wait_for_timeout(500)
            await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(400)
            g = await pg.evaluate(GROUPS, '#pauseOv')
            ok(f'{W}: the pause sheet has the same two groups', [x['cap'] for x in g] == ['Free flight', 'Segments'] and [c['pos'] for x in g for c in x['chips']] == ['runway', 'ramp', 'final', 'final1'], g)
            await pg.screenshot(path=f'{SHOTS}/after_pause_{W}x{vp["height"]}.png')
            ok(f'{W}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        # a segment ends in the full results card; free flight in the brief one
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        r = await land(pg, 'final')
        ok('3 mile final segment: the results card, paused, named as the segment', r['on'] and not r['brief'] and r['paused'] and '3 mile final segment' in r['title'], r)
        await finger(pg, '#lKeep'); await pg.wait_for_timeout(300)
        r = await land(pg, 'final', seg=False)   # the same approach flown as free flight (the segment's landing already done)
        ok('free flight: the brief card', r['on'] and r['brief'] and not r['paused'] and 'Free flight landing' in r['title'], r)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('segments_check'))

asyncio.run(main())
