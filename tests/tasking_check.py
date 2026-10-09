# Tasking item 1: the mission framework. A drill template (two stages) runs through the whole engine: the seeded roll,
# the briefing that holds the sim, the stage card, Mission Control on the radio (text, the squelch cue, Easy's plain
# line), the reply buttons in the top bar (placed clear of pause, the readouts and the controls at three phone sizes),
# a timed out ask, the score, the results card with the device board line, the XP pop (the Worker's formula), the
# Taskings group of four on Challenges and its four device boards (the Worker refuses task: ids: tasking_worker_check),
# RETRY rolling a new seed, and Back on the briefing.
# Run: .venv/bin/python tests/tasking_check.py
import asyncio, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
STEP = f"(n)=>{{for(let i=0;i<n;i++){K}.stepFrame(1/30,false,true)}}"
DRILL = """()=>{const K=window.__kgeu;K.TASKS.drill={name:'Drill',role:'Test',ac:'cessna',base:'kgeu',limit:400,
  roll:(R,d)=>{d.wdir=200;d.wkt=8;d.par=60;d.r1=R();d.r2=R();},
  brief:d=>({ac:'Cessna 172 \\u00b7 Glendale runway 1',sit:'A drill for the framework test.',facts:[['PAR','1:00'],['WIND','200 at 8']]}),
  spawn:d=>{},
  stages:[{id:'a',name:'Answer the call',obj:d=>['Answer Mission Control','WILCO or UNABLE'],
     enter:d=>K.tkQuiet(()=>{const l=K.tkMC(K.state().type==='cessna'?'Skyhawk, Mission Control, radio check, how do you read?':'x',{plain:'Mission Control asks if you can hear them.'});
       K.tkAsk([{k:'WILCO',fn:()=>{d.w=1;}},{k:'UNABLE',fn:()=>{d.u=1;}}],{line:l});}),tick:d=>d.w||d.u},
    {id:'b',name:'Report',obj:d=>['Report ready','Tap REPORT'],enter:d=>{K.tkAsk([{k:'REPORT',say:'Skyhawk, ready.',fn:()=>{d.r=1;}}],{keep:1});},tick:d=>d.r},
    {id:'c',name:'Wait',obj:d=>['Wait','for the call'],enter:d=>{K.tkAsk([{k:'WILCO'}],{wait:2,late:()=>{d.late=1;}});},tick:d=>d.late}],
  score:d=>({score:d.w?88:40,title:'Done',lines:[['Answered',d.w?'yes':'no']],wait:300})};}"""

