# Frame rate for the aircraft session: the same scenarios on two builds, back to back and
# alternating, so machine drift cancels. Headless software rendering runs at a few fps;
# only the ratio between the builds means anything. iPhone landscape, 2x.
#   .venv/bin/python tests/aircraft_fps.py <base_root> <new_root> [rounds]
# Scenarios: each rebuilt aircraft in the chase view on the runway and on final, the
# Cessna cockpit, the MQ-9A at night, and the menu carousel (it draws the models).
# *_ms rows are wall time per held tick (sim + render, synced by a readback): finer
# grained than the rAF count, which software GL quantises to a few steps.
import asyncio, functools, http.server, json, os, socketserver, sys, threading
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HERE, '..', 'node_modules/three/build/three.min.js')).read()
K = 'window.__kgeu'
FLOOR = 0.90          # a scenario may lose at most 10% against the base build

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'

async def fps(pg, seconds=6.0, warm=2.0):
    await pg.wait_for_timeout(int(warm * 1000))
    await pg.evaluate("""()=>{window.__stop=1;window.__f=0;setTimeout(()=>{window.__stop=0;
      const t=()=>{if(window.__stop)return;window.__f++;requestAnimationFrame(t);};requestAnimationFrame(t);},60);}""")
    await pg.wait_for_timeout(int(seconds * 1000) + 60)
    return await pg.evaluate("()=>{window.__stop=1;return window.__f;}") / seconds

async def frame_ms(pg, n=24):
    # hold the loop and time n full ticks (sim + render), synced with a 1 px readback
    return await pg.evaluate("""(n)=>{const K=window.__kgeu,c=document.getElementById('gl');
      const gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
      K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
      const t0=performance.now();for(let i=0;i<n;i++)K.stepFrame(1/60);
      gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);const ms=(performance.now()-t0)/n;
      K.stepFrame(0,true);return ms;}""", n)

async def run(b, url):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    out = {}
    for t in ['cessna', 'alpha', 'reaper', 'mq9b']:
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('runway')}}"); await pg.wait_for_timeout(2500)
        out[f'{t}_runway'] = await fps(pg)
        out[f'{t}_runway_ms'] = await frame_ms(pg)
        await pg.evaluate(f"()=>{{{K}.start('final')}}"); await pg.wait_for_timeout(2500)
        out[f'{t}_final'] = await fps(pg)
        out[f'{t}_final_ms'] = await frame_ms(pg)
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.start('runway');let k=0;while({K}.camMode()!==1&&k++<5){K}.cycleCam();}}"); await pg.wait_for_timeout(2500)
    out['cessna_cockpit'] = await fps(pg)
    out['cessna_cockpit_ms'] = await frame_ms(pg)
    await pg.evaluate(f"()=>{{let k=0;while({K}.camMode()!==0&&k++<5){K}.cycleCam();{K}.setTOD('night');{K}.pick('reaper');{K}.start('final')}}"); await pg.wait_for_timeout(2500)
    out['reaper_night'] = await fps(pg)
    out['reaper_night_ms'] = await frame_ms(pg)
    await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.openMenu&&{K}.openMenu();const h=document.getElementById('hFly');if(h)h.click();}}"); await pg.wait_for_timeout(2500)
    out['carousel'] = await fps(pg)
    await ctx.close()
    return out, errs

async def main():
    base, new = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    ub, un = serve(os.path.abspath(base)), serve(os.path.abspath(new))
    acc = {'base': [], 'new': []}; errs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        for r in range(rounds):
            for label, url in (('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub)):
                o, e = await run(b, url); acc[label].append(o); errs += [f'{label}: {x}' for x in e]
                print(label, json.dumps({k: round(v, 2) for k, v in o.items()}))
        await b.close()
    mean = lambda L, k: sum(x[k] for x in L) / len(L)
    fails = []
    for k in acc['base'][0]:
        bb, nn = mean(acc['base'], k), mean(acc['new'], k)
        r = (bb / nn if nn else 1) if k.endswith('_ms') else (nn / bb if bb else 1)   # >1 is faster either way
        ok = r >= FLOOR
        print(f"  {'ok  ' if ok else 'FAIL'} {k}: base {bb:.2f} new {nn:.2f} ratio {r:.2f}")
        if not ok: fails.append(k)
    if errs:
        from collections import Counter
        print('page errors:', dict(Counter(errs)))
    print('aircraft_fps: ' + ('all passed' if not fails and not [e for e in errs if e.startswith('new')] else 'FAILED ' + ', '.join(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
