# One-off screenshot script for phone notes 0929, item 6 (pause sheet music controls:
# Prev/Play/Next, music survives game pause, play state survives pause/resume/backgrounding).
# iPhone landscape (844x390, dsf 2, mobile, touch). Prints window.__kgeu.music() next to
# each shot. Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item06_shots.py
import asyncio, os, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, page, finger, IPHONE_15

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item06')
os.makedirs(SHOTS, exist_ok=True)
M = "()=>window.__kgeu.music()"
SR = 8000

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TONES = [{'name': f'_pz{i}.wav', 'url': tone(f, 30.0), 'title': f'Tone {f}'} for i, f in enumerate((330, 440, 550))]

async def m(pg): return await pg.evaluate(M)
async def label(pg): return await pg.evaluate("()=>document.getElementById('pMusic').textContent")

async def wait_for(pg, cond, limit=6000, every=150):
    t = 0
    while t < limit:
        s = await m(pg)
        if cond(s): return s
        await pg.wait_for_timeout(every); t += every
    return await m(pg)

async def shot(pg, name, state):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f'wrote {path}\n  music()={state}\n  pMusic label={await label(pg)}')

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        seed = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        pg = await page(b, url, vp=IPHONE_15, storage=seed)
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
        await pg.touchscreen.tap(330, 8)
        await wait_for(pg, lambda s: s['playing'])

        await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway')}")
        await wait_for(pg, lambda s: s['playing'] is None, 8000)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)

        # start music from the pause sheet (label goes Play -> Pause)
        await finger(pg, '#pMusic')
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.3)
        await pg.wait_for_timeout(400)
        await shot(pg, 'pause_sheet_playing.png', s)

        # tap Next: toast/track name visible
        p0 = s['playing']
        await finger(pg, '#pMnext')
        s = await wait_for(pg, lambda s: s['playing'] != p0, 3000)
        await pg.wait_for_timeout(200)
        await shot(pg, 'pause_sheet_after_next.png', s)
        await pg.wait_for_timeout(1800)  # let the toast/crossfade settle before the next shot

        # tap Pause: label goes back to Play
        await finger(pg, '#pMusic')
        s = await wait_for(pg, lambda s: s['playing'] is None, 5000)
        await pg.wait_for_timeout(300)
        await shot(pg, 'pause_sheet_after_pause.png', s)

        rects = await pg.evaluate("()=>['pPrev','pMusic','pMnext'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return [id, Math.round(r.width), Math.round(r.height)]})")
        print('button sizes (css px):', rects)
        print('errs:', pg.errs[:5])
        await b.close()
    srv.shutdown()

asyncio.run(main())
