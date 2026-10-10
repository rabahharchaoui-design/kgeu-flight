# School2 item 1 screenshots: Stage 3's pilotage and dead reckoning lesson (Glendale to Sky Harbor and back on a nav log).
# map_s3_<WxH>: the Flight school screen, Stage 3 selected (one real row, three Coming soon), at 844x390, 568x320, 390x844.
# xc_brief_844x390: the briefing, card 3 (the Class Bravo card). xc_climb_<WxH>: chase view, just past 1,500 ft AGL on
# course to the stadium, the nav log card open, the cue strip showing. xc_bravo_<WxH>: the CALL button up for the Class
# Bravo clearance, right after passing Tolleson, with Dana's subtitle. xc_final_844x390: short final to Sky Harbor 7L,
# about 1 nm out at 400 ft AGL, chase view (body.appr). xc_debrief_<WxH>: the debrief after a full clean run, flown the
# way school_xc_check.py does. xc_map_844x390: the mini map canvas, cropped, en route (the dashed route, the fix dots).
# Run: .venv/bin/python tests/school2_shots.py   (--item1a: map/brief/climb/bravo/final/map; --item1b: the debrief only)
# Finer split for a 110s-per-call harness: --maps (map_s3 x3 + xc_brief), --fly844/--fly568 (xc_climb/xc_bravo/xc_map/xc_final
# at one size), --deb844/--deb568 (xc_debrief at one size).
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, PLACED
from school_fly import K, BASE, start, rwy, call, final, touchdown, stop

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'school2')
os.makedirs(SHOTS, exist_ok=True)
ST = dict(BASE, **PLACED)
SIZES = [(844, 390), (568, 320)]
R = "()=>{const K=window.__kgeu;for(let i=0;i<6;i++)K.stepFrame(0.03,false,false);K.stepFrame(0,true)}"
NAVS = f"()=>{{const N={K}.NAV;return {{leg:N.leg,on:N.on,show:N.show,legs:N.legs.map(l=>({{to:l.to.short,c:l.course,seg:l.seg,at:l.at,miss:l.miss,eta:l.eta}})),x:N.legs.map(l=>[l.from.x,l.from.z,l.to.x,l.to.z])}}}}"
ASK = "K.TASK.ask&&K.TASK.ask.shown"
FLY = """([n,o])=>{const K=window.__kgeu,u=o.until?new Function('K','s','return '+o.until):null;let i=0;
  for(;i<n&&K.LES.on;i++){const s=K.state();s.windKt=0;s.gustAmp=0;
    if(o.hold!=null)s.pos.y+=(o.hold-K.G.alt)/3.28084;
    if(o.alt!=null){s.pos.y+=(o.alt-K.G.alt)/3.28084;o.alt=null;}
    if(o.x!=null){s.pos.x=o.x;s.pos.z=o.z;o.x=null;}
    if(o.agl!=null){s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+o.agl/3.28084+(o.gear||1.3);o.agl=null;}
    const hd=o.hdg+(o.rate||0)*i*0.1,h=hd*Math.PI/180,V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225),vy=(o.vs||0)/196.85;
    s.vel.set(Math.sin(h)*V,vy,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(Math.atan2(vy,V)+0.04,-h,-(o.bank||0)*Math.PI/180,'YXZ'));s.w.set(0,0,0);
    s.onGround=false;K.stepFrame(0.1,false,true);if(u&&u(K,K.state()))break;}
  K.stepFrame(0,true);const L=K.LES;return {i:i,ph:L.ph,on:L.on}}"""

async def fly(pg, n, **o):
    return await pg.evaluate(FLY, [n, o])

async def answer(pg):
    return await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")

async def leg(pg, i, alt, kt=105, stop_on_ask=True):
    """fly leg i of the nav log on its course until it is passed, or (default) a CALL comes up"""
    n = await pg.evaluate(NAVS)
    c = n['legs'][i]['c']
    until = f"K.NAV.leg>{i}" + (f"||({ASK})" if stop_on_ask else '')
    return await fly(pg, 6000, hold=alt, kt=kt, vs=0, hdg=c, until=until)

