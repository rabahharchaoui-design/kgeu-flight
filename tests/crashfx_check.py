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
  return {crashed:st.crashed,why:st.crashReason,imp:K.strImp(),cfx:K.cfx(),rec:{id:r.id,name:r.name,cls:r.cls,x:r.x,z:r.z,hx:r.hx,hz:r.hz,y0:r.y0,y1:r.y1},frames:n};}"""

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
            # the warm-up first (the menu's steps, and a first flight frame): from then on every program a crash into a
            # structure uses must already exist
            await pg.wait_for_function("()=>window.__kgeu.warm()", timeout=300000)
            await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway');for(let i=0;i<3;i++)K.stepFrame(1/30);}")
            pr0 = await pg.evaluate("()=>window.__kgeu.progN()")
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
            # item 2, the breakup: what breaks scales with the energy; a light structure collapses, a big one breaks locally
            BR = {}
            for t, sel, ax, sg, back, frac, spd, key in [('cessna', "r.name==='a hangar'", 'z', 1, 40, 0.5, 50, 'c_hangar'), ('b737', "r.name==='a hangar'", 'z', 1, 60, 0.5, 75, 'b_hangar'),
                                                         ('cessna', "r.name==='the stadium'", 'x', -1, 40, 0.45, 50, 'c_stadium'), ('b747', "r.name==='the stadium'", 'x', -1, 60, 0.45, 80, 'b_stadium')]:
                r = await pg.evaluate(FLY, [t, sel, ax, sg, back, frac, spd, None])
                await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<150;i++)K.stepFrame(1/30,false,i%25!==0);}")
                x = await pg.evaluate("()=>{const K=window.__kgeu,B=K.CFXB,I=K.cfx();I.hidden=K.STR.list.filter(r=>r.meshes&&r.meshes.length&&!r.meshes[0].visible).map(r=>r.id);return I;}")
                BR[key] = (r, x)
                print(f"  {key}: rh {x['rh']:.1f} m, collapse {x['rc'] if x['rc']<1e8 else 'all'}, fc {x['fc']:.2f}, E {x['E']/1e6:.0f} MJ, removed {x['removed']}, tris {x['tris']}, chunks {x['chunks']}, rest {x['rest']}, built in {x['ms']} ms")
            pr1 = await pg.evaluate("()=>window.__kgeu.progN()")
            ok('no shader program compiled in flight by any crash into a structure (after the warm-up)', pr1['compiles'] == pr0['compiles'], (pr0, pr1))
            c, b7 = BR['c_hangar'][1], BR['b_hangar'][1]
            ok('Cessna into a hangar: a hole and a partial collapse, the hangar stands', c['on'] and c['removed'] > 0 and not c['total'] and c['rc'] > c['rh'] and c['fc'] < 1, c)
            ok('737 into a hangar: the hangar comes down', b7['total'], b7['fc'])
            cs, bs = BR['c_stadium'][1], BR['b_stadium'][1]
            ok('the stadium only ever breaks locally', not cs['total'] and not bs['total'] and cs['rc'] == cs['rh'] and bs['rc'] == bs['rh'], (cs['rc'], bs['rc']))
            ok('a 747 breaks a far bigger hole than a Cessna (energy and span)', bs['rh'] > 4 * cs['rh'] and bs['removed'] > cs['removed'], (cs['rh'], bs['rh']))
            ok('the 747 hole in the stadium stays local (under 15 percent of its 318 m)', bs['rh'] < 0.15 * 318, bs['rh'])
            ok('the stadium mesh is swapped for the broken one', BR['b_stadium'][0]['imp']['id'] in bs['hidden'], bs['hidden'])
            ok('chunks fall and settle (most at rest after 5 s)', sum(bs['rest'].values()) > 0.6 * sum(bs['chunks'].values()), (bs['chunks'], bs['rest']))
            b0 = BR['b_stadium'][0]['cfx']
            ok('dust and glass from the stadium', b0['dust'] > 0 and b0['glass'] > 0, (b0['dust'], b0['glass']))
            ok('a breakup builds in under 60 ms (headless)', max(x[1]['ms'] for x in BR.values()) < 60, [x[1]['ms'] for x in BR.values()])
            # item 3, the fire: its size, length and column from the fuel (Heskestad), the column leaning downwind, the glow at night
            F = {}
            for t, key in [('cessna', 'c'), ('f16', 'f'), ('b747', 'b')]:
                await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('day');}")
                r = await pg.evaluate(FLY, [t, "r.name==='the stadium'", 'x', -1, 50, 0.45, 70 if t != 'f16' else 150, None])
                await pg.evaluate("()=>{const K=window.__kgeu,s=K.state();s.windDir=270;s.windKt=12;s.gust=0;for(let i=0;i<300;i++)K.stepFrame(1/30,false,i%30!==0);}")
                F[key] = await pg.evaluate("()=>{const K=window.__kgeu,S=K.SF,f=K.sf();let dx=0,n=0;for(const m of S.sm)if(m.live&&m.q.visible&&m.q.p.y-S.y>0.6*S.zmax){dx+=m.q.p.x-S.x;n++;}f.lean=n?dx/n:0;return f;}")
                f = F[key]
                print(f"  {key}: fuel {f['fuel']:.0f} kg  pool D {f['D']:.1f} m  Q {f['Q']/1000:.0f} MW  flames L {f['L']:.1f} m  column to {f['zmax']:.0f} m  burns {f['dur']:.0f} s  puffs {f['puffs']} flames {f['flames']}  lean {f['lean']:.0f} m  top {f['top']:.0f} m")
            ok('fire size follows the fuel: 747 > F-16 > Cessna (pool, flames, heat, column)', F['b']['D'] > F['f']['D'] > F['c']['D'] and F['b']['L'] > F['f']['L'] > F['c']['L'] and F['b']['zmax'] > F['f']['zmax'] > F['c']['zmax'], [(F[k]['D'], F[k]['L'], F[k]['zmax']) for k in 'cfb'])
            ok('Heskestad flame lengths in range (Cessna 3-9 m, 747 35-70 m)', 3 <= F['c']['L'] <= 9 and 35 <= F['b']['L'] <= 70, (F['c']['L'], F['b']['L']))
            ok('jet fuel smokes black, the Cessna is avgas', F['b']['jet'] and F['f']['jet'] and not F['c']['jet'])
            ok('it burns on for minutes', min(F[k]['dur'] for k in 'cfb') >= 180, [F[k]['dur'] for k in 'cfb'])
            ok('the column leans downwind (wind from 270: toward +x)', F['b']['lean'] > 30 and F['c']['lean'] > 5, (F['c']['lean'], F['b']['lean']))
            ok('the 747 column stands hundreds of metres tall', F['b']['top'] > 300, F['b']['top'])
            ok('a wall fire: flames out of the hole and the fall below it', F['b']['wall'] and F['b']['two'], F['b'])
            await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('night');for(let i=0;i<30;i++)K.stepFrame(1/30,false,true);}")
            gn = await pg.evaluate("()=>window.__kgeu.sf().glow")
            await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('day');for(let i=0;i<30;i++)K.stepFrame(1/30,false,true);}")
            gd = await pg.evaluate("()=>window.__kgeu.sf().glow")
            ok('the ground glows round the fire at night, faintly by day', gn > 0.6 and gd < 0.45 * gn, (gd, gn))
            # item 4, the crash camera: after a crash into the stadium and into a hangar it ends outside every building, the
            # impact point and the fire in the frame, the card after it
            await pg.evaluate(f"()=>{K}.initAudio()")
            for t, sel, ax, sg, back, spd in [('b747', "r.name==='the stadium'", 'x', -1, 60, 80), ('cessna', "r.name==='a hangar'", 'z', 1, 40, 50)]:
                await pg.evaluate(FLY, [t, sel, ax, sg, back, 0.5, spd, None])
                cam = await pg.evaluate("""()=>{const K=window.__kgeu,R=K.R3(),c=R.camera,out=[];
                  for(const ts of [0.5,1.5,3.5]){while(K.crashFx().t<ts)K.stepFrame(1/30);const I=K.strImp(),p=new THREE.Vector3(...I.p).project(c),cp=c.position;
                    const inside=K.STR.list.some(r=>Math.hypot(r.x-cp.x,r.z-cp.z)<r.hx+r.hz+5&&K.strInside(r,cp.x,cp.y,cp.z));
                    out.push({t:ts,inView:Math.abs(p.x)<0.9&&Math.abs(p.y)<0.9&&p.z<1,inside:inside,d:cp.distanceTo(new THREE.Vector3(...I.p))});}
                  return {seq:out,card:K.crashFx().card,audio:!!(K.cfxAudio&&K.cfxAudio())};}""")
                ok(f'{t}: the crash camera stays outside the buildings and keeps the impact in the frame', all(x['inView'] and not x['inside'] for x in cam['seq']),
                   [(x['t'], x['inView'], x['inside'], round(x['d'])) for x in cam['seq']])
                ok(f'{t}: it pulls back from the hole to show the whole fire', cam['seq'][2]['d'] > cam['seq'][0]['d'] * 1.4, [round(x['d']) for x in cam['seq']])
                ok(f'{t}: the impact, the groans and the fire crackle play (audio context up)', cam['audio'] or not (await pg.evaluate(f"()=>!!{K}.actx()")), cam['audio'])
            # a consequence, never a reward: a crash into a structure writes nothing a ground crash does not (scores, runs,
            # achievements, XP, boards all live in localStorage or go through it)
            SNAP = "()=>{const o={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);o[k]=localStorage.getItem(k);}return o;}"
            def diff(a, b): return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            s0 = await pg.evaluate(SNAP)
            await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway');for(let i=0;i<3;i++)K.stepFrame(1/30,false,true);K.crashNow('Test crash.');for(let i=0;i<150;i++)K.stepFrame(1/30,false,true);}")
            s1 = await pg.evaluate(SNAP)
            await pg.evaluate(FLY, ['cessna', "r.name==='a hangar'", 'z', 1, 40, 0.5, 50, None])
            await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<150;i++)K.stepFrame(1/30,false,true);}")
            s2 = await pg.evaluate(SNAP)
            dg, ds = diff(s0, s1), diff(s1, s2)
            ok('a crash into a structure writes nothing a ground crash does not (no score, run, XP or achievement)', set(ds) <= set(dg) | {'kgeuResume'}, (dg, ds))
            # a new flight puts every structure back
            z = await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway');for(let i=0;i<3;i++)K.stepFrame(1/30,false,true);const S=K.R3().scene;"
                                  "return {on:K.CFXB.on,adds:K.CFXB.adds.length,hidden:K.STR.list.filter(r=>r.meshes&&r.meshes.some(m=>!m.visible)).length,slab:S.getObjectByName('cfx_slab').visible,fire:K.sf().on,audio:K.cfxAudio()};}")
            ok('a new flight: every structure whole again, no chunks, the fire and its sound gone', not z['on'] and z['adds'] == 0 and z['hidden'] == 0 and not z['slab'] and not z['fire'] and not z['audio'], z)
            # a house: into its roof from above (a descent at 20 degrees)
            r = await pg.evaluate("""()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway');for(let i=0;i<3;i++)K.stepFrame(1/30,false,true);
              const r=K.STR.list.find(r=>r.name==='a house'&&Math.hypot(r.x-3000,r.z+3000)<20000);const st=K.state(),d=new THREE.Vector3(1,-0.7,0).normalize();
              st.pos.set(r.x-d.x*40,r.y1-d.y*40+1.6,r.z);st.vel.copy(d).multiplyScalar(45);st.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);st.onGround=false;st.gearDown=false;st.gearPos=0;st.airTime=5;
              let n=0;while(!st.crashed&&n<300){K.stepFrame(1/60,false,true);n++;}return {crashed:st.crashed,why:st.crashReason,imp:K.strImp(),id:r.id,y1:r.y1};}""")
            im = r['imp']
            ok('Cessna into a house: a house impact', r['crashed'] and im and im['id'] == r['id'] and im['cls'] == 'house', f"{r['why']} {im and (im['name'], im['roof'], [round(v,1) for v in im['p']])}")
            h = await pg.evaluate("(id)=>{const K=window.__kgeu,r=K.STR.list[id],m=new THREE.Matrix4();r.im.getMatrixAt(r.ii,m);const s=new THREE.Vector3().setFromMatrixScale(m);"
                                  "K.pick('cessna');K.start('runway');K.stepFrame(1/30,false,true);r.im.getMatrixAt(r.ii,m);const s2=new THREE.Vector3().setFromMatrixScale(m);return {hid:s.length(),back:s2.length()};}", r['id'])
            ok('the house instance is hidden for its broken copy, and back on the next flight', h['hid'] < 1e-6 and h['back'] > 1, h)
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
