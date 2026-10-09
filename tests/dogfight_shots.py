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
#   .venv/bin/python tests/dogfight_shots.py --set 53                 (5.3 defense shots, all of them)
#   .venv/bin/python tests/dogfight_shots.py --set 53 --only lock,launch (a subset)
#
# 5.2 shot names: buttons (also writes 52_buttons_568.png), search, lock, missile, gun, killcam
# 5.3 shot names: lock, launch, launch_easy, flares, hit2, harddeck, eject, launch_568, high
# 5.4 shot names: brief, brief_easy, brief_568, brief_silent, arrows (also writes 54b_arrows_568.png), lock, awacs
import asyncio, os, json, argparse
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger, IPHONE_15, THREE, splash_gone, IGNORE

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
# feet (dogfight HUD altitude) -> world y metres, lifted from tests/dogfight_defense_check.py
FTY = "(ft)=>(ft-1071)/3.28084+1.5"


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
    await pg.evaluate(f"()=>{{{K}.DF.test.noBrief=true;{K}.dfStart();}}")
    await pg.wait_for_timeout(500)
    await fast(pg, 0.3)


async def new_page(b, url, type_='cessna', vp=IPHONE_15, skill='pilot'):
    return await page(b, url, vp=vp, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuType': type_})


async def wait_rwr(pg, target, timeout=16.0):
    """Fast-forward in 0.1 s ticks until DF.rwr reaches target ('search'/'lock'/'launch'), or give up.
    #dfVig's amber/red edges are a CSS animation (dfVp, infinite alternate) driven by real wallclock
    time, not sim time: the class is added the instant rwr flips, so a screenshot taken immediately
    (as fast() leaves no real time between ticks) always lands on the animation's 'from' keyframe
    (opacity .2) -- the pulse reads as basically invisible. A short real wait afterwards lets the
    pulse move into its visible range before the caller screenshots."""
    t = 0.0
    while t < timeout:
        await fast(pg, 0.1); t += 0.1
        if await pg.evaluate(f"()=>{K}.DF.rwr") == target:
            await pg.wait_for_timeout(250)
            return t
    return None


async def wait_missile_gone(pg, timeout=10.0):
    """Fast-forward until no live bandit missile remains (hit, miss or decoyed), or give up."""
    t = 0.0
    while t < timeout:
        await fast(pg, 0.1); t += 0.1
        if not await pg.evaluate(f"()=>{K}.DF.msl.some(m=>m.on&&m.foe)"):
            return t
    return None


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


# ===================== 5.3 =====================
# All of these place bandit 0 on our six (off=pi, "straight behind") so the missile/RWR arrow
# reads as a 6 o'clock threat, matching tests/dogfight_defense_check.py's own PLACE usage.
SIX = 3.14159


async def shot53_lock(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, SIX)
    t = await wait_rwr(pg, 'lock')
    print('  lock: t', t)
    await shot(pg, '53_lock.png')


async def shot53_launch(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, SIX)
    t = await wait_rwr(pg, 'launch')
    print('  launch: t', t)
    await shot(pg, '53_launch.png')


async def shot53_launch_easy(pg):
    # the page is already loaded with kgeuOnboard=rookie (new_page's skill=); dfStart reads SKILL at call time
    await dfstart_f16(pg)
    await place(pg, 0, 1500, SIX)
    t = await wait_rwr(pg, 'launch')
    print('  launch_easy: t', t)
    await shot(pg, '53_launch_easy.png')


async def shot53_launch_568(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, SIX)
    t = await wait_rwr(pg, 'launch')
    print('  launch_568: t', t)
    await shot(pg, '53_launch_568.png')


async def shot53_flares(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, SIX)
    await wait_rwr(pg, 'launch')
    await finger(pg, '#bFlr')
    f = await pg.evaluate(f"()=>{K}.DF.flares")
    print('  flares: count', f)
    await shot(pg, '53_flares.png')


async def shot53_hit2(pg):
    await dfstart_f16(pg)
    for _ in range(2):   # straight and level: each forced launch hits, per dogfight_defense_check.py
        await place(pg, 0, 1500, SIX)
        await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
        await wait_missile_gone(pg)
        await fast(pg, 2.2)   # clear of the hit-flash cooldown before the next
    h = await pg.evaluate(f"()=>{K}.DF.hits")
    print('  hit2: hits', h)
    await shot(pg, '53_hit2.png')


async def shot53_harddeck(pg):
    await dfstart_f16(pg)
    await fast(pg, 3)   # clear of the "fight's on" intro line so it doesn't join the Pull up call in the strip
    y = await pg.evaluate(FTY, 5700)
    await pg.evaluate("([y])=>{const s=window.__kgeu.state();s.pos.y=y;s.vel.y=-12;}", [y])
    await fast(pg, 0.3)
    w = await pg.evaluate("()=>document.getElementById('warn').textContent")
    print('  harddeck: warn', w)
    await shot(pg, '53_harddeck.png')


async def shot53_eject(pg):
    await dfstart_f16(pg)
    for _ in range(3):
        await place(pg, 0, 1500, SIX)
        await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
        await wait_missile_gone(pg)
        await fast(pg, 2.2)
    await fast(pg, 2.5)
    await pg.wait_for_timeout(300)
    r = await pg.evaluate(f"()=>({{ej:{K}.DF.ej,card:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent}})")
    print('  eject: state', r)
    await shot(pg, '53_eject.png')


async def shot53_high(pg):
    # The normal chase camera reads nothing but sky at 25,000 ft: level flight puts the true horizon
    # at roughly the same screen row at any altitude, but terrain only streams in out to a radius tuned
    # for low-altitude flight, so the ground this far below the sightline to that horizon is simply never
    # built -- not a white patch or a torn edge, just empty fog-colored sky where ground should be. A
    # freeCam a little above and behind, pitched down at the arena (as tests/dogfight_shots.py's own 5.1
    # shots do for framing bandits), is the only way to actually see the ground and check it for glitches.
    await dfstart_f16(pg)
    y = await pg.evaluate(FTY, 25000)
    await pg.evaluate("([y])=>{const s=window.__kgeu.state();s.pos.y=y;s.vel.y=0;}", [y])
    await pg.evaluate(f"""()=>{{const K={K},s=K.state(),hdg=Math.atan2(s.vel.x,-s.vel.z);
      const camP=[s.pos.x-Math.sin(hdg)*700,s.pos.y+400,s.pos.z+Math.cos(hdg)*700];
      const camT=[s.pos.x+Math.sin(hdg)*1800,s.pos.y-1300,s.pos.z-Math.cos(hdg)*1800];
      K.freeCam({{w:true,p:camP,t:camT,fov:55}});}}""")
    await fast(pg, 0.5)
    await shot(pg, '53_high.png')


# name -> (shot fn, viewport override, skill override); None means the 5.3 default (f16, 844x390, pilot)
SHOTS_53 = {
    'lock': (shot53_lock, None, None),
    'launch': (shot53_launch, None, None),
    'launch_easy': (shot53_launch_easy, None, 'rookie'),
    'flares': (shot53_flares, None, None),
    'hit2': (shot53_hit2, None, None),
    'harddeck': (shot53_harddeck, None, None),
    'eject': (shot53_eject, None, None),
    'launch_568': (shot53_launch_568, {'width': 568, 'height': 320}, None),
    'high': (shot53_high, None, None),
}


# ===================== 5.4 (54b: the briefing card, voices, arrows, amber lock) =====================
IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'


async def new_page_ios(b, url, skill='pilot'):
    """An iPhone-UA context with no navigator.audioSession stub at all (unlike the real iPhone this
    doesn't have one, which is Chromium's actual default) -- IS_IOS reads true from the UA string, so
    the briefing card's 'Turn off silent mode' line shows, matching dogfight_voice_check.py's own case."""
    ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2, user_agent=IPHONE_UA)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
        f'localStorage.setItem("kgeuOnboard",{skill!r});localStorage.setItem("kgeuTut","1");localStorage.setItem("kgeuType","f16");}})()')
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    await pg.wait_for_timeout(300)
    return pg


