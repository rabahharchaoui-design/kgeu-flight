# fix2 item 9: thin wings read as solid, antialiased lines. Medium tier, iPhone landscape (844x390), the MQ-9B
# climbing out of Luke as tests/fix2_wings_shots.py places it (600 m AGL, 15 degrees nose up, 150 kt, Day, the sun
# behind the camera), chase view.
#  - Medium: the aircraft layer runs in the chase view (pfx().layer, its box under 35 percent of the screen), the scene
#    target itself plain; High (--high): the scene target multisampled (pfx().samples >= 2);
#  - at scale 0.7 the layer goes over the upscaled world (pfx().split, FULL at the full target size); the layer target
#    and FULL allocated once and kept (no 'rt' stall tag in flight once made), no program compiled across the scale
#    steps;
#  - the wing reads as a continuous line at scale 1 and 0.7: the canvas's centre 360x200 (backing pixels, read in the
#    frame's own task), each pixel compared with the same frame drawn without the aircraft; over the middle 60 percent
#    of the span no run of columns without a wing pixel longer than 2;
#  - the edge is smoother with the layer (Medium) or multisampling (High) on than off (__kgeu.layerOff, msaaOff): along the two wing panels
#    (10 to 38 and 62 to 90 percent of the span: no fuselage, tails, prop or winglets) the top edge row index's sign
#    changes (the spec's count, printed) and, asserted, the stair step residual: the coverage weighted top edge less its
#    21 px moving average, RMS (an aliased edge is a staircase, half a pixel peak to peak).
# Usage: .venv/bin/python -u tests/wings_check.py [type] [--high]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

TYPE = ([a for a in sys.argv[1:] if not a.startswith('--')] or ['mq9b'])[0]
TIER = 'high' if '--high' in sys.argv else 'medium'
SETUP = open(os.path.join(os.path.dirname(__file__), 'fix2_wings_shots.py')).read().split('SETUP_CLIMB = """')[1].split('"""')[0]
W, H = 360, 200
# one frame drawn and its centre read back in the same task (the drawing buffer is not preserved); hide: without the
# aircraft (the sky behind it)
GRAB = """([hide,w,h])=>{const K=window.__kgeu,r=K.R3().renderer,gl=r.getContext(),P=K.plane();
  if(hide)P.g.visible=false;K.stepFrame(0);
  const x0=(gl.drawingBufferWidth-w)>>1,y0=(gl.drawingBufferHeight-h)>>1,px=new Uint8Array(w*h*4);
  r.setRenderTarget(null);gl.readPixels(x0,y0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,px);
  if(hide)P.g.visible=true;return Array.from(px);}"""
THR = 30


def wing(I, B):
    D = [[0] * W for _ in range(H)]
    for y in range(H):
        r = (H - 1 - y) * W
        for x in range(W):
            i = (r + x) * 4
            D[y][x] = abs(I[i] - B[i]) + abs(I[i + 1] - B[i + 1]) + abs(I[i + 2] - B[i + 2])
    rows = [sum(1 for x in range(W) if D[y][x] > THR) for y in range(H)]
    y0 = max(range(H), key=lambda y: rows[y])
    lo, hi = max(0, y0 - 12), min(H, y0 + 13)
    hit = [x for x in range(W) if any(D[y][x] > THR for y in range(lo, hi))]
    if len(hit) < 20:
        return None
    a, b = hit[0], hit[-1]
    L = b - a
    gap = run = 0
    for x in range(a + int(0.2 * L), b - int(0.2 * L) + 1):
        run = 0 if any(D[y][x] > THR for y in range(lo, hi)) else run + 1
        gap = max(gap, run)
    signs, res = 0, []
    for p0, p1 in ((0.10, 0.38), (0.62, 0.90)):
        tops, sub = [], []
        for x in range(a + int(p0 * L), a + int(p1 * L) + 1):
            col = [D[y][x] for y in range(lo, hi)]
            m = max(col)
            if m <= THR:
                continue
            tops.append(next(i for i, v in enumerate(col) if v > THR))
            c = [min(1.0, v / m) if v > THR * 0.5 else 0.0 for v in col]
            T = sum(c)
            sub.append(sum((i + 0.5) * v for i, v in enumerate(c)) / T - T / 2)
        d = [v for v in (tops[i + 1] - tops[i] for i in range(len(tops) - 1)) if v]
        signs += sum(1 for i in range(len(d) - 1) if (d[i] > 0) != (d[i + 1] > 0))
        k = 10
        for i in range(k, len(sub) - k):
            res.append(sub[i] - sum(sub[i - k:i + k + 1]) / (2 * k + 1))
    rms = (sum(v * v for v in res) / max(1, len(res))) ** 0.5
    return {'row': y0, 'span': [a, b], 'gap': gap, 'signs': signs, 'stair': round(rms, 4)}


