# Tasking item 5: FINDER (Cessna 172, search and rescue). A seeded Hard run: the briefing, the search box on the White
# Tanks' east slopes with the hiker in it, the 172 airborne east of it at the search height, the box and pattern drawn,
# AUTO NAV flying the legs (the waypoint steps on), the mirror flash (dark beyond 2.6 km, short pulses inside it,
# never steady), a MARK far from him (negative, counted, MARK stays), a MARK over him (the find time, the error), the
# orbit (Ranger 41's time out, AUTO's orbit on the mark, the band and its warning), Ranger 41 asking, REPORT reading the
# mark's coordinates, the score, 3 to 6 minutes, the card. Then three seeds, the night brief (a strobe), Easy at 568
# (the plain line, the flash seen from 3.5 km). Run: .venv/bin/python tests/tasking_finder_check.py
import asyncio, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False
async def shot(pg, path):
    await pg.evaluate("()=>window.__kgeu.stepFrame(0.02,false,false)"); await pg.screenshot(path=path)
T = f"()=>{K}.task()"
SHOW = f"()=>{{const a={K}.task().ask;return !!(a&&a.shown)}}"
# put the 172 at (dx, dz) metres off the hiker at the search height, flying west at 105 kt
PUT = """([dx,dz])=>{const K=window.__kgeu,s=K.state(),d=K.TASK.d;s.pos.x=d.h.x+dx;s.pos.z=d.h.z+dz;s.pos.y=Math.max(s.pos.y,d.altY+1);s.vel.set(-54,0,0);s.quat.setFromEuler(new THREE.Euler(0,Math.PI/2,0,'YXZ'));s.w.set(0,0,0);}"""
# how many 0.1 s frames of n the flash shows, and the most frames in a row
FLASH = """(n)=>{const K=window.__kgeu;let v=0,run=0,best=0;for(let i=0;i<n;i++){K.stepFrame(0.1,false,true);const on=K.TASK.d.fl0.visible;v+=on?1:0;run=on?run+1:0;best=Math.max(best,run);}return [v,best];}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTOD': 'day'})
        await pg.evaluate(f"()=>{K}.taskStart('finder',{{seed:8}})"); await pg.wait_for_timeout(500)
        br = await pg.evaluate("()=>({k:document.getElementById('tkbK').textContent,ac:document.getElementById('tkbAc').textContent,sit:document.getElementById('tkbSit').textContent,f:[...document.querySelectorAll('#tkbF span b')].map(e=>e.textContent),n:document.querySelectorAll('#tkbSt li').length})")
        ok('the briefing: Search and rescue, the 172 east of the White Tanks, three objectives, par to find, search height, legs, wind', br['k'] == 'TASKING · SEARCH AND RESCUE' and 'Cessna 172' in br['ac'] and br['n'] == 3 and br['f'] == ['PAR TO FIND', 'SEARCH', 'PATTERN', 'WIND'] and 'signal mirror' in br['sit'] and 'strobe' not in br['sit'], br)
        s = await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d,s=K.state(),B=d.box;return {{type:s.type,air:!s.onGround,agl:Math.round((s.pos.y-K.groundHeight(s.pos.x,s.pos.z))*3.28),inBox:d.h.x>B.x0&&d.h.x<B.x1&&d.h.z>B.z0&&d.h.z<B.z1,box:[Math.round(B.cx),Math.round(B.cz)],slope:Math.round(K.groundHeight(B.cx,B.cz)),east:s.pos.x>B.x1,objs:K.TASK.objs.length,legs:d.P.length/2}}}}")
        ok('the 172 airborne east of the box; the box on the White Tanks\' east slopes (ground above the valley), the hiker in it; box, pattern, hiker and flash in the world',
           s['type'] == 'cessna' and s['air'] and s['east'] and s['inBox'] and -19400 < s['box'][0] < -17500 and s['slope'] > 30 and s['objs'] == 4 and s['legs'] >= 3, s)
        await finger(pg, '#tkGo'); await until(pg, SHOW, 20)
        t = await pg.evaluate(T)
        ok('Mission Control: an overdue hiker, the box, the pattern height, a signal mirror', any('overdue in the White Tanks' in l.get('text', '') and 'signal mirror' in l.get('text', '') for l in t['log']) and t['ask']['opts'] == ['WILCO', 'UNABLE'])
        await finger(pg, '#tkReply button[data-k="WILCO"]'); await adv(pg, 0.5)
        ok('then MARK waits in the top bar', (await pg.evaluate(T))['ask']['opts'] == ['MARK'])
        await finger(pg, '#bAuto'); await adv(pg, 0.5)
        ok('AUTO NAV flies the pattern at the search height', await pg.evaluate(f"()=>{K}.state().ap&&{K}.state().ap.mode==='hold'&&document.getElementById('bAutoT').textContent==='AUTO OFF'"))
        await until(pg, f"()=>{K}.TASK.d.wp>=1", 200)
        ok('the pattern\'s waypoint steps on as each point is reached', await pg.evaluate(f"()=>{K}.TASK.d.wp>=1"))
        await pg.evaluate(PUT, [4200, 0]); fa = await pg.evaluate(FLASH, 60)
        ok('beyond 2.6 km the flash never shows', fa[0] == 0, fa)
        await pg.evaluate(PUT, [1800, 300]); fa = await pg.evaluate(FLASH, 80)
        ok('inside it: short pulses (a mirror), never steady', fa[0] >= 2 and fa[1] <= 4, fa)
        await pg.evaluate(PUT, [1500, 900]); await adv(pg, 0.2)
        await pg.evaluate(f"()=>{{const K={K};K.TASK.d.fl0.visible=true;K.TASK.d.fl0.material.opacity=1;}}"); await shot(pg, '/tmp/tasking_fd_flash.png')
        await pg.evaluate(f"()=>{K}.taskAnswer('MARK')"); await adv(pg, 0.5)
        t = await pg.evaluate(T)
        ok('a MARK 1.7 km off: negative, a false mark counted, MARK stays', t['d']['falseMark'] == 1 and any('nothing at that mark' in l.get('text', '') for l in t['log']) and t['ask']['opts'] == ['MARK'] and t['stage'] == 'search', t['d']['falseMark'])
        await pg.evaluate(PUT, [55, -30]); await adv(pg, 0.1)
        await pg.evaluate(f"()=>{K}.taskAnswer('MARK')"); await adv(pg, 0.5)
        t = await pg.evaluate(T)
        ok('MARK over him: the find time and the error, the orbit stage', t['stage'] == 'orbit' and t['d']['mark'] and t['d']['mark']['err'] < 100 and t['d']['findT'] > 0 and any('mark, mark, mark' in l.get('text', '') for l in t['log']), t['d'].get('mark'))
        await until(pg, SHOW, 20)
        t = await pg.evaluate(T); eta = t['d']['eta']
        ok('Mission Control: Ranger 41 is on its way (minutes out said), orbit the hiker', 45 <= eta <= 240 and any('Ranger 41, DPS helicopter, is' in l.get('text', '') for l in t['log']), eta)
        await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        await finger(pg, '#bAuto'); await adv(pg, 0.3)
        a = await pg.evaluate(f"()=>{{const s={K}.state();return [s.ap&&s.ap.mode,document.getElementById('bAutoT').textContent]}}")
        if a[0] != 'orbit':   # the first tap took the pattern autopilot off
            await finger(pg, '#bAuto'); await adv(pg, 0.3); a = await pg.evaluate(f"()=>{{const s={K}.state();return [s.ap&&s.ap.mode,document.getElementById('bAutoT').textContent,s.ap&&[s.ap.cx,s.ap.cz]]}}")
        ok('AUTO in the orbit stage: an orbit on the mark', a[0] == 'orbit' and a[1] == 'AUTO OFF', a)
        await adv(pg, 25)
        await pg.evaluate(PUT, [3200, 0]); await adv(pg, 0.3)
        cue = await pg.evaluate("()=>document.getElementById('missS').textContent")
        ok('3.2 km off the hiker: the card says too far', 'Too far' in cue, cue)
        await pg.evaluate(f"()=>{K}.auto()"); await pg.evaluate(f"()=>{K}.auto()")
        await until(pg, f"()=>{K}.task().stage==='report'", 260)
        await until(pg, SHOW, 30); await adv(pg, 1.5)
        await finger(pg, '#tkReply button[data-k="REPORT"]')
        await until(pg, f"()=>{K}.task().done", 30)
        t = await pg.evaluate(T)
        mk = t['d']['mark']; ll = await pg.evaluate(f"()=>{K}.tkLL({mk['x']},{mk['z']})")
        rep = [l['text'] for l in t['log'] if l.get('who') == 'You' and l['text'].startswith('Ranger 41')]
        ok('REPORT reads the mark\'s coordinates to Ranger 41; Ranger 41 has him', rep and ll in rep[0] and any(l.get('who') == 'Ranger 41' and 'We have him' in l.get('text', '') for l in t['log']), (ll, rep[:1]))
        ok('the whole tasking runs 3 to 6 minutes', 180 <= t['d']['secs'] <= 360, t['d']['secs'])
        r = t['res']
        ok('the score: find time, the mark, the orbit (the excursion shows), the report; less 5 for the false mark', r and [l[0] for l in r['lines']] == ['Find time', 'Mark from the hiker', 'Orbit kept', 'Report', 'First flash seen'] and '1 false mark' in r['lines'][1][1] and 50 <= r['score'] <= 97, r and (r['score'], r['lines']))
        await pg.wait_for_timeout(3200)
        c = await pg.evaluate("()=>({on:document.getElementById('missOv').classList.contains('on'),t:document.getElementById('mTitle').textContent,retry:document.getElementById('mRetry').textContent})")
        ok('the results card: Finder, RETRY FINDER', c['on'] and c['t'].startswith('Finder: ') and c['retry'] == 'RETRY FINDER', c)
        rolls = []
        for sd in (31, 32, 33):
            await pg.evaluate(f"()=>{{{K}.taskStop();{K}.taskStart('finder',{{seed:{sd}}})}}")
            rolls.append(await pg.evaluate(f"()=>{{const d={K}.TASK.d;return [Math.round(d.box.cx),Math.round(d.box.cz),Math.round(d.h.x),Math.round(d.h.z),d.P.length,d.wdir]}}"))
        ok('three seeds, three searches (box, hiker, pattern, wind)', len({json.dumps(r[:4]) for r in rolls}) == 3, rolls)
        await pg.evaluate(f"()=>{{{K}.taskStop();{K}.setTOD('night');{K}.taskStart('finder',{{seed:31}})}}"); await pg.wait_for_timeout(300)
        ok('at night the briefing says a strobe', 'strobe after dark' in await pg.evaluate("()=>document.getElementById('tkbSit').textContent"))
        await pg.evaluate(f"()=>{{{K}.taskStop();{K}.setTOD('day')}}")
        ok('no console errors', not pg.errs, pg.errs[:3])
        await pg.close()
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTOD': 'day'})
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('finder',{{seed:8}})}}")
        await until(pg, SHOW, 30); await pg.wait_for_timeout(300)
        pl = await pg.evaluate("()=>{const e=document.querySelector('#atc .plain');return e?e.textContent:''}")
        ok('Easy: the plain line', 'tap MARK' in pl, pl)
        await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        await pg.evaluate(PUT, [3200, 0]); fa = await pg.evaluate(FLASH, 80)
        ok('Easy: the flash shows from 3.2 km (3.5 km range)', fa[0] >= 2, fa)
        await shot(pg, '/tmp/tasking_fd_easy_568.png')
        ok('no console errors (Easy)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('tasking_finder_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
