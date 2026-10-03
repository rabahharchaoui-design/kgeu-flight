# Screenshots for Red Flag Dogfight. iPhone 15 landscape (844x390, device scale 2) unless noted.
#
# The headless build renders at about 3 fps under software rendering, so bulk sim time is
# advanced fast with stepFrame's skipRender flag (no draw, cheap) and only a short burst of
# real stepFrame calls (which do draw) runs right before each screenshot -- the same split
# tests/world_region_shots.py uses (TAKEOFF_STEP vs settle()).
#
# Usage:
#   .venv/bin/python tests/dogfight_shots.py --set 51                 (5.1 shots, the original set)
#   .venv/bin/python tests/dogfight_shots.py --set 52                 (5.2 shots, all of them)
#   .venv/bin/python tests/dogfight_shots.py --set 52 --only gun,lock (a subset -- keeps one run under 100 s)
#
# 5.2 shot names: buttons (also writes 52_buttons_568.png), search, lock, missile, gun, killcam
import asyncio, os, argparse
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger, IPHONE_15

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'dogfight'))
K = 'window.__kgeu'

# bandit i at d metres along the nose (or off it by off radians, positive to the left), flying our way and
# speed: straight and level (test.hold). Lifted from tests/dogfight_weapons_check.py's PLACE helper.
PLACE = """([i,d,off])=>{const K=window.__kgeu,s=K.state(),D=K.DF,b=D.bandits[i];D.test.hold=true;
  const q=s.quat.clone();if(off)q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),off));
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(q);b.p.copy(s.pos).addScaledVector(n,d);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);return true;}"""
GUNHOLD = "(on)=>{const g=document.getElementById('bGun');g.dispatchEvent(new PointerEvent(on?'pointerdown':'pointerup',{pointerId:77,bubbles:true,pointerType:'touch',isPrimary:false}));}"


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


async def place(pg, i, d, off=0.0):
    await pg.evaluate(PLACE, [i, d, off])


async def gunhold(pg, on):
    await pg.evaluate(GUNHOLD, on)


async def wait_lock(pg, timeout=4.0):
    """Fast-forward in 0.1 s ticks until DF.seek.state is 'lock', or give up."""
    t = 0.0
    while t < timeout:
        await fast(pg, 0.1); t += 0.1
        if await pg.evaluate(f"()=>{K}.DF.seek.state") == 'lock':
            return True
    return False


async def dfstart_f16(pg):
    """The 5.2 shots place bandits by hand, so skip the menu/card flow and start the dogfight
    directly as tests/dogfight_weapons_check.py does, with the aircraft forced to the F-16."""
    await pg.evaluate(f"()=>{K}.dfStart()")
    await pg.wait_for_timeout(500)
    await fast(pg, 0.3)


async def new_page(b, url, type_='cessna'):
    return await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': type_})


# ===================== 5.1 =====================
async def run_51(pg):
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


# ===================== 5.2 =====================
async def shot52_buttons(pg):
    await dfstart_f16(pg)
    await kill_wave(pg); await fast(pg, 5)   # -> wave 2 (2 bandits)
    await kill_wave(pg); await fast(pg, 5)   # -> wave 3 (3 bandits)
    w = await pg.evaluate(f"()=>({{wave:{K}.DF.wave,n:{K}.DF.bandits.length}})")
    print('  buttons: wave state', w)
    await place(pg, 0, 1400, -0.35)   # two in view, boxed
    await place(pg, 1, 1900, 0.35)
    await place(pg, 2, 1600, 2.6)     # behind: an edge arrow
    await fast(pg, 0.3)
    await shot(pg, '52_buttons.png')
    await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400); await fast(pg, 0.1)
    await shot(pg, '52_buttons_568.png')
    await pg.set_viewport_size(IPHONE_15)


async def shot52_search(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, 0)
    await fast(pg, 0.5)   # under the 1.5 s lock time: still searching
    st = await pg.evaluate(f"()=>{K}.DF.seek.state")
    print('  search: seek.state', st)
    await shot(pg, '52_search.png')


async def shot52_lock(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, 0)
    locked = await wait_lock(pg)
    print('  lock: locked', locked)
    await shot(pg, '52_lock.png')


async def shot52_missile(pg):
    await dfstart_f16(pg)
    # a little off boresight so the missile reads as a separate object from the bandit's own box,
    # rather than both sitting on the same dead-ahead point
    await place(pg, 0, 1700, 0.05)
    await wait_lock(pg)
    await pg.evaluate(f"()=>{{{K}.DF.test.noDecoy=true;}}")
    await finger(pg, '#bFox')
    await fast(pg, 0.9)   # 0.5-1 s after launch: still in flight (it kills at ~1.6 s), well separated by now
    m = await pg.evaluate(f"()=>({{on:{K}.DF.msl.filter(m=>m.on).length,alive:{K}.DF.bandits[0].alive}})")
    print('  missile: state', m)
    await shot(pg, '52_missile.png')


async def shot52_gun(pg):
    await dfstart_f16(pg)
    # off boresight: dead ahead the pipper and the tracer stream sit right on top of the target
    # box and read as nothing happening -- a slight offset separates the pipper (the lead
    # computing sight) from the box so the tracer stream reads as a stream, not a point
    await place(pg, 0, 400, 0.1)
    await fast(pg, 0.1)
    await gunhold(pg, True)
    await fast(pg, 0.12)                 # short burst: a 400 m kill takes 0.35 s of full-rate fire
    await shot(pg, '52_gun.png', n=6)    # fewer draw frames too, to stay well under the kill threshold
    await gunhold(pg, False)
    g = await pg.evaluate(f"()=>({{alive:{K}.DF.bandits[0].alive,hp:{K}.DF.bandits[0].hp,trc:{K}.DF.trc.filter(t=>t.on).length}})")
    print('  gun: state', g)


async def shot52_killcam(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, 0)
    await wait_lock(pg)
    await pg.evaluate(f"()=>{{{K}.DF.test.noDecoy=true;}}")
    await finger(pg, '#bFox')
    t, alive = 0.0, True
    while t < 12 and alive:
        await fast(pg, 0.1); t += 0.1
        alive = await pg.evaluate(f"()=>{K}.DF.bandits[0].alive")
    kc = await pg.evaluate(f"()=>({{kc:{K}.DF.kc,dim:document.body.classList.contains('dfKc')}})")
    print('  killcam: state', kc)
    await shot(pg, '52_killcam.png')


SHOTS_52 = {'buttons': shot52_buttons, 'search': shot52_search, 'lock': shot52_lock,
            'missile': shot52_missile, 'gun': shot52_gun, 'killcam': shot52_killcam}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', choices=['51', '52'], default='51')
    ap.add_argument('--only', default=None, help='comma-separated subset of 5.2 shot names')
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if args.set == '51':
            pg = await new_page(b, url, 'cessna')
            await run_51(pg)
            if pg.errs:
                print('  console errors:', pg.errs[:5])
            else:
                print('  no console errors')
        else:
            names = args.only.split(',') if args.only else list(SHOTS_52.keys())
            for name in names:
                name = name.strip()
                fn = SHOTS_52.get(name)
                if not fn:
                    print('  unknown 5.2 shot:', name); continue
                pg = await new_page(b, url, 'f16')
                await fn(pg)
                if pg.errs:
                    print(f'  console errors ({name}):', pg.errs[:5])
                else:
                    print(f'  no console errors ({name})')
                await pg.close()
        await b.close()
    srv.shutdown()

asyncio.run(main())
