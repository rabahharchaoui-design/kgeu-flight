# School2 fps: frame rate against the preschool2 tag (the build before any of the School2 lessons), on the same
# method as tests/school_fps.py (read that file first): alternating rounds so machine drift cancels, ms per held
# frame (sim with no render, synced by a readback), FLOOR 0.90. Headless software GL is slow: only the ratio
# between builds means anything, never the absolute ms.
#   .venv/bin/python tests/school2_fps.py <base_root> <new_root> [rounds] [--quick] [--row NAME] [--cert]
# Shared rows (as school_fps.py has them; must cost nothing with no lesson on): the 172 free flight from the
# Glendale runway, the 172 on a 3 mile final, the F-16 free flight, the 172 cockpit view. These run on both the
# preschool2 base and the school2 branch and are compared to each other directly.
# New rows (branch only: none of these lessons exist on preschool2) are each compared instead against the base's
# shared 172-on-a-3-mile-final row (shared_c172_final3), the closest thing the base build has to an airborne 172
# at cruise or on short final:
#   new_pilotage_cruise: Pilotage at cruise with the nav log open and the cue strip. Teleported (not flown) onto
#     the Tolleson leg at 3,500 ft the way school_xc_check.py's own leg geometry works (NAV.legs[1], the course
#     and endpoints), since flying there realistically (climb-out, hold, two full legs) costs several hundred
#     real seconds for no extra render cost.
#   new_divert_card: the diversion card up with the GPS gone, driven the way school_divert_check.py's to_card()
#     and the dust-storm wait do it (pinned flight, no render, so this is fast even though it steps up to 3,000
#     sim frames).
#   new_night_final300: the night pattern on short final at 300 ft AGL, via school_night_check.py's own
#     climbout/downwind/base/final circuit helpers (school_fly.py), stopped at 300 ft instead of flown to touch.
#   new_ride_steep: the mock checkride during steep turns, via school_ride_check.py's rideSeed(42) and its wait()
#     for the first task.
#   new_cert_card (only with --cert; OFF by default): the certificate card open, driving the full rideSeed(42)
#     sequence (steep, slow, stall, emerg, hood, landings) to the end the way school_ride_check.py's DRIVE dict
#     does. This chains six realistic task flights (including a full three-circuit landings lesson) plus the
#     grading and certificate animation. It is the one row the task brief said to skip if it is too long for a
#     single row in the 9-minute budget: left out of the default round, available on request.
# FLOOR: no row may be slower than 0.90 of its base comparison.
import asyncio, functools, http.server, json, math, os, socketserver, sys, threading
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HERE, '..', 'node_modules/three/build/three.min.js')).read()
K = 'window.__kgeu'
FLOOR = 0.90
FT2M = 3.28084
KT2MS = 1.943844

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'

async def frame_ms(pg, n=16):
    return await pg.evaluate("""(n)=>{const K=window.__kgeu,c=document.getElementById('gl');
      const gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
      K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
      const t0=performance.now();for(let i=0;i<n;i++)K.stepFrame(1/60);
      gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);const ms=(performance.now()-t0)/n;
      K.stepFrame(0,true);return ms;}""", n)

# ---- flight stepping (school_fly.py's FLY, plus divert's 'hold' altitude feature): sim only, no render, one
# batched JS loop per call so stepping hundreds of frames costs real milliseconds, not real seconds ----
FLY = """([n,o])=>{const K=window.__kgeu,u=o.until?new Function('K','s','return '+o.until):null;let i=0;
  for(;i<n&&K.LES.on;i++){const s=K.state();s.windKt=0;s.gustAmp=0;
    if(o.hold!=null)s.pos.y+=(o.hold-K.G.alt)/3.28084;
    if(o.alt!=null){s.pos.y+=(o.alt-K.G.alt)/3.28084;o.alt=null;}
    if(o.x!=null){s.pos.x=o.x;s.pos.z=o.z;o.x=null;}
    if(o.agl!=null){s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+o.agl/3.28084+(o.gear||1.3);o.agl=null;}
    if(o.thr!=null){s.throttle=s.power=o.thr;}
    const hd=o.hdg+(o.rate||0)*i*0.1,h=hd*Math.PI/180,V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225),vy=(o.vs||0)/196.85;
    s.vel.set(Math.sin(h)*V,vy,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(Math.atan2(vy,V)+0.04,-h,-(o.bank||0)*Math.PI/180,'YXZ'));s.w.set(0,0,0);
    s.onGround=false;K.stepFrame(0.1,false,true);if(u&&u(K,K.state()))break;}
  K.stepFrame(0,true);return {i:i,ph:K.LES.ph,on:K.LES.on}}"""