async def dfopen_brief(pg):
    """From the menu: Arcade -> tap the Red Flag Dogfight card -> the briefing card shows (no test.noBrief,
    the normal path a player takes)."""
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
    await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(500)


async def shot54b_brief(pg, name):
    await dfopen_brief(pg)
    r = await pg.evaluate("""()=>{const g=document.getElementById('dfbNext').getBoundingClientRect();
      return {mode:document.getElementById('dfbMode').textContent,fits:g.bottom<=innerHeight&&g.top>=0,btn:[g.width,g.height]}}""")
    print(f'  {name}: state', r)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def shot54b_brief_hard(pg):
    await shot54b_brief(pg, '54b_brief.png')


async def shot54b_brief_easy(pg):
    await shot54b_brief(pg, '54b_brief_easy.png')


async def shot54b_brief_568(pg):
    await shot54b_brief(pg, '54b_brief_568.png')


async def shot54b_brief_silent(pg):
    await dfopen_brief(pg)
    r = await pg.evaluate("""()=>{const s=document.getElementById('dfbSil');
      return {sil:!s.hidden&&s.offsetParent!==null,txt:s.textContent,as:'audioSession' in navigator}}""")
    print('  brief_silent: state', r)
    path = os.path.join(OUT, '54b_brief_silent.png')
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def shot54b_arrows(pg):
    # bandits at 3, 6 and 9 o'clock (off=+-pi/2 and pi, the same placement dogfight_defense_check.py's
    # own arrows() check uses) plus a forced launch off the 6 o'clock one (bandits[0] -- test.launchAt
    # always fires it) so the red missile arrow shows alongside the three green bandit arrows.
    await pg.evaluate(f"()=>{{{K}.DF.test.noBanditFire=true;{K}.DF.test.noBrief=true;{K}.dfStart();}}")
    await pg.wait_for_timeout(400); await fast(pg, 0.2)
    await pg.evaluate(f"()=>{K}.DF.test.wave(3)")
    for i, off in ((0, SIX), (1, -1.5708), (2, 1.5708)):
        await place(pg, i, 3000 if i == 0 else 2000, off)
    await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
    await fast(pg, 0.2)
    a = await pg.evaluate(f"()=>({{rwr:{K}.DF.rwr,n:{K}.DF.bandits.filter(b=>b.alive).length}})")
    print('  arrows: state', a)
    await shot(pg, '54b_arrows.png')
    await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400); await fast(pg, 0.1)
    await shot(pg, '54b_arrows_568.png')
    await pg.set_viewport_size(IPHONE_15)


