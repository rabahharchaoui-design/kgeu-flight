# School2 item 1: Stage 3 lesson 1, pilotage and dead reckoning (Glendale to Sky Harbor and back on a nav log).
# (a) the lesson starts from the school screen by a real tap (Stage 3 node, row 1) with a 'ride' placement.
# (b) flown well, pinned frame by frame (tests/school_fly.py): the nav log card has 4 rows out with headings and ETAs; the
# takeoff clearance read back; on course at 1,500 ft above the ground (the stamp, the log open); each leg at 3,500 and
# 105 kt on its course, NAV.leg advancing and the rows ticking; the Bravo request and readback on CALL after Tolleson;
# the Phoenix Tower readback past downtown; a touchdown on runway 7L and a stop; the return legs at 4,500; the Glendale
# call and the landing clearance; a touchdown on runway 1 and a stop. The debrief: the 8 task rows, bravo, phx and home
# passed, an A or a B. (c) the Bravo call skipped: entering the 5 nm ring fails the bravo row with the violation text and
# Dana says so. (d) no page errors.
# Run: .venv/bin/python tests/school_xc_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, FLY, start, said, rwy, call, final, touchdown, stop
ok = Checks()
NAVS = f"()=>{{const N={K}.NAV;return {{leg:N.leg,on:N.on,show:N.show,legs:N.legs.map(l=>({{to:l.to.short,c:l.course,seg:l.seg,at:l.at,miss:l.miss,eta:l.eta}})),x:N.legs.map(l=>[l.from.x,l.from.z,l.to.x,l.to.z])}}}}"
VIS = """()=>{const g=id=>document.getElementById(id),L=g('navLog'),r=L.getBoundingClientRect(),rows=[...L.querySelectorAll('tr')].map(t=>t.getBoundingClientRect());
  return {appr:document.body.classList.contains('appr'),log:getComputedStyle(L).display!=='none',dest:getComputedStyle(g('hDest')).display!=='none',lit:g('lesLog').getAttribute('aria-pressed'),
    box:[r.left,r.top,r.right,r.bottom],W:innerWidth,H:innerHeight,inside:rows.length===5&&rows.every(q=>q.top>=r.top-0.5&&q.bottom<=r.bottom+0.5),h:r.height}}"""
ROWS = "()=>[...document.querySelectorAll('#navLog tbody tr')].map(r=>[...r.cells].map(c=>c.textContent).concat([r.className]))"
ASK = "K.TASK.ask&&K.TASK.ask.shown"
# school_fly's FLY, with hold: the altitude (MSL ft) pinned every frame (minutes of cruise would drift with FLY's pitch)
FLYH = FLY.replace("if(o.alt!=null)", "if(o.hold!=null)s.pos.y+=(o.hold-K.G.alt)/3.28084;if(o.alt!=null)")

async def fly(pg, n, **o):
    return await pg.evaluate(FLYH, [n, o])

async def taps(pg, hold, hdg, k=2, n=400):
    """pinned in cruise, wait for each CALL and tap it; how many were tapped"""
    m = 0
    for _ in range(k):
        await fly(pg, n, hold=hold, kt=105, vs=0, hdg=hdg, until=ASK)
        if await answer(pg): m += 1
    return m

async def answer(pg):
    return await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")

async def leg(pg, i, alt, kt=105, stop_on_ask=True):
    """fly leg i of the nav log on its course until it is passed (or a CALL is up); the position is not moved"""
    n = await pg.evaluate(NAVS)
    c = n['legs'][i]['c']
    until = f"K.NAV.leg>{i}" + (f"||({ASK})" if stop_on_ask else '')
    return await fly(pg, 6000, hold=alt, kt=kt, vs=0, hdg=c, until=until)

