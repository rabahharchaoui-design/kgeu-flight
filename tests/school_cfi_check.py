# School1 item 5: the instructor, Dana Reyes, CFI.
# (a) slow flight (briefing skipped): the opening line is Dana's in RADIO.log and the subtitle reads Dana; (b) a correction
# cue: 250 ft high for 5 s gives one Dana line about being high, and no second one within 12 s; (c) the debrief tip is
# hers (a full stop, a task named on B to D); (d) a passed solo run: kgeuEndorse.solo saved, the Endorsement row, the
# offAir line says endorsement; (e) the pattern: CALL on the ground within 3 s, no clearance before it, the tap sends our
# request then the tower's takeoff clearance with closed traffic; (f) no page errors; (g) no voices: nothing throws.
# Run: .venv/bin/python tests/school_cfi_check.py
import asyncio, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, PLACED, IPHONE_15
ok = Checks()
K = "window.__kgeu"
BASE = dict({'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchoolEasy': '0'}, **PLACED)
CUES = r"/feet (high|low)|knots (fast|slow)|degrees (left|right|steep|shallow)|centerline/"

async def to_ph1(pg):   # the lesson clock runs on the frame time: step frames, not ff
    return await pg.evaluate(f"()=>{{const K={K};for(let n=0;n<400&&K.LES.ph!==1;n++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);return K.LES.ph===1}}")

