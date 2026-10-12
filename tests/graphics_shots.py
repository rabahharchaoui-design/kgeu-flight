# Graphics session screenshots: one fixed set of scenes, iPhone landscape 844x390 at 2x, for a before/after
# sheet of any build. Uses only hooks the pregraphics build already has, so it runs on both.
#   .venv/bin/python tests/graphics_shots.py <root> <outdir> [scene,scene,...]
# Shots: home, the six reference and trainer aircraft in the chase view on the KGEU runway by day,
# the Cessna on final at night, in the haboob and at sunset, the F-16 on the runway at sunset, the MQ-9A sensor ball in white hot, the map, and
# the dogfight 3 s in (fixed seed). <outdir>/metrics.json: load time to splash gone, JS heap, page errors.
# tests/graphics_fps.py imports SCENES, setup() and the page helpers from here.
import asyncio, functools, http.server, json, os, socketserver, sys, threading, time
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HERE, '..', 'node_modules/three/build/three.min.js')).read()
K = 'window.__kgeu'
SETTLE = 2500
# no onboarding, tutorial, coach marks or school intake; the load moment is caught the same way on every build
INIT = ("localStorage.setItem('kgeuOnboard','pilot');"+("localStorage.setItem('kgeuTier','"+os.environ['PFS_TIER']+"');" if os.environ.get('PFS_TIER') else '')+"localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');"
        "localStorage.setItem('kgeuPlace','{\"level\":\"ride\",\"hours\":null}');"
        "window.__gone=null;document.addEventListener('DOMContentLoaded',()=>{const s=document.getElementById('splash');if(!s)return;"
        "const o=new MutationObserver(()=>{if(s.classList.contains('gone')){window.__gone=performance.now();o.disconnect();}});"
        "o.observe(s,{attributes:true,attributeFilter:['class']});});")

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(root):
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'

async def launch(p):
    return await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])

async def open_page(b, url):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script(INIT)
    pg = await ctx.new_page(); pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    await pg.wait_for_timeout(3000)
    return ctx, pg

CAM0 = f"let k=0;while({K}.camMode()!==0&&k++<5){K}.cycleCam();"
UNMAP = f"if({K}.freeCam)({K}.freeCam(null));if(document.getElementById('mapOv').classList.contains('on')){K}.fmClose();"
# graphics item 6: the clouds are picked per flight from the daily seed (30% of days clear by day), so the day shots hold
# the scattered preset still for a stable before/after (a build without setClouds has them anyway)
def fly(t, tod, pos, base='kgeu'):
    cl = "'scattered'" if tod == 'day' else 'null'
    return f"{UNMAP}{K}.setTOD('{tod}');if({K}.setClouds){K}.setClouds({cl});{K}.pick('{t}');{K}.pickBase('{base}');{K}.start('{pos}');{CAM0}"
AC = [('f16', 'f16'), ('c130', 'c130'), ('mq9a', 'reaper'), ('mq9b', 'mq9b'), ('cessna', 'cessna'), ('pipistrel', 'alpha')]

# name -> list of steps: a JS body (run in the page) or a number (ms to wait in between)
SCENES = {'home': []}
for n, t in AC: SCENES[n] = [fly(t, 'day', 'runway')]
SCENES['night'] = [fly('cessna', 'night', 'final')]
SCENES['haboob'] = [fly('cessna', 'haboob', 'final')]
# graphics item 4: golden hour (the Cessna on final, the F-16 in the chase view on the runway)
SCENES['sunset'] = [fly('cessna', 'sunset', 'final')]
SCENES['golden_f16'] = [fly('f16', 'sunset', 'runway')]
SCENES['sensor'] = [fly('reaper', 'day', 'final'), 1200, "document.getElementById('bSensor').click();", 400, f"{K}.setSensorMode('irw');"]
SCENES['map'] = [fly('cessna', 'day', 'final'), 800, f"{K}.fmOpen();"]
# graphics item 5, the real terrain: an aircraft put in the air (state() and snapCam(), so the base builds run it too) at
# x, z (world metres), alt (ft MSL), heading (deg true), speed (kt), gear up
def air(x, z, alt, hdg, kt):
    return (f"const K={K},s=K.state(),h={hdg}*Math.PI/180,V={kt}/1.944;s.pos.set({x},({alt}-1071)/3.2808,{z});"
            "s.vel.set(Math.sin(h)*V,0,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));s.w.set(0,0,0);"
            "s.onGround=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.8;K.snapCam();")