async def shot54b_lock(pg):
    await dfstart_f16(pg)
    await place(pg, 0, 1500, SIX)
    t = await wait_rwr(pg, 'lock')
    print('  lock: t', t)
    # the amber edges (#dfVig .a, keyframes dfVa) pulse 0.3 -> 1 opacity on a real-wallclock CSS animation
    # (the sim itself stays frozen -- stepFrame holds loopHeld -- so nothing else moves). This headless,
    # software-rendered browser only advances that animation's clock at an actual style query, not during
    # one long idle wait_for_timeout (a single big sleep then a single read comes back pinned at the 0.3
    # start value); polling with a style read every 50 ms, like wait_rwr's own fast-forward loop, walks it
    # forward for real and lets the screenshot land once it's within sight of its brightest frame.
    await settle(pg, 4)
    await pg.evaluate("()=>{const el=document.getElementById('dfVig');el.classList.remove('lock');void el.offsetHeight;el.classList.add('lock');}")
    op = 0.0
    for _ in range(20):
        await pg.wait_for_timeout(50)
        op = float(await pg.evaluate("()=>getComputedStyle(document.getElementById('dfVig').querySelector('.a')).opacity"))
        if op >= 0.9:
            break
    print('  lock: peak opacity', round(op, 2))
    path = os.path.join(OUT, '54b_lock.png')
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def shot54b_awacs(pg):
    await dfstart_f16(pg)
    await kill_wave(pg)
    await fast(pg, 4.2)   # DF.gap is a fixed 4 s; wave 2 spawns and dfPicture() queues Sentry's call right after
    # dfPicture() only queues the call (vqAdd); the wave-clear "Splash"/"Picture clean" lines queued just
    # before it have to finish airing first, so poll (in small sim ticks) until the Sentry picture line is
    # actually the one on the air, not just the toast or the previous call's leftover text in the strip.
    t = 0.0
    while t < 12.0:
        live = await pg.evaluate(f"()=>{{const c={K}.VQ.cur;return c&&c.line&&c.line.text||''}}")
        if live.startswith('Sentry,'):
            break
        await fast(pg, 0.2); t += 0.2
    w = await pg.evaluate("""()=>({wave:window.__kgeu.DF.wave,sub:document.getElementById('dfSub').classList.contains('on'),
      txt:document.getElementById('dfSub').innerText})""")
    print('  awacs: waited', round(t, 1), 'state', w)
    await shot(pg, '54b_awacs.png')


