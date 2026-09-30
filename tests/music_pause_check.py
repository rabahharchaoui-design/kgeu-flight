# Item 6: the pause sheet's music controls, and the music's play state across pause,
# resume and backgrounding. Real touch taps (page.touchscreen.tap on the element centre).
#  - free flight (music in free flight off): the pause sheet reads Play, not a dead Pause
#  - Play starts it (and turns it on for free flight), Next / Prev change the track with a
#    crossfade and show the title, Play/Pause toggles and its label follows, saved
#  - Resume: the music carries on in flight
#  - backgrounded (document.hidden + visibilitychange, AudioContext suspended), back again:
#    the same track plays on; with iOS refusing a resume until a gesture, one tap wakes it
#  - a user pause survives backgrounding and a reload
# Run: .venv/bin/python tests/music_pause_check.py
import asyncio, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
from harness import serve, page, Checks, finger
ok = Checks()
M = "()=>window.__kgeu.music()"
SR = 8000

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TONES = [{'name': f'_pz{i}.wav', 'url': tone(f, 30.0), 'title': f'Tone {f}'} for i, f in enumerate((330, 440, 550))]

async def m(pg): return await pg.evaluate(M)

async def wait_for(pg, cond, limit=6000, every=150):
    t = 0
    while t < limit:
        s = await m(pg)
        if cond(s): return s
        await pg.wait_for_timeout(every); t += every
    return await m(pg)

async def label(pg): return await pg.evaluate("()=>document.getElementById('pMusic').textContent")

HIDE = """(h)=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>h});
  Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>h?'hidden':'visible'});
  document.dispatchEvent(new Event('visibilitychange'));}"""

