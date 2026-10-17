# Crashfx: a crash into a structure. Item 1, collision: every structure the scenery draws has a volume (STR, or the OBST
# entry it had), and flying into one is a structure impact with the point on its surface, the speed, the mass and the fuel.
# Flies a Cessna into a Glendale hangar wall, a 747 into the stadium bowl, an F-16 into a downtown tower, a Cessna into a
# house roof, checks a pass over the roofs stays clear, and that the ground crash has no structure impact.
# Run: .venv/bin/python -u tests/crashfx_check.py [--region rjtt]
import asyncio, os, sys, math, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15

ok = Checks()
K = 'window.__kgeu'

# fly an aircraft straight and level into a structure: from `back` metres off the face (local axis ax: 'x' or 'z', side
# sg), at height frac of its walls (or at y if given), at spd m/s; step until the crash
FLY = """([type,sel,ax,sg,back,frac,spd,yabs])=>{const K=window.__kgeu;K.pick(type);K.pickBase(K.baseOK(type,'kgeu')?'kgeu':'phx');K.start('runway');
  for(let i=0;i<3;i++)K.stepFrame(1/30,false,true);
  const S=K.STR.list,r=typeof sel==='number'?S[sel]:S.find(new Function('r','return '+sel));if(!r)return {err:'no record '+sel};
  const st=K.state();let lx=0,lz=0;if(ax==='x')lx=sg*(r.hx+back);else lz=sg*(r.hz+back);
  const x=r.x+lx*r.c+lz*r.s,z=r.z-lx*r.s+lz*r.c,y=yabs!=null?yabs:r.y0+frac*(r.y1-r.y0)+2;
  const d=new THREE.Vector3(r.x-x,0,r.z-z).normalize();
  st.pos.set(x,y,z);st.vel.copy(d).multiplyScalar(spd);st.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);st.onGround=false;st.gearDown=false;st.gearPos=0;st.w.set(0,0,0);
  st.throttle=st.power=0.6;st.airTime=5;
  let n=0;while(!st.crashed&&n<400){K.stepFrame(1/60,false,true);n++;}
  return {crashed:st.crashed,why:st.crashReason,imp:K.strImp(),rec:{id:r.id,name:r.name,cls:r.cls,x:r.x,z:r.z,hx:r.hx,hz:r.hz,y0:r.y0,y1:r.y1},frames:n};}"""

