# Screenshots for Red Flag Dogfight (5.1), modelled on tests/dogfight_check.py and the shot
# helpers in tests/world_region_shots.py. iPhone 15 landscape (844x390, device scale 2).
#
# The headless build renders at about 3 fps under software rendering, so bulk sim time is
# advanced fast with stepFrame's skipRender flag (no draw, cheap) and only a short burst of
# real stepFrame calls (which do draw) runs right before each screenshot -- the same split
# tests/world_region_shots.py uses (TAKEOFF_STEP vs settle()).
#
# Usage: .venv/bin/python tests/dogfight_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger, IPHONE_15

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'dogfight'))
K = 'window.__kgeu'


async def fast(pg, secs, dt=0.1):
    """Advance sim time without drawing: physics, AI and timers run, nothing paints."""
    n = int(round(secs / dt))
    await pg.evaluate("(a)=>{const n=a[0],dt=a[1];const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);}", [n, dt])


async def settle(pg, n=12):
    """Real frames (they draw): enough to clear the HUD's 80 ms refresh throttle."""
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)


async def shot(pg, name, n=12):
    await settle(pg, n)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def kill_wave(pg):
    await pg.evaluate(f"()=>{{const D={K}.DF;D.bandits.slice().forEach(b=>{K}.dfKill(b,'test'));}}")


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'cessna'})

        # 1: the ARCADE screen, Red Flag Dogfight card
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
        await shot(pg, '51_arcade_card.png')

        # 2: just after the dogfight starts -- HUD, wave line, bandit ahead
        await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(600)
        await shot(pg, '51_start.png')

        # 3: the wave 1 bandit seen close, with freeCam (world coordinates) rather than the
        # game's own chase camera: on the player's exact bearing to the bandit, the chase rig
        # puts the bandit directly behind the player's own tail (tried first -- the player's
        # own aircraft was all that showed, the bandit hidden dead astern of it). A dead-astern
        # freeCam on the bandit itself showed only its tailpipe, so this sits off to one side
        # and above -- a rear 3/4, ~240 m out, 70 m up -- so the splinter camo on the spine and
        # wings is in view, at a 17 deg fov (a gun-camera/zoomed framing of a 250 m contact).
        info = await pg.evaluate(f"""()=>{{const K={K},b=K.DF.bandits[0],h=b.hdg+2.6;
          const camP=[b.p.x+Math.sin(h)*240,b.p.y+70,b.p.z-Math.cos(h)*240],camT=[b.p.x,b.p.y+1,b.p.z];
          K.freeCam({{w:true,p:camP,t:camT,fov:17}});
          return {{camP:camP,bp:b.p.toArray()}};}}""")
        print('  bandit close freeCam', info)
        await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", 2)
        await pg.screenshot(path=os.path.join(OUT, '51_bandit_close.png')); print('  wrote 51_bandit_close.png')

        # 4: one or two frames after a kill on that same close bandit -- airburst, smoke.
        # Keep freeCam fixed on the same spot so the explosion lands in frame.
        await pg.evaluate(f"()=>{{{K}.dfKill({K}.DF.bandits[0],'test');}}")
        await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", 2)
        await pg.screenshot(path=os.path.join(OUT, '51_kill.png')); print('  wrote 51_kill.png')
        await pg.evaluate(f"()=>{K}.freeCam(null)")   # back to the normal chase camera

        # wave 1 is now clear (the breather), wave 2 (2 bandits) spawns after the ~4 s gap
        await fast(pg, 5)
        await kill_wave(pg)
        # wave 3 (3 bandits) after its gap
        await fast(pg, 5)
        await kill_wave(pg)
        # wave 4 (4 bandits) after its gap
        await fast(pg, 5)
        w = await pg.evaluate(f"()=>({{wave:{K}.DF.wave,n:{K}.DF.bandits.length}})")
        print('  wave4 state', w)

        # 5: wave 4, the default chase view, no camera trickery. (Tried aiming the player at
        # the bandits' mean bearing first: dfWave's own fan for 4 bandits spans up to ~160
        # degrees -- (i-1.5)*0.95 rad either side of the heading at spawn, +/-82 deg -- wider
        # than any single lens, so forcing the "mean" bearing just swung the nose through the
        # bandits without ever framing more than one or two. Taking it as the player actually
        # sees it is the more honest shot.)
        await shot(pg, '51_wave4.png')

        # finish the win
        await kill_wave(pg)
        await fast(pg, 3.5)
        r = await pg.evaluate(f"()=>({{won:{K}.DF.won,kills:{K}.DF.kills,on:document.getElementById('arcOv').classList.contains('on')}})")
        print('  result state', r)
        await shot(pg, '51_results.png')

        # back to the menu cleanly (MAIN MENU button -> resMenu -> openMenu -> hudClear -> dfStop)
        await finger(pg, '#aHub'); await pg.wait_for_timeout(400)

        # 6/7: the full map -- the Red Flag Dogfight icon and the Barry M. Goldwater Range name,
        # once with the legend collapsed (an unobstructed view of the icon and name) and once
        # with it open (the legend itself, as asked)
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}"); await pg.wait_for_timeout(800)
        await pg.evaluate(f"()=>{{{K}.fmOpen();{K}.FM.cx={K}.DF.C.x;{K}.FM.cz={K}.DF.C.z;{K}.FM.scale=0.02;{K}.fmFlush();}}")
        await pg.wait_for_timeout(200)
        mp = await pg.evaluate(f"()=>{{const L={K}.LBL();return {{icon:L.placed.some(p=>p.kind==='dogfight'),leg:document.getElementById('mapLeg').classList.contains('min')}}}}")
        print('  map state', mp)
        await finger(pg, '#mapLegT'); await pg.wait_for_timeout(200)   # collapse the legend
        await shot(pg, '51_map.png')
        await finger(pg, '#mapLegT'); await pg.wait_for_timeout(200)   # reopen it
        await shot(pg, '51_map_legend.png')

        if pg.errs:
            print('  console errors:', pg.errs[:5])
        else:
            print('  no console errors')
        await b.close()
    srv.shutdown()

asyncio.run(main())