async def fly_leg(pg, i, alt):
    """leg i to its fix, answering every CALL on the way"""
    for _ in range(6):
        await leg(pg, i, alt)
        if (await pg.evaluate(NAVS))['leg'] > i: break
        await answer(pg)

async def taps(pg, hold, hdg, k=2, n=400):
    for _ in range(k):
        await fly(pg, n, hold=hold, kt=105, vs=0, hdg=hdg, until=ASK)
        await answer(pg)

async def shot(pg, name):
    await pg.evaluate(R)
    await pg.wait_for_timeout(450)
    p = os.path.abspath(os.path.join(SHOTS, name))
    await pg.screenshot(path=p)
    print(p)

async def climbout(pg, F):
    """home runway (Glendale) climb out to on course, phase >= 1"""
    x, z = await pg.evaluate(f"()=>{{const K={K},u=K.rwyFrame().thr+1700;return [K.wX(u,0),K.wZ(u,0)]}}")
    return await fly(pg, 200, x=x, z=z, agl=1300, kt=74, vs=700, hdg=60, until='K.LES.ph>=1')

async def maps(b, url):
    # map_s3: the Flight school screen, Stage 3 selected
    for W, H in SIZES + [(390, 844)]:
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
        await pg.evaluate("()=>document.body.classList.add('portraitok')")
        await pg.evaluate(f"()=>{{{K}.openMenu('sSchool');{K}.schSelect('s3')}}")
        await shot(pg, f'map_s3_{W}x{H}.png')
        await pg.context.close()

    # xc_brief: the briefing, card 3 (the Class Bravo card, index 2 of 3)
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    await pg.evaluate(f"()=>{K}.startLesson('pilotage')")
    for _ in range(2):
        await pg.evaluate(f"()=>{K}.lesBriefNext()")
        await pg.wait_for_timeout(400)
    await pg.wait_for_function(f"()=>{{const t=document.getElementById('brTrack');return Math.abs(t.scrollLeft-2*t.clientWidth)<2}}", timeout=8000)
    await shot(pg, 'xc_brief_844x390.png')
    await pg.context.close()

async def fly_size(b, url, W, H):
    # xc_climb, xc_bravo, (xc_final, xc_map at 844 only): flown in the lesson, one page at one size
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    await start(pg, 'pilotage')
    F = await rwy(pg)
    await call(pg)   # the takeoff clearance read back
    await climbout(pg, F)
    n = await pg.evaluate(NAVS)
    ok_climb = (await pg.evaluate(f"()=>({{ph:{K}.LES.ph,show:{K}.NAV.show,cue:document.getElementById('lesCue').classList.contains('on')}})"))
    print('  xc_climb state', W, H, ok_climb)
    await shot(pg, f'xc_climb_{W}x{H}.png')

    # on to Tolleson: leg 0 (to the stadium) to completion, then leg 1 (to Tolleson) which stops right as the
    # Bravo CALL comes up (or the leg itself completes, whichever this engine does first)
    await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
    start_leg = (await pg.evaluate(NAVS))['leg']
    for i in range(start_leg, 2):
        await leg(pg, i, 3500)
    ask = await pg.evaluate(f"()=>{{const a={K}.TASK.ask;return !!(a&&a.shown)}}")
    sub = await pg.evaluate("()=>document.getElementById('atc').classList.contains('on')")
    print('  xc_bravo state', W, H, 'ask', ask, 'sub', sub)
    await shot(pg, f'xc_bravo_{W}x{H}.png')
    if W == 844:
        # the mini map, cropped to its canvas, en route (still on the Tolleson/downtown leg)
        r = await pg.evaluate("()=>{const r=document.getElementById('map').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
        await pg.evaluate(R)
        await pg.wait_for_timeout(450)
        p = os.path.abspath(os.path.join(SHOTS, 'xc_map_844x390.png'))
        await pg.screenshot(path=p, clip={'x': r[0], 'y': r[1], 'width': r[2], 'height': r[3]})
        print(p)
        # xc_final: short final to Sky Harbor 7L, about 1 nm out, 400 ft AGL, chase, body.appr
        tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1751-1852,-300),K.shZ(-1751-1852,-300)]}")
        await pg.evaluate(f"()=>{{{K}.LES.ph=3}}")
        await fly(pg, 30, x=tx, z=tz, agl=400, kt=65, vs=-500, hdg=92)
        appr = await pg.evaluate("()=>document.body.classList.contains('appr')")
        print('  xc_final state appr', appr)
        await shot(pg, 'xc_final_844x390.png')
    await pg.context.close()