async def air(pg, n=600):
    for _ in range(n // 30):
        await pg.evaluate(STEP, 30)
        t = await pg.evaluate(f"()=>{K}.task()")
        if t['ask'] and t['ask']['shown']: return t
    return await pg.evaluate(f"()=>{K}.task()")

RECT = "(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}"
def hit(a, b): return a and b and a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in [(844, 390), (568, 320), (667, 375)]:
            print(f'-- {vp[0]}x{vp[1]}')
            pg = await page(b, url, vp={'width': vp[0], 'height': vp[1]}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(DRILL)
            await pg.evaluate(f"()=>{K}.taskStart('drill',{{seed:1234}})"); await pg.wait_for_timeout(400)
            t = await pg.evaluate(f"()=>({{t:{K}.task(),p:{K}.paused(),on:document.getElementById('tkBrief').classList.contains('on'),"
                                  "fit:(()=>{const s=document.querySelector('#tkBrief .sheet').getBoundingClientRect();return s.top>=0&&s.bottom<=innerHeight&&s.left>=0&&s.right<=innerWidth})(),"
                                  "go:(()=>{const r=document.getElementById('tkGo').getBoundingClientRect();return r.height>=44&&r.bottom<=innerHeight})()})")
            ok('the briefing is up, the sim held, the whole card on screen with ACCEPT TASKING at least 44 tall', t['on'] and t['p'] and t['t']['brief'] and t['fit'] and t['go'], t)
            await pg.evaluate(f"()=>{K}.togglePause&&{K}.togglePause()")
            ok('pause does nothing under the briefing', await pg.evaluate(f"()=>document.getElementById('tkBrief').classList.contains('on')&&!document.getElementById('pauseOv').classList.contains('on')"))
            d1 = await pg.evaluate(f"()=>[{K}.task().d.r1,{K}.task().d.r2]")
            await finger(pg, '#tkGo'); await pg.wait_for_timeout(200)
            t = await pg.evaluate(f"()=>({{t:{K}.task(),p:{K}.paused(),card:document.getElementById('missT').textContent}})")
            ok('ACCEPT TASKING starts stage 1 and the sim; the card says 1/3 and the objective', not t['p'] and t['t']['stage'] == 'a' and t['card'].startswith('1/3') and 'Mission Control' in t['card'], t['card'])
            t = await air(pg)
            ok('the reply buttons come up once the call is on the air: WILCO, UNABLE', t['ask'] and t['ask']['shown'] and t['ask']['opts'] == ['WILCO', 'UNABLE'], t['ask'])
            sub = await pg.evaluate("()=>document.getElementById('atc').textContent")
            ok('the opening call waits for the tower\'s clearance and its readback, then is text in the radio subtitle', 'Mission Control' in sub and 'radio check' in sub, sub)
            lg = await pg.evaluate(f"()=>{K}.radioLog().slice(-3)")
            ok('the call went out on the radio queue (no clips: the squelch cue and the text)', any(l['who'] == 'Mission Control' and not l['clips'] for l in lg), lg)
            await pg.wait_for_timeout(350)   # the bar's 180 ms entrance from .96
            rb = await pg.evaluate(RECT, '#tkReply'); bts = [await pg.evaluate(RECT, f'#tkReply button:nth-child({i})') for i in (1, 2)]
            others = {s: await pg.evaluate(RECT, s) for s in ('#bPause', '#hud', '#dock', '#thrCol', '#topCol', '#map')}
            bad = [s for s, r in others.items() if r and any(hit(x, r) for x in bts)]
            ok('the replies sit in the top bar right of pause, on screen, clear of pause, the readouts and the controls', rb and rb[0] > others['#bPause'][2] and rb[2] <= vp[0] and rb[1] >= 0 and not bad, (rb, bad))
            ok('each reply is at least 44 tall and 56 wide', all(x and x[3] - x[1] >= 43.5 and x[2] - x[0] >= 56 for x in bts), bts)
            if vp[0] == 844: await pg.screenshot(path='/tmp/tasking_check_ask.png')
            await finger(pg, '#tkReply button[data-k="WILCO"]'); await pg.wait_for_timeout(150)
            await pg.evaluate(STEP, 3)
            t = await pg.evaluate(f"()=>{K}.task()")
            ok('WILCO: our readback in the log, the next stage, its REPORT button', t['stage'] == 'b' and any(l.get('who') == 'You' and l['text'].startswith('Wilco') for l in t['log']) and t['ask'] and t['ask']['opts'] == ['REPORT'], (t['stage'], t['log'][-2:]))
            rl = await pg.evaluate(f"()=>{K}.radioQ().map(l=>[l.who,(l.clips||[]).join(' ')])")
            ok('the Wilco readback uses the recorded clip', any(c.startswith('p_rb_wilco') for _, c in rl) or any(l['clips'] and l['clips'][0] == 'p_rb_wilco' for l in await pg.evaluate(f"()=>{K}.radioLog()")), rl)
            await pg.evaluate(STEP, 200)
            ok('a keep ask stays up while it waits (REPORT after 6 s)', (await pg.evaluate(f"()=>{K}.task().ask"))['opts'] == ['REPORT'])
            await finger(pg, '#tkReply button[data-k="REPORT"]'); await pg.wait_for_timeout(150); await pg.evaluate(STEP, 3)
            t = await air(pg, 120)
            ok('REPORT: the stage after it', t['stage'] == 'c', t['stage'])
            await pg.evaluate(STEP, 120)
            t = await pg.evaluate(f"()=>{K}.task()")
            ok('an ask nobody answers times out: its late call runs, a missed reply is counted, the tasking ends', t['done'] and t['d']['missed'] >= 1 and t['res'], (t['done'], t['d'].get('missed')))
            await pg.wait_for_timeout(900)
            r = await pg.evaluate("()=>({on:document.getElementById('missOv').classList.contains('on'),t:document.getElementById('mTitle').textContent,s:document.getElementById('mScore').textContent,"
                                  "l:[...document.querySelectorAll('#mLines .gl')].map(e=>e.innerText.replace(/\\s+/g,' ')),retry:document.getElementById('mRetry').textContent})")
            xp = await pg.evaluate(f"()=>{K}.XPP.log.slice(-1)[0]")
            want = await pg.evaluate(f"()=>{K}.taskXp(88,'hard',true)")
            ok('the results card: the grade, 88 of 100, the lines, the time against par, RETRY DRILL', r['on'] and r['t'].startswith('Drill: Done') and r['s'].startswith('88') and any(x.startswith('Time') and 'par 1:00' in x for x in r['l']) and r['retry'] == 'RETRY DRILL', r)
            ok('the device board line and the XP pop (the Worker formula, Hard, first run is a best)', any('Board, this device' in x and '#1 of 1' in x for x in r['l']) and xp and xp['amount'] == want == 72, (r['l'], xp))
            # RETRY: a new seed, a new roll
            await finger(pg, '#mRetry'); await pg.wait_for_timeout(400)
            t = await pg.evaluate(f"()=>{K}.task()")
            ok('RETRY flies the tasking again with a fresh seed (the briefing first)', t['on'] and t['brief'] and t['seed'] != 1234 and await pg.evaluate(f"()=>{K}.RUNSTART().k==='task'"), t['seed'])
            await pg.evaluate(f"()=>{K}.taskStop()")
            await pg.evaluate(f"()=>{K}.taskStart('drill',{{seed:1234}})"); d2 = await pg.evaluate(f"()=>[{K}.task().d.r1,{K}.task().d.r2]")
            ok('the same seed rolls the same tasking', d1 == d2, (d1, d2))
            await finger(pg, '#tkBack'); await pg.wait_for_timeout(400)
            ok('Back on the briefing: the tasking is gone, the Challenges screen is up', await pg.evaluate(f"()=>!{K}.task().on&&document.getElementById('menu').classList.contains('on')&&document.getElementById('sArc').classList.contains('on')"))
            ok('no console errors', not pg.errs, pg.errs[:3])
            await pg.close()

        print('-- Easy: the plain English line; Challenges and the boards')
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(DRILL)
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('drill',{{seed:7}})}}")
        await air(pg)
        pl = await pg.evaluate("()=>{const e=document.querySelector('#atc .plain');return e?e.textContent:''}")
        ok('Easy: the call shows its plain line', pl == 'Mission Control asks if you can hear them.', pl)
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=false;{K}.taskStop();{K}.openMenu('sArc')}}"); await pg.wait_for_timeout(300)
        c = await pg.evaluate("()=>{const g=[...document.querySelectorAll('#arcCards > *')];const i=g.findIndex(e=>e.classList.contains('cgrp'));return {head:g[i]&&g[i].textContent,cards:i<0?[]:g.slice(i+1).map(e=>({id:e.dataset.m,b:e.querySelector('b').textContent,tro:!!e.querySelector('.tro'),ico:!!e.querySelector('svg')}))}}")
        built = await pg.evaluate(f"()=>['overwatch','lifeline','shepherd','finder'].filter(t=>{K}.TASKS[t]).map(t=>{K}.TASKS[t].name)")
        ok('Challenges: a Taskings group with a card for each tasking that is in, each with an icon and a board link (the drill has none)', (c['head'] == 'Taskings' if built else c['head'] is None) and [x['b'] for x in c['cards']] == built and all(x['tro'] and x['ico'] for x in c['cards']), (c, built))
        # the device boards: two runs on Overwatch's board, the picker group, the rows, the note, works with no Worker
        await pg.evaluate(f"()=>{{localStorage.removeItem('kgeuTaskLB');const L={K}.LB;window._a=L.localAdd('task:overwatch',71,240);window._b=L.localAdd('task:overwatch',64,250);window._c=L.localAdd('task:overwatch',90,230);}}")
        a = await pg.evaluate("()=>[window._a,window._b,window._c]")
        ok('localAdd ranks among this device\'s runs and spots a best', a[0] == {'rank': 1, 'total': 1, 'pb': True} and a[1] == {'rank': 2, 'total': 2, 'pb': False} and a[2] == {'rank': 1, 'total': 3, 'pb': True}, a)
        await pg.evaluate(f"()=>{K}.LB.lbOpen('task:overwatch')"); await pg.wait_for_timeout(400)
        lb = await pg.evaluate("()=>({t:document.getElementById('lbTitle').textContent,rows:[...document.querySelectorAll('#lbRowsIn .lbRow .s')].map(e=>e.textContent),me:document.getElementById('lbMe').innerText,tot:document.getElementById('lbTotal').textContent,msg:document.getElementById('lbRowsIn').innerText})")
        ok('the Overwatch board shows this device\'s runs, best first, and says where they live', lb['t'] == 'Overwatch' and lb['rows'][:3] == ['90 pts', '71 pts', '64 pts'] and 'this device' in lb['me'] and lb['tot'] == '3 runs' and 'Offline' not in lb['msg'], lb)
        await finger(pg, '#lbPick'); await pg.wait_for_timeout(300)
        g = await pg.evaluate("()=>{const h=[...document.querySelectorAll('#lbList h3')].map(e=>e.textContent);const i=h.indexOf('Taskings');return {h:h,ids:i<0?[]:[...document.querySelectorAll('#lbList .lbG')][i].querySelectorAll('button').length}}")
        ok('the board picker has a Taskings group of four', 'Taskings' in g['h'] and g['ids'] == 4, g)
        ok('no console errors (Easy, boards)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('tasking_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
