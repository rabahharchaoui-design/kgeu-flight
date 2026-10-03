# Item 4.4: Rio Santos Dumont (SBRJ) landmarks, mountains, beach, night, billboard. iPhone 15 landscape, Hard, Cessna.
# The mountains raised to their real height over the field elevation (Sugarloaf 396 m, Morro da Urca 220,
# Corcovado 710, groundHeight being metres over the home runway); landmark groups by name (Christ the
# Redeemer 38 m over its summit; the cable car cabins moving between two frames 10 s apart; 6 or more boats;
# the Copacabana sand; 40 to 60 hotels; 450 favela boxes); the item under 60k triangles; Sugarloaf in the
# frustum 3 km past the departure end of 20L at 400 m, Christ in it from the 3 nm final; nothing over 60 m
# within 1 km of the 20L final's centre line; the Rio-Niteroi bridge's raised span; the @OhRabah board on
# land right of the final, inside 1 nm and 35 degrees, facing the approach, in OBST, CITYBB.setChamp; at
# night Christ lit without fog and the windows lit; no console errors.
# Screenshots to overnight-screenshots/rio/ unless --noshots.
# Usage: .venv/bin/python tests/rio_check.py [--noshots]
import asyncio, sys, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

SHOT = '--noshots' not in sys.argv
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'rio')
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'sbrj'}

INVIEW = """(pts)=>{const K=window.__kgeu,c=K.R3().camera;c.updateMatrixWorld();
  const F=new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(c.projectionMatrix,c.matrixWorldInverse));
  const o={};for(const k in pts)o[k]=F.containsPoint(new THREE.Vector3(...pts[k]));return o;}"""
# Sugarloaf at 60% of its height, Christ at 70% of his
PTS = """()=>{const K=window.__kgeu,R=K.RIO,s=R.lm.sugarloaf,g=K.groundHeight(...s);
  return {sugarloaf:[s[0],g*0.6,s[1]],christ:[R.cv[0],R.christBase+38*0.7,R.cv[1]]};}"""
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/30,false,true);}"
CABINS = "()=>window.__kgeu.RIO.cabins.map(c=>[c.g.position.x,c.g.position.y,c.g.position.z])"


