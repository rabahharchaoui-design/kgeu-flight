# Fix2 item 10: aircraft exterior lights in their real places, never inside a propeller disc, small halos.
# Tables (all 13 AC_LIGHTS tables through __kgeu.acLightTable, the 11 flyable types plus the AI airliner and
# helicopter): red on x<0 and green on x>0 at the same |x| (within 0.05), the white aft light (tail:1) the rearmost
# light or at a wingtip trailing edge (|x| at least 95 percent of the half span, aft of the nav light), the MQ-9A's
# and MQ-9B's strobes within 0.01 of the nav lights, the MQ-9s' white aft light on the ventral fin's tip trailing
# edge (below the fuselage, clear of the prop disc by the hub radius plus 0.3 m), no light (glow included) inside any
# prop / fan / rotor disc (__kgeu.propDiscs: centre, radius and axis read from the built models, 0.4 m thick).
# Strobe size: at distance its point is at most 1.3x the nav light's (__kgeu.aclSize, the numbers the shader uses).
# Halo: chase view from behind at night (tests/fix2_lights_shots.py placement), light clock frozen between flashes;
# the frame with the aircraft lights hidden is subtracted, the brightest blob near the projected aft light found
# and its radius above half max (sqrt(area/pi), device px at 844x390 2x) must be under 10 px: MQ-9B, F-16, 737.
# Usage: .venv/bin/python tests/lights_check.py [--no-halo]
import asyncio, io, math, sys
from PIL import Image
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

TYPES = ['cessna', 'archer', 'alpha', 'f16', 'a10', 'b737', 'a320', 'b747', 'c130', 'reaper', 'mq9b', 'airliner', 'heli']
FLY = TYPES[:11]
SPAN = {'cessna': 5.5, 'archer': 5.34, 'alpha': 5.25, 'f16': 4.99, 'a10': 8.77, 'b737': 18.02, 'a320': 18.3, 'b747': 32.23,
        'c130': 20.2, 'reaper': 10.06, 'mq9b': 12.56}
DPR = 2

SETUP_CLIMB = """([kt,alt,pitchDeg])=>{const K=window.__kgeu,s=K.state();
  const V=kt/1.94384/Math.sqrt(1.097*Math.exp(-alt/9200)/1.225),pr=pitchDeg*Math.PI/180;
  s.pos.y=alt+K.groundHeight(s.pos.x,s.pos.z);s.quat.setFromEuler(new THREE.Euler(pr,0,0,'YXZ'));
  s.vel.set(0,V*Math.sin(pr),-V*Math.cos(pr));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.85;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60);return true;}"""


def in_disc(l, d):
    a = d['axis']
    dx, dy, dz = l['x'] - d['x'], l['y'] - d['y'], l['z'] - d['z']
    ax = dx * a[0] + dy * a[1] + dz * a[2]
    rad = math.sqrt(max(0.0, dx * dx + dy * dy + dz * dz - ax * ax))
    return abs(ax) <= 0.2 and rad <= d['r'], ax, rad


def halo(on, off, x, y, win=14, reach=40):
    # light added per device pixel: summed channel increase, lights shown minus hidden
    X, Y = round(x * DPR), round(y * DPR)
    W, H = on.size
    A, B = on.load(), off.load()

    def d(i, j):
        p, q = A[i, j], B[i, j]
        return max(0, p[0] - q[0]) + max(0, p[1] - q[1]) + max(0, p[2] - q[2])
    best, bx, by = 0, X, Y
    for i in range(max(0, X - win), min(W, X + win + 1)):
        for j in range(max(0, Y - win), min(H, Y + win + 1)):
            v = d(i, j)
            if v > best:
                best, bx, by = v, i, j
    if best <= 0:
        return 0, 0.0, (bx, by)
    n = sum(1 for i in range(max(0, bx - reach), min(W, bx + reach + 1)) for j in range(max(0, by - reach), min(H, by + reach + 1))
            if d(i, j) >= best / 2)
    return best, math.sqrt(n / math.pi), (bx, by)


