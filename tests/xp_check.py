# ui1 items 5 to 8: the XP pop and where it fires.
#  (a) xpPop(amount, reason): a centre screen burst that counts up to the amount, the reason under it, inside the safe
#      area (a 47 px notch stood in), never takes a touch (the stick under it still gets the finger), two close together
#      stack (the older one steps up), gone after about 2.5 s; 568x320 and 844x390.
#  (b) the pops fire only when the (mocked) Worker grants XP, with its number: a free flight landing, a lesson, a
#      challenge and the daily; none with no callsign, for a practice daily, a refused run or no connection.
#  (c) Home: the rank insignia, callsign, total XP from the server and the bar to the next rank (filled to the right
#      share, animated on transform), updated by a run's answer; the top rank and no callsign read right.
# Run: .venv/bin/python tests/xp_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT
from ui1_mock import Mock
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'ui1')
SETSAFE = """([t,l,r,b])=>{const s=document.documentElement.style;s.setProperty('--saT',t+'px');s.setProperty('--saL',l+'px');s.setProperty('--saR',r+'px');s.setProperty('--saB',b+'px');}"""
POP = """()=>{const p=[...document.querySelectorAll('#xpPops .xpPop')];return p.map(e=>{const r=e.querySelector('.xpIn').getBoundingClientRect();
  return {n:e.querySelector('.xpN b').textContent,r:(e.querySelector('.xpR')||{}).textContent||'',x:r.left,y:r.top,w:r.width,h:r.height,cx:r.left+r.width/2,cy:r.top+r.height/2,
    pe:[e,...e.querySelectorAll('*')].every(n=>getComputedStyle(n).pointerEvents==='none'),done:e.classList.contains('done'),tr:e.style.transform}})}"""


