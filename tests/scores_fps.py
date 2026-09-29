# Frame rate with the leaderboards in play, against the build before them (prescores), same
# session, alternating so machine drift cancels. The new build runs as a player with a
# callsign: it is painted on the aircraft, the fame boards are drawn from a cached fetch,
# the Worker is unreachable (offline, the queue path), and the race scenario flies a ghost
# beside the player (the base build flies the same challenge without one).
# Headless software GL runs at a few fps; only the ratio means anything.
#   .venv/bin/python tests/scores_fps.py <base_root> <new_root> [rounds]
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aircraft_fps import serve, fps, frame_ms, THREE, K, FLOOR

FAME = json.dumps({'day': 0, 'daily': {'cs': 'SIDEWINDER7'}, 'top': [{'cs': 'HABOOB'}, {'cs': 'SAGUARO'}, {'cs': 'MONSOON'}]})
PLAYER = json.dumps({'cs': 'SIDEWINDER7', 'key': 'f' * 48, 'xp': 1500, 'creator': False})

async def run(b, url, new):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    init = "localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');"
    if new:
        init += f"localStorage.setItem('kgeuLBUrl','http://127.0.0.1:9');localStorage.setItem('kgeuLB',{PLAYER!r});localStorage.setItem('kgeuFame',{FAME!r});"
    await ctx.add_init_script(init)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000); await pg.wait_for_timeout(3000)
    if new: await pg.evaluate(f"()=>{{const c=document.getElementById('csOv');if(c)c.classList.remove('on');}}")
    out = {}
    for t, pos in (('f16', 'runway'), ('cessna', 'runway'), ('c130', 'final'), ('reaper', 'final')):
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('{pos}')}}"); await pg.wait_for_timeout(2500)
        out[f'{t}_{pos}'] = await fps(pg)
        out[f'{t}_{pos}_ms'] = await frame_ms(pg)
    # the KGEU ramp facing the hangars (the Top Guns wall)
    await pg.evaluate(f"""()=>{{const K={K};K.pick('cessna');K.start('ramp');const s=K.state(),x0=K.wX(840,-330),z0=K.wZ(840,-330),x1=K.wX(840,-398),z1=K.wZ(840,-398),h=Math.atan2(x1-x0,-(z1-z0));
        s.pos.set(x0,K.groundHeight(x0,z0)+1.5,z0);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));K.snapCam();}}"""); await pg.wait_for_timeout(2500)
    out['hangars'] = await fps(pg)
    out['hangars_ms'] = await frame_ms(pg)
    # the 1 mile landing challenge; the new build races a ghost on a straight in path
    if new:
        await pg.evaluate(f"""()=>{{const K={K};K.pick('cessna');K.arcStart('landing1');const s=K.state(),n=300,f=new Float32Array(n*6),
            e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ'),v=s.vel.clone();for(let i=0;i<n;i++){{f.set([s.pos.x+v.x*i*0.2+12,s.pos.y+v.y*i*0.2,s.pos.z+v.z*i*0.2,e.y,e.x,e.z],i*6);}}
            K.LB.ghostStart('arc:landing1','HABOOB','cessna',false,{{n:n,f:f}});}}""")
    else:
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.arcStart('landing1')}}")
    await pg.wait_for_timeout(2500)
    out['race'] = await fps(pg)
    out['race_ms'] = await frame_ms(pg)
    if new: out['_ghost_visible'] = await pg.evaluate(f"()=>{K}.LB.E.ghost&&{K}.LB.E.ghost.m.g.visible?1:0")
    await ctx.close()
    return out, errs

async def main():
    base, new = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ub, un = serve(os.path.abspath(base)), serve(os.path.abspath(new))
    acc = {'base': [], 'new': []}; errs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        for r in range(rounds):
            for label, url in (('base', ub), ('new', un)) if r % 2 == 0 else (('new', un), ('base', ub)):
                o, e = await run(b, url, label == 'new'); acc[label].append(o); errs += [f'{label}: {x}' for x in e]
                print(label, json.dumps({k: round(v, 2) for k, v in o.items()}))
        await b.close()
    mean = lambda L, k: sum(x[k] for x in L) / len(L)
    fails = []
    ok_ghost = all(x.get('_ghost_visible') == 1 for x in acc['new'])
    print(f"  {'ok  ' if ok_ghost else 'FAIL'} the race scenario really flew a ghost in the new build")
    if not ok_ghost: fails.append('ghost')
    for k in acc['base'][0]:
        bb, nn = mean(acc['base'], k), mean(acc['new'], k)
        r = (bb / nn if nn else 1) if k.endswith('_ms') else (nn / bb if bb else 1)
        ok = r >= FLOOR
        print(f"  {'ok  ' if ok else 'FAIL'} {k}: base {bb:.2f} new {nn:.2f} ratio {r:.2f}")
        if not ok: fails.append(k)
    if errs:
        from collections import Counter
        print('page errors:', dict(Counter(errs)))
    print('scores_fps: ' + ('all passed' if not fails and not [e for e in errs if e.startswith('new')] else 'FAILED ' + ', '.join(fails)))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    asyncio.run(main())