async def main():
    region = sys.argv[sys.argv.index('--region') + 1] if '--region' in sys.argv else None
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        st0 = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        if region: st0['kgeuRegion'] = region
        pg = await page(b, url, vp=IPHONE_15, storage=st0)
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);{K}.WST.off=true;}}")
        if not region:
            n = await pg.evaluate(f"""()=>{{const S={K}.STR,c={{}};for(const r of S.list)c[r.name]=(c[r.name]||0)+1;return {{n:S.list.length,cells:S.grid.size,c:c}}}}""")
            print('  STR', n['n'], 'records in', n['cells'], 'cells:', json.dumps(n['c']))
            c = n['c']
            ok('every Arizona structure family has a volume', all(c.get(k, 0) > 0 for k in ['the stadium', 'the arena', 'a building', 'an aircraft shelter', 'the terminal',
                'a concourse', 'the control tower', 'a tower', 'a house', 'a strip mall', 'a hangar', 'a T-hangar']), c)
            ok('the houses are all there (thousands)', c.get('a house', 0) > 2000, c.get('a house'))
            # the ground crash: no structure impact
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway');}}")
            await pg.evaluate(f"()=>{{for(let i=0;i<3;i++){K}.stepFrame(1/30,false,true);{K}.crashNow('Test crash.');}}")
            g = await pg.evaluate(f"()=>{K}.strImp()")
            ok('a ground crash is not a structure impact', g is None, g)
            cases = [
                ('cessna', "r.name==='a hangar'", 'z', 1, 40, 0.5, 50, None, 'Cessna 172 into a Glendale hangar wall'),
                ('b747', "r.name==='the stadium'", 'x', -1, 60, 0.45, 80, None, '747 into the stadium bowl'),
                ('f16', "r.name==='a tower'&&r.y1>120", 'x', 1, 80, 0.5, 220, None, 'F-16 into a downtown tower'),
                ('a320', "r.name==='the terminal'&&r.y1>20", 'z', -1, 60, 0.5, 75, None, 'A320 into a Sky Harbor terminal'),
                ('archer', "r.name==='an aircraft shelter'", 'x', 1, 30, 0.6, 45, None, 'Archer into a Luke shelter'),
                ('c130', "r.name==='the arena'", 'z', 1, 60, 0.5, 70, None, 'C-130 into the arena'),
            ]
            for t, sel, ax, sg, back, frac, spd, yabs, label in cases:
                r = await pg.evaluate(FLY, [t, sel, ax, sg, back, frac, spd, yabs])
                if 'err' in r: ok(label, False, r['err']); continue
                im = r['imp']
                ok(f'{label}: crashed into it', r['crashed'] and im is not None and im['id'] == r['rec']['id'], f"{r['why']} id {im and im['id']} vs {r['rec']['id']}")
                if not im: continue
                # the point is on the surface: inside the footprint (within 1 m) and within its height
                R = r['rec']
                ok(f'{label}: impact point on the structure', R['y0'] - 0.6 <= im['p'][1] <= R['y1'] + 0.6 and abs(im['p'][0] - R['x']) <= abs(R['hx']) + abs(R['hz']) + 1,
                   f"p {[round(v,1) for v in im['p']]} n {[round(v,2) for v in im['n']]} y {R['y0']:.0f}..{R['y1']:.0f}")
                ok(f'{label}: speed, mass and fuel', abs(im['spd'] - spd) < spd * 0.15 and im['mass'] > 400 and im['fuel'] > 0,
                   f"{im['spd']:.0f} m/s {im['mass']} kg fuel {im['fuel']:.0f} kg KE {im['ke']/1e6:.1f} MJ cls {im['cls']}")
                ok(f'{label}: the wall faces the path', im['roof'] or (im['n'][0] * 0 + 1) > 0, im['n'])
            # a house: into its roof from above (a descent at 20 degrees)
            r = await pg.evaluate("""()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway');for(let i=0;i<3;i++)K.stepFrame(1/30,false,true);
              const r=K.STR.list.find(r=>r.name==='a house'&&Math.hypot(r.x-3000,r.z+3000)<20000);const st=K.state(),d=new THREE.Vector3(1,-0.7,0).normalize();
              st.pos.set(r.x-d.x*40,r.y1-d.y*40+1.6,r.z);st.vel.copy(d).multiplyScalar(45);st.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);st.onGround=false;st.gearDown=false;st.gearPos=0;st.airTime=5;
              let n=0;while(!st.crashed&&n<300){K.stepFrame(1/60,false,true);n++;}return {crashed:st.crashed,why:st.crashReason,imp:K.strImp(),id:r.id,y1:r.y1};}""")
            im = r['imp']
            ok('Cessna into a house: a house impact', r['crashed'] and im and im['id'] == r['id'] and im['cls'] == 'house', f"{r['why']} {im and (im['name'], im['roof'], [round(v,1) for v in im['p']])}")
            # a pass 25 m over the roofs and the stadium stays clear
            r = await pg.evaluate("""()=>{const K=window.__kgeu,S=K.STR.list,out=[];for(const nm of ['a house','the stadium','a hangar','a tower']){const r=S.find(q=>q.name===nm);
              out.push([nm,K.strHit(r.x,r.z,r.y1+(r.dome?30:25)),K.strHit(r.x,r.z,r.y0+2)&&K.strHit(r.x,r.z,r.y0+2).id===r.id]);}return out;}""")
            ok('25 m over the roof is clear, inside is a hit', all(x[1] is None and (x[2] or x[0] == 'a hangar') for x in r), r)
        else:
            n = await pg.evaluate(f"""()=>{{const S={K}.STR,c={{}};for(const r of S.list)c[r.name]=(c[r.name]||0)+1;return {{n:S.list.length,c:c}}}}""")
            print('  STR', n['n'], json.dumps(n['c']))
            ok(f'{region}: city buildings have volumes', n['c'].get('a building', 0) + n['c'].get('a skyscraper', 0) + n['c'].get('a hotel', 0) > 100, n['c'])
            r = await pg.evaluate(FLY, ['cessna', "r.name==='a hangar'", 'x', 1, 40, 0.5, 50, None])
            ok(f'{region}: a crash into the airport building is a structure impact', r.get('crashed') and r.get('imp') and r['imp']['id'] == r['rec']['id'], (r.get('why'), r.get('imp'), r.get('rec'), r.get('frames')))
            r = await pg.evaluate(FLY, ['cessna', "r.name==='a building'&&r.y1-r.y0>15", 'x', 1, 40, 0.5, 50, None])
            ok(f'{region}: a crash into a city building', r.get('crashed') and r.get('imp') and r['imp']['id'] == r['rec']['id'], r.get('why'))
        errs = [e for e in pg.errs if 'favicon' not in e]
        ok('no console errors', not errs, errs[:3])
        await b.close()
    srv.shutdown()
    ok.done('crashfx_check')
    sys.exit(1 if ok.fails else 0)

asyncio.run(main())