async def item1a(b, url):
    await maps(b, url)
    for W, H in SIZES:
        await fly_size(b, url, W, H)

async def debrief_size(b, url, W, H):
    # xc_debrief: the debrief after a full clean run, flown the way school_xc_check.py does, one page at one size
    if True:
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
        await start(pg, 'pilotage')
        F = await rwy(pg)
        await call(pg)
        await climbout(pg, F)
        n = await pg.evaluate(NAVS)
        await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
        start_leg = (await pg.evaluate(NAVS))['leg']
        for i in range(start_leg, 4):
            await fly_leg(pg, i, 3500)
        # Sky Harbor runway 7L: a touchdown 300 m past the threshold, then a stop
        tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1751+300,-300),K.shZ(-1751+300,-300)]}")
        await fly(pg, 2, x=tx, z=tz, agl=20, kt=62, vs=-200, hdg=92)
        await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:180,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [tx, tz])
        await fly(pg, 2, agl=10, kt=55, vs=-100, hdg=92)
        sx, sz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1751+900,-300),K.shZ(-1751+900,-300)]}")
        await pg.evaluate(f"""([x,z])=>{{const K={K};for(let i=0;i<30&&K.LES.on;i++){{const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;s.throttle=0;K.stepFrame(0.1,false,true);}}
          K.stepFrame(0,true);}}""", [sx, sz])
        # the climb out home
        await fly(pg, 200, x=sx, z=sz, agl=1300, kt=74, vs=700, hdg=287, until='K.LES.d.ret===1')
        n = await pg.evaluate(NAVS)
        await fly(pg, 150, hold=4500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
        for i in range(4, 7):
            await fly_leg(pg, i, 4500)
        hg = await pg.evaluate(f"()=>{{const K={K},s=K.state(),F=K.rwyFrame(),u=F.thr;return (Math.atan2(K.wX(u,0)-s.pos.x,-(K.wZ(u,0)-s.pos.z))*180/Math.PI+360)%360}}")
        await taps(pg, 4500, hg, k=2, n=300)
        await final(pg, F)
        await touchdown(pg, F, past=60, fpm=160)
        r = await stop(pg, F)
        await pg.wait_for_timeout(800)
        on = await pg.evaluate("()=>document.getElementById('gradeOv').classList.contains('on')")
        letter = await pg.evaluate("()=>document.getElementById('gLetter').textContent")
        print('  xc_debrief state', W, H, 'on', on, 'letter', letter, 'stop', r)
        await shot(pg, f'xc_debrief_{W}x{H}.png')
        await pg.context.close()

async def item1b(b, url):
    for W, H in SIZES:
        await debrief_size(b, url, W, H)

MEAS = """()=>{const g=id=>{const e=document.getElementById(id);if(!e)return null;const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom,r.width,r.height]};
  const btn=id=>{const e=document.getElementById(id);if(!e)return null;const r=e.getBoundingClientRect();return [r.width,r.height]};
  const clipped=id=>{const e=document.getElementById(id);if(!e)return null;return e.scrollWidth>e.clientWidth+1};
  return {navLog:g('navLog'),stick:g('stick'),stickZone:g('stickZone'),lesLog:btn('lesLog'),lesQuit:btn('lesQuit'),hDest:g('hDest'),
    navClipped:clipped('navLog'),title:document.getElementById('lesT')&&document.getElementById('lesT').textContent,
    navRows:[...document.querySelectorAll('#navLog tbody tr')].map(r=>[...r.cells].map(c=>c.textContent))}}"""

CENTRE = """()=>{const W=innerWidth,H=innerHeight,B=[W/3,H/3,2*W/3,2*H/3],out=[];
  const skip='button,.overlay,#sixpack,#menu,#pauseOv,#stickZone,#thrCol,#dock,#dzMark,#dzArrow,#tgtMarks,#crash,#crashTop,#photoOv,#mapOv,#hud,#rotate';
  const vis=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.05)return false;}return true;};
  for(const e of document.body.querySelectorAll('*')){
    if(e.closest(skip))continue;
    const own=[...e.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim()).map(n=>n.textContent.trim()).join(' ');
    if(!own||!vis(e))continue;
    let r=e.getBoundingClientRect(),x0=r.left,y0=r.top,x1=r.right,y1=r.bottom;
    for(let n=e.parentElement;n&&n!==document.body;n=n.parentElement){const s=getComputedStyle(n);
      if(s.overflow!=='visible'||s.overflowY!=='visible'||s.overflowX!=='visible'){const q=n.getBoundingClientRect();x0=Math.max(x0,q.left);y0=Math.max(y0,q.top);x1=Math.min(x1,q.right);y1=Math.min(y1,q.bottom);}}
    if(x1-x0<1||y1-y0<1)continue;
    if(x0<B[2]&&x1>B[0]&&y0<B[3]&&y1>B[1])out.push((e.id?'#'+e.id:e.className||e.tagName)+' "'+own.slice(0,30)+'" '+[x0,y0,x1,y1].map(Math.round).join(','));}
  return out;}"""

async def measure_final844(b, url):
    """picky-player check: centre third clear on xc_final's short-final moment at 844x390"""
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    await start(pg, 'pilotage')
    F = await rwy(pg)
    await call(pg)
    tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1751-1852,-300),K.shZ(-1751-1852,-300)]}")
    await pg.evaluate(f"()=>{{{K}.LES.ph=3}}")
    await fly(pg, 30, x=tx, z=tz, agl=400, kt=65, vs=-500, hdg=92)
    appr = await pg.evaluate("()=>document.body.classList.contains('appr')")
    bad = await pg.evaluate(CENTRE)
    print('MEASURE final844 appr', appr, 'centre-third-hits', bad)
    await pg.context.close()

