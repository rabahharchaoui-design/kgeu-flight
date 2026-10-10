# School1 item 6: the stage check and first solo. (a) flown well: the request at the hold, the stage check circuit to a
# full stop with Dana silent, her line getting out, then three solo circuits each to a full stop with the tower clearing
# the takeoff and the landing (read back with CALL), Dana saying nothing more until the debrief; the pattern altitude hold
# on each downwind; the debrief a row per task all passed, the Endorsement row, kgeuEndorse.solo saved. (b) flown badly: a
# stage check final under 55 kt: Dana takes it, the check fails, no endorsement. (c) no page errors.
# Run: .venv/bin/python tests/school_solo_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, start, fly, said, rwy, call, climbout, downwind, base, final, touchdown, stop
ok = Checks()
WAIT_RB = "()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}"

async def circuit(pg, F, past=60):
    S = []
    r = await climbout(pg, F); S.append(r['d']['s'])
    r = await downwind(pg, F); S.append(r['d']['s'])
    rb = await call(pg)
    await downwind(pg, F, 60)
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
        await start(pg, 'solo'); F = await rwy(pg)
        c0 = await call(pg); await pg.evaluate(WAIT_RB)
        S, rb, r = await circuit(pg, F)
        ok('(a) the stage check: the request, every leg, the full stop, on to the solo', c0 and rb and S == [1, 2, 3, 4] and r['ph'] == 1 and r['c'] == 1, (c0, rb, S, r))
        d0 = await pg.evaluate(DANA)
        ok('(a) Dana: the stage check opening, then quiet until she gets out', len(d0) == 2 and 'Stage check' in d0[0] and 'I am getting out' in d0[1], d0)
        res = []
        for k in range(3):
            to = await call(pg)
            S, rb, r = await circuit(pg, F, past=40 + 40 * k)
            res.append((to, rb, S, r['on'] if k == 2 else r['c']))
        ok('(a) three solo circuits, each cleared for takeoff and to land, each to a full stop', res == [(True, True, [1, 2, 3, 4], 2), (True, True, [1, 2, 3, 4], 3), (True, True, [1, 2, 3, 4], None)], res)
        await pg.wait_for_timeout(800)
        d = await pg.evaluate(DEBRIEF); dana = await pg.evaluate(DANA)
        ok('(a) no Dana lines during the solo, her debrief at the end', len(dana) == 3 and 'endorsement' in dana[2], dana)
        tw = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'].startswith('Glendale Tower')]
        ok('(a) the tower cleared each takeoff and each landing', sum('cleared for takeoff' in t for t in tw) >= 4 and sum('cleared to land' in t for t in tw) >= 4, tw)
        ok('(a) the downwind hold graded', await pg.evaluate(f"()=>{K}.G.tasks.dw.tAll>0"))
        names = [x[0] for x in d['rows']]
        ok('(a) the debrief: a row per task, all passed', d['on'] and names == ['Pattern altitude held', 'Three full stop landings', 'Touchdowns under 300 fpm', 'Touchdowns within 400 ft of the point', 'On the centerline'] and all(x[1] for x in d['rows']) and d['letter'] in 'AB', d)
        ok('(a) the worst of the three touchdowns', ['Touchdowns within 400 ft of the point', True, '394 ft past the point, worst of 3, standard 0 to 400 ft'] in d['rows'], d['rows'])
        ok('(a) the Endorsement row', ['Endorsement', 'Solo, signed by Dana Reyes, CFI'] in d['gl'], d['gl'])
        e = await pg.evaluate("()=>JSON.parse(localStorage.getItem('kgeuEndorse')||'{}').solo")
        ok('(a) kgeuEndorse.solo saved by Dana', e and e['by'] == 'Dana Reyes, CFI' and e['lesson'] == 'solo', e)
        await pg.screenshot(path='/tmp/sch6/solo_debrief.png')
        await pg.evaluate("()=>localStorage.removeItem('kgeuEndorse')")
        # (b) a stage check final at 50 kt
        await start(pg, 'solo'); await call(pg); await pg.evaluate(WAIT_RB)
        await climbout(pg, F); await downwind(pg, F); await call(pg); await base(pg, F)
        await final(pg, F, kt=50)
        await pg.wait_for_timeout(600)
        d = await pg.evaluate(DEBRIEF); dana = await pg.evaluate(DANA)
        ok('(b) a final under 55 kt: Dana takes it, the stage check fails', d['on'] and d['letter'] == 'F' and 'Stage check: final under 55 kt' in d['why'] and any('Too slow on final' in t for t in dana), (d['letter'], d['why'], dana))
        ok('(b) no endorsement', await pg.evaluate("()=>!JSON.parse(localStorage.getItem('kgeuEndorse')||'{}').solo") and not any(x[0] == 'Endorsement' for x in d['gl']))
        ok('(c) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_solo_check'))
asyncio.run(main())
