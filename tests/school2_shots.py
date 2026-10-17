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
#
# School2 item 2: Stage 3's diversion and lost procedures lesson (the dust storm over Sky Harbor, the diversion card, the
# lost-procedure CALL, the debrief). div_card_<WxH>: the card up (heading/minutes steppers, SET), the mini map hidden,
# Dana's dust storm subtitle live, the lesson card. div_set_844x390: right after SET (card gone, the cue strip HDG/ALT, the
# instruction line). div_call_<WxH>: the vectors CALL button up (Approach's radar contact subtitle if it landed in time).
# div_debrief_<WxH>: the debrief after a clean run (7 rows). Split for the 110s cap: --div844 (card+set+call at 844),
# --div568 (card+call at 568), --divdeb844, --divdeb568 (the full flown lesson, one size each: ~60s alone).
#
# School2 item 3: Stage 3's night lesson (three full stops at KGEU, night mode for the lesson only). night_rwy_<WxH>: on
# the runway at the start, chase, the runway edge lights/threshold/PAPI lit, Dana's opening subtitle, the CALL button up.
# night_final_844x390: short final on the first circuit (about 0.8 nm, 300 ft AGL) at night, the runway lights and PAPI
# ahead, the lesson card. night_debrief_<WxH>: the debrief after three clean full stops (7 rows). night_after_844x390: a
# frame after the debrief's CONTINUE IN FREE FLIGHT, the sky back to day. Split for the 110s cap: --n844 (rwy+final at
# 844, ~25s), --n568 (rwy only at 568, ~10s), --ndeb844 (debrief+after at 844, ~75s), --ndeb568 (debrief only at 568, ~65s).
#
# School2 item 4: Stage 3 lesson 4, the solo cross country (the pilotage trip, nobody in the right seat). map_s3_full_844x390:
# the Flight school screen, Stage 3 selected, all four real rows (pilotage, divert, night, soloxc), kgeuSchool seeded with
# pilotage A, divert B, night A so soloxc is the next lesson. solo_call_<WxH>: the moment the Bravo CALL button is up (the
# same leg as item1's xc_bravo, flown as 'soloxc' instead), the lesson card's "Call Phoenix Approach: tap CALL." prompt, and
# whether the #atc subtitle is live (it should not be a Dana line: she is silent after her start line). solo_debrief_<WxH>:
# the debrief after a clean run (the same shape as school_soloxc_check.py's run_b: out to Sky Harbor, a stop, back to
# Glendale, a stop): the Endorsement row first ("Solo cross country, signed by Dana Reyes, CFI"). logbook_xc_844x390: the
# Logbook screen right after that same run, no replay: kgeuEndorse seeded with the Stage 1 solo endorsement already signed
# (so it reads as earned, same as a real student who soloed before their XC), plus the solo cross country endorsement this
# run grants; the last logbook entry 1.5 solo / 1.5 XC. Split for the 110s cap: --item4map (map only, no flight, ~5s),
# --item4call844 / --item4call568 (to the Bravo CALL, one size each), --item4deb844 (the full out-and-back to the debrief,
# then straight on to the Logbook for logbook_xc_844x390, no replay), --item4deb568 (the debrief only). --item4 runs the
# whole group end to end (well over 110s: never call it directly in one foreground Bash call).
#
# School2 item 5: Stage 4 lesson 1, the oral exam (#orOv over the Flight school screen, the result on #gradeOv, no
# flight). map_s4_844x390: the Flight school screen, Stage 4 selected (the Oral exam START row, Mock checkride Coming
# soon row). oral_q1_<WxH> (844x390, 568x320, 390x844): Question 1 of 15 unanswered, the Back button present.
# oral_wrong_<WxH> (844, 568): the longest question in the oralSeed(1) draw (by question + answers length), answered
# wrong (the red answer, the right one outlined, the explanation shown, NEXT enabled). oral_pass_<WxH> (844, 568): all
# 15 right (A, 15 of 15, six topic rows). oral_fail_844x390: 10 right then 5 wrong (F, the Missed list). Each shot also
# prints the FIT/MEAS_ORAL measurement (answer/Back/NEXT button heights at the shot's size, the question block's
# scrollHeight vs clientHeight). A page load + the school navigation alone runs about 25-30s in this headless
# harness, so each shot gets its own per-size flag to stay under the 110s cap: --item5map (map only, ~10s),
# --item5q1_844 / --item5q1_568 / --item5q1_390x844 (~30s each; --item5q1 combines all three, ~90s, risks the cap),
# --item5wrong_844 / --item5wrong_568 (steps to the longest question first, ~35-45s each; --item5wrong combines both),
# --item5pass_844 / --item5pass_568 (15 answers, ~45-60s each; --item5pass combines both), --item5fail (844 only, 15
# answers, ~45s). --item5 runs the whole group end to end (well over 110s: never call it directly in one foreground
# Bash call).
#
# School2 item 6: Stage 4 lesson 2, the mock checkride (Frank Delgado, DPE; #RIDE draws steep, slow, stall, emerg,
# hood, landings under rideSeed(42)). ride_task_<WxH>: mid ride, during the steep turns task (partway into the turn,
# not complete): Frank's subtitle (#atc, "Frank" as the speaker), the lesson card (Checkride: Steep turns, or its
# narrow form), the cue strip. ride_cert_<WxH>: the certificate card after the passed run (seed 42), shot at once and
# again after 1.5s (the XP pop may still show, or may have faded); measures #gLines/.cert scrollHeight vs clientHeight
# at 568x320 for clipping. ride_fail_844x390: the F card (Notice of disapproval) after the failed run (seed 1, slow
# flight stalled), the Retrain row(s), RETRAIN at least 44px. boards_ride_844x390: the Boards screen, Checkride board
# selected, one row. map_s4_cert_844x390: the Flight school screen after the pass (the header's certificate line,
# Stage 4 ticked). A full pass drive (all six tasks) runs close to the 110s per-call cap on its own, so boards/map
# are seeded from localStorage dumped by the --item6cert run instead of re-flying the whole ride: --item6task
# (~15s), --item6fail (~20s), --item6cert (the full pass drive + both cert shots, ~90-100s: dumps every kgeu* key to
# /tmp/ride_pass_storage.json), --item6boardsmap (needs --item6cert to have run first in this session; a page load +
# two taps, ~15s). --item6 runs the whole group end to end (well over 110s: never call it directly in one foreground
# Bash call).
#
# School2 item 7: the logbook (certificate block, endorsements in order signed, entry notes, "N night" by Landings,
# the debrief's Logbook row). logbook_full_<WxH> (844x390, 568x320, 390x844): one page seeded exactly like
# school_log_check.py's (e) block (pilotage, soloxc, night, hood, oral, ride entries with notes, kgeuCert set, the
# solo + solo cross country endorsements), resized per shot; each shot prints the #logCert/#logEnd/#logList
# scrollWidth-vs-clientWidth and the #mBack size. logbook_worst_<WxH> (844, 568): school_break_check.py's worst
# case copied by value (60 entries, 999.9 h, 9,999 landings and night landings, the longest notes), same
# measurement. night_debrief_log_844x390: the night lesson's clean three-stop run to the debrief's Logbook row
# ("+1.0 h night, 3 night landings"). Split for the 110s cap: --item7full (~20s, no flight), --item7worst (~15s,
# no flight), --item7night (~75s, the full night circuit flown three times, like --ndeb844). --item7 runs the
# whole group end to end (well over 110s: never call it directly in one foreground Bash call).
import asyncio, json, math, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, PLACED, finger
from school_fly import K, BASE, start, rwy, call, final, touchdown, stop, DANA, DEBRIEF, downwind, base
import school_fly as SF  # SF.climbout: the circuit climb-out; this file's own climbout() (item1) is the nav lesson's departure, a different flight

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'school2')
os.makedirs(SHOTS, exist_ok=True)
ST = dict(BASE, **PLACED)
SIZES = [(844, 390), (568, 320)]
# item 4: Stage 3 progress seeded directly (pilotage A, divert B, night A) so soloxc is the next lesson; kgeuEndorse is
# seeded only for the logbook shot, with the Stage 1 solo endorsement already signed (soloxc itself grants 'xc', not 'solo')
SCH_SEED = '{"cessna:pilotage":"A","cessna:divert":"B","cessna:night":"A"}'
ENDORSE_SEED = '{"solo":{"at":1759000000000,"by":"Dana Reyes, CFI","lesson":"solo"}}'
ST4 = dict(ST, kgeuSchool=SCH_SEED)
ST4E = dict(ST4, kgeuEndorse=ENDORSE_SEED)
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
        tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5-1852,361),K.shZ(-1442.5-1852,361)]}")
        await pg.evaluate(f"()=>{{{K}.LES.ph=3}}")
        await fly(pg, 30, x=tx, z=tz, agl=400, kt=65, vs=-500, hdg=90)
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
        tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5+300,361),K.shZ(-1442.5+300,361)]}")
        await fly(pg, 2, x=tx, z=tz, agl=20, kt=62, vs=-200, hdg=90)
        await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:180,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [tx, tz])
        await fly(pg, 2, agl=10, kt=55, vs=-100, hdg=90)
        sx, sz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5+900,361),K.shZ(-1442.5+900,361)]}")
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
    tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5-1852,361),K.shZ(-1442.5-1852,361)]}")
    await pg.evaluate(f"()=>{{{K}.LES.ph=3}}")
    await fly(pg, 30, x=tx, z=tz, agl=400, kt=65, vs=-500, hdg=90)
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