# the F-16 at 6,000 ft 10 km west of KGEU looking west at the White Tanks, by day
SCENES['terrain_west'] = [fly('f16', 'day', 'runway'), 600, air(-10000, -1000, 6000, 270, 330)]
# the Cessna at 3,000 ft west of downtown, flying at it: South Mountain to the right and Camelback to the left, sunset
SCENES['terrain_phx'] = [fly('cessna', 'sunset', 'runway'), 600, air(14000, 2000, 3000, 126, 100)]
# the F-16 on the KGEU runway, the camera behind it looking west at the White Tanks over the airport (freeCam, world frame)
SCENES['terrain_ramp'] = [fly('f16', 'day', 'runway'), 600,
    f"{K}.freeCam({{w:true,p:[48,4.5,-1],t:[-24000,350,-6400],fov:38}});"]
# not in the sheet: the White Tanks close up by day, for the rock colours
CLOSE = {'wt_close': [fly('f16', 'day', 'runway'), 600, air(-16000, -3000, 4500, 260, 330)]}
# graphics item 6, atmosphere. A build without the hooks shoots the same views (setClouds and GFX guarded).
# the F-16 on the KGEU runway by day, chase view, its shadow on the runway (main() takes it twice, 100 ms apart, and diffs)
SCENES['shadow_ramp'] = [fly('f16', 'day', 'runway')]
# the C-130 on the KGEU ramp at sunset, the camera behind its right wing (aircraft frame): the long shadow east
SCENES['shadow_golden'] = [fly('c130', 'sunset', 'ramp'), 600, f"{K}.freeCam({{p:[24,16,36],t:[-10,0,-80],fov:50}});"]
# High forced (main() puts Auto back after every shot): the Cessna at 4,000 ft at sunset east of the White Tanks
# heading west south west at them, the range's shadows reaching out across the valley toward it
SCENES['shadow_valley'] = [f"if({K}.GFX)({K}.GFX.setTier('high'));", fly('cessna', 'sunset', 'runway'), 600, air(-15000, -9000, 4000, 241, 82)]
# the Cessna at 5,000 ft by day heading south east out of KGEU: the monsoon builds ahead
SCENES['clouds_monsoon'] = [fly('cessna', 'day', 'runway'), 600, f"if({K}.setClouds){K}.setClouds('monsoon');", air(-2000, -2000, 5000, 140, 82)]
# the same at 5,000 ft heading north west under the scattered cumulus
SCENES['clouds_scattered'] = [fly('cessna', 'day', 'runway'), 600, f"if({K}.setClouds){K}.setClouds('scattered');", air(2000, 2000, 5000, 320, 82)]
# graphics item 7, the haboob as the signature visual: the aircraft put in the air with air(), the wall jumped to m metres
# ahead of it (haboobJump; a negative m puts it inside), chase view unless said
def hbj(m): return f"if({K}.haboobJump)({K}.haboobJump({m}));"
# the Cessna at 2,000 ft heading south east 4 km from the wall, the late sun over the right shoulder (the lit face), seen
# from 36 m behind it with a 46 degree lens so the wall fills the frame
SCENES['haboob_wall'] = [fly('cessna', 'haboob', 'runway'), 600, air(3000, 3000, 3071, 150, 95), hbj(4000),
    f"{K}.freeCam({{p:[0,7,36],t:[0,330,-4000],fov:46}});"]
# 500 m from the face at 1,500 ft
SCENES['haboob_face'] = [fly('cessna', 'haboob', 'runway'), 600, air(3000, 3000, 2571, 150, 95), hbj(500)]
# 1 km inside at 1,500 ft: the dust streaks in the chase view, then in the cockpit
SCENES['haboob_inside'] = [fly('cessna', 'haboob', 'runway'), 600, air(3000, 3000, 2571, 150, 95), hbj(-1000)]
SCENES['haboob_inside_cockpit'] = SCENES['haboob_inside'] + [f"{K}.cycleCam();"]
# inside heading west, the camera looking 20 degrees up at the sun (sun azimuth 268, elevation 21): the forward scatter
SCENES['haboob_sun'] = [fly('cessna', 'haboob', 'runway'), 600, air(3000, 3000, 2571, 268, 95), hbj(-1000),
    f"{K}.freeCam({{p:[0,2.5,12],t:[0,370,-1000],fov:62}});"]
SETTLE_AT = {'explosion': 0, 'explosion_sunset': 0, 'explosion_smoke': 0, 'explosion_smoke_sunset': 0}
# 3 s of sim in 0.1 s ticks (the headless loop runs ~3 fps, so real time would be about 1 s of flight)
SCENES['dogfight'] = [f"{UNMAP}{K}.setTOD('day');{K}.DF.test.seed=1;{K}.DF.test.noBrief=true;{K}.dfStart();{CAM0}", 600,
    f"for(let i=0;i<30;i++){K}.stepFrame(0.1,false,true);{K}.stepFrame(0,true);"]

