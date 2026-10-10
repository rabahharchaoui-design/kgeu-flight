# School1 item 7: crosswind landings. (a) the lesson's wind: 12 kt, 70 degrees off runway 1, steady (windHold), and the
# flight's own wind back after it; (b) flown well: the 3 mile final tracked on the centreline from 2 nm, Dana's forward
# slip call at 500 ft and a slip (over 700 fpm without speeding up), a touchdown straight down the runway (pushed on the
# events queue), a full stop, the tower's takeoff clearance read back, a second circuit to a full stop: every phase
# reached, the debrief a row per task, all passed, drift graded on the worse of 2; (c) flown badly: 25 m off the
# centreline, no slip, a crabbed touchdown fail track, slip and drift; (d) no page errors.
# Run: .venv/bin/python tests/school_xwind_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, fly, said, rwy, call, xz, climbout, downwind, base, final, touchdown, stop
ok = Checks()
WIND = "()=>{const s=window.__kgeu.state(),L=window.__kgeu.LES;return {kt:s.windKt,base:s.windBase,dir:s.windDir,hold:!!s.windHold,w0:L.d.w0||null}}"

async def run(pg, good):
    PH = []
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('xwind');K.lesBriefSkip();}}")   # school_fly's start would zero the wind
    await pg.wait_for_timeout(200); F = await rwy(pg)
    w = await pg.evaluate(WIND)
    off = 0 if good else 25
    x, z = await xz(pg, F['thr'] - 2.2 * 1852, off)
    await fly(pg, 5, x=x, z=z, agl=2.2 * 1852 * 0.0524 * 3.28084, kt=65, vs=-345, hdg=F['rh'])
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await fly(pg, 400, kt=65, vs=-345, hdg=F['rh'], until="K.LES.ph===1")
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    if good: await fly(pg, 80, kt=66, vs=-800, hdg=F['rh'], until="K.LES.ph===2")
    else: await fly(pg, 300, kt=65, vs=-300, hdg=F['rh'], until="K.LES.ph===2")
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    x, z = await xz(pg, F['thr'] + F['aim'] - 300, off)
    await fly(pg, 20, x=x, z=z, agl=40, kt=62, vs=-200, hdg=F['rh'] + (0 if good else 12))
    await touchdown(pg, F, past=40)
    r = await stop(pg, F, u=F['aim'] + 500)
    c1 = await call(pg)
    r = await climbout(pg, F)
    await downwind(pg, F); rb = await call(pg); await downwind(pg, F, 80)
    await base(pg, F); await final(pg, F)
    await touchdown(pg, F, past=60)
    await stop(pg, F, u=F['aim'] + 600)
    await pg.wait_for_timeout(600)
    return w, PH, c1, rb, await pg.evaluate(DEBRIEF), await pg.evaluate(DANA), await pg.evaluate(WIND)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        F = await rwy(pg)
        w, PH, c1, rb, d, dana, w2 = await run(pg, True)
        rel = abs(((w['base'] - F['rh']) % 360 + 540) % 360 - 180)
        ok('(a) the wind: 12 kt, 70 degrees off the runway, held steady', w['kt'] == 12 and abs(rel - 70) < 0.5 and w['hold'] and w['dir'] == w['base'], (w, F['rh']))
        ok('(a) and the flight\'s own wind back after it', w2['kt'] == w['w0']['kt'] and w2['base'] == w['w0']['base'] and not w2['hold'], (w2, w['w0']))
        ok('(b) every phase: the crab, the slip, the landing', PH == [0, 1, 2], PH)
        ok('(b) the takeoff clearance and the landing readback on the second circuit', c1 and rb, (c1, rb))
        miss = said(dana, 'Crab into the wind on final', 'Forward slip: rudder one way, aileron the other.', 'Wing low, nose straight, upwind wheel first.')
        ok('(b) Dana: crab, the forward slip, wing low nose straight', not miss, (miss, dana))
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: a row per task, all passed', d['on'] and names == ['Tracked the centerline on final', 'Forward slip to lose height', 'No sideways drift at touchdown', 'Touchdown under 300 fpm', 'On the centerline']
           and all(x[1] for x in d['rows']), d['rows'])
        rw = {x[0]: x for x in d['rows']}
        ok('(b) drift and the touchdowns graded on the worse of 2', 'worst of 2' in rw['No sideways drift at touchdown'][2] and 'worst of 2' in rw['Touchdown under 300 fpm'][2], d['rows'])
        w, PH, c1, rb, d, dana, w2 = await run(pg, False)
        rw = {x[0]: x for x in d['rows']}
        for n in ['Tracked the centerline on final', 'Forward slip to lose height', 'No sideways drift at touchdown']:
            ok('(c) flown badly fails: ' + n, n in rw and not rw[n][1], rw.get(n))
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_xwind_check'))
asyncio.run(main())
