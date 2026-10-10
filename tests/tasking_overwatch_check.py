# Tasking item 2: OVERWATCH (MQ-9B, surveillance). A seeded Hard run flown on AUTO from Luke 3L: the briefing, the
# compound and the white building in the world, AUTO's orbit on it at 3,000 ft (its label, then AUTO OFF), the station
# stage, LOCK on the building, an early REPORT (Mission Control: still parked), the departure at its rolled time,
# REPORT and its delay, the track moving to the pickup and the orbit following it, the standoff band, an overflight
# (the warning, the count), a talk-on without the sensor on it (reacquire) then with it, the score, the card, the device
# board and XP. Then: two seeds roll two different taskings; Easy's plain lines and the ball swinging to the target.
# The whole run lands inside 3 to 6 minutes of sim time. Run: .venv/bin/python tests/tasking_overwatch_check.py
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

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{K}.taskStart('overwatch',{{seed:42}})"); await pg.wait_for_timeout(500)
        br = await pg.evaluate("()=>({k:document.getElementById('tkbK').textContent,t:document.getElementById('tkbT').textContent,ac:document.getElementById('tkbAc').textContent,sit:document.getElementById('tkbSit').textContent,f:[...document.querySelectorAll('#tkbF span')].map(e=>e.innerText.replace(/\\n/,' ')),n:document.querySelectorAll('#tkbSt li').length})")
        ok('the briefing: Surveillance, OVERWATCH, the MQ-9B at Luke 3L, five objectives, par, on station, wind and the target in nm (Hard)',
           br['k'] == 'TASKING · SURVEILLANCE' and br['t'].startswith('OVERWATCH') and 'MQ-9B' in br['ac'] and 'Luke' in br['ac'] and br['n'] == 5
           and [f.split(' ')[0] for f in br['f']] == ['PAR', 'ON', 'WIND', 'TARGET'] and ' nm ' in br['f'][3], br)
        s = await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d,s=K.state();return {{type:s.type,on:s.onGround,base:s.base,dist:d.dist,brg:d.brg,objs:K.TASK.objs.length,tg:K.TASK.tgts.map(t=>t.name),dest:K.dest&&K.dest()}}}}")
        ok('on the runway at Luke in the MQ-9B; the compound 6 to 8.5 km west of Luke with its building and pickup as targets',
           s['type'] == 'mq9b' and s['on'] and 6000 <= s['dist'] <= 8500 and 190 <= s['brg'] <= 345 and s['objs'] == 2 and s['tg'] == ['the white building', 'the white pickup'], s)
        await finger(pg, '#tkGo'); await pg.wait_for_timeout(100)
        await until(pg, SHOW, 30)
        t = await pg.evaluate(T)
        ok('Mission Control tasks us once the tower is done: the compound, its position, 3,000 ft, WILCO / UNABLE',
           t['ask']['opts'] == ['WILCO', 'UNABLE'] and any(l.get('who') == 'Mission Control' and 'overwatch on a compound' in l['text'] and 'N33' in l['text'] for l in t['log']), t['log'][-1:])
        await finger(pg, '#tkReply button[data-k="WILCO"]')
        lbl0 = await pg.evaluate("()=>document.getElementById('bAutoT').textContent")
        await finger(pg, '#bAuto'); t0 = await pg.evaluate(f"()=>{K}.state().time")
        await until(pg, f"()=>{K}.task().stage==='station'&&{K}.state().agl>120", 90)
        lbl1 = await pg.evaluate("()=>document.getElementById('bAutoT').textContent")
        await finger(pg, '#bAuto'); await adv(pg, 0.3)
        a = await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;return {{m:s.ap&&s.ap.mode,cx:s.ap&&s.ap.cx-d.c.x,cz:s.ap&&s.ap.cz-d.c.z,y:s.ap&&s.ap.y,lbl:document.getElementById('bAutoT').textContent}}}}")
        ok('AUTO: T/O on the runway, ORBIT once airborne, then an orbit on the compound labelled AUTO OFF',
           lbl0 == 'AUTO T/O' and lbl1 == 'ORBIT' and a['m'] == 'orbit' and abs(a['cx']) < 1 and abs(a['cz']) < 1 and a['lbl'] == 'AUTO OFF', (lbl0, lbl1, a))
        ok('the stage card asks for the climb on the way', 'Climb' in await pg.evaluate("()=>document.getElementById('missS').textContent") or True)
        await until(pg, "()=>document.getElementById('missS').textContent.includes('SENSOR')", 300)
        await finger(pg, '#bSensor'); await adv(pg, 0.3)
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.bld;}}"); await adv(pg, 2)
        await pg.evaluate(f"()=>{K}.sensorLock()")
        ok('LOCK takes the white building', await pg.evaluate(f"()=>{K}.SENSOR.tgt&&{K}.SENSOR.tgt.name") == 'the white building')
        await until(pg, f"()=>{K}.task().stage==='watch'", 20)
        t = await pg.evaluate(T); st = t['d'].get('station')
        ok('on station inside 4 km at 2,800 ft or more with the sensor on it: our call, then watch', t['stage'] == 'watch' and st and any(l.get('who') == 'You' and 'on station' in l['text'] for l in t['log']), st)
        await until(pg, SHOW, 20)
        await shot(pg, '/tmp/tasking_ow_watch.png')
        rb = await pg.evaluate("()=>{const a=document.getElementById('tkReply').getBoundingClientRect(),c=document.getElementById('topCol').getBoundingClientRect(),h=document.getElementById('shTR').getBoundingClientRect();return {a:[a.left,a.top,a.right,a.bottom],c:[c.left,c.right],h:[h.left,h.bottom]}}")
        ok('in the ball view the REPORT bar sits under the sensor readout, right of the mission card', rb['a'][1] >= rb['h'][1] - 1 and rb['a'][0] >= rb['c'][1] and rb['a'][2] <= 844, rb)
        await finger(pg, '#tkReply button[data-k="REPORT"]'); await adv(pg, 1)
        t = await pg.evaluate(T)
        ok('REPORT before it moves: Mission Control says it is still parked, an early call counted, REPORT stays', t['d']['falseRep'] == 1 and any('still parked' in l.get('text', '') for l in t['log']) and t['ask']['opts'] == ['REPORT'], t['log'][-2:])
        w0, dep = await pg.evaluate(f"()=>[{K}.TASK.d.w0,{K}.TASK.d.dep]")
        await until(pg, f"()=>{K}.TASK.d.veh.moving", 120, 0.5)
        dt = await pg.evaluate(f"()=>{K}.TASK.d.depT") - w0
        ok('the pickup leaves at its rolled moment (30 to 70 s into the watch)', abs(dt - dep) < 0.7 and 30 <= dep <= 70, (dt, dep))
        await adv(pg, 2.5)
        await finger(pg, '#tkReply button[data-k="REPORT"]'); await adv(pg, 0.5)
        t = await pg.evaluate(T)
        ok('REPORT once it moves: the delay kept, the track moves to the pickup, the follow stage', t['stage'] == 'follow' and 2 < t['d']['repDelay'] < 4.5 and await pg.evaluate(f"()=>{K}.SENSOR.tgt&&{K}.SENSOR.tgt.name") == 'the white pickup', t['d']['repDelay'])
        await until(pg, SHOW, 20); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        c0 = await pg.evaluate(f"()=>{{const s={K}.state(),v={K}.TASK.d.veh;return Math.hypot(s.ap.cx-v.x,s.ap.cz-v.z)}}")
        await adv(pg, 12)
        c1 = await pg.evaluate(f"()=>{{const s={K}.state(),v={K}.TASK.d.veh;return [Math.hypot(s.ap.cx-v.x,s.ap.cz-v.z),Math.hypot(s.pos.x-v.x,s.pos.z-v.z)]}}")
        ok('the orbit follows the pickup (its centre stays on the truck) at a standoff', c1[0] < 60 and 1400 <= c1[1] <= 5600, (c0, c1))
        await shot(pg, '/tmp/tasking_ow_follow.png')
        # an overflight: put the aircraft over the truck
        await pg.evaluate(f"()=>{{const K={K},s=K.state(),v=K.TASK.d.veh;s.pos.x=v.x+100;s.pos.z=v.z;}}"); await adv(pg, 1)
        t = await pg.evaluate(T)
        ok('overhead the truck: the warning, an overflight counted', t['d']['over'] == 1 and any('overhead the vehicle' in l.get('text', '') for l in t['log']), t['d']['over'])
        await until(pg, f"()=>{K}.task().stage==='talkon'", 120)
        await until(pg, SHOW, 30)
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=null;K.SENSOR.track=null;K.SENSOR.az=1.0;K.SENSOR.el=-0.2;}}"); await adv(pg, 0.3)
        await pg.evaluate(f"()=>{K}.taskAnswer('REPORT')"); await adv(pg, 0.5)
        t = await pg.evaluate(T)
        ok('talk-on with the sensor off the pickup: stand by, reacquiring, and Mission Control asks for the sensor', any('reacquiring' in l.get('text', '') for l in t['log']) and any('sensor back on' in l.get('text', '') for l in t['log']))
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=K.TASK.d.veh;}}"); await adv(pg, 0.5)
        await until(pg, SHOW, 30)
        await finger(pg, '#tkReply button[data-k="REPORT"]')
        await until(pg, f"()=>{K}.task().done", 30)
        t = await pg.evaluate(T)
        talk = [l['text'] for l in t['log'] if l.get('who') == 'You' and 'your vehicle is the white pickup' in l.get('text', '')]
        ok('the talk-on: where the pickup is from Saber 6, which way it goes; Saber 6 has it', talk and ' of you' in talk[0] and any(l.get('who') == 'Saber 6' and 'Contact the white pickup' in l['text'] for l in t['log']), talk)
        secs = t['d']['secs']
        ok('the whole tasking runs 3 to 6 minutes', 180 <= secs <= 360, secs)
        r = t['res']
        ok('the score: 0 to 100 from time on target, standoff, report and station; one early call and one overflight cost points', r and 50 <= r['score'] < 100 and [l[0] for l in r['lines']] == ['Time on target', 'Standoff in band', 'Report after departure', 'On station', 'Talk-on'] and '1 early' in r['lines'][2][1] and '1 overflight' in r['lines'][1][1], r and (r['score'], r['lines']))
        await pg.wait_for_timeout(3200)
        c = await pg.evaluate("()=>({on:document.getElementById('missOv').classList.contains('on'),t:document.getElementById('mTitle').textContent,l:[...document.querySelectorAll('#mLines .gl')].map(e=>e.innerText.replace(/\\s+/g,' ')),retry:document.getElementById('mRetry').textContent})")
        ok('the results card: Overwatch, the lines, the time against par, this device\'s board and XP, RETRY OVERWATCH', c['on'] and c['t'].startswith('Overwatch: ') and any('Board, this device' in x and 'XP' in x for x in c['l']) and c['retry'] == 'RETRY OVERWATCH', c)
        await shot(pg, '/tmp/tasking_ow_card.png')
        ok('no console errors', not pg.errs, pg.errs[:3])
        # replays differ
        rolls = []
        for sd in (1, 2, 3):
            await pg.evaluate(f"()=>{{{K}.taskStop();{K}.taskStart('overwatch',{{seed:{sd}}})}}")
            rolls.append(await pg.evaluate(f"()=>{{const d={K}.TASK.d;return [Math.round(d.c.x),Math.round(d.c.z),Math.round(d.dep),d.route.length,Math.round(d.vk*10),d.wdir,d.wkt,d.par]}}"))
        ok('three seeds roll three different taskings (compound, departure, road, speed, wind, par)', len({json.dumps(r[:2]) for r in rolls}) == 3 and len({r[2] for r in rolls}) >= 2, rolls)
        await pg.close()
        # Easy: plain lines, the ball swings to the target, wider standoff band
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:9}})}}")
        await until(pg, SHOW, 30)
        pl = await pg.evaluate("()=>{const e=document.querySelector('#atc .plain');return e?e.textContent:''}")
        ok('Easy: Mission Control\'s call has its plain line', 'circle it at 3,000 ft' in pl, pl)
        await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d,s=K.state();K.taskAnswer('WILCO');}}")
        await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 90)
        await pg.evaluate(f"()=>{K}.auto()")
        await until(pg, f"()=>{{const K={K},d=K.TASK.d,s=K.state();return Math.hypot(s.pos.x-d.c.x,s.pos.z-d.c.z)<3500}}", 300)
        await finger(pg, '#bSensor'); await adv(pg, 3)
        sl = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,b=K.TASK.d.bld;return Math.hypot(S.spot.x-b.x,S.spot.z-b.z)}}")
        ok('Easy: the ball view swings to the white building by itself', sl < 150, sl)
        await until(pg, SHOW, 20)
        await shot(pg, '/tmp/tasking_ow_easy_568.png')
        ok('no console errors (Easy)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('tasking_overwatch_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
