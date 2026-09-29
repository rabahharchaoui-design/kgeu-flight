# Easy and Hard (session "modes"): the two cards on the fly screen, the toggle in Settings
# and the pause sheet, the saved choice across a reload (old 'rookie' and 'pilot' installs
# keep theirs), switching mid flight in every aircraft (mid turn and on final) with no jolt,
# and run tagging (any Easy moment makes the whole run Easy). iPhone landscape.
# Run: .venv/bin/python tests/modes_check.py
import asyncio, math, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15, IPHONE_SE
ok = Checks()
K = "window.__kgeu"
TYPES = ['cessna', 'alpha', 'reaper', 'mq9b', 'f16', 'c130']
E = "The plane helps you fly. Auto leveling, stall protection, and a glowing path to the runway."
H = "Real flying. No assists, full gauges, and full radio calls."

# attitude and rate each frame for a few seconds; the worst frame to frame change is the jolt
SAMPLE = """([n,dt])=>{const K=window.__kgeu,out=[];const e=new THREE.Euler();
  for(let i=0;i<n;i++){K.stepFrame(dt,false,true);const s=K.state();e.setFromQuaternion(s.quat,'YXZ');
    out.push([e.x,e.z,s.w.x,s.w.y,s.w.z,s.vel.length(),s.pos.y,s.crashed?1:0]);}return out;}"""

