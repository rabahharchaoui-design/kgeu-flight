# Tasking item 4: SHEPHERD (F-16C, escort). A seeded Hard run: the briefing, the lead (the game's own C-130H model,
# props turning, gear up) flying its rolled corridor, the F-16 2 miles behind; Hard's AUTO does not fly it (no
# autoland either); the jet held in the escort position (a test hand: put back in the slot every 0.3 s) to join, then a
# 20 s excursion out of the band (the cue says which way, the score counts it); both traffic calls against where the
# traffic really is (a Cessna and a 737 flying there, at the called clock and range), CONTACT and LOOKING (then "no
# factor"), the weather (Mission Control approves, the lead turns 20 degrees round a buildup, the lane widens, back on
# course), the hand off, the score, 3 to 6 minutes, the card. Then three seeds, and Easy at 568 (AUTO holds the slot,
# the diamond). Run: .venv/bin/python tests/tasking_shepherd_check.py
import asyncio, json, math
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
# the test's hand on the stick: the jet put back in the escort position (o: metres right, aft, up off it) at the lead's
# speed and heading every 0.3 s of sim time, in one page call per chunk
FLY = """([sec,o,stop])=>{const K=window.__kgeu,n=Math.round(sec/0.3);
  for(let i=0;i<n;i++){const d=K.TASK.d;if(!d||K.TASK.done)break;const L=d.L,s=K.state(),f={x:Math.sin(L.h),z:-Math.cos(L.h)},r={x:Math.cos(L.h),z:Math.sin(L.h)};
    const R=300+o[0],B=350+o[1];s.pos.set(L.x+r.x*R-f.x*B,L.y+1.72+o[2],L.z+r.z*R-f.z*B);s.vel.set(f.x*118,0,f.z*118);s.quat.setFromEuler(new THREE.Euler(0,-L.h,0,'YXZ'));s.w.set(0,0,0);
    for(let k=0;k<3;k++)K.stepFrame(0.1,false,true);
    const a=K.TASK.ask;if(stop&&a&&a.shown)break;}
  const a=K.TASK.ask;return {done:K.TASK.done,stage:K.TASK.stage&&K.TASK.stage.id,ask:a&&a.shown?a.opts.map(x=>x.k):null};}"""
