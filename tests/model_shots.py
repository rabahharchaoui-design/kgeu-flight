# Model screenshots: every aircraft from four fixed angles, in the game, on the runway.
# Usage: .venv/bin/python tests/model_shots.py <outdir> [type ...] [--big]
# Writes <outdir>/<type>_{side,front,top,quarter}.png and prints the triangle count
# of each model. Reads the reference photo folder if present and lays each shot
# next to it as <outdir>/<type>_sheet.png.
import asyncio, os, sys, json, threading, functools, http.server, socketserver
from playwright.async_api import async_playwright

def serve(root):
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    h = functools.partial(H, directory=root)
    class Q(socketserver.TCPServer): allow_reuse_address = True
    srv = Q(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/index.html'

THREE = open('node_modules/three/build/three.min.js').read()
SRV, URL = serve(os.path.abspath('.'))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/models')
TYPES = args[1:] or ['c130', 'mq9b', 'f16', 'reaper', 'cessna', 'alpha']
BIG = '--big' in sys.argv
VIEW = {'width': 1200, 'height': 700} if BIG else {'width': 844, 'height': 390}

# Reference photo per type, from refs/ (gitignored). The C-130 and MQ-9B refs were
# supplied; the others are public domain / CC photos fetched by tests/../refs/SOURCES.md.
REFS = {
    'c130': ['refs/IMG_2834.WEBP', 'refs/IMG_2832.WEBP', 'refs/IMG_2836.WEBP', 'refs/IMG_2835.WEBP'],
    'mq9b': ['refs/Pasted 2026-09-27 at 6.07.09 PM.png', 'refs/Pasted 2026-09-27 at 6.06.51 PM.png'],
    'f16': ['refs/ref_f16.jpg'], 'reaper': ['refs/ref_mq9a.jpg'],
    'cessna': ['refs/ref_c172.jpg'], 'alpha': ['refs/ref_alpha.jpg'],
}

# camera offsets in the aircraft frame, scaled by the type's length or span
def angles(L, span):
    d = max(L, span * 0.55) * 1.15          # side and three quarter
    w = max(L, span * 0.80) * 1.15          # front and top must fit the span
    return {
        'side':    {'p': [d, L * 0.10, 0.05 * L], 't': [0, 0.05 * L, 0.05 * L], 'fov': 34},
        'front':   {'p': [0, L * 0.12, -w * 1.05], 't': [0, 0.02 * L, 0], 'fov': 34},
        'top':     {'p': [0.001, w * 1.25, 0.05 * L], 't': [0, 0, 0.05 * L], 'fov': 34},
        'quarter': {'p': [d * 0.75, L * 0.36, -d * 0.75], 't': [0, 0.06 * L, 0.05 * L], 'fov': 34},
    }

async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport=VIEW, is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'ERR_' not in m.text else None)
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
        await pg.goto(URL)
        await pg.wait_for_timeout(2000)
        await pg.add_style_tag(content='body>*:not(#gl){visibility:hidden!important}')
        tris = {}
        for t in TYPES:
            await pg.evaluate(f"()=>window.__kgeu.pick('{t}')")
            await pg.wait_for_timeout(150)
            await pg.evaluate("()=>window.__kgeu.start('runway')")
            await pg.wait_for_timeout(2500)
            info = await pg.evaluate("""()=>{const p=window.__kgeu.plane();let n=0,d=0;
              p.g.traverse(m=>{if(m.isMesh&&m.visible){d++;const g=m.geometry;n+=g.index?g.index.count/3:g.attributes.position.count/3;}});
              const T=window.__kgeu.TYPES[window.__kgeu.state().type];return {tris:Math.round(n),draws:d,L:T.len,span:T.span};}""")
            tris[t] = info
            print(f'{t}: {info["tris"]} triangles, {info["draws"]} meshes')
            for name, cam in angles(info['L'], info['span']).items():
                await pg.evaluate("(c)=>window.__kgeu.freeCam(c)", cam)
                await pg.wait_for_timeout(700)
                await pg.screenshot(path=f'{OUT}/{t}_{name}.png')
            await pg.evaluate("()=>window.__kgeu.freeCam(null)")
            await pg.evaluate("()=>window.__kgeu.openMenu&&window.__kgeu.openMenu()")
            await pg.wait_for_timeout(300)
        await b.close()
    json.dump(tris, open(f'{OUT}/tris.json', 'w'), indent=1)
    if errs: print('console errors:', errs[:5])
    sheets()

def sheets():
    """Four game shots in a column beside the reference photo(s)."""
    try:
        from PIL import Image
    except ImportError:
        print('Pillow not installed, no sheets'); return
    for t in TYPES:
        shots = [f'{OUT}/{t}_{a}.png' for a in ('side', 'front', 'top', 'quarter')]
        if not all(os.path.exists(s) for s in shots): continue
        ims = [Image.open(s).convert('RGB') for s in shots]
        w = 640; ims = [i.resize((w, int(i.height * w / i.width))) for i in ims]
        refs = [Image.open(r).convert('RGB') for r in REFS.get(t, []) if os.path.exists(r)]
        refs = [r.resize((w, int(r.height * w / r.width))) for r in refs]
        hl = sum(i.height for i in ims) + 8 * (len(ims) + 1)
        hr = sum(r.height for r in refs) + 8 * (len(refs) + 1) if refs else 0
        H = max(hl, hr, 100)
        sheet = Image.new('RGB', (w * 2 + 24, H), (28, 30, 34))
        y = 8
        for i in ims: sheet.paste(i, (8, y)); y += i.height + 8
        y = 8
        for r in refs: sheet.paste(r, (w + 16, y)); y += r.height + 8
        sheet.save(f'{OUT}/{t}_sheet.png')
        print('sheet', f'{OUT}/{t}_sheet.png', 'refs' if refs else 'no reference photo')

asyncio.run(main())
