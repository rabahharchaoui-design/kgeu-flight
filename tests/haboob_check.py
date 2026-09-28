# Haboob (3.7): the fourth Time preset brings a dust wall in from the south-east at 18 m/s.
# Checks the wall spawns 4.5 km out with no dust, that dust, wind, gusts and fog build as
# the front is jumped closer, that the tower calls it once, that it clears on the far side
# of a jump back out, and that it never leaks into another preset (start with day, or
# switch away from haboob in the pause menu mid-flight).
# Also writes screenshots to overnight-screenshots/haboob/.
# Run: .venv/bin/python tests/haboob_check.py [--noshots]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'haboob')
K = 'window.__kgeu'
SHOT = '--noshots' not in sys.argv
# free camera from world coordinates: freeCam takes offsets in the aircraft frame
CAMW = """([p,t,fov])=>{const K=window.__kgeu,s=K.state(),qi=s.quat.clone().invert();
  const P=new THREE.Vector3(p[0],p[1],p[2]).sub(s.pos).applyQuaternion(qi),T=new THREE.Vector3(t[0],t[1],t[2]).sub(s.pos).applyQuaternion(qi);
  K.freeCam({p:P.toArray(),t:T.toArray(),fov:fov});}"""

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        ev = lambda js: pg.evaluate("()=>{" + js + "}")
        async def frames(n, render=False):
            await pg.evaluate("([n,r])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/60,false,!(r&&i==n-1));}", [n, render])
        async def hb(): return await pg.evaluate(f"()=>{K}.haboob()")
        async def jump(m, n=3):
            await ev(f"{K}.haboobJump({m})"); await frames(n)
            return await hb()
        async def shot(name):
            await frames(1, True)
            await pg.screenshot(path=f'{SHOTS}/{name}.png')
        async def camw(pw, tw, fov):
            await pg.evaluate(CAMW, [pw, tw, fov])
        await ev(f"{K}.setSkill('pilot')")
        await ev(f"{K}.setTOD('haboob');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')")
        await pg.wait_for_timeout(800); await frames(3)
        h = await hb()
        ok('haboob chip persisted', await pg.evaluate("()=>localStorage.getItem('kgeuTOD')") == 'haboob')
        ok('cessna at Glendale: wall on, front about 4.5 km out, no dust', h['on'] and h['wallVisible'] and 4200 < h['dist'] < 4600 and h['d'] == 0, h)
        # one wind: the tower's clearance, the HUD and the physics all read the ambient 8 kt out here
        await frames(60, True)
        w = await pg.evaluate("()=>[document.getElementById('atc').textContent,document.getElementById('hWindT').textContent,window.__kgeu.state().windKt]")
        ok('before the dust: tower, HUD and physics all say 8 kt', ' at 8,' in w[0] and w[1].endswith(' 8 KT') and w[2] == 8, w)
        h = await jump(800)
        ok('front 800 m out: dust building, wind over 20 kt', h['d'] > 0.3 and h['windKt'] > 20, h)
        h = await jump(-1000)
        ok('1 km inside: thick dust, fog near < 300, gusts > 0.9, tower called', h['d'] > 0.95 and h['fogNear'] < 300 and h['gustAmp'] > 0.9 and h['called'], h)
        ok('inside: wall handed to the fog, dim sun disc up, wind from the SE', not h['wallVisible'] and h['sunDisc'] and abs(((h['windDir'] - 150) + 180) % 360 - 180) < 2, h)
        rq = await pg.evaluate("()=>document.getElementById('atc').textContent")
        ok('tower line on the radio', 'Glendale Tower' in rq and 'blowing dust' in rq, rq)
        await frames(120)
        ok('turbulence: still flying the runway roll without errors', not pg.errs, pg.errs[:3])
        h = await jump(4000, 10)
        ok('front 4 km out again: dust gone', h['d'] == 0 and h['fogNear'] == 5000, h)
        # screenshots
        if SHOT:
            await ev(f"{K}.start('ramp')"); await frames(3)
            h = await jump(4000)
            s = await pg.evaluate(f"()=>{K}.state().pos.toArray()")
            C, T = h['C'], h['T']
            await camw([s[0], s[1] + 3, s[2]], [C[0] + T[0] * 1200, 500, C[1] + T[1] * 1200], 62)
            await shot('wall_from_ramp')
            await ev(f"{K}.freeCam(null)")
        # F-16 at Luke, 3000 ft, seen from the side
        await ev(f"{K}.pick('f16');{K}.pickBase('luke');{K}.start('runway')"); await frames(3)
        h = await hb()
        ok('F-16 at Luke in haboob: wall on', h['on'] and h['d'] == 0, h)
        if SHOT:
            C, T = h['C'], h['T']
            Lx, Lz = -T[1], T[0]            # the lateral axis (heading + 90)
            # the aircraft 4 km ahead of the front and 7 km off to one side, at 3000 ft
            px, pz = C[0] + T[0] * 5000 + Lx * 5500, C[1] + T[1] * 5000 + Lz * 5500
            await pg.evaluate("""([x,z])=>{const K=window.__kgeu,s=K.state();s.pos.set(x,K.groundHeight(x,z)+914,z);s.onGround=false;s.vel.set(0,0,0);K.snapCam();}""", [px, pz])
            await frames(2)
            s = await pg.evaluate(f"()=>{K}.state().pos.toArray()")
            await camw([s[0] + Lx * 40 - T[0] * 20, s[1] + 8, s[2] + Lz * 40 - T[1] * 20], [C[0] - Lx * 800 + T[0] * 400, s[1] + 250, C[1] - Lz * 800 + T[1] * 400], 62)
            await shot('wall_from_air')
            # 6000 ft, out past one end, looking back along the front
            px, pz = C[0] + T[0] * 5000 + Lx * 16000, C[1] + T[1] * 5000 + Lz * 16000
            await pg.evaluate("([x,z])=>{const K=window.__kgeu,s=K.state();s.pos.set(x,K.groundHeight(x,z)+1500,z);s.vel.set(0,0,0);K.snapCam();}", [px, pz])
            await frames(2)
            s = await pg.evaluate(f"()=>{K}.state().pos.toArray()")
            await camw([s[0], s[1] + 5, s[2]], [C[0] + Lx * 2000, s[1] - 300, C[1] + Lz * 2000], 62)
            await shot('wall_along_6000ft')
            await ev(f"{K}.freeCam(null)")
        # switching to day in the pause menu mid-flight removes the storm
        await ev(f"{K}.togglePause()")
        await ev("document.querySelector('#pauseOv .pick[data-tod=\"day\"]').click()")
        await ev(f"{K}.togglePause()"); await frames(3)
        h = await hb()
        ok('pause menu Day: wall gone, no dust, clear fog back', not h['on'] and not h['wallVisible'] and h['d'] == 0 and h['fogNear'] == 5000 and h['gustAmp'] == 0.35, h)
        await ev(f"{K}.start('runway')"); await frames(3)
        h = await hb()
        ok('F-16 at Luke in day: no wall, no dust', not h['on'] and not h['wallVisible'] and h['d'] == 0, h)
        # and switching to haboob mid-flight spawns it 4.5 km out
        await ev(f"{K}.togglePause()")
        await ev("document.querySelector('#pauseOv .pick[data-tod=\"haboob\"]').click()")
        await ev(f"{K}.togglePause()"); await frames(3)
        h = await hb()
        ok('pause menu Haboob mid-flight: wall 4.5 km out', h['on'] and 4200 < h['dist'] < 4600, h)
        # inside on the 3 mile final, chase view; then facing the sun
        await ev(f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')"); await frames(3)
        h = await jump(-1000, 30)
        ok('final inside the storm: thick dust', h['d'] > 0.95, h)
        if SHOT:
            await ev(f"{K}.snapCam()"); await frames(5)
            await shot('inside_final')
            await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),qi=s.quat.clone().invert();
              const d=new THREE.Vector3(-0.8,0.3,0.4).normalize().multiplyScalar(1000).applyQuaternion(qi);
              K.freeCam({p:[0,1.5,-3],t:d.toArray(),fov:60});}""")
            await shot('sun_disc')
            await ev(f"{K}.freeCam(null)")
        await ev(f"{K}.setTOD('day')"); await frames(2)
        h = await hb()
        ok('day again: storm off', not h['on'] and h['d'] == 0, h)
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('haboob_check')

sys.exit(asyncio.run(main()))
