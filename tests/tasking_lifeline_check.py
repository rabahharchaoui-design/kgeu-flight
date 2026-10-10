# Tasking item 3: LIFELINE (C-130H, resupply). A seeded Hard run on AUTO NAV: the briefing, the drop zone moved to
# Hilltop's rolled position (no smoke until they pop it), DROP refused before the smoke call, the route to the IP, the
# smoke in its rolled colour, a wrong colour (Hilltop: not our smoke, a new decoy) then the right one, the drop on the
# green light, Hilltop's call of where the bundle landed, the pickup pass that AUTO flies (a racetrack onto a line
# through the panels, terrain checked), the score lines, 3 to 6 minutes, the card. Then: the drop zone goes home and the
# plain airdrop is as before (red smoke, its own call); three seeds roll three taskings; Easy at 568 (plain lines, the
# reply bar clear of the LOOK pad). Run: .venv/bin/python tests/tasking_lifeline_check.py
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
SMOKE = f"()=>{{const z={K}.DZ;return {{vis:z.smoke.filter(p=>p.visible).length,col:z.smoke[0]&&z.smoke[0].material.color.toArray().map(v=>+v.toFixed(2))}}}}"

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        home = await pg.evaluate(f"()=>[{K}.DROPZ.x,{K}.DROPZ.z]")
        await pg.evaluate(f"()=>{K}.taskStart('lifeline',{{seed:5}})"); await pg.wait_for_timeout(500)
        br = await pg.evaluate("()=>({k:document.getElementById('tkbK').textContent,ac:document.getElementById('tkbAc').textContent,f:[...document.querySelectorAll('#tkbF span b')].map(e=>e.textContent),n:document.querySelectorAll('#tkbSt li').length})")
        ok('the briefing: Resupply, the C-130 out of Luke, four objectives, par to the drop, the run in, wind and the drop height', br['k'] == 'TASKING · RESUPPLY' and 'C-130H' in br['ac'] and br['n'] == 4 and br['f'] == ['PAR TO DROP', 'RUN IN', 'WIND', 'DROP'], br)
        s = await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d,s=K.state();return {{type:s.type,air:!s.onGround,ft:Math.round((s.pos.y-K.groundHeight(s.pos.x,s.pos.z))*3.28),dz:[K.DROPZ.x,K.DROPZ.z],c:[d.c.x,d.c.z],r:Math.hypot(d.c.x-K.LUKE.x,d.c.z-K.LUKE.z),drop:K.MISS.on&&K.MISS.kind}}}}")
        ok('airborne in the C-130 at 1,500 ft; the drop zone is Hilltop\'s, 11 to 18 km from Luke; the airdrop machinery is armed', s['type'] == 'c130' and s['air'] and 1300 < s['ft'] < 1700 and s['dz'] == s['c'] and 11000 <= s['r'] <= 18000 and s['drop'] == 'drop', s)
        await finger(pg, '#tkGo'); await adv(pg, 1)
        sm = await pg.evaluate(SMOKE)
        ok('no smoke over the team until they pop it', sm['vis'] == 0, sm)
        await pg.evaluate(f"()=>{K}.missDrop()")
        ok('DROP before the smoke call is refused, nothing leaves the ramp', not await pg.evaluate(f"()=>{K}.MISS.dropped") and 'smoke first' in await pg.evaluate("()=>document.getElementById('toast').textContent"))
        await until(pg, SHOW, 20)
        t = await pg.evaluate(T)
        ok('Mission Control: Hilltop, its position, route via the IP, the run in heading, 1,000 feet, smoke', any('Hilltop needs resupply' in l.get('text', '') and 'run in heading' in l.get('text', '') and 'N33' in l.get('text', '') for l in t['log']) and t['ask']['opts'] == ['WILCO', 'UNABLE'])
        await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        await finger(pg, '#bAuto'); await adv(pg, 1)
        ok('AUTO NAV: the route on autopilot (labelled AUTO OFF)', await pg.evaluate(f"()=>{K}.state().ap&&{K}.state().ap.mode==='hold'&&document.getElementById('bAutoT').textContent==='AUTO OFF'"))
        await until(pg, f"()=>{K}.task().stage==='smoke'", 200)
        await until(pg, SHOW, 20); await adv(pg, 2)
        sm = await pg.evaluate(SMOKE); d = await pg.evaluate(f"()=>{K}.TASK.d")
        want = {'green': [0.2, 0.72, 0.26], 'yellow': [0.95, 0.83, 0.2], 'violet': [0.55, 0.27, 0.78], 'red': [0.85, 0.13, 0.11]}[d['smoke']]
        ratio = [round(sm['col'][i] / max(sm['col']) / (want[i] / max(want)), 2) for i in range(3)] if sm['col'] and max(sm['col']) > 0 else None
        ok('at the IP: we ask for smoke, Hilltop pops it in its rolled colour', sm['vis'] > 10 and ratio and all(abs(x - 1) < 0.05 for x in ratio), (d['smoke'], sm, ratio))
        await shot(pg, '/tmp/tasking_ll_smoke.png')
        a = await pg.evaluate(T)
        ok('the reply buttons: the right colour and a decoy', sorted(a['ask']['opts']) == sorted([d['smoke'].upper(), d['decoy'].upper()]), a['ask'])
        wrong = d['decoy'].upper()
        await finger(pg, f'#tkReply button[data-k="{wrong}"]'); await until(pg, SHOW, 20)
        t = await pg.evaluate(T)
        ok('the wrong colour: Hilltop says not our smoke, asks again with a new decoy', any('not our smoke' in l.get('text', '') for l in t['log']) and d['smoke'].upper() in t['ask']['opts'] and wrong not in t['ask']['opts'], t['ask'])
        await finger(pg, f'#tkReply button[data-k="{d["smoke"].upper()}"]'); await adv(pg, 1)
        t = await pg.evaluate(T)
        ok('the right colour: cleared to drop', t['stage'] == 'drop' and any('You are cleared to drop' in l.get('text', '') for l in t['log']))
        green = await until(pg, f"()=>{K}.DZ.light==='green'", 200, 0.5)
        ok('the jump lights go green on the run in', green)
        await pg.evaluate(f"()=>{K}.missDrop()"); await adv(pg, 2)
        ok('the load goes', await pg.evaluate(f"()=>{K}.MISS.dropped"))
        await until(pg, f"()=>{K}.task().stage==='pass'", 30)
        await until(pg, f"()=>{K}.TASK.d.dist!=null", 90)
        t = await pg.evaluate(T)
        ok('the bundle lands: Hilltop says how far and which side of the smoke', t['d']['dist'] < 150 and any(l.get('who') == 'Hilltop' and 'Bundle on the ground' in l.get('text', '') for l in t['log']), t['d']['dist'])
        await until(pg, f"()=>{K}.task().done", 260, 2)
        t = await pg.evaluate(T)
        ok('AUTO flies the pickup pass: under 300 ft, within 150 m, Hilltop confirms', t['d'].get('pass') and t['d']['pass']['ft'] < 300 and t['d']['pass']['r'] < 150 and any('Pass confirmed' in l.get('text', '') for l in t['log']), t['d'].get('pass'))
        ok('the pass flew over the ground, never into it', not await pg.evaluate(f"()=>{K}.state().crashed"))
        ok('the whole tasking runs 3 to 6 minutes', 180 <= t['d']['secs'] <= 360, t['d']['secs'])
        r = t['res']
        ok('the score: drop accuracy, time against par, the smoke call (second call), the pass', r and [l[0] for l in r['lines']] == ['Drop from the smoke', 'Time to the drop', 'Smoke call', 'Pickup pass', 'Wind at the drop'] and 'second call' in r['lines'][2][1] and 40 <= r['score'] <= 95, r and (r['score'], r['lines']))
        await pg.wait_for_timeout(3200)
        c = await pg.evaluate("()=>({on:document.getElementById('missOv').classList.contains('on'),t:document.getElementById('mTitle').textContent,retry:document.getElementById('mRetry').textContent})")
        ok('the results card: Lifeline, RETRY LIFELINE', c['on'] and c['t'].startswith('Lifeline: ') and c['retry'] == 'RETRY LIFELINE', c)
        await shot(pg, '/tmp/tasking_ll_card.png')
        # back home: the drop zone and the plain airdrop
        await finger(pg, '#mMenu'); await pg.wait_for_timeout(300)
        ok('MAIN MENU: the drop zone is back where the airdrop has it', await pg.evaluate(f"()=>[{K}.DROPZ.x,{K}.DROPZ.z]") == home)
        await pg.evaluate(f"()=>{K}.mission('drop')"); await adv(pg, 2)
        sm = await pg.evaluate(SMOKE); lg = await pg.evaluate(f"()=>{K}.radioLog().map(l=>l.who)")
        ok('the plain airdrop after it: red smoke at its own drop zone and its own call', sm['vis'] > 10 and sm['col'][0] > sm['col'][1] * 3 and 'Drop Zone Control' in lg and await pg.evaluate(f"()=>{K}.DZ.g.children.length>0&&Math.hypot({K}.DROPZ.x-({home[0]}),{K}.DROPZ.z-({home[1]}))<1"), (sm, lg[-3:]))
        rolls = []
        for sd in (11, 12, 13):
            await pg.evaluate(f"()=>{{{K}.taskStop();{K}.taskStart('lifeline',{{seed:{sd}}})}}")
            rolls.append(await pg.evaluate(f"()=>{{const d={K}.TASK.d;return [Math.round(d.c.x),Math.round(d.c.z),d.smoke,d.wdir,d.wkt,d.par]}}"))
        ok('three seeds, three taskings (team, smoke colour, wind, par)', len({json.dumps(r[:2]) for r in rolls}) == 3 and len({r[3] for r in rolls}) >= 2, rolls)
        await pg.evaluate(f"()=>{K}.taskStop()")
        ok('no console errors', not pg.errs, pg.errs[:3])
        await pg.close()
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('lifeline',{{seed:5}})}}")
        await until(pg, SHOW, 30); await pg.wait_for_timeout(300)
        pl = await pg.evaluate("()=>{const e=document.querySelector('#atc .plain');return e?e.textContent:''}")
        rb = await pg.evaluate("()=>{const a=document.getElementById('tkReply').getBoundingClientRect(),l=document.getElementById('lookPad').getBoundingClientRect();return {a:[a.left,a.right],l:[l.left,l.right],look:getComputedStyle(document.getElementById('lookPad')).display}}")
        ok('Easy: the plain line under Mission Control\'s call', 'drop the bundle from 1,000 ft' in pl, pl)
        e = await pg.evaluate(f"()=>({{hint:document.getElementById('dzHint').classList.contains('on'),dest:{K}.dest&&{K}.dest().name}})")
        ok('Easy: no "head for the red smoke" hint, the waypoint is the IP (not the drop zone)', not e['hint'] and e['dest'] == 'IP Hilltop', e)
        ok('568 wide: the replies stop short of the LOOK pad', rb['look'] == 'none' or rb['a'][1] <= rb['l'][0] - 4, rb)
        await shot(pg, '/tmp/tasking_ll_easy_568.png')
        ok('no console errors (Easy)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('tasking_lifeline_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
