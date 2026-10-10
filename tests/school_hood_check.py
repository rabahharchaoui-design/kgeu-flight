# School1 item 7: under the hood. (a) the hood: the cockpit view, #hood shown over the whole viewport, before #uiroot with no z-index (every readout, button, the lesson card and its cue strip draw over it),
# the six pack on; gone after with the camera put back; (b) flown well: 60 s at 3,500, 360, 90 kt, the turn to 090 and
# held, "Dana has the controls" while she sets nose low 25, bank 50, then idle, wings level, nose up; then nose high 30,
# bank 40, full power, nose down, wings level: every phase reached, the debrief a row per task, all passed; (c) flown
# badly: the pull with the power on and the wings banked fails the nose low, wings levelled before the nose comes down
# without power fails the nose high; (d) no page errors. (e) round 2 layout: the hood fills the viewport, the six pack on its
# panel; at 844x390 Dana's subtitle in full inside the viewport, under the card and clear of the six pack; at 568x320 no
# mini map, the card at least 170 px wide clear of the dock buttons, the throttle and the six pack panel, the subtitle shown.
# Run: .venv/bin/python tests/school_hood_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, STEP, start, fly, said
ok = Checks()
HOOD = """()=>{const h=document.getElementById('hood'),r=h.getBoundingClientRect(),sp=document.getElementById('sixpack'),q=sp.getBoundingClientRect(),cs=getComputedStyle(h),K=window.__kgeu;
  return {on:document.body.classList.contains('hoodOn'),disp:cs.display,top:r.top,bottom:r.bottom,w:r.width,sp:sp.classList.contains('on'),spTop:q.top,z:cs.zIndex,pe:cs.pointerEvents,bg:cs.backgroundColor,
    before:!!(h.compareDocumentPosition(document.getElementById('uiroot'))&Node.DOCUMENT_POSITION_FOLLOWING),cam:K.camMode(),
    card:getComputedStyle(document.getElementById('lesson')).display,lesI:document.getElementById('lesI').textContent}}"""
ATT = "()=>{const K=window.__kgeu,s=K.state(),e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');return {p:Math.round(e.x*180/Math.PI),b:Math.round(-e.z*180/Math.PI),kt:Math.round(K.G.kt),thr:s.throttle}}"
R = "()=>{const K=window.__kgeu;for(let i=0;i<4;i++)K.stepFrame(0.03,false,false);K.stepFrame(0,true)}"
LAYOUT = """()=>{const q=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return r.width?{l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}:null};
  const a=document.getElementById('atc'),sp=q('#sixpack'),h=q('#hood');
  return {W:innerWidth,H:innerHeight,hood:h,card:q('#lesson'),atc:q('#atc'),atcOn:a.classList.contains('on')&&getComputedStyle(a).opacity!=='0',atcTx:a.textContent.trim(),
    atcCut:[...a.querySelectorAll('.tx')].some(e=>e.scrollHeight>e.clientHeight+1)||a.scrollHeight>a.clientHeight+1,
    panel:sp&&{l:sp.l-3,t:sp.t-3,r:sp.r+3,b:sp.b+3},thr:q('#thr'),map:q('#map'),
    dock:[...document.querySelectorAll('#dock button')].map(b=>{const r=b.getBoundingClientRect();return r.width?{l:r.left,t:r.top,r:r.right,b:r.bottom,id:b.id||b.textContent.trim()}:null}).filter(Boolean)}}"""
X = lambda a, b: a and b and a['l'] < b['r'] and b['l'] < a['r'] and a['t'] < b['b'] and b['t'] < a['b']
INSIDE = lambda a, L: a and a['l'] >= 0 and a['t'] >= 0 and a['r'] <= L['W'] and a['b'] <= L['H']

def vs(kt, deg):   # the vertical speed that puts school_fly's nose at deg (it adds 0.04 rad)
    import math
    return kt * 101.27 * math.tan(math.radians(deg) - 0.04)

