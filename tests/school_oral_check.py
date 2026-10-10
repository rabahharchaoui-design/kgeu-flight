# School2 item 5: Stage 4 lesson 1, the oral exam (15 questions from ORAL_Q, no flight).
# (a) the bank: 40+ questions, 6+ a topic, four distinct answers, ok in range, a why, a known topic; (b) with a 'ride'
# placement the Stage 4 node and the oral row by real taps: the sheet, Question 1 of 15, a topic chip, four 44 px answers,
# Back; Back on question 1 leaves without a result; oralSeed makes the draw repeatable; (c) every answer right: green,
# the explanation, NEXT, no Back from question 2; the card reads A, 15 of 15, six topic rows, no misses, the pass tip;
# RETRY draws new questions; FLIGHT SCHOOL closes onto the school screen; (d) a fresh run 10 right then 5 wrong: F, five
# Missed rows, the fail tip, not passed; RETRY with 11 right: C, passed, the logbook entry reads 11 of 15 with no time;
# (e) 568x320: the longest question, answers and explanation fit, 44 px targets; (f) no page errors.
# Run: .venv/bin/python tests/school_oral_check.py
import asyncio, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, PLACED, IPHONE_15
ok = Checks()
K = "window.__kgeu"
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchoolEasy': '0', 'kgeuTOD': 'day'}
TOPICS = ['airspace', 'weather', 'regs', 'aeromed', 'systems', 'perf']
SHEET = f"""()=>{{const o=document.getElementById('orOv');return {{on:o.classList.contains('on')&&!o.classList.contains('out'),n:document.getElementById('orN').textContent,
  chip:document.getElementById('orChip').textContent,ans:[...document.querySelectorAll('#orA .orAns')].map(b=>{{const r=b.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]}}),
  back:!document.getElementById('orBack').hidden,next:document.getElementById('orNext').textContent,dis:document.getElementById('orNext').disabled,
  why:!document.getElementById('orWhy').hidden}}}}"""
IDLE = "()=>{const o=document.getElementById('orOv');return o.getAnimations({subtree:true}).every(a=>a.playState==='finished')}"
FIT = """()=>{const s=document.querySelector('#orOv .sheet'),W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('sheet scrolls '+s.scrollHeight+'>'+s.clientHeight);
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});
  return bad;}"""
CARD = """()=>{const o=document.getElementById('gradeOv');return {on:o.classList.contains('on'),letter:document.getElementById('gLetter').textContent,
  score:document.getElementById('gScore').textContent,topics:[...o.querySelectorAll('.rLines .gt')].map(r=>[r.firstChild.textContent,r.lastChild.textContent,r.classList.contains('ok')]),
  missed:[...o.querySelectorAll('.rLines .orMs')].map(r=>[r.firstChild.textContent,r.lastChild.textContent]),mh:!!o.querySelector('.orMh'),
  tip:(o.querySelector('.rTip')||{}).textContent,retry:document.getElementById('gRetry').textContent,free:!document.getElementById('gFree').hidden,
  sch:document.getElementById('gSchool').textContent}}"""

async def answer_all(pg, right):
    """answer the 15 by real taps: the first `right` right, the rest wrong; returns the first answered state"""
    first = None
    for i in range(15):
        q = await pg.evaluate(f"(i)=>{{const Q={K}.ORAL[i];return {{ok:Q.ok,n:document.getElementById('orN').textContent}}}}", i)
        k = q['ok'] if i < right else (q['ok'] + 1) % 4
        await finger(pg, f'#orA .orAns:nth-child({k + 1})'); await pg.wait_for_timeout(120)
        if i == 0:
            first = await pg.evaluate(SHEET)
            first['cls'] = await pg.evaluate("()=>[...document.querySelectorAll('#orA .orAns')].map(b=>b.className.replace('orAns','').trim())")
            first['k'] = k
        if i == 1:
            first['back2'] = (await pg.evaluate(SHEET))['back']
        await finger(pg, '#orNext'); await pg.wait_for_timeout(120)
    await pg.wait_for_timeout(300)
    return first

