# Real multi touch: one finger holds the stick hard right while a second finger taps
# GEAR, FLAPS UP, FLAPS DN, holds BRAKE and taps VIEW. Every button must work and the
# stick must never let go. Sent through CDP as genuine two point touch events.
# Run: .venv/bin/python tests/multitouch_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()

# record every touch listener put on document or window
SPY = """(()=>{window.__docTouch=[];const add=EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener=function(t,...a){
    const at=(new Error().stack||'').split('\\n').slice(2).join(' ');
    // only the game's own code counts, not the test driver's injected helpers
    if((this===document||this===window||this===document.documentElement||this===document.body)&&/^touch/.test(t)&&at.includes('index.html'))
      window.__docTouch.push(t);
    return add.call(this,t,...a);};})()"""

async def centre(pg, sel):
    return await pg.evaluate("(s)=>{const r=document.querySelector(s).getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}", sel)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuType': 'c130', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.context.add_init_script(SPY); await pg.reload()
        await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(800)
        K = 'window.__kgeu'
        await pg.evaluate(f"()=>{{{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('final');}}")
        await pg.wait_for_timeout(1500)
        cdp = await pg.context.new_cdp_session(pg)
        async def touch(kind, pts):
            await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [
                {'x': x, 'y': y, 'id': i, 'radiusX': 4, 'radiusY': 4, 'force': 1} for i, (x, y) in pts]})
        state = f"()=>{{const s={K}.state();return {{ail:{K}.touchIn.ail,on:document.getElementById('stick').classList.contains('on'),gear:s.gearDown,flap:s.flapIdx,brake:{K}.touchIn.brake,cam:{K}.camMode(),paused:{K}.paused()}}}}"

        z = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}")
        f1 = (z[0], z[1])
        await touch('touchStart', [(1, f1)]); await pg.wait_for_timeout(80)
        f1 = (z[0] + 80, z[1]); await touch('touchMove', [(1, f1)]); await pg.wait_for_timeout(120)
        s = await pg.evaluate(state)
        ok('finger 1 holds the stick right', s['ail'] > 0.5 and s['on'], s)

        async def second(sel, hold_ms=120, during=None):
            c = await centre(pg, sel)
            await touch('touchStart', [(1, f1), (2, (c[0], c[1]))]); await pg.wait_for_timeout(40)
            # finger 1 keeps pushing right while finger 2 is down
            await touch('touchMove', [(1, (f1[0] + 4, f1[1])), (2, (c[0], c[1]))]); await pg.wait_for_timeout(40)
            await touch('touchMove', [(1, f1), (2, (c[0], c[1]))]); await pg.wait_for_timeout(hold_ms)
            mid = await pg.evaluate(state)
            await touch('touchEnd', [(2, (c[0], c[1]))]); await pg.wait_for_timeout(250)   # CDP touchEnd lists the fingers that lift: finger 2 only
            return mid, await pg.evaluate(state)

        async def still(label):
            s = await pg.evaluate(state)
            ok(f'  stick still held right after {label}', s['ail'] > 0.5 and s['on'], s)

        s0 = await pg.evaluate(state)
        _, s1 = await second('#bGear')
        ok('GEAR toggles with the stick held', s1['gear'] != s0['gear'], f"{s0['gear']} -> {s1['gear']}")
        await still('GEAR')
        s0 = s1
        _, s1 = await second('#bFlapUp')
        ok('FLAPS UP steps one notch up', s1['flap'] == s0['flap'] - 1, f"{s0['flap']} -> {s1['flap']}")
        await still('FLAPS UP')
        s0 = s1
        _, s1 = await second('#bFlapDn')
        ok('FLAPS DN steps one notch down', s1['flap'] == s0['flap'] + 1, f"{s0['flap']} -> {s1['flap']}")
        await still('FLAPS DN')
        mid, s1 = await second('#bBrake', 300)
        ok('BRAKE is on while held', mid['brake'], mid)
        ok('BRAKE lets go when the finger lifts', not s1['brake'], s1)
        await still('BRAKE')
        s0 = s1
        _, s1 = await second('#bCam')
        ok('VIEW changes the camera', s1['cam'] != s0['cam'], f"{s0['cam']} -> {s1['cam']}")
        await still('VIEW')
        ok('nothing paused along the way', not s1['paused'], s1)

        await touch('touchEnd', [(1, f1)]); await pg.wait_for_timeout(300)
        s = await pg.evaluate(state)
        ok('stick springs back once finger 1 lifts', s['ail'] == 0, s)

        # which buttons each skill and aircraft gets
        VIS = "()=>['bAuto','bCam','bSensor','bDrop','bGear','bFlapUp','bFlapDn','bBrake'].filter(id=>{const e=document.getElementById(id);return e.offsetParent!==null&&e.getBoundingClientRect().width>0}).join(',')"
        async def shown(skill, t, mode='final'):
            await pg.evaluate(f"()=>{{{K}.setSkill('{skill}');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('{mode}');}}")
            await pg.wait_for_timeout(500)
            return await pg.evaluate(VIS)
        ok('Rookie: only AUTO, VIEW, BRAKE', await shown('rookie', 'c130') == 'bAuto,bCam,bBrake', await shown('rookie', 'c130'))
        ok('Pilot C-130: AUTO, VIEW, GEAR, FLAPS UP/DN, BRAKE', await shown('pilot', 'c130') == 'bAuto,bCam,bGear,bFlapUp,bFlapDn,bBrake', await shown('pilot', 'c130'))
        ok('Pilot F-16: no flaps buttons', await shown('pilot', 'f16') == 'bAuto,bCam,bGear,bBrake', await shown('pilot', 'f16'))
        ok('Pilot Cessna: no GEAR', await shown('pilot', 'cessna') == 'bAuto,bCam,bFlapUp,bFlapDn,bBrake', await shown('pilot', 'cessna'))
        ok('Pilot Alpha: no GEAR', 'bGear' not in await shown('pilot', 'alpha'))
        ok('MQ-9A shows SENSOR', 'bSensor' in await shown('rookie', 'reaper') and 'bSensor' in await shown('pilot', 'reaper'))
        ok('MQ-9B shows SENSOR', 'bSensor' in await shown('pilot', 'mq9b'))
        await pg.evaluate("()=>document.getElementById('bSensor').click()"); await pg.wait_for_timeout(600)
        ok('SENSOR enters the ball view on the MQ-9B', await pg.evaluate(f"()=>{K}.camMode()===2&&{K}.sensorMode()"))
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.mission('drop');}}"); await pg.wait_for_timeout(800)
        drops = await pg.evaluate("()=>[...document.querySelectorAll('#uiroot button')].filter(b=>b.offsetParent!==null&&/DROP/.test(b.textContent)).length")
        ok('C-130 airdrop shows exactly one DROP', drops == 1, drops)

        dt = await pg.evaluate("()=>window.__docTouch")
        ok('no touch listeners on document or window', 'touchmove' not in dt and not dt, dt)
        src = await pg.evaluate("()=>[...document.scripts].map(s=>s.textContent).join('\\n')")
        ok('no document touchmove handler in the source', "document.addEventListener('touchmove'" not in src and "window.addEventListener('touchmove'" not in src)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('multitouch_check'))

asyncio.run(main())