# ---------------- item 2: the diversion lesson (Glendale's bearing/distance, the card's steppers, the CALL) ----------------
GLN = """()=>{const K=window.__kgeu,s=K.state(),x=K.LES.d.G0.x,z=K.LES.d.G0.z,dx=x-s.pos.x,dz=z-s.pos.z;
  return {brg:((Math.atan2(dx,-dz)*180/Math.PI-12)%360+360)%360,nm:Math.hypot(dx,dz)/1852}}"""
HOLD = f"()=>{K}.stepFrame(0.001,false,true)"
DIVASK = "K.TASK.ask&&K.TASK.ask.shown"
DIVRECTS = """()=>{const R=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};
  return {card:R('#divCard'),tkReply:R('#tkReply'),les:R('#lesson'),pause:R('#bPause'),W:innerWidth,H:innerHeight}}"""

async def to_card(pg):
    """fly until the diversion card opens (past downtown, the dust storm)"""
    c = await pg.evaluate(f"()=>{K}.NAV.legs[2].course")
    return await fly(pg, 3000, hold=3500, kt=105, vs=0, hdg=c, until="K.DIV.on")

DUST_ON = "document.getElementById('atc').classList.contains('on')&&/dust storm/.test(document.getElementById('atc').textContent)"

async def to_dust(pg, n=400):
    """the card opens with the dust-storm line only queued; fly on (heading is free, GPS is off), checked inside the
    same frame loop (no per-frame round trip: the browser's own render loop already burns real time at ~3 fps headless,
    so this must stay a single evaluate call), until Dana's dust-storm line is the *live* subtitle, not just logged"""
    await fly(pg, n, hold=3500, kt=105, vs=0, hdg=300, until=DUST_ON)
    return await pg.evaluate(f"()=>{{return {DUST_ON}}}")

async def div_set(pg):
    """the real taps: heading to the 5 deg nearest Glendale's bearing, minutes at 105 kt, then SET. Returns the heading picked."""
    gl = await pg.evaluate(GLN)
    want = int(round(gl['brg'] / 5) * 5) % 360 or 360
    mins = max(1, int(round(gl['nm'] / 105 * 60)))
    await pg.evaluate(HOLD)
    h0 = await pg.evaluate(f"()=>{K}.DIV.h")
    dh = ((want - h0 + 540) % 360) - 180
    taps = 0
    while dh != 0 and taps < 40:
        step = 10 if dh >= 10 else -10 if dh <= -10 else 5 if dh > 0 else -5
        await pg.click(f'#divCard [data-h="{step}"]'); dh -= step; taps += 1
    m0 = await pg.evaluate(f"()=>{K}.DIV.m")
    for _ in range(abs(mins - m0)):
        await pg.click('#divCard [data-m="%d"]' % (1 if mins > m0 else -1))
    await pg.click('#divSet')
    return want

async def div_to_card_shot(pg, W, H):
    await start(pg, 'divert')
    await fly(pg, 3, hold=3500, kt=105, vs=0, hdg=await pg.evaluate(f"()=>{K}.NAV.legs[2].course"))
    await to_card(pg)
    got = await to_dust(pg)
    r = await pg.evaluate(DIVRECTS)
    print(f'  div_card {W}x{H} dust-storm subtitle live: {got}  rects {r}')
    await shot(pg, f'div_card_{W}x{H}.png')

async def div844(b, url):
    # div_card, div_set, div_call all at 844x390 in one page (card -> SET -> the CALL for vectors)
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    await div_to_card_shot(pg, 844, 390)
    want = await div_set(pg)
    await pg.wait_for_timeout(300)
    r = await pg.evaluate(DIVRECTS)
    print('  div_set 844x390 rects', r)
    await shot(pg, 'div_set_844x390.png')
    tgt = (want + 12) % 360
    await fly(pg, 1, alt=4500, kt=105, vs=0, hdg=tgt)
    await fly(pg, 400, hold=4500, kt=105, vs=0, hdg=tgt, until=DIVASK)
    sub = await pg.evaluate(f"()=>{K}.TASK.ask&&{K}.TASK.ask.opts[0].sub")
    r = await pg.evaluate(DIVRECTS)
    print('  div_call 844x390 CALL sub', sub, 'rects', r)
    await shot(pg, 'div_call_844x390.png')
    await pg.context.close()

async def div568(b, url):
    # div_card, div_call at 568x320 (no div_set shot asked at this size)
    pg = await page(b, url, vp={'width': 568, 'height': 320}, storage=ST)
    await div_to_card_shot(pg, 568, 320)
    want = await div_set(pg)
    tgt = (want + 12) % 360
    await fly(pg, 1, alt=4500, kt=105, vs=0, hdg=tgt)
    await fly(pg, 400, hold=4500, kt=105, vs=0, hdg=tgt, until=DIVASK)
    sub = await pg.evaluate(f"()=>{K}.TASK.ask&&{K}.TASK.ask.opts[0].sub")
    r = await pg.evaluate(DIVRECTS)
    print('  div_call 568x320 CALL sub', sub, 'rects', r)
    await shot(pg, 'div_call_568x320.png')
    await pg.context.close()

async def divdebrief(b, url, W, H):
    # the whole lesson flown clean (the way school_divert_check.py's run_a does it), one size, to the debrief
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    await start(pg, 'divert')
    F = await rwy(pg)
    await fly(pg, 3, hold=3500, kt=105, vs=0, hdg=await pg.evaluate(f"()=>{K}.NAV.legs[2].course"))
    await to_card(pg)
    want = await div_set(pg)
    tgt = (want + 12) % 360
    await fly(pg, 1, alt=4500, kt=105, vs=0, hdg=tgt)
    await fly(pg, 400, hold=4500, kt=105, vs=0, hdg=tgt, until=DIVASK)
    await pg.evaluate(HOLD)
    await pg.click('#tkReply button')
    await fly(pg, 300, hold=4500, kt=105, vs=0, hdg=tgt, until="K.radioLog().some(l=>/radar contact/.test(l.text))")
    await fly(pg, 6000, hold=4500, kt=105, vs=0, hdg=tgt, until='K.LES.ph>=5')
    for _ in range(4):
        await fly(pg, 600, hold=4500, kt=90, vs=0, hdg=tgt, until=DIVASK)
        await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
        if await pg.evaluate(f"()=>{K}.radioLog().some(l=>l.who==='Skyhawk 8401L'&&/^Cleared to land/.test(l.text))"): break
    await final(pg, F)
    await touchdown(pg, F, past=60, fpm=160)
    await stop(pg, F)
    await pg.wait_for_timeout(800)
    d = await pg.evaluate(DEBRIEF)
    print(f'  div_debrief {W}x{H} letter {d["letter"]} rows {len(d["rows"])} all_ok {all(x[1] for x in d["rows"])}')
    m = await pg.evaluate("""()=>{const e=document.getElementById('gLines');const r=e.getBoundingClientRect();
      return {scrollH:e.scrollHeight,clientH:e.clientHeight,more:e.classList.contains('more'),rect:[r.top,r.bottom],Hvp:innerHeight}}""")
    print(f'  div_debrief {W}x{H} #gLines measure {m}')
    await shot(pg, f'div_debrief_{W}x{H}.png')
    await pg.context.close()