async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in ({'width': 844, 'height': 390}, {'width': 568, 'height': 320}):
            tag = f"{vp['width']}x{vp['height']}"
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(SETSAFE, [0, 47, 47, 21])
            await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}"); await pg.wait_for_timeout(500)
            await pg.evaluate(f"()=>{K}.xpPop(37,'Landing graded',{{hold:5000}})")
            await pg.wait_for_timeout(250)
            a = await pg.evaluate(POP)
            ok(f'{tag} (a) one pop shows at once, the reason under it', len(a) == 1 and a[0]['r'] == 'Landing graded', a)
            W, H = vp['width'], vp['height']
            ok(f'{tag} (a) centre screen: centred across, in the middle band, inside the safe area',
               a and abs(a[0]['cx'] - W / 2) < 6 and H * 0.2 < a[0]['cy'] < H * 0.62 and a[0]['x'] >= 47 - 0.5 and a[0]['x'] + a[0]['w'] <= W - 47 + 0.5, a)
            ok(f'{tag} (a) it never takes a touch (pointer-events none all the way down)', a and a[0]['pe'], a)
            # a finger on the pop lands on what is under it
            hit = await pg.evaluate("()=>{const r=document.querySelector('#xpPops .xpIn').getBoundingClientRect();const e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return e&&!e.closest('#xpPops')}")
            ok(f'{tag} (a) a tap on it goes through to the game', hit)
            await pg.wait_for_timeout(900)
            a = await pg.evaluate(POP)
            ok(f'{tag} (a) the number counted up to 37 and glows', a and a[0]['n'] == '37' and a[0]['done'], a)
            await pg.evaluate(f"()=>{K}.xpPop(15,'Personal best')")
            for _ in range(12):   # the step up is a 260 ms transition: at 3 fps under load it can take a few frames
                await pg.wait_for_timeout(250); a = await pg.evaluate(POP)   # DOM order: the older pop first
                if len(a) == 2 and a[0]['cy'] < a[1]['cy'] - 30: break
            ok(f'{tag} (a) a second pop stacks: the new one in the centre, the older one stepped up and smaller', len(a) == 2 and a[0]['cy'] < a[1]['cy'] - 30 and 'translateY' in a[0]['tr'] and abs(a[1]['cx'] - W / 2) < 6, a)
            await pg.screenshot(path=os.path.join(SHOTS, f'xp_stack_{tag}.png'))
            await pg.wait_for_timeout(2600)
            await pg.evaluate(f"()=>{{{K}.xpPop(37,'Landing graded',{{hold:6000}})}}"); await pg.wait_for_timeout(1300)
            await pg.screenshot(path=os.path.join(SHOTS, f'xp_pop_{tag}.png'))
            await pg.wait_for_timeout(5200)
            await pg.evaluate(f"()=>{{const K={K};K.xpPop(1,'a');K.xpPop(2,'b');K.xpPop(3,'c');}}"); await pg.wait_for_timeout(200)
            n = await pg.evaluate("()=>document.querySelectorAll('#xpPops .xpPop').length")
            ok(f'{tag} (a) never more than three on screen', n == 3, n)
            ok(f'{tag} (a) nothing for zero or a negative amount', await pg.evaluate(f"()=>{K}.xpPop(0,'x')===null&&{K}.xpPop(-5,'x')===null"))
            await pg.wait_for_timeout(2800)
            n = await pg.evaluate("()=>document.querySelectorAll('#xpPops .xpPop').length")
            ok(f'{tag} (a) gone after about 2.5 s', n == 0, n)
            ok(f'{tag} (a) the light haptic was asked for', await pg.evaluate(f"()=>{K}.HAP?{K}.HAP.log.some(x=>x.n==='xp'):true"))
            ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        # ---------------- (b) the pops follow the server's grant ----------------
        m = Mock(gain=37)
        st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}; st.update(m.storage())
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st, pre=m.install)
        await pg.wait_for_timeout(800)
        LAST = f"()=>{{const L={K}.XPP.log;return L.length?L[L.length-1]:null}}"
        async def run(board, prep, score, gain, opt='{}'):
            m.extra['gain'] = gain; n0 = len(m.subs); l0 = await pg.evaluate(f"()=>{K}.XPP.log.length")
            await pg.evaluate(prep); await pg.wait_for_timeout(300)
            for _ in range(20):
                if await pg.evaluate(f"(b)=>!!{K}.LB.E.runs[b]", board): break
                await pg.evaluate(f"()=>{{for(let i=0;i<3;i++){K}.stepFrame(1/30,false,true)}}")
            await pg.wait_for_timeout(300)
            await pg.evaluate(f"([b,s])=>{K}.LB.runEnd(b,s,{opt})", [board, score])
            for _ in range(30):
                await pg.wait_for_timeout(200)
                if len(m.subs) > n0 and await pg.evaluate(f"()=>{K}.XPP.log.length") > l0: break
            return (len(m.subs) > n0, await pg.evaluate(LAST) if await pg.evaluate(f"()=>{K}.XPP.log.length") > l0 else None)
        sent, last = await run('free:landing', f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}", 88, 37)
        ok('(b) free flight landing graded: the pop shows the 37 XP the server granted', sent and last and last['amount'] == 37 and last['reason'].startswith('Landing graded'), last)
        ok('(b) the reason says why the bonus (the server answered top 10)', last and 'Top 10' in last['reason'], last)
        xp = await pg.evaluate(f"()=>{K}.LB.P.xp")
        ok('(b) the local XP follows the server total', xp == m.xp, (xp, m.xp))
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(1500)
        HR = "()=>{const f=document.getElementById('hRkF');return {cs:document.getElementById('hRkCs').textContent,rk:document.getElementById('hRkN').textContent,x:document.getElementById('hRkX').textContent,n:document.getElementById('hRkNext').textContent,v:+document.getElementById('hRkBar').getAttribute('aria-valuenow'),tf:f.style.transform,tr:getComputedStyle(f).transitionProperty,svg:!!document.querySelector('#hRkI svg.rk'),rec:!!document.querySelector('#hRank #hRec')}}"
        h = await pg.evaluate(HR)
        # 1,687 XP: Flight Lead (1,200) to Instructor Pilot (3,500): 487 of 2,300 = 21 percent
        ok('(c) Home: insignia, ACEPILOT, Flight Lead, the server XP, 1,813 to Instructor Pilot', h['svg'] and h['cs'] == 'ACEPILOT' and h['rk'] == 'Flight Lead' and h['x'] == '1,687 XP' and h['n'] == '1,813 XP to Instructor Pilot' and h['rec'], h)
        ok('(c) Home: the bar is filled to 21 percent, on transform with a transition', h['v'] == 21 and h['tf'].startswith('scaleX(0.21') and 'transform' in h['tr'], h)
        await pg.screenshot(path=os.path.join(SHOTS, 'xp_home_844x390.png'))
        await pg.evaluate(f"()=>{{const K={K};K.LB.P.xp=20000;K.LB.ui()}}"); await pg.wait_for_timeout(300)
        h = await pg.evaluate(HR)
        ok('(c) Home: the top rank reads Top Gun, the bar full', h['rk'] == 'Top Gun' and h['n'].startswith('Top rank') and h['v'] == 100, h)
        await pg.evaluate(f"()=>{{const K={K};K.LB.P.xp={m.xp};K.LB.ui()}}")
        sent, last = await run('lesson:steep', f"()=>{{{K}.startLesson('steep',true);{K}.lesBriefSkip()}}", 80, 22)
        ok('(b) a lesson: +22 (whatever the server says), "Lesson: Steep turns"', sent and last and last['amount'] == 22 and last['reason'].startswith('Lesson: Steep turns'), last)
        sent, last = await run('arc:drop', f"()=>{{const K={K};K.pick('c130',1);K.start('drop')}}", 12.5, 41)
        ok('(b) a challenge (the airdrop): +41 "Airdrop"', sent and last and last['amount'] == 41 and last['reason'].startswith('Airdrop'), last)
        sent, last = await run('daily', f"()=>{{const K={K};K.dailyRegion('az');K.dailyKind('landing');localStorage.removeItem('kgeuDaily');K.arcStart('daily')}}", 900, 55, "{secs:120}")
        ok('(b) the daily (a landing day): +55 "Daily challenge"', sent and last and last['amount'] == 55 and last['reason'].startswith('Daily challenge'), last)
        sent, last = await run('daily', f"()=>{{const K={K};K.arcStart('daily')}}", 900, 55, "{secs:120}")
        ok('(b) a practice daily (the official attempt used): nothing sent, no pop', not sent and last is None, (sent, last))
        m.extra['reject'] = 'run of 2.0 s is under the 8 s minimum'
        sent, last = await run('free:landing', f"()=>{{const K={K};K.start('runway')}}", 90, 37)
        ok('(b) a refused run: no pop', sent and last is None, (sent, last))
        m.extra.pop('reject')
        m.offline = True
        sent, last = await run('free:landing', f"()=>{{const K={K};K.start('runway')}}", 90, 37)
        ok('(b) no connection (queued): no pop', not sent and last is None, (sent, last))
        m.offline = False
        # school1 item 9: a device lesson board (climbs): no Worker, XP by its formula at the debrief, banked in kgeuTaskXP
        async def les(lid, frac):
            l0 = await pg.evaluate(f"()=>{K}.XPP.log.length"); x0 = await pg.evaluate("()=>+localStorage.getItem('kgeuTaskXP')||0")
            await pg.evaluate(f"()=>{{const K={K};K.startLesson('{lid}',true);K.lesBriefSkip()}}"); await pg.wait_for_timeout(500)
            for _ in range(3): await pg.evaluate(f"()=>{K}.stepFrame(1/30,false,true)")
            run_ = await pg.evaluate(f"()=>!!{K}.LB.E.runs['lesson:{lid}']")
            await pg.evaluate(f"""(f)=>{{const K={K},G=K.G;let acc=0;G.def.tasks.forEach(t=>{{const w=t.w||0,y=acc+w<=f*100+0.01;if(y)acc+=w;
              G.tasks[t.id]={{kind:'event',ok:y,pts:y?w:0,detail:''}};}});K.gEnd()}}""", frac)
            await pg.wait_for_timeout(700)
            log = await pg.evaluate(f"(n)=>{K}.XPP.log.slice(n)", l0)
            x1 = await pg.evaluate("()=>+localStorage.getItem('kgeuTaskXP')||0")
            line = await pg.evaluate("()=>{const e=document.querySelector('#gradeOv .lbLine');return e?e.textContent:''}")
            return run_, log, x1 - x0, line
        await pg.evaluate("()=>{localStorage.removeItem('kgeuTaskLB');localStorage.removeItem('kgeuTaskXP')}")
        n0 = len(m.subs)
        r, log, dx, line = await les('climbs', 0.7)
        ok('(b9) a device lesson (climbs): one pop, "Lesson: Climbs, descents and turns", a positive amount', len(log) == 1 and log[0]['reason'] == 'Lesson: Climbs, descents and turns' and log[0]['amount'] > 0, log)
        ok('(b9) kgeuTaskXP grows by the amount popped', log and dx == log[0]['amount'], (dx, log))
        ok('(b9) the debrief board line: #1 of 1 on this device, first run', 'Board, this device' in line and '#1 of 1' in line and 'FIRST RUN' in line, line)
        ok('(b9) no Worker run: no token asked, nothing submitted', not r and len(m.subs) == n0, (r, len(m.subs) - n0))
        r, log, dx, line = await les('climbs', 1.0)
        ok('(b9) a second better run: 78 XP (50 x1.25 Hard + 15 best), "Personal best" in the reason', len(log) == 1 and log[0]['amount'] == 78 and log[0]['reason'] == 'Lesson: Climbs, descents and turns  \u00b7  Personal best' and dx == 78, (log, dx))
        ok('(b9) the board line: #1 of 2, personal best', '#1 of 2' in line and 'PERSONAL BEST' in line, line)
        r, log, dx, line = await les('climbs', 0)
        ok('(b9) an F: no pop, no XP banked, the run still on the board (#3 of 3)', not log and dx == 0 and '#3 of 3' in line and 'XP' not in line, (log, dx, line))
        rows = await pg.evaluate(f"()=>{K}.LB.localRows('lesson:climbs').rows.map(x=>x.mode)")
        ok('(b9) the device rows carry the mode (Standard tolerances: hard)', rows == ['hard'] * 3, rows)
        ok('(b9) the Boards picker still lists only the six server lessons', await pg.evaluate(f"()=>!!{K}.LB.BOARDS['lesson:climbs'].local&&!{K}.LB.BOARDS['lesson:steep'].local"))
        ok('(b9) no device lesson submitted to the Worker', not [x for x in m.subs if str(x.get('board', '')).startswith('lesson:') and x.get('board') != 'lesson:steep'], [x.get('board') for x in m.subs])
        ok('(b) no page errors', not [e for e in pg.errs if 'pfs-mock' not in e and 'Failed to fetch' not in e and 'status of 400' not in e], pg.errs[:3])
        await pg.context.close()
        m = Mock(cs=None, gain=37)
        st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}; st.update(m.storage())
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st, pre=m.install)
        await pg.wait_for_timeout(600)
        await pg.evaluate("()=>{const o=document.getElementById('csOv');if(o)o.classList.remove('on')}")
        sent, last = await run('free:landing', f"()=>{{const K={K};K.pick('cessna');K.start('runway')}}", 88, 37)
        ok('(b) no callsign: nothing sent, no pop', not sent and last is None, (sent, last))
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(600)
        h = await pg.evaluate("()=>({cs:document.getElementById('hRkCs').textContent,n:document.getElementById('hRkNext').textContent,none:document.getElementById('hRank').classList.contains('none')})")
        ok('(c) Home with no callsign: Nugget card asks for a callsign, no bar', h['cs'] == 'No callsign yet' and 'Pick a callsign' in h['n'] and h['none'], h)
        await pg.context.close()
        await b.close()
    sys.exit(ok.done('xp_check'))

asyncio.run(main())
