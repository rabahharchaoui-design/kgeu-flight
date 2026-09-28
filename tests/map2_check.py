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
        # the legend: every icon type, a tap lights them up and flies to the nearest
        await pg.evaluate(f"()=>{K}.fmOpen()")
        leg = await pg.evaluate("()=>[...document.querySelectorAll('#mapLegL .lrow')].map(b=>b.dataset.kind)")
        ok('legend lists every icon type', leg == ['airport', 'airbase', 'landmark', 'drop', 'range', 'race', 'school', 'egg'], leg)
        await finger(pg, '#mapLegL .lrow[data-kind="drop"]'); await pg.wait_for_timeout(2500)
        await pg.evaluate(f"()=>{K}.fmFlush()")
        r = await pg.evaluate(f"""()=>{{const L={K}.LBL(),d=L.placed.find(p=>p.kind==='drop'),W=innerWidth,H=innerHeight;
          return {{on:document.querySelector('#mapLegL .lrow[data-kind=drop]').classList.contains('on'),drop:d?[(d.box[0]+d.box[2])/2,(d.box[1]+d.box[3])/2]:null,W:W,H:H}}}}""")
        ok('tapping Airdrop highlights it and pans the airdrop icon on screen', r['on'] and r['drop'] and 0 < r['drop'][0] < r['W'] and 0 < r['drop'][1] < r['H'], r)
        await shot(pg, 'legend_drop')
        # waypoint on an icon: pin, route line, distance and time, the same route on the mini map, then clear
        await pg.evaluate(f"()=>{{{K}.FM.cx={K}.state().pos.x-4000;{K}.FM.cz={K}.state().pos.z+6000;{K}.FM.scale=0.02;{K}.fmFlush()}}")
        rng = await pg.evaluate(f"()=>{{const P={K}.LBL().placed.find(p=>p.kind==='range');return P&&[(P.box[0]+P.box[2])/2,(P.box[1]+P.box[3])/2]}}")
        if not rng:
            await pg.evaluate(f"()=>{{{K}.FM.cx=-13400;{K}.FM.cz=14400;{K}.fmFlush()}}")
            rng = await pg.evaluate(f"()=>{{const P={K}.LBL().placed.find(p=>p.kind==='range');return P&&[(P.box[0]+P.box[2])/2,(P.box[1]+P.box[3])/2]}}")
        await pg.touchscreen.tap(rng[0], rng[1]); await pg.wait_for_timeout(400)
        dd = await pg.evaluate(f"()=>{K}.dest()")
        ok('tapping the strike range icon drops a waypoint there', dd and dd.get('name') == 'Strike range', dd)
        await pg.evaluate(f"()=>{K}.fmFlush()")
        info = await pg.evaluate("()=>document.getElementById('mapInfo').innerText")
        ok('route card shows the name, distance and time', 'Strike range' in info and 'nm' in info, info)
        pin = await pg.evaluate(f"()=>{K}.LBL().placed.some(p=>p.kind==='pin')")
        ok('the waypoint pin shows', pin)
        await shot(pg, 'route_full')
        await finger(pg, '#mapX'); await pg.wait_for_timeout(900)
        cyan = await pg.evaluate("""()=>{const c=document.getElementById('map'),x=c.getContext('2d'),d=x.getImageData(0,0,c.width,c.height).data;let n=0;
          for(let i=0;i<d.length;i+=4)if(d[i]<120&&d[i+1]>190&&d[i+2]>220)n++;return n}""")
        ok('the route line shows on the mini map', cyan > 20, cyan)
        await shot(pg, 'route_minimap')
        await finger(pg, '#map'); await pg.wait_for_timeout(500)
        await finger(pg, '#mapClear'); await pg.wait_for_timeout(300)
        ok('Clear removes the waypoint', await pg.evaluate(f"()=>{K}.dest()") is None and await pg.evaluate("()=>document.getElementById('mapClear').hidden"))
        # controls: double tap zooms in where you tap, recenter comes back to the aircraft
        await pg.evaluate(f"()=>{{{K}.FM.cx=0;{K}.FM.cz=20000;{K}.FM.scale=0.01;{K}.fmFlush()}}")
        s0 = await pg.evaluate(f"()=>{K}.FM.scale")
        await pg.touchscreen.tap(300, 200); await pg.wait_for_timeout(120); await pg.touchscreen.tap(300, 200); await pg.wait_for_timeout(1500)
        s1 = await pg.evaluate(f"()=>{K}.FM.scale")
        ok('double tap zooms in', s1 > s0 * 1.8, f'{s0:.4f} -> {s1:.4f}')
        await finger(pg, '#mapCtr'); await pg.wait_for_timeout(1500)
        c = await pg.evaluate(f"()=>{{const p={K}.fmP({K}.state().pos.x,{K}.state().pos.z);return p}}")
        ok('recenter brings the aircraft back on screen', 0 < c[0] < 844 and 0 < c[1] < 390, c)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        # a haboob day: the legend gains Haboob, its icon and dust show on both maps
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.wait_for_function(f"()=>{K}.MAPD.ready", timeout=20000)
        await pg.evaluate(f"()=>{{{K}.setTOD('haboob');{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('final')}}"); await pg.wait_for_timeout(1500)
        await pg.evaluate(f"()=>{K}.haboobJump(4000)"); await pg.wait_for_timeout(1200)
        await shot(pg, 'minimap_haboob')
        await finger(pg, '#map'); await pg.wait_for_timeout(400)
        leg = await pg.evaluate("()=>[...document.querySelectorAll('#mapLegL .lrow')].map(b=>b.dataset.kind)")
        ok('haboob day: the legend lists Haboob', 'haboob' in leg, leg)
        await finger(pg, '#mapLegL .lrow[data-kind="haboob"]'); await pg.wait_for_timeout(2000)
        await pg.evaluate(f"()=>{K}.fmFlush()")
        o = await pg.evaluate(OVL)
        ok('haboob icon shows, still no overlaps', 'haboob' in o['kinds'] and not o['bad'], o)
        await shot(pg, 'full_haboob')
        ok('no page errors (haboob)', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('map2_check'))
asyncio.run(main())
