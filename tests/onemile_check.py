# 1 mile final (session "onemile"): the start option on the fly screen and the pause sheet,
# every aircraft at both bases in Easy and Hard (lined up on the centre line, about 300 ft on
# the 3 degree path, at that aircraft's approach speed; Easy already configured to land, Hard
# set up like the 3 mile final), Easy lands it by itself, Restart comes back to it, the choice is saved, and the
# 1 mile arcade landing challenge with its own best score. iPhone landscape.
# Run: .venv/bin/python tests/onemile_check.py [--shots]
import asyncio, math, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15, IPHONE_SE, ROOT
ok = Checks()
K = "window.__kgeu"
TYPES = ['cessna', 'alpha', 'reaper', 'mq9b', 'f16', 'c130']
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'onemile')
SAVE = '--shots' in sys.argv
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/30,false,true)}"

async def shot(pg, name):
    if SAVE:
        os.makedirs(SHOTS, exist_ok=True); await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))

# where the aircraft is against its base's landing runway: metres before the aim point, off the
# centre line, height above the field, heading error, indicated airspeed against its approach speed
GEOM = """()=>{const K=window.__kgeu,s=K.state(),B=K.BASES[s.base],h=B.hdg*Math.PI/180,f=B.fin(0),dx=s.pos.x-f[0],dz=s.pos.z-f[1];
  const along=-(dx*Math.sin(h)-dz*Math.cos(h)),off=dx*Math.cos(h)+dz*Math.sin(h),e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');
  const T=K.TYPES[s.type],hd=((-e.y-h)*180/Math.PI+540)%360-180;
  return {along:Math.round(along),off:Math.round(off),ft:Math.round(s.agl*3.28084),hdg:+hd.toFixed(1),kt:Math.round(s.ias*1.943844),vapp:Math.round(T.vapp*1.943844),
    gear:s.gearDown,flap:s.flapIdx,land:T.landFlap,retract:!!T.retract,mode:s.mode,spawn:s.spawn,onGround:s.onGround}}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # ---- the option on the fly screen and in the pause sheet, both phone sizes ----
        for vp in (IPHONE_15, IPHONE_SE):
            W = vp['width']
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
            await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(400)
            c = await pg.evaluate("""()=>[...document.querySelectorAll('#sFly [data-pos]')].map(b=>{const r=b.getBoundingClientRect();return {p:b.dataset.pos,t:b.textContent.trim(),h:r.height,w:r.width,x:r.x}})""")
            ok(f'{W}: fly screen offers Runway, Ramp, 1 mi final, 3 mi final', [x['t'] for x in c] == ['Runway', 'Ramp', '1 mi final', '3 mi final'], [x['t'] for x in c])
            ok(f'{W}: every start chip is a 44 px target that fits', all(x['h'] >= 44 and x['w'] >= 56 for x in c), [(x['t'], round(x['w'])) for x in c])
            fit = await pg.evaluate("()=>{const s=document.getElementById('sFly'),g=document.getElementById('bGo').getBoundingClientRect();return s.scrollHeight<=s.clientHeight+1&&g.right<=innerWidth&&g.bottom<=innerHeight}")
            ok(f'{W}: fly screen still fits, GO on screen', fit)
            await finger(pg, '#sFly [data-pos="final1"]'); await pg.wait_for_timeout(200)
            s = await pg.evaluate("()=>({ls:localStorage.getItem('kgeuPos'),sum:document.getElementById('sumLine').textContent})")
            ok(f'{W}: choosing it saves it and the summary says 1 mile final', s['ls'] == 'final1' and 'on 1 mile final' in s['sum'], s)
            if W == 844: await shot(pg, 'fly_844')
            await pg.reload(); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(1500)
            await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(300)
            sel = await pg.evaluate("()=>[...document.querySelectorAll('#sFly [data-pos].sel')].map(b=>b.dataset.pos)")
            ok(f'{W}: still chosen after reopening', sel == ['final1'], sel)
            await finger(pg, '#bGo'); await pg.wait_for_timeout(1500)
            g = await pg.evaluate(GEOM)
            ok(f'{W}: GO starts on 1 mile final', g['spawn'] == 'final1' and 1700 < g['along'] < 2000, g)
            await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(500)
            c = await pg.evaluate("""()=>[...document.querySelectorAll('#pauseOv [data-pos]')].map(b=>{const r=b.getBoundingClientRect();return {t:b.textContent.trim(),h:r.height,w:r.width,sel:b.classList.contains('sel')}})""")
            ok(f'{W}: pause sheet offers it too, selected', [x['t'] for x in c] == ['Runway', 'Ramp', '1 mi final', '3 mi final'] and c[2]['sel'] and all(x['h'] >= 44 for x in c), c)
            if W == 667: await shot(pg, 'pause_667')
            await pg.evaluate(f"()=>{K}.stepFrame(1/30,false,true)")
            await finger(pg, '#pRestart'); await pg.wait_for_timeout(800)
            g = await pg.evaluate(GEOM)
            ok(f'{W}: Restart comes back to 1 mile final', g['spawn'] == 'final1' and 1700 < g['along'] < 2000, g)
            ok(f'{W}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        # ---- every aircraft, both bases, both modes ----
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
        for skill in ('rookie', 'pilot'):
            M = 'Easy' if skill == 'rookie' else 'Hard'
            for base in ('kgeu', 'luke'):
                for t in TYPES:
                    await pg.evaluate(f"()=>{{{K}.setSkill('{skill}');{K}.pick('{t}');{K}.pickBase('{base}');{K}.start('final1')}}")
                    await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,true)")
                    g = await pg.evaluate(GEOM)
                    tag = f'{M} {base} {t}'
                    good = abs(g['along'] - 1852) < 60 and abs(g['off']) < 5 and 280 <= g['ft'] <= 350 and abs(g['hdg']) < 1 and abs(g['kt'] - g['vapp']) <= 10
                    ok(f'{tag}: 1 nm out on the centre line, {g["ft"]} ft, {g["kt"]} kt (approach {g["vapp"]} kt)', good, g)
                    if skill == 'rookie':
                        ok(f'{tag}: Easy: gear down, landing flaps', g['gear'] and g['flap'] == g['land'], g)
                    else:
                        ok(f'{tag}: Hard: set up like the 3 mile final (gear down, approach flaps)', g['gear'] and g['flap'] <= g['land'], g)
                    # the first 10 s hands off are no worse than the same aircraft's 3 mile final: glide path
                    # deviation and distance off the centre line, compared against a 3 mile start flown the same way
                    DEV = GEOM.replace('return {', 'return {dev:Math.round(s.agl*3.28084-along*Math.tan(3*Math.PI/180)*3.28084),')
                    # the same still air for both, so the comparison is like for like; the spawn trims for the wind
                    # it was given, so trim again for the still air
                    CALM = "()=>{const K=window.__kgeu,s=K.state();s.windKt=0;s.gustAmp=0;s.gust=0;s.gustTarget=0;K.trimSpawn(-3*Math.PI/180);}"
                    await pg.evaluate(f"()=>{K}.start('final1')"); await pg.evaluate(CALM)
                    await pg.evaluate(STEP, 300); a1 = await pg.evaluate(DEV); c1 = await pg.evaluate(f"()=>{K}.state().crashed")
                    await pg.evaluate(f"()=>{K}.start('final')"); await pg.evaluate(CALM); await pg.evaluate(STEP, 300); a3 = await pg.evaluate(DEV)
                    ok(f'{tag}: 10 s hands off, no worse than the 3 mile final (path {a1["dev"]:+} ft vs {a3["dev"]:+} ft, {a1["off"]} m vs {a3["off"]} m off)',
                       not c1 and not a1['onGround'] and abs(a1['dev']) <= abs(a3['dev']) + 60 and abs(a1['off']) <= abs(a3['off']) + 30, (a1, a3))
                    await pg.evaluate(f"()=>{K}.start('final1')"); await pg.evaluate(STEP, 1)
                    if t == 'c130' and skill == 'rookie' and base == 'kgeu': await pg.evaluate(f"()=>{K}.stepFrame(1/60)"); await shot(pg, 'easy_c130_final1')
                    if t == 'f16' and skill == 'pilot' and base == 'luke':
                        await pg.evaluate(f"()=>{K}.stepFrame(1/60)"); await shot(pg, 'hard_f16_luke_start')
        ok('no page errors (all aircraft)', not pg.errs, pg.errs[:3])
        await pg.context.close()
        # ---- the 1 mile arcade landing challenge, its own best score ----
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(500)
        cards = await pg.evaluate("()=>[...document.querySelectorAll('#arcCards .mcard b')].map(b=>b.textContent)")
        ok('arcade lists the 1 mile landing challenge next to the 5 mile one', 'Landing challenge' in cards and '1 mile landing challenge' in cards
           and cards.index('1 mile landing challenge') == cards.index('Landing challenge') + 1, cards)
        await shot(pg, 'arcade')
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.arcStart('landing1')}}"); await pg.evaluate(STEP, 2)
        g = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),e=K.RWY_ENDS.find(e=>e.rwy.code==='KGEU'&&e.num==='1'),d=Math.hypot(s.pos.x-e.x,s.pos.z-e.z);
          return {d:Math.round(d),ft:Math.round(s.agl*3.28084),kt:Math.round(s.ias*1.943844),vapp:Math.round(K.TYPES.cessna.vapp*1.943844),gear:s.gearDown,flap:s.flapIdx}}""")
        ok('1 mile challenge starts 1 nm out, about 300 ft, at approach speed', abs(g['d'] - 1852) < 30 and 280 <= g['ft'] <= 360 and abs(g['kt'] - g['vapp']) <= 10, g)
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(80):
            await pg.evaluate(STEP, 150)
            if await pg.evaluate(f"()=>{K}.ARC.done||{K}.state().crashed"): break
        await pg.wait_for_timeout(3500)
        await pg.wait_for_timeout(3000)
        best = await pg.evaluate(f"()=>{{const s=JSON.parse(localStorage.getItem('kgeuScores')||'{{}}').best||{{}};return {{one:s['arc:landing1']||null,five:s['arc:landing']||null,title:document.getElementById('aTitle').textContent}}}}")
        ok('the 1 mile challenge scores under its own best, apart from the 5 mile one', best['one'] is not None and best['five'] is None, best)
        await shot(pg, 'arcade_result')
        ok('no page errors (arcade)', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('onemile_check'))
asyncio.run(main())
