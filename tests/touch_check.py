# Feature 3: touch controls with no tilt anywhere. The left thumb stick flies pitch
# and roll and springs back, the right edge throttle slides, brake holds, settings
# change sensitivity and invert pitch, and no motion permission is ever requested.
# Run: .venv/bin/python tests/touch_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks
ok = Checks()

# fail loudly if anything asks iOS for motion access
SPY = """(()=>{window.__motionAsks=0;
  for(const n of ['DeviceOrientationEvent','DeviceMotionEvent']){
    const E=window[n]||function(){};E.requestPermission=()=>{window.__motionAsks++;return Promise.resolve('granted');};window[n]=E;}
  const add=window.addEventListener;window.__motionListeners=0;
  window.addEventListener=function(t,...a){if(t==='deviceorientation'||t==='devicemotion')window.__motionListeners++;return add.call(this,t,...a);};})()"""

async def pdown(pg, sel, x, y, pid=5):
    await pg.evaluate("""([s,x,y,p])=>document.querySelector(s).dispatchEvent(new PointerEvent('pointerdown',{pointerId:p,clientX:x,clientY:y,bubbles:true}))""", [sel, x, y, pid])
async def pmove(pg, sel, x, y, pid=5):
    await pg.evaluate("""([s,x,y,p])=>document.querySelector(s).dispatchEvent(new PointerEvent('pointermove',{pointerId:p,clientX:x,clientY:y,bubbles:true}))""", [sel, x, y, pid])