SHOTS_54B = {
    'brief': (shot54b_brief_hard, None, 'pilot', False),
    'brief_easy': (shot54b_brief_easy, None, 'rookie', False),
    'brief_568': (shot54b_brief_568, {'width': 568, 'height': 320}, 'pilot', False),
    'brief_silent': (shot54b_brief_silent, None, 'pilot', True),
    'arrows': (shot54b_arrows, None, 'pilot', False),
    'lock': (shot54b_lock, None, 'pilot', False),
    'awacs': (shot54b_awacs, None, 'pilot', False),
}


# ===================== 5.5 =====================
# Red Flag Dogfight modes, scoring and the eight leaderboards. Hooks lifted from
# tests/dogfight_modes_check.py (TURN, for the sustained-9g grey vision shot) and
# tests/dogfight_lb_check.py (the stubbed Worker at http://lb.test, win(), the daily hooks).
WK = 'http://lb.test'
ME = 'HABOOB'
CORS55 = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
ROWS55 = [{'r': 1, 'cs': 'VIPER', 'score': 1700, 'secs': 250, 'ac': 'f16', 'mode': 'hard', 'xp': 900, 'rank': 'Wingman', 'creator': False, 'when': 0},
          {'r': 2, 'cs': 'EAGLE', 'score': 1550, 'secs': 230, 'ac': 'f16', 'mode': 'hard', 'xp': 700, 'rank': 'Wingman', 'creator': False, 'when': 0},
          {'r': 3, 'cs': ME, 'score': 1200, 'secs': 210, 'ac': 'f16', 'mode': 'hard', 'xp': 400, 'rank': 'Rookie', 'creator': False, 'when': 0}]


async def worker55(route):
    req = route.request
    path = req.url[len(WK):].split('?')[0]
    if req.method == 'OPTIONS':
        return await route.fulfill(status=204, headers=CORS55)
    body = {}
    try:
        body = json.loads(req.post_data or '{}')
    except Exception:
        pass
    sub = {'ok': True, 'rank': 3, 'total': 40, 'pb': True, 'top10': True, 'best': body.get('score'), 'xp': 400, 'gain': 60, 'rankName': 'Wingman',
           'df': {'kills': {'score': 10, 'rank': 1, 'total': 12, 'pb': True, 'top10': True}, 'clear': {'score': 250, 'rank': 14, 'total': 20, 'pb': True, 'top10': False}, 'guns': None},
           'ach': [{'id': 'ace', 'xp': 150}], 'achXp': 150}
    ans = {'/health': {'ok': True}, '/me': {'cs': ME, 'xp': 250, 'creator': False}, '/pool': {'tokens': []}, '/fame': {'day': 0, 'daily': None, 'top': []},
           '/token': {'token': 'tok.1', 't0': 0, 'day': 0}, '/submit': sub,
           '/board': {'board': 'df:score:hard', 'mode': 'hard', 'period': 'today', 'dir': 1, 'total': 40, 'rows': ROWS55, 'me': None, 'ghost': None, 'now': 0, 'day': 0},
           '/ghost': {'ghost': None}}.get(path, {})
    await route.fulfill(status=200, headers=CORS55, content_type='application/json', body=json.dumps(ans))