# the ride-driving variant (school_ride_check.py's FLY): pinned to the task it starts in, so the ride can move on
# to the next task underneath it without this loop running past it
FLY_PIN = FLY.replace("let i=0;\n  for(;i<n&&K.LES.on;i++)", "let i=0;const tk=K.LES.on;\n  for(;i<n&&K.LES.on===tk;i++)")
UV = "(u,v)=>{const K=window.__kgeu,R=K.rwyFrame().rh*Math.PI/180;return [Math.sin(R)*u+Math.cos(R)*v,-Math.cos(R)*u+Math.sin(R)*v]}"
STALL = """(o)=>{const K=window.__kgeu,u=o.u?new Function('K','return '+o.u):null;let i=0;const tk=K.LES.on;
  for(;i<(o.n||400)&&K.LES.on===tk;i++){const s=K.state();s.windKt=0;s.gustAmp=0;s.throttle=s.power=o.thr;
    const V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225);s.vel.set(0,o.vy||0,-V);s.quat.setFromEuler(new THREE.Euler(o.p,0,0,'YXZ'));s.w.set(0,0,0);
    K.stepFrame(0.1,false,true);if(u&&u(K))break;}K.stepFrame(0,true);return {ph:K.LES.ph,on:K.LES.on,i:i}}"""
GROUND = """([x,z,n])=>{const K=window.__kgeu,tk=K.LES.on;for(let i=0;i<n&&K.LES.on===tk;i++){const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return K.LES.on}"""
FIELD = """()=>{const K=window.__kgeu,O=K.lesObjs(),M=O.filter(o=>o.name==='fieldMk'),s=K.state();if(!M.length)return null;
  const cx=M.reduce((p,o)=>p+o.x,0)/M.length,cz=M.reduce((p,o)=>p+o.z,0)/M.length;
  return {cx:cx,cz:cz,brg:(Math.atan2(cx-s.pos.x,-(cz-s.pos.z))*180/Math.PI+360)%360,M:M.map(o=>[o.x,o.z])}}"""
WAIT = "(id)=>{const K=window.__kgeu;let i=0;for(;i<900&&K.LES.on&&K.LES.on!==id;i++){const s=K.state();s.windKt=0;s.gustAmp=0;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return K.LES.on}"

async def fly(pg, n, **o): return await pg.evaluate(FLY, [n, o])
async def flypin(pg, n, **o): return await pg.evaluate(FLY_PIN, [n, o])
async def rwy(pg): return await pg.evaluate(f"()=>{K}.rwyFrame()")
async def xzuv(pg, u, v): return await pg.evaluate(f"([u,v])=>({UV})(u,v)", [u, v])

async def climbout(pg, F):
    x, z = await xzuv(pg, F['thr'] + 1300, 0)
    return await fly(pg, 40, x=x, z=z, agl=760, kt=74, vs=600, hdg=F['rh'], until="K.LES.d.s===1")
async def downwind(pg, F, n=60):
    x, z = await xzuv(pg, F['thr'] + 1500, 900)
    return await fly(pg, n, x=x, z=z, agl=2100 - F['field'], kt=95, vs=0, hdg=F['rh'] + 180)
async def base_leg(pg, F):
    x, z = await xzuv(pg, F['thr'] + 100, 900)
    return await fly(pg, 20, x=x, z=z, agl=1000, kt=80, vs=-400, hdg=F['rh'] - 90, until="K.LES.d.s===3")
async def final_leg(pg, F, kt=65, to=60):
    x, z = await xzuv(pg, F['thr'] - 1300, 0)
    await fly(pg, 60, x=x, z=z, agl=390, kt=kt, vs=-500, hdg=F['rh'])
    return await fly(pg, 30, agl=to, kt=kt, vs=-300, hdg=F['rh'])