async def fly_leg(pg, i, alt):
    """leg i to its fix, answering every CALL on the way; the CALLs answered"""
    calls = 0
    for _ in range(6):
        await leg(pg, i, alt)
        if (await pg.evaluate(NAVS))['leg'] > i: break
        if await answer(pg): calls += 1
    return calls

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # ---------------- (a) a real tap from the school screen ----------------
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(200)
        await finger(pg, '#hSch'); await pg.wait_for_timeout(400)
        node = await pg.evaluate("()=>{const n=document.querySelector('.sNode[data-st=s3]');return n&&[n.className,n.textContent]}")
        ok('(a) the Stage 3 node is open, no Coming soon', node and 'soon' not in node[0] and 'locked' not in node[0] and 'Coming soon' not in node[1], node)
        await finger(pg, '.sNode[data-st=s3]'); await pg.wait_for_timeout(400)
        rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.classList.contains('soon')])")
        ok('(a) Stage 3: pilotage and divert lesson rows, then two Coming soon rows', rows == [['pilotage', False], ['divert', False], ['night', True], ['soloxc', True]], rows)
        await finger(pg, '#school .lrow[data-l=pilotage]'); await pg.wait_for_timeout(600)
        r = await pg.evaluate(f"()=>({{on:{K}.LES.on,brief:document.getElementById('brOv').classList.contains('on'),t:document.getElementById('brT').textContent}})")
        ok('(a) the row tap opens the briefing for the pilotage lesson', r == {'on': 'pilotage', 'brief': True, 't': 'Pilotage and dead reckoning'}, r)
        await pg.close()

        # ---------------- (b) flown well ----------------
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await start(pg, 'pilotage'); F = await rwy(pg)
        n = await pg.evaluate(NAVS)
        ok('(b) the plan: 4 legs out, 4 back, the dest on the first fix', [l['seg'] for l in n['legs']] == [0, 0, 0, 0, 1, 1, 1, 1] and [l['to'] for l in n['legs']] == ['Stadium', 'Tolleson', 'Downtown', 'Sky Harbor', 'Downtown', 'Tolleson', 'Stadium', 'Glendale'], n['legs'])
        await finger(pg, '#lesLog'); await pg.wait_for_timeout(200)
        R = await pg.evaluate(ROWS)
        ok('(b) LOG opens the card: 4 rows out, a 3 digit heading and an m:ss ETA each', len(R) == 4 and all(len(x[1]) == 3 and x[1].isdigit() and ':' in x[3] for x in R) and [x[0] for x in R] == ['Stadium', 'Tolleson', 'Downtown', 'Sky Harbor'], R)
        lb = await pg.evaluate("()=>{const r=document.getElementById('lesLog').getBoundingClientRect();return [r.width,r.height]}")
        ap = await pg.evaluate(VIS)
        ok('(b) on the runway (the approach rule): the log hidden, the readout back, LOG unlit', ap['appr'] and not ap['log'] and ap['dest'] and ap['lit'] == 'false', ap)
        ok('(b) LOG is 44 px or more', lb[0] >= 44 and lb[1] >= 44, lb)
        await pg.screenshot(path='/tmp/sch2_xc_log.png')
        c0 = await call(pg)
        ok('(b) the takeoff clearance read back', c0)
        # the climb out: past the departure end toward the stadium, through 1,500 ft above the ground
        x, z = await pg.evaluate(f"()=>{{const K={K},u=K.rwyFrame().thr+1700;return [K.wX(u,0),K.wZ(u,0)]}}")
        r = await fly(pg, 200, x=x, z=z, agl=1300, kt=74, vs=700, hdg=60, until='K.LES.ph>=1')
        n = await pg.evaluate(NAVS)
        ok('(b) on course: phase 1, the log open by itself, the route hold on (the heading once turned onto the leg)', r['ph'] >= 1 and n['show'] and await pg.evaluate(f"()=>{K}.G.tasks.route.on&&!{K}.G.tasks.hdg"), (r, n['show']))
        t0 = await pg.evaluate(f"()=>{K}.NAV.t0[0]")
        await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
        # the out legs
        calls = []
        start_leg = (await pg.evaluate(NAVS))['leg']
        for i in range(start_leg, 4):
            if i == 2:   # cruise between Tolleson and downtown, clear of every runway: the log in the readout's place
                await fly(pg, 400, hold=3500, kt=105, vs=0, hdg=(await pg.evaluate(NAVS))['legs'][2]['c'], until=ASK)
                calls.append(1 if await answer(pg) else 0)
                await pg.evaluate(f"()=>{{{K}.stepFrame(0.1,false,false);{K}.stepFrame(0,true)}}"); await pg.wait_for_timeout(200)
                v = await pg.evaluate(VIS)
                ok('(b) cruise: the log up in the left column (outside the centre third), the readout hidden, LOG lit, header and 4 rows uncut', not v['appr'] and v['log'] and not v['dest'] and v['lit'] == 'true' and v['box'][2] <= v['W'] / 3 and v['inside'] and v['h'] <= 92, v)
                await pg.screenshot(path='/tmp/sch2_xc_cruise.png')
            calls.append(await fly_leg(pg, i, 3500))
        n = await pg.evaluate(NAVS)
        ok('(b) the out legs passed in turn, each time stamped', n['leg'] == 4 and all(l['at'] is not None and not l['miss'] for l in n['legs'][:4]), n['legs'][:4])
        ok('(b) the Bravo request and readback, then the Phoenix Tower readback (CALLs answered)', sum(calls) >= 3, calls)
        bv = await pg.evaluate(f"()=>{K}.G.tasks.bravo")
        ok('(b) bravo passed: cleared into the Class Bravo, read back', bv and bv['ok'] and 'read back' in bv['detail'], bv)
        radio = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()")]
        ok('(b) Approach: squawk 4521, cleared into the Class Bravo airspace', any('cleared into the Class Bravo airspace' in t and 'squawk 4521' in t for t in radio), radio[-8:])
        R = await pg.evaluate(ROWS)
        await pg.screenshot(path='/tmp/sch2_xc_out.png')
        ok('(b) inside 5 nm of Sky Harbor the marker is on runway 7L', (await pg.evaluate(f"()=>{K}.dest()"))['name'] == 'Sky Harbor runway 7L', await pg.evaluate(f"()=>{K}.dest()"))
        # Sky Harbor runway 7L: a touchdown 300 m past the threshold, then a stop
        tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1751+300,-300),K.shZ(-1751+300,-300)]}")
        await fly(pg, 2, x=tx, z=tz, agl=20, kt=62, vs=-200, hdg=92)
        await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:180,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [tx, tz])
        await fly(pg, 2, agl=10, kt=55, vs=-100, hdg=92)
        ph = await pg.evaluate(f"()=>{K}.G.tasks.phx")
        ok('(b) the touchdown on Sky Harbor 7L: phx passed', ph and ph['ok'] and '07L' in ph['detail'], ph)
        sx, sz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1751+900,-300),K.shZ(-1751+900,-300)]}")
        r = await pg.evaluate(f"""([x,z])=>{{const K={K};for(let i=0;i<30&&K.LES.on;i++){{const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;s.throttle=0;K.stepFrame(0.1,false,true);}}
          K.stepFrame(0,true);return {{on:K.LES.on,ph:K.LES.ph,show:K.NAV.show,leg:K.NAV.leg}}}}""", [sx, sz])
        ok('(b) stopped at Sky Harbor: phase 4, the log closed, the return legs next', r['on'] == 'pilotage' and r['ph'] == 4 and not r['show'] and r['leg'] == 4, r)
        dana = await pg.evaluate(DANA)
        ok('(b) Dana: welcome to Sky Harbor, 4,500 home', any('Welcome to Sky Harbor' in t and '4,500' in t for t in dana), dana[-3:])
        # the climb out home
        r = await fly(pg, 200, x=sx, z=sz, agl=1300, kt=74, vs=700, hdg=287, until='K.LES.d.ret===1')
        await finger(pg, '#lesLog') if not (await pg.evaluate(NAVS))['show'] else None
        R = await pg.evaluate(ROWS)
        ok('(b) on course home: the log shows the 4 return rows', r['d'] is not None and len(R) == 4 and [x[0] for x in R] == ['Downtown', 'Tolleson', 'Stadium', 'Glendale'], R)
        await fly(pg, 150, hold=4500, kt=90, vs=0, hdg=287)
        for i in range(4, 7):
            await fly_leg(pg, i, 4500)
        n = await pg.evaluate(NAVS)
        ph5 = await pg.evaluate(f"()=>{K}.LES.ph")
        # inside 5 nm of Glendale: the inbound call, the tower's landing clearance and the readback (some may be done on the legs)
        hg = await pg.evaluate(f"()=>{{const K={K},s=K.state(),F=K.rwyFrame(),u=F.thr;return (Math.atan2(K.wX(u,0)-s.pos.x,-(K.wZ(u,0)-s.pos.z))*180/Math.PI+360)%360}}")
        await taps(pg, 4500, hg, k=2, n=300)
        tw = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'].startswith('Glendale Tower')]
        me = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'] == 'Skyhawk 8401L']
        ok('(b) Glendale: phase 5, the inbound call, cleared to land, read back', ph5 == 5 and any('inbound full stop' in t for t in me) and any('cleared to land' in t for t in tw) and any(t.startswith('Cleared to land') for t in me), (ph5, me[-4:], tw[-3:]))
        await final(pg, F)
        await touchdown(pg, F, past=60, fpm=160)
        r = await stop(pg, F)
        await pg.wait_for_timeout(800)
        d = await pg.evaluate(DEBRIEF)
        names = [x[0] for x in d['rows']]
        ok('(b) the TRK hold in nm', 'nm' in d['rows'][2][2] if d['rows'] else False, d['rows'][:3])
        ok('(b) the debrief: the 8 task rows', d['on'] and names == ['Cruise altitude held', 'Heading on each leg', 'Within 3 nm of the route', 'Checkpoints within 5 min of ETA', 'Class Bravo clearance obtained', 'Landed at Sky Harbor', 'Landed back at Glendale', 'Touchdowns under 300 fpm'], d)
        row = {x[0]: x for x in d['rows']}
        ok('(b) bravo, phx and home passed', row.get('Class Bravo clearance obtained', [0, 0])[1] and row.get('Landed at Sky Harbor', [0, 0])[1] and row.get('Landed back at Glendale', [0, 0])[1], d['rows'])
        ok('(b) the ETA row in minutes at a named checkpoint, the worse touchdown of 2', ' min' in row.get('Checkpoints within 5 min of ETA', ['', '', ''])[2] and 'worse of 2' in row.get('Touchdowns under 300 fpm', ['', '', ''])[2], d['rows'])
        bn = await pg.evaluate("()=>[...document.querySelectorAll('#badges .badge.on')].map(e=>e.textContent)")
        ok('(b) no NEW RECORD banner over the debrief (a lesson landing)', not any('NEW RECORD' in t for t in bn), bn)
        ok('(b) letter A or B', d['letter'] in ('A', 'B'), (d['letter'], d['res']))
        ok('(b) the destination cleared at the end', await pg.evaluate(f"()=>{K}.dest()") is None)
        await pg.screenshot(path='/tmp/sch2_xc_debrief.png')
        print('  debrief', d['letter'], d['res']['score'] if d['res'] else None, d['rows'])

        # ---------------- (c) the Bravo call skipped ----------------
        await pg.evaluate(f"()=>{K}.resClose(document.getElementById('gradeOv'))")
        await start(pg, 'pilotage')
        await call(pg)
        r = await fly(pg, 200, x=x, z=z, agl=1300, kt=74, vs=700, hdg=60, until='K.LES.ph>=1')
        n = await pg.evaluate(NAVS)
        # 1 nm short of Tolleson on its leg, then 6 nm west of the field on the next one: no CALL tapped
        tx, tz = n['x'][1][2], n['x'][1][3]
        await fly(pg, 1, x=tx, z=tz - 1852, hold=3500, kt=105, vs=0, hdg=n['legs'][1]['c'])
        await fly(pg, 300, hold=3500, kt=105, vs=0, hdg=n['legs'][1]['c'], until='K.NAV.leg>1')
        ax, az = await pg.evaluate("()=>{const K=window.__kgeu;return [K.SKY_HARBOR.x-6*1852,K.SKY_HARBOR.z]}")
        await fly(pg, 1, x=ax, z=az, hold=3500, kt=105, vs=0, hdg=90)
        await fly(pg, 3000, hold=3500, kt=105, vs=0, hdg=90, until="Math.hypot(K.state().pos.x-K.SKY_HARBOR.x,K.state().pos.z-K.SKY_HARBOR.z)<9000")
        bv = await pg.evaluate(f"()=>{K}.G.tasks.bravo")
        dana = await pg.evaluate(DANA)
        ok('(c) inside the ring without the call: bravo failed, the violation text', bv and not bv['ok'] and bv['detail'] == 'entered the Bravo without a clearance', bv)
        ok('(c) Dana: a violation, call them now', any('without a clearance. That is a violation' in t for t in dana), dana[-3:])
        await fly(pg, 300, hold=3500, kt=105, vs=0, hdg=90, until=ASK)
        ok('(c) the call still offered: Request the Bravo', await pg.evaluate(f"()=>{{const a={K}.TASK.ask;return !!(a&&a.shown&&a.opts[0].sub==='Request the Bravo')}}"))
        # a touchdown in the desert ends it: the debrief's bravo row fails with the violation
        q = await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.pos.x,s.pos.z]}")
        await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:200,paved:false,x:x,z:z,ias:33,bank:0}})}}", q)
        await fly(pg, 2, kt=100, vs=0, hdg=90)
        await pg.wait_for_timeout(600)
        d = await pg.evaluate(DEBRIEF)
        row = {x[0]: x for x in d['rows']}
        ok('(c) the debrief: bravo fails with the violation text', d['on'] and row.get('Class Bravo clearance obtained') and not row['Class Bravo clearance obtained'][1] and row['Class Bravo clearance obtained'][2] == 'entered the Bravo without a clearance', d['rows'])
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_xc_check'))
asyncio.run(main())
