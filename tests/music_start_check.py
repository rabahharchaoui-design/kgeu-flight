# Item 5: music never starts at app open. One gate (MUSIC.allowed, through musicWanted)
# opens on the first gesture, and on a first launch with leaderboards on only once the
# callsign card is completed or skipped. The first tap still unlocks the AudioContext.
#  (a) LB origin (http://localhost:8765), fresh profile: taps while the callsign card is up
#      unlock audio but play nothing; claiming a callsign and tapping I SAVED IT starts it
#  (b) LB origin, relaunch with a callsign: nothing before a tap, music on the first tap
#  (c) LB origin, the Worker does not answer: no card, music on the first tap
#  (d) LB off (plain harness origin): nothing before the first tap, music after it
# The Worker is faked with page routes, so nothing leaves the machine.
# Run: .venv/bin/python tests/music_start_check.py
import asyncio, sys, os, io, math, struct, base64, wave, json
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, page, Checks, THREE, IPHONE_15, ROOT
from scores_check import serve_game
ok = Checks()
M = "()=>window.__kgeu.music()"
WORKER = 'https://pfs-scores.rabahharchaoui.workers.dev'
ARGS = ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader',
        '--autoplay-policy=no-user-gesture-required']   # so only the game's own gate keeps it quiet

def tone(freq, secs=6.0, sr=8000):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / sr))) for i in range(int(sr * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TONES = [{'name': f'_start{i}.wav', 'url': tone(f)} for i, f in enumerate((330, 440))]

async def fake_worker(route):
    u = route.request.url.split('?')[0][len(WORKER):]
    body = {}
    if u == '/health': body = {'ok': True}
    elif u == '/name': body = {'free': True}
    elif u == '/signup':
        cs = json.loads(route.request.post_data or '{}').get('cs', 'HABOOB')
        body = {'cs': cs, 'xp': 0, 'recovery': 'SAND DUNE MESA HAWK', 'created': 1}
    elif u == '/me': body = {'cs': 'MESQUITE', 'xp': 0}
    elif u == '/board': body = {'rows': [], 'total': 0}
    await route.fulfill(status=200, content_type='application/json', body=json.dumps(body),
                        headers={'Access-Control-Allow-Origin': '*'})

async def dead_worker(route):
    await route.abort()

async def lb_page(b, storage, worker=fake_worker):
    ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.route(WORKER + '/**', worker)
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
        + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    await pg.goto('http://localhost:8765/index.html')
    await pg.wait_for_function('()=>window.__kgeu&&window.__kgeu.LB', timeout=30000)
    await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    await pg.wait_for_timeout(600)
    return pg

async def m(pg): return await pg.evaluate(M)

async def wait_for(pg, cond, limit=8000):
    t = 0
    while t < limit:
        s = await m(pg)
        if cond(s): return s
        await pg.wait_for_timeout(150); t += 150
    return await m(pg)

async def main():
    game = serve_game()
    srv, url = serve()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=ARGS)
            seed = {'kgeuTut': '1', 'kgeuCoach': '3'}

            # (a) fresh profile on the LB origin
            pg = await lb_page(b, seed)
            await pg.wait_for_function("()=>document.getElementById('csOv').classList.contains('on')", timeout=15000)
            s = await m(pg)
            ok('(a) card up, nothing playing before any tap', s['playing'] is None and not s['allowed'], s)
            for xy in ((40, 40), (420, 30), (800, 360), (420, 200)):
                await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(250)
            await pg.wait_for_timeout(2500)
            s = await m(pg)
            ok('(a) taps with the card up unlock audio', s['ctx'] == 'running', s['ctx'])
            ok('(a) taps with the card up play no music', s['playing'] is None and not s['allowed'] and s['gain'] < 1e-3 and not s['want'], s)
            ok('(a) card still up', await pg.evaluate("()=>document.getElementById('csOv').classList.contains('on')"))
            await pg.fill('#csIn', 'MESQUITE')
            await pg.wait_for_function("()=>/is free/.test(document.getElementById('csStat').textContent)", timeout=10000)
            await pg.tap('#csGo')
            await pg.wait_for_function("()=>!document.getElementById('csCode').hidden", timeout=10000)
            await pg.wait_for_timeout(1500)
            s = await m(pg)
            ok('(a) recovery code screen (callsign claimed, card not done): still quiet', s['playing'] is None and not s['allowed'], s)
            await pg.tap('#csGo')
            s = await wait_for(pg, lambda s: s['playing'])
            ok('(a) I SAVED IT closes the card and the music starts', s['allowed'] and s['playing'] is not None, s)
            ok('(a) no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()

            # (b) relaunch with a callsign on the LB origin
            st = dict(seed, kgeuOnboard='pilot', kgeuLB=json.dumps({'cs': 'MESQUITE', 'key': 'ab' * 24, 'xp': 0}))
            pg = await lb_page(b, st)
            await pg.wait_for_timeout(2500)
            s = await m(pg)
            card = await pg.evaluate("()=>document.getElementById('csOv').classList.contains('on')")
            ok('(b) callsign exists: no card, nothing playing before a tap', not card and s['playing'] is None and not s['allowed'], (card, s))
            await pg.touchscreen.tap(420, 8)
            s = await wait_for(pg, lambda s: s['playing'])
            ok('(b) music starts on the first tap', s['allowed'] and s['playing'] is not None, s)
            ok('(b) no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()

            # (c) LB origin, fresh profile, the Worker is unreachable: no card, first tap plays
            pg = await lb_page(b, dict(seed, kgeuOnboard='pilot'), worker=dead_worker)
            await pg.wait_for_timeout(1500)
            s = await m(pg)
            ok('(c) Worker down: nothing before a tap', s['playing'] is None and not s['allowed'], s)
            await pg.touchscreen.tap(420, 8)
            s = await wait_for(pg, lambda s: s['playing'])
            card = await pg.evaluate("()=>document.getElementById('csOv').classList.contains('on')")
            ok('(c) Worker down: no card, music on the first tap', not card and s['playing'] is not None, (card, s))
            await pg.context.close()

            # (d) LB off: the plain harness origin
            pg = await page(b, url, vp=IPHONE_15, storage=dict(seed, kgeuOnboard='pilot'))
            await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
            await pg.evaluate("()=>{window.__kgeu.musicTick();window.dispatchEvent(new Event('visibilitychange'))}")
            await pg.wait_for_timeout(2000)
            s = await m(pg)
            lb = await pg.evaluate("()=>window.__kgeu.LB.E.enabled")
            ok('(d) LB off: nothing before the first gesture, even after ticks', not lb and s['playing'] is None and not s['allowed'], (lb, s))
            await pg.touchscreen.tap(420, 8)
            s = await wait_for(pg, lambda s: s['playing'])
            ok('(d) LB off: music after the first gesture', s['allowed'] and s['playing'] is not None, s)
            ok('(d) no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
            await b.close()
    finally:
        game.shutdown(); srv.shutdown()
    return ok.done('music_start_check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
