# C-130 drop camera (3.3b): LOOK pad free look, LOOK BACK ramp view, pallet follow after DROP.
# Run: .venv/bin/python tests/dropcam_check.py
import asyncio, os, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15, finger
ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'dropcam')
K = 'window.__kgeu'

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        ev = lambda js: pg.evaluate("()=>{" + js + "}")
        dc = lambda: pg.evaluate(f"()=>{K}.dropCam()")
        vis = lambda sel: pg.is_visible(sel)
        async def step(n, dt=1/60, skip=False):
            await pg.evaluate("([n,dt,sk])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(dt,false,sk);}", [n, dt, skip])
        await ev(f"{K}.setSkill('pilot')")

        print('-- only in the airdrop --')
        await ev(f"{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('final')"); await pg.wait_for_timeout(1500)
        ok('plain C-130 flight: no LOOK pad, no LOOK BACK', not await vis('#lookPad') and not await vis('#bLookBack'))
        await ev(f"{K}.pick('cessna');{K}.start('final')"); await pg.wait_for_timeout(1500)
        ok('Cessna: no LOOK pad, no LOOK BACK', not await vis('#lookPad') and not await vis('#bLookBack'))
        await ev(f"{K}.mission('drop')"); await pg.wait_for_timeout(1800)
        ok('airdrop: LOOK pad and LOOK BACK showing', await vis('#lookPad') and await vis('#bLookBack'))
        d = await dc(); ok('starts in the chase view', d['mode'] == 'chase', d)

        print('-- free look pad --')
        c = await pg.evaluate("()=>{const r=document.getElementById('lookPad').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}")
        await step(5)
        q0 = await pg.evaluate(f"()=>{K}.camQuat()")
        pe = "([t,x,y])=>document.getElementById('lookPad').dispatchEvent(new PointerEvent(t,{pointerId:11,pointerType:'touch',clientX:x,clientY:y,bubbles:true,cancelable:true}))"
        await pg.evaluate(pe, ['pointerdown', c[0], c[1]])
        for i in range(1, 11):
            await pg.evaluate(pe, ['pointermove', c[0] - 17 * i, c[1] + 5 * i]); await step(3)
        await step(40)
        d = await dc(); q1 = await pg.evaluate(f"()=>{K}.camQuat()")
        dq = 1 - abs(sum(a * b for a, b in zip(q0, q1)))
        ok('dragging the pad swings the yaw', d['mode'] == 'look' and abs(d['yaw']) > 100, d)
        ok('and pitches down', d['pitch'] < -30, d['pitch'])
        ok('camera attitude changed', dq > 0.05, f'{dq:.3f}')
        await pg.screenshot(path=f'{SHOTS}/look_pad_drag.png')
        await pg.evaluate(pe, ['pointerup', c[0] - 170, c[1] + 50])
        await step(60)
        d = await dc(); ok('released: yaw springs back to about 0 inside 1 s', abs(d['yaw']) < 2 and abs(d['pitch']) < 2 and d['mode'] == 'chase', d)

        print('-- look back from the ramp --')
        # past the DZ and flying away from it, so the bullseye is behind the ramp
        await ev(f"const s={K}.state();s.pos.x={K}.DROPZ.x-520;s.pos.z={K}.DROPZ.z;{K}.snapCam()")
        await step(10)
        await finger(pg, '#bLookBack'); await step(30)
        d = await dc()
        aft = await pg.evaluate(f"""()=>{{const s={K}.state(),c={K}.camPos(),z=new s.pos.constructor(0,0,1).applyQuaternion(s.quat);
          return (c[0]-s.pos.x)*z.x+(c[1]-s.pos.y)*z.y+(c[2]-s.pos.z)*z.z;}}""")
        ok('LOOK BACK: ramp view', d['mode'] == 'ramp', d)
        ok('camera aft of the aircraft along its +Z', aft > 2, f'{aft:.1f} m')
        ok('LOOK BACK lit', await pg.evaluate("()=>document.getElementById('bLookBack').classList.contains('lit')"))
        await pg.screenshot(path=f'{SHOTS}/look_back.png')
        await finger(pg, '#bLookBack'); await step(30)
        d = await dc(); ok('second tap: back to chase', d['mode'] == 'chase', d)

        print('-- pallet follow --')
        await ev(f"const s={K}.state();s.pos.x={K}.DROPZ.x+260;s.pos.z={K}.DROPZ.z;{K}.snapCam()")
        for _ in range(60):
            await step(2)
            if await pg.evaluate(f"()=>{K}.MISS.armed"): break
        ok('drop window armed', await pg.evaluate(f"()=>{K}.MISS.armed"))
        await finger(pg, '#bDrop')
        await step(60)
        d = await dc(); cp = await pg.evaluate(f"()=>{K}.camPos()")
        ok('DROP: camera follows the pallet within 1 s', d['mode'] == 'pallet', d)
        ok('toCenter is a number', isinstance(d['toCenter'], (int, float)), d['toCenter'])
        dist = math.dist(cp, d['pallet']) if d['pallet'] else 1e9
        ok('camera within 60 m of the pallet', dist < 60, f'{dist:.1f} m')
        mt = await pg.evaluate("()=>document.getElementById('missT').textContent")
        ok('HUD shows TO CENTER', mt.startswith('TO CENTER:'), mt)
        # stick input still flies the aircraft while the camera rides the bundle
        roll = f"()=>{{const s={K}.state(),r=new s.pos.constructor(1,0,0).applyQuaternion(s.quat);return Math.asin(r.y)*180/Math.PI}}"
        r0 = await pg.evaluate(roll)
        await ev(f"{K}.touchIn.ail=1;{K}.touchIn.active=true"); await step(45)
        r1 = await pg.evaluate(roll)
        await ev(f"{K}.touchIn.ail=-1"); await step(45)
        await ev(f"{K}.touchIn.ail=0;{K}.touchIn.active=false")
        ok('stick still rolls the aircraft during the follow', abs(r1 - r0) > 5, f'{r0:.1f} -> {r1:.1f} deg')
        ok('still following the pallet', (await dc())['mode'] == 'pallet')
        await step(24, 0.1, True); await step(3)
        await pg.screenshot(path=f'{SHOTS}/pallet_follow.png')

        print('-- landing --')
        n = 0
        # coarse until it is low, then a frame at a time so the landing moment is exact
        while n < 900 and (await dc())['pallet'][1] > 60:
            await step(10, 0.1, True); n += 10
        while not (await dc())['down'] and n < 1200:
            await step(1, 1/30, True); n += 1/3
        d = await dc(); ok('pallet lands', d['down'], f'{n/10:.0f} s')
        await step(30)
        mt = await pg.evaluate("()=>document.getElementById('missT').textContent")
        ok('landed label with the final distance', mt.startswith('LANDED') and 'from center' in mt, mt)
        ok('still on the pallet during the hold', (await dc())['mode'] == 'pallet')
        await pg.screenshot(path=f'{SHOTS}/landed.png')
        t = 0.5
        while (await dc())['mode'] != 'chase' and t < 5:
            await step(6); t += 0.1
        ok('back to chase within 3 s of landing', (await dc())['mode'] == 'chase' and t <= 3.0, f'{t:.1f} s')
        await step(90)
        ok('result card comes up', await vis('#missOv'))
        ok('pad and LOOK BACK gone once scored', not await vis('#lookPad') and not await vis('#bLookBack'))

        print('-- VIEW cancels the follow --')
        await ev(f"{K}.stepFrame(0,true);document.getElementById('missOv').classList.remove('on');{K}.mission('drop')"); await pg.wait_for_timeout(1500)
        await ev(f"const s={K}.state();s.pos.x={K}.DROPZ.x+260;s.pos.z={K}.DROPZ.z;{K}.snapCam()")
        await pg.wait_for_timeout(700)
        await finger(pg, '#bDrop'); await pg.wait_for_timeout(600)
        m1 = (await dc())['mode']
        await finger(pg, '#bCam'); await pg.wait_for_timeout(200)
        d = await dc()
        ok('VIEW during the follow returns to chase at once', m1 == 'pallet' and d['mode'] == 'chase' and d['blend'] == 1, f'{m1} -> {d}')
        await ev(f"{K}.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('dropcam_check')

sys.exit(asyncio.run(main()))