# n frames of 0.1 s with the plane pinned (attitude, velocity) at the snapshot, dft feet above 3,500
PIN = """([n,dft])=>{const K=window.__kgeu,S=window.__snap;for(let i=0;i<n&&K.LES.on;i++){const s=K.state();
  s.pos.y=S.y+dft/3.28084;s.vel.copy(S.v);s.vel.y=0;s.quat.copy(S.q);s.w.set(0,0,0);K.stepFrame(0.1,false,true);}K.stepFrame(0,true);
  return K.radioLog().filter(l=>l.who==='Dana'&&%s.test(l.text)).map(l=>[l.t,l.text]);}""" % CUES

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # (a) and (b): slow flight
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(f"()=>{{{K}.radioLog(true);{K}.startLesson('slow');{K}.lesBriefSkip()}}"); await pg.wait_for_timeout(900)
        r = await pg.evaluate(f"()=>{{const l={K}.radioLog().find(l=>/^Slow flight/.test(l.text));const b=document.querySelector('#atc b');return {{who:l&&l.who,text:l&&l.text,atc:b&&b.textContent}}}}")
        ok('(a) the opening line is Dana\'s in RADIO.log', r['who'] == 'Dana', r)
        ok('(a) the subtitle reads Dana in bold', r['atc'] == 'Dana', r)
        ok('(a) her line has no exclamation mark', r['text'] and '!' not in r['text'], r)
        sp = await pg.evaluate(f"()=>{K}.cfiSp('Hold 3,500 at 74 kt, 2,100 ft, 45\\u00b0.')")
        ok('(a) her speech says the numbers as a CFI does', sp == 'Hold thirty-five hundred at seventy-four knots, twenty-one hundred feet, forty-five degrees.', sp)
        ok('(b) slow flight reaches the hold', await to_ph1(pg))
        await pg.evaluate(f"""()=>{{const K={K},s=K.state(),T=K.G.tasks;window.__snap={{y:s.pos.y+(3500-K.G.alt)/3.28084,v:s.vel.clone(),q:s.quat.clone()}};
          T.spd.get=()=>typeof T.spd.target==='function'?T.spd.target():T.spd.target;T.hdg.get=()=>360;K.radioLog(true);}}""")
        c0 = await pg.evaluate(PIN, [35, 0])
        ok('(b) on altitude for 3.5 s: no correction', not c0, c0)
        c1 = await pg.evaluate(PIN, [50, 250])
        ok('(b) 250 ft high for 5 s: Dana says one line about being high', len(c1) == 1 and 'high' in c1[0][1], c1)
        c2 = await pg.evaluate(PIN, [105, 250])
        ok('(b) still high: no second correction within 12 s', len(c2) == 1, c2)
        c3 = await pg.evaluate(PIN, [40, 250])
        ok('(b) after 12 s she corrects again', len(c3) == 2 and c3[1][0] - c3[0][0] >= 11.9, c3)
        cue = await pg.evaluate(f"()=>[{K}.cfiCue('alt',154),{K}.cfiCue('spd',-6.4),{K}.cfiCue('hdg',-15.2),{K}.cfiCue('bank',-8)]")
        ok('(b) the cue strings, feet to tens, knots and degrees to units', cue == ['You are 150 feet high. Ease the power back a touch.', 'Nose down a little, you are 6 knots slow.',
           'Bring the heading back right, you are 15 degrees left.', 'A little more bank, you are 8 degrees shallow.'], cue)
        # (c) the debrief tip
        T = [{'ok': True, 'name': 'Altitude within 100 ft', 'pts': 30, 'w': 35}, {'ok': False, 'name': 'Airspeed on target', 'pts': 10, 'w': 35}, {'ok': True, 'name': 'No stall', 'pts': 10, 'w': 10}]
        tips = await pg.evaluate(f"(T)=>['A','B','C','D','F'].map(L=>{K}.dbTip({{letter:L,lines:T}})).concat([{K}.dbTip({{letter:'F',failWhy:'stalled',lines:[{{ok:false,why:true,name:'Stalled during slow flight'}}].concat(T)}})])", T)
        ok('(c) every tip ends with a full stop', all(t.endswith('.') for t in tips), tips)
        ok('(c) B to D name the lowest failed task', all('Airspeed on target' in t for t in tips[1:4]), tips[1:4])
        ok('(c) A: checkride standard, in her voice', tips[0] == 'That was checkride standard. I would sign that off any day.', tips[0])
        ok('(c) F with a reason: the reason, then set it up again', tips[5] == 'Stalled during slow flight. Let us set it up again.', tips[5])
        ok('(c) F otherwise names the task', tips[4].startswith('Not to standard today') and 'Airspeed on target' in tips[4], tips[4])
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (d) the solo endorsement: a solo run with every task passed
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(f"()=>{{{K}.startLesson('slow',true,{{brief:false}})}}"); await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{{if(!{K}.paused()){K}.togglePause();{K}.radioLog(true)}}"); await pg.wait_for_timeout(200)
        await pg.evaluate(f"""()=>{{const K={K};K.LES.on='solo';K.LES.name='Stage check and first solo';K.LES.quiz={{ok:false}};K.gBegin(K.lessonDef('solo'));
          K.gHold('dw',{{get:()=>2100,target:2100,grace:0}});for(let i=0;i<30;i++)K.gTick(0.1);K.gEvent('three',true);K.gRange('fpm',120);K.gRange('tdz',150);K.gRange('cl',1.5);K.gEnd();}}""")
        await pg.wait_for_timeout(800)
        d = await pg.evaluate(f"""()=>({{E:JSON.parse(localStorage.getItem('kgeuEndorse')||'null'),api:{K}.endorsements(),letter:document.getElementById('gLetter').textContent,
          row:[...document.querySelectorAll('#gLines .gl')].map(r=>[r.querySelector('span').textContent,r.querySelector('b').textContent]),
          said:{K}.radioLog().filter(l=>l.who==='Dana').map(l=>l.text)}})""")
        e = (d['E'] or {}).get('solo') or {}
        ok('(d) kgeuEndorse.solo saved, signed by Dana Reyes, CFI', e.get('by') == 'Dana Reyes, CFI' and e.get('lesson') == 'solo' and isinstance(e.get('at'), (int, float)) and e['at'] > 1e12, d['E'])
        ok('(d) endorsements() on window.__kgeu reads it', d['api'] == d['E'], d['api'])
        ok('(d) the card shows the Endorsement row', ['Endorsement', 'Solo, signed by Dana Reyes, CFI'] in d['row'], d['row'])
        ok('(d) the quiz row is hers', ['Quiz', 'We went over the answer'] in d['row'], d['row'])
        ok('(d) her debrief line mentions the endorsement', any('endorsement' in t for t in d['said']), d['said'])
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (e) the pattern: the CALL button and Glendale Tower
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(f"()=>{{{K}.radioLog(true);{K}.startLesson('pattern',true);{K}.lesBriefSkip()}}")
        on = False
        for _ in range(30):
            await pg.wait_for_timeout(100)
            on = await pg.evaluate("()=>{const e=document.getElementById('tkReply'),b=e.querySelector('button');return e.classList.contains('on')&&!!b&&b.textContent.startsWith('CALL')&&b.getBoundingClientRect().width>40}")
            if on: break
        g = await pg.evaluate(f"()=>{K}.state().onGround")
        ok('(e) the CALL button is up on the ground within 3 s', on and g, (on, g))
        pre = await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<30;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);return K.radioLog().filter(l=>/cleared for takeoff/i.test(l.text)).map(l=>l.text)}}")
        ok('(e) no clearance before the call', not pre, pre)
        await finger(pg, '#tkReply button'); await pg.wait_for_timeout(200)
        lg = await pg.evaluate(f"""()=>{{const K={K};for(let i=0;i<400;i++){{K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}}K.stepFrame(0,true);
          return K.radioLog().map(l=>[l.who,l.kind||'',l.text,l.clips]);}}""")
        pi = next((i for i, l in enumerate(lg) if l[1] == 'pilot' and l[2].startswith('Glendale Tower, Skyhawk')), None)
        ti = next((i for i, l in enumerate(lg) if l[1] == 'tower' and 'cleared for takeoff' in l[2] and 'closed traffic' in l[2]), None)
        ok('(e) the tap sends our request: Glendale Tower, Skyhawk ...', pi is not None and 'holding short runway 1, request closed traffic' in lg[pi][2], lg)
        ok('(e) then the tower clears us for takeoff with closed traffic', ti is not None and pi is not None and ti > pi, lg)
        if pi is not None and ti is not None:
            ok('(e) recorded clips: our request and the tower answer', lg[pi][3] == ['p_glendale_tower', 'p_cs_skyhawk', 'p_hold_closed'] and lg[ti][3][:2] == ['t_cs_skyhawk_s', 't_glendale_tower'] and 't_closed_traffic' in lg[ti][3], (lg[pi][3], lg[ti][3]))
        ri = next((i for i, l in enumerate(lg) if l[1] == 'pilot' and l[2].startswith('Cleared for takeoff, Skyhawk')), None)
        ok('(e) and we read the clearance back', ri is not None and ti is not None and ri > ti, lg)
        ok('(e) the button is gone after the tap', await pg.evaluate("()=>!document.getElementById('tkReply').classList.contains('on')"))
        tk = await pg.evaluate(f"()=>{K}.lessonDef('pattern').tasks.map(t=>[t.id,t.w])")
        ok('(e) pattern grades Made the tower calls, weight 10, the weights sum to 100', ['calls', 10] in tk and sum(x[1] for x in tk) == 100, tk)
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (g) a device with no voices: nothing throws
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate("()=>{if(window.speechSynthesis){speechSynthesis.getVoices=()=>[];}}")
        await pg.evaluate(f"()=>{{{K}.startLesson('slow',true,{{brief:false}})}}"); await pg.wait_for_timeout(300)
        v = await pg.evaluate(f"()=>{{const K={K};const v=K.cfiVoice();K.cfi('Hold 3,500. Small moves.');for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);return v}}")
        ok('(g) no voices: the default voice, no pick', v is None, v)
        pk = await pg.evaluate(f"()=>{{speechSynthesis.getVoices=()=>[{{name:'Alex',lang:'en-US'}},{{name:'Thomas',lang:'fr-FR'}},{{name:'Karen',lang:'en-AU'}}];const v={K}.cfiVoice();return v&&v.name}}")
        ok('(g) with voices: an English female voice is preferred', pk == 'Karen', pk)
        ok('(f) (g) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_cfi_check'))
asyncio.run(main())
