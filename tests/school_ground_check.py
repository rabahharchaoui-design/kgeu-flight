# School1 item 6: ground reference (the rectangle, S turns across the road, turns around a point), the plane moved along
# a drawn path frame by frame at 800 ft AGL and 100 kt. (a) the marks in the world: four corner pylons, the box, the road,
# the point's pylon and ring, gone after the lesson; the site flat (under 6 m across 1.5 km) southwest of the field.
# (b) flown well: the four corners in order, four even lobes of 300 m, one circle of 300 m: every phase reached, Dana's
# line for each, the alt and spd holds graded, the debrief all passed. (c) flown badly: the box cut through (inside over
# 5 s) fails rect; uneven S turns fail sturn. (d) no page errors. Run: .venv/bin/python tests/school_ground_check.py
import asyncio, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15
from school_fly import K, BASE, DEBRIEF, DANA, start, said
ok = Checks()
# move along pts (x, z) at most `step` metres a frame, pinned 800 ft above the ground at 100 kt, level
PATH = """([P,step])=>{const K=window.__kgeu;let n=0;
  for(let i=0;i<P.length-1&&K.LES.on;i++){const a=P[i],b=P[i+1],L=Math.hypot(b[0]-a[0],b[1]-a[1]),k=Math.max(1,Math.ceil(L/step)),h=Math.atan2(b[0]-a[0],-(b[1]-a[1]));
    for(let j=1;j<=k&&K.LES.on;j++){const s=K.state(),x=a[0]+(b[0]-a[0])*j/k,z=a[1]+(b[1]-a[1])*j/k;s.windKt=0;s.gustAmp=0;
      s.pos.set(x,K.groundHeight(x,z)+800/3.28084+1.3,z);const V=100/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225);
      s.vel.set(Math.sin(h)*V,0,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(0.04,-h,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;K.stepFrame(0.1,false,true);n++;}}
  K.stepFrame(0,true);return {n:n,ph:K.LES.ph,on:K.LES.on,d:{k:K.LES.d.k,n:K.LES.d.n,lb:K.LES.d.lb&&K.LES.d.lb.map(o=>Math.round(o.pk))}}}"""

def lap(g, cut=False):
    o = 275
    if cut:   # straight through the middle of the box
        return [[g['sx'], g['sz']], [g['cx'], g['z1'] - 50], [g['cx'], g['z0'] + 50], [g['cx'], g['z0'] - 600]]
    return [[g['sx'], g['sz']], [g['x0'] - o, g['z0'] - o], [g['x1'] + o, g['z0'] - o], [g['x1'] + o, g['z1'] + o], [g['x0'] - o, g['z1'] + o], [g['x0'] - 400, g['z1'] + o]]

def sturns(g, rw=300, re=300):
    rx, z = g['rx'], g['z1'] + 275
    P = [[rx + 400, z], [rx + 200, z]]
    for k in range(4):
        r = rw if k % 2 == 0 else re; side = -1 if k % 2 == 0 else 1   # west lobes first (we come from the east)
        cz = z - r
        for i in range(1, 19):
            t = math.pi * i / 18
            P.append([rx + side * r * math.sin(t), cz + r * math.cos(t)])
        z -= 2 * r
    P.append([rx + 150, z]); P.append([rx + 250, z])
    return P

