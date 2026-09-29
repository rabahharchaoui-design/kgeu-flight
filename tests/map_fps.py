# Frame rate for the map session: the same scenarios on two builds, back to back, so
# machine drift cancels. Headless software rendering runs at a few fps; only the
# ratio between the two builds means anything. iPhone landscape, 2x.
#   .venv/bin/python tests/map_fps.py <base_root> <new_root> [rounds]
# Scenarios: flying with the mini map, inside a haboob (C-130), the C-130 crash,
# the full map open, and the full map while panning.
import asyncio, functools, http.server, json, os, socketserver, sys, threading
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HERE, '..', 'node_modules/three/build/three.min.js')).read()
K = 'window.__kgeu'

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'

async def fps(pg, seconds=6.0, warm=2.0, pan=False):
    await pg.wait_for_timeout(int(warm * 1000))
    await pg.evaluate("""(pan)=>{window.__stop=1;window.__f=0;setTimeout(()=>{window.__stop=0;let x=300,d=1;const c=document.getElementById('fmap');
      if(pan)c.dispatchEvent(new PointerEvent('pointerdown',{pointerId:9,clientX:x,clientY:200,bubbles:true}));
      const t=()=>{if(window.__stop){if(pan)c.dispatchEvent(new PointerEvent('pointerup',{pointerId:9,clientX:x,clientY:200,bubbles:true}));return;}
        window.__f++;if(pan){x+=d*12;if(x>600||x<200)d=-d;c.dispatchEvent(new PointerEvent('pointermove',{pointerId:9,clientX:x,clientY:200,bubbles:true}));}
        requestAnimationFrame(t);};requestAnimationFrame(t);},60);}""", pan)
    await pg.wait_for_timeout(int(seconds * 1000) + 60)
    return await pg.evaluate("()=>{window.__stop=1;return window.__f;}") / seconds

async def run(b, url):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    out = {}
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}"); await pg.wait_for_timeout(6000)
    out['cruise_minimap'] = await fps(pg)
    await pg.evaluate(f"()=>{K}.fmOpen()"); out['full_map_open'] = await fps(pg)
    out['full_map_pan'] = await fps(pg, pan=True)
    await pg.evaluate(f"()=>{K}.fmClose()")
    await pg.evaluate(f"()=>{{{K}.setTOD('haboob');{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('final')}}"); await pg.wait_for_timeout(4000)
    await pg.evaluate(f"()=>{K}.haboobJump(-2500)"); out['haboob_inside'] = await fps(pg)
    await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.pick('c130');{K}.start('final')}}"); await pg.wait_for_timeout(4000)
    await pg.evaluate(f"()=>{K}.crashNow('fps test')"); out['c130_crash'] = await fps(pg, seconds=6.0, warm=0.3)
    # the C-130 airdrop, with the drop zone in view: day, night, inside a haboob (Easy shows everything)
    await pg.evaluate("()=>localStorage.setItem('kgeuOnboard','rookie')")
    for tod in ('day', 'night', 'haboob'):
        await pg.evaluate(f"()=>{{{K}.setSkill&&{K}.setSkill('rookie');{K}.setTOD('{tod}');{K}.mission('drop')}}"); await pg.wait_for_timeout(3000)
        if tod == 'haboob': await pg.evaluate(f"()=>{K}.haboobJump(-1500)")
        out['drop_' + tod] = await fps(pg)
    out['errors'] = errs[:3]
    await ctx.close()
    return out

async def main():
    base, new = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    ub, un = serve(base), serve(new)
    res = {'base': [], 'new': []}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        for r in range(rounds):   # alternate the order so drift hits both builds alike
            for k, u in ((('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub))):
                o = await run(b, u); res[k].append(o); print(k, json.dumps(o))
        await b.close()
    fail = []
    print('\nscenario            base   new   ratio')
    for s in [k for k in res['base'][0] if k != 'errors']:
        a = sum(o[s] for o in res['base']) / rounds; n = sum(o[s] for o in res['new']) / rounds
        ok = n >= 0.8 * a
        print(f'{s:18} {a:6.2f} {n:6.2f}  {n/a:5.2f} {"ok" if ok else "FAIL"}')
        if not ok: fail.append(s)
    errs = [e for o in res['new'] for e in o['errors']]
    if errs: fail.append('page errors: ' + ' | '.join(errs[:2]))
    json.dump(res, open(os.path.join(HERE, 'map_fps.json'), 'w'), indent=1)
    print('FAILED ' + ', '.join(fail) if fail else 'map_fps: all passed')
    sys.exit(1 if fail else 0)
asyncio.run(main())
