# Model screenshots: every aircraft from four fixed angles, in the game, on the runway.
# Usage: .venv/bin/python tests/model_shots.py <outdir> [type ...] [--big]
# Writes <outdir>/<type>_{side,left,front,rear,quarter,top}.png and prints the triangle
# count of each model. Reads the reference photo folders in refs/ (gitignored) if present
# and lays the shots next to them as <outdir>/<type>_sheet.png.
import asyncio, os, sys, json, glob, threading, functools, http.server, socketserver
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

# Reference photos per type, from refs/ (gitignored, never committed). A folder takes
# every photo in it; WEBP and HEIC are read through a sips copy in /tmp if Pillow cannot.
REFS = {
    'c130': ['refs/IMG_2834.WEBP', 'refs/IMG_2832.WEBP', 'refs/IMG_2836.WEBP', 'refs/IMG_2835.WEBP'],
    'mq9b': ['refs/mq9b'], 'f16': ['refs/ref_f16.jpg'], 'reaper': ['refs/mq9a'],
    'cessna': ['refs/cessna172'], 'alpha': ['refs/pipistrel'],
}
def ref_files(t):
    out = []
    for r in REFS.get(t, []):
        if os.path.isdir(r):
            out += sorted(f for f in glob.glob(r + '/*') if f.lower().rsplit('.', 1)[-1] in ('jpg', 'jpeg', 'png', 'webp', 'heic'))
        elif os.path.exists(r): out.append(r)
    return out
def open_ref(path, Image):
    try: return Image.open(path).convert('RGB')
    except Exception:
        tmp = '/tmp/model_shots_refs/' + os.path.basename(path).rsplit('.', 1)[0] + '.jpg'
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        if not os.path.exists(tmp): os.system(f'sips -s format jpeg "{path}" --out "{tmp}" >/dev/null 2>&1')
        try: return Image.open(tmp).convert('RGB')
        except Exception: return None

# camera offsets in the aircraft frame, scaled by the type's length or span
def angles(L, span):
    d = max(L * 1.15, span * 0.7 + L * 0.5)  # side and three quarter: keep the near wingtip well off the lens
    w = max(L, span * 0.80) * 1.15          # front and top must fit the span
    return {
        'side':    {'p': [d, L * 0.10, 0.05 * L], 't': [0, 0.05 * L, 0.05 * L], 'fov': 34},
        'left':    {'p': [-d, L * 0.10, 0.05 * L], 't': [0, 0.05 * L, 0.05 * L], 'fov': 34},
        'front':   {'p': [0, L * 0.12, -w * 1.05], 't': [0, 0.02 * L, 0], 'fov': 34},
        'rear':    {'p': [0, L * 0.14, w * 1.05], 't': [0, 0.03 * L, 0], 'fov': 34},
        'quarter': {'p': [d * 0.75, L * 0.36, -d * 0.75], 't': [0, 0.06 * L, 0.05 * L], 'fov': 34},
        'top':     {'p': [0.001, w * 1.25, 0.05 * L], 't': [0, 0, 0.05 * L], 'fov': 34},
    }

# the camera of the main reference photo, where it differs from the fixed angles
def photo_angle(t, L, span):
    d = max(L * 1.15, span * 0.7 + L * 0.5)
    return {'alpha':  {'p': [d * 0.93, L * 0.05, -d * 0.36], 't': [0, 0.0, 0.05 * L], 'fov': 30},
            'cessna': {'p': [-d, L * 0.30, -d * 0.05], 't': [0, 0.02 * L, 0.05 * L], 'fov': 30},
            'reaper': {'p': [-d * 0.55, L * 0.55, -d * 0.35], 't': [0, 0, 0.05 * L], 'fov': 34},
            'mq9b':   {'p': [-d * 0.62, L * 0.40, d * 0.35], 't': [0, 0, 0], 'fov': 34}}.get(t)

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
            A = angles(info['L'], info['span'])
            if photo_angle(t, info['L'], info['span']): A['photo'] = photo_angle(t, info['L'], info['span'])
            for name, cam in A.items():
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
        shots = [f'{OUT}/{t}_{a}.png' for a in ('side', 'left', 'front', 'rear', 'quarter', 'top')]
        if not all(os.path.exists(s) for s in shots): continue
        ims = [Image.open(s).convert('RGB') for s in shots]
        w = 640; ims = [i.resize((w, int(i.height * w / i.width))) for i in ims]
        refs = [i for i in (open_ref(r, Image) for r in ref_files(t)) if i is not None]
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