# the C-130 drop mission by day, put at 1,000 ft AGL 1.5 km north east of the drop zone heading 245, the column left of
# the nose and the sun (azimuth 147) off the left wing, so the smoke shows a lit and a shaded side
SCENES['dz_smoke'] = [f"{UNMAP}{K}.setTOD('day');if({K}.setClouds){K}.setClouds('scattered');{K}.mission('drop');{CAM0}", 1500,
    f"const K={K},D=K.DROPZ,s=K.state(),h=245*Math.PI/180,V=140/1.944,x=D.x+1260,z=D.z-820;s.pos.set(x,K.groundHeight(x,z)+305,z);"
    "s.vel.set(Math.sin(h)*V,0,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));s.w.set(0,0,0);"
    "s.onGround=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.7;K.snapCam();"]
# an F-16 crash on the KGEU runway, the wreck camera about 0.5 s into the explosion (stepped until fx().t is there) (SETTLE_AT: no settle, the shot at once);
# last in the list, as nothing in the later scenes clears the burning wreck
def boom(tod): return [fly('f16', tod, 'runway'), 1500, f"{K}.crashNow('Graphics shot.');for(let i=0;i<120&&!({K}.fx().active&&{K}.fx().t>=0.47);i++){K}.stepFrame(1/30,false,true);{K}.stepFrame(1/60);"
    "document.getElementById('bigFlash').style.visibility='hidden';document.getElementById('toast').classList.remove('on');", 150]
SCENES['explosion'] = boom('day')
SCENES['explosion_sunset'] = boom('sunset')
# not in the sheet: the same crash 6 s on by day and at sunset, for the smoke column's light
CLOSE['explosion_smoke'] = boom('day')[:-1] + [f"for(let i=0;i<165;i++){K}.stepFrame(1/30,false,true);{K}.stepFrame(1/60);", 150]
CLOSE['explosion_smoke_sunset'] = boom('sunset')[:-1] + [f"for(let i=0;i<165;i++){K}.stepFrame(1/30,false,true);{K}.stepFrame(1/60);", 150]

# the mean and the largest abs difference (0..255) over the aircraft and its shadow (the middle of the frame, under
# the HUD), and the share of pixels there that moved more than 24
def swim(a, b):
    from PIL import Image, ImageChops, ImageStat
    A, B = Image.open(a).convert('L'), Image.open(b).convert('L')
    w, h = A.size; box = (int(w * 0.3), int(h * 0.48), int(w * 0.7), int(h * 0.78))
    d = ImageChops.difference(A.crop(box), B.crop(box)); hg = d.histogram(); n = sum(hg)
    mx = max(i for i, c in enumerate(hg) if c)
    return f'mean {ImageStat.Stat(d).mean[0]:.2f} max {mx} moved {sum(hg[25:]) / n * 100:.2f}%'

async def setup(pg, name):
    for s in SCENES[name]:
        if isinstance(s, int): await pg.wait_for_timeout(s)
        else: await pg.evaluate("(js)=>{(new Function(js))();}", s)
    await pg.wait_for_timeout(SETTLE_AT.get(name, SETTLE))

async def main():
    root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    T0 = time.time()
    async with async_playwright() as p:
        b = await launch(p)
        ctx, pg = await open_page(b, serve(root))
        load = await pg.evaluate("()=>window.__gone==null?null:Math.round(window.__gone)")
        only = sys.argv[3].split(',') if len(sys.argv) > 3 else None   # optional: a comma list of scene names
        for name in SCENES:
            if only and name not in only: continue
            t = time.time()
            try:
                await setup(pg, name)
                await pg.screenshot(path=os.path.join(out, name + '.png'))
                if name == 'shadow_ramp':   # two frames 100 ms apart: the shadow must not swim
                    await pg.wait_for_timeout(100); await pg.screenshot(path=os.path.join(out, 'shadow_ramp_b.png'))
                    print('  shadow_ramp vs 100 ms later: ' + swim(os.path.join(out, 'shadow_ramp.png'), os.path.join(out, 'shadow_ramp_b.png')))
                await pg.evaluate(f"()=>{{if({K}.setClouds){K}.setClouds(null);if({K}.GFX&&{K}.GFX.setTier&&{K}.GFX.tier!=={K}.GFX.auto){K}.GFX.setTier('auto');}}")
                info = await pg.evaluate(f"()=>({{scr:{K}.curScr(),run:{K}.running(),cam:{K}.camMode(),df:!!({K}.DF&&{K}.DF.on)}})")
                print(f'{name}.png  {time.time()-t:.1f}s  {json.dumps(info)}')
            except Exception as e:
                print(f'{name}.png  FAILED  {str(e).splitlines()[0]}'); pg.errs.append(f'{name}: {e}')
        heap = await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576*10)/10:null")
        errs = list(pg.errs)
        await ctx.close(); await b.close()
    json.dump({'loadMs': load, 'heapMB': heap, 'errors': errs}, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    print(f'graphics_shots: {len(SCENES)} shots to {out} in {time.time()-T0:.0f}s, loadMs {load}, heapMB {heap}, {len(errs)} page errors')
    for e in errs: print('  error:', e)

if __name__ == "__main__":
    asyncio.run(main())
