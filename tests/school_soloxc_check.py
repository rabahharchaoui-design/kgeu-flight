# School2 item 4: Stage 3 lesson 4, the solo cross country (the pilotage trip, nobody in the right seat).
# (a) Stage 3 shows the four lesson rows with soloxc a normal row; the row tap opens its briefing (card title Solo XC).
# (b) flown well, as school_xc_check's clean run: Dana says only her start line before the debrief (the radio log filtered
# to Dana has exactly one line until then), the CALLs still come with the controllers' lines, the card carries the Bravo
# prompt; the debrief: the 8 task rows, the Endorsement row first with 'Solo cross country', kgeuEndorse.xc, the logbook
# entry 1.5 solo and 1.5 XC, an A or a B, Dana's endorsement line. (c) the Bravo call skipped: entering the 5 nm ring fails
# the bravo row with the violation text and no spoken line. (d) no page errors.
# Run: .venv/bin/python tests/school_soloxc_check.py
import asyncio, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, FLY, start, rwy, call, final, touchdown, stop
ok = Checks()
NAVS = f"()=>{{const N={K}.NAV;return {{leg:N.leg,on:N.on,show:N.show,legs:N.legs.map(l=>({{to:l.to.short,c:l.course,seg:l.seg,at:l.at,miss:l.miss,eta:l.eta}})),x:N.legs.map(l=>[l.from.x,l.from.z,l.to.x,l.to.z])}}}}"
ASK = "K.TASK.ask&&K.TASK.ask.shown"
FLYH = FLY.replace("if(o.alt!=null)", "if(o.hold!=null)s.pos.y+=(o.hold-K.G.alt)/3.28084;if(o.alt!=null)")
LESI = "()=>document.getElementById('lesI').textContent"

async def fly(pg, n, **o):
    return await pg.evaluate(FLYH, [n, o])

async def answer(pg):
    return await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")

async def taps(pg, hold, hdg, k=2, n=400):
    m = 0
    for _ in range(k):
        await fly(pg, n, hold=hold, kt=105, vs=0, hdg=hdg, until=ASK)
        if await answer(pg): m += 1
    return m

async def leg(pg, i, alt, kt=105):
    n = await pg.evaluate(NAVS)
    c = n['legs'][i]['c']
    return await fly(pg, 6000, hold=alt, kt=kt, vs=0, hdg=c, until=f"K.NAV.leg>{i}||({ASK})")

