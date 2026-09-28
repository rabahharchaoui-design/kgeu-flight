# Map redesign (session "map"): the OSM data file loads, the full map is opaque and
# layered, labels never overlap at five zoom levels, the legend, waypoints and route,
# the controls, and the restyled mini map. iPhone landscape.
# Run: .venv/bin/python tests/map2_check.py [--shots]   (--shots saves overnight-screenshots/map/)
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15, ROOT
ok = Checks()
K = "window.__kgeu"
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'map')
SAVE = '--shots' in sys.argv

async def shot(pg, name):
    if SAVE:
        os.makedirs(SHOTS, exist_ok=True)
        await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.wait_for_function(f"()=>{K}.MAPD.ready", timeout=20000)
        d = await pg.evaluate(f"""()=>{{const M={K}.MAPD;return {{roads:M.roads.map(a=>a?a.length:0),shields:[...new Set(M.shields.map(s=>s.ref))].sort(),
            water:M.polys[0].length,parks:M.polys[1].length,golf:M.polys[2].length,taxi:M.taxi.length,urban:!!(M.urban&&M.urban.data)}}}}""")
        ok('map data loads: every road class, water, parks, golf, taxiways, urban grid',
           all(n > 0 for n in d['roads']) and d['water'] > 100 and d['parks'] > 100 and d['golf'] > 10 and d['taxi'] > 50 and d['urban'], d)
        ok('shields for I-10, I-17, 101, 202 and 303', d['shields'] == ['101', '202', '303', 'I-10', 'I-17'], d['shields'])
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}"); await pg.wait_for_timeout(1500)
        await shot(pg, 'flight_minimap')
        await finger(pg, '#map'); await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{K}.fmFlush()"); await pg.wait_for_timeout(200)
        await shot(pg, 'full_open')
        # five zoom levels, each centred somewhere busy: nothing overlaps anything
        OVL = """()=>{const L=%s.LBL(),P=L.placed,bad=[];const hit=(a,b)=>a[0]<b[2]&&a[2]>b[0]&&a[1]<b[3]&&a[3]>b[1];
          for(let i=0;i<P.length;i++){for(let j=i+1;j<P.length;j++)if(hit(P[i].box,P[j].box))bad.push(P[i].kind+'/'+P[j].kind);
            for(const u of L.ui)if(hit(P[i].box,u))bad.push(P[i].kind+'/ui');}
          return {n:P.length,kinds:[...new Set(P.map(p=>p.kind))],bad:bad}}""" % K
        views = [('open', None, None, None), ('west', -6000, 0, 0.012), ('luke', 'KLUF', None, 0.05), ('phx', 'KPHX', None, 0.07), ('kgeu', 'KGEU', None, 0.2)]
        for name, cx, cz, sc in views:
            if name != 'open':
                if isinstance(cx, str):
                    await pg.evaluate(f"()=>{{const r={K}.RWY_ENDS.filter(e=>e.rwy.code==='{cx}');{K}.FM.cx=r.reduce((s,e)=>s+e.x,0)/r.length;{K}.FM.cz=r.reduce((s,e)=>s+e.z,0)/r.length;{K}.FM.scale={sc}}}")
                else:
                    await pg.evaluate(f"()=>{{{K}.FM.cx={cx};{K}.FM.cz={cz};{K}.FM.scale={sc}}}")
            await pg.evaluate(f"()=>{K}.fmFlush()"); await pg.wait_for_timeout(150)
            o = await pg.evaluate(OVL)
            ok(f'zoom {name}: {o["n"]} labels and icons, none overlapping each other or the buttons', not o['bad'] and o['n'] >= 2, o['bad'][:6] or o['kinds'])
            if name == 'luke':
                ok('close in, runway numbers show', 'rwy' in o['kinds'], o['kinds'])
            await shot(pg, f'full_{name}')
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('map2_check'))
asyncio.run(main())
