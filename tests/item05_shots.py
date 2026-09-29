# One-off screenshot script for phone notes 0929, item 5 (music no longer starts at app open).
# Confirms visually, at iPhone landscape (844x390, dsf 2, mobile, touch), served on
# localhost:8765 like music_start_check.py so the LB gate is live:
#   - the callsign card on a fresh LB profile, with window.__kgeu.music() printed
#     alongside showing nothing playing
#   - the menu after the card is completed, with music playing
# Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item05_shots.py
import asyncio, os, sys, json
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, THREE, IPHONE_15
from scores_check import serve_game

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'phone0929', 'item05')
os.makedirs(SHOTS, exist_ok=True)
WORKER = 'https://pfs-scores.rabahharchaoui.workers.dev'
M = "()=>window.__kgeu.music()"

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

async def lb_page(b, storage):
    ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.route(WORKER + '/**', fake_worker)
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
        + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    await pg.goto('http://localhost:8765/index.html')
    await pg.wait_for_function('()=>window.__kgeu&&window.__kgeu.LB', timeout=30000)
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

async def shot(pg, name, state):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f'wrote {path}  music()={state}')

async def main():
    game = serve_game()
    srv, url = serve()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl',
                '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
            seed = {'kgeuTut': '1', 'kgeuCoach': '3'}

            # fresh LB profile: the callsign card comes up before anything plays
            pg = await lb_page(b, seed)
            await pg.wait_for_function("()=>document.getElementById('csOv').classList.contains('on')", timeout=15000)
            s = await m(pg)
            print('callsign card music() state:', s)
            await shot(pg, 'callsign_card_no_music.png', s)

            # complete the card: claim a callsign, save the recovery code
            await pg.fill('#csIn', 'MESQUITE')
            await pg.wait_for_function("()=>/is free/.test(document.getElementById('csStat').textContent)", timeout=10000)
            await pg.tap('#csGo')
            await pg.wait_for_function("()=>!document.getElementById('csCode').hidden", timeout=10000)
            await pg.tap('#csGo')
            s = await wait_for(pg, lambda s: s['playing'])
            print('after closing card, music() state:', s)
            await pg.wait_for_timeout(400)
            await shot(pg, 'menu_music_playing.png', s)
            print('errs:', pg.errs[:5])
            await pg.context.close()
            await b.close()
    finally:
        game.shutdown(); srv.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