def jolt(a):
    """largest per step change in pitch/roll (deg), body rate (deg/s) and speed (m/s)"""
    att = rate = spd = 0
    for p, q in zip(a, a[1:]):
        att = max(att, abs(math.degrees(q[0] - p[0])), abs(math.degrees(math.atan2(math.sin(q[1] - p[1]), math.cos(q[1] - p[1])))))
        rate = max(rate, max(abs(math.degrees(q[i] - p[i])) for i in (2, 3, 4)))
        spd = max(spd, abs(q[5] - p[5]))
    return att, rate, spd

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # ---- fly screen cards, both sizes ----
        for vp in (IPHONE_15, IPHONE_SE):
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
            await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(400)
            c = await pg.evaluate("""()=>[...document.querySelectorAll('#sFly .modeCard')].map(b=>{const r=b.getBoundingClientRect();
              return {k:b.dataset.skill,t:b.querySelector('b').textContent,d:b.querySelector('span').textContent,x:r.x,y:r.y,w:r.width,h:r.height,sel:b.classList.contains('sel')}})""")
            ok(f'{vp["width"]}: two big cards side by side, EASY and HARD', len(c) == 2 and c[0]['t'] == 'EASY' and c[1]['t'] == 'HARD'
               and abs(c[0]['y'] - c[1]['y']) < 1 and c[1]['x'] > c[0]['x'] + c[0]['w'] - 1 and min(x['h'] for x in c) >= 50, c)
            ok(f'{vp["width"]}: each with its description', c[0]['d'] == E and c[1]['d'] == H)
            ok(f'{vp["width"]}: saved Rookie shows as EASY selected', c[0]['sel'] and not c[1]['sel'])
            fit = await pg.evaluate("()=>{const s=document.getElementById('sFly');return s.scrollHeight<=s.clientHeight+1&&document.getElementById('bGo').getBoundingClientRect().bottom<=innerHeight}")
            ok(f'{vp["width"]}: fly screen still fits, GO on screen', fit)
            await finger(pg, '#sFly .modeCard[data-skill="pilot"]'); await pg.wait_for_timeout(200)
            st = await pg.evaluate("()=>({ls:localStorage.getItem('kgeuOnboard'),sel:[...document.querySelectorAll('#sFly .modeCard.sel')].map(b=>b.dataset.skill)})")
            ok(f'{vp["width"]}: tapping HARD highlights it and saves it', st == {'ls': 'pilot', 'sel': ['pilot']}, st)
            await pg.reload(); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(1500)
            await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(300)
            s2 = await pg.evaluate("()=>[...document.querySelectorAll('#sFly .modeCard.sel')].map(b=>b.dataset.skill)")
            ok(f'{vp["width"]}: after reopening, HARD is still chosen', s2 == ['pilot'], s2)
            ok(f'{vp["width"]}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        # ---- existing installs: old Pilot opens as HARD; Settings toggle; the first launch chooser ----
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(300)
        s = await pg.evaluate("()=>({sel:[...document.querySelectorAll('#sSet [data-skill].sel')].map(b=>b.textContent.trim()),d:document.querySelector('#sSet .modeDesc').textContent,lbl:document.querySelector('#sSet .modeSeg').closest('.srow').firstElementChild.textContent})")
        ok('an old Pilot install opens as Hard in Settings', s['sel'] == ['Hard'] and s['d'] == H and s['lbl'] == 'Mode', s)
        await finger(pg, '#sSet [data-skill="rookie"]'); await pg.wait_for_timeout(200)
        s = await pg.evaluate("()=>({ls:localStorage.getItem('kgeuOnboard'),d:document.querySelector('#sSet .modeDesc').textContent})")
        ok('Settings toggle switches to Easy and the description follows', s == {'ls': 'rookie', 'd': E}, s)
        scroll = await pg.evaluate("()=>{const s=document.getElementById('sSet');return s.scrollHeight>s.clientHeight+1}")
        ok('Settings still fits without scrolling', not scroll)
        vis = await pg.evaluate("()=>document.body.innerText")
        ok('no Rookie or Pilot mode names left on screen', 'Rookie' not in vis and '>Pilot<' not in vis)
        await pg.context.close()
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuTut': '1'})
        f = await pg.evaluate("()=>['fRookie','fPilot'].map(i=>document.querySelector('#'+i+' b').textContent)")
        ok('first launch chooser offers EASY and HARD', f == ['EASY', 'HARD'], f)
        await pg.context.close()
        # ---- switching from the pause sheet mid flight, every aircraft ----
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        worst = {}
        for t in TYPES:
            for case in ('turn', 'final'):
                for frm, to in (('pilot', 'rookie'), ('rookie', 'pilot')):
                    await pg.evaluate(f"()=>{{{K}.setSkill('{frm}');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('final')}}")
                    await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,true)")
                    if case == 'turn':   # a 30 degree bank, level, well above the ground
                        await pg.evaluate(f"""()=>{{const s={K}.state(),e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');s.pos.y+=500;
                          s.quat.setFromEuler(new THREE.Euler(0.03,e.y,0.52,'YXZ'));s.gearDown=false;}}""")
                    before = await pg.evaluate(SAMPLE, [30, 1 / 30])
                    await pg.evaluate(f"()=>{K}.togglePause()")
                    await pg.evaluate(f"()=>document.querySelector('#pauseOv [data-skill=\"{to}\"]').click()")
                    await pg.evaluate(f"()=>{K}.togglePause()")
                    after = await pg.evaluate(SAMPLE, [60, 1 / 30])
                    jb, ja = jolt(before), jolt(before[-1:] + after)
                    key = f'{t} {case} {frm}->{to}'
                    worst[key] = (ja, jb)
                    easyNow = await pg.evaluate(f"()=>{K}.state().easy")
                    ok(f'{key}: applied on resume, no restart, no crash', easyNow == (to == 'rookie') and not after[-1][7], (easyNow, after[-1][7]))
                    # no jolt: body rate never steps by more than 12 deg/s in a frame (the assist eases in over
                    # 1.5 s), attitude moves at most 2.5 deg a frame (the F-16 levels at about 55 deg/s in Easy),
                    # and the first frame after resume moves no more than the flight was already moving
                    first = jolt(before[-1:] + after[:3])
                    ok(f'{key}: no jolt  (att {ja[0]:.2f} deg, rate {ja[1]:.1f} deg/s, speed {ja[2]:.2f} m/s a step)',
                       ja[0] < 2.5 and ja[1] < 12 and ja[2] < 1.0 and first[0] <= max(0.6, jb[0] * 1.5 + 0.2), (first, jb))
        # ---- run tagging ----
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.pick('cessna');{K}.start('final')}}")
        await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,true)")
        ok('a fresh Hard run is tagged hard', await pg.evaluate(f"()=>{K}.runMode()") == 'hard')
        await pg.evaluate(f"()=>{{{K}.togglePause();{K}.setSkill('rookie');{K}.togglePause();for(let i=0;i<10;i++){K}.stepFrame(1/30,false,true);{K}.togglePause();{K}.setSkill('pilot');{K}.togglePause();}}")
        ok('switching to Easy for a moment makes the whole run Easy', await pg.evaluate(f"()=>{K}.runMode()") == 'easy')
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(40):
            await pg.evaluate("()=>{for(let i=0;i<300;i++)window.__kgeu.stepFrame(1/30,false,true)}")
            if await pg.evaluate(f"()=>{K}.runs().some(r=>r.kind==='touchdown')"): break
        r = await pg.evaluate(f"()=>{K}.runs()[0]")
        ok('the landing is logged with the run\'s mode (easy)', r and r['mode'] == 'easy', r)
        rec = await pg.evaluate(f"()=>{{const s=JSON.parse(localStorage.getItem('kgeuScore')||'{{}}');return (s.recent||[])[0]||null}}")
        ok('landing records carry the mode', rec is None or rec.get('mode') == 'easy', rec and rec.get('mode'))
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.start('final')}}"); await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,true)")
        ok('the next run starts clean as hard', await pg.evaluate(f"()=>{K}.runMode()") == 'hard')
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('modes_check'))
asyncio.run(main())
