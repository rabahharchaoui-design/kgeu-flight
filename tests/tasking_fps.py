# Tasking item 6: frame rate against the build before the Taskings, back to back and alternating so machine drift
# cancels (headless software GL runs at a few fps: only the ratio between builds means anything). ms per held tick
# (sim + render, synced by a readback), as tests/aircraft_fps.py.
#   .venv/bin/python tests/tasking_fps.py <base_root> <new_root> [rounds]
# Shared rows run the same thing on both builds (the Taskings' per-frame hooks must cost nothing when no tasking is on).
# Tasking rows put each tasking at its busiest moment on the new build and the closest existing mode on the base:
#   overwatch (ball view on the compound) vs the strike range's ball view; lifeline (the run in, smoke out) vs the
#   airdrop's run in; shepherd (escorting the C-130, the traffic out) vs the F-16 in free flight; finder (the search,
#   the flash) vs the 172 in free flight. FLOOR: no row may be slower than 0.90 of its base.
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
# put the flown aircraft at (x, z), y metres MSL above the field, heading h, at the speed of v m/s, in level flight
PLACE = """([x,z,y,h,v])=>{const K=window.__kgeu,s=K.state();s.pos.set(x,y,z);s.vel.set(Math.sin(h)*v,0,-Math.cos(h)*v);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;}"""

async def run(b, url, new):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');localStorage.setItem('kgeuTOD','day');")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    out = {}
    async def settle(sec=3): await pg.evaluate(STEP, int(sec * 10)); await pg.wait_for_timeout(600)
    # shared: the same on both builds
    for name, js in [('c172_runway', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')"),
                     ('mq9b_luke', f"{K}.pick('mq9b');{K}.start('runway','luke')"),
                     ('f16_final', f"{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('final')"),
                     ('airdrop', f"{K}.mission('drop')"),
                     ('strike_ball', f"{K}.mission('range')")]:
        await pg.evaluate(f"()=>{{{js}}}"); await settle()
        out['shared_' + name] = await frame_ms(pg)
    # each tasking at its busiest against its nearest existing mode
    if new:
        await pg.evaluate(f"()=>{{const K={K};K.TASK.test.noBrief=true;K.taskStart('overwatch',{{seed:42}})}}")
        await pg.evaluate(PLACE, await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;return [d.c.x+2400,d.c.z,(3000-1071)/3.28084,0,64]}}"))
        await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;K.auto();K.TASK.d.veh.moving=true;}}"); await settle(1)
        await pg.evaluate(f"()=>{{const K={K};let k=0;while(K.camMode()!==2&&k++<5)K.cycleCam();K.SENSOR.tgt=K.TASK.d.veh;}}"); await settle(2)
    else:
        await pg.evaluate(f"()=>{K}.mission('range')"); await settle(2)
    out['task_overwatch'] = await frame_ms(pg)
    if new:
        await pg.evaluate(f"()=>{{const K={K};K.taskStop();K.taskStart('lifeline',{{seed:5}})}}"); await settle(1)
        await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;K.DZ.noSmoke=false;const s=K.state();s.pos.x=d.c.x-d.f.x*3000;s.pos.z=d.c.z-d.f.z*3000;s.vel.set(d.f.x*72,0,d.f.z*72);s.quat.setFromEuler(new THREE.Euler(0,-Math.atan2(d.f.x,-d.f.z),0,'YXZ'));}}"); await settle(2)
    else:   # the airdrop at the same place on its own run in: 3 km out, into the wind, looking at the smoke
        await pg.evaluate(f"()=>{K}.mission('drop')"); await settle(1)
        await pg.evaluate(f"()=>{{const K={K},s=K.state();s.windBase=s.windDir=20;s.windKt=13;s.windPh=0;}}")   # Lifeline seed 5's wind: the smoke leans the same way
        await pg.evaluate(f"()=>{{const K={K},s=K.state(),h=s.windDir*Math.PI/180,f={{x:Math.sin(h),z:-Math.cos(h)}};s.pos.x=K.DROPZ.x-f.x*3000;s.pos.z=K.DROPZ.z-f.z*3000;s.vel.set(f.x*72,0,f.z*72);s.quat.setFromEuler(new THREE.Euler(0,-Math.atan2(f.x,-f.z),0,'YXZ'));}}"); await settle(2)
    out['task_lifeline'] = await frame_ms(pg)
    if new:
        await pg.evaluate(f"()=>{{const K={K};K.taskStop();K.taskStart('shepherd',{{seed:3}})}}"); await settle(1)
        await pg.evaluate(f"""()=>{{const K={K},d=K.TASK.d,L=d.L,s=K.state(),f={{x:Math.sin(L.h),z:-Math.cos(L.h)}},r={{x:Math.cos(L.h),z:Math.sin(L.h)}};
          s.pos.set(L.x+r.x*300-f.x*350,L.y+1.72,L.z+r.z*300-f.z*350);s.vel.set(f.x*118,0,f.z*118);s.quat.setFromEuler(new THREE.Euler(0,-L.h,0,'YXZ'));
          d.e0=s.time-200;d.c1=0;d.c2=0;d.cw=0;d.t1=0;d.t2=1;d.devAt=2;K.TASK.si=1;K.TASK.stage=K.TASKS.shepherd.stages[1];}}"""); await settle(3)
    else:
        await pg.evaluate(f"()=>{{const K={K};K.pick('f16');K.start('runway','luke')}}")
        await pg.evaluate(PLACE, [-12659, -1404, (8000 - 1071) / 3.28084, 3.3, 118]); await settle(3)
    out['task_shepherd'] = await frame_ms(pg)
    if new:
        await pg.evaluate(f"()=>{{const K={K};K.taskStop();K.taskStart('finder',{{seed:8}})}}"); await settle(1)
        await pg.evaluate(PLACE, await pg.evaluate(f"()=>{{const d={K}.TASK.d;return [d.h.x+1500,d.h.z,d.altY,-1.5708,54]}}")); await settle(2)
    else:
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}")
        await pg.evaluate(PLACE, [-17400, -6000, 1372, -1.5708, 54]); await settle(2)
    out['task_finder'] = await frame_ms(pg)
    await ctx.close()
    return out, errs

async def main():
    base, new = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ub, un = serve(base), serve(new)
    res = {'base': [], 'new': []}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        for r in range(rounds):
            for tag, url in (('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub)):
                o, e = await run(b, url, tag == 'new')
                res[tag].append(o)
                if e: print(tag, 'errors', e[:3])
        await b.close()
    keys = res['base'][0].keys()
    avg = lambda tag, k: sum(o[k] for o in res[tag]) / len(res[tag])
    bad = []
    print(f"{'scenario':22} {'base ms':>9} {'new ms':>9} {'ratio':>7}")
    for k in keys:
        a, n = avg('base', k), avg('new', k); ratio = a / n
        print(f"{k:22} {a:9.2f} {n:9.2f} {ratio:7.3f}" + ('  SLOWER' if ratio < FLOOR else ''))
        if ratio < FLOOR: bad.append(k)
    print(json.dumps(res))
    print('\ntasking_fps: ' + ('FAILED ' + ', '.join(bad) if bad else f'all within {FLOOR:.2f}'))
    return 1 if bad else 0

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
