# One-off screenshot script for phone notes 0929, item 9 (nose wheel steering from
# ~1 kt at idle). Shows the Cessna and the C-130 each mid-turn on the runway/taxiway
# at low ground speed with idle throttle, HUD showing the speed readout and the
# throttle grip parked at IDLE.
# Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item09_shots.py
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, THREE, IGNORE, splash_gone

SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'overnight-screenshots', 'phone0929', 'item09')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'
VP = {'width': 844, 'height': 390}

# put the aircraft on runway 1 at idle rolling at kt, no wind, then hold the stick at
# ail for sec so a turn is well underway when the shot is taken
TURN = """([kt,ail,sec])=>{const K=window.__kgeu;K.start('runway');const s=K.state(),T=THREE;
  s.windKt=0;s.gustAmp=0;s.throttle=s.power=0;s.brake=false;s.ap=null;s.apW=null;s.w.set(0,0,0);
  const f=new T.Vector3(0,0,-1).applyQuaternion(s.quat);f.y=0;f.normalize();const V=kt/1.94384;
  s.vel.set(f.x*V,0,f.z*V);K.touchIn.active=true;K.touchIn.elev=0;K.touchIn.ail=ail;
  const n=Math.round(sec*60);
  for(let i=0;i<n;i++)K.stepFrame(1/60,false,true);
  return {kt:Math.hypot(s.vel.x,s.vel.z)*1.94384,ground:s.onGround,crashed:s.crashed?s.crashReason:''};}"""

async def shot(pg, name, note=''):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f'wrote {path}' + (f'  {note}' if note else ''))

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        for t in ['cessna', 'c130']:
            ctx = await b.new_context(viewport=VP, has_touch=True, is_mobile=True, device_scale_factor=2)
            await ctx.add_init_script("(()=>{if(sessionStorage.getItem('__seeded'))return;sessionStorage.setItem('__seeded','1');localStorage.clear();"
                "localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');"
                f"localStorage.setItem('kgeuType','{t}');}})()")
            pg = await ctx.new_page(); pg.errs = []
            pg.on('pageerror', lambda e: pg.errs.append(str(e)))
            pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
            await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
            await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
            await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
            await pg.goto(url); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await splash_gone(pg)
            await pg.evaluate(f"()=>{{const K={K};K.pick('{t}');K.pickBase('kgeu');K.start('runway');}}")
            await pg.wait_for_timeout(300)
            res = await pg.evaluate(TURN, [5, 1.0, 2.5])
            print(t, 'turn state:', res)
            # freeze the input at full deflection and idle throttle, then render one frame for the shot
            await pg.evaluate(f"()=>{{const K={K},s=K.state();s.throttle=s.power=0;K.stepFrame(0,true);}}")
            await pg.wait_for_timeout(150)
            hud = await pg.evaluate("()=>({ias:document.getElementById('hIas').textContent,thr:document.getElementById('thrGrip').getBoundingClientRect().top})")
            print(t, 'hud:', hud)
            await shot(pg, f'item09_{t}_midturn_idle.png', res)
            print(t, 'errs:', pg.errs[:5])
            await ctx.close()
        await b.close()
    srv.shutdown()

asyncio.run(main())
