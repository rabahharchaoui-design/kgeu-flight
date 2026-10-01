# Phone2 item 8: music only in flight. Nothing on the splash, the callsign card, the main menu or
# any menu screen, ever. It starts with a flight and fades out within 1 s on the way to the main
# menu, from the pause sheet, from a results card and from the crash card. A menu screen opened
# from the pause sheet is silent too, but Back and Resume carry the same track on.
# Launch, sit on the main menu 10 s: silence. Fly, pause, Main menu: silence within 1.5 s.
# Run: .venv/bin/python tests/music_menu_check.py
import asyncio, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
from harness import serve, page, Checks, finger, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
M = "()=>window.__kgeu.music()"
SR = 8000

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TONES = [{'name': f'_mm{i}.wav', 'url': tone(f, 40.0), 'title': f'Menu Tone {i}'} for i, f in enumerate((330, 440, 550))]

async def m(pg): return await pg.evaluate(M)
async def wait_for(pg, cond, limit=8000, every=100):
    t = 0
    while t < limit:
        s = await m(pg)
        if cond(s): return s
        await pg.wait_for_timeout(every); t += every
    return await m(pg)

async def silence_within(pg, ms):
    """samples the gain every 100 ms; returns (time to < 0.02, final state)"""
    t = 0
    while t < ms:
        s = await m(pg)
        if s['gain'] < 0.02: return t, s
        await pg.wait_for_timeout(100); t += 100
    return None, await m(pg)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
        await pg.touchscreen.tap(420, 8)
        s = await wait_for(pg, lambda s: s['allowed'], 4000)
        ok('launch, a tap on the main menu: the audio gate opens', s['allowed'], s['allowed'])
        # 10 s on the main menu, then the FLY and Settings screens: nothing ever plays
        peak = 0.0; played = set()
        for i in range(20):
            await pg.wait_for_timeout(500); s = await m(pg)
            peak = max(peak, s['gain']); played.add(s['playing'])
        ok('10 s on the main menu: silence, nothing playing', peak < 1e-3 and played == {None}, (peak, played))
        for scr in ('sFly', 'sMis', 'sSet'):
            await pg.evaluate(f"(s)=>{K}.nav(s)", scr); await pg.wait_for_timeout(1200); s = await m(pg)
            ok(f'{scr}: silent', s['gain'] < 1e-3 and s['playing'] is None and not s['want'], (s['gain'], s['playing']))

        # a flight: the music starts; the pause sheet keeps it; Main menu: silence within 1.5 s
        await pg.evaluate(f"()=>{K}.mission('drop')")
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.3, 8000)
        ok('a mission starts: music plays', s['playing'] is not None and s['gain'] > 0.3, (s['playing'], s['gain']))
        track = s['playing']
        await finger(pg, '#bPause'); await pg.wait_for_timeout(800); s = await m(pg)
        ok('pause sheet: the music plays on', s['playing'] == track and s['gain'] > 0.3 and s['want'], (s['playing'], s['gain']))
        await finger(pg, '#pMenu')
        t, s = await silence_within(pg, 1500)
        ok('pause, Main menu: silence within 1.5 s', t is not None, (t, s['gain']))
        await pg.wait_for_timeout(2500); s = await m(pg)
        ok('main menu after a flight: the track is stopped, nothing playing', s['playing'] is None and s['gain'] < 1e-3, (s['playing'], s['gain']))

        # a menu screen from the pause sheet: silent, but Back and Resume carry the same track on
        await pg.evaluate(f"()=>{K}.mission('drop')")
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.3, 8000)
        track = s['playing']
        await finger(pg, '#bPause'); await pg.wait_for_timeout(400)
        await finger(pg, '#pSet')
        t, s = await silence_within(pg, 1500)
        ok('pause, Settings: silent within 1.5 s', t is not None and not s['want'], (t, s['gain']))
        await pg.wait_for_timeout(2500); s = await m(pg)
        ok('Settings from the pause sheet: the track is held, not dropped', s['playing'] == track, (track, s['playing']))
        await finger(pg, '#sSet .back'); await pg.wait_for_timeout(400)
        ok('Back returns to the pause sheet', await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')"))
        await finger(pg, '#pResume')
        s = await wait_for(pg, lambda s: s['gain'] > 0.3, 4000)
        ok('Resume: the same track comes back up', s['playing'] == track and s['gain'] > 0.3 and s['want'], (track, s['playing'], s['gain']))

        # the results card's MAIN MENU
        await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z;}}"); await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{{const K={K};K.missDrop();K.missTick(4000,1/60);}}"); await pg.wait_for_timeout(500)
        card = await pg.evaluate("()=>document.getElementById('missOv').classList.contains('on')")
        if ok('airdrop results card is up', card):
            s = await m(pg)
            ok('results card: the music plays on under it', s['gain'] > 0.3, s['gain'])
            await finger(pg, '#mMenu')
            t, s = await silence_within(pg, 1500)
            ok('results card, MAIN MENU: silence within 1.5 s', t is not None, (t, s['gain']))

        # the crash card's MENU
        await pg.evaluate(f"()=>{K}.mission('drop')")
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.3, 8000)
        await pg.evaluate(f"()=>{K}.crashNow('Test crash')")
        got = False
        for _ in range(60):
            await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)")
            if await pg.evaluate("()=>document.getElementById('crash').classList.contains('on')"): got = True; break
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        if ok('crash card is up', got):
            await pg.wait_for_function("()=>document.getElementById('cMenu').getBoundingClientRect().bottom<=innerHeight", timeout=8000)
            await finger(pg, '#cMenu')
            t, s = await silence_within(pg, 1500)
            ok('crash card, MENU: silence within 1.5 s', t is not None, (t, s['gain']))
        ok('no page errors and no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('music_menu_check'))

asyncio.run(main())
