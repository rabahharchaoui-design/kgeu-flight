# School1 item 7: short field. On runway 1: flaps 10, the brakes held to full power, a real takeoff roll (the physics, the
# stick back from the keyboard), Vx 62 kt to 500 ft AGL, the circuit with the tower calls, a full flap final on the
# aiming bar, the touchdown pushed on the events queue and a stop. (a) the aiming bar; (b) flown well: every phase
# reached, the Vx hold, Dana's lines (the brief, 500 feet, flaps up maximum braking), the debrief a row per task, all
# passed, the tdz row says where it stopped; (c) flown badly: flaps up on the roll and 75 kt fail Vx (flaps noted), a
# touchdown 100 m past the bar fails the zone; (d) no page errors.
# Run: .venv/bin/python tests/school_short_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, start, fly, said, rwy, call, climbout, downwind, base, final, touchdown, stop
ok = Checks()
WAIT_RB = "()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}"
# the takeoff roll on the real physics: flaps, the brakes and full power for 2 s, then released, the stick back from 40 kt
ROLL = """([fl,brk])=>{const K=window.__kgeu,s=K.state();s.flapIdx=fl;let n=0;
  for(;n<600&&K.LES.on&&s.onGround;n++){s.windKt=0;s.gustAmp=0;s.throttle=1;K.stepFrame(0.05,false,true);}
  K.stepFrame(0,true);return {n:n,air:!s.onGround,kt:Math.round(s.ias*1.943844)}}"""

async def run(pg, good):
    PH = []
    await start(pg, 'short'); F = await rwy(pg)
    aim = await pg.evaluate(f"()=>{K}.lesObjs()")
    c0 = await call(pg)
    await pg.evaluate(WAIT_RB)
    if good:   # the brakes held to full power, then released
        await pg.keyboard.down(' ')
        await pg.evaluate(f"()=>{{const K={K},s=K.state();s.flapIdx=1;for(let i=0;i<20;i++){{s.throttle=1;K.stepFrame(0.1,false,true);}}K.stepFrame(0,true)}}")
        await pg.keyboard.up(' ')
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await pg.keyboard.down('s')
    r = await pg.evaluate(ROLL, [1 if good else 0, 0])
    await pg.keyboard.up('s')
    assert r['air'], r
    r = await fly(pg, 700, kt=62 if good else 75, vs=650, hdg=F['rh'], until="K.LES.d.vx===2")
    r = await climbout(pg, F); PH.append(r['ph'])
    await downwind(pg, F); rb = await call(pg); await downwind(pg, F, 80)
    r = await base(pg, F)
    await final(pg, F); PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await touchdown(pg, F, past=40 if good else 100)
    await pg.wait_for_timeout(100)
    r = await stop(pg, F, u=F['aim'] + 125)
    await pg.wait_for_timeout(600)
    return PH, aim, c0, rb, await pg.evaluate(DEBRIEF), await pg.evaluate(DANA)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        PH, aim, c0, rb, d, dana = await run(pg, True)
        ok('(a) the aiming bar is on the runway', any(o['name'] == 'aim' and o['inScene'] for o in aim), aim)
        ok('(b) the CALL request and the landing readback', c0 and rb, (c0, rb))
        ok('(b) every phase: the takeoff, the circuit, the approach', PH == [0, 1, 2], PH)
        miss = said(dana, 'Short field', 'Hold the brakes, full power, then release', '500 feet', 'Flaps up, maximum braking.')
        ok('(b) Dana: the brief, 500 feet, flaps up maximum braking', not miss, (miss, dana))
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: a row per task, all passed', d['on'] and names == ['Climb at Vx, 62 kt', 'Touchdown within 200 ft of the point', 'Touchdown under 300 fpm', 'Approach speed held', 'On the centerline']
           and all(x[1] for x in d['rows']), d)
        rw = {x[0]: x for x in d['rows']}
        ok('(b) the zone row says where it stopped', 'stopped 125 m past the bar' in rw.get('Touchdown within 200 ft of the point', ['', '', ''])[2], rw.get('Touchdown within 200 ft of the point'))
        ok('(b) the bar is cleared after the lesson', await pg.evaluate(f"()=>{K}.lesObjs().length") == 0)
        PH, aim, c0, rb, d, dana = await run(pg, False)
        rw = {x[0]: x for x in d['rows']}
        v = rw.get('Climb at Vx, 62 kt', ['', True, ''])
        ok('(c) flaps up on the roll and 75 kt fail Vx, the flaps noted', not v[1] and 'flaps 0 on the roll' in v[2], v)
        z = rw.get('Touchdown within 200 ft of the point', ['', True, ''])
        ok('(c) 100 m past the bar fails the zone', not z[1], z)
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_short_check'))
asyncio.run(main())
