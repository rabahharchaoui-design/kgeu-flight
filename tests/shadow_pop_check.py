# Gfxfix: proves the shadow cascade pop. csmFrame (index.html) switches the near cascade off once the camera's
# AGL clears 762 m and the mid cascade off above 2,438 m, with no hysteresis and no fade. Climbing or descending
# through those heights on a held, deterministic loop (stepFrame, one tick per frame, render included) should
# show a single-frame spike in frame to frame image difference right where the cascade mask bit flips.
#   .venv/bin/python tests/shadow_pop_check.py <root> --out <dir> [--tier medium|high] [--seq A,B,C,D] [--n frames]
# Every DOM overlay (HUD, map, buttons, radio, stick) is hidden before any sequence runs, leaving only the WebGL
# canvas, so the diff is scene pixels only.
# Sequence A climbs the F-16 700 m to 1,000 m AGL over the flat valley floor (crosses the 762 m near threshold),
# 2.5 m/frame x 120 frames; B is the same descent. Metric: mean (and summed) abs difference of greyscale pixels
# against the previous frame, over a 260x140 box centred on the aircraft (fixed per sequence, picked by eye at
# the flip frame and printed; see VERIFY_NOTE below).
# Sequence C is the ridge shimmer: the F-16 at sunset, terrain-following 150 m AGL toward the White Tanks ridge
# line (found by sampling groundHeight), 90 frames, diffed over the lower 55% of the frame (the terrain). D is
# the same scenario with GFX.setTier('high') first (the far cascade is High only); the 'sawtooth' ratio (median
# of odd-frame diffs / median of even-frame diffs) is the number that matters there.
# Always exits 0: this is a measurement script, not a gate.
import asyncio, json, os, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
def opt(name, dflt):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return dflt
OUT = opt('--out', '/tmp/gfxfix/pop')
TIER = opt('--tier', 'medium')
NFRAMES = int(opt('--n', '120'))    # frames for A/B; default 120 (2.5 m/frame over 300 m). Lower only for a smoke test.
NFRAMES_C = int(opt('--nc', '90'))  # frames for C/D
SEQ = opt('--seq', 'A,B,C,D').split(',')
ROOT = os.path.abspath(args[0] if args else os.path.join(HERE, '..'))
os.environ['PFS_TIER'] = TIER   # graphics_shots builds INIT from this at import time (kgeuTier in localStorage)

sys.path.insert(0, HERE)
from graphics_shots import serve, launch, open_page, fly, air, CAM0, K   # noqa: E402

os.makedirs(OUT, exist_ok=True)

# hide every DOM overlay over the canvas (#gl is a direct <body> child; every other direct child -- #fpsPill,
# #sensorFx, #hood, #uiroot (HUD, map, buttons, stick, radio) -- sits beside it, not inside it) so the HUD's
# live numbers stop contributing to the pixel diff. The canvas itself, and the 3D scene, are untouched.
HIDE_JS = "Array.from(document.body.children).forEach(e=>{if(e.id!=='gl')e.style.visibility='hidden';});"

# ---------- sequences A/B: climb/descend through the near cascade threshold ----------
# the F-16 level, 6 km west of KGEU over the flat valley floor (groundHeight there is 0; air() takes alt in ft
# MSL, the valley floor at 1,071 ft), heading 270 (west) at 300 kt
AC_X, AC_Z, HDG, KT = -6000, 0, 270, 300
FIELD_FT = 1071.0      # ft MSL of the valley floor here (verified ~0 m groundHeight, printed below)
def alt_ft(agl_m, gh_m=0.0): return FIELD_FT + (gh_m + agl_m) * 3.2808

