# Sensor ball view on the drones: autopilot on entry, drag to slew, ZOOM / MODE / LOCK,
# the overlay, and the autopilot letting go only when the stick moves after leaving.
# Run: .venv/bin/python tests/sensor_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'

async def click(pg, sel):
    await pg.evaluate("(s)=>document.querySelector(s).click()", sel)
    await pg.wait_for_timeout(250)

async def sensor(pg):
    return await pg.evaluate(f"()=>{K}.sensor()")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})

        async def enter(t):
            await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.pick('{t}');{K}.pickBase('luke');{K}.start('final');}}")
            await pg.wait_for_timeout(1200)
            ap0 = await pg.evaluate(f"()=>!!{K}.state().ap")
            await click(pg, '#bSensor'); await pg.wait_for_timeout(300)
            s = await sensor(pg)
            ok(f'{t}: no autopilot before the ball view', not ap0)
            ok(f'{t}: SENSOR enters the ball view with the autopilot on', s['ap'] and await pg.evaluate(f"()=>{K}.camMode()===2&&{K}.sensorMode()"), s)
            tt = await pg.inner_text('#toast')
            ok(f'{t}: toast says AUTOPILOT ENGAGED', 'AUTOPILOT ENGAGED' in tt, repr(tt))
            mode = await pg.evaluate(f"()=>{K}.state().ap.mode")
            ok(f'{t}: the autopilot orbits the ground point', mode == 'orbit', mode)
            return s

        s0 = await enter('reaper')
        # the overlay
        # sensor item 4: the symbology (tests/sensor_overlay_check.py checks every value)
        hud = await pg.evaluate("()=>['shTL','shTR','shTgt'].map(i=>document.getElementById(i).textContent)")
        ok('overlay: sensor and field of view top left', hud[0].startswith('DTV') and 'WFOV' in hud[0], hud[0])
        ok('overlay: UTC, AZ / EL / DEP and the laser top right', hud[1].endswith('Z\nAZ R000 EL -34 DEP 34\nLSR SAFE  CODE 1688') or (' EL ' in hud[1] and 'DEP' in hud[1] and 'LSR SAFE' in hud[1]), hud[1])
        ok('overlay: point of interest and the aircraft (ALT, HDG) under the map', 'MGRS' not in hud[2] and '12S ' in hud[2] and 'ALT ' in hud[2] and 'HDG ' in hud[2], hud[2])
        ok('flight cards step aside in the ball view', not await pg.is_visible('#hud'))
        vis = await pg.evaluate("()=>['bMode','bZoom','bLock','bFire','bGear','bBrake'].filter(i=>{const e=document.getElementById(i);return e.offsetParent!==null})")
        ok('MODE, ZOOM and LOCK shown; FIRE, GEAR and BRAKE not', vis == ['bMode', 'bZoom', 'bLock'], vis)

        # one finger drag on the canvas slews the ball
        await pg.evaluate("""()=>{const g=document.getElementById('gl'),o={pointerId:21,pointerType:'touch',isPrimary:true,bubbles:true};
          g.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:420,clientY:200}));
          for(let i=1;i<=8;i++)g.dispatchEvent(new PointerEvent('pointermove',{...o,clientX:420+i*15,clientY:200+i*8}));
          g.dispatchEvent(new PointerEvent('pointerup',{...o,clientX:540,clientY:264}));}""")
        await pg.wait_for_timeout(200)
        s1 = await sensor(pg)
        ok('a drag on the canvas moves az and el', abs(s1['az']-s0['az']) > 0.5 and abs(s1['el']-s0['el']) > 0.3, f"{s0['az']},{s0['el']} -> {s1['az']},{s1['el']}")
        ok('a drag does not lock', not s1['lock'])

        # sensor item 3: the MTS-B ladder (docs/mtsb.md), ZOOM IN to the narrow end, ZOOM OUT back
        fovs = []
        for _ in range(8):
            fovs.append((await sensor(pg))['fov']); await click(pg, '#bZoom')
        ok('ZOOM IN walks WFOV to UNFOV EZ 4X and stops there', fovs == [34, 17, 5.7, 2.8, 0.47, 0.08, 0.04, 0.02] and (await sensor(pg))['fov'] == 0.02, fovs)
        ok('ZOOM IN dims at the narrow end', await pg.evaluate("()=>document.getElementById('bZoom').classList.contains('dim')"))
        for _ in range(5): await click(pg, '#bWide')
        zl = await pg.inner_text('#fovInd')
        ok('ZOOM OUT steps back, the field of view named between them', zl == 'MFOV' and (await sensor(pg))['fov'] == 5.7, zl)
        for _ in range(3): await click(pg, '#bWide')
        ok('ZOOM OUT stops at WFOV, dimmed', (await sensor(pg))['fov'] == 34 and await pg.evaluate("()=>document.getElementById('bWide').classList.contains('dim')"))
        await pg.evaluate(f"()=>{K}.setSensorMode('irw')")
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=5;}}")
        ok('IR UNFOV is 0.23 degrees', (await sensor(pg))['fov'] == 0.23, (await sensor(pg))['fov'])
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=0;{K}.setSensorMode('tv');}}")

        modes = []
        for _ in range(5):
            modes.append((await sensor(pg))['mode']); await click(pg, '#bMode')
        ok('MODE cycles tv, nir, irw, irb, tv', modes == ['tv', 'nir', 'irw', 'irb', 'tv'], modes)
        await pg.evaluate(f"()=>{K}.setSensorMode('irw')"); await pg.wait_for_timeout(400)
        ok('IR white overlay reads IR WHT', (await pg.inner_text('#shTL')).startswith('IR WHT'))
        await pg.evaluate(f"()=>{K}.setSensorMode('tv')")

        c0 = await pg.evaluate(f"()=>{{const a={K}.state().ap;return [a.cx,a.cz];}}")
        await click(pg, '#bLock')
        s2 = await sensor(pg)
        c1 = await pg.evaluate(f"()=>{{const a={K}.state().ap;return [a.cx,a.cz,a.mode];}}")
        ok('LOCK holds the point under the crosshair', s2['lock'])
        ok('LOCK moves the orbit over the locked point', abs(c1[0]-c0[0])+abs(c1[1]-c0[1]) > 50 and c1[2] == 'orbit', f'{c0} -> {c1[:2]}')
        ok('overlay shows LOCK', 'LOCK' in await pg.inner_text('#shMid'))
        await pg.keyboard.press('l'); await pg.wait_for_timeout(150)
        ok('L key toggles the lock off', not (await sensor(pg))['lock'])
        await pg.keyboard.press('z'); await pg.wait_for_timeout(100)
        ok('Z key steps the zoom', (await sensor(pg))['zoomIdx'] == 1)
        await pg.keyboard.press('x'); await pg.wait_for_timeout(100)
        ok('X key zooms back out', (await sensor(pg))['zoomIdx'] == 0)
        await pg.keyboard.press('m'); await pg.wait_for_timeout(100)
        ok('M key steps the mode, not the sound', (await sensor(pg))['mode'] == 'nir')
        await pg.evaluate(f"()=>{{{K}.setSensorMode('tv');}}")

        # throttle while the sensor autopilot flies: stays on
        await pg.evaluate("()=>document.querySelector('#thr .det[data-p=\"1\"]').dispatchEvent(new PointerEvent('pointerdown',{pointerId:30,bubbles:true}))")
        await pg.evaluate("()=>document.querySelector('#thr .det[data-p=\"1\"]').dispatchEvent(new PointerEvent('pointerup',{pointerId:30,bubbles:true}))")
        await pg.wait_for_timeout(200)
        ok('a throttle tap does not disconnect the autopilot', (await sensor(pg))['ap'])

        # leave with VIEW: autopilot stays until the stick moves
        await click(pg, '#bCam')
        ok('VIEW leaves the ball view', await pg.evaluate(f"()=>{K}.camMode()") == 0)
        await pg.wait_for_timeout(400)
        ok('autopilot stays on after leaving', (await sensor(pg))['ap'])
        box = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];}")
        await pg.evaluate("""([x,y])=>{const z=document.getElementById('stickZone');
          z.dispatchEvent(new PointerEvent('pointerdown',{pointerId:9,clientX:x,clientY:y,bubbles:true}));
          z.dispatchEvent(new PointerEvent('pointermove',{pointerId:9,clientX:x+2,clientY:y+1,bubbles:true}));}""", box)
        await pg.wait_for_timeout(250)
        ok('a thumb resting on the stick inside the deadband keeps it', (await sensor(pg))['ap'])
        await pg.evaluate("""([x,y])=>{const z=document.getElementById('stickZone');
          z.dispatchEvent(new PointerEvent('pointermove',{pointerId:9,clientX:x+40,clientY:y-30,bubbles:true}));}""", box)
        await pg.wait_for_timeout(250)
        ok('moving the stick disconnects the autopilot', not (await sensor(pg))['ap'])
        tt = await pg.inner_text('#sideToast')   # phone2 item 6: autopilot changes read beside the throttle, never in the centre
        ok('the side readout says AUTOPILOT OFF', 'AUTOPILOT OFF' in tt, repr(tt))
        await pg.evaluate("()=>document.getElementById('stickZone').dispatchEvent(new PointerEvent('pointerup',{pointerId:9,bubbles:true}))")

        # the MQ-9B gets the same, and the orbit label on AUTO
        await enter('mq9b')
        await click(pg, '#bSensor')
        await pg.evaluate(f"()=>{{{K}.state().ap=null;}}"); await pg.wait_for_timeout(300)
        ok('MQ-9B AUTO button offers ORBIT', await pg.inner_text('#bAutoT') == 'ORBIT', await pg.inner_text('#bAutoT'))
        await click(pg, '#bAuto')
        ok('MQ-9B AUTO starts the orbit', await pg.evaluate(f"()=>({K}.state().ap||{{}}).mode") == 'orbit')

        # Rookie words
        await pg.evaluate(f"()=>{{{K}.setSkill('rookie');{K}.pick('reaper');{K}.pickBase('luke');{K}.start('final');}}")
        await pg.wait_for_timeout(1200)
        await click(pg, '#bSensor'); await pg.wait_for_timeout(300)
        l0 = await pg.inner_text('#bModeT'); h0 = await pg.inner_text('#shTL')
        await click(pg, '#bMode'); await pg.wait_for_timeout(200)
        l1 = await pg.inner_text('#bModeT'); h1 = await pg.inner_text('#shTL')
        await click(pg, '#bMode'); await pg.wait_for_timeout(200)
        m2 = (await sensor(pg))['mode']
        ok('Rookie labels read Day camera / Heat camera', l0.lower() == 'day camera' and l1.lower() == 'heat camera' and h0.startswith('Day camera') and h1.startswith('Heat camera'), f'{l0!r} {l1!r} {h0!r} {h1!r}')
        ok('Rookie MODE has two entries', m2 == 'tv', m2)
        for _ in range(6): await click(pg, '#bZoom')
        z = await sensor(pg); zl = await pg.inner_text('#fovInd')
        ok('Easy: five zoom steps, WFOV to NFOV, named 5 of 5', z['zoomIdx'] == 4 and z['fov'] == 0.47 and zl == '5 of 5', (z['zoomIdx'], zl))
        bl = await pg.inner_text('#shTgt')
        ok('Rookie overlay uses feet and compass words', ' ft' in bl and 'HDG ' in bl, bl)

        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('sensor_check'))

asyncio.run(main())
