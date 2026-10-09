# Item 7: the "now playing" ticker at the top of the flight screen. Real touch taps.
#  - in flight with music playing: the ticker shows, with the current track's title
#  - a title too long for the pill scrolls (a CSS animation), a short one sits still
#  - tapping it opens Prev / Play-Pause / Next in its place, without pausing the game;
#    Next changes the track and the ticker text follows
#  - hidden on the pause sheet, in the photo view, on the menu, and when music is off in Settings
#  - paused by the player in flight: stays, dimmed with a play icon, one tap plays; a new flight drops it
# Run: .venv/bin/python tests/ticker_check.py
import asyncio, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
from harness import serve, page, Checks, finger
ok = Checks()
SR = 8000

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TITLES = ['Short One', 'A Much Longer Song Title That Will Not Fit In The Pill', 'Tone Three Is Also Quite A Long Name Here']
TONES = [{'name': f'_tk{i}.wav', 'url': tone(f, 30.0), 'title': TITLES[i]} for i, f in enumerate((330, 440, 550))]

async def m(pg): return await pg.evaluate("()=>window.__kgeu.music()")
async def tk(pg): return await pg.evaluate("()=>window.__kgeu.ticker()")

async def wait_for(pg, fn, cond, limit=6000, every=150):
    t = 0
    while t < limit:
        s = await fn(pg)
        if cond(s): return s
        await pg.wait_for_timeout(every); t += every
    return await fn(pg)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        pg = await page(b, url, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuMusicFree': '1'})
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
        await pg.touchscreen.tap(330, 3)
        await wait_for(pg, m, lambda s: s['allowed'])
        t = await tk(pg)
        ok('home screen: no ticker (menus hide it, and are silent)', not t['vis'], t)

        await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway')}")
        s = await wait_for(pg, m, lambda s: s['playing'] and s['want'], 8000)
        t = await wait_for(pg, tk, lambda t: t['vis'], 4000)
        ok('flight, music playing: the ticker shows', t['vis'] and t['on'], t)
        ok('ticker text is the track title', t['text'] == s['title'], (t['text'], s['title']))
        long_ = s['title'] != TITLES[0]
        anim = await pg.evaluate("()=>getComputedStyle(document.getElementById('tkT')).animationName")
        ok('a long title scrolls, a short one sits still', t['scroll'] == long_ and (anim == 'tkM') == long_, (s['title'], t['scroll'], anim))
        box = await pg.evaluate("()=>{const r=document.getElementById('tk').getBoundingClientRect();return [r.width,r.height,r.right,r.top]}")
        ok('tap target at least 44 x 44, inside the screen', box[0] >= 44 and box[1] >= 44 and box[2] <= 667 and box[3] >= 0, box)

        # tap: the controls, the game keeps flying
        await finger(pg, '#tk'); await pg.wait_for_timeout(400)
        t = await tk(pg)
        paused = await pg.evaluate("()=>window.__kgeu.paused()")
        ok('tap: Prev / Play-Pause / Next open in its place', t['ctlVis'] and not t['vis'], t)
        ok('tap: the game is not paused', not paused)
        lab = await pg.evaluate("()=>document.getElementById('tkPlay').textContent")
        ok('the Play-Pause button reads Pause while music plays', lab == 'Pause', lab)
        p0 = s['playing']
        await finger(pg, '#tkNext')
        s = await wait_for(pg, m, lambda s: s['playing'] != p0, 3000)
        ok('Next: the track changes', s['playing'] and s['playing'] != p0, (p0, s['playing']))
        t = await wait_for(pg, tk, lambda t: t['vis'], 9000)
        s = await m(pg)
        ok('the controls close by themselves, the ticker comes back', t['vis'] and not t['ctlVis'], t)
        ok('Next: the ticker text follows the new track', t['text'] == s['title'], (t['text'], s['title']))

        # the pause sheet and the photo view hide it; resume brings it back
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        t = await tk(pg)
        ok('pause sheet: ticker hidden', not t['vis'], t)
        await pg.evaluate("()=>window.__kgeu.photoOpen()"); await pg.wait_for_timeout(500)
        t = await tk(pg)
        ok('photo view: ticker hidden', not t['vis'], t)
        await pg.evaluate("()=>window.__kgeu.photoClose()"); await pg.wait_for_timeout(500)
        if await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')"):
            await finger(pg, '#pResume'); await pg.wait_for_timeout(800)
        t = await wait_for(pg, tk, lambda t: t['vis'], 3000)
        ok('resume: ticker back', t['vis'], t)
        fit = await pg.evaluate("""(ls)=>{const K=window.__kgeu,r=ls.map(n=>{K.tickerForce(n);return K.ticker().scroll;});K.tickerForce(null);return r;}""", [TITLES[0], TITLES[1]])
        ok('fit: a short title is still, a long one scrolls', fit == [False, True], fit)

        # music paused from the strip: the ticker stays, dimmed, a play icon, the title still
        await finger(pg, '#tk'); await pg.wait_for_timeout(300)
        await finger(pg, '#tkPlay')
        s = await wait_for(pg, m, lambda s: s['playing'] is None, 6000)
        t = await wait_for(pg, tk, lambda t: not t['ctlVis'], 8000)
        ok('music paused from the strip: ticker stays, in its paused state', s['userPaused'] and t['vis'] and t['paused'], (s['userPaused'], t))
        icon = await pg.evaluate("()=>[getComputedStyle(document.querySelector('#tk .tkPl')).display,getComputedStyle(document.querySelector('#tk .tkN')).display,+getComputedStyle(document.querySelector('#tk .tkP')).opacity]")
        ok('paused: a play icon, dimmed, the title does not scroll', icon[0] != 'none' and icon[1] == 'none' and icon[2] < 0.9 and t['anim'] == 'none', (icon, t['anim']))
        await finger(pg, '#tk')
        s = await wait_for(pg, m, lambda s: s['playing'] and not s['userPaused'], 6000)
        t = await wait_for(pg, tk, lambda t: t['vis'] and not t['paused'], 3000)
        ok('paused ticker: one tap plays again, ticker back to normal', s['playing'] and t['vis'] and not t['paused'] and not t['ctlVis'], (s['playing'], t))
        ok('playing again: ticker text is the track title', t['text'] == s['title'], (t['text'], s['title']))

        # switched off in Settings: it goes
        await pg.evaluate("()=>document.getElementById('oMusic').click()")
        s = await wait_for(pg, m, lambda s: s['playing'] is None, 6000)
        t = await tk(pg)
        ok('music off in Settings: ticker hidden', not s['on'] and not t['vis'] and not t['on'], (s['on'], t))
        await pg.evaluate("()=>document.getElementById('oMusic').click()")
        t = await wait_for(pg, tk, lambda t: t['vis'], 6000)
        ok('music back on: ticker back', t['vis'] and not t['paused'], t)

        # paused, then a new flight: the paused ticker does not carry over
        await finger(pg, '#tk'); await pg.wait_for_timeout(300)
        await finger(pg, '#tkPlay')
        await wait_for(pg, m, lambda s: s['playing'] is None, 6000)
        await pg.evaluate("()=>window.__kgeu.start('runway')"); await pg.wait_for_timeout(800)
        await pg.evaluate("()=>window.__kgeu.musicTick()")
        t = await tk(pg)
        ok('new flight after a pause: ticker and controls hidden', not t['vis'] and not t['ctlVis'] and not t['paused'], t)
        await pg.evaluate("()=>window.__kgeu.setMusicOn(true)")
        t = await wait_for(pg, tk, lambda t: t['vis'], 6000)

        # the main menu hides it
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        await finger(pg, '#pMenu'); await pg.wait_for_timeout(1200)
        t = await tk(pg)
        menu = await pg.evaluate("()=>document.body.classList.contains('menuOn')")
        ok('main menu: ticker hidden', menu and not t['vis'], (menu, t))

        # portrait: no room for the strip beside the readouts, the tap opens the pause sheet's music row
        await pg.set_viewport_size({'width': 390, 'height': 844}); await pg.wait_for_timeout(500)
        await pg.evaluate("()=>{document.body.classList.add('portraitok');const K=window.__kgeu;K.start('runway')}")
        t = await wait_for(pg, tk, lambda t: t['vis'], 6000)
        ok('portrait: ticker shows', t['vis'], t)
        await finger(pg, '#tk'); await pg.wait_for_timeout(500)
        pz = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
        ok('portrait tap: the pause sheet with its music row opens', pz)
        ok('no page errors and no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('ticker_check'))

asyncio.run(main())
