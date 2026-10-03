# Throwaway screenshots for item 4.6b (region location picker, pause sheet, per region
# map, credits). iPhone landscape, Hard mode (kgeuOnboard=pilot). Follows the same
# recipe as tests/world_ui_check.py (read first): seed localStorage with kgeuRegion,
# wait on window.__kgeu.WORLD.ready for a non Arizona region, then use K.pick/pickBase/
# pickPos/start, K.fmOpen/fmFlush/FM.cx/cz/scale for the map, finger() for real taps.
# Verification only -- does not touch game code. Not part of run_all.
# Usage: .venv/bin/python tests/world_ui_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger, IPHONE_15, IPHONE_SE, ROOT

OUT = os.path.join(ROOT, 'overnight-screenshots', 'world', 'ui')
os.makedirs(OUT, exist_ok=True)
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
HOME = {'rjtt': '34R', 'lfpg': '26L', 'sbrj': '20L'}


async def settle(pg, n=12):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path)
    print('  wrote', path)


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        # (a) FLY in Arizona, 844x390 and 667x375, plus a scroll to Tokyo
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(500)
        await shot(pg, 'fly_az_844.png')
        await pg.set_viewport_size(IPHONE_SE); await pg.wait_for_timeout(400)
        await shot(pg, 'fly_az_667.png')
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        await pg.evaluate("()=>{const c=document.querySelector('#sFly .pick[data-b=rjtt]'),L=c.closest('.locs');L.scrollLeft=c.closest('.lgrp').offsetLeft;}")
        await pg.wait_for_timeout(300)
        await shot(pg, 'fly_az_844_scrolled.png')
        await pg.context.close()

        # (b) FLY with kgeuRegion rjtt: Tokyo selected, summary line, no Haboob chip
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion='rjtt'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
        await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(500)
        await shot(pg, 'fly_rjtt_844.png')
        await pg.context.close()

        # (c) pause sheet, Change flight panel with the picker: Paris in flight, 844x390
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion='lfpg'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('lfpg');{K}.start('runway')}}"); await pg.wait_for_timeout(600)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        await shot(pg, 'pause_lfpg.png')
        await pg.context.close()

        # (d) same, Arizona, 667x375
        pg = await page(b, url, vp=IPHONE_SE, storage=BASE)
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}"); await pg.wait_for_timeout(600)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        await shot(pg, 'pause_az_667.png')
        await pg.context.close()

        # (e) the map at each region as it opens, rjtt also zoomed close in, sbrj with a destination set
        for rid in ('rjtt', 'lfpg', 'sbrj'):
            pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion=rid))
            await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('{rid}');{K}.start('final')}}"); await pg.wait_for_timeout(1000)
            await pg.wait_for_function(f"()=>{K}.MAPD.ready", timeout=30000)
            await finger(pg, '#map'); await pg.wait_for_timeout(300)
            await pg.evaluate(f"()=>{K}.fmFlush()"); await pg.wait_for_timeout(200)
            await shot(pg, f'map_{rid}.png')
            if rid == 'rjtt':
                await pg.evaluate(f"()=>{{const K={K},e=K.RWY_ENDS;K.FM.cx=e.reduce((s,q)=>s+q.x,0)/e.length;K.FM.cz=e.reduce((s,q)=>s+q.z,0)/e.length;K.FM.scale=0.07;K.fmFlush();}}")
                await pg.wait_for_timeout(200)
                await shot(pg, 'map_rjtt_zoom.png')
            if rid == 'sbrj':
                q = await pg.evaluate(f"()=>{{const K={K},e=K.RWY_ENDS.find(e=>e.num==='{HOME[rid]}');return K.fmP(e.x,e.z)}}")
                await pg.touchscreen.tap(q[0], q[1]); await pg.wait_for_timeout(400)
                await pg.evaluate(f"()=>{K}.fmFlush()"); await pg.wait_for_timeout(200)
                await shot(pg, 'map_sbrj_dest.png')
            await pg.context.close()

        # (f) mini map at Rio, 3 mile final
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion='sbrj'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
        # POS_OK = ['runway','ramp','final1','final'] in index.html -- 'final' is the 3 mile final
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('sbrj');{K}.pickPos('final');{K}.start('final')}}"); await pg.wait_for_timeout(1000)
        await settle(pg)
        await shot(pg, 'minimap_sbrj.png')
        await pg.context.close()

        # (g) Settings credits footer, 667x375
        pg = await page(b, url, vp=IPHONE_SE, storage=BASE)
        await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(300)
        await shot(pg, 'settings_credits.png')
        await pg.context.close()

        # (h) MISSIONS at Tokyo, ARIZONA tags
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion='rjtt'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
        await pg.evaluate(f"()=>{K}.openMenu('sMis')"); await pg.wait_for_timeout(400)
        await shot(pg, 'missions_rjtt.png')
        await pg.context.close()

        await b.close()
    srv.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
