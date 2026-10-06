# Phone2 item 6: flap, gear, trim and autopilot changes never show in the centre of the screen.
# They show as a small readout beside the throttle (left of the dock, level with the throttle)
# for about 2 s, then fade. Every aircraft, Easy and Hard, landscape and portrait; the centre of
# the screen stays clear through an autoland. Run: .venv/bin/python tests/sidetoast_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone2', 'item6')
SIDE = """()=>{const e=document.getElementById('sideToast'),r=e.getBoundingClientRect(),t=document.getElementById('thr').getBoundingClientRect(),d=document.getElementById('dock').getBoundingClientRect();
  const cs=getComputedStyle(e);return {on:e.classList.contains('on'),text:e.textContent,op:+cs.opacity,x:r.x,y:r.y,w:r.width,h:r.height,
    cx:r.x+r.width/2,cy:r.y+r.height/2,thr:[t.x,t.y,t.width,t.height],dock:[d.x,d.y,d.width,d.height],W:innerWidth,H:innerHeight,
    centre:Math.abs(r.x+r.width/2-innerWidth/2)<innerWidth*0.2&&Math.abs(r.y+r.height/2-innerHeight/2)<innerHeight*0.2,
    bigcfg:!!document.getElementById('bigcfg'),
    btns:[...document.querySelectorAll('#dock button')].map(b=>b.getBoundingClientRect()).filter(q=>q.width).map(q=>[q.x,q.y,q.width,q.height])}}"""