async def main():
    if SHOT: os.makedirs(SHOTS, exist_ok=True)
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=60000)
        ev = lambda js, a=None: pg.evaluate(js, a)
        await ev("()=>{const K=window.__kgeu;K.setSkill('pilot');K.setTOD('day');}")
        r = await ev("""()=>{const K=window.__kgeu,R=K.RIO,S=K.R3().scene,B=new THREE.Box3(),g=K.groundHeight,E=K.REGION.elev,
            o={region:K.REGION.id,built:R.built,tris:R.tris,n:R.n,elev:E,dois:R.doisTop,bumps:K.TERR.bumps.map(b=>b.name)};
          o.sug=g(...R.lm.sugarloaf);o.urca=g(...R.lm.urca);o.cv=g(...R.cv);
          for(const n of ['sugarloaf','morro_da_urca','corcovado','cable_car','christ_redeemer','copacabana_sand','copacabana_waves','copacabana_promenade',
            'avenida_atlantica','copacabana_sea','copacabana_hotels','centro_towers','museum_of_tomorrow','favelas','bay_boats','bay_ferries','city_billboard']){
            const q=S.getObjectByName(n);o[n]=q?(B.setFromObject(q),{top:B.max.y,count:q.isInstancedMesh?q.count:null}):null;}
          o.christH=o.christ_redeemer&&o.christ_redeemer.top-R.christBase;o.cabins=R.cabins.length;o.ferries=R.ferries.length;o.route=!!R.ferryRoute;
          o.sea=K.isWater(R.arc.pts[40].x-R.arc.pts[40].nx*200,R.arc.pts[40].z-R.arc.pts[40].nz*200);o.sand=!K.isWater(R.arc.pts[40].x+R.arc.pts[40].nx*50,R.arc.pts[40].z+R.arc.pts[40].nz*50);
          o.deckTop=R.deckTop;o.arcLen=R.arc.len;return o;}""")
        c('sbrj: Rio built', r['region'] == 'sbrj' and r['built'], r['region'])
        names = ['sugarloaf', 'morro_da_urca', 'corcovado', 'cable_car', 'christ_redeemer', 'copacabana_sand', 'copacabana_waves', 'copacabana_promenade',
                 'avenida_atlantica', 'copacabana_sea', 'copacabana_hotels', 'centro_towers', 'museum_of_tomorrow', 'favelas', 'bay_boats', 'bay_ferries', 'city_billboard']
        c('every landmark group by name', all(r[n] for n in names), [n for n in names if not r[n]])
        E = r['elev']
        c('Sugarloaf summit about 396 m (over the field)', abs(r['sug'] - (396 - E)) < 30, round(r['sug'], 1))
        c('Morro da Urca about 220 m', abs(r['urca'] - (220 - E)) < 30, round(r['urca'], 1))
        c('Corcovado about 710 m', abs(r['cv'] - (710 - E)) < 30, round(r['cv'], 1))
        c('Christ the Redeemer 38 m over the summit (30 m statue on an 8 m pedestal)', r['christH'] and abs(r['christH'] - 38) < 1, r['christH'])
        c('cable car: two cabins, Copacabana sea in front of the sand', r['cabins'] == 2 and r['sea'] and r['sand'], (r['cabins'], r['sea'], r['sand']))
        c('Copacabana: the sand a 3 to 4.5 km crescent, 40 to 60 hotels', 3000 < r['arcLen'] < 4500 and 40 <= r['n'].get('hotels', 0) <= 60, (r['arcLen'], r['n'].get('hotels')))
        c('Centro: 15 to 25 towers; 3 favela clusters of 150 (450 instances)', 15 <= r['n'].get('towers', 0) <= 25 and r['favelas']['count'] == 450, (r['n'].get('towers'), r['favelas']['count']))
        c('6 or more boats in the bay, 2 ferries on an all-water route', r['n'].get('boats', 0) >= 6 and r['ferries'] == 2 and r['route'], (r['n'].get('boats'), r['ferries'], r['route']))
        c('Rio-Niteroi bridge: the deck 72 m over the water at the span', abs(r['deckTop'] - 72.4) < 2, r['deckTop'])
        tot = sum(r['tris'].values())
        c('Rio item under 60k triangles', tot < 60000, (tot, r['tris']))
        # cabins move between two frames 10 s apart
        await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');}")
        c0 = await ev(CABINS)
        await ev(STEP, 300)
        c1 = await ev(CABINS)
        mv = [((a[0]-b2[0])**2 + (a[1]-b2[1])**2 + (a[2]-b2[2])**2) ** 0.5 for a, b2 in zip(c0, c1)]
        c('cable car cabins move in 10 s', len(mv) == 2 and all(m > 5 for m in mv), [round(m, 1) for m in mv])
        # the 3 nm final to 20L, rendered: Christ in the frustum
        await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');for(let i=0;i<4;i++)K.stepFrame(1/30);}")
        pts = await ev(PTS)
        v = await ev(INVIEW, pts)
        c('3 nm final to 20L: Christ the Redeemer in view', v['christ'], v)
        if SHOT: await pg.screenshot(path=f'{SHOTS}/final_day.png')
        # 3 km past the departure end of 20L, 400 m, runway heading
        await ev("""()=>{const K=window.__kgeu,s=K.state(),fr=K.wframe(),u=fr.len+3000,x=Math.sin(fr.rh)*u,z=-Math.cos(fr.rh)*u;
          s.pos.set(x,400,z);s.vel.set(Math.sin(fr.rh)*55,0,-Math.cos(fr.rh)*55);s.quat.setFromEuler(new THREE.Euler(0,-fr.rh,0,'YXZ'));s.w.set(0,0,0);
          s.onGround=false;s.airTime=30;s.gearDown=false;s.gearPos=0;K.snapCam();for(let i=0;i<3;i++)K.stepFrame(1/30);}""")
        v = await ev(INVIEW, pts)
        ang = await ev("""()=>{const K=window.__kgeu,s=K.state(),fr=K.wframe(),q=K.RIO.lm.sugarloaf,b=Math.atan2(q[0]-s.pos.x,-(q[1]-s.pos.z));
          return ((b-fr.rh)*180/Math.PI+540)%360-180;}""")
        c('after takeoff from 20L: Sugarloaf in view, left of the nose within 30 degrees', v['sugarloaf'] and -31 < ang < 0, (v, round(ang, 1)))
        if SHOT: await pg.screenshot(path=f'{SHOTS}/departure_day.png')
        # nothing over 60 m within 1 km of the final's centre line (out to 10 km), nor on the field
        tall = await ev("""()=>{const K=window.__kgeu,R=K.RIO,fr=K.wframe(),g=K.groundHeight,out=[];
          const uv=(x,z)=>[x*Math.sin(fr.rh)-z*Math.cos(fr.rh),x*Math.cos(fr.rh)+z*Math.sin(fr.rh)];
          const chk=(x,z,h,n)=>{const [u,v]=uv(x,z);if(u<fr.thr01+200&&u>fr.thr01-10000&&Math.abs(v)<1000&&h>60)out.push([n,Math.round(u),Math.round(v),Math.round(h)]);};
          for(const t of R.towers)chk(t.x,t.z,t.h,'tower');for(const h of R.hotels)chk(h[0],h[1],h[4],'hotel');
          for(const p of R.deck)chk(p[0],p[2],p[1],'bridge');
          for(const o of K.OBST)if(o.kind==='circ')chk(o.x,o.z,o.h-g(o.x,o.z),o.name);
          const im=K.R3().scene.getObjectByName('cityBoxes'),M=new THREE.Matrix4(),q=new THREE.Vector3(),sc=new THREE.Vector3(),qq=new THREE.Quaternion();
          for(let i=0;i<im.count;i++){im.getMatrixAt(i,M);M.decompose(q,qq,sc);chk(q.x,q.z,sc.y,'city');}
          return {out:out.slice(0,6),n:out.length,towersMinV:Math.min(...R.towers.map(t=>Math.abs(uv(t.x,t.z)[1])))};}""")
        c('nothing over 60 m within 1 km of the 20L final centre line; Centro towers clear of it', tall['n'] == 0 and tall['towersMinV'] > 1000, tall)
        # the billboard and its champion line
        bb = await ev("""()=>{const K=window.__kgeu,B=K.CITYBB,o=B.list[0];if(!o)return null;const d0=o.tex.image.toDataURL(),v0=o.tex.version;
          B.setChamp('ABC');const r={n:B.list.length,champ:B.champ,changed:o.tex.image.toDataURL()!==d0&&o.tex.version>v0,city:o.city,hdg:o.hdg};B.setChamp(null);r.reset=B.champ===null;
          const fr=K.wframe(),u=o.x*Math.sin(fr.rh)-o.z*Math.cos(fr.rh),vv=o.x*Math.cos(fr.rh)+o.z*Math.sin(fr.rh);r.u=u-fr.thr01;r.v=vv;r.rh=fr.rh*180/Math.PI;
          r.ang=Math.atan2(vv,-r.u)*180/Math.PI;r.d=Math.hypot(r.u,vv);r.h=K.groundHeight(o.x,o.z);
          r.obst=K.OBST.some(q=>q.name==='a billboard'&&Math.hypot(q.x-o.x,q.z-o.z)<1);r.water=K.isWater(o.x,o.z);
          const im=K.R3().scene.getObjectByName('cityBoxes'),M=new THREE.Matrix4(),p=new THREE.Vector3();let near=1e9;
          for(let i=0;i<im.count;i++){im.getMatrixAt(i,M);p.setFromMatrixPosition(M);near=Math.min(near,Math.hypot(p.x-o.x,p.z-o.z));}r.near=Math.round(near);return r;}""")
        c('one city billboard, Rio', bb and bb['n'] == 1 and bb['city'] == 'Rio', bb)
        c("CITYBB.setChamp('ABC') redraws the texture", bb and bb['champ'] == 'ABC' and bb['changed'] and bb['reset'], bb)
        c('billboard right of the 20L final, inside 1 nm of the threshold and 35 degrees, facing the approach, on land over the water level, in OBST, boxes cleared',
          bb and bb['u'] < 0 and bb['v'] > 0 and bb['ang'] <= 35 and bb['d'] <= 1852 and abs(((bb['hdg'] - (bb['rh'] + 180)) + 540) % 360 - 180) < 2
          and not bb['water'] and bb['h'] > 0 and bb['obst'] and bb['near'] > 60, bb)
        # OBST and a crash into Christ
        cr = await ev("""()=>{const K=window.__kgeu,o=K.OBST.map(q=>q.name),R=K.RIO,s=K.state();
          s.pos.set(R.cv[0]+150,R.christBase+22,R.cv[1]);s.vel.set(-50,0,0);s.quat.setFromEuler(new THREE.Euler(0,Math.PI/2,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;
          for(let i=0;i<120&&!s.crashed;i++)K.stepFrame(1/30,false,true);
          return {christ:o.includes('Christ the Redeemer'),cable:o.includes('the cable car station'),crashed:s.crashed,why:s.crashReason};}""")
        c('OBST: Christ the Redeemer, the cable car stations; flying into Christ crashes', cr['christ'] and cr['cable'] and cr['crashed'], cr)
        # night
        await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');K.setTOD('night');}")
        await ev(STEP, 3)
        nt = await ev("""()=>{const K=window.__kgeu,R=K.RIO,S=K.R3().scene,m=S.getObjectByName('christ_mesh').material,cm=S.getObjectByName('cityBoxes').material,
          hm=S.getObjectByName('copacabana_hotels').material,tm=S.getObjectByName('centro_towers').material;
          return {christ:m.emissive.getHex()>0&&m.emissiveIntensity>0.5&&m.fog===false,city:!!cm.emissiveMap&&cm.emissiveIntensity>0,hotels:!!hm.emissiveMap&&hm.emissiveIntensity>0,
            towers:!!tm.emissiveMap&&tm.emissiveIntensity>0,L:R.L.pts.visible,CL:R.CL.pts.visible,nL:R.L.count()}}""")
        c('night: Christ floodlit white, no fog', nt['christ'], nt)
        c('night: windows lit (city, hotels, Centro), the lights on', nt['city'] and nt['hotels'] and nt['towers'] and nt['L'] and nt['CL'], nt)
        if SHOT:
            await ev("()=>{const K=window.__kgeu;for(let i=0;i<4;i++)K.stepFrame(1/30);}")
            await pg.screenshot(path=f'{SHOTS}/final_night.png')
        await ev("()=>window.__kgeu.setTOD('day')")
        await ev(STEP, 2)
        dy = await ev("()=>{const m=window.__kgeu.R3().scene.getObjectByName('christ_mesh').material;return {lit:m.emissiveIntensity>0&&m.emissive.getHex()>0}}")
        c('day: Christ unlit', not dy['lit'], dy)
        c('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(c.done('rio_check'))

asyncio.run(main())
