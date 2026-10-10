# School1 item 7: emergency descent and forced landing. (a) the smoke call with its SMOKE warning; (b) flown well: idle and
# 45 degrees of bank at once, down from 6,000 under 163 kt, levelled at 3,500, 10 s level, then the engine failure: the
# throttle locked at idle, the field drawn (a sand outline and four low rust markers, 1.5 to 2.5 nm away, downwind),
# landable while it is drawn, best glide held, a touchdown in it (pushed on the events queue) and a stop: every phase
# reached, Dana's lines, the debrief a row per task, all passed, the field gone after; (c) flown badly: power on and
# shallow fails idle, 170 kt fails Vne with the VNE warning, levelling 200 ft high fails the level off, a touchdown 400 m
# past the field fails it; (d) no page errors.
# Run: .venv/bin/python tests/school_emerg_check.py
import asyncio, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, STEP, start, fly, said
ok = Checks()
FIELD = """()=>{const K=window.__kgeu,O=K.lesObjs(),M=O.filter(o=>o.name==='fieldMk'),s=K.state();if(!M.length)return null;
  const cx=M.reduce((p,o)=>p+o.x,0)/M.length,cz=M.reduce((p,o)=>p+o.z,0)/M.length;
  return {n:M.length,outline:O.some(o=>o.name==='field'),cx:cx,cz:cz,nm:Math.hypot(cx-s.pos.x,cz-s.pos.z)/1852,brg:(Math.atan2(cx-s.pos.x,-(cz-s.pos.z))*180/Math.PI+360)%360,
    wdir:s.windDir,paved:K.isPaved(cx,cz),M:M.map(o=>[o.x,o.z])}}"""
WARN = "()=>{const w=document.getElementById('warn');return w.classList.contains('on')?w.textContent:''}"
GROUND = """([x,z,n])=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on;i++){const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return K.LES.on}"""

async def run(pg, good):
    PH = []
    await start(pg, 'emerg')
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<60&&!K.LES.d.go;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}}")
    smoke = await pg.evaluate(WARN); PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    if good: await fly(pg, 700, thr=0, bank=45, kt=130, vs=-2500, hdg=0, rate=8, until="K.LES.ph===1")
    else:
        await fly(pg, 70, thr=0.8, bank=10, kt=170, vs=-3000, hdg=0)
    vne = await pg.evaluate(WARN)
    if not good: await fly(pg, 700, thr=0, bank=45, kt=130, vs=-2500, hdg=0, until="K.LES.ph===1")
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await fly(pg, 80, alt=3500 if good else 3700, thr=0.8, kt=100, vs=0, hdg=90, until="K.LES.ph===2")
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await fly(pg, 140, kt=100, vs=0, hdg=90, until="K.LES.ph===3")
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    f = await pg.evaluate(FIELD)
    r = await fly(pg, 3, thr=1, kt=68, vs=-650, hdg=f['brg'])
    thr = await pg.evaluate(f"()=>{K}.state().throttle")
    await fly(pg, 120, kt=68, vs=-650, hdg=f['brg'])
    # short final into the field: 250 ft above it, then the touchdown in it (or 400 m past its far end)
    ax, az = (f['M'][1][0] - f['M'][0][0]), (f['M'][1][1] - f['M'][0][1]); L = math.hypot(ax, az); ax, az = ax / L, az / L
    h = (math.degrees(math.atan2(ax, -az)) + 360) % 360
    x0, z0 = f['cx'] - ax * 600, f['cz'] - az * 600
    await fly(pg, 10, x=x0, z=z0, agl=250, kt=62, vs=-500, hdg=h)
    tx, tz = (f['cx'], f['cz']) if good else (f['cx'] + ax * 700, f['cz'] + az * 700)
    await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:220,paved:K.isPaved(x,z),x:x,z:z,ias:30,bank:0}})}}", [tx, tz])
    await fly(pg, 2, agl=20, kt=50, vs=-100, hdg=h)
    await pg.evaluate(GROUND, [tx, tz, 30])
    await pg.wait_for_timeout(600)
    gone = await pg.evaluate(f"([x,z])=>{K}.isPaved(x,z)", [f['cx'], f['cz']])
    return PH, smoke, vne, f, thr, gone, await pg.evaluate(DEBRIEF), await pg.evaluate(DANA)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        PH, smoke, vne, f, thr, gone, d, dana = await run(pg, True)
        ok('(a) the smoke call flashes SMOKE', smoke == 'SMOKE', smoke)
        ok('(b) every phase: the descent, the level off, level flight, the forced landing', PH == [0, 1, 2, 3], PH)
        dw = abs(((f['brg'] - (f['wdir'] + 180)) % 360 + 540) % 360 - 180)
        ok('(b) the field: an outline and four markers, 1.5 to 2.5 nm away, downwind (within 75 degrees), landable', f['n'] == 4 and f['outline'] and 1.45 <= f['nm'] <= 2.55 and dw <= 76 and f['paved'], (f['n'], f['outline'], round(f['nm'], 2), round(dw), f['paved']))
        ok('(b) the throttle is locked at idle after the failure', thr == 0, thr)
        miss = said(dana, 'Smoke in the cockpit. Emergency descent.', 'level off at 3,500', 'Engine failure. Best glide 68, pick a field', 'miles')
        ok('(b) Dana: the smoke, the level off, the engine failure and where the field is', not miss, (miss, dana))
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: a row per task, all passed', d['on'] and names == ['Idle and banked within 5 s', 'Stayed below Vne, 163 kt', 'Levelled off within 100 ft', 'Best glide held, 68 kt', 'Landed in the field']
           and all(x[1] for x in d['rows']), d['rows'])
        ok('(b) the field is gone after the lesson (no longer landable)', not gone)
        PH, smoke, vne, f, thr, gone, d, dana = await run(pg, False)
        ok('(c) 170 kt flashes VNE', vne == 'VNE', vne)
        rw = {x[0]: x for x in d['rows']}
        for n in ['Idle and banked within 5 s', 'Stayed below Vne, 163 kt', 'Levelled off within 100 ft', 'Landed in the field']:
            ok('(c) flown badly fails: ' + n, n in rw and not rw[n][1], rw.get(n))
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_emerg_check'))
asyncio.run(main())
