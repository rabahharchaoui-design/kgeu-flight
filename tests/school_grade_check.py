# School1 item 4: the grading engine, the live tolerance cues, the debrief and the Easy toggle.
# (a) engine arithmetic through window.__kgeu (a hold, a range, an event); (b) slow flight's cue strip, ALT turning out and
# back in; (c) slow flight flown to the end with Easy on: the debrief rows, the quiz row, the Easy tag, fits at 844x390 and
# 568x320; (d) the Standard / Easy chips persist and lock during a lesson; (e) no page errors; (f) item 6: slow flight's
# asymmetric speed band (+10/-0 kt: 54 kt out, 64 in, the band drawn off centre; Easy +20/-5) and the stall lesson's power
# on stall after the power off one, both recoveries scored.
# Run: .venv/bin/python tests/school_grade_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED
ok = Checks()
K = "window.__kgeu"
BASE = dict({'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}, **PLACED)
FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('scrolls');
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});return bad;}"""
FAKE = """{name:'Fake',tasks:[{id:'h',name:'Hold it',w:50,kind:'hold',tol:100,unit:'ft'},{id:'r',name:'Range it',w:30,kind:'range',tol:300,unit:'ft'},{id:'e',name:'Event it',w:20,kind:'event'}]}"""
RUN = """([nin,nout])=>{const K=window.__kgeu;K.gBegin(%s);window.__v=50;K.gHold('h',{get:()=>window.__v,target:0,grace:0});
  const cue=document.getElementById('lesCue').classList.contains('on');
  for(let i=0;i<nin;i++)K.gTick(0.1);window.__v=150;for(let i=0;i<nout;i++)K.gTick(0.1);
  K.gRange('r',250);K.gEvent('e',true,'in 1.4 s');K.gEnd();const R=K.G.res;
  return {cue:cue,score:R.score,lines:R.lines.map(l=>[l.ok,l.detail]),letter:document.getElementById('gLetter').textContent,
    rows:[...document.querySelectorAll('#gLines .gt')].map(r=>[r.classList.contains('ok'),r.querySelector('span').textContent,r.querySelector('b').textContent]),
    tag:!!document.querySelector('#gScore .ezTag'),score2:document.getElementById('gScore').textContent,tip:document.querySelector('#gradeOv .rTip').textContent,
    cueOff:!document.getElementById('lesCue').classList.contains('on')}}""" % FAKE
CLEAR = """()=>{const L=document.getElementById('lesson').getBoundingClientRect(),bad=[];
  const hit=e=>{const r=e.getBoundingClientRect();return r.width&&r.left<L.right&&r.right>L.left&&r.top<L.bottom&&r.bottom>L.top;};
  [...document.querySelectorAll('#dock button'),document.getElementById('thr'),document.getElementById('bPause')].forEach(e=>{if(e&&hit(e))bad.push(e.id);});
  if(L.height>=0.45*innerHeight)bad.push('tall '+Math.round(L.height)+' of '+innerHeight);
  if(!document.getElementById('lesCue').classList.contains('on'))bad.push('no strip');return bad;}"""
CUE = "()=>[...document.querySelectorAll('#lesCue .cue')].map(r=>[r.querySelector('b').textContent,r.className.replace('cue','').trim(),r.querySelector('span').textContent])"

# slow flight's spd hold driven by window.__v: the band class after 54, 64 and 48 kt, the band's gradient, the graded time
BAND = """()=>{const K=window.__kgeu;K.gBegin(K.lessonDef('slow'));K.gHold('alt',{get:()=>3500,target:3500,grace:0});K.gHold('spd',{get:()=>window.__v,target:55,grace:0});
  const h=K.G.tasks.spd,row=()=>document.querySelectorAll('#lesCue .cue')[1],b=[];
  for(const v of [54,64,48]){window.__v=v;for(let i=0;i<3;i++)K.gTick(0.1);b.push(row().className.replace('cue','').trim());}
  window.__v=54;const t0=h.tIn;for(let i=0;i<10;i++)K.gTick(0.1);
  return {hl:[h.hi,h.lo],b:b,bg:row().children[1].style.background,bgAlt:document.querySelectorAll('#lesCue .cue')[0].children[1].style.background,tIn:h.tIn-t0,tAll:h.tAll}}"""
# the stall lesson pinned: o.kt indicated, o.p pitch (rad), o.vy (m/s), o.thr; frames until o.u or o.n
STALL = """(o)=>{const K=window.__kgeu,u=o.u?new Function('K','return '+o.u):null;let i=0;
  for(;i<(o.n||400)&&K.LES.on;i++){const s=K.state();s.windKt=0;s.gustAmp=0;s.throttle=s.power=o.thr;
    const V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225);s.vel.set(0,o.vy||0,-V);s.quat.setFromEuler(new THREE.Euler(o.p,0,0,'YXZ'));s.w.set(0,0,0);
    K.stepFrame(0.1,false,true);if(u&&u(K))break;}K.stepFrame(0,true);return {ph:K.LES.on?K.LES.ph:null,i:i,stalled:K.state().stalled}}"""

async def held(pg):
    await pg.evaluate(f"()=>{{{K}.startLesson('slow',true,{{brief:false}})}}"); await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{{if(!{K}.paused()){K}.togglePause()}}"); await pg.wait_for_timeout(200)

async def to_ph1(pg):   # frame by frame: the lesson clock runs on the frame time (at most 0.1 s a frame), not on ff
    return await pg.evaluate(f"()=>{{const K={K};for(let n=0;n<400&&K.LES.ph!==1;n++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);return K.LES.ph===1}}")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # (a) the engine's arithmetic, Standard tolerances
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuSchoolEasy='0'))
        await held(pg)
        r = await pg.evaluate(RUN, [100, 10])
        ok('(a) the cue strip shows while the hold runs and goes after gEnd', r['cue'] and r['cueOff'], r)
        ok('(a) 10 s in, 1 s out, the range at 250 of 300, the event: 95 (45.5 + 30 + 20), an A', r['score'] == 95 and r['letter'] == 'A', r)
        ok('(a) the detail wording', r['lines'] == [[True, 'inside 91% of the time, worst 150 ft'], [True, '250 ft, standard 300 ft'], [True, 'in 1.4 s']], r['lines'])
        ok('(a) the debrief rows: tick, name, detail', r['rows'] == [[True, 'Hold it', 'inside 91% of the time, worst 150 ft'], [True, 'Range it', '250 ft, standard 300 ft'], [True, 'Event it', 'in 1.4 s']], r['rows'])
        ok('(a) Standard: no Easy tag, the score reads 95 of 100, Dana says checkride standard', not r['tag'] and r['score2'] == '95 of 100' and r['tip'] == 'That was checkride standard. I would sign that off any day.', r)
        t = await pg.evaluate("()=>document.getElementById('gTitle').firstChild.textContent")
        ok('(a) the title reads Debrief: <lesson>', t == 'Debrief: Slow flight', t)
        await held(pg)
        r = await pg.evaluate(RUN, [60, 50])
        ok('(a) 6 s in, 5 s out: the hold fails and scores 5, total 55, an F', r['score'] == 55 and r['letter'] == 'F' and r['lines'][0] == [False, 'inside 55% of the time, worst 150 ft'], r)
        ok('(a) the F tip names the lowest task', r['tip'] == 'Not to standard today, and that is normal at this point. Hold it needs work, so we fly it again.', r['tip'])
        tip = await pg.evaluate(f"()=>{K}.dbTip({{letter:'C',lines:[{{ok:true,name:'Altitude within 100 ft',pts:30,w:35}},{{ok:false,name:'Airspeed on target',pts:10,w:35}}]}})")
        ok('(a) a B to D tip names the worst failed task', tip == 'You passed. Airspeed on target was outside the standard; we will work on it.', tip)
        await pg.context.close()

        # (b) slow flight: the cue strip on the lesson card, three rows, ALT out when 250 ft high, back in
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuSchoolEasy='0'))
        await pg.evaluate(f"()=>{{{K}.startLesson('slow');{K}.lesBriefSkip()}}"); await pg.wait_for_timeout(300)
        hid = await pg.evaluate("()=>getComputedStyle(document.getElementById('lesCue')).display")
        ok('(b) no cue strip before the hold starts', hid == 'none', hid)
        ok('(b) slow flight reaches phase 1', await to_ph1(pg))
        await pg.evaluate(f"()=>{K}.ff(0.3)"); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CUE)
        vis = await pg.evaluate("()=>{const e=document.getElementById('lesCue'),r=e.getBoundingClientRect();return getComputedStyle(e).display!=='none'&&r.height>20&&getComputedStyle(e).pointerEvents==='none'}")
        ok('(b) the strip is visible with ALT, SPD, HDG', vis and [x[0] for x in c] == ['ALT', 'SPD', 'HDG'], c)
        bad = await pg.evaluate(CLEAR)
        ok('(b) 844x390: the card with the strip clears the dock, the throttle and pause, under 45% tall', not bad, bad)
        fit = await pg.evaluate("""()=>{const t=document.getElementById('lesT'),o=t.textContent,r=['Climbs, descents and turns','Stage check and first solo'].filter(n=>{t.textContent=n;return t.scrollWidth>t.clientWidth+0.5;});t.textContent=o;return r}""")
        ok('(b) 844x390: the longest Stage 1 and 2 names fit the title line', not fit, fit)
        await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(500)
        bad = await pg.evaluate(CLEAR)
        m = await pg.evaluate("()=>getComputedStyle(document.getElementById('lesM')).display")
        ok('(b) 568x320: the numbers line is hidden while the strip shows', m == 'none', m)
        t = await pg.evaluate("()=>{const t=document.getElementById('lesT');return [t.textContent,t.getBoundingClientRect().height<24]}")
        ok('(b) 568x320: the card with the strip clears the dock, the throttle and pause, under 45% tall', not bad, bad)
        ok('(b) the title is the lesson name on one line', t == ['Slow flight', True], t)
        await pg.set_viewport_size({'width': 844, 'height': 390}); await pg.wait_for_timeout(500)
        y0 = await pg.evaluate(f"()=>{{const s={K}.state(),y=s.pos.y;s.pos.y+=250/3.28084;return y}}")
        await pg.evaluate(f"()=>{K}.ff(0.5)"); await pg.wait_for_timeout(500)
        c = await pg.evaluate(CUE)
        ok('(b) 250 ft high turns the ALT row out within 0.5 s', c[0][1] == 'out', c)
        await pg.evaluate(f"(y)=>{{const s={K}.state();s.pos.y=y;s.vel.y=0}}", y0)
        await pg.evaluate(f"()=>{K}.ff(0.5)"); await pg.wait_for_timeout(500)
        c = await pg.evaluate(CUE)
        ok('(b) back on altitude, ALT is in again', c[0][1] == 'in', c)
        await pg.context.close()

        # (c) slow flight to the end with Easy on, through the quiz (right answer), the plane held on its numbers
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuSchoolEasy='1'))
        await pg.evaluate(f"()=>{{{K}.startLesson('slow');{K}.lesBriefAnswer(0);{K}.lesBriefSkip()}}"); await pg.wait_for_timeout(300)
        ok('(c) slow flight reaches phase 1', await to_ph1(pg))
        await pg.evaluate(f"()=>{{const s={K}.state();window.__snap={{y:s.pos.y,v:s.vel.clone(),q:s.quat.clone()}}}}")
        # held frame by frame (stepFrame, 0.1 s each, no render): the lesson clock runs on the frame time, not ff
        HOLD = """()=>{const K=window.__kgeu,S=window.__snap;for(let n=0;n<60&&K.LES.on;n++){const s=K.state();s.pos.y=S.y;s.vel.copy(S.v);s.quat.copy(S.q);s.w.set(0,0,0);K.stepFrame(0.1,false,true);}return !!K.LES.on}"""
        for _ in range(12):
            if not await pg.evaluate(HOLD): break
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)"); await pg.wait_for_timeout(500)
        d = await pg.evaluate("""()=>({on:document.getElementById('gradeOv').classList.contains('on'),
          rows:[...document.querySelectorAll('#gLines .gt')].map(r=>[r.querySelector('span').textContent,r.querySelector('b').textContent]),
          tag:(document.querySelector('#gScore .ezTag')||{}).textContent,letter:document.getElementById('gLetter').textContent,score:document.getElementById('gScore').textContent})""")
        names = [x[0] for x in d['rows']]
        ok('(c) the debrief: a row per task in order with a detail, then the quiz', d['on'] and names == ['Altitude within 100 ft', 'Airspeed on target', 'Heading within 10 degrees', 'No stall', 'Quiz']
           and all(x[1] for x in d['rows'] if x[0] not in ('No stall',)) and d['rows'][-1][1] == 'Right first time', d)
        ok('(c) Easy on: the EASY TOLERANCES, x2 tag beside the score', d['tag'] == 'EASY TOLERANCES, x2', d)
        ok('(c) Easy on marks the run Easy', await pg.evaluate(f"()=>{K}.runMode()") == 'easy')
        bad = await pg.evaluate(FIT, '#gradeOv')
        sc = await pg.evaluate("()=>{const b=document.getElementById('gLines');return b.scrollHeight>b.clientHeight+1}")
        ok('(c) 844x390: the debrief fits without scrolling, 44 px buttons', not bad and not sc, (bad, sc))
        sc6 = await pg.evaluate("()=>{const b=document.getElementById('gLines'),r=b.querySelector('.gt');b.insertBefore(r.cloneNode(true),r);const s=b.scrollHeight>b.clientHeight+1;b.removeChild(b.querySelector('.gt'));return s}")
        ok('(c) 844x390: five tasks and the quiz fit without scrolling', not sc6)
        await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400)
        bad = await pg.evaluate(FIT, '#gradeOv')
        ok('(c) 568x320: the debrief fits (the lines may scroll), 44 px buttons', not bad, bad)
        ok('(e) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (d) the chips: unset follows the game mode, persists, locked during a lesson
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuOnboard='rookie'))
        CH = "()=>({ls:localStorage.getItem('kgeuSchoolEasy'),sel:[...document.querySelectorAll('[data-ez]')].filter(b=>b.getAttribute('aria-checked')==='true').map(b=>b.dataset.ez),dis:[...document.querySelectorAll('[data-ez]')].map(b=>b.disabled),hint:document.getElementById('ezHint').textContent,h:[...document.querySelectorAll('[data-ez]')].map(b=>b.getBoundingClientRect().height)})"
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CH)
        ok('(d) unset: an Easy player starts on Easy, saved', c['ls'] == '1' and c['sel'] == ['1'] and c['hint'] == 'Every tolerance doubled, for new pilots' and min(c['h']) >= 44, c)
        await pg.evaluate("()=>document.querySelector('[data-ez=\"0\"]').click()"); await pg.wait_for_timeout(100)
        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await pg.wait_for_timeout(1500)
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
        c = await pg.evaluate(CH)
        ok('(d) Standard persists across a reload', c['ls'] == '0' and c['sel'] == ['0'] and c['hint'] == 'Private ACS tolerances' and c['dis'] == [False, False], c)
        await pg.evaluate(f"()=>{{{K}.startLesson('slow');{K}.lesBriefSkip()}}"); await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(200)
        await pg.evaluate("()=>document.getElementById('pSch').click()"); await pg.wait_for_timeout(300)   # the school screen from the pause sheet
        c = await pg.evaluate(CH)
        await pg.evaluate("()=>document.querySelector('[data-ez=\"1\"]').click()")
        c2 = await pg.evaluate(CH)
        ok('(d) during a lesson the chips are disabled with Set before a lesson', c['dis'] == [True, True] and c['hint'] == 'Set before a lesson' and c2['ls'] == '0', (c, c2))
        ok('(e) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (f) the stall lesson: the power off stall, its recovery, then the power on stall and its recovery
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuSchoolEasy='0'))
        # (f) slow flight's speed band: +10/-0 kt around 55 (Standard), +20/-5 (Easy), on a held slow flight
        await held(pg)
        for ez, exp in ((False, [10, 0, 'out', 'in', 'out']), (True, [20, 5, 'in', 'in', 'near'])):
            await pg.evaluate(f"(e)=>{K}.ezSet(e,true)", ez)
            r = await pg.evaluate(BAND)
            ok(f'(f) {"Easy" if ez else "Standard"}: hi {exp[0]}, lo {exp[1]}; 54 kt {exp[2]}, 64 in, 48 {exp[4]}', r['hl'] == exp[:2] and r['b'] == exp[2:], r)
            if not ez:
                ok('(f) the band is drawn off centre (50% to 66.67%), the symmetric ALT row is not', r['bg'] and ' 50%' in r['bg'] and '66.67%' in r['bg'] and not r['bgAlt'], r)
                ok('(f) 54 kt counts as out of tolerance in the grading too', r['tIn'] == 0 and r['tAll'] > 0, r)
        await pg.evaluate(f"()=>{K}.ezSet(false,true)")
        await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('stall');K.lesBriefSkip()}}"); await pg.wait_for_timeout(200)
        P = []
        for o in ({'kt': 48, 'p': 0.5, 'thr': 0, 'u': 'K.LES.ph===1'}, {'kt': 60, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===2'}, {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1, 'u': 'K.LES.ph===3'},
                  {'kt': 58, 'p': 0.1, 'vy': 0, 'thr': 0.4, 'n': 20}, {'kt': 52, 'p': 0.55, 'thr': 1, 'u': 'K.LES.ph===4'}, {'kt': 62, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===5'},
                  {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1, 'u': '!K.LES.on'}):
            P.append(await pg.evaluate(STALL, o))
        await pg.wait_for_timeout(600)
        d = await pg.evaluate("""()=>({rows:[...document.querySelectorAll('#gLines .gt')].map(r=>[r.querySelector('span').textContent,r.classList.contains('ok')]),letter:document.getElementById('gLetter').textContent,
          dana:window.__kgeu.radioLog().filter(l=>l.who==='Dana').map(l=>l.text)})""")
        ok('(f) the stall lesson reaches every phase: stall, recover, climb, the power on stall, recover, climb', [x['ph'] for x in P] == [1, 2, 3, 3, 4, 5, None], P)
        ok('(f) the debrief: both stalls, seven rows, all passed', [x[0] for x in d['rows']] == ['Altitude lost under 150 ft', 'Full power within 2 s', 'Wings within 20 degrees', 'No secondary stall',
           'Power on: lost under 150 ft', 'Power on: wings within 20 degrees', 'Power on: no secondary stall'] and all(x[1] for x in d['rows']) and d['letter'] in 'AB', d)
        ok('(f) Dana: two stalls, the power on stall, its recovery', any(t.startswith('Two stalls') for t in d['dana']) and any('Now the power on stall' in t for t in d['dana'])
           and any('The power is already in' in t for t in d['dana']), d['dana'])
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_grade_check'))
asyncio.run(main())