# ---------------- item 3: the night lesson (KGEU home runway, three circuits, the sky toggled for the lesson only) ----------------
NIGHT_WAIT_RB = f"()=>{{const K=window.__kgeu;for(let i=0;i<500;i++){{K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}}K.stepFrame(0,true)}}"
WAIT_CALL = f"(n)=>{{const K={K};for(let i=0;i<n&&K.LES.on;i++){{if(K.TASK.ask&&K.TASK.ask.shown)break;K.stepFrame(0.1,false,true);}}K.stepFrame(0,true);return !!(K.TASK.ask&&K.TASK.ask.shown)}}"
NIGHT_SKY = f"()=>{{const L={K}.lights();return {{tod:{K}.TOD().id,saved:localStorage.getItem('kgeuTOD'),lit:L.layers.every(l=>l.visible&&l.inScene),u:L.uLights}}}}"

async def night_start(pg):
    """start the night lesson, wait for the takeoff clearance CALL (not yet tapped), report the sky + Dana's subtitle"""
    await start(pg, 'night')
    F = await rwy(pg)
    shown = await pg.evaluate(WAIT_CALL, 400)
    sub = await pg.evaluate("()=>document.getElementById('atc').textContent")
    sky = await pg.evaluate(NIGHT_SKY)
    return F, shown, sub, sky

async def night_circuit(pg, F, past=60):
    """one circuit to a full stop, the same shape as school_night_check.py's circuit()"""
    await SF.climbout(pg, F)
    await downwind(pg, F)
    await call(pg)
    await downwind(pg, F, 80)
    await base(pg, F)
    await final(pg, F)
    await touchdown(pg, F, past=past)
    await stop(pg, F)

async def night_rwy(b, url, W, H):
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    F, shown, sub, sky = await night_start(pg)
    print(f'  night_rwy {W}x{H} CALL up {shown} sky {sky} Dana: {sub[:90]}')
    await shot(pg, f'night_rwy_{W}x{H}.png')
    return pg, F

async def n844(b, url):
    # night_rwy_844x390, then on into the first circuit to short final for night_final_844x390
    pg, F = await night_rwy(b, url, 844, 390)
    await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    await pg.evaluate(NIGHT_WAIT_RB)
    await SF.climbout(pg, F)
    await downwind(pg, F)
    await call(pg)
    await downwind(pg, F, 80)
    await base(pg, F)
    x, z = await pg.evaluate(f"([u,v])=>{{const K={K};return [K.wX(u,v),K.wZ(u,v)]}}", [F['thr'] - 1482, 0])
    r = await fly(pg, 50, x=x, z=z, agl=300, kt=65, vs=-500, hdg=F['rh'])
    st = await pg.evaluate(f"()=>({{s:{K}.LES.d.s,fin:{K}.LES.d.fin,alt:Math.round({K}.G.alt),kt:Math.round({K}.G.kt)}})")
    card = await pg.evaluate("()=>({t:document.getElementById('lesT').textContent,cue:document.getElementById('lesCue').classList.contains('on')})")
    print(f'  night_final 844x390 ph {r["ph"]} state {st} card {card}')
    await shot(pg, 'night_final_844x390.png')
    await pg.context.close()

async def n568(b, url):
    # night_rwy_568x320 only
    pg, F = await night_rwy(b, url, 568, 320)
    await pg.context.close()

async def ndeb(b, url, W, H, after=False):
    # night_debrief_<WxH> after three clean full stops; at 844 also night_after_844x390 past CONTINUE IN FREE FLIGHT
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    F, shown, sub, sky0 = await night_start(pg)
    await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    await pg.evaluate(NIGHT_WAIT_RB)
    for k in range(3):
        if k: await call(pg)
        await night_circuit(pg, F, past=40 + 30 * k)
    await pg.wait_for_timeout(800)
    d = await pg.evaluate(DEBRIEF)
    print(f'  night_debrief {W}x{H} on {d["on"]} letter {d["letter"]} rows {len(d["rows"])} all_ok {all(x[1] for x in d["rows"])}')
    await shot(pg, f'night_debrief_{W}x{H}.png')
    if after:
        await pg.evaluate("()=>document.getElementById('gFree').click()")
        await pg.wait_for_timeout(300)
        sky1 = await pg.evaluate(NIGHT_SKY)
        print(f'  night_after sky0(lesson) {sky0} sky1(after CONTINUE) {sky1}')
        await shot(pg, 'night_after_844x390.png')
    await pg.context.close()

# ---------------- item 4: the solo cross country (the pilotage trip flown alone) ----------------
LESI = "()=>document.getElementById('lesI').textContent"

async def map_s3_full(b, url):
    # map_s3_full: Stage 3 selected with all four real rows, pilotage/divert/night already passed so soloxc is next
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST4)
    await pg.evaluate(f"()=>{{{K}.openMenu('sSchool');{K}.schSelect('s3')}}")
    rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.classList.contains('soon'),r.classList.contains('done'),r.classList.contains('next')])")
    print('  map_s3_full rows', rows)
    await shot(pg, 'map_s3_full_844x390.png')
    await pg.context.close()

async def solo_to_bravo(pg):
    """soloxc flown like item1's fly_size, up to (or just past) the Bravo CALL coming up near Tolleson/downtown"""
    F = await rwy(pg)
    await call(pg)   # the takeoff clearance read back
    await climbout(pg, F)
    n = await pg.evaluate(NAVS)
    await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
    start_leg = (await pg.evaluate(NAVS))['leg']
    for i in range(start_leg, 2):
        await leg(pg, i, 3500)
    return F

async def solo_call(b, url, W, H):
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST4)
    await start(pg, 'soloxc')
    await solo_to_bravo(pg)
    ask = await pg.evaluate(f"()=>{{const a={K}.TASK.ask;return !!(a&&a.shown)}}")
    atc_on = await pg.evaluate("()=>document.getElementById('atc').classList.contains('on')")
    card = await pg.evaluate(LESI)
    dana = await pg.evaluate(DANA)
    print(f'  solo_call {W}x{H} CALL up {ask} atc.on {atc_on} card {card!r} Dana lines so far {len(dana)}')
    await shot(pg, f'solo_call_{W}x{H}.png')
    await pg.context.close()

async def solo_fly_full(pg):
    """the whole soloxc lesson, clean, the same shape as school_soloxc_check.py's run_b: out to Sky Harbor, a stop,
    back to Glendale, a stop. Identical in substance to this file's own debrief_size (item1), lesson id swapped"""
    F = await rwy(pg)
    await call(pg)
    await climbout(pg, F)
    n = await pg.evaluate(NAVS)
    await fly(pg, 150, hold=3500, kt=90, vs=0, hdg=n['legs'][n['leg']]['c'])
    start_leg = (await pg.evaluate(NAVS))['leg']
    for i in range(start_leg, 4):
        await fly_leg(pg, i, 3500)
    # Sky Harbor runway 7L: a touchdown 300 m past the threshold, then a stop
    tx, tz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5+300,361),K.shZ(-1442.5+300,361)]}")
    await fly(pg, 2, x=tx, z=tz, agl=20, kt=62, vs=-200, hdg=90)
    await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:180,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [tx, tz])
    await fly(pg, 2, agl=10, kt=55, vs=-100, hdg=90)
    sx, sz = await pg.evaluate("()=>{const K=window.__kgeu;return [K.shX(-1442.5+900,361),K.shZ(-1442.5+900,361)]}")
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
    await stop(pg, F)
    await pg.wait_for_timeout(800)
    return F