async def touchdown_(pg, F, past=60, fpm=150, v=1.0):
    x, z = await xzuv(pg, F['thr'] + F['aim'] + past, v)
    await pg.evaluate(f"([x,z,f])=>{{const K={K};K.events.push({{type:'touchdown',fpm:f,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [x, z, fpm])
    return await flypin(pg, 2, agl=30, kt=60, vs=-100, hdg=F['rh'])
async def stop_(pg, F, u=700, n=30):
    x, z = await xzuv(pg, F['thr'] + u, 0)
    return await pg.evaluate(f"""([x,z,n])=>{{const K={K};for(let i=0;i<n&&K.LES.on;i++){{const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;s.throttle=0;K.stepFrame(0.1,false,true);}}
      K.stepFrame(0,true);return {{on:K.LES.on,ph:K.LES.ph}}}}""", [x, z, n])
async def call_(pg, n=400):
    r = await pg.evaluate(f"(n)=>{{const K={K};for(let i=0;i<n&&K.LES.on;i++){{if(K.TASK.ask&&K.TASK.ask.shown)break;K.stepFrame(0.1,false,true);}}K.stepFrame(0,true);return !!(K.TASK.ask&&K.TASK.ask.shown)}}", n)
    if r: r = await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    return r

def vs_(kt, deg): return kt * 101.27 * math.tan(math.radians(deg) - 0.04)

async def cockpit(pg):
    await pg.evaluate(f"()=>{{const K={K};let k=0;while(K.camMode()!==1&&k++<6)K.cycleCam();}}")

async def lesson_start(pg, lid, ride=False):
    extra = f"{K}.rideSeed(42);" if ride else ""
    await pg.evaluate(f"()=>{{const K={K};{extra}K.radioLog(true);K.startLesson('{lid}');K.lesBriefSkip();const s=K.state();s.windKt=0;s.gustAmp=0;}}")
    await pg.wait_for_timeout(200)

# ---- setup functions: leave the page in the state to measure; no settling or timing here ----
async def setup_runway(pg):
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}")
async def setup_final3(pg):
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}")
async def setup_f16(pg):
    await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('runway')}}")
async def setup_cockpit(pg):
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}")
    await cockpit(pg)

async def setup_pilotage_cruise(pg):
    await lesson_start(pg, 'pilotage')
    # teleport onto the Tolleson leg (NAV.legs[1]) at 3,500 ft instead of flying the climb-out and the first leg:
    # same leg geometry school_xc_check.py reads (from/to x,z and course), just placed rather than flown to.
    await pg.evaluate("""()=>{const K=window.__kgeu,N=K.NAV,l=N.legs[1],s=K.state();
      const mx=(l.from.x+l.to.x)/2, mz=(l.from.z+l.to.z)/2, h=l.course*Math.PI/180, V=105/1.943844;
      s.pos.set(mx,3500/3.28084,mz); s.vel.set(Math.sin(h)*V,0,-Math.cos(h)*V);
      s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ')); s.w.set(0,0,0); s.onGround=false;
      N.leg=1; N.show=true; K.stepFrame(0,true);}""")