def beside(s):
    # right of the screen centre, clear of the throttle and the dock, level with the throttle
    right_of_centre = s['cx'] > s['W'] * 0.55
    clear_thr = s['x'] + s['w'] <= s['thr'][0] + 0.5
    # phone3: clear of every dock button (it may sit in the dock's empty corner beside them), and out of the centre third
    clear_dock = all(s['x'] + s['w'] <= b[0] + 0.5 or s['x'] >= b[0] + b[2] - 0.5 or s['y'] + s['h'] <= b[1] + 0.5 or s['y'] >= b[1] + b[3] - 0.5 for b in s['btns'])
    clear_mid = s['x'] >= s['W'] * 2 / 3 - 0.5 or s['y'] + s['h'] <= s['H'] / 3 + 0.5 or s['y'] >= s['H'] * 2 / 3 - 0.5
    level = s['thr'][1] <= s['cy'] <= s['thr'][1] + s['thr'][3]
    on_screen = s['x'] >= 0 and s['y'] >= 0 and s['x'] + s['w'] <= s['W'] and s['y'] + s['h'] <= s['H']
    return right_of_centre and clear_thr and clear_dock and clear_mid and level and on_screen

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('pilot', 'rookie'):
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3'})
            tag = 'Hard' if skill == 'pilot' else 'Easy'
            ok(f'{tag}: the centre readout element is gone', not await pg.evaluate("()=>!!document.getElementById('bigcfg')"))
            for ac in ('cessna', 'f16', 'c130', 'reaper', 'mq9b', 'alpha'):
                await pg.evaluate(f"()=>{{const K={K};K.pick('{ac}');K.pickBase('kgeu');K.start('final');}}"); await pg.wait_for_timeout(400)
                await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)")
                # Hard: the dock's FLAP buttons (the F-16 schedules its own flaps: its gear instead). Easy: the
                # flaps are automatic and the buttons hidden, so the change comes through the state, as the
                # Easy assist's own changes do.
                if skill == 'pilot' and ac == 'f16':
                    pass   # the Viper schedules its own flaps off the gear: its gear tap below shows GEAR, then FLAPS
                elif skill == 'pilot':
                    await finger(pg, '#bFlapDn' if await pg.evaluate("()=>!document.getElementById('bFlapDn').classList.contains('dim')") else '#bFlapUp'); await pg.wait_for_timeout(150)
                else:
                    await pg.evaluate(f"()=>{{const s={K}.state();s.ezManFlap=1;s.flapIdx=s.flapIdx>0?s.flapIdx-1:1;}}")
                await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await pg.wait_for_timeout(150)
                s = await pg.evaluate(SIDE)
                if not (skill == 'pilot' and ac == 'f16'):
                    ok(f'{tag} {ac}: a flap change shows FLAPS beside the throttle', s['on'] and 'FLAPS' in s['text'] and beside(s), {k: s[k] for k in ('on', 'text', 'x', 'y', 'w', 'h', 'thr', 'dock')})
                if ac == 'cessna' and skill == 'pilot': await pg.screenshot(path=f'{SHOTS}/flaps_844x390.png')
                if ac in ('f16', 'c130') and skill == 'pilot':   # Easy raises and lowers the gear itself
                    await finger(pg, '#bGear'); await pg.wait_for_timeout(150)
                    await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await pg.wait_for_timeout(150)
                    s = await pg.evaluate(SIDE)
                    ok(f'{tag} {ac}: a gear change shows GEAR beside the throttle', s['on'] and 'GEAR' in s['text'] and beside(s), s['text'])
                # it fades after about 2 s of flight
                await pg.evaluate(f"()=>{{for(let i=0;i<24;i++){K}.stepFrame(0.1,false,true)}}"); await pg.wait_for_timeout(600)
                s = await pg.evaluate(SIDE)
                ok(f'{tag} {ac}: the readout fades after about 2 s', not s['on'], s['text'])
                await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
            # trim keys and the autopilot toggles
            await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('final');}}"); await pg.wait_for_timeout(400)
            await pg.keyboard.down('y'); await pg.wait_for_timeout(400); await pg.keyboard.up('y'); await pg.wait_for_timeout(150)
            s = await pg.evaluate(SIDE)
            ok(f'{tag}: trim shows TRIM beside the throttle', s['on'] and 'TRIM' in s['text'] and beside(s), s['text'])
            await pg.evaluate(f"()=>{K}.auto()"); await pg.wait_for_timeout(300)
            s = await pg.evaluate(SIDE)
            ok(f'{tag}: autoland engages beside the throttle, not in the centre', s['on'] and 'AUTOLAND' in s['text'] and beside(s) and 'Autoland' not in await pg.inner_text('#toast'), s['text'])
            await pg.evaluate(f"()=>{{const K={K};K.state().ap=null;K.state().apW=null;K.touchIn.elev=0.5;}}")
            await pg.evaluate(f"()=>{K}.auto()"); await pg.wait_for_timeout(200)
            await pg.evaluate(f"()=>{K}.auto()"); await pg.wait_for_timeout(300)
            s = await pg.evaluate(SIDE)
            ok(f'{tag}: autopilot off beside the throttle', s['on'] and 'AUTOPILOT OFF' in s['text'] and beside(s), s['text'])
            # the centre stays clear through a whole autoland: nothing but the HUD, no element at the screen centre apart from the scene
            await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('final');}}"); await pg.wait_for_timeout(300)
            await pg.evaluate(f"()=>{K}.auto()")
            centre_hits = set()
            for _ in range(70):
                await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
                h = await pg.evaluate("()=>{const e=document.elementFromPoint(innerWidth/2,innerHeight*0.57);return e?(e.id||e.className||e.tagName):''}")
                if h and h not in ('gl', 'uiroot', 'touch', 'stickZone'): centre_hits.add(h)
                st = await pg.evaluate(f"()=>{{const s={K}.state();return s.onGround||s.crashed}}")
                if st: break
            ok(f'{tag}: the centre of the screen stays clear through the landing', not centre_hits, centre_hits)
            ok(f'{tag}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        # portrait
        pg = await page(b, url, vp={'width': 390, 'height': 844}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('final');}}"); await pg.wait_for_timeout(500)
        await finger(pg, '#bFlapDn' if await pg.evaluate("()=>!document.getElementById('bFlapDn').classList.contains('dim')") else '#bFlapUp'); await pg.wait_for_timeout(150)
        await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await pg.wait_for_timeout(150)
        s = await pg.evaluate(SIDE)
        sz = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
        clear_stick = s['x'] + s['w'] <= sz[0] or s['x'] >= sz[0] + sz[2] or s['y'] + s['h'] <= sz[1] or s['y'] >= sz[1] + sz[3]
        clear_ctl = s['x'] + s['w'] <= (s['dock'][0] if s['dock'][2] else s['thr'][0]) + 0.5 or s['y'] + s['h'] <= s['thr'][1]
        on_screen = s['x'] >= 0 and s['y'] >= 0 and s['x'] + s['w'] <= s['W'] and s['y'] + s['h'] <= s['H']
        ok('portrait: the readout sits beside the controls, clear of the stick zone', s['on'] and 'FLAPS' in s['text'] and clear_stick and clear_ctl and on_screen, {k: s[k] for k in ('on', 'text', 'x', 'y', 'w', 'h', 'thr', 'dock', 'W', 'H')})
        await pg.screenshot(path=f'{SHOTS}/flaps_390x844.png')
        ok('portrait: no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('sidetoast_check'))

asyncio.run(main())