async def new_page_lb(b, url, type_='f16', vp=IPHONE_15, skill='pilot', scores=None):
    storage = {'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuType': type_, 'kgeuLBUrl': WK,
               'kgeuLB': json.dumps({'cs': ME, 'key': 'a' * 48, 'xp': 250})}
    if scores:
        storage['kgeuScores'] = json.dumps(scores)
    ctx = await b.new_context(viewport=vp, has_touch=True, is_mobile=True, device_scale_factor=2)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
    await ctx.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await ctx.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await ctx.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    await ctx.route(WK + '/**', worker55)
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
                              + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    await pg.wait_for_timeout(500)
    return pg


async def report(pg, name):
    if pg.errs:
        print(f'  console errors ({name}):', pg.errs[:5])
    else:
        print(f'  no console errors ({name})')


async def until(pg, cond, max_secs, dt=0.1):
    n = int(round(max_secs / dt))
    return await pg.evaluate("""([cond,dt,n])=>{const K=window.__kgeu,D=K.DF,f=new Function('K','D','return ('+cond+')');
      for(let i=0;i<n;i++){K.stepFrame(dt,false,true);if(f(K,D))return true;}return false;}""", [cond, dt, n])


async def kill_wave_how(pg, how):
    await pg.evaluate(f"(h)=>{{const D={K}.DF;D.bandits.slice().forEach((b,i)=>{{if(b.alive){K}.dfKill(b,Array.isArray(h)?h[i%h.length]:h);}});}}", how)


async def start55(pg, skill):
    await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.setSkill('{skill}');D.test.seed=null;D.test.hold=false;D.test.noBanditFire=true;D.test.noBrief=true;K.windSeed(7);K.dfStart();}}")
    await pg.wait_for_timeout(300)
    await fast(pg, 0.2)


async def win55(pg):
    for w in range(4):
        await fast(pg, 2.5)
        await kill_wave_how(pg, ['fox2', 'gun'] if w == 1 else 'fox2')
        await until(pg, "D.gap<=0&&D.bandits.some(b=>b.alive)||!D.on", 10) if w < 3 else await until(pg, "!D.on", 2)


CARD55 = "()=>({on:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText})"


async def s55_results_win(b, url):
    pg = await new_page_lb(b, url)
    await pg.evaluate(f"()=>{{const A={K}.SCORE.ach;delete A.ace;delete A.guns;delete A.untouchable;}}")
    await start55(pg, 'pilot')
    await win55(pg)
    await until(pg, "document.getElementById('arcOv').classList.contains('on')", 8)
    await pg.wait_for_timeout(1500)
    c = await pg.evaluate(CARD55)
    print('  results_win: title', c['title'], '| lines tail', c['lines'][-160:])
    await shot(pg, '55_results_win.png')
    await report(pg, 'results_win')
    await pg.close()


async def s55_results_loss_easy(b, url):
    pg = await new_page(b, url, 'f16', skill='rookie')
    await pg.evaluate(f"()=>{{{K}.DF.test.noBrief=true;{K}.DF.test.noBanditFire=true;{K}.dfStart();}}")
    await pg.wait_for_timeout(400); await fast(pg, 0.3)
    await pg.evaluate(f"()=>{{{K}.dfHit();{K}.dfHit();{K}.dfHit();}}")
    await fast(pg, 2.5)
    await pg.wait_for_timeout(300)
    r = await pg.evaluate(CARD55)
    print('  results_loss_easy: title', r['title'])
    await shot(pg, '55_results_loss_easy.png')
    await report(pg, 'results_loss_easy')
    await pg.close()


async def s55_results_568(b, url):
    pg = await new_page_lb(b, url, vp={'width': 568, 'height': 320})
    await pg.evaluate(f"()=>{{const A={K}.SCORE.ach;delete A.ace;delete A.guns;delete A.untouchable;}}")
    await start55(pg, 'pilot')
    await win55(pg)
    await until(pg, "document.getElementById('arcOv').classList.contains('on')", 8)
    await pg.wait_for_timeout(1500)
    r = await pg.evaluate("""()=>{const sheet=document.querySelector('#arcOv .sheet'),hub=document.getElementById('aHub').getBoundingClientRect(),
      free=document.getElementById('aFree').getBoundingClientRect();
      return {scrollH:sheet.scrollHeight,clientH:sheet.clientHeight,hubFits:hub.bottom<=innerHeight&&hub.top>=0,freeFits:free.bottom<=innerHeight&&free.top>=0}}""")
    print('  results_568: layout', r)
    await shot(pg, '55_results_568.png')
    await report(pg, 'results_568')
    await pg.close()


