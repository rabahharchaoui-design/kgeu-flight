# School1 item 6: takeoffs and landings, three circuits from runway 1 (a touch and go, a go around on Dana's call, a full
# stop), the plane moved through each leg (school_fly) and the touchdowns pushed on the events queue. (a) the aiming bar
# on the runway 305 m past the threshold; (b) flown well: the CALL request at the hold, the tower's touch and go, option
# and land clearances each read back with CALL, every leg of every circuit reached, the go around (full power at once, 100
# ft up), the approach speed hold graded, the debrief all passed with Made the tower calls 4 of 4; (c) flown badly: the
# go around without power and a landing short of the bar fail ga and tdz; (d) no page errors.
# Run: .venv/bin/python tests/school_landings_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import STEP, K, BASE, DEBRIEF, DANA, start, fly, said, rwy, call, climbout, downwind, base, final, touchdown, stop
ok = Checks()
WAIT_RB = "()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}"
LOG = "()=>window.__kgeu.radioLog().map(l=>[l.who,l.kind||'',l.text])"

async def run(pg, good):
    S = []   # (circuit, step) seen
    await start(pg, 'landings'); F = await rwy(pg)
    aim = await pg.evaluate(f"()=>{K}.lesObjs()")
    c0 = await call(pg)
    await pg.evaluate(WAIT_RB)   # our request, the tower's clearance and our readback go out (the radio runs on the sim clock)
    for c in range(3):
        r = await climbout(pg, F); S.append((r['d']['c'], r['d']['s']))
        r = await downwind(pg, F); S.append((r['d']['c'], r['d']['s']))
        rb = await call(pg)
        if good or c != 1: assert rb, ('no readback call', c)
        await downwind(pg, F, 80)   # the readback airs
        r = await base(pg, F); S.append((r['d']['c'], r['d']['s']))
        if c == 1:   # the go around: Dana calls it at 300 ft
            await final(pg, F, to=320)
            await fly(pg, 3, agl=295, kt=65, vs=-400, hdg=F['rh'])
            ga = await pg.evaluate(DANA)
            if good: r = await fly(pg, 120, thr=1, kt=70, vs=900, hdg=F['rh'], until="K.LES.d.c===2")
            else: r = await fly(pg, 220, thr=0.3, kt=65, vs=-50, hdg=F['rh'], until="K.LES.d.c===2")
            S.append((r['d']['c'], r['d']['s']))
            continue
        await final(pg, F)
        r = await touchdown(pg, F, past=60 if good else -100); S.append((r['d']['c'], r['d']['s']))
        if c == 0:
            await fly(pg, 30, agl=30, kt=60, vs=0, hdg=F['rh'])   # rolling: her touch and go line airs
            r = await fly(pg, 10, agl=150, kt=70, vs=500, hdg=F['rh'], until="K.LES.d.c===1"); S.append((r['d']['c'], r['d']['s']))
        else:
            r = await stop(pg, F); S.append(('end', r['on']))
    await pg.wait_for_timeout(600)
    return S, aim, c0, ga, await pg.evaluate(DEBRIEF), await pg.evaluate(DANA), await pg.evaluate(LOG)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        S, aim, c0, ga, d, dana, log = await run(pg, True)
        F = await rwy(pg)
        bar = [o for o in aim if o['name'] == 'aim']
        ok('(a) the aiming bars: one mesh, a sand bar with a rust edge and a rust bar beyond it (12 triangles), in the scene', len(bar) == 1 and bar[0]['tri'] == 12 and bar[0]['inScene'], aim)
        ok('(b) the CALL request at the hold', c0)
        ok('(b) every leg of every circuit: climb, downwind, base, touchdown, the go around, the full stop',
           S == [(0, 1), (0, 2), (0, 3), (0, 4), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3), (2, 4), ('end', None)], S)
        tw = [l[2] for l in log if l[0].startswith('Glendale Tower')]; pl = [l[2] for l in log if l[1] == 'pilot']
        ok('(b) the tower: cleared for takeoff closed traffic, touch and go, the option, to land', any('cleared for takeoff, make right closed traffic' in t for t in tw)
           and any('cleared touch and go' in t for t in tw) and any('cleared for the option' in t for t in tw) and any('cleared to land' in t for t in tw), tw)
        ok('(b) and each read back', any(t.startswith('Glendale Tower, Skyhawk') for t in pl) and any(t.startswith('Cleared touch and go') for t in pl)
           and any(t.startswith('Cleared for the option runway 1') for t in pl) and any(t.startswith('Cleared to land') for t in pl), pl)
        miss = said(dana, 'Takeoffs and landings', 'Touch and go', 'Go around. Full power, nose up, flaps up a notch.', 'full stop')
        ok('(b) Dana: the opening, the touch and go, the go around call, the full stop', not miss, (miss, dana))
        ok('(b) the approach speed hold ran on the finals', await pg.evaluate(f"()=>{K}.G.tasks.vapp.tAll>0"))
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: a row per task in order, all passed, an A or B', d['on'] and names == ['Touchdown within 400 ft of the point', 'Touchdown under 300 fpm', 'On the centerline', 'Approach speed held', 'Went around on command', 'Made the tower calls']
           and all(x[1] for x in d['rows']) and d['letter'] in 'AB', d)
        ok('(b) the calls: 4 of 4', ['Made the tower calls', True, '4 of 4 made'] in d['rows'], d['rows'])
        ok('(b) the bar is cleared after the lesson', await pg.evaluate(f"()=>{K}.lesObjs().length") == 0)
        S, aim, c0, ga, d, dana, log = await run(pg, False)
        rw = {x[0]: x for x in d['rows']}
        ok('(c) no power on the go around fails it', not rw['Went around on command'][1], rw.get('Went around on command'))
        ok('(c) touching down 100 m short of the bar fails the zone', not rw['Touchdown within 400 ft of the point'][1] and 'short of' in rw['Touchdown within 400 ft of the point'][2], rw.get('Touchdown within 400 ft of the point'))
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_landings_check'))
asyncio.run(main())
