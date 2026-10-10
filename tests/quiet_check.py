# 3.12 Quiet menus: no ATC radio on the home screen or any menu screen, and a call
# that is mid sentence fades out quickly (not a hard cut) on pause or on the menu.
# The queue survives the pause and carries on after Resume.
# Run: .venv/bin/python tests/quiet_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, page, Checks, PLACED
ok = Checks()
ST = "()=>window.__kgeu.radioState()"
LOGN = "()=>window.__kgeu.radioLog().length"

async def step(pg, secs, dt=0.1):
    # simulated time: the loop is held and ticked by hand, no render
    await pg.evaluate(f"()=>{{const K=window.__kgeu;for(let i=0;i<{int(round(secs/dt))};i++)K.stepFrame({dt},false,true);}}")

async def release(pg):
    await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")

async def wait_call(pg, limit=12000):
    # step the sim (the headless render loop is too slow to rely on) until the
    # tower's clips are actually playing; the audio clock runs in real time
    t = 0
    while t < limit:
        s = await pg.evaluate("()=>{window.__kgeu.stepFrame(0.1,false,true);return window.__kgeu.radioState()}")
        if s['srcCount'] > 0: return s
        await pg.wait_for_timeout(50); t += 50
    return await pg.evaluate(ST)

async def fade_checks(pg, tag):
    await pg.wait_for_timeout(200)
    s1 = await pg.evaluate(ST)
    ok(f'{tag}: radio is off the air', not s1['live'], s1)
    ok(f'{tag}: gain ramps toward 0 within 200 ms', s1['gain'] is not None and s1['gain'] < 0.1 * max(0.05, s1['vol']), s1)
    await pg.wait_for_timeout(100)
    s2 = await pg.evaluate(ST)
    ok(f'{tag}: no radio sources after 300 ms', s2['srcCount'] == 0, s2)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', **PLACED})
        await pg.evaluate("()=>window.__kgeu.initAudio()")
        for _ in range(40):   # clips load six at a time over localhost
            r = await pg.evaluate("()=>{const R=window.__kgeu.RADIO;return R.want&&R.got+Math.max(0,R.err)>=R.want}")
            if r: break
            await pg.wait_for_timeout(500)

        # (a) the home screen and every menu screen, 40 simulated seconds each
        n0 = await pg.evaluate(LOGN)
        for sid in ['sHome', 'sFly', 'sSchool', 'sArc', 'rec', 'sSet']:
            if sid == 'rec':
                await pg.evaluate("()=>{window.__kgeu.nav('sHome',true);document.getElementById('hRec').click()}")
            elif sid == 'sFly':
                await pg.evaluate("()=>window.__kgeu.openFly()")
            else:
                await pg.evaluate(f"()=>window.__kgeu.nav('{sid}')")
            await step(pg, 40)
            s = await pg.evaluate(ST); n = await pg.evaluate(LOGN)
            ok(f'{sid}: 40 s on the menu, no radio lines and no sources', n == n0 and s['srcCount'] == 0 and not s['live'], (n - n0, s))
        await pg.evaluate("()=>document.getElementById('recOv').classList.remove('on')")
        await release(pg)

        # (b) pause mid call: fade, silence while paused, the queue carries on after Resume
        await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway')}")
        s = await wait_call(pg)
        ok('flight: the tower call starts playing', s['srcCount'] > 0 and s['live'], s)
        await pg.evaluate("()=>window.__kgeu.togglePause()")
        await fade_checks(pg, 'pause')
        q = await pg.evaluate(ST)
        ok('pause: the pending readback is still queued', q['queued'] > 0, q)
        n1 = await pg.evaluate(LOGN)
        await step(pg, 30)
        s = await pg.evaluate(ST); n = await pg.evaluate(LOGN)
        ok('pause: no new line for 30 s', n == n1 and s['srcCount'] == 0, (n - n1, s))
        await pg.evaluate("()=>document.getElementById('pResume').click()")
        await step(pg, 0.3)
        await release(pg)
        await pg.wait_for_timeout(400)
        s = await pg.evaluate(ST)
        ok('resume: gain is back to the radio volume', s['live'] and abs(s['gain'] - s['vol']) < 0.05, s)
        await step(pg, 5)
        n = await pg.evaluate(LOGN)
        log = await pg.evaluate("()=>window.__kgeu.radioLog().slice(-3).map(l=>l.text)")
        ok('resume: the queue keeps playing (readback)', n > n1 and any('Cleared for takeoff' in t for t in log), log)
        await release(pg)

        # (c) the main menu mid call: same fade, then 40 s of silence across the menus
        await pg.evaluate("()=>window.__kgeu.start('runway')")
        s = await wait_call(pg)
        ok('second flight: the tower call starts playing', s['srcCount'] > 0, s)
        await pg.evaluate("()=>window.__kgeu.openMenu()")
        await fade_checks(pg, 'main menu')
        n2 = await pg.evaluate(LOGN)
        for sid in ['sHome', 'sFly', 'sSchool', 'sArc', 'sSet']:
            await pg.evaluate(f"()=>window.__kgeu.nav('{sid}')")
            await step(pg, 40 / 6)
        await step(pg, 5)
        s = await pg.evaluate(ST); n = await pg.evaluate(LOGN)
        ok('main menu: no radio lines for 40 s', n == n2 and s['srcCount'] == 0, (n - n2, s))
        await release(pg)

        # (d)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('quiet_check'))

asyncio.run(main())