async def s55_arcade_card(b, url):
    scores = {'log': {'time': 0, 'landings': 0, 'streak': 0, 'bestStreak': 0},
              'best': {'arc:dogfight:hard': {'pts': 2295, 'kills': 10, 'gunKills': 4, 'waves': 4, 'hits': 1, 'secs': 0,
                                              'won': True, 'mode': 'hard', 'ac': 'F-16C Viper', 'stars': 3, 'clr': 0.2}},
              'ach': {}}
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16', 'kgeuScores': json.dumps(scores)})
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(400)
    t = await pg.evaluate('()=>document.querySelector(\'#arcCards [data-m="dogfight"]\').innerText')
    print('  arcade_card: card text', t)
    await shot(pg, '55_arcade_card.png')
    await report(pg, 'arcade_card')
    await pg.close()


async def s55_boards(b, url):
    pg = await new_page_lb(b, url)
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen()}}"); await pg.wait_for_timeout(600)
    await pg.evaluate("""()=>{const hs=[...document.querySelectorAll('#lbList h3')];
      const h=hs.find(e=>e.textContent==='Red Flag Dogfight');if(h)h.scrollIntoView({block:'start'});}""")
    await pg.wait_for_timeout(300)
    await shot(pg, '55_boards.png')
    await report(pg, 'boards')
    await pg.close()


async def s55_board_score_hard(b, url):
    pg = await new_page_lb(b, url)
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen('df:score:hard')}}"); await pg.wait_for_timeout(800)
    r = await pg.evaluate("()=>({t:document.getElementById('lbTitle').textContent,n:document.querySelectorAll('#lbRowsIn .lbRow').length})")
    print('  board_score_hard: state', r)
    await shot(pg, '55_board_score_hard.png')
    await report(pg, 'board_score_hard')
    await pg.close()


async def s55_daily_card(b, url):
    pg = await new_page(b, url, 'f16', skill='pilot')
    await pg.evaluate(f"()=>{{{K}.dailyKind('dogfight');{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(400)
    t = await pg.evaluate('()=>document.querySelector(\'#arcCards .mcard[data-m="daily"]\').innerText')
    print('  daily_card: card text', t)
    await shot(pg, '55_daily_card.png')
    await report(pg, 'daily_card')
    await pg.close()


GREY_BUILD = """(secs)=>{const K=window.__kgeu,T=K.touchIn,s=K.state();
  s.vel.multiplyScalar(600/(s.ias*1.943844));T.active=true;s.throttle=s.power=1;
  const e=new THREE.Euler(0,0,0,'YXZ');
  for(let i=0;i<secs*20;i++){e.setFromQuaternion(s.quat,'YXZ');const bank=-e.z,want=Math.acos(Math.min(0.995,1/9));
    T.ail=Math.max(-1,Math.min(1,(want-bank)*2));T.elev=1;
    K.stepFrame(0.05,false,true);}
  return {gv:K.DF.gv,g:s.gload};}"""
GREY_HOLD = """(n)=>{const K=window.__kgeu,T=K.touchIn,s=K.state();
  const e=new THREE.Euler(0,0,0,'YXZ');
  for(let i=0;i<n;i++){e.setFromQuaternion(s.quat,'YXZ');const bank=-e.z,want=Math.acos(Math.min(0.995,1/9));
    T.ail=Math.max(-1,Math.min(1,(want-bank)*2));T.elev=1;s.throttle=s.power=1;
    K.stepFrame(1/60);}
  T.active=false;return {gv:K.DF.gv,g:s.gload,t:document.getElementById('hG').textContent};}"""


async def s55_grey(b, url):
    pg = await new_page(b, url, 'f16', skill='pilot')
    await dfstart_f16(pg)
    r1 = await pg.evaluate(GREY_BUILD, 4.5)
    r2 = await pg.evaluate(GREY_HOLD, 8)
    print('  grey: build', r1, 'hold', r2)
    path = os.path.join(OUT, '55_grey.png')
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)
    await report(pg, 'grey')
    await pg.close()


