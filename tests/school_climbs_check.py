# School1 item 6: the climbs, descents and turns lesson, flown by pinning the plane frame by frame (school_fly.FLY).
# (a) flown well: the Vy hold opens once climbing over 300 fpm and closes at 3,400; the level off at 3,500 measured; the
# 500 fpm descent held from 3,400 to 3,100; the level off at 3,000; the turn right to 090 at 25 degrees of bank, rolled out
# on the heading; every phase reached, Dana's line for each, the debrief with a row per task, all passed. (b) flown badly:
# the turn at 50 degrees of bank fails the turn task. (c) no page errors.
# Run: .venv/bin/python tests/school_climbs_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, start, fly, said
ok = Checks()

async def run(pg, bank):
    ph = []
    await start(pg, 'climbs')
    r = await fly(pg, 30, kt=74, vs=700, hdg=360, thr=1); ph.append(r['ph'])
    vy = await pg.evaluate(f"()=>{{const h={K}.G.tasks.vy;return !!(h&&h.on)}}")
    r = await fly(pg, 80, kt=74, vs=700, hdg=360, thr=1, alt=3380, until="K.LES.ph===1"); ph.append(r['ph'])
    vy2 = await pg.evaluate(f"()=>{{const h={K}.G.tasks.vy;return [h.on,h.tAll>0]}}")
    r = await fly(pg, 60, kt=95, vs=0, hdg=360, thr=0.75, alt=3520, until="K.LES.ph===2"); ph.append(r['ph'])
    r = await fly(pg, 100, kt=90, vs=-500, hdg=360, alt=3430); vs = await pg.evaluate(f"()=>{{const h={K}.G.tasks.vs;return h&&[h.on,h.tAll>0]}}")
    r = await fly(pg, 100, kt=90, vs=-500, hdg=360, alt=3120, until="K.LES.ph===3"); ph.append(r['ph'])
    vs2 = await pg.evaluate(f"()=>{{const h={K}.G.tasks.vs;return h&&!h.on}}")
    r = await fly(pg, 60, kt=95, vs=0, hdg=360, alt=2990, until="K.LES.ph===4"); ph.append(r['ph'])
    for hd in (20, 45, 70, 85):
        await fly(pg, 10, kt=95, vs=0, hdg=hd, bank=bank)
    r = await fly(pg, 10, kt=95, vs=0, hdg=88, bank=0, until="!K.LES.on")
    await pg.wait_for_timeout(600)
    return ph, vy, vy2, vs, vs2, await pg.evaluate(DEBRIEF), await pg.evaluate(DANA)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        ph, vy, vy2, vs, vs2, d, dana = await run(pg, 25)
        ok('(a) every phase reached: climb, level at 3,500, descend, level at 3,000, turn', ph == [0, 1, 2, 3, 4], ph)
        ok('(a) the Vy hold opens once climbing, closes at 3,400 with time graded', vy and vy2 == [False, True], (vy, vy2))
        ok('(a) the 500 fpm hold opens below 3,400 and closes at 3,100', vs == [True, True] and vs2, (vs, vs2))
        miss = said(dana, 'Climbs, descents', 'Level off at 3,500', 'Descend at 500', 'heading 090')
        ok('(a) Dana says each phase', not miss, (miss, dana))
        names = [x[0] for x in d['rows']]
        ok('(a) the debrief: a row per task in order', d['on'] and names == ['Climb at Vy, 74 kt', 'Level off at 3,500 ft', 'Descent at 500 fpm', 'Level off at 3,000 ft', 'Medium bank turn to a heading'], d)
        ok('(a) flown well: every task passed, a pass', all(x[1] for x in d['rows']) and d['letter'] in 'ABC', d)
        ph, vy, vy2, vs, vs2, d, dana = await run(pg, 50)
        t = [x for x in d['rows'] if x[0] == 'Medium bank turn to a heading']
        ok('(b) 50 degrees of bank: the turn fails, the bank named', t and not t[0][1] and 'bank reached 50' in t[0][2], t)
        ok('(c) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_climbs_check'))
asyncio.run(main())
