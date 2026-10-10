# School1 item 2: the flight school stage map and the placement intake.
# (a) first open shows the intake, CONTINUE waits for a pick, Soloed opens stages 1 and 2; (b) every level's open set;
# (c) Never flown is lesson by lesson; (d) locked rows and a locked stage; (e) Start from day one keeps grades;
# (f) Settings, Retake placement, with Back; (g) the screen and the intake fit at 844x390 and 568x320; (h) no errors.
# Run: .venv/bin/python tests/school_map_check.py
import asyncio, json, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
S1 = ['first', 'climbs', 'pattern', 'slow', 'stall', 'ground', 'landings', 'engine', 'solo']
S2 = ['steep', 'short', 'soft', 'xwind', 'emerg', 'hood']
# the FIT snippet from school_check, with the card grid allowed to scroll: its rows only need their size
FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('scrolls');
  s.querySelectorAll('button,input').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;const inGrid=!!e.closest('#school');
    if(!inGrid&&(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5))bad.push('off '+(e.textContent||e.id).trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+(e.textContent||e.id).trim().slice(0,14));});
  [...s.querySelectorAll('*')].forEach(e=>{if(e.closest('#school')||e.id==='school')return;if(e.scrollHeight>e.clientHeight+1&&/auto|scroll/.test(getComputedStyle(e).overflowY))bad.push('scrolls '+(e.id||e.className));});
  return bad;}"""
SAY = "()=>[document.getElementById('toast').textContent,document.getElementById('schMsg').textContent]"
OPEN = f"()=>{{const K={K};return {{l:{json.dumps(S1 + S2)}.filter(id=>K.lessonOpen(id)),s:['s1','s2','s3','s4'].filter(s=>K.stageOpen(s))}}}}"

IDLE = "()=>document.querySelector('#plOv .sheet').getAnimations().every(a=>a.playState==='finished')"

async def fit_map(pg, tag):
    for s in ('s1', 's2', 's3'):
        await pg.evaluate(f"(s)=>{K}.schSelect(s)", s); await pg.wait_for_timeout(250)
        bad = await pg.evaluate(FIT, '#sSchool')
        sc = await pg.evaluate("()=>{const L=document.getElementById('school'),r=L.getBoundingClientRect(),f=L.querySelector('.lrow').getBoundingClientRect();return {ov:getComputedStyle(L).overscrollBehaviorY,first:f.top>=r.top-0.5&&f.bottom<=Math.min(r.bottom,innerHeight)+0.5}}")
        ok(f'(g) {tag} stage {s[1]}: nothing off screen, 44 px targets, only the card grid scrolls, its first row in view', not bad and sc == {'ov': 'contain', 'first': True}, (bad, sc))

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # (a) the first visit: the intake, no way past it without a pick
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(200)
        await finger(pg, '#hSch'); await pg.wait_for_timeout(300); await pg.wait_for_function(IDLE, timeout=5000)
        st = await pg.evaluate("()=>({on:document.getElementById('plOv').classList.contains('on'),dis:document.getElementById('plGo').disabled,back:document.getElementById('plBack').hidden,n:document.querySelectorAll('#plOpts [role=radio]').length})")
        ok('(a) the school tab with no placement shows the intake: six options, CONTINUE disabled, no Back', st == {'on': True, 'dis': True, 'back': True, 'n': 6}, st)
        bad = await pg.evaluate(FIT, '#plOv .sheet')
        ok('(g) 844x390 the intake fits, 44 px targets', not bad, bad)
        await finger(pg, '#plGo'); await pg.wait_for_timeout(200)
        ok('(a) CONTINUE does nothing before a pick', await pg.evaluate("()=>document.getElementById('plOv').classList.contains('on')&&!localStorage.getItem('kgeuPlace')"))
        await finger(pg, '#plOpts [data-lv=solo]'); await pg.wait_for_timeout(100)
        st = await pg.evaluate("()=>({dis:document.getElementById('plGo').disabled,chk:[...document.querySelectorAll('#plOpts [aria-checked=true]')].map(e=>e.dataset.lv)})")
        ok('(a) picking Soloed checks it and enables CONTINUE', st == {'dis': False, 'chk': ['solo']}, st)
        await pg.fill('#plHrs', '-40'); await pg.evaluate("()=>document.getElementById('plHrs').dispatchEvent(new Event('change'))")
        ok('(a) negative hours clamp to 0', await pg.evaluate("()=>document.getElementById('plHrs').value") == '0')
        await pg.fill('#plHrs', '35.5')
        await finger(pg, '#plGo'); await pg.wait_for_timeout(500)
        pl = await pg.evaluate("()=>JSON.parse(localStorage.getItem('kgeuPlace')||'null')")
        ok('(a) CONTINUE saves kgeuPlace (level solo, 35.5 hours)', pl and pl['level'] == 'solo' and pl['hours'] == 35.5 and pl.get('at'), pl)
        ok('(a) it says the stages open', await pg.evaluate(SAY) == ['Stages 1 and 2 open'] * 2, await pg.evaluate(SAY))
        ok('(a) the intake closes', not await pg.evaluate("()=>document.getElementById('plOv').classList.contains('on')"))
        o = await pg.evaluate(OPEN)
        ok('(a) stages 1 and 2 open, 3 and 4 locked', o['s'] == ['s1', 's2'], o)
        nodes = await pg.evaluate("()=>[...document.querySelectorAll('#schMap .sNode')].map(n=>n.className.replace('sNode','').trim())")
        ok('(a) the map: stage 1 selected, stages 3 and 4 soon', nodes[0] == 'sel' and nodes[1] == '' and nodes[2] == 'soon' and nodes[3] == 'soon', nodes)
        await fit_map(pg, '844x390')

        # (b) every level's open set
        want = {'never': (['first'], ['s1']), 'student': (S1, ['s1']), 'solo': (S1 + S2, ['s1', 's2']), 'xc': (S1 + S2, ['s1', 's2', 's3']),
                'ride': (S1 + S2, ['s1', 's2', 's3', 's4']), 'cert': (S1 + S2, ['s1', 's2', 's3', 's4'])}
        for lv, (ls, ss) in want.items():
            o = await pg.evaluate(f"(lv)=>{{{K}.setPlace(lv,null);return ({OPEN})()}}", lv)
            ok(f'(b) {lv}: open lessons and stages', o['l'] == ls and o['s'] == ss, o)
        ok('(b) cert shows the REFRESHER tag', await pg.evaluate("()=>!document.getElementById('schRef').hidden"))

        # (g) 568x320: the intake again (from Settings, so with Back too), then the map
        await pg.set_viewport_size({'width': 568, 'height': 320})
        await pg.evaluate(f"()=>{{{K}.openMenu('sSet');document.getElementById('bPlace').scrollIntoView({{block:'nearest'}})}}"); await pg.wait_for_timeout(300)   # one scrolling column at 568
        await finger(pg, '#bPlace'); await pg.wait_for_timeout(300); await pg.wait_for_function(IDLE, timeout=5000)
        bad = await pg.evaluate(FIT, '#plOv .sheet')
        ok('(g) 568x320 the intake fits with Back showing, 44 px targets', not bad and await pg.evaluate("()=>!document.getElementById('plBack').hidden"), bad)
        await finger(pg, '#plOpts [data-lv=student]'); await finger(pg, '#plGo'); await pg.wait_for_timeout(500)
        await fit_map(pg, '568x320')
        # item 8 round 2: the compact header at 700 px or less; the cards start by 216 px (the floor with a title line, a 44 px
        # button row and the under-node map below the 66 px tab bar) and a second row of cards shows
        L = await pg.evaluate("""()=>{const R=[...document.querySelectorAll('#school .lrow')].map(e=>e.getBoundingClientRect().top),T=[...new Set(R.map(Math.round))].sort((a,b)=>a-b);
          const cap=document.querySelector('#schMap .sNode .cap').getBoundingClientRect(),ring=document.querySelector('#schMap .sNode .ring').getBoundingClientRect();
          return {first:T[0],second:T[1],H:innerHeight,under:cap.top>=ring.bottom-0.5,ring:Math.round(ring.width),hint:getComputedStyle(document.getElementById('ezHint')).display,
            cap:document.querySelector('.schT .gcap').textContent,sum:getComputedStyle(document.getElementById('schSum')).display}}""")
        ok('(g) 568x320: the first card row starts by 216 px and a second row shows', L['first'] <= 216 and L['second'] < L['H'] - 12, L)
        ok('(g) 568x320: captions under 40 px nodes, the hint hidden, the summary folded into the caption', L['under'] and L['ring'] == 40 and L['hint'] == 'none' and L['sum'] == 'none'
           and L['cap'].startswith('Cessna 172 at Glendale · ') and ' h · ' in L['cap'], L)
        ok('(h) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (c) Never flown is sequential; (d) locked rows and a locked stage
        # (b) checked never with nothing passed; here First flight is passed
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuPlace='{"level":"never","hours":null}', kgeuSchool='{"cessna:first":"B"}'))
        o = await pg.evaluate(OPEN)
        ok('(c) First flight passed: Climbs opens next (every Stage 1 lesson flies since item 6)', o['l'] == ['first', 'climbs'] and await pg.evaluate(f"()=>{K}.nextLesson()") == 'climbs', o)
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
        rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].filter(r=>!r.classList.contains('soon')).map(r=>[r.dataset.l,r.className.replace('lrow','').trim(),!!r.querySelector('.lk')])")
        ok('(d) the nine stage 1 rows all flyable: first done, climbs next, the other seven locked with a lock', rows == [['first', 'done', False], ['climbs', 'next', False]] + [[l, 'locked', True] for l in S1[2:]], rows)
        await pg.evaluate("()=>document.querySelector('#school [data-l=slow]').scrollIntoView({block:'nearest'})")
        await finger(pg, '#school [data-l=slow]'); await pg.wait_for_timeout(500)
        ok('(d) a locked row says what to pass and starts nothing', await pg.evaluate(SAY) == ['Pass Climbs, descents and turns first'] * 2 and await pg.evaluate(f"()=>{K}.LES.on===null&&!{K}.running()"), await pg.evaluate(SAY))
        await finger(pg, '#schMap [data-st=s2]'); await pg.wait_for_timeout(400)
        st = await pg.evaluate(f"()=>({{sel:{K}.schSel,rows:[...document.querySelectorAll('#school .lrow')].map(r=>r.dataset.l),lk:document.querySelector('#school [data-l=steep]').classList.contains('locked'),soon:document.querySelectorAll('#school .lrow.soon').length,node:document.querySelector('#schMap [data-st=s2]').className}})")
        ok('(d) tapping the locked stage 2 selects it and shows its locked cards', st['sel'] == 's2' and st['rows'] == S2 and st['lk'] and 'locked' in st['node'] and 'sel' in st['node'], st)
        ok('(d) every Stage 2 row is flyable now (item 7): no Coming soon row in stage 2', st['soon'] == 0 and await pg.evaluate(f"()=>{json.dumps(S2)}.every(id=>!{K}.lessonDef(id).soon&&!!{K}.lessonDef(id).fly)"), st)
        await finger(pg, '#school [data-l=steep]'); await pg.wait_for_timeout(500)
        ok('(d) a lesson in a locked stage: Finish Stage 1 first', await pg.evaluate(SAY) == ['Finish Stage 1 first'] * 2 and await pg.evaluate(f"()=>{K}.LES.on===null"), await pg.evaluate(SAY))
        await finger(pg, '#school [data-l=short]'); await pg.wait_for_timeout(300)
        ok('(d) a Stage 2 flight in the locked stage (short field) does nothing either', await pg.evaluate(SAY) == ['Finish Stage 1 first'] * 2 and await pg.evaluate(f"()=>{K}.LES.on===null"))
        await pg.evaluate(f"()=>{K}.startLesson('stall')"); await pg.wait_for_timeout(300)
        ok('(d) startLesson refuses a locked lesson, force starts it', await pg.evaluate(f"()=>{K}.LES.on") is None and await pg.evaluate(f"()=>{{{K}.startLesson('stall',true);{K}.lesBriefSkip();return {K}.LES.on}}") == 'stall')
        await pg.evaluate("()=>document.getElementById('lesQuit').click()")
        await pg.evaluate("()=>localStorage.removeItem('kgeuPlace')")
        await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(300)
        ok('(a) never over the pause sheet', await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')&&!document.getElementById('plOv').classList.contains('on')"))

        # (e) Start from day one keeps the grades; (f) Retake placement from Settings, with Back
        await pg.evaluate(f"()=>{{{K}.setPlace('solo',12);{K}.openMenu('sSchool')}}"); await pg.wait_for_timeout(300)
        await finger(pg, '#schDay'); await pg.wait_for_timeout(400)
        st = await pg.evaluate(f"()=>({{p:JSON.parse(localStorage.getItem('kgeuPlace')),g:localStorage.getItem('kgeuSchool'),o:{K}.lessonOpen('first')&&{K}.lessonOpen('climbs')&&!{K}.lessonOpen('pattern'),s2:{K}.stageOpen('s2'),ln:document.querySelector('#school [data-l=first]').classList.contains('done')}})")
        ok('(e) Start from day one: placement never, hours and grades kept, First flight still ticked', st['p']['level'] == 'never' and st['p']['hours'] == 12 and st['g'] == '{"cessna:first":"B"}' and st['o'] and not st['s2'] and st['ln'], st)
        ok('(e) it says so', await pg.evaluate(SAY) == ['Starting from lesson 1. Your passed lessons stay passed'] * 2, await pg.evaluate(SAY))
        await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(300)
        await finger(pg, '#bPlace'); await pg.wait_for_timeout(500)
        st = await pg.evaluate(f"()=>({{scr:{K}.curScr(),on:document.getElementById('plOv').classList.contains('on'),back:!document.getElementById('plBack').hidden,chk:[...document.querySelectorAll('#plOpts [aria-checked=true]')].map(e=>e.dataset.lv)}})")
        ok('(f) Retake placement opens the school screen and the intake with Back', st == {'scr': 'sSchool', 'on': True, 'back': True, 'chk': ['never']}, st)
        await finger(pg, '#plOpts [data-lv=cert]'); await finger(pg, '#plBack'); await pg.wait_for_timeout(400)
        st = await pg.evaluate("()=>({on:document.getElementById('plOv').classList.contains('on'),lv:JSON.parse(localStorage.getItem('kgeuPlace')).level})")
        ok('(f) Back closes it and keeps the old placement', st == {'on': False, 'lv': 'never'}, st)
        ok('(h) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('school_map_check'))
asyncio.run(main())
