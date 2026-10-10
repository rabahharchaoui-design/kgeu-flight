# Flight school on the home screen, with the first flight tutorial as lesson 1.
# Run: .venv/bin/python tests/school_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"
FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight,bad=[];
  if(s.scrollHeight>s.clientHeight+1)bad.push('scrolls');
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});return bad;}"""

async def st(pg): return await pg.evaluate(f"()=>{{const s={K}.state();return {{g:s.onGround,agl:s.agl,v:Math.hypot(s.vel.x,s.vel.z),ph:{K}.LES.ph,on:{K}.LES.on,crash:s.crashed,thr:s.throttle}}}}")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # first launch as a rookie: the funnel starts lesson 1 by itself, through its briefing (school1 item 3)
        pg = await page(b, url, storage={})
        await finger(pg, '#fRookie'); await pg.wait_for_timeout(1500)
        br = await pg.evaluate(f"()=>({{on:{K}.lesBrief.on,les:{K}.LES.on,paused:{K}.paused()}})")
        ok('New to flying opens lesson 1 with its briefing first', br == {'on': True, 'les': 'first', 'paused': True}, br)
        for i in range(3):
            await finger(pg, '#brNext')
            await pg.wait_for_function(f"()=>{{const t=document.getElementById('brTrack');return {K}.lesBrief.slide=={i + 1}&&Math.abs(t.scrollLeft-{i + 1}*t.clientWidth)<2}}", timeout=8000)
        await finger(pg, '#brTrack .brQ .brAns:nth-child(4)'); await pg.wait_for_timeout(200)
        await finger(pg, '#brNext'); await pg.wait_for_timeout(1200)
        s = await st(pg)
        ok('New to flying launches lesson 1 after NEXT x3, an answer and LET\'S FLY', s['on'] == 'first' and s['g'] and not await pg.evaluate(f"()=>{K}.lesBrief.on||{K}.paused()"), s)
        info = await pg.evaluate(f"()=>({{type:{K}.state().type,base:{K}.state().base,skip:document.getElementById('lesQuit').textContent,arrow:document.getElementById('tutArrow').classList.contains('on')}})")
        ok('it is the Cessna at Glendale with a big Skip and an arrow', info == {'type': 'cessna', 'base': 'kgeu', 'skip': 'Skip', 'arrow': True}, info)
        r = await pg.evaluate("()=>{const r=document.getElementById('lesQuit').getBoundingClientRect();return [r.width,r.height]}")
        ok('Skip is a 44 px target', r[0] >= 44 and r[1] >= 44, r)
        # fly it with the real controls
        t = await pg.evaluate("()=>{const r=document.getElementById('thr').getBoundingClientRect();return [r.x+r.width/2,r.y,r.height]}")
        await pg.evaluate("""([x,y,h])=>{const e=document.getElementById('thr');const ev=(n,yy)=>e.dispatchEvent(new PointerEvent(n,{pointerId:4,clientX:x,clientY:yy,bubbles:true}));
          ev('pointerdown',y+h*0.9);ev('pointermove',y+h*0.5);ev('pointermove',y+h*0.02);ev('pointerup',y+h*0.02);}""", t)
        await pg.wait_for_timeout(400)
        ok('step 1 done when the throttle reaches full', (await st(pg))['ph'] == 1)
        z = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}")
        async def stick(dx, dy):
            await pg.evaluate("""([x,y,dx,dy])=>{const e=document.getElementById('stickZone');const o={pointerId:6,bubbles:true};
              if(!window.__sd){e.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:x,clientY:y}));window.__sd=1;}
              e.dispatchEvent(new PointerEvent('pointermove',{...o,clientX:x+dx,clientY:y+dy}));}""", [z[0], z[1], dx, dy])
        async def release():
            await pg.evaluate("()=>{document.getElementById('stickZone').dispatchEvent(new PointerEvent('pointerup',{pointerId:6,bubbles:true}));window.__sd=0;}")
        phases = {}
        for i in range(160):
            s = await st(pg)
            phases[s['ph']] = phases.get(s['ph'], 0) + 1
            if s['on'] != 'first' or s['crash']: break
            if s['ph'] == 1: await stick(0, 30)
            elif s['ph'] == 3: await stick(40, 0)
            else: await release()
            await pg.evaluate(f"()=>{K}.ff(0.8)"); await pg.wait_for_timeout(90)
        await release(); await pg.wait_for_timeout(500)
        s = await st(pg)
        ok('lesson 1 runs every step to the end without a crash', set(range(1, 8)) <= set(phases) and not s['crash'] and s['on'] is None, (phases, s))
        g = await pg.evaluate("()=>({card:document.getElementById('gradeOv').classList.contains('on'),next:document.getElementById('gNext').textContent,hid:document.getElementById('gNext').hidden,letter:document.getElementById('gLetter').textContent})")
        ok('the result screen has a big Next lesson button', g['card'] and not g['hid'] and g['next'] == 'Next lesson: Climbs, descents and turns', g)
        sim = sum(phases.values()) * 0.8
        bad = await pg.evaluate(FIT, '#gradeOv')
        ok('result screen fits with 44 px targets', not bad, bad)
        ok('lesson 1 takes about a minute of flying', 45 < sim < 100, f'{sim:.0f} s simulated')
        await finger(pg, '#gNext'); await pg.wait_for_timeout(1200)
        ok('Next lesson starts Climbs (school1: the curriculum order), its briefing first', await pg.evaluate(f"()=>[{K}.LES.on,{K}.lesBrief.on]") == ['climbs', True])
        await pg.evaluate("()=>document.getElementById('lesQuit').click()")
        # home and the school screen
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(300)
        home = await pg.evaluate("()=>[...document.querySelectorAll('#sHome button')].map(b=>b.id)")
        ok('home: big FLY, then FLIGHT SCHOOL, CHALLENGES and RECORDS (ui1: Settings and Boards are tabs)', sorted(home) == sorted(['hRec','hFly','hSch','hChal']), home)
        sz = await pg.evaluate("()=>['hFly','hSch'].map(i=>{const r=document.getElementById(i).getBoundingClientRect();return r.width*r.height})")
        ok('FLY is the big primary button', sz[0] > sz[1] * 1.6, sz)
        ok('Start here is gone once lesson 1 is finished', not await pg.evaluate("()=>document.getElementById('startHere').classList.contains('on')"))
        await finger(pg, '#hSch'); await pg.wait_for_timeout(400)
        # school1: no placement yet, so the intake is up first. Never flown: lesson by lesson
        ok('the placement intake shows over the school screen on the first visit', await pg.evaluate("()=>document.getElementById('plOv').classList.contains('on')"))
        await finger(pg, '#plOpts [data-lv=never]'); await finger(pg, '#plGo'); await pg.wait_for_timeout(400)
        rows = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.classList.contains('done'),r.classList.contains('next'),r.classList.contains('soon')])")
        fly = [r[0] for r in rows if not r[3]]
        nxt = [r[0] for r in rows if r[2]]
        ok('stage 1 selected: nine rows, all flyable (item 6), lesson 1 ticked, Climbs highlighted next', len(rows) == 9 and len(fly) == 9 and rows[0][:2] == ['first', True] and nxt == ['climbs'], rows)
        caps = await pg.evaluate("()=>[...document.querySelectorAll('#schMap .sNode')].map(c=>[c.dataset.st,c.classList.contains('sel')])")
        ok('the stage map: four stages, stage 1 selected', caps == [['s1', True], ['s2', False], ['s3', False], ['s4', False]], caps)
        soon = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow.soon')].every(r=>r.getAttribute('aria-disabled')==='true'&&!r.onclick&&/Coming soon/i.test(r.textContent))")
        ok('the lessons still to come are disabled and tagged Coming soon', soon)
        VIS = """()=>{const L=document.getElementById('school'),lr=L.getBoundingClientRect(),bad=[];const rs=[...L.querySelectorAll('.lrow')];
          rs.slice(0,2).forEach(e=>{const r=e.getBoundingClientRect();if(r.top<lr.top-0.5||r.bottom>lr.bottom+0.5||r.bottom>innerHeight+0.5)bad.push('hidden '+e.dataset.l);});
          document.querySelectorAll('#sSchool button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});
          if(L.scrollHeight>L.clientHeight+1&&getComputedStyle(L).overscrollBehaviorY!=='contain')bad.push('no overscroll contain');
          if(document.getElementById('sSchool').scrollHeight>document.getElementById('sSchool').clientHeight+1)bad.push('screen scrolls');return bad;}"""
        ok('school screen: the first rows in view, the list scrolls inside, 44 px targets', not await pg.evaluate(VIS), await pg.evaluate(VIS))
        ok('flight school is not a Challenges card', await pg.evaluate("()=>{window.__kgeu.nav('sArc');return !document.querySelector('#arcCards [data-m=school]')}"))
        await pg.evaluate(f"()=>{K}.nav('sSchool')"); await pg.wait_for_timeout(200)
        await finger(pg, '#school [data-l="climbs"]'); await pg.wait_for_timeout(1200)
        ok('one tap on a lesson starts it (its briefing up)', await pg.evaluate(f"()=>[{K}.LES.on,{K}.lesBrief.on]") == ['climbs', True])
        ok('no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # a rookie who has not done lesson 1 sees Start here; a pilot does not
        pg = await page(b, url, storage={'kgeuOnboard': 'rookie'})
        ok('Start here shows for a rookie until lesson 1', await pg.evaluate("()=>document.getElementById('startHere').classList.contains('on')"))
        await pg.evaluate(f"()=>{K}.setSkill('pilot')"); await pg.evaluate(f"()=>{K}.nav('sHome',true)")
        ok('no Start here for pilots', not await pg.evaluate("()=>document.getElementById('startHere').classList.contains('on')"))
        await pg.evaluate(f"()=>{{{K}.setSkill('rookie');{K}.startLesson('first');{K}.lesBriefSkip()}}"); await pg.wait_for_timeout(800)
        await finger(pg, '#lesQuit'); await pg.wait_for_timeout(300)
        ok('Skip ends it, flight carries on', await pg.evaluate(f"()=>{K}.LES.on===null&&!{K}.paused()"))
        await pg.evaluate(f"()=>{{{K}.openMenu('sSet')}}"); await pg.wait_for_timeout(200)
        await finger(pg, '#bReplay'); await pg.wait_for_timeout(1000)
        ok('Replay lesson 1 in Settings starts lesson 1', await pg.evaluate(f"()=>{K}.LES.on") == 'first')
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('school_check'))
asyncio.run(main())
