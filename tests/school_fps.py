# School1: frame rate against the build before Flight School, back to back and alternating so machine drift
# cancels (headless software GL runs at a few fps: only the ratio between builds means anything). ms per held tick
# (sim + render, synced by a readback), as tests/tasking_fps.py and tests/aircraft_fps.py.
#   .venv/bin/python tests/school_fps.py <base_root> <new_root> [rounds] [--only shared]
# Shared rows run the same thing on both builds (the school hooks must cost nothing with no lesson on): the Cessna
# 172 free flight from the Glendale runway, the 172 on a 3 mile final, the 172 cockpit view, the F-16 free flight.
# School rows put the new build at its busiest moment against the closest thing the base build (the preschool1 tag,
# which predates the lesson engine, the briefing, the grading engine and five of the nine lessons) has:
#   slow flight with the cue strip visible: new starts through startLesson('slow',true,{brief:false}) then steps
#     until LES.ph===1; base has an old startLesson('slow') of its own that flies at once, same phase to wait for.
#   ground reference with the pylons, the box and the ring in view: new starts the lesson (it does not exist on the
#     base) and is placed over the site at 800 ft AGL; base is the 172 in free flight placed over the same spot.
#   the landings lesson on short final with the aiming bars (new; the lesson does not exist on the base) against the
#     172 on the built-in 1 mile final (base).
#   under the hood, the hood and the six pack (new; the lesson does not exist on the base) against the 172 cockpit
#     view (base, the closest the old build has to an instrument view).
# FLOOR: no row may be slower than 0.90 of its base.
import asyncio, functools, http.server, json, os, socketserver, sys, threading
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HERE, '..', 'node_modules/three/build/three.min.js')).read()
K = 'window.__kgeu'
FLOOR = 0.90

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'

async def frame_ms(pg, n=24):
    return await pg.evaluate("""(n)=>{const K=window.__kgeu,c=document.getElementById('gl');
      const gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
      K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
      const t0=performance.now();for(let i=0;i<n;i++)K.stepFrame(1/60);
      gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);const ms=(performance.now()-t0)/n;
      K.stepFrame(0,true);return ms;}""", n)

STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true);window.__kgeu.stepFrame(0,true);}"
# direct placement, as tasking_fps.py's own PLACE: x,z world metres, y metres above the field (not AGL in general,
# but Glendale's local frame puts y=0 at field elevation, so AGL and this y agree near the field), heading h in
# radians, speed v in m/s, level flight
PLACE = """([x,z,y,h,v])=>{const K=window.__kgeu,s=K.state();s.pos.set(x,y,z);s.vel.set(Math.sin(h)*v,0,-Math.cos(h)*v);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;}"""
FT2M = 3.28084
KT2MS = 1.943844

async def run(b, url, new, ground_site, only_shared):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');localStorage.setItem('kgeuTOD','day');")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    out = {}
    async def settle(sec=3): await pg.evaluate(STEP, int(sec * 10)); await pg.wait_for_timeout(600)
    async def cockpit():   # camMode 1 is the cockpit view (school_hood_check.py: the hood forces it); cycleCam to it
        await pg.evaluate(f"()=>{{const K={K};let k=0;while(K.camMode()!==1&&k++<6)K.cycleCam();}}")
    # ---- shared: the same on both builds (the school hooks must cost nothing with no lesson on) ----
    for name, js in [('c172_runway', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')"),
                     ('c172_final3', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')"),
                     ('f16_free', f"{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('runway')")]:
        await pg.evaluate(f"()=>{{{js}}}"); await settle()
        out['shared_' + name] = await frame_ms(pg)
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}"); await settle()
    await cockpit(); await settle(1)
    out['shared_c172_cockpit'] = await frame_ms(pg)
    if only_shared:
        await ctx.close(); return out, errs

    # ---- school: the new build at its busiest moment against the closest thing the base build has ----
    if new: await pg.evaluate(f"()=>{{const K={K};K.startLesson('slow',true,{{brief:false}})}}")
    else: await pg.evaluate(f"()=>{{const K={K};K.startLesson('slow')}}")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.ph!==1;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);}", 400)
    await settle(1)
    out['school_slow_cue'] = await frame_ms(pg)

    gx, gz = ground_site
    if new: await pg.evaluate(f"()=>{{const K={K};K.startLesson('ground',true,{{brief:false}})}}")
    else: await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}")
    await pg.evaluate(PLACE, [gx, gz, 800 / FT2M, 0, 100 / KT2MS])
    await settle(1)
    out['school_ground_ref'] = await frame_ms(pg)

    if new:
        await pg.evaluate(f"()=>{{const K={K};K.startLesson('landings',true,{{brief:false}})}}")
        xz = await pg.evaluate(f"()=>{{const K={K},F=K.rwyFrame(),R=F.rh*Math.PI/180,u=F.thr-700,v=0;return [Math.sin(R)*u+Math.cos(R)*v,-Math.cos(R)*u+Math.sin(R)*v,R]}}")
        await pg.evaluate(PLACE, [xz[0], xz[1], 300 / FT2M, xz[2], 65 / KT2MS])
    else:
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('final1')}}")
    await settle(1)
    out['school_landings_final'] = await frame_ms(pg)

    if new:
        await pg.evaluate(f"()=>{{const K={K};K.startLesson('hood',true,{{brief:false}})}}")
        await settle(1)
    else:
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}")
        await settle(1); await cockpit(); await settle(1)
    out['school_hood_view'] = await frame_ms(pg)

    await ctx.close()
    return out, errs

async def main():
    args = sys.argv[1:]
    only_shared = False
    if '--only' in args:
        i = args.index('--only'); only_shared = args[i + 1] == 'shared'; del args[i:i + 2]
    base, new = args[0], args[1]
    rounds = int(args[2]) if len(args) > 2 else 1
    ub, un = serve(base), serve(new)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        ground_site = (0, 0)
        if not only_shared:
            # the ground reference site exists only on the new build (grSite); read its world coordinates once
            ctx = await b.new_context(viewport={'width': 844, 'height': 390})
            pg = await ctx.new_page()
            await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
            await pg.route('**/fonts.g*/**', lambda r: r.abort())
            await pg.goto(un); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(1500)
            g = await pg.evaluate(f"()=>{{const g={K}.grSite();return [g.cx,g.cz]}}")
            ground_site = (g[0], g[1])
            await ctx.close()
        res = {'base': [], 'new': []}
        for r in range(rounds):
            for tag, url in (('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub)):
                o, e = await run(b, url, tag == 'new', ground_site, only_shared)
                res[tag].append(o)
                if e: print(tag, 'errors', e[:3])
        await b.close()
    keys = res['base'][0].keys()
    avg = lambda tag, k: sum(o[k] for o in res[tag]) / len(res[tag])
    bad = []
    print(f"{'scenario':24} {'base ms':>9} {'new ms':>9} {'ratio':>7}")
    for k in keys:
        a, n = avg('base', k), avg('new', k); ratio = a / n
        print(f"{k:24} {a:9.2f} {n:9.2f} {ratio:7.3f}" + ('  SLOWER' if ratio < FLOOR else ''))
        if ratio < FLOOR: bad.append(k)
    print(json.dumps(res))
    print('\nschool_fps: ' + ('FAILED ' + ', '.join(bad) if bad else f'all within {FLOOR:.2f}'))
    return 1 if bad else 0

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