async def solo_debrief(b, url, W, H, logbook=False):
    # solo_debrief_<WxH>; at 844 with logbook=True, continues on (no replay) to the Logbook screen for logbook_xc_844x390
    st = ST4E if logbook else ST4
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=st)
    await start(pg, 'soloxc')
    await solo_fly_full(pg)
    d = await pg.evaluate(DEBRIEF)
    dana = await pg.evaluate(DANA)
    print(f'  solo_debrief {W}x{H} on {d["on"]} letter {d["letter"]} gl[0] {d["gl"][0] if d["gl"] else None} Dana lines {len(dana)}')
    await shot(pg, f'solo_debrief_{W}x{H}.png')
    if logbook:
        await pg.evaluate(f"()=>{{{K}.resClose(document.getElementById('gradeOv'));{K}.openMenu();{K}.nav('sLog')}}")
        await pg.wait_for_timeout(400)
        rings = await pg.evaluate("()=>[...document.querySelectorAll('#logRings .lRing')].map(r=>r.dataset.k)")
        endo = await pg.evaluate("()=>document.getElementById('logEnd').textContent")
        entry = await pg.evaluate("()=>{const e=JSON.parse(localStorage.getItem('kgeuLogbook')||'{}').entries||[];return e[e.length-1]}")
        print(f'  logbook_xc rings {rings} endorsements {endo!r} last entry {entry}')
        await shot(pg, 'logbook_xc_844x390.png')
    await pg.context.close()

async def item4(b, url):
    # the whole item4 group, end to end; well over 110s, never call this one directly in a single foreground Bash call
    await map_s3_full(b, url)
    await solo_call(b, url, 844, 390)
    await solo_call(b, url, 568, 320)
    await solo_debrief(b, url, 844, 390, logbook=True)
    await solo_debrief(b, url, 568, 320)

# ---------------- item 5: Stage 4 lesson 1, the oral exam (#orOv, the result on #gradeOv, no flight) ----------------
ORAL_SHEET = f"""()=>{{const o=document.getElementById('orOv');return {{on:o.classList.contains('on')&&!o.classList.contains('out'),n:document.getElementById('orN').textContent,
  chip:document.getElementById('orChip').textContent,ans:[...document.querySelectorAll('#orA .orAns')].map(b=>{{const r=b.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]}}),
  back:!document.getElementById('orBack').hidden,next:document.getElementById('orNext').textContent,dis:document.getElementById('orNext').disabled,
  why:!document.getElementById('orWhy').hidden,cls:[...document.querySelectorAll('#orA .orAns')].map(b=>b.className.replace('orAns','').trim())}}}}"""
ORAL_IDLE = "()=>{const o=document.getElementById('orOv');return o.getAnimations({subtree:true}).every(a=>a.playState==='finished')}"
ORAL_FIT = """()=>{const s=document.querySelector('#orOv .sheet'),W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('sheet scrolls '+s.scrollHeight+'>'+s.clientHeight);
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14)+' '+Math.round(r.width)+'x'+Math.round(r.height));});
  return bad;}"""
MEAS_ORAL = """()=>{const h=s=>[...document.querySelectorAll(s)].map(e=>Math.round(e.getBoundingClientRect().height));
  const qb=document.querySelector('#orOv .orQ'),sheet=document.querySelector('#orOv .sheet');
  return {ansH:h('#orA .orAns'),backH:h('#orBack'),nextH:h('#orNext'),
    qScrollH:qb&&qb.scrollHeight,qClientH:qb&&qb.clientHeight,
    sheetScrollH:sheet.scrollHeight,sheetClientH:sheet.clientHeight};}"""
ORAL_CARD = """()=>{const o=document.getElementById('gradeOv');return {on:o.classList.contains('on'),letter:document.getElementById('gLetter').textContent,
  score:document.getElementById('gScore').textContent,topics:[...o.querySelectorAll('.rLines .gt')].map(r=>[r.firstChild.textContent,r.lastChild.textContent,r.classList.contains('ok')]),
  missed:[...o.querySelectorAll('.rLines .orMs')].map(r=>[r.firstChild.textContent,r.lastChild.textContent]),mh:!!o.querySelector('.orMh')};}"""

async def school_s4(pg):
    await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(200)
    await finger(pg, '#hSch'); await pg.wait_for_timeout(400)
    await finger(pg, '.sNode[data-st=s4]'); await pg.wait_for_timeout(400)

async def open_oral(pg):
    await finger(pg, '#school .lrow[data-l=oral]'); await pg.wait_for_timeout(300)
    await pg.wait_for_function(ORAL_IDLE, timeout=8000)

async def oral_answer(pg, i, right):
    """tap the answer for drawn question i (0-based): right picks the correct one, else the next (wrong) one"""
    q = await pg.evaluate(f"(i)=>{{const Q={K}.ORAL[i];return {{ok:Q.ok}}}}", i)
    k = q['ok'] if right else (q['ok'] + 1) % 4
    await finger(pg, f'#orA .orAns:nth-child({k + 1})'); await pg.wait_for_timeout(120)
    return k

async def oral_next(pg):
    await finger(pg, '#orNext'); await pg.wait_for_timeout(120)

async def map_s4(b, url):
    # map_s4_844x390: the Flight school screen, Stage 4 selected (Oral exam START row, Mock checkride Coming soon row)
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    await school_s4(pg)
    rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.classList.contains('soon'),r.textContent.includes('START')])")
    print('  map_s4 rows', rows)
    await shot(pg, 'map_s4_844x390.png')
    await pg.context.close()

async def oral_q1(b, url, W, H):
    # oral_q1_<WxH>: Question 1 of 15 unanswered, Back present; also the FIT/MEAS_ORAL measurement at this size
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    if H > W:
        await pg.evaluate("()=>document.body.classList.add('portraitok')")
    await school_s4(pg)
    await pg.evaluate(f"()=>{K}.oralSeed(1)")
    await open_oral(pg)
    s = await pg.evaluate(ORAL_SHEET)
    bad = await pg.evaluate(ORAL_FIT)
    m = await pg.evaluate(MEAS_ORAL)
    print(f'  oral_q1 {W}x{H} n={s["n"]!r} chip={s["chip"]!r} back={s["back"]} next={s["next"]!r} dis={s["dis"]} FIT bad={bad} MEAS {m}')
    await shot(pg, f'oral_q1_{W}x{H}.png')
    await pg.context.close()

async def oral_goto_worst(pg):
    """draws the oral exam (oralSeed(1)), finds the question with the longest question+answers text in the draw,
    steps to it answering every one before it right, then answers that one wrong; returns (idx, k, sheet state)"""
    await pg.evaluate(f"()=>{K}.oralSeed(1)")
    await open_oral(pg)
    draw = await pg.evaluate(f"()=>{K}.ORAL.map(q=>q.q.length+q.a.join('').length)")
    idx = draw.index(max(draw))
    for i in range(idx):
        await oral_answer(pg, i, right=True)
        await oral_next(pg)
    k = await oral_answer(pg, idx, right=False)
    s = await pg.evaluate(ORAL_SHEET)
    return idx, k, s

async def oral_wrong(b, url, W, H):
    # oral_wrong_<WxH>: the longest question in the draw, answered wrong: red answer, the right one outlined (should),
    # the explanation shown, NEXT enabled; also the FIT/MEAS_ORAL measurement at this size
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    await school_s4(pg)
    idx, k, s = await oral_goto_worst(pg)
    bad = await pg.evaluate(ORAL_FIT)
    m = await pg.evaluate(MEAS_ORAL)
    print(f'  oral_wrong {W}x{H} idx={idx} k={k} cls={s["cls"]} next={s["next"]!r} dis={s["dis"]} why={s["why"]} FIT bad={bad} MEAS {m}')
    await shot(pg, f'oral_wrong_{W}x{H}.png')
    await pg.context.close()

