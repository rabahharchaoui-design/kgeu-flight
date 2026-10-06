# Phone3 item 8: offline mode. A copy of the game is served from a temp folder (so a new version can be
# shipped mid test). First visit online (with ?sw=1, the harness origin is not one of the real ones): the
# service worker installs, takes the page, precaches the page, three.js, the radio clips, the region data
# and the icons; a music track played is cached. Then airplane mode (context offline) and a reload: the
# game opens, the Offline chip shows on the menu, a flight starts and flies, radio clips and the played
# track load, an unplayed track fails quietly, no page errors. Back online the chip goes. Then a new
# version is shipped (APP_VER and version.json bumped): one online reload brings the new page, the new
# worker takes over and the old version's cache is gone (the music cache stays).
# Run: .venv/bin/python tests/offline_check.py
import asyncio, os, sys, shutil, tempfile, threading, functools, http.server, socketserver, re, json
from playwright.async_api import async_playwright
from harness import launch, Checks, IPHONE_15, ROOT
ok = Checks()
K = 'window.__kgeu'

def serve_dir(d):
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def end_headers(self):
            self.send_header('Cache-Control', 'max-age=600'); super().end_headers()   # like GitHub Pages
    h = functools.partial(Q, directory=d)
    class S(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = S(('127.0.0.1', 0), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/index.html?sw=1'

CACHES = """async()=>{const out={};for(const k of await caches.keys()){const c=await caches.open(k);out[k]=(await c.keys()).map(r=>r.url);}return out;}"""

async def main():
    tmp = tempfile.mkdtemp(prefix='pfs-off-')
    for f in ('index.html', 'sw.js', 'version.json', 'manifest.json'): shutil.copy(os.path.join(ROOT, f), tmp)
    for d in ('icons', 'radio', 'assets'): os.symlink(os.path.join(ROOT, d), os.path.join(tmp, d))
    srv, url = serve_dir(tmp)
    ver0 = json.load(open(os.path.join(tmp, 'version.json')))['v']
    async with async_playwright() as p:
        b = await launch(p)
        ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2, service_workers='allow')
        await ctx.add_init_script("(()=>{if(localStorage.getItem('kgeuOnboard'))return;localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');})()")
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(url); await pg.wait_for_function(f"()=>window.__kgeu&&{K}.WORLD&&{K}.WORLD.ready", timeout=60000)
        await pg.wait_for_function("()=>navigator.serviceWorker&&navigator.serviceWorker.controller", timeout=60000)
        await pg.wait_for_function("async()=>{const k=await caches.keys();if(!k.some(x=>x.startsWith('pfs-2')))return false;const c=await caches.open(k.find(x=>x.startsWith('pfs-2')));return (await c.keys()).length>=260}", timeout=120000, polling=1000)
        c = await pg.evaluate(CACHES)
        core = [k for k in c if k.startswith('pfs-2')]
        ok('online: the worker controls the page, one cache for this version', len(core) == 1 and core[0] == 'pfs-' + ver0, list(c))
        urls = c[core[0]]
        ok('precached: the page, the radio clips, region data, icons', any(u.endswith('/index.html') for u in urls) and sum('/radio/' in u for u in urls) >= 240
           and any('assets/world/rjtt.json' in u for u in urls) and any('assets/map/phx.bin' in u for u in urls) and any('/icons/' in u for u in urls), len(urls))
        ok('three.js cached from the CDN', any('three.min.js' in u for u in c.get('pfs-ext', [])), c.get('pfs-ext'))
        # a track played (the game fetches tracks whole)
        n = await pg.evaluate("()=>fetch('assets/music/cruise.m4a').then(r=>r.arrayBuffer()).then(a=>a.byteLength)")
        await pg.wait_for_timeout(500)
        c = await pg.evaluate(CACHES)
        ok('a played track is cached', n > 10000 and any('cruise.m4a' in u for u in c.get('pfs-music', [])), c.get('pfs-music'))
        ok('online: no Offline chip', await pg.evaluate("()=>document.getElementById('hOff').hidden"))
        # ---- airplane mode
        await ctx.set_offline(True)
        await pg.reload(); await pg.wait_for_function(f"()=>window.__kgeu&&{K}.WORLD&&{K}.WORLD.ready", timeout=60000)
        await pg.wait_for_timeout(800)
        chip = await pg.evaluate("()=>{const e=document.getElementById('hOff'),r=e.getBoundingClientRect();return {hidden:e.hidden,w:r.width,txt:e.textContent.trim(),menu:document.getElementById('menu').classList.contains('on')}}")
        ok('offline: the game opens on the menu with the Offline chip', not chip['hidden'] and chip['w'] > 40 and chip['txt'] == 'Offline' and chip['menu'], chip)
        ok('offline: three.js came from the cache', await pg.evaluate("()=>typeof THREE!=='undefined'"))
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final');}}"); await pg.wait_for_timeout(500)
        for _ in range(20): await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)")
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        s = await pg.evaluate(f"()=>({{run:{K}.running(),t:{K}.state().time,crashed:{K}.state().crashed}})")
        ok('offline: a flight starts and flies', s['run'] and s['t'] > 1.5, s)
        r = await pg.evaluate("()=>fetch('radio/'+'t_crash.m4a').then(r=>r.status).catch(()=>0)")
        ok('offline: a radio clip loads', r == 200, r)
        r = await pg.evaluate("()=>fetch('assets/music/cruise.m4a').then(r=>r.status).catch(()=>0)")
        ok('offline: the played track loads', r == 200, r)
        r = await pg.evaluate("()=>fetch('assets/music/metallica-one.m4a').then(r=>r.status).catch(()=>'failed')")
        ok('offline: a track never played fails quietly (no page error)', r == 'failed', r)
        await ctx.set_offline(False); await pg.evaluate("()=>window.dispatchEvent(new Event('online'))"); await pg.wait_for_timeout(300)
        ok('back online: the chip goes', await pg.evaluate("()=>document.getElementById('hOff').hidden"))
        ok('no page errors', not errs, errs[:3])
        # ---- ship a new version
        ver1 = ver0 + '-next'
        s0 = open(os.path.join(tmp, 'index.html')).read()
        open(os.path.join(tmp, 'index.html'), 'w').write(s0.replace(f"const APP_VER='{ver0}'", f"const APP_VER='{ver1}'"))
        json.dump({'v': ver1}, open(os.path.join(tmp, 'version.json'), 'w'))
        await pg.reload(); await pg.wait_for_function(f"()=>window.__kgeu&&{K}.APP_VER", timeout=60000)
        ok('one online reload brings the new page', await pg.evaluate(f"()=>{K}.APP_VER") == ver1, await pg.evaluate(f"()=>{K}.APP_VER"))
        await pg.wait_for_function(f"()=>navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL.includes('{ver1}')", timeout=60000)
        await pg.wait_for_function(f"async()=>!(await caches.keys()).includes('pfs-{ver0}')", timeout=60000)
        c = await pg.evaluate(CACHES)
        ok('the new worker took over, the old cache is gone, the music cache stays', 'pfs-' + ver1 in c and 'pfs-' + ver0 not in c and 'pfs-music' in c, list(c))
        await ctx.set_offline(True)
        await pg.reload(); await pg.wait_for_function(f"()=>window.__kgeu&&{K}.APP_VER", timeout=60000)
        ok('offline again: the new version opens', await pg.evaluate(f"()=>{K}.APP_VER") == ver1)
        await b.close()
    srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(ok.done('offline_check'))

asyncio.run(main())