async def run(pg, good):
    PH = []
    cam0 = await pg.evaluate(f"()=>{K}.camMode()")
    await start(pg, 'hood'); await pg.evaluate(R); await pg.wait_for_timeout(450)
    await pg.wait_for_function("()=>getComputedStyle(document.getElementById('atc')).opacity==='1'", timeout=5000)   # the subtitle's 0.35 s fade in has finished
    h0 = await pg.evaluate(HOOD); h0['L'] = await pg.evaluate(LAYOUT)
    await fly(pg, 700, alt=3500, kt=90, vs=0, hdg=0, until="K.LES.ph===1"); PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await fly(pg, 200, kt=90, vs=0, hdg=0, rate=4.5, bank=15)
    await fly(pg, 400, kt=90, vs=0, hdg=90, until="K.LES.ph===2"); PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await pg.evaluate(STEP, 10); dana = await pg.evaluate(HOOD)
    await pg.evaluate(STEP, 30); low = await pg.evaluate(ATT)
    if good:
        await fly(pg, 6, thr=0, bank=50, kt=118, vs=vs(118, -25), hdg=90)
        await fly(pg, 6, bank=0, kt=125, vs=vs(125, -25), hdg=90)
        await fly(pg, 30, bank=0, kt=125, vs=300, hdg=90, until="K.LES.ph===3")
    else:
        await fly(pg, 30, bank=50, kt=118, vs=300, hdg=90, until="K.LES.ph===3")
    PH.append(await pg.evaluate(f"()=>{K}.LES.ph"))
    await pg.evaluate(STEP, 40); high = await pg.evaluate(ATT)
    if good:
        await fly(pg, 6, thr=1, bank=-40, kt=68, vs=vs(68, 30), hdg=90)
        await fly(pg, 10, bank=-40, kt=70, vs=0, hdg=90)
        await fly(pg, 60, bank=0, kt=75, vs=0, hdg=90)
    else:
        await fly(pg, 10, bank=0, kt=68, vs=vs(68, 30), hdg=90)
        await fly(pg, 60, bank=0, kt=70, vs=0, hdg=90)
    await pg.wait_for_timeout(600); await pg.evaluate(R)
    return PH, cam0, h0, dana, low, high, await pg.evaluate(HOOD), await pg.evaluate(DEBRIEF), await pg.evaluate(DANA)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        PH, cam0, h0, dh, low, high, h1, d, dana = await run(pg, True)
        ok('(a) the hood: the cockpit view, shown, the whole viewport, the six pack on', h0['on'] and h0['disp'] == 'block' and h0['cam'] == 1 and h0['top'] == 0
           and h0['bottom'] == 390 and h0['w'] >= 844 and h0['sp'], {k: h0[k] for k in h0 if k != 'L'})
        ok('(a) under every control: before #uiroot, no z-index, no pointer events, #2b2b2b, the lesson card shown', h0['before'] and h0['z'] == 'auto' and h0['pe'] == 'none' and h0['bg'] == 'rgb(43, 43, 43)' and h0['card'] != 'none', h0)
        ok('(b) every phase: the holds, the turn, nose low, nose high', PH == [1, 2, 3], PH)
        ok('(b) the card says Dana has the controls', dh['lesI'] == 'Dana has the controls', dh['lesI'])
        ok('(b) she sets nose low 25, bank 50, then nose high 30, bank 40 the other way', abs(low['p'] + 25) <= 3 and abs(low['b'] - 50) <= 3 and abs(high['p'] - 30) <= 3 and abs(high['b'] + 40) <= 3, (low, high))
        miss = said(dana, 'Under the hood.', 'Turn right to 090, standard rate', 'Close your eyes. I have the controls.', 'Your controls. Recover.')
        ok('(b) Dana: the hood, the turn, I have the controls, your controls', not miss, (miss, dana))
        names = [x[0] for x in d['rows']]
        ok('(b) the debrief: a row per task, all passed', d['on'] and names == ['Altitude within 200 ft', 'Heading within 20 degrees', 'Airspeed within 10 kt', 'Nose low recovery', 'Nose high recovery']
           and all(x[1] for x in d['rows']), d['rows'])
        L = h0['L']
        ok('(e) 844x390: the hood fills the viewport', L['hood']['l'] == 0 and L['hood']['t'] == 0 and L['hood']['w'] == L['W'] and L['hood']['h'] == L['H'], L['hood'])
        ok('(e) 844x390: the subtitle in full, inside the viewport, under the card, clear of the six pack panel', L['atcOn'] and L['atcTx'] and not L['atcCut'] and INSIDE(L['atc'], L)
           and L['atc']['t'] >= L['card']['b'] and not X(L['atc'], L['card']) and not X(L['atc'], L['panel']), (L['atc'], L['card'], L['panel'], L['atcTx']))
        ok('(a) after: the hood gone, the camera put back', not h1['on'] and h1['disp'] == 'none' and h1['cam'] == cam0, (h1, cam0))
        PH, cam0, h0, dh, low, high, h1, d, dana = await run(pg, False)
        pg2 = await page(b, url, vp={'width': 568, 'height': 320}, storage=dict(BASE, **PLACED))
        await start(pg2, 'hood'); await pg2.evaluate(R); await pg2.wait_for_timeout(450)
        await pg2.wait_for_function("()=>getComputedStyle(document.getElementById('atc')).opacity==='1'", timeout=5000)
        L = await pg2.evaluate(LAYOUT)
        hit = [x['id'] for x in L['dock'] if X(L['card'], x)] + (['throttle'] if X(L['card'], L['thr']) else []) + (['six pack'] if X(L['card'], L['panel']) else [])
        ok('(e) 568x320: the card at least 170 px wide, clear of the dock buttons, the throttle and the six pack panel', L['card']['w'] >= 170 and not hit and INSIDE(L['card'], L), (L['card'], hit))
        ok('(e) 568x320: the subtitle shown with its text, inside the viewport, clear of the card and the six pack', L['atcOn'] and L['atcTx'] and not L['atcCut'] and INSIDE(L['atc'], L) and not X(L['atc'], L['card']) and not X(L['atc'], L['panel']), (L['atc'], L['atcTx']))
        ok('(e) 568x320: the mini map hidden', L['map'] is None, L['map'])
        ok('(e) 568x320: no page errors', not pg2.errs, pg2.errs[:3])
        await pg2.context.close()
        rw = {x[0]: x for x in d['rows']}
        for n in ['Nose low recovery', 'Nose high recovery']:
            ok('(c) flown badly fails: ' + n, n in rw and not rw[n][1], rw.get(n))
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_hood_check'))
asyncio.run(main())
