# Runways session: "before" pictures of every runway end in the game, from the
# unchanged baseline (run this against the prerunways worktree/tag before the
# runway_grade_check work lands, then again after, to diff by eye).
#
# iPhone 15 landscape (844x390, device_scale_factor 2), software rendering
# (swiftshader), served over http the way tests/aircraft_fps.py's serve(root)
# does: a ThreadingTCPServer on a random port, three.min.js routed from
# node_modules, fonts blocked.
#
# One page per region (localStorage kgeuRegion = az | rjtt | lfpg | sbrj), Hard
# mode (kgeuOnboard=pilot, kgeuTut=1, kgeuCoach=3), graphics tier left default.
# For every end in window.__kgeu.RWY_ENDS (az: Glendale KGEU, Luke KLUF, Sky
# Harbor KPHX and the assault strip LZ, about 14 ends; a world region: just its
# own runways, 8/8/4 for rjtt/lfpg/sbrj -- about 34 ends total) the Cessna is
# placed by hand at the end: 60 m past the threshold on the centreline, stopped
# ('runway'), or on the 3 degree path 1 nm out, established ('final'). Each
# position is shot in both cameras (cockpit = the nose camera, camMode 1; chase
# = camMode 0 -- verified against a real screenshot, not the reverse) and both
# times of day (day, night): 8 shots per end, named
#   <outdir>/<region>_<code>_<num>_<pos>_<cam>_<tod>.png
#
# Usage:
#   .venv/bin/python tests/runway_shots.py <root> <outdir> [--regions az,rjtt,lfpg,sbrj] [--ends CODE-NUM,...]
import argparse, asyncio, functools, http.server, os, socketserver, threading
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HERE, '..', 'node_modules/three/build/three.min.js')).read()

BASE_STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
POS = ('runway', 'final')
CAMS = ('cockpit', 'chase')
TODS = ('day', 'night')
CAM_TARGET = {'chase': 0, 'cockpit': 1}   # CAMS=['Chase','Nose camera',...] in index.html; camMode defaults to 0 (chase)

# ---------- browser-side snippets (args passed through evaluate, never string-interpolated) ----------
ENDS_JS = "()=>window.__kgeu.RWY_ENDS.map(e=>({num:e.num,x:e.x,z:e.z,h:e.h,dx:e.dx,dz:e.dz,code:e.rwy.code,apt:e.rwy.apt}))"
BASE_KEY_JS = "()=>Object.keys(window.__kgeu.BASES)[0]"
WORLD_READY_JS = "()=>!!(window.__kgeu.WORLD&&window.__kgeu.WORLD.ready)"
SETUP_JS = "(b)=>{const K=window.__kgeu;K.pick('cessna');K.pickBase(b);K.start('final');}"
CAM_JS = "(m)=>{const K=window.__kgeu;let k=0;while(K.camMode()!==m&&k++<6)K.cycleCam();}"
TOD_JS = "(id)=>{const K=window.__kgeu;K.setTOD(id);if(K.setWX){try{K.setWX('clear');}catch(e){}}}"
SNAP_STEP_JS = "()=>{const K=window.__kgeu;K.snapCam();for(let i=0;i<4;i++)K.stepFrame(1/30);}"

PLACE_JS = {
    'runway': """(e)=>{const K=window.__kgeu,s=K.state(),fr=K.rwyFrame();
      const x=e.x+e.dx*60, z=e.z+e.dz*60;
      s.pos.set(x, K.groundHeight(x,z)+fr.gear, z);
      s.vel.set(0,0,0);
      s.quat.setFromEuler(new THREE.Euler(0,-e.h,0,'YXZ'));
      s.w.set(0,0,0); s.onGround=true; s.airTime=0; s.throttle=s.power=0; s.ap=null;
      K.touchIn.active=false;}""",
    'final': """(e)=>{const K=window.__kgeu,s=K.state(),fr=K.rwyFrame();
      const x=e.x-e.dx*1852, z=e.z-e.dz*1852;
      const y=K.groundHeight(e.x,e.z)+1852*Math.tan(3*Math.PI/180)+fr.gear;
      s.pos.set(x,y,z);
      s.vel.set(32*e.dx,-1.7,32*e.dz);
      s.quat.setFromEuler(new THREE.Euler(0.03,-e.h,0,'YXZ'));
      s.onGround=false; s.airTime=30; s.flapIdx=3; s.gearDown=true; s.gearPos=1; s.throttle=s.power=0.3;}""",
}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'


async def splash_gone(pg):
    await pg.wait_for_function(
        "()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)


async def run_region(b, url, outdir, region, want_ends):
    storage = dict(BASE_STORAGE)
    storage['kgeuRegion'] = region
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True,
                               device_scale_factor=2)
    await ctx.add_init_script(''.join(f"localStorage.setItem({k!r},{v!r});" for k, v in storage.items()))
    pg = await ctx.new_page()
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url)
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await splash_gone(pg)
    if region != 'az':
        await pg.wait_for_function(WORLD_READY_JS, timeout=60000)
        await pg.wait_for_timeout(2000)
    else:
        await pg.wait_for_timeout(500)

    ends = await pg.evaluate(ENDS_JS)
    if want_ends:
        ends = [e for e in ends if f"{e['code']}-{e['num']}" in want_ends]
    base = 'kgeu' if region == 'az' else await pg.evaluate(BASE_KEY_JS)
    print(f'{region}: {len(ends)} ends, base {base!r}')

    written = []
    for e in ends:
        tag = f"{region}_{e['code']}_{e['num']}"
        try:
            await pg.evaluate(SETUP_JS, base)
            await pg.wait_for_timeout(300)
        except Exception as ex:
            print(f'  FAIL {tag} setup: {ex}')
            continue
        for pos in POS:
            try:
                await pg.evaluate(PLACE_JS[pos], e)
            except Exception as ex:
                print(f'  FAIL {tag}_{pos} place: {ex}')
                continue
            for camn in CAMS:
                try:
                    await pg.evaluate(CAM_JS, CAM_TARGET[camn])
                except Exception as ex:
                    print(f'  FAIL {tag}_{pos}_{camn} cam: {ex}')
                    continue
                for tod in TODS:
                    fname = f"{tag}_{pos}_{camn}_{tod}.png"
                    path = os.path.join(outdir, fname)
                    try:
                        await pg.evaluate(TOD_JS, tod)
                        await pg.evaluate(SNAP_STEP_JS)
                        await pg.wait_for_timeout(250)
                        await pg.screenshot(path=path, timeout=60000)
                        written.append(fname)
                        print('  wrote', fname)
                    except Exception as ex:
                        print(f'  FAIL {fname}: {ex}')
    await ctx.close()
    return written


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('outdir')
    ap.add_argument('--regions', default='az,rjtt,lfpg,sbrj')
    ap.add_argument('--ends', default='')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    regions = [r for r in args.regions.split(',') if r]
    want_ends = set(x for x in args.ends.split(',') if x) or None
    url = serve(os.path.abspath(args.root))

    all_written = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl',
                                           '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        for region in regions:
            print(f'== {region} ==')
            try:
                w = await run_region(b, url, args.outdir, region, want_ends)
            except Exception as ex:
                print(f'  FAIL region {region}: {ex}')
                w = []
            all_written += w
        await b.close()

    idx_path = os.path.join(args.outdir, 'index.txt')
    with open(idx_path, 'a') as f:
        for w in all_written:
            f.write(w + '\n')
    print(f'runway_shots: {len(all_written)} shots written this run, index at {idx_path}')


if __name__ == '__main__':
    asyncio.run(main())