async def oral_pass(b, url, W, H):
    # oral_pass_<WxH>: all 15 right -> the result card A, 15 of 15, six topic rows
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    await school_s4(pg)
    await pg.evaluate(f"()=>{K}.oralSeed(1)")
    await open_oral(pg)
    for i in range(15):
        await oral_answer(pg, i, right=True)
        await oral_next(pg)
    await pg.wait_for_timeout(300)
    c = await pg.evaluate(ORAL_CARD)
    print(f'  oral_pass {W}x{H} on={c["on"]} letter={c["letter"]!r} score={c["score"]!r} topics={len(c["topics"])} missed={len(c["missed"])}')
    await shot(pg, f'oral_pass_{W}x{H}.png')
    await pg.context.close()

async def oral_fail(b, url):
    # oral_fail_844x390: 10 right then 5 wrong -> F, the Missed list (5 rows)
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    await school_s4(pg)
    await pg.evaluate(f"()=>{K}.oralSeed(7)")
    await open_oral(pg)
    for i in range(15):
        await oral_answer(pg, i, right=(i < 10))
        await oral_next(pg)
    await pg.wait_for_timeout(300)
    c = await pg.evaluate(ORAL_CARD)
    print(f'  oral_fail 844x390 on={c["on"]} letter={c["letter"]!r} score={c["score"]!r} missed={len(c["missed"])} mh={c["mh"]}')
    await shot(pg, 'oral_fail_844x390.png')
    await pg.context.close()

async def item5(b, url):
    # the whole item5 group, end to end; may run over 110s, never call this one directly in a single foreground Bash call
    await map_s4(b, url)
    await oral_q1(b, url, 844, 390); await oral_q1(b, url, 568, 320); await oral_q1(b, url, 390, 844)
    await oral_wrong(b, url, 844, 390); await oral_wrong(b, url, 568, 320)
    await oral_pass(b, url, 844, 390); await oral_pass(b, url, 568, 320)
    await oral_fail(b, url)

# ---------------- item 6: Stage 4 lesson 2, the mock checkride (Frank Delgado, DPE; #RIDE) ----------------
# Driving helpers duplicated from school_ride_check.py rather than imported: that module's last line is a bare
# asyncio.run(main()) with no __main__ guard, so importing it would run the whole check (a second server/browser) as
# a side effect. R-prefixed to avoid clashing with this file's own fly()/FLY (a different flight interpolation used
# by the nav lessons).
RFLY = SF.FLY.replace("let i=0;\n  for(;i<n&&K.LES.on;i++)", "let i=0;const tk=K.LES.on;\n  for(;i<n&&K.LES.on===tk;i++)")
assert RFLY != SF.FLY
RWAIT = "(id)=>{const K=window.__kgeu;let i=0;for(;i<900&&K.LES.on&&K.LES.on!==id;i++){const s=K.state();s.windKt=0;s.gustAmp=0;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return [K.LES.on,i,document.getElementById('lesT').textContent]}"
RSTALL = """(o)=>{const K=window.__kgeu,u=o.u?new Function('K','return '+o.u):null;let i=0;const tk=K.LES.on;
  for(;i<(o.n||400)&&K.LES.on===tk;i++){const s=K.state();s.windKt=0;s.gustAmp=0;s.throttle=s.power=o.thr;
    const V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225);s.vel.set(0,o.vy||0,-V);s.quat.setFromEuler(new THREE.Euler(o.p,0,0,'YXZ'));s.w.set(0,0,0);
    K.stepFrame(0.1,false,true);if(u&&u(K))break;}K.stepFrame(0,true);return {ph:K.LES.ph,on:K.LES.on,i:i}}"""
RGROUND = """([x,z,n])=>{const K=window.__kgeu,tk=K.LES.on;for(let i=0;i<n&&K.LES.on===tk;i++){const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return K.LES.on}"""
RFIELD = """()=>{const K=window.__kgeu,O=K.lesObjs(),M=O.filter(o=>o.name==='fieldMk'),s=K.state();if(!M.length)return null;
  const cx=M.reduce((p,o)=>p+o.x,0)/M.length,cz=M.reduce((p,o)=>p+o.z,0)/M.length;
  return {cx:cx,cz:cz,brg:(Math.atan2(cx-s.pos.x,-(cz-s.pos.z))*180/Math.PI+360)%360,M:M.map(o=>[o.x,o.z])}}"""
RCARD = """()=>{const g=document.getElementById('gradeOv'),q=s=>{const e=g.querySelector(s);return e?e.textContent:null};
  return {on:g.classList.contains('on'),cert:g.classList.contains('cert'),letter:q('#gLetter'),
    title:document.getElementById('gTitle').firstChild.textContent,kick:q('.cert .cK'),name:q('.cert .cN'),date:q('.cert .cD'),score:q('.cert .cS'),
    rows:[...g.querySelectorAll('#gLines .gt')].map(r=>[r.querySelector('span').textContent,r.className.replace('gl gt rr','').trim(),r.querySelector('b').textContent]),
    board:q('#gLines .lbLine'),rt:[...g.querySelectorAll('.rtGo')].map(b=>{const r=b.getBoundingClientRect();return [b.dataset.l,b.textContent,Math.round(r.width),Math.round(r.height)]}),
    tip:q('.rTip'),retry:q('#gRetry')}}"""
RFIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight,bad=[];
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});
  const c=s.querySelector('.cert');if(c){const r=c.getBoundingClientRect();if(r.bottom>H||r.top<0)bad.push('cert off screen');}
  const b=s.querySelector('.rLines');if(b&&b.scrollHeight>b.clientHeight+1)bad.push('lines scroll');return bad;}"""
RMEAS = """()=>{const g=document.getElementById('gLines'),c=document.querySelector('#gradeOv .cert');
  return {glScrollH:g&&g.scrollHeight, glClientH:g&&g.clientHeight, certScrollH:c&&c.scrollHeight, certClientH:c&&c.clientHeight};}"""
RFRANK = "()=>window.__kgeu.radioLog().filter(l=>l.who==='Frank').map(l=>l.text)"

async def rfly(pg, n, **o):
    return await pg.evaluate(RFLY, [n, o])

def rvs(kt, deg):
    return kt * 101.27 * math.tan(math.radians(deg) - 0.04)

async def rwait(pg, tid):
    return await pg.evaluate(RWAIT, tid)

async def r_t_steep(pg):
    kt = await pg.evaluate(f"()=>Math.round({K}.state().ias*1.943844)")
    await rfly(pg, 10, kt=kt, vs=0, hdg=0, bank=45, until="K.LES.ph===1")
    await rfly(pg, 600, kt=kt, vs=0, hdg=0, bank=45, rate=10, until="K.LES.d.turned>=340")
    await rfly(pg, 20, kt=kt, vs=0, hdg=360, bank=0)

async def r_t_slow(pg):
    await rfly(pg, 400, kt=58, vs=0, hdg=0, thr=0.5, until="K.LES.ph===1")
    await rfly(pg, 600, kt=58, vs=0, hdg=0, thr=0.5)

async def r_t_stall(pg):
    for o in ({'kt': 48, 'p': 0.5, 'thr': 0, 'u': 'K.LES.ph===1'}, {'kt': 60, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===2'}, {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1, 'u': 'K.LES.ph===3'},
              {'kt': 58, 'p': 0.1, 'vy': 0, 'thr': 0.4, 'n': 20}, {'kt': 52, 'p': 0.55, 'thr': 1, 'u': 'K.LES.ph===4'}, {'kt': 62, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===5'},
              {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1}):
        await pg.evaluate(RSTALL, o)

async def r_t_emerg(pg):
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<60&&!K.LES.d.go;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}}")
    await rfly(pg, 700, thr=0, bank=45, kt=130, vs=-2500, hdg=0, rate=8, until="K.LES.ph===1")
    await rfly(pg, 80, alt=3500, thr=0.8, kt=100, vs=0, hdg=90, until="K.LES.ph===2")
    await rfly(pg, 140, kt=100, vs=0, hdg=90, until="K.LES.ph===3")
    f = await pg.evaluate(RFIELD)
    await rfly(pg, 120, kt=68, vs=-650, hdg=f['brg'])
    ax, az = (f['M'][1][0] - f['M'][0][0]), (f['M'][1][1] - f['M'][0][1]); L = math.hypot(ax, az); ax, az = ax / L, az / L
    h = (math.degrees(math.atan2(ax, -az)) + 360) % 360
    await rfly(pg, 10, x=f['cx'] - ax * 600, z=f['cz'] - az * 600, agl=250, kt=62, vs=-500, hdg=h)
    await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:220,paved:K.isPaved(x,z),x:x,z:z,ias:30,bank:0}})}}", [f['cx'], f['cz']])
    await rfly(pg, 2, agl=20, kt=50, vs=-100, hdg=h)
    await pg.evaluate(RGROUND, [f['cx'], f['cz'], 30])

async def r_t_hood(pg):
    await rfly(pg, 700, alt=3500, kt=90, vs=0, hdg=0, until="K.LES.ph===1")
    await rfly(pg, 200, kt=90, vs=0, hdg=0, rate=4.5, bank=15)
    await rfly(pg, 400, kt=90, vs=0, hdg=90, until="K.LES.ph===2")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on==='hood';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", 40)
    await rfly(pg, 6, thr=0, bank=50, kt=118, vs=rvs(118, -25), hdg=90)
    await rfly(pg, 6, bank=0, kt=125, vs=rvs(125, -25), hdg=90)
    await rfly(pg, 30, bank=0, kt=125, vs=300, hdg=90, until="K.LES.ph===3")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on==='hood';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", 40)
    await rfly(pg, 6, thr=1, bank=-40, kt=68, vs=rvs(68, 30), hdg=90)
    await rfly(pg, 10, bank=-40, kt=70, vs=0, hdg=90)
    await rfly(pg, 60, bank=0, kt=75, vs=0, hdg=90)

async def r_t_landings(pg):
    F = await rwy(pg)
    assert await call(pg), 'no CALL at the hold'
    await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}")
    for c in range(3):
        await SF.climbout(pg, F); await downwind(pg, F)
        assert await call(pg), ('no readback', c)
        await downwind(pg, F, 80); await base(pg, F)
        if c == 1:
            await final(pg, F, to=320)
            await SF.fly(pg, 3, agl=295, kt=65, vs=-400, hdg=F['rh'])
            await SF.fly(pg, 120, thr=1, kt=70, vs=900, hdg=F['rh'], until="K.LES.d.c===2")
            continue
        await final(pg, F)
        await touchdown(pg, F, past=60)
        if c == 0:
            await SF.fly(pg, 30, agl=30, kt=60, vs=0, hdg=F['rh'])
            await SF.fly(pg, 10, agl=150, kt=70, vs=500, hdg=F['rh'], until="K.LES.d.c===1")
        else:
            await stop(pg, F)

RDRIVE = {'steep': r_t_steep, 'slow': r_t_slow, 'stall': r_t_stall, 'emerg': r_t_emerg, 'hood': r_t_hood, 'landings': r_t_landings}
RIDE_DUMP = '/tmp/ride_pass_storage.json'

async def ride_task(b, url, W, H):
    # ride_task_<WxH>: mid ride, during the steep turns task (the ride's first task under rideSeed(42), partway into
    # the turn, not complete): Frank's subtitle (#atc, "Frank" as the speaker), the lesson card, the cue strip
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
    seq = await pg.evaluate(f"()=>{{{K}.rideSeed(42);const s={K}.rideDraw();{K}.rideSeed(42);return s}}")
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('ride');K.lesBriefSkip();const s=K.state();s.windKt=0;s.gustAmp=0;}}")
    await pg.wait_for_timeout(200)
    w = await rwait(pg, 'steep')
    kt = await pg.evaluate(f"()=>Math.round({K}.state().ias*1.943844)")
    await rfly(pg, 10, kt=kt, vs=0, hdg=0, bank=45, until="K.LES.ph===1")
    await rfly(pg, 90, kt=kt, vs=0, hdg=0, bank=45, rate=10)  # partway into the 340 degree turn: mid-task
    info = await pg.evaluate("""()=>{const a=document.getElementById('atc'),b=a.querySelector('b');
      return {title:document.getElementById('lesT').textContent, cue:document.getElementById('lesCue').classList.contains('on'),
        atcOn:a.classList.contains('on'), who:b&&b.textContent, turned:window.__kgeu.LES.d.turned};}""")
    print(f'  ride_task {W}x{H} seq={seq} w={w} title={info["title"]!r} cue={info["cue"]} atcOn={info["atcOn"]} who={info["who"]!r} turned={round(info["turned"])}')
    await shot(pg, f'ride_task_{W}x{H}.png')
    await pg.context.close()

async def ride_fail(b, url):
    # ride_fail_844x390: rideSeed(1) (slow flight first) stalled: the F card (Notice of disapproval), the Retrain row(s)
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    seq = await pg.evaluate(f"()=>{{{K}.rideSeed(1);const s={K}.rideDraw();{K}.rideSeed(1);return s}}")
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('ride');K.lesBriefSkip();}}")
    w = await rwait(pg, seq[0])
    await pg.evaluate(RSTALL, {'kt': 40, 'p': 0.6, 'thr': 0, 'n': 200})
    await pg.wait_for_timeout(700)
    c = await pg.evaluate(RCARD)
    bad = await pg.evaluate(RFIT, '#gradeOv')
    print(f'  ride_fail 844x390 seq={seq} w={w} letter={c["letter"]!r} title={c["title"]!r} row0={c["rows"][0]} rt={c["rt"]} FIT bad={bad}')
    await shot(pg, 'ride_fail_844x390.png')
    await pg.context.close()

async def ride_cert(b, url):
    # drives rideSeed(42) (steep, slow, stall, emerg, hood, landings) through to a pass, shoots ride_cert_844x390 at
    # once and again 1.5s later (the XP pop), then resizes to 568x320 for the narrow shot (no redrive: same trick
    # school_ride_check.py uses for its own 844/568 cert shots). Dumps every kgeu* localStorage key to RIDE_DUMP so
    # ride_boards_map can be seeded straight to the passed state instead of re-flying the whole ride.
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(ST, kgeuSchoolEasy='1'))
    seq = await pg.evaluate(f"()=>{{{K}.rideSeed(42);const s={K}.rideDraw();{K}.rideSeed(42);return s}}")
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('ride');K.lesBriefSkip();const s=K.state();s.windKt=0;s.gustAmp=0;}}")
    await pg.wait_for_timeout(200)
    w = await rwait(pg, 'steep')  # the lesson needs a few simulated frames to actually enter the first task
    assert w[0] == 'steep', ('never started', 'steep', w)
    for k, tid in enumerate(seq):
        if k:
            w = await rwait(pg, tid)
            assert w[0] == tid, ('never started', tid, w)
        await RDRIVE[tid](pg)
    await pg.wait_for_timeout(700)
    c = await pg.evaluate(RCARD)
    bad = await pg.evaluate(RFIT, '#gradeOv')
    xp = await pg.evaluate("()=>{const b=document.getElementById('xpPops');return {log:window.__kgeu.XPP.log.slice(-1),n:b?b.children.length:0,boxExists:!!b}}")
    print(f'  ride_cert 844x390 seq={seq} letter={c["letter"]!r} cert={c["cert"]} score={c["score"]!r} rows={len(c["rows"])} board={c["board"]!r} FIT bad={bad} xp={xp}')
    await shot(pg, 'ride_cert_844x390.png')
    await pg.wait_for_timeout(1500)
    xp2 = await pg.evaluate("()=>{const b=document.getElementById('xpPops'),e=b&&b.firstElementChild;return {n:b?b.children.length:0,op:e&&getComputedStyle(e).opacity,txt:e&&e.textContent}}")
    print(f'  ride_cert 844x390 (+1.5s) xp={xp2}')
    await shot(pg, 'ride_cert_844x390_t1500.png')
    await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400)
    bad2 = await pg.evaluate(RFIT, '#gradeOv')
    meas = await pg.evaluate(RMEAS)
    print(f'  ride_cert 568x320 FIT bad={bad2} MEAS {meas}')
    await shot(pg, 'ride_cert_568x320.png')
    fr = await pg.evaluate(RFRANK)
    print('\n  Frank, the passed ride, in order:')
    for t in fr:
        print('   - ' + t)
    print()
    dump = await pg.evaluate("()=>Object.fromEntries(Object.keys(localStorage).filter(k=>k.indexOf('kgeu')===0).map(k=>[k,localStorage.getItem(k)]))")
    with open(RIDE_DUMP, 'w') as f:
        json.dump(dump, f)
    await pg.context.close()

async def ride_boards_map(b, url):
    # boards_ride_844x390 (Boards screen, Checkride board selected, one row) and map_s4_cert_844x390 (the Flight
    # school screen after the pass: the header's certificate line, Stage 4 ticked); seeded from RIDE_DUMP (written by
    # ride_cert) so this is a page load + two taps instead of a second full ride drive
    with open(RIDE_DUMP) as f:
        dump = json.load(f)
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(ST, **dump))
    await pg.evaluate(f"()=>{{{K}.openMenu('sLb');{K}.LB.lbOpen('lesson:ride')}}"); await pg.wait_for_timeout(500)
    lb = await pg.evaluate("""()=>{const g=[...document.querySelectorAll('#lbList h3')].map(h=>[h.textContent,[...h.nextElementSibling.querySelectorAll('[data-lbb]')].map(b=>[b.dataset.lbb,b.textContent])]);
      return {g:g,title:document.getElementById('lbTitle').textContent,rows:document.querySelectorAll('#lbRowsIn .lbRow').length,how:document.getElementById('lbHow').textContent}}""")
    print(f'  boards_ride 844x390 title={lb["title"]!r} rows={lb["rows"]} how={lb["how"]!r}')
    await shot(pg, 'boards_ride_844x390.png')
    await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
    await pg.evaluate("()=>{const b=document.querySelector('#schMap [data-st=s4]');if(b)b.click()}"); await pg.wait_for_timeout(300)
    h = await pg.evaluate("""()=>({c:document.getElementById('schCert').textContent,vis:!document.getElementById('schCert').hidden&&getComputedStyle(document.getElementById('schCert')).display!=='none',
      ring:document.querySelector('#schMap [data-st=s4] .ring').textContent, row:[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.className.replace('lrow','').trim()])})""")
    print(f'  map_s4_cert 844x390 cert={h["c"]!r} vis={h["vis"]} ring={h["ring"]!r} rows={h["row"]}')
    await shot(pg, 'map_s4_cert_844x390.png')
    await pg.context.close()

async def item6(b, url):
    # the whole item6 group, end to end; well over 110s, never call this one directly in a single foreground Bash call
    await ride_task(b, url, 844, 390); await ride_task(b, url, 568, 320)
    await ride_fail(b, url)
    await ride_cert(b, url)
    await ride_boards_map(b, url)

# ---------------- item 7: the logbook (certificate block, endorsements in order, entry notes, "N night", debrief Logbook row) ----------------
# logbook_full: the same seed as school_log_check.py's (e) block -- pilotage, soloxc, night, hood, oral, ride (F then a
# passing B once kgeuCert is set): solo + solo cross country endorsements, the certificate block, XC full (3.0 of 3), "3 night".
LOG7_SEED = f"""()=>{{const K={K};
  localStorage.setItem('kgeuEndorse',JSON.stringify({{xc:{{at:Date.UTC(2026,9,8,18),by:'Dana Reyes, CFI',lesson:'soloxc'}},solo:{{at:Date.UTC(2026,9,2,18),by:'Dana Reyes, CFI',lesson:'solo'}}}}));
  K.logbookAdd('pilotage',{{letter:'B',score:84}});K.logbookAdd('soloxc',{{letter:'A',score:91}});K.logbookAdd('night',{{letter:'B',score:82}});
  K.logbookAdd('hood',{{letter:'C',score:74}});K.logbookAdd('oral',{{letter:'C',score:80,right:12,of:15}});K.logbookAdd('ride',{{letter:'F',score:61}});
  localStorage.setItem('kgeuCert',JSON.stringify({{at:Date.UTC(2026,9,9,18),cs:'N172KG',score:88,examiner:'Frank Delgado, DPE'}}));
  K.logbookAdd('ride',{{letter:'B',score:88}});}}"""

# logbook_worst: the break check's worst case (school_break_check.py's SEEDED), copied by value so this file never
# imports and re-runs that check's own asyncio.run(main()) -- 60 entries, 999.9 h, 9,999 landings and night landings,
# the longest notes, both endorsements and the certificate block.
LESSON_IDS7 = ['first', 'climbs', 'pattern', 'slow', 'stall', 'ground', 'landings', 'engine', 'solo',
               'steep', 'short', 'soft', 'xwind', 'emerg', 'hood', 'pilotage', 'divert', 'night', 'soloxc', 'oral', 'ride']
CS7 = 'WWWWWWWWWWWW'

def mk_logbook7():
    ents = []
    for i in range(60):
        lid = LESSON_IDS7[i % len(LESSON_IDS7)]
        f = i % 11 == 0
        ents.append({'id': lid, 'at': 1700000000000 - i * 86400000, 'score': 0 if f else 93, 'letter': 'F' if f else 'A',
                     'dual': 0 if f else 5.5, 'solo': 0 if f else 2.3, 'xc': 0 if f else 4.1,
                     'night': 0 if f else 3.2, 'inst': 0 if f else 2.7, 'ldg': 0 if f else 12, 'nldg': 0 if f else 12,
                     'note': ['KGEU-KPHX-KGEU, 36 nm', '12 of 15', 'Notice of disapproval', '9999 night landings', 'Diverted to KGEU'][i % 5]})
    return {'dual': 900.0, 'solo': 99.9, 'xc': 5, 'night': 5, 'inst': 5, 'ldg': 9999, 'nldg': 9999, 'entries': ents}

WORST7 = dict(BASE, **{
    'kgeuPlace': json.dumps({'level': 'cert', 'hours': 20000, 'at': 1700000000000}),
    'kgeuSchool': json.dumps({f'cessna:{lid}': 'A' for lid in LESSON_IDS7}),
    'kgeuLogbook': json.dumps(mk_logbook7()),
    'kgeuEndorse': json.dumps({'solo': {'at': 1700000000000, 'by': 'Dana Reyes, CFI', 'lesson': 'solo'},
                                'xc': {'at': 1700500000000, 'by': 'Dana Reyes, CFI', 'lesson': 'soloxc'}}),
    'kgeuCert': json.dumps({'at': 1700000000000, 'cs': CS7, 'score': 100, 'examiner': 'Frank Delgado, DPE'}),
    'kgeuLB': json.dumps({'cs': CS7, 'key': 'k' * 48, 'xp': 16000, 'creator': False, 'renamed': 0, 'renameAt': 0, 'created': 1}),
})

MEAS7 = """()=>{const ov=id=>{const e=document.getElementById(id);if(!e)return null;return [e.scrollWidth,e.clientWidth,e.scrollWidth>e.clientWidth+1]};
  const b=document.getElementById('mBack').getBoundingClientRect();
  return {cert:ov('logCert'),end:ov('logEnd'),list:ov('logList'),back:[Math.round(b.width),Math.round(b.height)]}}"""

async def open_log(pg):
    await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
    await finger(pg, '#schLog'); await pg.wait_for_timeout(800)

async def logbook_full(b, url):
    # logbook_full_<WxH> at 844x390, 568x320, 390x844, one page/seed, resized for each shot
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    await pg.evaluate(LOG7_SEED)
    await open_log(pg)
    await pg.wait_for_timeout(400)
    for W, H in ((844, 390), (568, 320), (390, 844)):
        await pg.set_viewport_size({'width': W, 'height': H}); await pg.wait_for_timeout(400)
        m = await pg.evaluate(MEAS7)
        print(f'  logbook_full {W}x{H} meas {m}')
        await shot(pg, f'logbook_full_{W}x{H}.png')
    await pg.context.close()

async def logbook_worst(b, url):
    # logbook_worst_<WxH> at 844 and 568: the break check's worst case
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=WORST7)
    await open_log(pg)
    for W, H in ((844, 390), (568, 320)):
        await pg.set_viewport_size({'width': W, 'height': H}); await pg.wait_for_timeout(400)
        m = await pg.evaluate(MEAS7)
        print(f'  logbook_worst {W}x{H} meas {m}')
        await shot(pg, f'logbook_worst_{W}x{H}.png')
    await pg.context.close()

async def night_debrief_log(b, url):
    # night_debrief_log_844x390: the night lesson's clean run (three full stops), the debrief's Logbook row
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=ST)
    F, shown, sub, sky0 = await night_start(pg)
    await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    await pg.evaluate(NIGHT_WAIT_RB)
    for k in range(3):
        if k: await call(pg)
        await night_circuit(pg, F, past=40 + 30 * k)
    await pg.wait_for_timeout(800)
    d = await pg.evaluate(DEBRIEF)
    vis = await pg.evaluate("""()=>{const sheet=document.querySelector('#gradeOv .sheet'),rl=document.querySelector('#gradeOv .rLines');
      const log=document.querySelector('#gradeOv .gLog');if(!log)return {log:false};const r=log.getBoundingClientRect();
      const rows=[...rl.children].map(e=>{const q=e.getBoundingClientRect(),cs=getComputedStyle(e);return [e.className,Math.round(q.top),Math.round(q.bottom),cs.opacity,cs.visibility,cs.display,cs.color,cs.zIndex]});
      const btns=document.querySelector('#gradeOv .rBtns');const br=btns?btns.getBoundingClientRect():null;
      return {log:true,sheetScroll:sheet.scrollHeight,sheetClient:sheet.clientHeight,cols:getComputedStyle(rl).gridTemplateColumns,
        logTop:Math.round(r.top),logBottom:Math.round(r.bottom),logInView:r.top>=0&&r.bottom<=innerHeight,rows:rows,
        btns:br&&[Math.round(br.top),Math.round(br.bottom)],sheetTop:sheet.getBoundingClientRect().top}}""")
    print(f'  night_debrief_log 844x390 on {d["on"]} letter {d["letter"]} gl {d["gl"]}')
    print(f'  night_debrief_log Logbook row visibility: {vis}')
    await shot(pg, 'night_debrief_log_844x390.png')
    await pg.context.close()

async def item7(b, url):
    # the whole item7 group, end to end; well over 110s, never call this one directly in a single foreground Bash call
    await logbook_full(b, url)
    await logbook_worst(b, url)
    await night_debrief_log(b, url)

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
        if '--div844' in sys.argv:
            await div844(b, url); await b.close(); srv.shutdown(); return
        if '--div568' in sys.argv:
            await div568(b, url); await b.close(); srv.shutdown(); return
        if '--divdeb844' in sys.argv:
            await divdebrief(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--divdeb568' in sys.argv:
            await divdebrief(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--n844' in sys.argv:
            await n844(b, url); await b.close(); srv.shutdown(); return
        if '--n568' in sys.argv:
            await n568(b, url); await b.close(); srv.shutdown(); return
        if '--ndeb844' in sys.argv:
            await ndeb(b, url, 844, 390, after=True); await b.close(); srv.shutdown(); return
        if '--ndeb568' in sys.argv:
            await ndeb(b, url, 568, 320, after=False); await b.close(); srv.shutdown(); return
        if '--item3' in sys.argv:
            await n844(b, url); await n568(b, url); await ndeb(b, url, 844, 390, after=True); await ndeb(b, url, 568, 320, after=False)
            await b.close(); srv.shutdown(); return
        if '--item4map' in sys.argv:
            await map_s3_full(b, url); await b.close(); srv.shutdown(); return
        if '--item4call844' in sys.argv:
            await solo_call(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--item4call568' in sys.argv:
            await solo_call(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item4deb844' in sys.argv:
            await solo_debrief(b, url, 844, 390, logbook=True); await b.close(); srv.shutdown(); return
        if '--item4deb568' in sys.argv:
            await solo_debrief(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item4' in sys.argv:
            await item4(b, url); await b.close(); srv.shutdown(); return
        if '--item5map' in sys.argv:
            await map_s4(b, url); await b.close(); srv.shutdown(); return
        # oral_q1 (~25-30s a size): per-size flags stay safely under the 110s cap; --item5q1 combines all three but
        # can border on it (never call it in a single foreground Bash call; use the per-size flags instead)
        if '--item5q1_844' in sys.argv:
            await oral_q1(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--item5q1_568' in sys.argv:
            await oral_q1(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item5q1_390x844' in sys.argv:
            await oral_q1(b, url, 390, 844); await b.close(); srv.shutdown(); return
        if '--item5q1' in sys.argv:
            await oral_q1(b, url, 844, 390); await oral_q1(b, url, 568, 320); await oral_q1(b, url, 390, 844)
            await b.close(); srv.shutdown(); return
        if '--item5wrong_844' in sys.argv:
            await oral_wrong(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--item5wrong_568' in sys.argv:
            await oral_wrong(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item5wrong' in sys.argv:
            await oral_wrong(b, url, 844, 390); await oral_wrong(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item5pass_844' in sys.argv:
            await oral_pass(b, url, 844, 390); await b.close(); srv.shutdown(); return
        if '--item5pass_568' in sys.argv:
            await oral_pass(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item5pass' in sys.argv:
            await oral_pass(b, url, 844, 390); await oral_pass(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item5fail' in sys.argv:
            await oral_fail(b, url); await b.close(); srv.shutdown(); return
        if '--item5' in sys.argv:
            await item5(b, url); await b.close(); srv.shutdown(); return
        if '--item6task' in sys.argv:
            await ride_task(b, url, 844, 390); await ride_task(b, url, 568, 320); await b.close(); srv.shutdown(); return
        if '--item6fail' in sys.argv:
            await ride_fail(b, url); await b.close(); srv.shutdown(); return
        if '--item6cert' in sys.argv:
            await ride_cert(b, url); await b.close(); srv.shutdown(); return
        if '--item6boardsmap' in sys.argv:
            await ride_boards_map(b, url); await b.close(); srv.shutdown(); return
        if '--item6' in sys.argv:
            await item6(b, url); await b.close(); srv.shutdown(); return
        if '--item7full' in sys.argv:
            await logbook_full(b, url); await b.close(); srv.shutdown(); return
        if '--item7worst' in sys.argv:
            await logbook_worst(b, url); await b.close(); srv.shutdown(); return
        if '--item7night' in sys.argv:
            await night_debrief_log(b, url); await b.close(); srv.shutdown(); return
        if '--item7' in sys.argv:
            await item7(b, url); await b.close(); srv.shutdown(); return
        if '--item1b' in sys.argv:
            await item1b(b, url); await b.close(); srv.shutdown(); return
        if '--item1a' in sys.argv:
            await item1a(b, url); await b.close(); srv.shutdown(); return
        await item1a(b, url)
        await item1b(b, url)
        await b.close()
    srv.shutdown()
asyncio.run(main())