async def school_s4(pg):
    await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(200)
    await finger(pg, '#hSch'); await pg.wait_for_timeout(400)
    await finger(pg, '.sNode[data-st=s4]'); await pg.wait_for_timeout(400)

async def open_oral(pg):
    await finger(pg, '#school .lrow[data-l=oral]'); await pg.wait_for_timeout(300)
    await pg.wait_for_function(IDLE, timeout=8000)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        # (a) the bank
        bank = await pg.evaluate(f"()=>{K}.ORAL_Q")
        bad = [q['q'][:40] for q in bank if len(q['a']) != 4 or len(set(q['a'])) != 4 or not (0 <= q['ok'] < 4) or not q.get('why') or q['t'] not in TOPICS or not q['q']]
        per = {t: sum(1 for q in bank if q['t'] == t) for t in TOPICS}
        ok('(a) the bank: every question has 4 distinct answers, ok in range, a why, a known topic', not bad, bad)
        ok('(a) at least 40 questions, at least 6 a topic', len(bank) >= 40 and all(v >= 6 for v in per.values()), (len(bank), per))
        ok('(a) every why is two sentences at most', all(q['why'].count('. ') <= 1 for q in bank), [q['q'][:30] for q in bank if q['why'].count('. ') > 1])

        # (b) the school screen: Stage 4 by a real tap
        await school_s4(pg)
        node = await pg.evaluate("()=>{const n=document.querySelector('.sNode[data-st=s4]');return [n.className,n.textContent]}")
        ok('(b) the Stage 4 node reads Checkride prep, no Coming soon', 'soon' not in node[0] and 'Checkride prep' in node[1] and 'Coming soon' not in node[1], node)
        rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.classList.contains('soon'),r.textContent.includes('START')])")
        ok('(b) Stage 4: Oral exam a START row, Mock checkride a Coming soon row', rows == [['oral', False, True], ['ride', True, False]], rows)
        prog = await pg.evaluate("()=>document.getElementById('schProg').textContent")
        ok('(b) the progress counts the oral: 0 of 20 passed', prog == '0 of 20 passed', prog)
        await pg.evaluate(f"()=>{K}.oralSeed(1)")
        await open_oral(pg)
        s = await pg.evaluate(SHEET)
        ok('(b) the row opens the exam: Question 1 of 15, a topic chip, four 44 px answers, Back, ANSWER FIRST disabled',
           s['on'] and s['n'] == 'Question 1 of 15' and s['chip'] in ('AIRSPACE', 'WEATHER', 'REGULATIONS', 'AEROMEDICAL', 'SYSTEMS', 'PERFORMANCE')
           and len(s['ans']) == 4 and all(w >= 44 and h >= 44 for w, h in s['ans']) and s['back'] and s['next'] == 'ANSWER FIRST' and s['dis'], s)
        ok('(b) the menu stays on the school screen under it, nothing flying', await pg.evaluate(f"()=>[{K}.curScr(),{K}.LES.on]") == ['sSchool', None])
        bad = await pg.evaluate(FIT)
        ok('(e) 844x390 the question fits, 44 px targets, the sheet does not scroll', not bad, bad)
        d1 = await pg.evaluate(f"()=>{K}.ORAL.map(q=>q.q)")
        tc = await pg.evaluate(f"()=>{{const c={{}};{K}.ORAL.forEach(q=>c[q.t]=(c[q.t]||0)+1);return c}}")
        ok('(b) 15 questions, no repeats, at least two of each topic', len(d1) == 15 and len(set(d1)) == 15 and all(tc.get(t, 0) >= 2 for t in TOPICS), tc)
        await finger(pg, '#orBack'); await pg.wait_for_timeout(400)
        st = await pg.evaluate(f"()=>({{ov:document.getElementById('orOv').classList.contains('on'),card:document.getElementById('gradeOv').classList.contains('on'),g:{K}.lessonOpen('oral')&&JSON.parse(localStorage.getItem('kgeuSchool')||'{{}}')['cessna:oral']||null,log:{K}.LOGB.entries.length,scr:{K}.curScr()}})")
        ok('(b) Back on question 1 leaves without a result', st == {'ov': False, 'card': False, 'g': None, 'log': 0, 'scr': 'sSchool'}, st)
        await pg.evaluate(f"()=>{K}.oralSeed(1)")
        await open_oral(pg)
        d2 = await pg.evaluate(f"()=>{K}.ORAL.map(q=>q.q)")
        ok('(b) oralSeed(1) again draws the same 15', d1 == d2)

        # (c) all right
        f = await answer_all(pg, 15)
        ok('(c) a right answer turns green, the others lock, the explanation shows, NEXT', f['cls'][f['k']] == 'right' and all(c == '' for j, c in enumerate(f['cls']) if j != f['k'])
           and f['why'] and f['next'] == 'NEXT' and not f['dis'], f)
        ok('(c) no Back from question 2', f['back2'] is False, f)
        c = await pg.evaluate(CARD)
        ok('(c) the card: A, 15 of 15', c['on'] and c['letter'] == 'A' and c['score'].startswith('15 of 15'), c)
        ok('(c) six topic rows, all green', len(c['topics']) == 6 and all(t[2] for t in c['topics']) and [t[0] for t in c['topics']] == ['AIRSPACE', 'WEATHER', 'REGULATIONS', 'AEROMEDICAL', 'SYSTEMS', 'PERFORMANCE'], c['topics'])
        ok('(c) no Missed list, the pass tip, RETRY ORAL EXAM, no free flight, FLIGHT SCHOOL', not c['missed'] and not c['mh'] and c['tip'].startswith('You know the material.')
           and c['retry'] == 'RETRY ORAL EXAM' and not c['free'] and c['sch'] == 'FLIGHT SCHOOL', c)
        g = await pg.evaluate(f"()=>[JSON.parse(localStorage.getItem('kgeuSchool'))['cessna:oral'],{K}.lessonOpen('oral'),{K}.LOGB.entries.slice(-1)[0]]")
        ok('(c) schoolBest cessna:oral A, the logbook entry has no time', g[0] == 'A' and g[2]['id'] == 'oral' and g[2]['right'] == 15 and g[2]['of'] == 15
           and all(g[2][k] == 0 for k in ('dual', 'solo', 'xc', 'night', 'inst', 'ldg')), g)
        await finger(pg, '#gRetry'); await pg.wait_for_timeout(300); await pg.wait_for_function(IDLE, timeout=8000)
        s = await pg.evaluate(SHEET); d3 = await pg.evaluate(f"()=>{K}.ORAL.map(q=>q.q)")
        ok('(c) RETRY: a new draw, Question 1 of 15, the card closed', s['on'] and s['n'] == 'Question 1 of 15' and d3 != d1
           and not await pg.evaluate("()=>document.getElementById('gradeOv').classList.contains('on')"), s)
        await finger(pg, '#orBack'); await pg.wait_for_timeout(400)
        await open_oral(pg); await answer_all(pg, 15)
        await finger(pg, '#gSchool'); await pg.wait_for_timeout(400)
        r = await pg.evaluate(f"()=>({{card:document.getElementById('gradeOv').classList.contains('on'),scr:{K}.curScr(),menu:document.getElementById('menu').classList.contains('on'),done:document.querySelector('#school .lrow[data-l=oral]').classList.contains('done'),prog:document.getElementById('schProg').textContent}})")
        ok('(c) FLIGHT SCHOOL closes onto the school screen, the oral row done, 1 of 20', r == {'card': False, 'scr': 'sSchool', 'menu': True, 'done': True, 'prog': '1 of 20 passed'}, r)
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (d) 10 right then 5 wrong, then 11 right
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await school_s4(pg); await pg.evaluate(f"()=>{K}.oralSeed(7)"); await open_oral(pg)
        await answer_all(pg, 10)
        c = await pg.evaluate(CARD)
        ok('(d) 10 of 15: F (under 70)', c['on'] and c['letter'] == 'F' and c['score'].startswith('10 of 15'), c)
        ok('(d) the Missed list has 5 rows, each with its right answer', c['mh'] and len(c['missed']) == 5 and all(m[0] and m[1] for m in c['missed']), c['missed'])
        ok('(d) some topic row red, the fail tip', any(not t[2] for t in c['topics']) and c['tip'].startswith('Not yet.'), c)
        ok('(d) not passed', await pg.evaluate(f"()=>{K}.lessonDef('oral')&&!JSON.parse(localStorage.getItem('kgeuSchool'))['cessna:oral'].match(/[ABC]/)"))
        clamp = await pg.evaluate("()=>{const s=document.querySelector('#gradeOv .orMs span'),lh=parseFloat(getComputedStyle(s).lineHeight);return s.getBoundingClientRect().height/lh}")
        ok('(d) a missed question is two lines at most', clamp <= 2.05, clamp)
        await finger(pg, '#gRetry'); await pg.wait_for_timeout(300); await pg.wait_for_function(IDLE, timeout=8000)
        await answer_all(pg, 11)
        c = await pg.evaluate(CARD)
        ok('(d) 11 of 15: C, passed', c['letter'] == 'C' and c['score'].startswith('11 of 15') and len(c['missed']) == 4, c)
        g = await pg.evaluate(f"()=>[JSON.parse(localStorage.getItem('kgeuSchool'))['cessna:oral'],{K}.LOGB.entries.slice(-1)[0],{K}.LOGB.entries.length]")
        ok("(d) lessonDone: the best letter is C", g[0] == 'C', g)
        ok('(d) the logbook: two entries, the last 11 of 15, C, no time', g[2] == 2 and g[1]['right'] == 11 and g[1]['of'] == 15 and g[1]['letter'] == 'C' and g[1]['dual'] == 0, g)
        await finger(pg, '#gSchool'); await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{K}.nav('sLog')"); await pg.wait_for_timeout(300)
        le = await pg.evaluate("()=>{const e=document.querySelector('#logList .lE');return e&&[e.querySelector('.n b').textContent,e.querySelector('.n span').textContent,e.querySelector('.lg').textContent]}")
        ok('(d) the logbook row: Oral exam, 11 of 15, C', le == ['Oral exam', '11 of 15', 'C'], le)
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (e) 568x320: the worst case question, answers and explanation
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage=dict(BASE, **PLACED))
        await school_s4(pg); await open_oral(pg)
        bads = [f'q1: {x}' for x in await pg.evaluate(FIT)]
        worst = await pg.evaluate(f"""()=>{{const B={K}.ORAL_Q,by=f=>B.reduce((a,q)=>f(q)>f(a)?q:a);
          return [by(q=>q.why.length),by(q=>Math.max(...q.a.map(s=>s.length))),by(q=>q.q.length),by(q=>q.a.join('').length)]}}""")
        for i, w in enumerate(worst):
            await pg.evaluate(f"([i,w])=>{{const D={K}.ORAL;D[i+1]=Object.assign({{}},w,{{got:null}});}}", [i, w])
        await finger(pg, '#orA .orAns:nth-child(1)'); await pg.wait_for_timeout(120)
        bads += [f'q1 answered: {x}' for x in await pg.evaluate(FIT)]
        for i, w in enumerate(worst):
            await finger(pg, '#orNext'); await pg.wait_for_timeout(150)
            bads += [f'worst {i}: {x}' for x in await pg.evaluate(FIT)]
            await finger(pg, f"#orA .orAns:nth-child({(w['ok'] + 1) % 4 + 1})"); await pg.wait_for_timeout(150)
            bads += [f'worst {i} answered wrong: {x}' for x in await pg.evaluate(FIT)]
        ok('(e) 568x320 the longest why, answers and question fit: 44 px targets on screen, the sheet does not scroll', not bads, bads)
        await pg.screenshot(path='/tmp/oral_568.png')
        ok('(f) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('school_oral_check'))
asyncio.run(main())
