# School1 item 3: the lesson briefing. Three swipeable cards and the quiz before every lesson flight.
# (a) a first start of slow flight: the sheet, four slides, no Skip, the sim held, pause blocked, no lesson card;
# (b) NEXT and a swipe move the dot, the quiz slide says ANSWER FIRST, disabled; (c) a wrong answer: red, the right
# one outlined, the explanation, LES.quiz.ok false, LET'S FLY; (d) LET'S FLY: the lesson runs, the card shows, the
# opening line goes out; (e) a replay shows Skip, Skip flies; (f) Back returns to the school screen; (g) it fits at
# 844x390 and 568x320, a card's body fills its slide; restarts (pause Restart, Try again, crash RETRY) fly at once; (h) the funnel's EASY path briefs lesson 1, then the arrows tutorial; (i) no page errors.
# Run: .venv/bin/python tests/school_brief_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuPlace': '{"level":"solo","hours":null}'}
ST = f"""()=>{{const o=document.getElementById('brOv');return {{on:o.classList.contains('on')&&!o.classList.contains('out'),n:document.querySelectorAll('#brTrack .brS').length,
  skip:!document.getElementById('brSkip').hidden,paused:{K}.paused(),card:document.getElementById('lesson').classList.contains('on'),les:{K}.LES.on,
  slide:{K}.lesBrief.slide,dot:[...document.querySelectorAll('#brDots i')].findIndex(e=>e.classList.contains('on')),
  next:document.getElementById('brNext').textContent,dis:document.getElementById('brNext').disabled,pz:document.getElementById('pauseOv').classList.contains('on')}}}}"""
# every button 44 px and on screen, the sheet itself never scrolls (the card body alone may)
FIT = """()=>{const s=document.querySelector('#brOv .sheet'),W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('sheet scrolls');const o=document.getElementById('brOv');if(o.scrollHeight>o.clientHeight+1)bad.push('overlay scrolls');
  const tr=document.getElementById('brTrack').getBoundingClientRect();
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;const sl=e.closest('.brS');
    if(sl){const q=sl.getBoundingClientRect();if(Math.abs(q.left-tr.left)>2)return;}   // only the slide in view
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});
  return bad;}"""
LINES = """()=>{const tr=document.getElementById('brTrack'),S=tr.querySelector('.brS'),h=S.querySelector('h4').getBoundingClientRect().height,
  p=S.querySelector('.brB p'),lh=parseFloat(getComputedStyle(p).lineHeight)||parseFloat(getComputedStyle(p).fontSize)*1.35;
  const b=S.querySelector('.brB'),cs=getComputedStyle(b),pad=parseFloat(cs.paddingTop)+parseFloat(cs.paddingBottom)+parseFloat(cs.borderTopWidth)*2;
  return (tr.clientHeight-h-7-pad)/lh;}"""

SETTLED = "()=>{const t=document.getElementById('brTrack');return Math.abs(t.scrollLeft-window.__kgeu.lesBrief.slide*t.clientWidth)<2}"

