# School2 item 3: Stage 3 lesson 3, night flying. (a) the sky goes to night for the lesson without saving it as the player's
# time of day (kgeuTOD stays 'day'), the KGEU runway light layers on; (b) three circuits each to a full stop with the tower
# calls, Dana's night lines (the opening, the PAPI on the first final, the first stop); (c) the debrief: 7 rows,
# 'Three full stop landings' passed, A or B, the sky back to day; (d) RETRY from the debrief sets night again, End mid
# lesson puts day back; (e) no page errors.
# Run: .venv/bin/python tests/school_night_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, start, said, rwy, call, climbout, downwind, base, final, touchdown, stop
ok = Checks()
WAIT_RB = "()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}"
SKY = f"()=>({{tod:{K}.TOD().id,saved:localStorage.getItem('kgeuTOD'),lit:{K}.lights().layers.every(l=>l.visible&&l.inScene),u:{K}.lights().uLights}})"

async def circuit(pg, F, past=60):
    S = []
    r = await climbout(pg, F); S.append(r['d']['s'])
    r = await downwind(pg, F); S.append(r['d']['s'])
    rb = await call(pg)
    await downwind(pg, F, 80)
    r = await base(pg, F); S.append(r['d']['s'])
    await final(pg, F)
    r = await touchdown(pg, F, past=past); S.append(r['d']['s'])
    r = await stop(pg, F)
    return S, rb, r

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        s0 = await pg.evaluate(SKY)
        await start(pg, 'night'); F = await rwy(pg)
        s1 = await pg.evaluate(SKY)
        ok('(a) day before the lesson', s0['tod'] == 'day', s0)
        ok('(a) night for the lesson, kgeuTOD still day, the runway lights on', s1['tod'] == 'night' and s1['saved'] == 'day' and s1['lit'] and s1['u'] == 1, s1)
        await pg.screenshot(path='/tmp/sch2n/night_start.png')
        c0 = await call(pg); await pg.evaluate(WAIT_RB)
        res = []
        for k in range(3):
            to = c0 if k == 0 else await call(pg)
            S, rb, r = await circuit(pg, F, past=40 + 30 * k)
            res.append((to, rb, S, r['on'] if k == 2 else r['c']))
            if k == 0: await pg.screenshot(path='/tmp/sch2n/night_stop1.png')
        ok('(b) three circuits, each cleared for takeoff and to land, each to a full stop', res == [(True, True, [1, 2, 3, 4], 1), (True, True, [1, 2, 3, 4], 2), (True, True, [1, 2, 3, 4], None)], res)
        await pg.wait_for_timeout(800)
        d = await pg.evaluate(DEBRIEF); dana = await pg.evaluate(DANA)
        miss = said(dana, 'Night pattern. Three full stops.', 'Watch the PAPI. Do not duck under.', 'Good. Two more.')
        ok('(b) Dana: the opening, the PAPI on the first final, the first stop', not miss and sum('Watch the PAPI' in t for t in dana) == 1, (miss, dana))
        tw = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'].startswith('Glendale Tower')]
        ok('(b) the tower cleared each takeoff and each landing', sum('cleared for takeoff' in t for t in tw) >= 3 and sum('cleared to land' in t for t in tw) >= 3, tw)
        names = [x[0] for x in d['rows']]
        ok('(c) the debrief: 7 rows, all passed, A or B', d['on'] and len(d['rows']) == 7 and all(x[1] for x in d['rows']) and d['letter'] in 'AB', d)
        ok('(c) three full stop landings', ['Three full stop landings', True, '3 of 3'] in d['rows'], d['rows'])
        s2 = await pg.evaluate(SKY)
        ok('(c) after the debrief the sky is day again', s2['tod'] == 'day' and s2['saved'] == 'day', s2)
        lg = await pg.evaluate("()=>JSON.parse(localStorage.getItem('kgeuLogbook')||'{}').night")
        ok('(c) the logbook night time credited', lg == 1, lg)
        await pg.screenshot(path='/tmp/sch2n/night_debrief.png')
        # (d) RETRY from the debrief, then End mid lesson
        await pg.evaluate("()=>document.getElementById('gRetry').click()"); await pg.wait_for_timeout(300)
        s3 = await pg.evaluate(SKY); on = await pg.evaluate(f"()=>{K}.LES.on")
        ok('(d) RETRY: the night lesson again under a night sky, kgeuTOD still day', on == 'night' and s3['tod'] == 'night' and s3['saved'] == 'day', (on, s3))
        await pg.evaluate("()=>document.getElementById('lesQuit').click()"); await pg.wait_for_timeout(300)
        s4 = await pg.evaluate(SKY); on = await pg.evaluate(f"()=>{K}.LES.on")
        ok('(d) End mid lesson: day again', not on and s4['tod'] == 'day' and s4['saved'] == 'day', (on, s4))
        ok('(e) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_night_check'))
asyncio.run(main())
