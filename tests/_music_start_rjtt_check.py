# Throwaway: music_start_check (d) LB-off scenario repeated with kgeuRegion='rjtt' in storage,
# since music_start_check.py's storage dict is just localStorage key/values and accepts it directly.
# Not part of run_all; verification only. Run: .venv/bin/python tests/_music_start_rjtt_check.py
import asyncio, sys, os
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, page, Checks, THREE, IPHONE_15
from music_start_check import TONES, M, wait_for, m

ok = Checks()
ARGS = ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader',
        '--autoplay-policy=no-user-gesture-required']

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=ARGS)
        seed = {'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuOnboard': 'pilot', 'kgeuRegion': 'rjtt'}
        pg = await page(b, url, vp=IPHONE_15, storage=seed)
        reg = await pg.evaluate("()=>localStorage.getItem('kgeuRegion')")
        ok('region is rjtt', reg == 'rjtt', reg)
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
        await pg.evaluate("()=>{window.__kgeu.musicTick();window.dispatchEvent(new Event('visibilitychange'))}")
        await pg.wait_for_timeout(1500)
        s = await m(pg)
        ok('rjtt: nothing before the first gesture', s['playing'] is None and not s['allowed'], s)
        await pg.touchscreen.tap(420, 8)
        s = await wait_for(pg, lambda s: s['allowed'])
        await pg.wait_for_timeout(1500); s = await m(pg)
        ok('rjtt: the gate opens on the first gesture, menu stays silent', s['allowed'] and s['playing'] is None, s)
        # mission('drop')/lesson/arcade are Arizona-only and would switch region + reload
        # (same as world_ui_check's "rjtt airdrop" case). Free flight itself only wants music
        # if the player presses Play (MUSIC.free, per musicCtx()'s comment in index.html), so
        # start a free flight in rjtt and press the pause sheet's Play button like a real player.
        await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.start('runway')}")
        await pg.wait_for_timeout(500)
        await pg.tap('#bPause')
        await pg.wait_for_timeout(300)
        await pg.tap('#pMusic')
        s = await wait_for(pg, lambda s: s['playing'])
        ok('rjtt: free flight music starts once the player presses Play', s['playing'] is not None, s)
        reg2 = await pg.evaluate("()=>localStorage.getItem('kgeuRegion')")
        ok('rjtt: still in rjtt (no region switch)', reg2 == 'rjtt', reg2)
        errs = await pg.evaluate("()=>window.__errs||[]")
        await pg.context.close()
        await b.close()
    srv.shutdown()
    return ok.done('music_start_rjtt_check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
