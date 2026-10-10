# School1 item 8: the logbook. (a) logbookAdd through window.__kgeu: the solo credits 0.5 dual, 0.5 solo, 3 landings and
# one entry; an F credits nothing but is an entry; totals keep counting past the 60 entry cap; (b) a real finish: slow
# flight flown to the debrief credits 1.0 dual and the entry has the score; (c) the screen: Logbook in the school header,
# the summary line, six rings with their captions, the disclaimer in view without scrolling at 844x390 and 568x320, the
# endorsement row, the prior hours line, back to #sSchool, 44 px buttons, nothing off screen; (d) no page errors.
# Run: .venv/bin/python tests/school_log_check.py
import asyncio, json, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuPlace': '{"level":"ride","hours":null}'}
CAPS = ['TOTAL of 40', 'DUAL of 20', 'SOLO of 10', 'NIGHT of 3', 'INSTRUMENT of 3', 'CROSS COUNTRY of 3']
NOTE = 'Practice log. Not creditable toward FAA requirements.'
# the screen: nothing off screen outside the entries list, 44 px buttons, the screen itself does not scroll, the disclaimer in view
FIT = """()=>{const s=document.getElementById('sLog'),W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('scrolls');
  s.querySelectorAll('*').forEach(e=>{if(e.closest('#logList'))return;const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+(e.id||e.className.baseVal||e.className||e.tagName));});
  document.querySelectorAll('#sLog button,#mBack').forEach(e=>{const r=e.getBoundingClientRect();if(r.width&&(r.width<43.5||r.height<43.5))bad.push('small '+(e.id||e.textContent));});
  const n=s.querySelector('.logNote'),r=n.getBoundingClientRect(),cs=getComputedStyle(n);
  if(!(r.height>0&&r.bottom<=H+0.5&&r.top>=0)||cs.visibility!=='visible')bad.push('note hidden');
  if(cs.fontSize!=='12px')bad.push('note '+cs.fontSize);
  const R=[...s.querySelectorAll('.lRing .lr')].map(e=>e.getBoundingClientRect());if(R.some(q=>q.width<63.5))bad.push('ring under 64');
  const L=document.getElementById('logList');if(getComputedStyle(L).overscrollBehaviorY!=='contain')bad.push('list overscroll');
  return bad;}"""
