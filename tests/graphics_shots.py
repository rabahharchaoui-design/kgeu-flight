# Graphics session screenshots: one fixed set of scenes, iPhone landscape 844x390 at 2x, for a before/after
# sheet of any build. Uses only hooks the pregraphics build already has, so it runs on both.
#   .venv/bin/python tests/graphics_shots.py <root> <outdir>
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
INIT = ("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');"
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
def fly(t, tod, pos, base='kgeu'):
    return f"{UNMAP}{K}.setTOD('{tod}');{K}.pick('{t}');{K}.pickBase('{base}');{K}.start('{pos}');{CAM0}"
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
# 3 s of sim in 0.1 s ticks (the headless loop runs ~3 fps, so real time would be about 1 s of flight)
SCENES['dogfight'] = [f"{UNMAP}{K}.setTOD('day');{K}.DF.test.seed=1;{K}.DF.test.noBrief=true;{K}.dfStart();{CAM0}", 600,
    f"for(let i=0;i<30;i++){K}.stepFrame(0.1,false,true);{K}.stepFrame(0,true);"]

async def setup(pg, name):
    for s in SCENES[name]:
        if isinstance(s, int): await pg.wait_for_timeout(s)
        else: await pg.evaluate("(js)=>{(new Function(js))();}", s)
    await pg.wait_for_timeout(SETTLE)

async def main():
    root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    T0 = time.time()
    async with async_playwright() as p:
        b = await launch(p)
        ctx, pg = await open_page(b, serve(root))
        load = await pg.evaluate("()=>window.__gone==null?null:Math.round(window.__gone)")
        for name in SCENES:
            t = time.time()
            try:
                await setup(pg, name)
                await pg.screenshot(path=os.path.join(out, name + '.png'))
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
