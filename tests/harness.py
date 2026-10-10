# Shared Playwright setup for the UX checks: iPhone landscape, served over http so
# the radio clips load, three.js from node_modules, fonts blocked.
import os, threading, functools, http.server, socketserver

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
THREE = open(os.path.join(ROOT, 'node_modules/three/build/three.min.js')).read()
IPHONE_SE = {'width': 667, 'height': 375}
IPHONE_15 = {'width': 844, 'height': 390}
# school1: a saved flight school placement, so the intake does not cover #sSchool. Tests opt in: storage=dict(..., **PLACED)
PLACED = {'kgeuPlace': '{"level":"ride","hours":null}'}
# ERR_CONNECTION_RESET / ERR_SOCKET_NOT_CONNECTED: the local test server dropping a request
# still in flight when a page reloads or closes, not the game
IGNORE = ('ERR_FAILED', 'fonts.googleapis', 'ERR_ABORTED', 'ERR_NAME_NOT_RESOLVED', 'ERR_CONNECTION_RESET', 'ERR_SOCKET_NOT_CONNECTED')

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=ROOT)
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, request, client_address): pass   # a closed browser drops its sockets
    srv = Q(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/index.html'

async def launch(p):
    return await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl',
        '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])

async def page(b, url, vp=IPHONE_SE, storage=None, touch=True, pre=None):
    """New iPhone-landscape page. storage: dict preloaded into localStorage. pre: async fn(ctx) run before the load (route mocks)."""
    ctx = await b.new_context(viewport=vp, has_touch=touch, is_mobile=touch, device_scale_factor=2)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    if storage is not None:
        await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
            + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in storage.items()) + '})()')
    if os.environ.get('PFS_SWITCH'):   # stand in iOS's <input switch>: the haptic labels go over every control (phone3 item 6)
        await ctx.add_init_script("Object.defineProperty(Navigator.prototype,'vibrate',{configurable:true,value:undefined});"
            "Object.defineProperty(HTMLInputElement.prototype,'switch',{configurable:true,get(){return this.hasAttribute('switch');},set(v){}});")
    if pre is not None: await pre(ctx)
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    await pg.wait_for_timeout(300)
    return pg

class Checks:
    def __init__(self): self.fails = []
    def __call__(self, name, ok, detail=''):
        print(('  ok   ' if ok else '  FAIL ') + name + (('  ' + str(detail)) if detail else ''))
        if not ok: self.fails.append(name)
        return ok
    def done(self, label):
        print(f'\n{label}: ' + ('FAILED\n  ' + '\n  '.join(self.fails) if self.fails else 'all passed'))
        return 1 if self.fails else 0

async def finger(pg, sel):
    """Tap where the element really is, the way a finger would: no actionability retries."""
    r = await pg.evaluate("(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}", sel)
    if not r: raise RuntimeError('no element ' + sel)
    await pg.touchscreen.tap(r[0], r[1])

async def splash_gone(pg):
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