SCR = """()=>({rings:[...document.querySelectorAll('#logRings .lRing')].map(r=>[r.querySelector('.lr b').textContent,r.querySelector('.lc').textContent,r.classList.contains('full')]),
  note:document.querySelector('#sLog .logNote').textContent,ldg:document.getElementById('logLdg').textContent,
  end:[...document.querySelectorAll('#logEnd p')].map(p=>p.textContent),prior:document.getElementById('logPrior').hidden?null:document.getElementById('logPrior').textContent,
  rows:[...document.querySelectorAll('#logList .lE')].map(e=>[e.querySelector('.n b').textContent,[...e.querySelectorAll('.n i')].map(i=>i.textContent),e.querySelector('.lg').textContent])})"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # (a) the arithmetic
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=BASE)
        r = await pg.evaluate(f"()=>{{const K={K};const e=K.logbookAdd('solo',{{letter:'B'}});const L=K.LOGB;return {{e:e,t:[L.dual,L.solo,L.xc,L.night,L.inst,L.ldg],n:L.entries.length,s:JSON.parse(localStorage.getItem('kgeuLogbook'))}}}}")
        ok('(a) the solo, a B: 0.5 dual, 0.5 solo, 3 landings, one entry', r['t'] == [0.5, 0.5, 0, 0, 0, 3] and r['n'] == 1 and r['e']['letter'] == 'B' and r['e']['dual'] == 0.5 and r['e']['solo'] == 0.5 and r['e']['ldg'] == 3, r)
        ok('(a) saved in kgeuLogbook', r['s']['dual'] == 0.5 and r['s']['ldg'] == 3 and len(r['s']['entries']) == 1, r['s'])
        r = await pg.evaluate(f"()=>{{const K={K};const e=K.logbookAdd('hood',{{letter:'F',score:40}});const L=K.LOGB;return {{e:e,t:[L.dual,L.solo,L.inst,L.ldg],n:L.entries.length}}}}")
        ok('(a) an F credits nothing but is an entry with its letter', r['t'] == [0.5, 0.5, 0, 3] and r['n'] == 2 and r['e']['letter'] == 'F' and r['e']['dual'] == 0 and r['e']['inst'] == 0 and r['e']['score'] == 40, r)
        r = await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<65;i++)K.logbookAdd('hood',{{letter:'C',score:72}});const L=K.LOGB;return {{t:[L.dual,L.solo,L.inst,L.ldg],n:L.entries.length,last:L.entries[59].id,first:L.entries[0].letter,sum:K.logSummary()}}}}")
        ok('(a) 65 more passes: totals keep counting (65.5 dual, 65 inst), the list keeps the last 60', r['t'] == [65.5, 0.5, 65, 3] and r['n'] == 60 and r['first'] == 'C', r)
        ok('(a) the summary line', r['sum'] == '66.0 h logged, 3 landings', r['sum'])
        await pg.context.close()

        # (b) a real finish: slow flight held on its numbers to the debrief (the forcing from school_grade_check)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuSchoolEasy='1'))
        await pg.evaluate(f"()=>{{{K}.startLesson('slow');{K}.lesBriefAnswer(0);{K}.lesBriefSkip()}}"); await pg.wait_for_timeout(300)
        ph = await pg.evaluate(f"()=>{{const K={K};for(let n=0;n<400&&K.LES.ph!==1;n++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);return K.LES.ph===1}}")
        await pg.evaluate(f"()=>{{const s={K}.state();window.__snap={{y:s.pos.y,v:s.vel.clone(),q:s.quat.clone()}}}}")
        HOLD = """()=>{const K=window.__kgeu,S=window.__snap;for(let n=0;n<60&&K.LES.on;n++){const s=K.state();s.pos.y=S.y;s.vel.copy(S.v);s.quat.copy(S.q);s.w.set(0,0,0);K.stepFrame(0.1,false,true);}return !!K.LES.on}"""
        for _ in range(12):
            if not await pg.evaluate(HOLD): break
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)"); await pg.wait_for_timeout(300)
        r = await pg.evaluate(f"()=>{{const L={K}.LOGB,e=L.entries[L.entries.length-1];return {{on:document.getElementById('gradeOv').classList.contains('on'),dual:L.dual,n:L.entries.length,e:e,score:{K}.G.res&&{K}.G.res.score,letter:document.getElementById('gLetter').textContent}}}}")
        ok('(b) slow flight flown to the debrief', ph and r['on'], r)
        ok('(b) it credits 1.0 dual and the entry has the score and the letter', r['dual'] == 1.0 and r['n'] == 1 and r['e']['id'] == 'slow' and r['e']['score'] == r['score'] and r['e']['letter'] == r['letter'] and r['letter'] != 'F', r)
        ok('(d) no page errors (b)', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (c) the screen, empty then seeded
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=BASE)
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
        r = await pg.evaluate("()=>{const b=document.getElementById('schLog').getBoundingClientRect();return {sum:document.getElementById('schSum').textContent,h:b.height,w:b.width,t:document.getElementById('schLog').textContent}}")
        ok('(c) the school header: the summary line and a 44 px Logbook button', r['sum'] == '0.0 h logged, 0 landings' and r['h'] >= 43.5 and r['w'] >= 43.5 and r['t'] == 'Logbook', r)
        await finger(pg, '#schLog'); await pg.wait_for_timeout(800)
        r = await pg.evaluate(SCR)
        ok('(c) Logbook opens #sLog', await pg.evaluate(f"()=>{K}.curScr()") == 'sLog')
        ok('(c) six rings with the right captions, empty', [x[1] for x in r['rings']] == CAPS and all(x[0] == '0.0' and not x[2] for x in r['rings']), r['rings'])
        ok('(c) the disclaimer, None yet, no prior hours line, no entries', r['note'] == NOTE and r['end'] == ['None yet'] and r['prior'] is None and r['rows'] == [], r)
        await finger(pg, '#mBack'); await pg.wait_for_timeout(400)
        ok('(c) the back button returns to #sSchool', await pg.evaluate(f"()=>{K}.curScr()") == 'sSchool')
        # seeded: the endorsement, prior hours, a pass and an F; then the fit at both sizes
        await pg.evaluate(f"""()=>{{const K={K};localStorage.setItem('kgeuEndorse',JSON.stringify({{solo:{{at:Date.UTC(2026,9,9,18),by:'Dana Reyes, CFI',lesson:'solo'}}}}));K.setPlace('solo',35);
          K.logbookAdd('solo',{{letter:'A',score:93}});K.logbookAdd('slow',{{letter:'F',score:41}});for(let i=0;i<20;i++)K.logbookAdd('first',{{letter:'B',score:80}});K.openMenu('sSchool')}}""")
        await pg.wait_for_timeout(300)
        ok('(c) the summary updates', await pg.evaluate("()=>document.getElementById('schSum').textContent") == '11.0 h logged, 23 landings, 1 endorsement')
        await finger(pg, '#schLog'); await pg.wait_for_timeout(800)
        r = await pg.evaluate(SCR)
        ok('(c) the rings: total 11.0, dual 10.5, solo 0.5', [x[0] for x in r['rings']] == ['11.0', '10.5', '0.5', '0.0', '0.0', '0.0'], r['rings'])
        ok('(c) the endorsement row', r['end'] == ['Solo endorsement, signed by Dana Reyes, CFI, Oct 9, 2026'], r['end'])
        ok('(c) the prior hours line', r['prior'] == 'Prior hours (your entry): 35', r['prior'])
        ok('(c) entries newest first, the F with 0.0 h, the solo with its tags', len(r['rows']) == 22 and r['rows'][0][0] == 'First flight' and r['rows'][20] == ['Slow flight', ['0.0 h'], 'F']
           and r['rows'][21] == ['Stage check and first solo', ['0.5 dual', '0.5 solo', '3 landings'], 'A'], r['rows'][19:])
        off = await pg.evaluate("()=>[...document.querySelectorAll('#logRings .fg')].map(c=>getComputedStyle(c).transitionDuration)")
        ok('(c) the rings fill with a 600 ms transition', off == ['0.6s'] * 6, off)
        for W, H in ((844, 390), (568, 320)):
            await pg.set_viewport_size({'width': W, 'height': H}); await pg.wait_for_timeout(400)
            bad = await pg.evaluate(FIT)
            ok(f'(c) {W}x{H}: the disclaimer in view without scrolling, rings 64 px or more, nothing off screen, 44 px buttons', not bad, bad)
            sc = await pg.evaluate("()=>{const L=document.getElementById('logList');return L.scrollHeight>L.clientHeight}")
            ok(f'(c) {W}x{H}: the entries list scrolls inside', sc)
        # a full ring turns green
        await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<30;i++)K.logbookAdd('hood',{{letter:'B',score:85}});K.nav('sSchool',true);K.nav('sLog')}}"); await pg.wait_for_timeout(800)
        r = await pg.evaluate("()=>[...document.querySelectorAll('#logRings .lRing')].map(r=>[r.dataset.k,r.classList.contains('full'),getComputedStyle(r.querySelector('.fg')).stroke])")
        ok('(c) full rings (total, dual, instrument) are green, the rest rust', [x[1] for x in r] == [True, True, False, False, True, False] and r[0][2] == 'rgb(63, 143, 79)' and r[2][2] == 'rgb(168, 89, 42)', r)
        await finger(pg, '#mBack'); await pg.wait_for_timeout(400)
        ok('(c) back again returns to #sSchool', await pg.evaluate(f"()=>{K}.curScr()") == 'sSchool')
        ok('(d) no page errors (c)', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('school_log_check'))
asyncio.run(main())
