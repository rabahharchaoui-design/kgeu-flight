# Throwaway screenshot script for the World airports leaderboard work (uncommitted on `world`).
# Modeled on tests/world_lb_check.py's recipes (mocked Date via sessionStorage.__off, the stubbed
# Worker at http://lb.test, the arc 'apt'/'daily' resume objects, the real-reload pattern) and on
# tests/paris_shots.py's place()/PLACE_PIN camera pinning for the billboard close-up.
# iPhone landscape 844x390 @2x unless stated. Usage: .venv/bin/python tests/world_lb_shots.py
import asyncio, os, sys, json, math
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, launch, IPHONE_15, finger, THREE, splash_gone

K = 'window.__kgeu'
WK = 'http://lb.test'
ME = 'HABOOB'
OUT = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'lb')
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuType': 'cessna', 'kgeuLBUrl': WK,
        'kgeuLB': json.dumps({'cs': ME, 'key': 'a' * 48, 'xp': 100})}
STUB = "()=>{window.__kgeuReload=()=>{window.__reloaded=(window.__reloaded||0)+1;};}"
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
FAME = {'day': 0, 'daily': None, 'top': [], 'apt': {'RJTT': None, 'LFPG': None, 'SBRJ': None}}
DATE = """(()=>{const R=Date,off=()=>{try{return +(sessionStorage.getItem('__off')||0);}catch(e){return 0;}};
  class D extends R{constructor(...a){if(a.length)super(...a);else super(R.now()+off());}static now(){return R.now()+off();}}
  window.Date=D;})()"""
PLACE_PIN = """([cx,cz,brgDeg,dist,alt,hdgDeg,n])=>{const K=window.__kgeu,r=brgDeg*Math.PI/180,h=hdgDeg*Math.PI/180;
  const x=cx+dist*Math.sin(r),z=cz-dist*Math.cos(r),y=K.groundHeight(x,z)+alt;
  const s=K.state();
  const pin=()=>{s.pos.set(x,y,z);s.vel.set(Math.sin(h)*55,0,-Math.cos(h)*55);
    s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));if(s.w)s.w.set(0,0,0);
    s.onGround=false;s.crashed=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.5;s.flapIdx=0;s.ap=null;};
  pin();K.snapCam();
  for(let i=0;i<n;i++){pin();K.snapCam();K.stepFrame(1/60);}
  pin();K.snapCam();
  return {x,y,z};}"""


async def worker(route):
    req = route.request
    path = req.url[len(WK):].split('?')[0]
    if req.method == 'OPTIONS':
        return await route.fulfill(status=204, headers=CORS)
    body = {}
    try:
        body = json.loads(req.post_data or '{}')
    except Exception:
        pass
    ans = {'/health': {'ok': True}, '/me': {'cs': ME, 'xp': 100, 'creator': False}, '/pool': {'tokens': []}, '/fame': FAME,
           '/token': {'token': 'tok.1', 't0': 0, 'day': 0},
           '/submit': {'ok': True, 'rank': 1, 'total': 1, 'pb': True, 'top10': True, 'best': body.get('score'), 'xp': 150, 'gain': 50},
           '/board': {'board': 'apt:RJTT', 'mode': 'all', 'period': 'today', 'dir': 1, 'total': 0, 'rows': [], 'me': None, 'ghost': None, 'now': 0, 'day': 0},
           '/ghost': {'ghost': None}}.get(path, {})
    await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps(ans))


async def newpage(b, url, storage, vp=IPHONE_15, off=0):
    ctx = await b.new_context(viewport=vp, has_touch=True, is_mobile=True, device_scale_factor=2)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await ctx.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await ctx.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await ctx.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    await ctx.route(WK + '/**', worker)
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
                              + f'sessionStorage.setItem("__off","{off}");'
                              + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    await ctx.add_init_script(DATE)
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    await pg.wait_for_timeout(300)
    return pg


async def after_reload(pg, cond, secs=90):
    for _ in range(secs * 4):
        try:
            if await pg.evaluate(cond):
                return True
        except Exception:
            pass
        await pg.wait_for_timeout(250)
    raise RuntimeError('timed out after the reload: ' + cond)