async def pup(pg, sel, x=0, y=0, pid=5):
    await pg.evaluate("""([s,x,y,p])=>document.querySelector(s).dispatchEvent(new PointerEvent('pointerup',{pointerId:p,clientX:x,clientY:y,bubbles:true}))""", [sel, x, y, pid])

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        ctx_pg = await page(b, url, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        pg = ctx_pg
        await pg.context.add_init_script(SPY); await pg.reload()
        await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(600)

        html = (await pg.content()).lower()
        ok('no tilt control, prompt or calibration in the page', 'tilt' not in html.replace('tiltedplane', ''),
           [l.strip()[:80] for l in html.splitlines() if 'tilt' in l][:3])
        await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.pickBase('kgeu');window.__kgeu.start('final');}")
        await pg.wait_for_timeout(1200)
        z = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
        cx, cy = z[0] + z[2]*0.5, z[1] + z[3]*0.55
        await pdown(pg, '#stickZone', cx, cy)
        await pg.wait_for_timeout(100)
        vis = await pg.evaluate("()=>{const s=document.getElementById('stick');const r=s.getBoundingClientRect();return [s.classList.contains('on'),r.x+r.width/2,r.y+r.height/2]}")
        ok('stick appears where the left thumb lands', vis[0] and abs(vis[1]-cx) < 2 and abs(vis[2]-cy) < 2, vis)
        await pmove(pg, '#stickZone', cx + 60, cy)          # full right
        await pg.wait_for_timeout(700)
        s = await pg.evaluate("()=>({ail:window.__kgeu.state().ail,elev:window.__kgeu.state().elev,ti:window.__kgeu.touchIn.ail})")
        ok('pushing right rolls right', s['ti'] > 0.8 and s['ail'] > 0.5, s)
        await pmove(pg, '#stickZone', cx, cy + 60)          # pull back
        await pg.wait_for_timeout(700)
        s = await pg.evaluate("()=>({ail:window.__kgeu.state().ail,elev:window.__kgeu.state().elev})")
        ok('pulling down on the stick pitches up (elevator back)', s['elev'] > 0.5, s)
        await pg.evaluate("()=>window.__kgeu.setInvPitch(true)")
        await pg.wait_for_timeout(500)
        s = await pg.evaluate("()=>window.__kgeu.state().elev")
        ok('invert pitch flips the elevator', s < -0.5, s)
        await pg.evaluate("()=>window.__kgeu.setInvPitch(false)")
        await pmove(pg, '#stickZone', cx, cy + 20)
        await pg.evaluate("()=>window.__kgeu.setStickSens(0)"); await pg.wait_for_timeout(400)
        lo = await pg.evaluate("()=>window.__kgeu.state().elev")
        await pg.evaluate("()=>window.__kgeu.setStickSens(4)"); await pg.wait_for_timeout(400)
        hi = await pg.evaluate("()=>window.__kgeu.state().elev")
        ok('sensitivity changes how much a small deflection does', hi > lo * 1.5 and lo > 0, f'{lo:.3f} -> {hi:.3f}')
        await pg.evaluate("()=>window.__kgeu.setStickSens(2)")
        await pup(pg, '#stickZone')
        await pg.wait_for_timeout(700)
        s = await pg.evaluate("()=>({ti:window.__kgeu.touchIn.active,ail:window.__kgeu.touchIn.ail,knob:document.getElementById('knob').style.transform})")
        ok('stick springs back to centre on release', not s['ti'] and s['ail'] == 0 and s['knob'] in ('', 'none'), s)

        # throttle slider
        t = await pg.evaluate("()=>{const r=document.getElementById('thr').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
        tx = t[0] + t[2]/2
        await pdown(pg, '#thr', tx, t[1] + t[3]*0.8, 9)
        await pmove(pg, '#thr', tx, t[1] + t[3]*0.5, 9)
        await pmove(pg, '#thr', tx, t[1] + t[3]*0.1, 9)
        await pup(pg, '#thr', tx, t[1] + t[3]*0.1, 9)
        await pg.wait_for_timeout(300)
        thr = await pg.evaluate("()=>window.__kgeu.state().throttle")
        ok('sliding the throttle up sets power', abs(thr - 0.9) < 0.05, thr)
        await pdown(pg, '#thr', tx, t[1] + t[3]*0.1, 9); await pmove(pg, '#thr', tx, t[1] + t[3]*0.99, 9); await pup(pg, '#thr', tx, t[1] + t[3]*0.99, 9)
        thr = await pg.evaluate("()=>window.__kgeu.state().throttle")
        ok('sliding it down brings it to idle', thr < 0.05, thr)

        # thumb stick and throttle together actually fly the aircraft
        await pg.evaluate("()=>{window.__kgeu.start('final');}"); await pg.wait_for_timeout(800)
        h0 = await pg.evaluate("()=>{const s=window.__kgeu.state();return Math.atan2(s.vel.x,-s.vel.z)}")
        await pdown(pg, '#stickZone', cx, cy, 11); await pmove(pg, '#stickZone', cx + 50, cy, 11)
        for _ in range(8):
            await pg.evaluate("()=>window.__kgeu.ff(0.5)"); await pg.wait_for_timeout(100)
        h1 = await pg.evaluate("()=>{const s=window.__kgeu.state();return Math.atan2(s.vel.x,-s.vel.z)}")
        await pup(pg, '#stickZone', 0, 0, 11)
        ok('holding the stick right turns the aircraft right', h1 - h0 > 0.05, f'{h0:.2f} -> {h1:.2f} rad')

        # brake is a hold button
        await pdown(pg, '#bBrake', 0, 0, 12); await pg.wait_for_timeout(100)
        br = await pg.evaluate("()=>window.__kgeu.touchIn.brake")
        await pup(pg, '#bBrake', 0, 0, 12); await pg.wait_for_timeout(100)
        br2 = await pg.evaluate("()=>window.__kgeu.touchIn.brake")
        ok('brake holds while pressed and lets go', br and not br2)

        # pause, top centre
        await pg.evaluate("()=>document.getElementById('bPause').click()"); await pg.wait_for_timeout(300)
        ok('pause button pauses and shows the pause sheet', await pg.evaluate("()=>window.__kgeu.paused()&&document.getElementById('pauseOv').classList.contains('on')"))
        await pg.evaluate("()=>document.getElementById('pResume').click()")

        # settings persist
        await pg.evaluate("()=>{window.__kgeu.setStickSens(3);window.__kgeu.setInvPitch(true)}")
        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(400)
        T = await pg.evaluate("()=>window.__kgeu.TOUCH")
        ok('sensitivity and invert pitch survive a reload', T['sens'] == 3 and T['inv'] is True, T)
        asks = await pg.evaluate("()=>[window.__motionAsks,window.__motionListeners]")
        ok('no motion permission request and no motion listeners', asks == [0, 0], asks)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('touch_check'))

asyncio.run(main())