# VERIFY_NOTE: box for A/B, picked by eye on the saved frames of an earlier run (same camera/placement code):
# the aircraft sits at roughly screen (847, 430) at 700 m AGL and (847, 320) at 1,000 m AGL (chase view, 1688x780
# at 2x); a 260x140 box centred at (847, 370) covers it fully through the 762 m flip region and at 1,000 m, and
# mostly (minus a little headroom) at the 700 m start -- the cascade flip never happens that early, so this is
# the region that matters. Printed again at run time.
BOX_AB = (717, 300, 977, 440)

# hold the aircraft level at a given AGL: re-set height every frame off the current x,z's ground, keep velocity
# level (air() already sets a level velocity; this only rewrites pos.y so the climb/descent/terrain-follow is
# driven by the test, not the autopilot)
def set_agl(agl_m):
    return (f"{{const K={K},s=K.state(),gh=K.groundHeight(s.pos.x,s.pos.z);"
            f"s.pos.y=gh+{agl_m};s.vel.y=0;s.w.set(0,0,0);}}")

def mean_sum_abs_diff(a_path, b_path, box):
    from PIL import Image, ImageChops, ImageStat
    A, B = Image.open(a_path).convert('L'), Image.open(b_path).convert('L')
    d = ImageChops.difference(A.crop(box), B.crop(box))
    st = ImageStat.Stat(d)
    return st.mean[0], st.sum[0]

async def run_sequence(pg, out_dir, name, agl_start, agl_end, n_frames, box, gh_fn=None):
    step = (agl_end - agl_start) / n_frames
    rows = []
    prev_path = None
    for i in range(n_frames + 1):
        agl = agl_start + step * i
        await pg.evaluate("(js)=>{(new Function(js))();}", set_agl(agl))
        await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
        cur_path = os.path.join(out_dir, f'{name}_{i:03d}.png')
        await pg.screenshot(path=cur_path)
        csm = await pg.evaluate(f"()=>{K}.csm()")
        act = csm['act'] or 0
        row = {'i': i, 'agl': round(agl, 2), 'near': bool(act & 1), 'mid': bool(act & 2), 'strength': csm['strength'],
               'path': cur_path}
        if prev_path is not None:
            row['diff'], row['diff_sum'] = mean_sum_abs_diff(prev_path, cur_path, box)
        else:
            row['diff'], row['diff_sum'] = 0.0, 0.0
        rows.append(row)
        prev_path = cur_path
    return rows