async def go_slide(pg, k):
    await pg.evaluate(f"(k)=>{{const t=document.getElementById('brTrack');t.scrollLeft=k*t.clientWidth;t.dispatchEvent(new Event('scroll'));}}", k)
    await pg.wait_for_timeout(250)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # (a) a first start: the sheet over the held sim
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(f"()=>{{{K}.radioLog(true);{K}.startLesson('slow')}}"); await pg.wait_for_timeout(600)
        s = await pg.evaluate(ST)
        ok('(a) slow flight opens the briefing: four slides, no Skip on a first start, paused, no lesson card', s['on'] and s['n'] == 4 and not s['skip'] and s['paused'] and not s['card'] and s['les'] == 'slow', s)
        cap = await pg.evaluate("()=>[document.getElementById('brK').textContent,document.getElementById('brT').textContent,document.querySelector('#brOv .brBy').textContent]")
        ok('(a) caption, title and the CFI byline', cap == ['STAGE 1 · LESSON 4 OF 9', 'Slow flight', 'DRDana Reyes, CFI'], cap)
        await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(150)
        s = await pg.evaluate(ST)
        ok('(a) the pause button does nothing while it is up', s['paused'] and not s['pz'] and s['on'], s)
        t0 = await pg.evaluate(f"()=>{K}.state().time"); await pg.wait_for_timeout(700)
        ok('(a) the sim is held', await pg.evaluate(f"()=>{K}.state().time") == t0)
        ok('(a) the radio is quiet: no opening line yet', not any('Slow flight' in (l.get('text') or '') for l in await pg.evaluate(f"()=>{K}.radioLog()")))
        # (b) NEXT, a swipe, the quiz slide
        await finger(pg, '#brNext'); await pg.wait_for_timeout(700)
        s = await pg.evaluate(ST)
        ok('(b) NEXT moves to card 2, the dot follows', s['slide'] == 1 and s['dot'] == 1 and s['next'] == 'NEXT', s)
        await go_slide(pg, 2)
        s = await pg.evaluate(ST)
        ok('(b) a swipe (scroll) moves to card 3, the dot follows', s['slide'] == 2 and s['dot'] == 2, s)
        await finger(pg, '#brNext'); await pg.wait_for_timeout(700)
        s = await pg.evaluate(ST)
        ok('(b) the quiz slide: ANSWER FIRST, disabled', s['slide'] == 3 and s['dot'] == 3 and s['next'] == 'ANSWER FIRST' and s['dis'], s)
        await finger(pg, '#brNext'); await pg.wait_for_timeout(300)
        ok('(b) the disabled button does not start the flight', (await pg.evaluate(ST))['on'])
        bad = await pg.evaluate(FIT)
        ok('(g) 844x390 the quiz fits, 44 px targets, the sheet does not scroll', not bad, bad)
        # (c) a wrong answer (slow flight's right answer is the first: Add power)
        await finger(pg, '#brTrack .brQ .brAns:nth-child(2)'); await pg.wait_for_timeout(300)
        q = await pg.evaluate("""()=>{const bs=[...document.querySelectorAll('#brTrack .brAns')],w=document.querySelector('#brTrack .brWhy');
          return {cls:bs.map(b=>b.className.replace('brAns','').trim()),bg:getComputedStyle(bs[1]).backgroundColor,dis:bs.map(b=>b.getAttribute('aria-disabled')),
            op:getComputedStyle(bs[2]).opacity,why:!w.hidden&&w.textContent,chk:bs.map(b=>b.getAttribute('aria-checked'))}}""")
        ok('(c) the tapped one turns red, the right one is outlined green, the others lock', q['cls'] == ['should', 'wrong', '', ''] and q['bg'] == 'rgb(216, 52, 44)'
           and q['dis'] == ['true', None, 'true', 'true'] and q['op'] == '0.6' and q['chk'] == ['false', 'true', 'false', 'false'], q)
        ok('(c) the explanation shows with Not quite.', bool(q['why']) and q['why'].startswith('Not quite. Pulling up near the stall'), q['why'])
        s = await pg.evaluate(ST)
        ok("(c) LES.quiz.ok is false and the button reads LET'S FLY", await pg.evaluate(f"()=>{K}.LES.quiz") == {'ok': False} and s['next'] == "LET'S FLY" and not s['dis'], s)
        await finger(pg, '#brTrack .brQ .brAns:nth-child(1)'); await pg.wait_for_timeout(200)
        ok('(c) a second tap changes nothing', await pg.evaluate(f"()=>{K}.LES.quiz") == {'ok': False})
        # (d) LET'S FLY
        await finger(pg, '#brNext'); await pg.wait_for_timeout(300)
        s = await pg.evaluate(ST)
        ok("(d) LET'S FLY: the lesson runs, not paused, the lesson card on", not s['on'] and s['les'] == 'slow' and not s['paused'] and s['card'], s)
        line = None
        for i in range(20):
            lg = await pg.evaluate(f"()=>{K}.radioLog().map(l=>l.text||'')")
            line = next((t for t in lg if t.startswith('Slow flight')), None) or (await pg.evaluate("()=>document.getElementById('atc').textContent") if 'Slow flight' in await pg.evaluate("()=>document.getElementById('atc').textContent") else None)
            if line: break
            await pg.wait_for_timeout(100)
        ok('(d) the opening line is on the air within 2 s', bool(line), line)
        await pg.wait_for_timeout(1200)
        ok('(d) the lesson clock started from 0 at LET\'S FLY', 0 < await pg.evaluate(f"()=>{K}.LES.t") < 5, await pg.evaluate(f"()=>{K}.LES.t"))
        # a restart (pause Restart, the runRestart path) of this first-start lesson flies at once, no sheet
        await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(300)
        r = await pg.evaluate("()=>{const e=document.getElementById('pApply'),r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2,e.textContent]}")
        await pg.touchscreen.tap(r[0], r[1]); await pg.wait_for_timeout(500)
        s = await pg.evaluate(ST)
        ok('(d) a pause Restart of a first-start lesson skips the briefing', r[2] == 'Restart' and not s['on'] and s['les'] == 'slow' and not s['paused'] and s['card'], s)
        await pg.evaluate(f"()=>{K}.runRestart()"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(ST)
        ok('(d) Try again (runRestart) skips it too', not s['on'] and s['les'] == 'slow' and not s['paused'], s)
        await pg.evaluate(f"()=>{K}.crashNow('Test crash.')")
        for _ in range(4): await pg.evaluate(f"()=>{K}.stepFrame(1/30,false,true)")
        await pg.evaluate(f"()=>{{{K}.stepFrame(0,true);{K}.crashRetry()}}"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(ST)
        ok('(d) crash RETRY skips it too', not s['on'] and s['les'] == 'slow' and not s['paused'], s)
        ok('(i) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (e) a replay: Skip briefing goes straight to the flight
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuSchool='{"cessna:slow":"C"}'))
        await pg.evaluate(f"()=>{K}.startLesson('slow')"); await pg.wait_for_timeout(500)
        s = await pg.evaluate(ST)
        ok('(e) a replay shows Skip briefing', s['on'] and s['skip'], s)
        # measured once the sheet's scale-in has finished (the headless harness can be mid animation at 500 ms)
        r = await pg.evaluate("async()=>{await Promise.all(document.getElementById('brOv').getAnimations({subtree:true}).map(a=>a.finished.catch(()=>0)));const r=document.getElementById('brSkip').getBoundingClientRect();return [r.width,r.height]}")
        ok('(e) Skip is a 44 px target', r[0] >= 44 and r[1] >= 44, r)
        await finger(pg, '#brSkip'); await pg.wait_for_timeout(300)
        s = await pg.evaluate(ST)
        ok('(e) Skip goes straight to the flight, no quiz recorded', not s['on'] and s['les'] == 'slow' and not s['paused'] and s['card'] and await pg.evaluate(f"()=>{K}.LES.quiz") is None, s)
        # (f) Back
        await pg.evaluate(f"()=>{K}.startLesson('slow')"); await pg.wait_for_timeout(500)
        await finger(pg, '#brBack'); await pg.wait_for_timeout(500)
        f = await pg.evaluate(f"()=>({{menu:document.getElementById('menu').classList.contains('on'),scr:{K}.curScr(),les:{K}.LES.on,brief:{K}.lesBrief.on,ov:document.getElementById('brOv').classList.contains('on')}})")
        ok('(f) Back returns to the school screen, no lesson', f == {'menu': True, 'scr': 'sSchool', 'les': None, 'brief': False, 'ov': False}, f)
        ok('(i) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (g) 568x320: every slide fits, the card body has four lines before it scrolls
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage=dict(BASE, kgeuSchool='{"cessna:engine":"B"}'))
        await pg.evaluate(f"()=>{K}.startLesson('engine')"); await pg.wait_for_timeout(500)
        n = await pg.evaluate(LINES)
        ok('(g) 568x320 the card body shows at least four lines before it scrolls', n >= 4, f'{n:.1f} lines')
        fill = await pg.evaluate("""()=>[...document.querySelectorAll('#brTrack .brCard')].map(S=>{const r=S.getBoundingClientRect(),b=S.querySelector('.brB').getBoundingClientRect();return [Math.round(r.bottom-b.bottom),S.querySelector('.brC').textContent]})""")
        ok('(g) each card body fills its slide, captioned CARD n OF 3', [f[1] for f in fill] == ['CARD 1 OF 3', 'CARD 2 OF 3', 'CARD 3 OF 3'] and all(abs(f[0]) <= 1 for f in fill), fill)
        bads = []
        for k in range(4):
            await go_slide(pg, k); bads += [f'{k}: {x}' for x in await pg.evaluate(FIT)]
        await finger(pg, '#brTrack .brQ .brAns:nth-child(3)'); await pg.wait_for_timeout(300)
        bads += [f'answered: {x}' for x in await pg.evaluate(FIT)]
        ok('(g) 568x320 every slide and the answered quiz: 44 px targets on screen, the sheet does not scroll', not bads, bads)
        ok('(i) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (h) the funnel's EASY path: lesson 1's briefing, then the arrows
        pg = await page(b, url, storage={})
        await finger(pg, '#fRookie'); await pg.wait_for_timeout(1200)
        s = await pg.evaluate(ST)
        ok('(h) EASY opens Lesson 1\'s briefing first', s['on'] and s['n'] == 4 and not s['skip'] and s['les'] == 'first' and s['paused'] and await pg.evaluate("()=>document.getElementById('brT').textContent") == 'First flight', s)
        ok('(h) no arrow under the briefing', not await pg.evaluate("()=>document.getElementById('tutArrow').classList.contains('on')"))
        for i in range(3): await pg.evaluate(f"()=>{K}.lesBriefNext()"); await pg.wait_for_timeout(500)
        await pg.wait_for_function(SETTLED, timeout=8000)   # the smooth scroll is slow at the harness's frame rate
        await finger(pg, '#brTrack .brQ .brAns:nth-child(4)'); await pg.wait_for_timeout(200)
        ok('(h) the right answer turns green and records ok', await pg.evaluate(f"()=>{K}.LES.quiz") == {'ok': True}
           and await pg.evaluate("()=>getComputedStyle(document.querySelector('#brTrack .brAns.right')).backgroundColor") == 'rgb(63, 143, 79)')
        await finger(pg, '#brNext'); await pg.wait_for_timeout(1200)
        s = await pg.evaluate(ST)
        ok("(h) after LET'S FLY the arrows tutorial runs", s['les'] == 'first' and not s['paused'] and not s['on'] and await pg.evaluate("()=>document.getElementById('tutArrow').classList.contains('on')"), s)
        ok('(i) no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('school_brief_check'))
asyncio.run(main())