async def measure568(b, url):
    """picky-player measurement pass at 568x320: #navLog vs #stick gap, button sizes, text clipping, at the cruise/bravo moment"""
    pg = await page(b, url, vp={'width': 568, 'height': 320}, storage=ST)
    await start(pg, 'pilotage')
    F = await rwy(pg)
    await call(pg)
    await climbout(pg, F)
    n = await pg.evaluate(NAVS)
    await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
    start_leg = (await pg.evaluate(NAVS))['leg']
    for i in range(start_leg, 2):
        await leg(pg, i, 3500)
    m = await pg.evaluate(MEAS)
    print('MEASURE 568x320', m)
    await pg.context.close()

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if '--maps' in sys.argv:
            await maps(b, url); await b.close(); srv.shutdown(); return
        if '--fly844' in sys.argv:
            await fly_size(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--fly568' in sys.argv:
            await fly_size(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--deb844' in sys.argv:
            await debrief_size(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--deb568' in sys.argv:
            await debrief_size(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--measure568' in sys.argv:
            await measure568(b, url); await b.close(); srv.shutdown(); return
        if '--measurefinal844' in sys.argv:
            await measure_final844(b, url); await b.close(); srv.shutdown(); return
        if '--item1b' in sys.argv:
            await item1b(b, url); await b.close(); srv.shutdown(); return
        if '--item1a' in sys.argv:
            await item1a(b, url); await b.close(); srv.shutdown(); return
        await item1a(b, url)
        await item1b(b, url)
        await b.close()
    srv.shutdown()
asyncio.run(main())