def summarize(rows, name):
    diffs = [r['diff'] for r in rows[1:]]
    sums = [r['diff_sum'] for r in rows[1:]]
    med = sorted(diffs)[len(diffs) // 2] if diffs else 0
    med_sum = sorted(sums)[len(sums) // 2] if sums else 0
    mx_i = max(range(1, len(rows)), key=lambda i: rows[i]['diff']) if len(rows) > 1 else 0
    mx = rows[mx_i]['diff'] if rows else 0
    mx_sum = rows[mx_i]['diff_sum'] if rows else 0
    flip_i = None
    for i in range(1, len(rows)):
        if rows[i]['near'] != rows[i - 1]['near']:
            flip_i = i; break
    pop = bool(med > 0 and mx > 4 * med and flip_i is not None and abs(mx_i - flip_i) <= 2)
    for r in rows:
        r['spike'] = (med > 0 and r['diff'] > 4 * med)
    return {'name': name, 'median_diff': round(med, 3), 'max_diff': round(mx, 3),
            'median_diff_sum': round(med_sum), 'max_diff_sum': round(mx_sum),
            'max_i': mx_i, 'max_agl': rows[mx_i]['agl'] if rows else None, 'near_flip_i': flip_i,
            'near_flip_agl': rows[flip_i]['agl'] if flip_i is not None else None, 'pop': pop}

def make_strip(rows, mx_i, out_path, span=3, label=None):
    from PIL import Image, ImageDraw
    idxs = [i for i in range(mx_i - span, mx_i + span + 1) if 0 <= i < len(rows)]
    if not idxs: return
    thumb_w, thumb_h = 211, 97   # 844x390 / 4
    cols = len(idxs)
    sheet = Image.new('RGB', (thumb_w * cols, thumb_h + 16), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    label = label or (lambda r, i: f"i{i} agl{r['agl']:.0f} n{int(r['near'])}m{int(r['mid'])}")
    for c, i in enumerate(idxs):
        im = Image.open(rows[i]['path']).convert('RGB').resize((thumb_w, thumb_h))
        sheet.paste(im, (c * thumb_w, 16))
        draw.text((c * thumb_w + 2, 2), label(rows[i], i), fill=(255, 255, 0))
    sheet.save(out_path)

# ---------- sequences C/D: the ridge shimmer (terrain-following toward the White Tanks at sunset) ----------
async def find_ridge_point(pg, z=-5000, x0=-12000, step=-100, thresh=300.0):
    x = x0
    while True:
        gh = await pg.evaluate(f"()=>{K}.groundHeight({x},{z})")
        if gh > thresh: return x, z, gh
        x += step
        if x < -30000: return x, z, gh   # safety stop

BOX_C = None   # computed at run time: (0, h*0.45, w, h)

async def run_ridge_sequence(pg, out_dir, name, x0, z0, agl_m, n_frames, box):
    rows = []
    prev_path = None
    for i in range(n_frames + 1):
        await pg.evaluate("(js)=>{(new Function(js))();}", set_agl(agl_m))
        await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
        cur_path = os.path.join(out_dir, f'{name}_{i:03d}.png')
        await pg.screenshot(path=cur_path)
        st = await pg.evaluate(f"()=>{{const s={K}.state();return {{x:s.pos.x,z:s.pos.z,y:s.pos.y}};}}")
        row = {'i': i, 'x': round(st['x'], 1), 'z': round(st['z'], 1), 'y': round(st['y'], 2), 'path': cur_path}
        if prev_path is not None:
            row['diff'], row['diff_sum'] = mean_sum_abs_diff(prev_path, cur_path, box)
        else:
            row['diff'], row['diff_sum'] = 0.0, 0.0
        rows.append(row)
        prev_path = cur_path
    return rows

def pctl(vals, p):
    if not vals: return 0
    s = sorted(vals); k = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
    return s[k]

def summarize_ridge(rows, name):
    diffs = [r['diff'] for r in rows[1:]]
    odd = [d for k, d in enumerate(diffs) if k % 2 == 1]     # frame indices 1-based within diffs; alternate parity
    even = [d for k, d in enumerate(diffs) if k % 2 == 0]
    med_odd = sorted(odd)[len(odd) // 2] if odd else 0
    med_even = sorted(even)[len(even) // 2] if even else 0
    saw = (med_odd / med_even) if med_even else (float('inf') if med_odd else 1.0)
    mx_i = max(range(1, len(rows)), key=lambda i: rows[i]['diff']) if len(rows) > 1 else 0
    return {'name': name, 'median_diff': round(sorted(diffs)[len(diffs) // 2] if diffs else 0, 4),
            'p90_diff': round(pctl(diffs, 90), 4), 'max_diff': round(max(diffs) if diffs else 0, 4),
            'max_i': mx_i, 'sawtooth_ratio': round(saw, 3)}

async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await launch(p)
        url = serve(ROOT)
        ctx, pg = await open_page(b, url)   # waits for splash gone + 3s settle already
        summary = {}

        if 'A' in SEQ or 'B' in SEQ:
            await pg.evaluate("(js)=>{(new Function(js))();}", fly('f16', 'day', 'runway'))
            await pg.wait_for_timeout(1000)
            # place the aircraft, level, 700 m AGL, over the flat valley floor
            await pg.evaluate("(js)=>{(new Function(js))();}", air(AC_X, AC_Z, alt_ft(700), HDG, KT))
            gh = await pg.evaluate(f"()=>{K}.groundHeight({AC_X},{AC_Z})")
            print(f'groundHeight({AC_X},{AC_Z}) = {gh} (expect ~0)')
            # settle the chase camera on the held loop: 30 frames, no measurement
            for _ in range(30):
                await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
            await pg.evaluate("(js)=>{(new Function(js))();}", HIDE_JS)
            await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
            print(f'box A/B: {BOX_AB} (260x140, centred on the aircraft, picked by eye -- see VERIFY_NOTE)')
            summary['groundHeight_AB'] = gh
            summary['box_AB'] = BOX_AB

        if 'A' in SEQ:
            print('--- sequence A: climb 700 -> 1000 m AGL ---')
            rows_a = await run_sequence(pg, OUT, 'a', 700, 1000, NFRAMES, BOX_AB)
            for r in rows_a:
                print(f"A i={r['i']:3d} agl={r['agl']:7.1f} near={int(r['near'])} mid={int(r['mid'])} "
                      f"strength={r['strength']:.3f} diff={r['diff']:.3f} sum={r['diff_sum']:.0f}" +
                      ('  SPIKE' if r.get('spike') else ''))
            sum_a = summarize(rows_a, 'A (climb 700->1000m)')
            make_strip(rows_a, sum_a['max_i'], os.path.join(OUT, 'pop_strip_a.png'))
            import shutil; shutil.copy(rows_a[sum_a['max_i']]['path'], os.path.join(OUT, 'max_spike_a.png'))
            json.dump([{k: v for k, v in r.items() if k != 'path'} for r in rows_a],
                       open(os.path.join(OUT, 'frames_A.json'), 'w'), indent=1)
            json.dump(sum_a, open(os.path.join(OUT, 'summary_A.json'), 'w'), indent=1)
            summary['A'] = sum_a

        if 'B' in SEQ:
            print('--- sequence B: descend 1000 -> 700 m AGL ---')
            rows_b = await run_sequence(pg, OUT, 'b', 1000, 700, NFRAMES, BOX_AB)
            for r in rows_b:
                print(f"B i={r['i']:3d} agl={r['agl']:7.1f} near={int(r['near'])} mid={int(r['mid'])} "
                      f"strength={r['strength']:.3f} diff={r['diff']:.3f} sum={r['diff_sum']:.0f}" +
                      ('  SPIKE' if r.get('spike') else ''))
            sum_b = summarize(rows_b, 'B (descend 1000->700m)')
            make_strip(rows_b, sum_b['max_i'], os.path.join(OUT, 'pop_strip_b.png'))
            import shutil; shutil.copy(rows_b[sum_b['max_i']]['path'], os.path.join(OUT, 'max_spike_b.png'))
            json.dump([{k: v for k, v in r.items() if k != 'path'} for r in rows_b],
                       open(os.path.join(OUT, 'frames_B.json'), 'w'), indent=1)
            json.dump(sum_b, open(os.path.join(OUT, 'summary_B.json'), 'w'), indent=1)
            summary['B'] = sum_b

        if 'A' in summary and 'B' in summary:
            from PIL import Image
            ia = Image.open(os.path.join(OUT, 'pop_strip_a.png')); ib = Image.open(os.path.join(OUT, 'pop_strip_b.png'))
            w = max(ia.width, ib.width)
            combo = Image.new('RGB', (w, ia.height + ib.height), (20, 20, 20))
            combo.paste(ia, (0, 0)); combo.paste(ib, (0, ia.height))
            combo.save(os.path.join(OUT, 'pop_strip.png'))

        if 'C' in SEQ or 'D' in SEQ:
            print('--- finding the ridge point (groundHeight sampled west from x=-12000, z=-5000) ---')
            rx, rz, rgh = await find_ridge_point(pg)
            print(f'ridge line (first > 300 m): x={rx} z={rz} groundHeight={rgh:.1f} m')
            cx, cz = rx + 2000, rz   # 2 km east of the ridge line
            cgh = await pg.evaluate(f"()=>{K}.groundHeight({cx},{cz})")
            print(f'sequence C/D start point: x={cx} z={cz} groundHeight={cgh:.1f} m')
            await pg.evaluate("(js)=>{(new Function(js))();}", fly('f16', 'sunset', 'runway'))
            await pg.wait_for_timeout(1000)
            await pg.evaluate("(js)=>{(new Function(js))();}", air(cx, cz, alt_ft(150, cgh), 270, 250))
            for _ in range(30):
                await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
            await pg.evaluate("(js)=>{(new Function(js))();}", HIDE_JS)
            await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
            vp = pg.viewport_size; sf = 2   # open_page's device_scale_factor
            box_c = (0, int(vp['height'] * sf * 0.45), int(vp['width'] * sf), int(vp['height'] * sf))
            print(f'box C/D: {box_c} (full width, lower 55% of frame, the terrain)')
            summary['ridge_point'] = {'x': rx, 'z': rz, 'gh': rgh}
            summary['start_point'] = {'x': cx, 'z': cz, 'gh': cgh}
            summary['box_C'] = box_c

        if 'C' in SEQ:
            print('--- sequence C: ridge shimmer, Medium ---')
            rows_c = await run_ridge_sequence(pg, OUT, 'c', cx, cz, 150, NFRAMES_C, box_c)
            for r in rows_c:
                print(f"C i={r['i']:3d} x={r['x']:9.1f} z={r['z']:9.1f} y={r['y']:7.2f} diff={r['diff']:.4f} sum={r['diff_sum']:.0f}")
            sum_c = summarize_ridge(rows_c, 'C (ridge shimmer, Medium)')
            make_strip(rows_c, sum_c['max_i'], os.path.join(OUT, 'strip_c.png'),
                       label=lambda r, i: f"i{i} x{r['x']:.0f} y{r['y']:.1f}")
            json.dump([{k: v for k, v in r.items() if k != 'path'} for r in rows_c],
                       open(os.path.join(OUT, 'frames_C.json'), 'w'), indent=1)
            json.dump(sum_c, open(os.path.join(OUT, 'summary_C.json'), 'w'), indent=1)
            summary['C'] = sum_c

        if 'D' in SEQ:
            print('--- sequence D: ridge shimmer, High (GFX.setTier) ---')
            await pg.evaluate(f"()=>{{if({K}.GFX)({K}.GFX.setTier('high'));}}")
            # re-place at the same start point (C may have flown the aircraft west along the ridge)
            await pg.evaluate("(js)=>{(new Function(js))();}", air(cx, cz, alt_ft(150, cgh), 270, 250))
            for _ in range(10):
                await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);}}")
            rows_d = await run_ridge_sequence(pg, OUT, 'd', cx, cz, 150, NFRAMES_C, box_c)
            for r in rows_d:
                print(f"D i={r['i']:3d} x={r['x']:9.1f} z={r['z']:9.1f} y={r['y']:7.2f} diff={r['diff']:.4f} sum={r['diff_sum']:.0f}")
            sum_d = summarize_ridge(rows_d, 'D (ridge shimmer, High)')
            make_strip(rows_d, sum_d['max_i'], os.path.join(OUT, 'strip_d.png'),
                       label=lambda r, i: f"i{i} x{r['x']:.0f} y{r['y']:.1f}")
            json.dump([{k: v for k, v in r.items() if k != 'path'} for r in rows_d],
                       open(os.path.join(OUT, 'frames_D.json'), 'w'), indent=1)
            json.dump(sum_d, open(os.path.join(OUT, 'summary_D.json'), 'w'), indent=1)
            summary['D'] = sum_d
            await pg.evaluate(f"()=>{{if({K}.GFX)({K}.GFX.setTier('auto'));}}")

        json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
        print('--- summary ---')
        print(json.dumps(summary, indent=1))
        errs = list(pg.errs)
        if errs: print('page errors:', errs)
        await ctx.close(); await b.close()

if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