async def main():
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        c('hooks', await pg.evaluate("()=>['acLightTable','propDiscs','aclSize'].every(h=>typeof window.__kgeu[h]==='function')"))
        for t in TYPES:
            L = await pg.evaluate("(t)=>window.__kgeu.acLightTable(t)", t)
            D = await pg.evaluate("(t)=>window.__kgeu.propDiscs(t)", t)
            RED, GREEN = 0xff2a1e, 0x38ff78
            navs = [l for l in L if l['kind'] == 'nav' and not l.get('tail') and l['color'] in (RED, GREEN)]
            reds = [l for l in navs if l['color'] == RED]
            greens = [l for l in navs if l['color'] == GREEN]
            c(f'{t}: red nav on the left, green on the right, mirrored',
              len(reds) == 1 and len(greens) == 1 and reds[0]['x'] < 0 < greens[0]['x'] and abs(abs(reds[0]['x']) - greens[0]['x']) <= 0.05,
              [(l['x'], l['color']) for l in navs])
            tails = [l for l in L if l.get('tail')]
            zmax = max(l['z'] for l in L)
            span = SPAN.get(t, max(abs(l['x']) for l in L))
            nz = greens[0]['z'] if greens else 0

            def aft_ok(l):
                return l['z'] >= zmax - 1e-6 or (abs(l['x']) >= 0.95 * span and l['z'] > nz)
            c(f'{t}: white aft light rearmost or at a wingtip trailing edge', tails and all(aft_ok(l) for l in tails),
              [(l['x'], l['y'], l['z']) for l in tails])
            if t in ('reaper', 'mq9b'):
                st = [l for l in L if l['kind'] == 'strobe']
                c(f'{t}: strobes on the nav lights (within 0.01)', len(st) == 2 and all(
                    any(abs(s['x'] - n['x']) <= 0.01 and abs(s['y'] - n['y']) <= 0.01 and abs(s['z'] - n['z']) <= 0.01 for n in navs) for s in st),
                  [(s['x'], s['y'], s['z']) for s in st])
                fin = await pg.evaluate("""([t,pz])=>{const m=window.__kgeu.acModel(t),g=m.g,v=new THREE.Vector3(),inv=new THREE.Matrix4();g.updateMatrixWorld(true);
                  inv.copy(g.matrixWorld).invert();let best=null;
                  g.traverse(o=>{if(!o.isMesh||!o.geometry.attributes.position)return;const a=o.geometry.attributes.position;
                    for(let i=0;i<a.count;i++){v.fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld).applyMatrix4(inv);
                      if(Math.abs(v.x)<0.08&&v.z>3&&v.z<pz&&v.y<-0.6&&(!best||v.y<best[1]-0.005||(Math.abs(v.y-best[1])<=0.005&&v.z>best[2])))best=v.toArray();}});
                  return best;}""", [t, D[0]['z'] - 0.25])   # ahead of the prop (its blades reach as low)
                tl = tails[0]
                d0 = D[0]
                gap = d0['z'] - 0.2 - tl['z']
                c(f'{t}: white aft light on the ventral fin tip trailing edge', fin and abs(tl['y'] - fin[1]) <= 0.05 and 0 <= tl['z'] - fin[2] <= 0.05,
                  ((tl['x'], tl['y'], tl['z']), fin and [round(v, 3) for v in fin]))
                c(f'{t}: white aft light clear of the prop disc by the hub radius plus 0.3 m', gap >= 0.135 + 0.3 and tl['y'] < 0,
                  round(gap, 2))
            bad = []
            for l in L:
                for d in D:
                    ins, ax, rad = in_disc(l, d)
                    if ins:
                        bad.append((l['kind'], l['x'], l['y'], l['z'], round(ax, 2), round(rad, 2)))
            c(f'{t}: no light inside a prop / rotor disc ({len(D)} discs)', not bad, bad)
        S = await pg.evaluate("()=>window.__kgeu.aclSize()")
        far_nav = S['softMin'] * S['nav']
        far_strobe = S['hardMin'] * S['strobe'] * S['flash']
        near_nav = S['softMax'] * S['nav']
        near_strobe = S['hardMax'] * S['strobe'] * S['flash']
        c('strobe point at most 1.3x the nav light (far and near)', far_strobe <= 1.3 * far_nav and near_strobe <= 1.3 * near_nav,
          (far_strobe, far_nav, near_strobe, near_nav))

        if '--no-halo' not in sys.argv:
            async def frame(hide=False):
                await pg.evaluate("(h)=>{const K=window.__kgeu;K.plane().lights.pts.visible=!h;K.stepFrame(0);}", hide)
                return Image.open(io.BytesIO(await pg.screenshot(timeout=120000))).convert('RGB')
            for t in ['mq9b', 'f16', 'b737']:
                await pg.evaluate("(t)=>{const K=window.__kgeu;K.setTOD('night');K.pick(t);K.pickBase('luke');K.start('runway');}", t)
                await pg.wait_for_timeout(300)
                await pg.evaluate("()=>{let k=0;while(window.__kgeu.camMode()!==0&&k++<5)window.__kgeu.cycleCam();}")
                await pg.evaluate(SETUP_CLIMB, [150, 600, 15])
                await pg.evaluate("()=>{for(let i=0;i<24;i++)window.__kgeu.stepFrame(1/60);window.__kgeu.lightClock(0.6);}")
                on = await frame()
                off = await frame(hide=True)
                await pg.evaluate("()=>{window.__kgeu.plane().lights.pts.visible=true;}")
                scr = await pg.evaluate("()=>window.__kgeu.acLightScreen()")
                tl = [l for l in scr if l['kind'] == 'tail' and l['front']]
                tl.sort(key=lambda l: -l['lx'])   # the right one first where there are two (737 wingtips)
                if not tl:
                    c(f'{t} night chase: aft light on screen', False)
                    continue
                pk, r, at = halo(on, off, tl[0]['x'], tl[0]['y'])
                c(f'{t} night chase: aft light halo radius above half max under 10 px', pk > 60 and r < 10,
                  f'peak {pk} radius {r:.1f} px at {at}')
            await pg.evaluate("()=>{const K=window.__kgeu;K.lightClock(null);}")
        c('no page errors', not pg.errs, pg.errs[:5])
        await b.close()
    srv.shutdown()
    return c.done('lights_check')


sys.exit(asyncio.run(main()))
