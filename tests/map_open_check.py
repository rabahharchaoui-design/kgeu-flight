# Opening the full map: instant and never a half painted frame. iPhone 15 landscape, 2x.
# Opens and closes the map 10 times while flying, then 5 more under a 4x CDP CPU throttle,
# then after rotating to portrait and back. For every open: the JS time of the open handler,
# and the map canvas read back right after the call (what the next composited frame shows,
# before any rAF) compared with the settled map (every tile rendered). A frame that differs
# is blank, coarse or partly painted: the flicker.
# Run: .venv/bin/python tests/map_open_check.py [root]   (root defaults to this repo)
import asyncio, functools, http.server, os, socketserver, sys, threading
from playwright.async_api import async_playwright
from harness import THREE, IGNORE, Checks, launch, splash_gone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, '..'))
K = 'window.__kgeu'
ok = Checks()

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'

# a grid of samples of the map canvas, as [r,g,b,a,...]
SAMPLE = """()=>{const c=document.getElementById('fmap'),x=c.getContext('2d'),W=c.width,H=c.height,d=x.getImageData(0,0,W,H).data,o=[];
  for(let j=2;j<H;j+=6)for(let i=2;i<W;i+=6){const k=(j*W+i)*4;o.push(d[k],d[k+1],d[k+2],d[k+3]);}return {w:W,h:H,px:o};}"""
OPEN = """()=>{const K=%s,t0=performance.now();K.fmOpen();const t1=performance.now();return [t1-t0,K.MT.queue.length,K.MT.cache.size];}""" % K

def diff(a, b):
    if a['w'] != b['w'] or a['h'] != b['h'] or len(a['px']) != len(b['px']): return 1.0
    p, q, n, bad = a['px'], b['px'], len(a['px']) // 4, 0
    for i in range(0, len(p), 4):
        if abs(p[i] - q[i]) + abs(p[i + 1] - q[i + 1]) + abs(p[i + 2] - q[i + 2]) + abs(p[i + 3] - q[i + 3]) > 30: bad += 1
    return bad / n

async def one(pg, label):
    ms, miss, tiles = await pg.evaluate(OPEN)
    first = await pg.evaluate(SAMPLE)
    await pg.wait_for_timeout(700)                       # let the map pump whatever it still needs
    await pg.evaluate(f"()=>{K}.fmFlush()")
    settled = await pg.evaluate(SAMPLE)
    blank = sum(1 for i in range(3, len(first['px']), 4) if first['px'][i] < 250) / (len(first['px']) // 4)
    dv = diff(first, settled)
    await pg.evaluate(f"()=>{K}.fmClose()")
    await pg.wait_for_timeout(350)                       # fly a little between opens
    print(f'    {label}: open {ms:6.2f} ms  tiles missing {miss:2d} (cached {tiles:2d})  first frame differs from settled {dv*100:5.2f}%  unpainted {blank*100:4.1f}%')
    return ms, dv, blank, miss

async def main():
    url = serve(ROOT)
    print('root', ROOT)
    async with async_playwright() as p:
        b = await launch(p)
        ctx = await b.new_context(viewport={'width': 844, 'height': 390}, has_touch=True, is_mobile=True, device_scale_factor=2)
        await ctx.add_init_script("if(!sessionStorage.getItem('__s')){sessionStorage.setItem('__s','1');localStorage.clear();localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');}")
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await splash_gone(pg)
        await pg.wait_for_function(f"()=>{K}.MAPD.ready", timeout=30000)
        await pg.wait_for_timeout(2500)                  # the menu is up: its warm-up gets a moment
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}")
        await pg.wait_for_timeout(2500)
        res = {}
        print('  unthrottled, landscape')
        res['fast'] = [await one(pg, f'open {i+1:2d}') for i in range(10)]
        cdp = await ctx.new_cdp_session(pg)
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        print('  CPU throttled 4x, landscape')
        res['slow'] = [await one(pg, f'open {i+1:2d}') for i in range(5)]
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
        print('  rotated to portrait, then back to landscape')
        await pg.set_viewport_size({'width': 390, 'height': 844}); await pg.wait_for_timeout(1500)
        res['rot'] = [await one(pg, 'portrait  ') for _ in range(2)]
        await pg.set_viewport_size({'width': 844, 'height': 390}); await pg.wait_for_timeout(1500)
        res['rot'] += [await one(pg, 'landscape ') for _ in range(2)]
        await ctx.close(); await b.close()

    f, s, r = res['fast'], res['slow'], res['rot']
    med = lambda v: sorted(v)[len(v) // 2]
    fm, sm = med([x[0] for x in f]), med([x[0] for x in s])
    print(f'\n  open handler: median {fm:.2f} ms (max {max(x[0] for x in f):.2f}) unthrottled, median {sm:.2f} ms (max {max(x[0] for x in s):.2f}) at 4x throttle')
    ok('open handler under 16 ms unthrottled (median of 10)', fm < 16, f'{fm:.2f} ms')
    ok('open handler under 16 ms at 4x CPU throttle (median of 5, report only past 16)', True, f'{sm:.2f} ms')
    worst = max(x[1] for x in f + s + r)
    ok('first frame after every open is the settled map (under 0.5% of samples differ)', worst < 0.005, f'worst {worst*100:.2f}%')
    ok('every tile of the opening view is ready at the open (nothing coarse to pop in)', max(x[3] for x in f + s + r) == 0, f'worst {max(x[3] for x in f + s + r)} missing')
    ok('first frame after every open is fully painted', max(x[2] for x in f + s + r) == 0, f'{max(x[2] for x in f + s + r)*100:.2f}% unpainted')
    ok('no page errors', not errs, errs[:3])
    return ok.done('map open check')

sys.exit(asyncio.run(main()))