async def fly_leg(pg, i, alt, cards=None):
    """leg i to its fix, answering every CALL on the way (the card's line noted first); the CALLs answered"""
    calls = 0
    for _ in range(6):
        await leg(pg, i, alt)
        if (await pg.evaluate(NAVS))['leg'] > i: break
        if cards is not None:
            await pg.evaluate(f"()=>{{{K}.stepFrame(0.05,false,true);{K}.stepFrame(0,true)}}")
            cards.append(await pg.evaluate(LESI))
        if await answer(pg): calls += 1
    return calls

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # ---------------- (a) the school screen ----------------
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(200)
        await finger(pg, '#hSch'); await pg.wait_for_timeout(400)
        await finger(pg, '.sNode[data-st=s3]'); await pg.wait_for_timeout(400)
        rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.classList.contains('soon')])")
        ok('(a) Stage 3: four lesson rows, soloxc a normal row', rows == [['pilotage', False], ['divert', False], ['night', False], ['soloxc', False]], rows)
        await finger(pg, '#school .lrow[data-l=soloxc]'); await pg.wait_for_timeout(600)
        r = await pg.evaluate(f"()=>({{on:{K}.LES.on,brief:document.getElementById('brOv').classList.contains('on'),t:document.getElementById('brT').textContent,c:document.getElementById('lesT').textContent}})")
        ok('(a) the row tap opens the solo cross country briefing, card title Solo XC', r == {'on': 'soloxc', 'brief': True, 't': 'Solo cross country', 'c': 'Solo XC'}, r)
        await pg.close()

        # ---------------- (b) flown well ----------------
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await start(pg, 'soloxc'); F = await rwy(pg)
        n = await pg.evaluate(NAVS)
        ok('(b) the pilotage plan: 4 legs out, 4 back', [l['seg'] for l in n['legs']] == [0, 0, 0, 0, 1, 1, 1, 1], n['legs'])
        c0 = await call(pg)
        ok('(b) the takeoff clearance read back', c0)
        dana0 = await pg.evaluate(DANA)
        ok('(b) Dana on the ground: her one start line', len(dana0) == 1 and dana0[0].startswith('This one is yours.') and 'come home' in dana0[0], dana0)
        x, z = await pg.evaluate(f"()=>{{const K={K},u=K.rwyFrame().thr+1700;return [K.wX(u,0),K.wZ(u,0)]}}")
        r = await fly(pg, 200, x=x, z=z, agl=1300, kt=74, vs=700, hdg=60, until='K.LES.ph>=1')
        n = await pg.evaluate(NAVS)
        ok('(b) on course: phase 1, the log open, the route hold on', r['ph'] >= 1 and n['show'], (r, n['show']))
        await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
        calls, cards = [], []
        for i in range((await pg.evaluate(NAVS))['leg'], 4):
            calls.append(await fly_leg(pg, i, 3500, cards))
        n = await pg.evaluate(NAVS)
        ok('(b) the out legs passed in turn', n['leg'] == 4 and all(l['at'] is not None and not l['miss'] for l in n['legs'][:4]), n['legs'][:4])
        ok('(b) the Bravo request, readback and Phoenix Tower readback on CALL', sum(calls) >= 3, calls)
        ok('(b) the card carries the Bravo prompt (under 34 characters)', 'Call Phoenix Approach: tap CALL.' in cards and all(len(c) <= 34 for c in cards), cards)
        bv = await pg.evaluate(f"()=>{K}.G.tasks.bravo")
        ok('(b) bravo passed', bv and bv['ok'], bv)
        radio = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()")]
        ok('(b) Approach still talks: cleared into the Class Bravo airspace', any('cleared into the Class Bravo airspace' in t for t in radio), radio[-8:])
        tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5+300,361),K.shZ(-1442.5+300,361)]}")
        await fly(pg, 2, x=tx, z=tz, agl=20, kt=62, vs=-200, hdg=90)
        await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:180,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [tx, tz])
        await fly(pg, 2, agl=10, kt=55, vs=-100, hdg=90)
        sx, sz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5+900,361),K.shZ(-1442.5+900,361)]}")
        r = await pg.evaluate(f"""([x,z])=>{{const K={K};for(let i=0;i<30&&K.LES.on;i++){{const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;s.throttle=0;K.stepFrame(0.1,false,true);}}
          K.stepFrame(0,true);return {{on:K.LES.on,ph:K.LES.ph,leg:K.NAV.leg,i:document.getElementById('lesI').textContent}}}}""", [sx, sz])
        ok('(b) stopped at Sky Harbor: phase 4, the card says what to do, no welcome', r['on'] == 'soloxc' and r['ph'] == 4 and r['leg'] == 4 and '4,500' in r['i'], r)
        r = await fly(pg, 200, x=sx, z=sz, agl=1300, kt=74, vs=700, hdg=287, until='K.LES.d.ret===1')
        await fly(pg, 150, hold=4500, kt=90, vs=0, hdg=287)
        for i in range(4, 7):
            await fly_leg(pg, i, 4500)
        hg = await pg.evaluate(f"()=>{{const K={K},s=K.state(),F=K.rwyFrame(),u=F.thr;return (Math.atan2(K.wX(u,0)-s.pos.x,-(K.wZ(u,0)-s.pos.z))*180/Math.PI+360)%360}}")
        await taps(pg, 4500, hg, k=2, n=300)
        me = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'] == 'Skyhawk 8401L']
        ok('(b) Glendale: the inbound call and the landing readback', any('inbound full stop' in t for t in me) and any(t.startswith('Cleared to land') for t in me), me[-4:])
        await final(pg, F)
        await touchdown(pg, F, past=60, fpm=160)
        dana1 = await pg.evaluate(DANA)
        ok('(b) Dana silent after her start line, all the way home (one line before the debrief)', len(dana1) == 1, dana1)
        await stop(pg, F)
        await pg.wait_for_timeout(800)
        d = await pg.evaluate(DEBRIEF)
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: the 8 task rows', d['on'] and names == ['Cruise altitude held', 'Heading on each leg', 'Within 3 nm of the route', 'Checkpoints within 5 min of ETA', 'Class Bravo clearance obtained', 'Landed at Sky Harbor', 'Landed back at Glendale', 'Touchdowns under 300 fpm'], d)
        ok('(b) letter A or B', d['letter'] in ('A', 'B'), (d['letter'], d['res']))
        ok('(b) the Endorsement row first: Solo cross country', d['gl'] and d['gl'][0] == ['Endorsement', 'Solo cross country, signed by Dana Reyes, CFI'], d['gl'][:2])
        e = await pg.evaluate("()=>JSON.parse(localStorage.getItem('kgeuEndorse')||'{}').xc")
        ok('(b) kgeuEndorse.xc signed by Dana', e and e['by'] == 'Dana Reyes, CFI' and e['lesson'] == 'soloxc', e)
        lg = await pg.evaluate("()=>{const e=JSON.parse(localStorage.getItem('kgeuLogbook')||'{}').entries||[];return e[e.length-1]}")
        ok('(b) the logbook entry: 1.5 solo, 1.5 XC, no dual, 2 landings', lg and lg['id'] == 'soloxc' and lg['solo'] == 1.5 and lg['xc'] == 1.5 and lg['dual'] == 0 and lg['ldg'] == 2, lg)
        dana2 = await pg.evaluate(DANA)
        ok('(b) Dana at the debrief: the solo cross country endorsement', len(dana2) == 2 and 'That is your solo cross country endorsement. I am signing your logbook.' in dana2[1], dana2)
        print('  debrief', d['letter'], d['res']['score'] if d['res'] else None)
        # the endorsement row wraps instead of cutting; the solo's short one stays on one line at 844
        await pg.set_viewport_size({'width': 844, 'height': 390}); await pg.wait_for_timeout(250)
        EB = "()=>{const b=document.querySelector('#gLines .gEnd b');const lh=parseFloat(getComputedStyle(b).lineHeight)||18;return {cut:b.scrollWidth>b.clientWidth+1,lines:Math.round(b.getBoundingClientRect().height/lh),ws:getComputedStyle(b).whiteSpace}}"
        e1 = await pg.evaluate(EB)
        ok('(b) 844: the Solo cross country endorsement reads in full (wraps, no ellipsis)', not e1['cut'] and e1['ws'] == 'normal' and e1['lines'] <= 2, e1)
        await pg.evaluate("()=>{document.querySelector('#gLines .gEnd b').textContent='Solo, signed by Dana Reyes, CFI'}")
        e2 = await pg.evaluate(EB)
        ok('(b) 844: the solo row (Solo, signed by Dana Reyes, CFI) on one line', not e2['cut'] and e2['lines'] == 1, e2)
        await pg.screenshot(path='/tmp/sch2_soloxc_debrief.png')
        BN = "()=>{const e=document.getElementById('banner');return {on:e.classList.contains('on'),vis:!!e.offsetParent&&getComputedStyle(e).opacity!=='0'&&e.classList.contains('on'),t:e.textContent}}"
        bn = await pg.evaluate(BN)
        ok('(b) no achievement or record pop over the open debrief', not bn['vis'], bn)
        await pg.evaluate(f"()=>{K}.resClose(document.getElementById('gradeOv'))"); await pg.wait_for_timeout(200)
        bn2 = await pg.evaluate(BN)
        ok('(b) the held pop is released once the debrief closes', bn2['on'] and 'ACHIEVEMENT' in bn2['t'] or not bn2['t'], bn2)

        # ---------------- (c) the Bravo call skipped ----------------
        await start(pg, 'soloxc')
        await call(pg)
        r = await fly(pg, 200, x=x, z=z, agl=1300, kt=74, vs=700, hdg=60, until='K.LES.ph>=1')
        n = await pg.evaluate(NAVS)
        tx, tz = n['x'][1][2], n['x'][1][3]
        await fly(pg, 1, x=tx, z=tz - 1852, hold=3500, kt=105, vs=0, hdg=n['legs'][1]['c'])
        await fly(pg, 300, hold=3500, kt=105, vs=0, hdg=n['legs'][1]['c'], until='K.NAV.leg>1')
        ax, az = await pg.evaluate("()=>{const K=window.__kgeu;return [K.SKY_HARBOR.x-6*1852,K.SKY_HARBOR.z]}")
        await fly(pg, 1, x=ax, z=az, hold=3500, kt=105, vs=0, hdg=90)
        await fly(pg, 3000, hold=3500, kt=105, vs=0, hdg=90, until="Math.hypot(K.state().pos.x-K.SKY_HARBOR.x,K.state().pos.z-K.SKY_HARBOR.z)<9000")
        bv = await pg.evaluate(f"()=>{K}.G.tasks.bravo")
        dana = await pg.evaluate(DANA)
        ok('(c) inside the ring without the call: bravo failed, the violation text', bv and not bv['ok'] and bv['detail'] == 'entered the Bravo without a clearance', bv)
        ok('(c) no spoken line from Dana: only her start line', len(dana) == 1 and dana[0].startswith('This one is yours.'), dana)
        q = await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.pos.x,s.pos.z]}")
        await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:200,paved:false,x:x,z:z,ias:33,bank:0}})}}", q)
        await fly(pg, 2, kt=100, vs=0, hdg=90)
        await pg.wait_for_timeout(600)
        d = await pg.evaluate(DEBRIEF)
        row = {x[0]: x for x in d['rows']}
        ok('(c) the debrief: bravo fails with the violation text, no endorsement row', d['on'] and row.get('Class Bravo clearance obtained') and not row['Class Bravo clearance obtained'][1] and row['Class Bravo clearance obtained'][2] == 'entered the Bravo without a clearance' and not any(g[0] == 'Endorsement' for g in d['gl']), (d['rows'], d['gl'][:1]))
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_soloxc_check'))
asyncio.run(main())