async def fly(pg, sec, o=(0, 0, 0), stop=False):
    return await pg.evaluate(FLY, [sec, list(o), stop])

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{K}.taskStart('shepherd',{{seed:3}})"); await pg.wait_for_timeout(500)
        br = await pg.evaluate("()=>({k:document.getElementById('tkbK').textContent,ac:document.getElementById('tkbAc').textContent,sit:document.getElementById('tkbSit').textContent,f:[...document.querySelectorAll('#tkbF span b')].map(e=>e.textContent),n:document.querySelectorAll('#tkbSt li').length})")
        ok('the briefing: Escort, the F-16 2 miles behind the package, the corridor, par, altitude, wind aloft; no weapons', br['k'] == 'TASKING · ESCORT' and 'F-16C' in br['ac'] and br['n'] == 3 and br['f'] == ['CORRIDOR', 'PAR', 'ALTITUDE', 'WIND ALOFT'] and 'No weapons' in br['sit'], br)
        s = await pg.evaluate(f"""()=>{{const K={K},d=K.TASK.d,L=d.L,s=K.state();let props=0,gear=null;
          return {{type:s.type,air:!s.onGround,dist:Math.round(Math.hypot(s.pos.x-L.x,s.pos.z-L.z)),alt:d.alt,lead:!!(L.Lm&&L.Lm.g.parent),props:L.Lm.ps.length,discs:L.Lm.ds.length,legs:d.W.length-1,len:Math.round(d.len)}}}}""")
        ok('the F-16 in the air about 2 miles behind; the lead is the C-130H model with its four props; a three leg corridor of 25 to 35 km',
           s['type'] == 'f16' and s['air'] and 3000 < s['dist'] < 4500 and s['lead'] and s['props'] == 4 and s['legs'] == 3 and 25000 <= s['len'] <= 35000, s)
        await finger(pg, '#tkGo'); await adv(pg, 0.5)
        r0 = await pg.evaluate(f"()=>{K}.TASK.d.L.Lm.ps[0].rotation.z"); await adv(pg, 0.5); r1 = await pg.evaluate(f"()=>{K}.TASK.d.L.Lm.ps[0].rotation.z")
        ok('the lead\'s props turn', abs(r1 - r0) > 1, (r0, r1))
        await finger(pg, '#bAuto'); await adv(pg, 0.3)
        a = await pg.evaluate(f"()=>({{ap:{K}.state().ap,lbl:document.getElementById('bAutoT').textContent,toast:document.getElementById('toast').textContent}})")
        ok('Hard: AUTO says hand fly and engages nothing (never an autoland)', a['ap'] is None and a['lbl'] == 'HAND FLY' and 'by hand' in a['toast'], a)
        await until(pg, SHOW, 20); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        t = await pg.evaluate(T)
        ok('Mission Control names the package, its range and altitude; Herky 21 checks in', any('Herky 21 is your package' in l.get('text', '') for l in t['log']))
        await fly(pg, 6)
        t = await pg.evaluate(T)
        ok('in the escort position for 4 s: joined, Herky 21 has us', t['stage'] == 'escort' and t['d']['join'] is not None and any('welcome aboard' in l.get('text', '') for l in t['log']), (t['stage'], t['d'].get('join')))
        await fly(pg, 10)
        cue = await pg.evaluate("()=>document.getElementById('missS').textContent")
        ok('the card says in position', 'In position' in cue, cue)
        await fly(pg, 20, (900, 0, 120))
        cue = await pg.evaluate("()=>document.getElementById('missS').textContent")
        ok('900 m wide and 400 ft high: out of the band, the cue says wide and high', 'Wide' in cue and 'high' in cue, cue)
        # through the escort, answering the calls
        seen = {}
        for _ in range(400):
            f = await fly(pg, 30, stop=True)
            if f['done'] or f['stage'] == 'handoff': break
            if not f['ask']: continue
            t = await pg.evaluate(T)
            if t['ask'] and t['ask']['shown'] and t['ask']['opts'][0] == 'CONTACT':
                n = 1 if 'c1' not in seen else 2
                if n not in seen.values() or True:
                    tf = await pg.evaluate(f"""()=>{{const K={K},d=K.TASK.d,T=d.tfc[d.tfc.length-1],s=K.state(),h=d.L.h;   // the test's hand holds the jet on the lead's heading
                      let rel=Math.atan2(T.x-s.pos.x,-(T.z-s.pos.z))-h;rel=((rel%(2*Math.PI))+2*Math.PI)%(2*Math.PI);return {{clk:rel*6/Math.PI,mi:Math.hypot(T.x-s.pos.x,T.z-s.pos.z)/1609,vis:T.g.visible,inScene:!!T.g.parent,dy:(T.y-s.pos.y)*3.28}}}}""")
                    call = [l['text'] for l in t['log'] if 'traffic,' in l.get('text', '')][-1]
                    said = int(call.split('traffic, ')[1].split(' ')[0]); said_mi = int(call.split("o'clock, ")[1].split(' ')[0])
                    ok(f'traffic call {len(seen) + 1}: the aircraft is really there, at the called clock and range ({call[:60]}...)', tf['inScene'] and tf['vis'] and min(abs(tf['clk'] - said), 12 - abs(tf['clk'] - said)) < 1.2 and abs(tf['mi'] - said_mi) < 1.2, (said, said_mi, tf))
                    k = 'CONTACT' if not seen else 'LOOKING'
                    seen['c%d' % (len(seen) + 1)] = k
                    await pg.evaluate(f"()=>{K}.taskAnswer('{k}')")
            elif t['ask'] and t['ask']['shown']:
                await pg.evaluate(f"()=>{K}.taskAnswer('{t['ask']['opts'][0]}')")
        t = await pg.evaluate(T)
        ok('both traffic calls answered: CONTACT, then LOOKING and Mission Control\'s no factor', len(seen) == 2 and any('no factor' in l.get('text', '') for l in t['log']), seen)
        dev = [l for l in t['log'] if 'Deviation 20' in l.get('text', '')]
        ok('weather: Mission Control approves 20 degrees round the buildup, Herky 21 turns and later is back on course; the buildup is in the world',
           dev and any('for weather' in l.get('text', '') for l in t['log']) and any('back on course' in l.get('text', '') for l in t['log']) and await pg.evaluate(f"()=>!!({K}.TASK.d.cloud&&{K}.TASK.d.cloud.parent&&{K}.TASK.d.cloud.children.length>=12)"), dev[:1])
        await fly(pg, 8)
        await until(pg, f"()=>{K}.task().done", 30)
        t = await pg.evaluate(T)
        ok('the hand off: Herky 21 thanks us, Mission Control releases us', any('You are released' in l.get('text', '') for l in t['log']) and t['done'])
        ok('the whole tasking runs 3 to 6 minutes', 180 <= t['d']['secs'] <= 360, t['d']['secs'])
        r = t['res']; k = r and float(r['lines'][0][1].split(' %')[0])
        ok('the score: escort position held (the excursion costs about 20 s), the corridor, the join', r and [l[0] for l in r['lines']] == ['Escort position held', 'In the corridor', 'Join', 'Traffic called', 'Weather'] and 80 <= k <= 95 and 75 <= r['score'] <= 96 and r['lines'][3][1] == 'contact, looking', r and (r['score'], r['lines']))
        await pg.wait_for_timeout(3200)
        c = await pg.evaluate("()=>({on:document.getElementById('missOv').classList.contains('on'),t:document.getElementById('mTitle').textContent,retry:document.getElementById('mRetry').textContent})")
        ok('the results card: Shepherd, RETRY SHEPHERD', c['on'] and c['t'].startswith('Shepherd: ') and c['retry'] == 'RETRY SHEPHERD', c)
        rolls = []
        for sd in (21, 22, 23):
            await pg.evaluate(f"()=>{{{K}.taskStop();{K}.taskStart('shepherd',{{seed:{sd}}})}}")
            rolls.append(await pg.evaluate(f"()=>{{const d={K}.TASK.d;return [d.W.map(w=>Math.round(w.x/100)),d.alt,Math.round(d.devAt),d.devSide,d.t1c,d.t2c,d.wdir]}}"))
        ok('three seeds, three corridors (route, altitude, weather, traffic, wind)', len({json.dumps(r[0]) for r in rolls}) == 3, rolls)
        await pg.evaluate(f"()=>{K}.taskStop()")
        ok('stopped: the lead, the traffic and the buildup leave the world', await pg.evaluate(f"()=>{K}.TASK.objs.length===0"))
        ok('no console errors', not pg.errs, pg.errs[:3])
        await pg.close()
        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('shepherd',{{seed:3}})}}")
        await adv(pg, 1)
        ok('Easy: a diamond marks the escort position', await pg.evaluate(f"()=>!!({K}.TASK.d.mk&&{K}.TASK.d.mk.visible)"))
        await pg.evaluate(f"()=>{K}.auto()"); await adv(pg, 0.5)
        ok('Easy: AUTO holds the slot (labelled AUTO OFF)', await pg.evaluate(f"()=>{K}.state().ap&&{K}.state().ap.mode==='hold'&&document.getElementById('bAutoT').textContent==='AUTO OFF'"))
        await until(pg, f"()=>{K}.task().stage==='escort'", 150)
        ok('Easy: AUTO joins inside the par and a half', await pg.evaluate(f"()=>{K}.TASK.d.join!=null&&{K}.TASK.d.join<90"), await pg.evaluate(f"()=>{K}.TASK.d.join"))
        await adv(pg, 30)
        ok('Easy: in the band on AUTO, the diamond hidden while there', await pg.evaluate(f"()=>{K}.TASK.d.inS/{K}.TASK.d.inT>0.9&&!{K}.TASK.d.mk.visible"))
        await shot(pg, '/tmp/tasking_sh_easy_568.png')
        ok('no console errors (Easy)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('tasking_shepherd_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
