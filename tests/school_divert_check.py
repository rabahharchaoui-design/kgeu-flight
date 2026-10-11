# School2 item 2: Stage 3 lesson 2, diversion and lost procedures.
# (a) flown well at 844x390, pinned frame by frame (tests/school_fly.py): airborne at 3,500 short of downtown with the nav log
# on; past downtown the dust storm and the GPS failure open the diversion card (the mini map, the log and the marker gone);
# real taps on the steppers and SET (page.click, 44 px controls) set a heading and a time; both estimates graded; the plan
# flown pinned at 4,500 on the picked heading; the CALL for vectors answered (Approach: radar contact, the clock position);
# inside 3 nm of Glendale the map and the marker are back; the tower call, a touchdown on runway 1 and a stop; the debrief's
# 7 rows and a letter. (b) at 568x320: the card fits beside the lesson card, under the top edge, above the dock and the
# throttle, clear of the centre column; no SET for 90 s: the plan sets itself, Dana says so. (c) no page errors.
# Run: .venv/bin/python tests/school_divert_check.py   (a or b alone: ... school_divert_check.py a)
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, FLY, start, rwy, final, touchdown, stop
ok = Checks()
ASK = "K.TASK.ask&&K.TASK.ask.shown"
HOLD = f"()=>{K}.stepFrame(0.001,false,true)"
FLYH = FLY.replace("if(o.alt!=null)", "if(o.hold!=null)s.pos.y+=(o.hold-K.G.alt)/3.28084;if(o.alt!=null)")
# Glendale's runway centre from here: the magnetic bearing, the distance (nm)
GLN = """()=>{const K=window.__kgeu,s=K.state(),x=K.LES.d.G0.x,z=K.LES.d.G0.z,dx=x-s.pos.x,dz=z-s.pos.z;
  return {brg:((Math.atan2(dx,-dz)*180/Math.PI-12)%360+360)%360,nm:Math.hypot(dx,dz)/1852}}"""
UI = """()=>{const g=id=>document.getElementById(id),vis=e=>!!e&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0;
  return {card:g('divCard').classList.contains('on'),map:vis(g('map')),log:vis(g('navLog')),lesLog:!g('lesLog').hidden,dest:window.__kgeu.dest()}}"""
RECTS = """()=>{const R=s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};
  return {card:R('#divCard'),les:R('#lesson'),top:R('#topCol'),dock:R('#uiroot > #dock'),thr:R('#thrCol'),pause:R('#bPause'),W:innerWidth,H:innerHeight,
    btn:[...document.querySelectorAll('#divCard button')].map(b=>{const r=b.getBoundingClientRect();return [r.width,r.height]})}}"""

async def fly(pg, n, **o):
    return await pg.evaluate(FLYH, [n, o])

def sep(a, b):
    return a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]

async def to_card(pg):
    c = await pg.evaluate(f"()=>{K}.NAV.legs[2].course")
    return await fly(pg, 3000, hold=3500, kt=105, vs=0, hdg=c, until="K.DIV.on")

async def main():
    srv, url = serve()
    part = sys.argv[1] if len(sys.argv) > 1 else 'ab'
    async with async_playwright() as p:
        b = await launch(p)
        if 'a' in part: await run_a(b, url)
        if 'b' in part: await run_b(b, url)
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_divert_check'))