def circle(g, r=300, wob=0):
    P = [[g['px'] + 900, g['pz'] + 900], [g['px'], g['pz'] + r]]
    for i in range(1, 80):
        t = 2 * math.pi * i / 72
        rr = r + wob * math.sin(3 * t)
        P.append([g['px'] + rr * math.sin(t), g['pz'] + rr * math.cos(t)])
    return P

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        await start(pg, 'ground')
        g = await pg.evaluate(f"()=>{K}.grSite()")
        m = await pg.evaluate(f"""(g)=>{{const K={K},s=K.state(),gh=K.groundHeight,O=K.lesObjs();let lo=1e9,hi=-1e9;for(let i=-3;i<=3;i++)for(let j=-3;j<=3;j++){{const h=gh(g.cx+i*250,g.cz+j*250);lo=Math.min(lo,h);hi=Math.max(hi,h);}}
          const py=O.filter(o=>o.type==='ConeGeometry');
          return {{flat:hi-lo,py:py.length,tri:Math.max(...py.map(o=>o.tri)),rib:O.filter(o=>o.type==='BufferGeometry').length,ring:O.filter(o=>o.type==='RingGeometry').length,all:O.every(o=>o.inScene),agl:Math.round(s.agl*3.28084),kt:Math.round(s.ias*1.943844),sw:g.cx<-2000&&g.cz>1000}}}}""", g)
        ok('(a) the site: flat (under 6 m across 1.5 km), southwest of the field', m['flat'] < 6 and m['sw'], m)
        ok('(a) five pylons (6 sides, at most 12 triangles), the box edges, its four rust corners, the road and the ring drawn', m['py'] == 5 and m['tri'] <= 12 and m['rib'] == 6 and m['ring'] == 1 and m['all'], m)
        ok('(a) the start: 800 ft AGL, 100 kt', abs(m['agl'] - 800) < 30 and abs(m['kt'] - 100) < 3, m)
        r = await pg.evaluate(PATH, [lap(g), 45])
        ok('(b) the rectangle: four corners in order, on to the S turns', r['ph'] == 1 and r['d']['k'] == 4, r)
        r = await pg.evaluate(PATH, [sturns(g), 40])
        ok('(b) the S turns: four lobes of about 300 m, on to the point', r['ph'] == 2 and len(r['d']['lb']) == 4 and all(250 < x < 330 for x in r['d']['lb']), r)
        r = await pg.evaluate(PATH, [circle(g), 40])
        ok('(b) the circle closes the lesson', r['on'] is None, r)
        await pg.wait_for_timeout(600)
        d = await pg.evaluate(DEBRIEF); dana = await pg.evaluate(DANA)
        miss = said(dana, 'Ground reference', 'S turns', 'turns around the point')
        ok('(b) Dana opens each phase', not miss, (miss, dana))
        ok('(b) the debrief: a row per task, all passed', d['on'] and [x[0] for x in d['rows']] == ['Altitude within 100 ft', 'Airspeed within 10 kt', 'Rectangular course flown', 'S turns even on both sides', 'Even radius around the point']
           and all(x[1] for x in d['rows']) and d['letter'] in 'AB', d)
        ok('(b) the holds ran through all three', await pg.evaluate(f"()=>{K}.G.tasks.alt.tAll>30&&{K}.G.tasks.spd.tAll>30"))
        n = await pg.evaluate(f"()=>{K}.lesObjs().length")
        ok('(a) the marks are cleared after the lesson', n == 0, n)
        # (c) badly: through the box, then lopsided S turns
        await start(pg, 'ground')
        r = await pg.evaluate(PATH, [lap(g, cut=True), 8])
        ok('(c) cutting through the box fails the rectangle and moves on', r['ph'] == 1 and await pg.evaluate(f"()=>{K}.G.tasks.rect.ok===false"), r)
        r = await pg.evaluate(PATH, [sturns(g, 300, 120), 40])
        st = await pg.evaluate(f"()=>{K}.G.tasks.sturn")
        ok('(c) lopsided S turns (300 m and 120 m lobes) fail sturn', r['ph'] == 2 and st and st['ok'] is False and 'uneven' in st['detail'], (r, st))
        r = await pg.evaluate(PATH, [circle(g, 300, 220), 40])
        await pg.wait_for_timeout(600)
        d = await pg.evaluate(DEBRIEF)
        pt = [x for x in d['rows'] if x[0] == 'Even radius around the point']
        ok('(c) a wobbling circle (220 m off) fails the point', pt and not pt[0][1], pt)
        ok('(d) no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_ground_check'))
asyncio.run(main())