async def setup_divert_card(pg):
    await lesson_start(pg, 'divert')
    c = await pg.evaluate(f"()=>{K}.NAV.legs[2].course")
    await fly(pg, 3, hold=3500, kt=105, vs=0, hdg=c)
    await fly(pg, 3000, hold=3500, kt=105, vs=0, hdg=c, until="K.DIV.on")
    g = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),x=K.LES.d.G0.x,z=K.LES.d.G0.z,dx=x-s.pos.x,dz=z-s.pos.z;
      return ((Math.atan2(dx,-dz)*180/Math.PI-12)%360+360)%360}}""")
    await fly(pg, 3, hold=3500, kt=105, vs=0, hdg=g + 12)
    await fly(pg, 80, hold=3500, kt=105, vs=0, hdg=g + 12)

async def setup_night_final300(pg):
    await lesson_start(pg, 'night')
    F = await rwy(pg)
    await climbout(pg, F); await downwind(pg, F); await downwind(pg, F, 80); await base_leg(pg, F)
    await final_leg(pg, F, to=300)

async def setup_ride_steep(pg):
    await lesson_start(pg, 'ride', ride=True)
    await pg.evaluate(WAIT, 'steep')

# ---- the six ride tasks (school_ride_check.py's DRIVE), only used for --cert ----
async def t_steep(pg):
    kt = await pg.evaluate(f"()=>Math.round({K}.state().ias*1.943844)")
    await flypin(pg, 10, kt=kt, vs=0, hdg=0, bank=45, until="K.LES.ph===1")
    await flypin(pg, 600, kt=kt, vs=0, hdg=0, bank=45, rate=10, until="K.LES.d.turned>=340")
    await flypin(pg, 20, kt=kt, vs=0, hdg=360, bank=0)
async def t_slow(pg):
    await flypin(pg, 400, kt=58, vs=0, hdg=0, thr=0.5, until="K.LES.ph===1")
    await flypin(pg, 600, kt=58, vs=0, hdg=0, thr=0.5)
async def t_stall(pg):
    for o in ({'kt': 48, 'p': 0.5, 'thr': 0, 'u': 'K.LES.ph===1'}, {'kt': 60, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===2'}, {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1, 'u': 'K.LES.ph===3'},
              {'kt': 58, 'p': 0.1, 'vy': 0, 'thr': 0.4, 'n': 20}, {'kt': 52, 'p': 0.55, 'thr': 1, 'u': 'K.LES.ph===4'}, {'kt': 62, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===5'},
              {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1}):
        await pg.evaluate(STALL, o)
async def t_emerg(pg):
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<60&&!K.LES.d.go;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}}")
    await flypin(pg, 700, thr=0, bank=45, kt=130, vs=-2500, hdg=0, rate=8, until="K.LES.ph===1")
    await flypin(pg, 80, alt=3500, thr=0.8, kt=100, vs=0, hdg=90, until="K.LES.ph===2")
    await flypin(pg, 140, kt=100, vs=0, hdg=90, until="K.LES.ph===3")
    f = await pg.evaluate(FIELD)
    await flypin(pg, 120, kt=68, vs=-650, hdg=f['brg'])
    ax, az = (f['M'][1][0] - f['M'][0][0]), (f['M'][1][1] - f['M'][0][1]); L = math.hypot(ax, az); ax, az = ax / L, az / L
    h = (math.degrees(math.atan2(ax, -az)) + 360) % 360
    await flypin(pg, 10, x=f['cx'] - ax * 600, z=f['cz'] - az * 600, agl=250, kt=62, vs=-500, hdg=h)
    await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:220,paved:K.isPaved(x,z),x:x,z:z,ias:30,bank:0}})}}", [f['cx'], f['cz']])
    await flypin(pg, 2, agl=20, kt=50, vs=-100, hdg=h)
    await pg.evaluate(GROUND, [f['cx'], f['cz'], 30])
async def t_hood(pg):
    await flypin(pg, 700, alt=3500, kt=90, vs=0, hdg=0, until="K.LES.ph===1")
    await flypin(pg, 200, kt=90, vs=0, hdg=0, rate=4.5, bank=15)
    await flypin(pg, 400, kt=90, vs=0, hdg=90, until="K.LES.ph===2")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on==='hood';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", 40)
    await flypin(pg, 6, thr=0, bank=50, kt=118, vs=vs_(118, -25), hdg=90)
    await flypin(pg, 6, bank=0, kt=125, vs=vs_(125, -25), hdg=90)
    await flypin(pg, 30, bank=0, kt=125, vs=300, hdg=90, until="K.LES.ph===3")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on==='hood';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", 40)
    await flypin(pg, 6, thr=1, bank=-40, kt=68, vs=vs_(68, 30), hdg=90)
    await flypin(pg, 10, bank=-40, kt=70, vs=0, hdg=90)
    await flypin(pg, 60, bank=0, kt=75, vs=0, hdg=90)
async def t_landings(pg):
    F = await rwy(pg)
    await call_(pg)
    await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}")
    for c in range(3):
        await climbout(pg, F); await downwind(pg, F)
        await call_(pg)
        await downwind(pg, F, 80); await base_leg(pg, F)
        if c == 1:
            await final_leg(pg, F, to=320)
            await flypin(pg, 3, agl=295, kt=65, vs=-400, hdg=F['rh'])
            await flypin(pg, 120, thr=1, kt=70, vs=900, hdg=F['rh'], until="K.LES.d.c===2")
            continue
        await final_leg(pg, F)
        await touchdown_(pg, F, past=60)
        if c == 0:
            await flypin(pg, 30, agl=30, kt=60, vs=0, hdg=F['rh'])
            await flypin(pg, 10, agl=150, kt=70, vs=500, hdg=F['rh'], until="K.LES.d.c===1")
        else:
            await stop_(pg, F)
DRIVE = {'steep': t_steep, 'slow': t_slow, 'stall': t_stall, 'emerg': t_emerg, 'hood': t_hood, 'landings': t_landings}

async def setup_cert_card(pg):
    await lesson_start(pg, 'ride', ride=True)
    seq = ['steep', 'slow', 'stall', 'emerg', 'hood', 'landings']
    await DRIVE['steep'](pg)
    for tid in seq[1:]:
        await pg.evaluate(WAIT, tid)
        await DRIVE[tid](pg)
    await pg.wait_for_timeout(500)

# name -> (setup fn, True if branch-only)
ROWS = {
    'shared_c172_runway':   (setup_runway, False),
    'shared_c172_final3':   (setup_final3, False),
    'shared_f16_free':      (setup_f16, False),
    'shared_c172_cockpit':  (setup_cockpit, False),
    'new_pilotage_cruise':  (setup_pilotage_cruise, True),
    'new_divert_card':      (setup_divert_card, True),
    'new_night_final300':   (setup_night_final300, True),
    'new_ride_steep':       (setup_ride_steep, True),
    'new_cert_card':        (setup_cert_card, True),
}
SHARED = ['shared_c172_runway', 'shared_c172_final3', 'shared_f16_free', 'shared_c172_cockpit']
NEWROWS = ['new_pilotage_cruise', 'new_divert_card', 'new_night_final300', 'new_ride_steep']
BASELINE_FOR_NEW = 'shared_c172_final3'

async def run(b, url, row_names, tag):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script("""localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');localStorage.setItem('kgeuSchoolEasy','0');localStorage.setItem('kgeuTOD','day');
      localStorage.setItem('kgeuPlace', JSON.stringify({level:'ride',hours:null}));""")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    out = {}
    async def settle(sec=1): await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", int(sec * 10)); await pg.wait_for_timeout(400)
    for name in row_names:
        print(f'  [{tag}] {name} ...', flush=True)
        fn = ROWS[name][0]
        await fn(pg)
        await settle(1)
        out[name] = await frame_ms(pg)
        print(f'  [{tag}] {name}: {out[name]:.2f} ms', flush=True)
    await ctx.close()
    return out, errs

async def main():
    args = sys.argv[1:]
    quick = '--quick' in args
    if quick: args.remove('--quick')
    cert = '--cert' in args
    if cert: args.remove('--cert')
    row = None
    if '--row' in args:
        i = args.index('--row'); row = args[i + 1]; del args[i:i + 2]
    base, new = args[0], args[1]
    rounds = int(args[2]) if len(args) > 2 else 1

    if row:
        row_names = [row]; rounds = 1
        base_names = [row] if not ROWS[row][1] else [BASELINE_FOR_NEW]
    elif quick:
        row_names = list(SHARED); base_names = list(SHARED)
    else:
        row_names = list(SHARED) + list(NEWROWS) + (['new_cert_card'] if cert else [])
        base_names = list(SHARED)

    ub, un = serve(base), serve(new)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        res = {'base': [], 'new': []}
        for r in range(rounds):
            print(f'-- round {r + 1}/{rounds} --', flush=True)
            order = [('base', ub, base_names), ('new', un, row_names)] if r % 2 == 0 else [('new', un, row_names), ('base', ub, base_names)]
            for tag, url, names in order:
                o, e = await run(b, url, names, tag)
                res[tag].append(o)
                if e: print(tag, 'errors', e[:3])
        await b.close()
    srv_names = ['base', 'new']
    avg = lambda tag, k: sum(o[k] for o in res[tag] if k in o) / len(res[tag])
    bad = []
    print(f"\n{'row':24} {'base ms':>9} {'new ms':>9} {'ratio':>7}")
    all_keys = list(dict.fromkeys([k for o in res['new'] for k in o]))
    base_final3 = avg('base', BASELINE_FOR_NEW) if any(k in base_names for k in [BASELINE_FOR_NEW]) else None
    for k in all_keys:
        is_shared = not ROWS[k][1]
        n = avg('new', k)
        if is_shared:
            a = avg('base', k); label = k
        else:
            a = base_final3; label = k + ' (vs final3)'
        ratio = a / n
        print(f"{label:34} {a:9.2f} {n:9.2f} {ratio:7.3f}" + ('  SLOWER' if ratio < FLOOR else ''))
        if ratio < FLOOR: bad.append(k)
    print(json.dumps(res))
    if not quick and not row and not cert:
        print('\nnote: new_cert_card (certificate card open) skipped by default: driving all six ride tasks plus '
              'grading in one row risks the 9-minute budget. Run with --cert (optionally --row new_cert_card) to add it.')
    print('\nschool2_fps: ' + ('FAILED ' + ', '.join(bad) if bad else f'all within {FLOOR:.2f}'))
    return 1 if bad else 0

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