async def run_a(b, url):
    if True:
        # ---------------- (a) flown well ----------------
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await start(pg, 'divert'); F = await rwy(pg)
        await fly(pg, 3, hold=3500, kt=105, vs=0, hdg=await pg.evaluate(f"()=>{K}.NAV.legs[2].course"))
        s0 = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),T=K.NAV.legs[2].to;return {{on:K.LES.on,ph:K.LES.ph,alt:Math.round(K.G.alt),air:!s.onGround,
          nm:Math.hypot(s.pos.x-T.x,s.pos.z-T.z)/1852,leg:K.NAV.leg,show:K.NAV.show,t:document.getElementById('lesT').textContent}}}}""")
        ui = await pg.evaluate(UI)
        ok('(a) airborne at 3,500 short of downtown, on its leg, the card title Diversion', s0['on'] == 'divert' and s0['air'] and abs(s0['alt'] - 3500) < 30 and s0['nm'] < 3 and s0['leg'] == 2 and s0['t'] == 'Diversion', s0)
        ok('(a) the nav log on (LOG up; the log itself waits out the approach ring here), the map up, the marker on downtown', s0['show'] and ui['lesLog'] and ui['map'] and ui['dest'] and ui['dest']['name'] == 'Downtown Phoenix', ui)
        r = await to_card(pg)
        dana = await pg.evaluate(DANA)
        ok('(a) past downtown Dana names Sky Harbor, then the storm opens the diversion card', r['ph'] == 3 and any(t.startswith('Downtown. Next is Sky Harbor') for t in dana), (r, dana[-3:]))
        await fly(pg, 3, hold=3500, kt=105, vs=0, hdg=(await pg.evaluate(GLN))['brg'] + 12)
        sub = await pg.evaluate("()=>document.getElementById('atc').textContent")
        ok('(a) the card opens with the dust storm line as the subtitle on screen', 'dust storm over Sky Harbor' in sub and 'GPS just dropped out' in sub, sub)
        await fly(pg, 80, hold=3500, kt=105, vs=0, hdg=(await pg.evaluate(GLN))['brg'] + 12)
        ui = await pg.evaluate(UI)
        ok('(a) the GPS gone: no mini map, no log, no LOG, no marker; the card up', ui['card'] and not ui['map'] and not ui['log'] and not ui['lesLog'] and ui['dest'] is None, ui)
        dana = await pg.evaluate(DANA)
        ok('(a) Dana: the dust storm, the diversion; the GPS dropped out, one line later', any('dust storm over Sky Harbor' in t and 'diverting to Glendale' in t for t in dana) and any('GPS just dropped out' in t for t in dana), dana[-2:])
        await pg.screenshot(path='/tmp/sch2_div_card.png')
        # the estimates by real taps: the heading to the 5 degrees nearest Glendale's bearing, the minutes at 105 kt
        gl = await pg.evaluate(GLN)
        want = int(round(gl['brg'] / 5) * 5) % 360 or 360
        mins = max(1, int(round(gl['nm'] / 105 * 60)))
        await pg.evaluate(HOLD)   # the frame loop held while the fingers work (the next fly() hands it back): no drift between taps
        h0 = await pg.evaluate(f"()=>{K}.DIV.h")
        dh = ((want - h0 + 540) % 360) - 180
        taps = 0
        while dh != 0 and taps < 40:
            step = 10 if dh >= 10 else -10 if dh <= -10 else 5 if dh > 0 else -5
            await pg.click(f'#divCard [data-h="{step}"]'); dh -= step; taps += 1
        await pg.click('#divCard [data-h="5"]'); await pg.click('#divCard [data-h="-5"]')   # +5 then -5, by hand
        m0 = await pg.evaluate(f"()=>{K}.DIV.m")
        for _ in range(abs(mins - m0)):
            await pg.click('#divCard [data-m="%d"]' % (1 if mins > m0 else -1))
        d = await pg.evaluate(f"()=>({{h:{K}.DIV.h,m:{K}.DIV.m,txt:document.getElementById('divH').textContent+'|'+document.getElementById('divM').textContent}})")
        ok('(a) the steppers set the heading and the minutes (3 digits magnetic on the card)', d['h'] == want and d['m'] == mins and d['txt'].startswith('%03d' % want), (d, want, mins, gl))
        await pg.click('#divSet')
        g = await pg.evaluate(f"()=>({{h:{K}.G.tasks.est_hdg,m:{K}.G.tasks.est_eta,ph:{K}.LES.ph,card:document.getElementById('divCard').classList.contains('on')}})")
        ok('(a) SET closes the card, est_hdg and est_eta graded and passed', not g['card'] and g['ph'] == 4 and g['h'] and g['h']['ok'] and g['m'] and g['m']['ok'], g)
        await fly(pg, 400, hold=3500, kt=105, vs=0, hdg=(want + 12) % 360, until="K.radioLog().some(l=>/we are westbound now/.test(l.text))")   # after the storm line, never over it
        dana = await pg.evaluate(DANA)
        ok("(a) Dana reads the plan back: heading, minutes, climb to 4,500 westbound", any(t.startswith('Heading %03d' % want) and '4,500, we are westbound' in t for t in dana), dana[-2:])
        tgt = (want + 12) % 360
        await fly(pg, 1, alt=4500, kt=105, vs=0, hdg=tgt)
        r = await fly(pg, 400, hold=4500, kt=105, vs=0, hdg=tgt, until=ASK)
        sub = await pg.evaluate(f"()=>{K}.TASK.ask&&{K}.TASK.ask.opts[0].sub")
        ok('(a) about 15 s after SET: CALL, Request vectors', sub == 'Request vectors', (sub, r))
        await pg.evaluate(HOLD)
        await pg.click('#tkReply button')
        await fly(pg, 300, hold=4500, kt=105, vs=0, hdg=tgt, until="K.radioLog().some(l=>/radar contact/.test(l.text))")
        radio = await pg.evaluate(f"()=>{K}.radioLog()")
        me = [l['text'] for l in radio if l['who'] == 'Skyhawk 8401L']
        ap = [l['text'] for l in radio if l['who'].startswith('Phoenix Approach')]
        ok('(a) the confession and Approach: radar contact, Glendale at a clock position and miles', any('unsure of position west of Phoenix' in t for t in me) and any("radar contact, Glendale is at your" in t and "o'clock" in t and 'mile' in t for t in ap), (me[-1:], ap[-1:]))
        ok('(a) the call event passed', (await pg.evaluate(f"()=>{K}.G.tasks.call"))['ok'])
        r = await fly(pg, 6000, hold=4500, kt=105, vs=0, hdg=tgt, until='K.LES.ph>=5')
        await fly(pg, 300, hold=4500, kt=105, vs=0, hdg=tgt, until="K.radioLog().some(l=>/The GPS is back/.test(l.text))")
        ui = await pg.evaluate(UI)
        dana = await pg.evaluate(DANA)
        ok('(a) inside 3 nm: the GPS back, the map up, the marker on runway 1', r['ph'] == 5 and ui['map'] and ui['dest'] and ui['dest']['name'] == 'Glendale runway 1' and any('The GPS is back' in t for t in dana), (r, ui))
        ev = await pg.evaluate(f"()=>{K}.G.tasks.eta")
        ok('(a) the arrival graded against the estimate', ev and ev['ok'] and 'estimate' in ev['detail'], ev)
        await pg.screenshot(path='/tmp/sch2_div_back.png')
        # the tower: the inbound call, cleared to land, read back
        for _ in range(4):
            await fly(pg, 600, hold=4500, kt=90, vs=0, hdg=tgt, until=ASK)
            await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
            if await pg.evaluate(f"()=>{K}.radioLog().some(l=>l.who==='Skyhawk 8401L'&&/^Cleared to land/.test(l.text))"): break
        tw = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'].startswith('Glendale Tower')]
        me = [l['text'] for l in await pg.evaluate(f"()=>{K}.radioLog()") if l['who'] == 'Skyhawk 8401L']
        ok('(a) Glendale: 3 miles inbound full stop, cleared to land, read back', any('3 miles' in t and 'inbound full stop' in t for t in me) and any('cleared to land' in t for t in tw) and any(t.startswith('Cleared to land') for t in me), (me[-3:], tw[-2:]))
        await final(pg, F)
        await touchdown(pg, F, past=60, fpm=160)
        await stop(pg, F)
        await pg.wait_for_timeout(800)
        d = await pg.evaluate(DEBRIEF)
        names = [x[0] for x in d['rows']]
        ok('(a) the debrief: the 7 task rows', d['on'] and names == ['Heading estimate within 15 degrees', 'Time estimate within 5 minutes', 'Diversion heading held', 'Altitude held', 'Arrived within 5 min of the estimate', 'Confessed and asked for vectors', 'Landed at Glendale'], d['rows'])
        ok('(a) every row passed, letter A or B', all(x[1] for x in d['rows']) and d['letter'] in ('A', 'B'), (d['letter'], d['rows']))
        pop = await pg.evaluate("()=>[...document.querySelectorAll('#badges .badge')].filter(e=>e.classList.contains('on')&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'&&+getComputedStyle(e).opacity>0.05).map(e=>e.textContent)")
        ok('(a) no achievement or record pop over the debrief', not any('ACHIEVEMENT' in t or 'NEW RECORD' in t for t in pop), pop)
        ok('(a) the map class cleared at the end', not await pg.evaluate("()=>document.body.classList.contains('navMapOff')||document.body.classList.contains('divOn')"))
        await pg.screenshot(path='/tmp/sch2_div_debrief.png')
        print('  debrief', d['letter'], d['res']['score'] if d['res'] else None, d['rows'])
        ok('(c) no page errors (a)', not pg.errs, pg.errs[:3])
        await pg.close()

async def run_b(b, url):
    if True:
        # ---------------- (b) 568x320: the card's place; no SET for 90 s ----------------
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage=dict(BASE, **PLACED))
        await start(pg, 'divert')
        await to_card(pg)
        await fly(pg, 20, hold=3500, kt=105, vs=0, hdg=300)
        await pg.wait_for_timeout(400)
        R = await pg.evaluate(RECTS)
        c = R['card']
        ok('(b) 568: every card control 44 px or more', all(w >= 44 and h >= 44 for w, h in R['btn']), R['btn'])
        ok('(b) 568: the card on screen, right of pause, above the dock and the throttle', c[0] >= R['pause'][2] and c[2] <= R['W'] and c[1] >= 0 and c[3] <= R['dock'][1] and c[3] <= R['thr'][1], R)
        ok('(b) 568: clear of the lesson card and the centre column', sep(c, R['les']) and sep(c, R['top']), R)
        ok('(b) 568: the card inside the top third (never in the centre third)', c[3] <= R['H'] / 3 + 0.5, (c, R['H'] / 3))
        await pg.screenshot(path='/tmp/sch2_div_568.png')
        r = await fly(pg, 1000, hold=3500, kt=105, vs=0, hdg=300, until='!K.DIV.on')
        g = await pg.evaluate(f"()=>({{h:{K}.G.tasks.est_hdg,m:{K}.G.tasks.est_eta,ph:{K}.LES.ph,p:{K}.LES.d.plan}})")
        dana = await pg.evaluate(DANA)
        ok('(b) no SET for 90 s: the plan sets itself on the current heading and 5 minutes, both graded', g['ph'] == 4 and g['p'] and g['p']['m'] == 5 and abs(((g['p']['h'] - 288 + 540) % 360) - 180) <= 1 and g['h'] and g['m'], g)
        ok("(b) Dana: I will take that as your plan", any(t.startswith('I will take that as your plan') for t in dana), dana[-2:])
        # the CALL for vectors ignored: the event fails, Dana says so once
        away = ((await pg.evaluate(GLN))['brg'] + 12 + 180) % 360   # away from Glendale: the 30 s run out before the field
        await fly(pg, 1000, hold=4500, kt=105, vs=0, hdg=away, until="K.G.tasks.call")
        await fly(pg, 300, hold=4500, kt=105, vs=0, hdg=away, until="K.radioLog().some(l=>/Confess. Call them/.test(l.text))")
        cl = await pg.evaluate(f"()=>{K}.G.tasks.call")
        dana = await pg.evaluate(DANA)
        ok('(b) no call: the call row fails, never asked for vectors; Dana: confess, call them', cl and not cl['ok'] and cl['detail'] == 'never asked for vectors' and sum('Confess. Call them.' in t for t in dana) == 1, (cl, dana[-2:]))
        ok('(c) no page errors (b)', not pg.errs, pg.errs[:3])
        await pg.close()
asyncio.run(main())
