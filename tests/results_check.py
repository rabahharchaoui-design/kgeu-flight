# Phone2 item 1: the post run results card. Every run end (free flight landing, challenge,
# lesson, mission, strike) gets one card: letter grade, score, key stats, the board line, and
# two buttons, CONTINUE and MAIN MENU. It slides in once the aircraft has stopped (or when the
# run ends in the air). Free flight: brief, never pauses, goes on its own, the stick and
# throttle beside it still work; a touch and go shows no card. Fits 844x390 and 568x320 and
# portrait 390x844 with 44 px targets. Screenshots: overnight-screenshots/phone2/item1/.
# Run: .venv/bin/python tests/results_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone2', 'item1')
CARD = """(id)=>{const o=document.getElementById(id),q=s=>o.querySelector(s);return {on:o.classList.contains('on'),brief:o.classList.contains('brief'),
  letter:q('.gLetter').textContent,title:q('.sub').textContent,score:q('.rScore').textContent,lines:q('.rLines').innerText,
  btns:[...o.querySelectorAll('.rBtns button')].map(b=>b.textContent),links:[...o.querySelectorAll('.rLinks button')].filter(b=>!b.hidden).map(b=>b.textContent),
  paused:window.__kgeu.paused(),running:window.__kgeu.running()}}"""
FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight;const bad=[];
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width||e.hidden)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off screen '+(e.id||e.textContent));
    if(r.width<43.5||r.height<43.5)bad.push('small '+(e.id||e.textContent)+' '+Math.round(r.width)+'x'+Math.round(r.height));
    if(e.scrollWidth>e.clientWidth+1)bad.push('text cut '+e.textContent);});
  const sh=s.querySelector('.sheet').getBoundingClientRect();if(sh.bottom>H+0.5||sh.top<-0.5)bad.push('sheet off screen '+Math.round(sh.top)+'..'+Math.round(sh.bottom)+' of '+H);
  if(s.scrollHeight>s.clientHeight+1)bad.push('scrolls '+s.scrollHeight+'>'+s.clientHeight);
  return bad;}"""
S = "()=>{const s=window.__kgeu.state();return {g:s.onGround,v:Math.hypot(s.vel.x,s.vel.z),crash:s.crashed}}"

async def land(pg, typ='cessna', pos='final'):
    await pg.evaluate(f"()=>{{const K={K};K.pick('{typ}');K.pickBase('kgeu');K.start('{pos}');}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{K}.auto()")
    for _ in range(90):
        await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
        st = await pg.evaluate(S)
        if st['g'] or st['crash']: return st
    return st

async def roll_to_stop(pg, ov, n=40):
    for _ in range(n):
        await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(100)
        if await pg.evaluate(f"()=>document.getElementById('{ov}').classList.contains('on')"): break
    await pg.wait_for_timeout(500)

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})

        # ---- free flight landing: brief card at the stop, no pause
        st = await land(pg)
        ok('autoland lands', st['g'] and not st['crash'], st)
        await pg.wait_for_timeout(400)
        c = await pg.evaluate(CARD, 'landOv')
        ok('no card while the aircraft is still rolling', not c['on'], c['on'])
        await roll_to_stop(pg, 'landOv')
        st = await pg.evaluate(S); c = await pg.evaluate(CARD, 'landOv')
        ok('the aircraft has stopped', st['g'] and st['v'] < 1.5, st)
        ok('free flight: the results card slides in at the stop, brief, no pause', c['on'] and c['brief'] and not c['paused'], c)
        ok('letter grade, score and title', c['letter'] in 'ABCDF' and 'pts' in c['score'] and 'Free flight landing' in c['title'], (c['letter'], c['score'], c['title']))
        for k in ('Sink rate', 'Airspeed', 'centreline', 'aim point', 'Flight time'):
            ok('stat: ' + k, k in c['lines'], c['lines'].replace('\n', ' | ')[:160])
        ok('CONTINUE and MAIN MENU', c['btns'] == ['CONTINUE', 'MAIN MENU'], c['btns'])
        ok('Fly again and Records as links', c['links'] == ['Fly again', 'Records'], c['links'])
        bad = await pg.evaluate(FIT, '#landOv')
        ok('fits 844x390 with 44 px targets', not bad, bad)
        await pg.screenshot(path=f'{SHOTS}/free_landing_844x390.png')
        # the stick and throttle beside it still work: the overlay lets touches through
        thru = await pg.evaluate("()=>{const r=document.getElementById('thr').getBoundingClientRect();const e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return !!e&&(e.id==='thr'||!!e.closest('#thrCol'))}")
        ok('the throttle is still reachable beside the brief card', thru)
        await finger(pg, '#lKeep'); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CARD, 'landOv')
        ok('CONTINUE dismisses it and the flight goes on', not c['on'] and not c['paused'] and c['running'], c)

        # ---- it goes on its own
        await pg.evaluate(f"()=>{{{K}.RES.briefAt=0;}}")
        st = await land(pg); await roll_to_stop(pg, 'landOv')
        c = await pg.evaluate(CARD, 'landOv')
        ok('second landing: card up again', c['on'] and c['brief'], c)
        await pg.evaluate(f"()=>{{{K}.RES.briefAt=performance.now()-1;}}"); await pg.wait_for_timeout(500)
        c = await pg.evaluate(CARD, 'landOv')
        ok('the brief card leaves on its own after its time', not c['on'], c)

        # ---- the grade badge opens the same card as the details, paused
        st = await land(pg); await pg.wait_for_timeout(300)
        await finger(pg, '#gBadge'); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CARD, 'landOv')
        ok('badge tap: the card as details, paused', c['on'] and not c['brief'] and c['paused'], c)
        await finger(pg, '#lKeep'); await pg.wait_for_timeout(200)

        # ---- touch and go: no card
        st = await land(pg)
        await pg.evaluate(f"()=>{{const s={K}.state();s.ap=null;s.apW=null;s.throttle=1;}}")
        flew = False
        for _ in range(30):
            await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(100)
            e = await pg.evaluate(S)
            if not e['g']: flew = True; break
        for _ in range(10): await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(80)
        c = await pg.evaluate(CARD, 'landOv')
        ok('touch and go: no results card', flew and not c['on'] and not e['crash'], (flew, c['on']))

        # ---- MAIN MENU from the brief card
        st = await land(pg); await roll_to_stop(pg, 'landOv')
        await finger(pg, '#lMenu'); await pg.wait_for_timeout(400)
        m = await pg.evaluate(f"()=>({{menu:document.getElementById('menu').classList.contains('on'),scr:{K}.curScr(),card:document.getElementById('landOv').classList.contains('on')}})")
        ok('MAIN MENU goes to the home screen and closes the card', m['menu'] and m['scr'] == 'sHome' and not m['card'], m)

        # ---- the 1 mile landing challenge: the card pauses, stats, the links
        for attempt in range(3):   # the autoland into a gusty 1 mile final can crash now and then: fly it again
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.arcStart('landing1')}}"); await pg.wait_for_timeout(500)
            await pg.evaluate(f"()=>{K}.auto()")
            for _ in range(90):
                await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
                st = await pg.evaluate(S)
                if st['g'] or st['crash']: break
            if st['g'] and not st['crash']: break
        ok('challenge lands', st['g'] and not st['crash'], st)
        await roll_to_stop(pg, 'arcOv')
        c = await pg.evaluate(CARD, 'arcOv')
        ok('challenge: results card, paused', c['on'] and not c['brief'] and c['paused'], c)
        ok('challenge: letter, score, time and touchdown stats', c['letter'] in 'ABCDF' and 'pts' in c['score'] and 'Time' in c['lines'] and 'Touchdown' in c['lines'] and 'Centreline' in c['lines'], c['lines'].replace('\n', ' | ')[:200])
        ok('challenge: CONTINUE, MAIN MENU and Try again', c['btns'] == ['CONTINUE', 'MAIN MENU'] and c['links'] == ['Try again'], (c['btns'], c['links']))
        bad = await pg.evaluate(FIT, '#arcOv')
        ok('challenge card fits 844x390', not bad, bad)
        await pg.screenshot(path=f'{SHOTS}/challenge_844x390.png')
        await finger(pg, '#aFree'); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CARD, 'arcOv')
        ok('CONTINUE: card gone, flying on, challenge over', not c['on'] and not c['paused'] and not await pg.evaluate(f"()=>{K}.ARC.on"), c)

        # ---- a lesson: the card at the run end in the air
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.startLesson('stall')}}"); await pg.wait_for_timeout(400)
        for _ in range(60):
            await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(80)
            if await pg.evaluate("()=>document.getElementById('gradeOv').classList.contains('on')"): break
        c = await pg.evaluate(CARD, 'gradeOv')
        if not c['on']:   # the stall lesson needs the pilot (school_check flies lesson 1 to its card): open the card the way grade() does
            await pg.evaluate(f"()=>{K}.resOpen(document.getElementById('gradeOv'),{{letter:'B',title:'Flight school: Power off stall',score:'84 of 100',lines:'<div class=ok>Held the heading</div><div class=no>Lost 400 ft</div>',board:'lesson:stall'}})")
            await pg.wait_for_timeout(300); c = await pg.evaluate(CARD, 'gradeOv')
        ok('lesson: the same card, paused', c['on'] and c['paused'] and c['btns'] == ['CONTINUE', 'MAIN MENU'], c)
        bad = await pg.evaluate(FIT, '#gradeOv')
        ok('lesson card fits 844x390', not bad, bad)
        await pg.screenshot(path=f'{SHOTS}/lesson_844x390.png')
        await finger(pg, '#gSchool'); await pg.wait_for_timeout(400)
        ok('lesson MAIN MENU: home', await pg.evaluate(f"()=>document.getElementById('menu').classList.contains('on')&&{K}.curScr()==='sHome'"))

        # ---- the airdrop mission card
        await pg.evaluate(f"()=>{{{K}.pick('c130',1);{K}.start('drop');}}"); await pg.wait_for_timeout(600)
        await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z;}}"); await pg.wait_for_timeout(500)
        await pg.evaluate(f"()=>{K}.missDrop()"); await pg.evaluate(f"()=>{K}.missTick(4000,1/60)"); await pg.wait_for_timeout(500)
        c = await pg.evaluate(CARD, 'missOv')
        ok('airdrop: the results card with distance, paused', c['on'] and c['paused'] and ' m' in c['score'] and 'Distance' in c['lines'] and c['btns'] == ['CONTINUE', 'MAIN MENU'], c)
        bad = await pg.evaluate(FIT, '#missOv')
        ok('mission card fits 844x390', not bad, bad)
        await pg.screenshot(path=f'{SHOTS}/airdrop_844x390.png')
        await finger(pg, '#mFree'); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CARD, 'missOv')
        ok('CONTINUE keeps flying where you are, mission over', not c['on'] and not c['paused'] and not await pg.evaluate(f"()=>{K}.MISS.on"), c)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # ---- 568x320 and portrait: every card fits
        for vp, tag in (({'width': 568, 'height': 320}, '568x320'), ({'width': 390, 'height': 844}, '390x844')):
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRotOk': '1'})
            await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway');}}"); await pg.wait_for_timeout(300)
            await pg.evaluate(f"()=>{K}.resOpen(document.getElementById('landOv'),{{letter:'A',title:'Free flight landing, Glendale runway 1  (12 kt crosswind)',score:'93 pts',sub:'Butter, on centerline',lines:'<div class=gl><span>Sink rate</span><b>101 fpm<i class=\"pt good\">100</i></b></div><div class=gl><span>Off centreline</span><b>1.9 m<i class=\"pt good\">100</i></b></div><div class=gl><span>From the aim point</span><b>59 m long<i class=\"pt good\">98</i></b></div><div class=gl><span>Airspeed</span><b>55 kt vs 65<i class=pt>67</i></b></div><div class=gl><span>Flight time</span><b>2:08</b></div><div class=\"gl lbLine\"><span>Leaderboard</span><b>#4 of 120<em>PERSONAL BEST</em></b></div>',board:''}},true)")
            await pg.wait_for_timeout(400)
            c = await pg.evaluate(CARD, 'landOv')
            ok(f'{tag}: free flight card up', c['on'] and c['brief'], c)
            bad = await pg.evaluate(FIT, '#landOv')
            ok(f'{tag}: landing card fits with 44 px targets', not bad, bad)
            await pg.screenshot(path=f'{SHOTS}/free_landing_{tag}.png')
            await pg.evaluate(f"()=>{K}.resClose(document.getElementById('landOv'))")
            await pg.evaluate(f"()=>{K}.resOpen(document.getElementById('arcOv'),{{letter:'B',title:'1 mile landing challenge: 912 points',score:'912 pts',sub:'Cessna 172',stars:2,stats:[['Time','1:02  (par 1:10)'],['Landing','B  Smooth, on centerline'],['Touchdown','180 fpm, 61 kt'],['Aim point','40 m long'],['Centreline','1.2 m'],['Best','912 pts, 1:02']],board:''}})")
            await pg.wait_for_timeout(400)
            bad = await pg.evaluate(FIT, '#arcOv')
            ok(f'{tag}: challenge card fits', not bad, bad)
            await pg.screenshot(path=f'{SHOTS}/challenge_{tag}.png')
            await pg.evaluate(f"()=>{K}.resClose(document.getElementById('arcOv'))")
            await pg.evaluate(f"()=>{K}.resOpen(document.getElementById('gradeOv'),{{letter:'A',title:'Flight school: Steep turns',score:'94 of 100',lines:'<div class=ok>Bank held within 5 degrees</div><div class=ok>Altitude within 100 ft</div><div class=no>Rolled out 12 degrees late</div>',board:''}})")
            await pg.wait_for_timeout(400)
            bad = await pg.evaluate(FIT, '#gradeOv')
            ok(f'{tag}: lesson card fits', not bad, bad)
            await pg.screenshot(path=f'{SHOTS}/lesson_{tag}.png')
            ok(f'{tag}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    sys.exit(ok.done('results_check'))

asyncio.run(main())
