# School1 item 7: soft field (runway 1 stands in for the grass). (b) flown well: flaps 10 and the stick held back from the
# keyboard through a real takeoff roll (the physics), a liftoff under 59 kt, low in ground effect to 70 kt, the circuit with
# the tower calls, a 100 fpm touchdown (pushed on the events queue), then a real 8 s rollout with the stick back and no
# brakes, a stop: every phase reached, Dana's lines, the debrief a row per task, all passed. (c) flown badly: no back
# pressure until 45 kt fails the nose, climbing at 62 kt fails the ground effect, a 250 fpm touchdown fails the
# 150 fpm standard, braking on the rollout fails no braking. (d) no page errors.
# Run: .venv/bin/python tests/school_soft_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, start, fly, said, rwy, call, xz, climbout, downwind, base, final, touchdown, stop
ok = Checks()
WAIT_RB = "()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}"
ROLL = """(kt)=>{const K=window.__kgeu,s=K.state();s.flapIdx=1;let n=0;
  for(;n<900&&K.LES.on&&s.onGround&&s.ias*1.943844<kt;n++){s.windKt=0;s.gustAmp=0;s.throttle=1;K.stepFrame(0.05,false,true);}
  K.stepFrame(0,true);return {n:n,air:!s.onGround,kt:Math.round(s.ias*1.943844)}}"""
# the rollout: on runway 1 at 50 kt, the real physics for n frames of 0.1 s
ROLLOUT = """([x,z,n])=>{const K=window.__kgeu,s=K.state(),R=K.rwyFrame().rh*Math.PI/180;s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);
  s.vel.set(Math.sin(R)*25,0,-Math.cos(R)*25);s.quat.setFromEuler(new THREE.Euler(0.05,-R,0,'YXZ'));s.w.set(0,0,0);s.onGround=true;s.throttle=s.power=0;
  for(let i=0;i<n&&K.LES.on;i++){s.windKt=0;s.throttle=0;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return {kt:Math.round(s.ias*1.943844),on:s.onGround,s:K.LES.d.s}}"""

async def run(pg, good):
    PH = []
    await start(pg, 'soft'); F = await rwy(pg)
    c0 = await call(pg)
    await pg.evaluate(WAIT_RB); PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    if good:
        await pg.keyboard.down('s'); r = await pg.evaluate(ROLL, 99); await pg.keyboard.up('s')
    else:   # no back pressure until 45 kt
        await pg.evaluate(ROLL, 45); await pg.keyboard.down('s'); r = await pg.evaluate(ROLL, 99); await pg.keyboard.up('s')
    assert r['air'], r
    if good:
        await fly(pg, 20, agl=12, kt=64, vs=0, hdg=F['rh'])
        await fly(pg, 20, kt=72, vs=0, hdg=F['rh'])
    else:
        await fly(pg, 40, kt=62, vs=700, hdg=F['rh'])
    r = await climbout(pg, F); PH.append(r['ph'])
    await downwind(pg, F); rb = await call(pg); await downwind(pg, F, 80)
    await base(pg, F); await final(pg, F); PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await touchdown(pg, F, past=40, fpm=100 if good else 250)
    x, z = await xz(pg, F['thr'] + F['aim'] + 60, 0.5)
    await pg.keyboard.down('s')
    if not good: await pg.keyboard.down(' ')
    ro = await pg.evaluate(ROLLOUT, [x, z, 85])
    await pg.keyboard.up('s'); await pg.keyboard.up(' ')
    await stop(pg, F, u=F['aim'] + 900)
    await pg.wait_for_timeout(600)
    return PH, c0, rb, ro, await pg.evaluate(DEBRIEF), await pg.evaluate(DANA)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        PH, c0, rb, ro, d, dana = await run(pg, True)
        ok('(b) the CALL request and the landing readback', c0 and rb, (c0, rb))
        ok('(b) every phase: the takeoff, the circuit, the approach', PH == [0, 1, 2], PH)
        ok('(b) the rollout stayed on the ground', ro['on'] and ro['s'] == 4, ro)
        miss = said(dana, 'Pretend the runway is grass today', 'Stay low in ground effect until 70', '70. Now climb at 74.', 'Hold the nose up. No brakes.', 'Now you can brake')
        ok('(b) Dana: grass today, stay low, climb at 74, nose up no brakes, now brake', not miss, (miss, dana))
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: a row per task, all passed', d['on'] and names == ['Nose held up on the takeoff roll', 'Accelerated in ground effect', 'Touchdown under 150 fpm', 'On the centerline', 'No braking after touchdown']
           and all(x[1] for x in d['rows']), d['rows'])
        PH, c0, rb, ro, d, dana = await run(pg, False)
        rw = {x[0]: x for x in d['rows']}
        for n in ['Nose held up on the takeoff roll', 'Accelerated in ground effect', 'Touchdown under 150 fpm', 'No braking after touchdown']:
            ok('(c) flown badly fails: ' + n, n in rw and not rw[n][1], rw.get(n))
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_soft_check'))
asyncio.run(main())