async def main():
    ok = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': TIER})
        await pg.evaluate(f"()=>{{const K=window.__kgeu;K.setTOD('day');K.pick('{TYPE}');K.pickBase('luke');K.start('runway');}}")
        await pg.wait_for_timeout(400)
        await pg.evaluate("()=>{let k=0;while(window.__kgeu.camMode()!==0&&k++<5)window.__kgeu.cycleCam();}")
        await pg.evaluate(SETUP, [150, 600, 15])
        await pg.evaluate("()=>{for(let i=0;i<24;i++)window.__kgeu.stepFrame(1/60);}")
        f = await pg.evaluate("()=>window.__kgeu.pfx()")
        ok(f'{TIER}: post chain on, WebGL2', f['post'] and f['webgl2'], f)
        if TIER == 'high':
            ok('high: scene target multisampled, samples >= 2', f['msaaRT'] and f['samples'] >= 2, f['samples'])
            ok('high, scale 1: no layer (the whole scene is multisampled)', not f['layer'], f['box'])
        else:
            ok('medium: scene target plain', not f['msaaRT'] and f['samples'] == 0, f['samples'])
            b_ = f['box']
            ok('medium, chase view: the aircraft layer ran, its box under 35% of the screen', f['layer'] and b_ and b_[2] * b_[3] < 0.35 * f['w'] * f['h'],
               f"box {b_} = {round(100 * b_[2] * b_[3] / (f['w'] * f['h']), 1) if b_ else '-'}% of the screen")
        ok('scale 1: no upscale (split false)', not f['split'] and f['sw'] == f['w'], f)

        imgs = {}

        async def grab(key):
            B = await pg.evaluate(GRAB, [True, W, H])
            I = await pg.evaluate(GRAB, [False, W, H])
            imgs[key] = I
            return wing(I, B)

        m = {}
        for sc in (1, 0.7):
            for off in (False, True):
                await pg.evaluate("([s,o,hi])=>{const K=window.__kgeu;K.setScale(s);if(hi)K.msaaOff(o);K.layerOff(o);K.stepFrame(0);}", [sc, off, TIER == 'high'])
                m[(sc, off)] = await grab((sc, off))
                f = await pg.evaluate("()=>window.__kgeu.pfx()")
                print(f'  scale {sc} {"off" if off else "on "}: {m[(sc, off)]}  samples {f["samples"]} layer {f["layer"]} box {f["box"]}')
        await pg.evaluate("()=>{const K=window.__kgeu;K.msaaOff(false);K.layerOff(false);K.setScale(1);K.stepFrame(0);}")
        for sc in (1, 0.7):
            w_ = m[(sc, False)]
            ok(f'scale {sc}: the wing found and continuous (no gap over 2 px in the middle 60% of the span)', w_ is not None and w_['gap'] <= 2, w_)
            o_ = m[(sc, True)]
            if w_ and o_ and sc == 1:
                ok(f'scale {sc}: smoother edge with the antialiasing on (stair RMS on < off)', w_['stair'] < o_['stair'],
                   f"on {w_['stair']} off {o_['stair']}; sign changes on {w_['signs']} off {o_['signs']}")

        # at 0.7 the aircraft is drawn at full resolution: its band (the wing row +-12) matches the scale 1 frame far
        # closer with the layer than without it (the upscaled 0.7 airframe)
        def band_diff(a, b, row):
            t = n = 0
            for y in range(max(0, row - 12), min(H, row + 13)):
                r_ = (H - 1 - y) * W
                for x in range(W):
                    i = (r_ + x) * 4
                    t += abs(a[i] - b[i]) + abs(a[i + 1] - b[i + 1]) + abs(a[i + 2] - b[i + 2]); n += 1
            return t / max(1, n)
        if m[(1, False)]:
            row = m[(1, False)]['row']
            d_on, d_off = band_diff(imgs[(0.7, False)], imgs[(1, False)], row), band_diff(imgs[(0.7, True)], imgs[(1, False)], row)
            ok('scale 0.7: the aircraft drawn at full resolution (band vs scale 1: layer under half of no layer)', d_on < 0.5 * d_off,
               f'mean abs diff layer {d_on:.2f} no layer {d_off:.2f}')

        # the split: entering and leaving it compiles nothing, FULL allocated once and kept
        r = await pg.evaluate("""()=>{const K=window.__kgeu,C=()=>K.progN().compiles;K.setScale(1);K.stepFrame(0);const c0=C(),a0=K.pfx().allocN,out=[];
          for(const s of [0.85,0.7,1,0.7,0.85,1,0.7]){K.setScale(s);K.stepFrame(1/60);const f=K.pfx();out.push([s,f.split,f.full,f.allocN,f.sw,f.w]);}
          return {comp:C()-c0,steps:out,a0:a0};}""")
        bad = [s for s in r['steps'] if s[1] != (s[0] < 1)]
        ok('the layer over the upscaled world exactly when the scale is under 1', not bad, r['steps'])
        full = [s for s in r['steps'] if s[1]]
        f = await pg.evaluate("()=>window.__kgeu.pfx()")
        ok('FULL is the full target size', all(s[2] == [f['w'], f['h']] for s in full), [s[2] for s in full][:2])
        ok('the layer target and FULL each allocated at most once across the scale steps', r['steps'][-1][3] - r['a0'] <= 2, f"allocN {r['a0']} -> {r['steps'][-1][3]}")
        ok('no program compiled across the scale changes and the split', r['comp'] == 0, r['comp'])
        # real frames across scale drops: the stall log's 'rt' tags (one allowed: FULL's allocation, already made above)
        await pg.evaluate("()=>{const K=window.__kgeu;K.setScale(1);K.stallsThr(120);K.stallsClear();K.stepFrame(0,true);}")
        for s in (0.7, 1, 0.85, 0.7):
            await pg.evaluate("(s)=>window.__kgeu.setScale(s)", s)
            await pg.wait_for_timeout(1200)
        st = await pg.evaluate("()=>window.__kgeu.stalls().log.map(e=>e.tags||e.tag||'')")
        rt = [t for t in st if 'rt' in (t if isinstance(t, list) else str(t).split(' '))]
        ok("stall log: no 'rt' tag in flight once FULL is made", len(rt) == 0, f'{len(st)} entries, rt {rt[:3]}')
        await pg.evaluate("()=>{const K=window.__kgeu;K.stepFrame(1/60,false,true);K.setScale(1);}")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('wings_check'))

asyncio.run(main())