async def s55_easy_fight(b, url):
    pg = await new_page(b, url, 'f16', skill='rookie')
    await pg.evaluate(f"()=>{{{K}.DF.test.noBrief=true;{K}.dfStart();}}")
    await pg.wait_for_timeout(500); await fast(pg, 0.3)
    await pg.evaluate(f"()=>{K}.DF.test.wave(2)")
    await place(pg, 0, 1500, 0)      # ahead: our own seeker circle shows, bigger in Easy
    await place(pg, 1, 1500, SIX)    # behind: the threat that launches
    t = await wait_rwr(pg, 'launch')
    print('  easy_fight: launch t', t)
    await shot(pg, '55_easy_fight.png')
    await report(pg, 'easy_fight')
    await pg.close()


async def s55_buttons_vp(b, url, vp, name):
    pg = await new_page(b, url, 'f16', skill='pilot')
    await dfstart_f16(pg)
    await kill_wave(pg); await fast(pg, 5)   # -> wave 2
    await kill_wave(pg); await fast(pg, 5)   # -> wave 3 (3 bandits)
    await place(pg, 0, 1400, -0.35)
    await place(pg, 1, 1900, 0.35)
    await place(pg, 2, 1600, 2.6)
    await fast(pg, 0.3)
    await pg.set_viewport_size({'width': vp[0], 'height': vp[1]}); await pg.wait_for_timeout(400); await fast(pg, 0.1)
    await shot(pg, name)
    await report(pg, name)
    await pg.close()


async def s55_buttons_667(b, url):
    await s55_buttons_vp(b, url, (667, 375), '55_buttons_667.png')


async def s55_buttons_932(b, url):
    await s55_buttons_vp(b, url, (932, 430), '55_buttons_932.png')


SHOTS_55 = {
    'results_win': s55_results_win,
    'results_loss_easy': s55_results_loss_easy,
    'results_568': s55_results_568,
    'arcade_card': s55_arcade_card,
    'boards': s55_boards,
    'board_score_hard': s55_board_score_hard,
    'daily_card': s55_daily_card,
    'grey': s55_grey,
    'easy_fight': s55_easy_fight,
    'buttons_667': s55_buttons_667,
    'buttons_932': s55_buttons_932,
}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', choices=['51', '52', '53', '54b', '55'], default='51')
    ap.add_argument('--only', default=None, help='comma-separated subset of 5.2/5.3 shot names')
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
        elif args.set == '52':
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
        elif args.set == '53':
            names = args.only.split(',') if args.only else list(SHOTS_53.keys())
            for name in names:
                name = name.strip()
                entry = SHOTS_53.get(name)
                if not entry:
                    print('  unknown 5.3 shot:', name); continue
                fn, vp, skill = entry
                pg = await new_page(b, url, 'f16', vp=vp or IPHONE_15, skill=skill or 'pilot')
                await fn(pg)
                if pg.errs:
                    print(f'  console errors ({name}):', pg.errs[:5])
                else:
                    print(f'  no console errors ({name})')
                await pg.close()
        elif args.set == '54b':
            names = args.only.split(',') if args.only else list(SHOTS_54B.keys())
            for name in names:
                name = name.strip()
                entry = SHOTS_54B.get(name)
                if not entry:
                    print('  unknown 54b shot:', name); continue
                fn, vp, skill, ios = entry
                pg = await new_page_ios(b, url, skill=skill or 'pilot') if ios else \
                    await new_page(b, url, 'f16', vp=vp or IPHONE_15, skill=skill or 'pilot')
                await fn(pg)
                if pg.errs:
                    print(f'  console errors ({name}):', pg.errs[:5])
                else:
                    print(f'  no console errors ({name})')
                await pg.close()
        else:
            names = args.only.split(',') if args.only else list(SHOTS_55.keys())
            for name in names:
                name = name.strip()
                fn = SHOTS_55.get(name)
                if not fn:
                    print('  unknown 5.5 shot:', name); continue
                await fn(b, url)
        await b.close()
    srv.shutdown()

asyncio.run(main())