async def land(pg):
    await pg.evaluate(f"()=>{K}.auto()")
    for _ in range(200):
        await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
        if await pg.evaluate(f"()=>{K}.state().onGround||{K}.state().crashed"):
            break
    for _ in range(40):
        await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(120)
        if await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')"):
            break
    await pg.wait_for_timeout(500)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        # ---- a: ARCADE in Arizona, as it opens and scrolled to World airports ----
        pg = await newpage(b, url, BASE)
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, 'arcade_az_844.png'))
        await pg.evaluate("()=>{const c=document.getElementById('arcCards');c.scrollTop=1e4;}"); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(OUT, 'arcade_az_844_scrolled.png'))
        print('wrote arcade_az_844.png, arcade_az_844_scrolled.png', pg.errs[:3])
        await pg.context.close()

        pg = await newpage(b, url, BASE, vp={'width': 667, 'height': 375})
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>{const c=document.getElementById('arcCards');c.scrollTop=1e4;}"); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(OUT, 'arcade_667_scrolled.png'))
        print('wrote arcade_667_scrolled.png', pg.errs[:3])
        await pg.context.close()

        # ---- b: a Paris (lfpg) daily day, MISSIONS daily card ----
        pg = await newpage(b, url, BASE)
        scan = await pg.evaluate(f"()=>{{const out=[];for(let i=0;i<40;i++){{sessionStorage.setItem('__off',String(i*86400000));const d={K}.dailySpec();out.push([i,d.region]);}}sessionStorage.setItem('__off','0');return out}}")
        paris = next((x[0] for x in scan if x[1] == 'lfpg'), None)
        print('  Paris day offset:', paris)
        await pg.context.close()
        off = (paris or 0) * 86400000
        pg = await newpage(b, url, BASE, off=off)
        d1 = await pg.evaluate(f"()=>{K}.dailySpec()")
        print('  dailySpec:', d1)
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sMis')}}"); await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, 'daily_lfpg_day.png'))
        print('wrote daily_lfpg_day.png', pg.errs[:3])
        await pg.context.close()

        # ---- c: Tokyo Haneda results card ----
        pg = await newpage(b, url, BASE)
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>{const c=document.getElementById('arcCards');c.scrollTop=1e4;}"); await pg.wait_for_timeout(200)
        await pg.evaluate(STUB)
        await finger(pg, '#arcCards .mcard[data-m="apt:RJTT"]'); await pg.wait_for_timeout(300)
        await pg.evaluate("()=>{delete window.__kgeuReload;location.reload();}")
        await after_reload(pg, f"()=>window.__kgeu&&{K}.REGION.id==='rjtt'&&{K}.WORLD.ready&&{K}.ARC.on&&{K}.running()")
        await pg.wait_for_timeout(400)
        await land(pg)
        r = await pg.evaluate("()=>({on:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent})")
        print('  results card:', r)
        await pg.screenshot(path=os.path.join(OUT, 'results_tokyo.png'))
        print('wrote results_tokyo.png', pg.errs[:3])
        await pg.context.close()

        # ---- d: Boards screen, World airports group ----
        pg = await newpage(b, url, BASE)
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen()}}"); await pg.wait_for_timeout(600)
        lbt = await pg.evaluate("()=>[...document.querySelectorAll('#lbList h3, #lbList [data-lbb]')].map(e=>e.textContent)")
        print('  lbList entries:', lbt)
        await pg.evaluate("()=>{const h=[...document.querySelectorAll('#lbList h3')].find(e=>e.textContent.trim()==='World airports');if(h)h.scrollIntoView({block:'start'});}")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, 'boards_world.png'))
        print('wrote boards_world.png', pg.errs[:3])
        await pg.context.close()

        # ---- e: Rio billboard, TESTPILOT champion, close up ----
        pg = await newpage(b, url, dict(BASE, kgeuRegion='sbrj'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=60000)
        await pg.evaluate(f"()=>{K}.LB.fameApply({{day:0,daily:null,top:[],apt:{{SBRJ:{{cs:'TESTPILOT',score:1200,mode:'hard'}}}}}})")
        champ = await pg.evaluate(f"()=>{K}.CITYBB.champ")
        print('  CITYBB.champ:', champ)
        bb = await pg.evaluate(f"()=>{{const b={K}.CITYBB.list[0];return [b.x,b.z,b.hdg]}}")
        hdg_to_board = (bb[2] + 180) % 360
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickPos('final');{K}.start('final');}}"); await pg.wait_for_timeout(300)
        await pg.evaluate(PLACE_PIN, [bb[0], bb[1], bb[2], 40, 20, hdg_to_board, 12])
        await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", 0)
        await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(OUT, 'billboard_champ_rio.png'))
        print('wrote billboard_champ_rio.png', pg.errs[:3])
        await pg.context.close()

        await b.close()

asyncio.run(main())