async def background(pg, block_resume=False):
    await pg.evaluate(HIDE, True)
    await pg.evaluate("()=>window.__kgeu.actx().suspend()")
    await pg.wait_for_timeout(800)
    if block_resume:   # iOS: no resume without a gesture
        await pg.evaluate("()=>{const a=window.__kgeu.actx();a.__r=a.resume;a.resume=()=>Promise.reject(new Error('gesture'))}")
    await pg.evaluate(HIDE, False)
    await pg.wait_for_timeout(600)
    if block_resume:
        await pg.evaluate("()=>{const a=window.__kgeu.actx();a.resume=a.__r;delete a.__r}")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        seed = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        pg = await page(b, url, storage=seed)
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
        await pg.touchscreen.tap(330, 8)
        s = await wait_for(pg, lambda s: s['playing'])
        ok('home: music plays after the first tap', s['playing'] is not None, s['playing'])

        # free flight, music in free flight off: it fades out
        await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway')}")
        s = await wait_for(pg, lambda s: s['playing'] is None, 8000)
        ok('free flight (off by default): no music', s['playing'] is None and not s['free'], (s['playing'], s['free']))
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        on = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
        ok('pause sheet opens from the pause button', on)
        ok('pause sheet: nothing playing, the button reads Play', await label(pg) == 'Play', await label(pg))

        await finger(pg, '#pMusic')
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.3)
        ok('Play (tap): music starts under the pause sheet', s['playing'] is not None and s['gain'] > 0.3, (s['playing'], s['gain']))
        ok('Play: label reads Pause, free flight music turned on', await label(pg) == 'Pause' and s['free'] and not s['userPaused'], (await label(pg), s['free']))
        await pg.wait_for_timeout(1800)
        p0 = (await m(pg))['playing']

        # the headless page runs at a few fps, too slow to sample a 1.5 s fade from outside:
        # record the gain ramps the tap schedules instead (in, to 1; out, to 0; ~1.5 s long)
        await pg.evaluate("""()=>{const P=AudioParam.prototype,o=P.linearRampToValueAtTime,R=window.__ramps=[];
          P.linearRampToValueAtTime=function(v,t){R.push([this,v,t]);return o.call(this,v,t);};window.__rampsOff=()=>{P.linearRampToValueAtTime=o;}}""")
        await finger(pg, '#pMnext')
        s = await wait_for(pg, lambda s: s['playing'] != p0, 3000)
        p1 = s['playing']
        ok('Next (tap): the track changes', p1 and p1 != p0, (p0, p1))
        xf = await pg.evaluate("""()=>{window.__rampsOff();const by=new Map();window.__ramps.forEach(([p,v,t])=>{if(!by.has(p))by.set(p,[]);by.get(p).push([v,t]);});
          return [...by.values()].filter(a=>a.length>=8).map(a=>({end:+a[a.length-1][0].toFixed(3),span:+(a[a.length-1][1]-a[0][1]).toFixed(2),t0:a[0][1]}));}""")
        ins = [r for r in xf if r['end'] > 0.99]; outs = [r for r in xf if r['end'] < 0.01]
        ok('Next: a crossfade (one ramp up, one down, ~1.5 s, together)', len(ins) == 1 and len(outs) == 1
           and all(1.2 < r['span'] < 1.6 for r in ins + outs) and abs(ins[0]['t0'] - outs[0]['t0']) < 0.3, xf)
        shown = await pg.evaluate("()=>[document.getElementById('pMusTitle').textContent,document.getElementById('toast').textContent]")
        ok('Next: the title shows on the sheet and in the toast', shown[0] == s['title'] and s['title'] in shown[1], (shown, s['title']))
        await pg.wait_for_timeout(1700)

        await finger(pg, '#pPrev')
        s = await wait_for(pg, lambda s: s['playing'] == p0, 2500)
        ok('Prev (tap): back to the track before', s['playing'] == p0, (p0, s['playing']))
        await pg.wait_for_timeout(1700)

        await finger(pg, '#pMusic')
        s = await wait_for(pg, lambda s: s['playing'] is None, 5000)
        ls = await pg.evaluate("()=>localStorage.getItem('kgeuMusicOn')")
        ok('Pause (tap): music fades out and stops, saved', s['playing'] is None and s['userPaused'] and ls == '0', (s['playing'], ls))
        ok('Pause: label reads Play', await label(pg) == 'Play', await label(pg))
        await finger(pg, '#pMusic')
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.3)
        ok('Play again (tap): music back, label Pause', s['playing'] and await label(pg) == 'Pause', (s['playing'], await label(pg)))
        await pg.wait_for_timeout(1700)

        await finger(pg, '#pResume'); await pg.wait_for_timeout(2000)
        s = await m(pg)
        paused = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
        ok('Resume: game unpaused, music still playing', not paused and s['playing'] and s['want'] and s['master'] > 0.3, (paused, s['playing'], s['master'], s['ducked']))

        # backgrounded and back: the same track plays on
        before = s['playing']
        await background(pg)
        s = await wait_for(pg, lambda s: s['ctx'] == 'running' and s['gain'] > 0.3, 4000)
        pz = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
        ok('background: the game paused itself', pz)
        ok('back from background: context running, same track playing', s['ctx'] == 'running' and s['playing'] == before and s['gain'] > 0.3, (s['ctx'], before, s['playing'], s['gain']))

        # iOS: the context will not resume without a gesture: one tap anywhere wakes it
        await background(pg, block_resume=True)
        s = await m(pg)
        ok('iOS-like: still suspended with no gesture', s['ctx'] != 'running', s['ctx'])
        await pg.touchscreen.tap(330, 8)
        s = await wait_for(pg, lambda s: s['ctx'] == 'running' and s['playing'] and s['gain'] > 0.3, 4000)
        ok('iOS-like: one tap resumes the context and the music', s['ctx'] == 'running' and s['playing'] and s['gain'] > 0.3, (s['ctx'], s['playing'], s['gain']))

        # a user pause survives backgrounding
        await finger(pg, '#pMusic')
        s = await wait_for(pg, lambda s: s['playing'] is None, 5000)
        await background(pg)
        await pg.wait_for_timeout(1500)
        s = await m(pg)
        ok('user pause survives backgrounding', s['playing'] is None and s['userPaused'] and s['ctx'] == 'running' and await label(pg) == 'Play', (s['playing'], s['ctx'], await label(pg)))
        ok('no page errors and no console errors', not pg.errs, pg.errs[:3])

        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await pg.wait_for_timeout(500)
        s = await m(pg)
        ok('reload: the user pause is kept', s['userPaused'] and not s['on'], s['on'])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('music_pause_check'))

asyncio.run(main())
