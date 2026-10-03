# Item 4.3: Paris Charles de Gaulle (LFPG) landmarks, the Seine, night, billboard. iPhone 15 landscape, Hard, Cessna.
# Landmark groups by name with their heights over their own ground (the Eiffel Tower 330 m built 1.6 times,
# the Arc de Triomphe 50, the Sacre-Coeur dome 83, Notre-Dame's towers 69, the Grande Arche 110, the Defense
# towers up to 231 m built 1.3 times); the item's triangles under 60k; the Eiffel Tower and the Defense
# cluster inside the camera frustum from the 3 nm final to 26L and 3 km past the departure end at 400 m;
# the @OhRabah board 2.5 nm out on the final, left of the centreline, facing the approach, and
# CITYBB.setChamp; OBST; the Seine round Notre-Dame (water both sides, the island land) and six bridges;
# Haussmann boxes in the core; Terminal 1 a 25 m drum; at night the Eiffel Tower gold, the sparkle forced
# on and off by PARIS.forceSparkle and on by itself in the first 5 minutes of the hour (Date mocked by an
# init script), the beacon; no console errors.
# Screenshots to overnight-screenshots/paris/ unless --noshots.
# Usage: .venv/bin/python tests/paris_check.py [--noshots]
import asyncio, sys, os, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

SHOT = '--noshots' not in sys.argv
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'paris')
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'lfpg'}
# the clock's minutes, mocked: window.__mins (30 until a case sets it)
MOCK = "window.__mins=30;Date.prototype.getMinutes=function(){return window.__mins;};"

INVIEW = """(pts)=>{const K=window.__kgeu,c=K.R3().camera;c.updateMatrixWorld();
  const F=new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(c.projectionMatrix,c.matrixWorldInverse));
  const o={};for(const k in pts)o[k]=F.containsPoint(new THREE.Vector3(...pts[k]));return o;}"""
# the Eiffel Tower at 60% of its height, the tallest Defense tower at half its height, the Grande Arche's top
PTS = """()=>{const K=window.__kgeu,P=K.PARIS,S=K.R3().scene,B=new THREE.Box3().setFromObject(S.getObjectByName('eiffel_tower')),o={};
  o.eiffel=[(B.min.x+B.max.x)/2,P.base.eiffel_tower+(B.max.y-P.base.eiffel_tower)*0.6,(B.min.z+B.max.z)/2];
  const t=P.def.reduce((a,b)=>b.h>a.h?b:a);o.defense=[t.x,K.groundHeight(t.x,t.z)+t.h/2,t.z];
  B.setFromObject(S.getObjectByName('grande_arche'));o.arche=[(B.min.x+B.max.x)/2,B.max.y-5,(B.min.z+B.max.z)/2];return o;}"""
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/30);}"


async def main():
    if SHOT: os.makedirs(SHOTS, exist_ok=True)
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.context.add_init_script(MOCK); await pg.evaluate("()=>{" + MOCK + "}")
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=30000)
        ev = lambda js, a=None: pg.evaluate(js, a)
        async def step(n):   # parisTick does its work every 0.4 s of real time: wait that out, then run frames
            await pg.wait_for_timeout(450); await ev(STEP, n)
        await ev("()=>{const K=window.__kgeu;K.setSkill('pilot');K.setTOD('day');}")
        r = await ev("""()=>{const K=window.__kgeu,P=K.PARIS,S=K.R3().scene,B=new THREE.Box3(),o={region:K.REGION.id,built:P.built,tris:P.tris,defTop:P.defTop,nDef:P.def.length,bridges:P.bridges,t1:K.WB.n.t1};
          for(const n of ['eiffel_tower','arc_de_triomphe','etoile_plaza','sacre_coeur','notre_dame','notre_dame_towers','grande_arche','la_defense','seine','seine_bridges','city_billboard']){
            const g=S.getObjectByName(n);if(!g){o[n]=null;continue;}B.setFromObject(g);o[n]={top:B.max.y};}
          for(const n in P.base)o[n].h=o[n].top-P.base[n];o.notre_dame_towers.h=o.notre_dame_towers.top-P.base.notre_dame;
          // the Arc's plaza: no city box within 80 m; Haussmann boxes in the core
          const a=P.lm.arc,im=S.getObjectByName('cityBoxes'),M=new THREE.Matrix4(),q=new THREE.Vector3(),sc=new THREE.Vector3(),qq=new THREE.Quaternion();let near=1e9,core=0,hs=[];
          for(let i=0;i<im.count;i++){im.getMatrixAt(i,M);M.decompose(q,qq,sc);near=Math.min(near,Math.hypot(q.x-a[0],q.z-a[1]));if(P.coreAt(q.x,q.z)<1){core++;hs.push(sc.y);}}
          o.arcNear=Math.round(near);o.core=core;o.coreH=[Math.min(...hs),Math.max(...hs)];o.n=im.count;
          const cm=im.material;o.roof=cm.userData&&0;return o;}""")
        c('lfpg: Paris built', r['region'] == 'lfpg' and r['built'])
        names = ['eiffel_tower', 'arc_de_triomphe', 'etoile_plaza', 'sacre_coeur', 'notre_dame', 'notre_dame_towers', 'grande_arche', 'la_defense', 'seine', 'seine_bridges', 'city_billboard']
        c('every landmark group by name', all(r[n] for n in names), [n for n in names if not r[n]])
        h = lambda n: round(r[n]['h'], 1)
        c('Eiffel Tower about 330 x 1.6 = 528 m over its ground', abs(r['eiffel_tower']['h'] - 528) < 8, h('eiffel_tower'))
        c('Arc de Triomphe 50 m', abs(r['arc_de_triomphe']['h'] - 50) < 1.5, h('arc_de_triomphe'))
        c('Sacre-Coeur dome 83 m', abs(r['sacre_coeur']['h'] - 83) < 2, h('sacre_coeur'))
        c("Notre-Dame: towers 69 m, the spire 96", abs(r['notre_dame_towers']['h'] - 69) < 1.5 and abs(r['notre_dame']['h'] - 96) < 2, (h('notre_dame_towers'), h('notre_dame')))
        c('Grande Arche 110 m', abs(r['grande_arche']['h'] - 110) < 2, h('grande_arche'))
        c('La Defense: 12 to 16 towers, the tallest 231 x 1.3 m', 12 <= r['nDef'] <= 16 and abs(r['defTop'] - 231 * 1.3) < 1, (r['nDef'], r['defTop']))
        tot = sum(r['tris'].values())
        c('Paris item under 60k triangles', tot < 60000, (tot, r['tris']))
        c('no city box within 80 m of the Arc', r['arcNear'] > 80, r['arcNear'])
        c('Haussmann core: over 1,000 boxes 18 to 30 m, cap 6,000 kept', r['core'] > 1000 and r['coreH'][0] >= 17.9 and r['coreH'][1] <= 30.1 and r['n'] <= 6000, (r['core'], r['coreH'], r['n']))
        c('six bridges over the Seine', r['bridges'] == 6, r['bridges'])
        c('Terminal 1 a 25 m drum', (r['t1'] or 0) >= 1, r['t1'])
        # the Seine round Notre-Dame: water north (280 m) and south (75 m), the island land
        w = await ev("""()=>{const K=window.__kgeu,n=K.PARIS.lm.notre_dame;return {nd:K.isWater(n[0],n[1]),north:K.isWater(n[0],n[1]-280),south:K.isWater(n[0],n[1]+75),
          eiffel:K.isWater(...K.PARIS.lm.eiffel)}}""")
        c('the Seine both sides of Notre-Dame, the Ile de la Cite land', w['north'] and w['south'] and not w['nd'] and not w['eiffel'], w)
        # the 3 nm final to 26L, rendered: the Eiffel Tower and the Defense in the frustum
        await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');for(let i=0;i<4;i++)K.stepFrame(1/30);}")
        pts = await ev(PTS)
        v = await ev(INVIEW, pts)
        c('3 nm final to 26L: the Eiffel Tower in view', v['eiffel'], v)
        c('3 nm final to 26L: the Defense cluster in view', v['defense'], v)
        if SHOT: await pg.screenshot(path=f'{SHOTS}/final_day.png')
        # 3 km past the departure end of 26L, 400 m, runway heading
        await ev("""()=>{const K=window.__kgeu,s=K.state(),fr=K.wframe(),u=fr.len+3000,x=Math.sin(fr.rh)*u,z=-Math.cos(fr.rh)*u;
          s.pos.set(x,400,z);s.vel.set(Math.sin(fr.rh)*55,0,-Math.cos(fr.rh)*55);s.quat.setFromEuler(new THREE.Euler(0,-fr.rh,0,'YXZ'));s.w.set(0,0,0);
          s.onGround=false;s.airTime=30;s.gearDown=false;s.gearPos=0;K.snapCam();for(let i=0;i<3;i++)K.stepFrame(1/30);}""")
        v = await ev(INVIEW, pts)
        c('after takeoff from 26L: the Eiffel Tower and the Defense in view', v['eiffel'] and v['defense'], v)
        if SHOT: await pg.screenshot(path=f'{SHOTS}/departure_day.png')
        # the billboard and its champion line
        bb = await ev("""()=>{const K=window.__kgeu,B=K.CITYBB,o=B.list[0];if(!o)return null;const d0=o.tex.image.toDataURL(),v0=o.tex.version;
          B.setChamp('ABC');const r={n:B.list.length,champ:B.champ,changed:o.tex.image.toDataURL()!==d0&&o.tex.version>v0,city:o.city,hdg:o.hdg};B.setChamp(null);r.reset=B.champ===null;
          const fr=K.wframe(),u=o.x*Math.sin(fr.rh)-o.z*Math.cos(fr.rh),vv=o.x*Math.cos(fr.rh)+o.z*Math.sin(fr.rh);r.u=u-fr.thr01;r.v=vv;r.rh=fr.rh*180/Math.PI;
          r.obst=K.OBST.some(q=>q.name==='a billboard'&&Math.hypot(q.x-o.x,q.z-o.z)<1);r.water=K.isWater(o.x,o.z);
          const im=K.R3().scene.getObjectByName('cityBoxes'),M=new THREE.Matrix4(),p=new THREE.Vector3();let near=1e9;
          for(let i=0;i<im.count;i++){im.getMatrixAt(i,M);p.setFromMatrixPosition(M);near=Math.min(near,Math.hypot(p.x-o.x,p.z-o.z));}r.near=Math.round(near);return r;}""")
        c('one city billboard, Paris', bb and bb['n'] == 1 and bb['city'] == 'Paris', bb)
        c("CITYBB.setChamp('ABC') redraws the texture", bb and bb['champ'] == 'ABC' and bb['changed'] and bb['reset'], bb)
        c('billboard 2.5 nm out on the final to 26L, 250 m left, facing the approach, on land, in OBST, boxes cleared',
          bb and -4900 < bb['u'] < -4300 and -300 < bb['v'] < -200 and abs(((bb['hdg'] - (bb['rh'] + 180)) + 540) % 360 - 180) < 2 and not bb['water'] and bb['obst'] and bb['near'] > 60, bb)
        # OBST and a crash into the Eiffel Tower's upper column
        cr = await ev("""()=>{const K=window.__kgeu,o=K.OBST.map(q=>q.name),P=K.PARIS,e=P.lm.eiffel,s=K.state();
          s.pos.set(e[0]+150,P.base.eiffel_tower+300,e[1]);s.vel.set(-50,0,0);s.quat.setFromEuler(new THREE.Euler(0,Math.PI/2,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;
          for(let i=0;i<120&&!s.crashed;i++)K.stepFrame(1/30,false,true);
          return {eiffel:o.includes('the Eiffel Tower'),arche:o.includes('the Grande Arche'),sc:o.includes('the Sacre-Coeur'),sky:o.filter(n=>n==='a skyscraper').length,crashed:s.crashed,why:s.crashReason};}""")
        c('OBST: the Eiffel Tower, the Grande Arche, the Sacre-Coeur, the tallest Defense towers', cr['eiffel'] and cr['arche'] and cr['sc'] and cr['sky'] >= 3, cr)
        c('flying into the Eiffel Tower crashes', cr['crashed'] and 'Eiffel' in (cr['why'] or ''), cr)
        # night: gold, the sparkle forced on and off, then by the (mocked) clock
        await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');K.setTOD('night');}")
        await step(3)
        nt = await ev("""()=>{const K=window.__kgeu,P=K.PARIS,S=K.R3().scene,m=S.getObjectByName('eiffel_mesh').material,cm=S.getObjectByName('cityBoxes').material,
          em=n=>{const q=S.getObjectByName(n).material;return q.emissive.getHex()>0&&q.emissiveIntensity>0;};
          return {gold:m.emissive.getHex()>0&&m.emissiveIntensity>0.5&&m.fog===false,g:m.emissive.getHexString(),arc:em('arc_mesh'),sc:em('sacre_coeur_mesh'),nd:em('notre_dame_mesh'),
            def:S.getObjectByName('la_defense').material.emissiveIntensity,city:!!cm.emissiveMap&&cm.emissiveIntensity>0,sparkle:P.sparkle,spVis:P.SP.pts.visible,L:P.L.pts.visible,n:P.SP.count()}}""")
        c('night: the Eiffel Tower gold, no fog', nt['gold'], nt)
        c('night: the Arc, the Sacre-Coeur and Notre-Dame lit, Defense and city windows lit', nt['arc'] and nt['sc'] and nt['nd'] and nt['def'] > 0.5 and nt['city'] and nt['L'], nt)
        c('night at :30: no sparkle', not nt['sparkle'] and not nt['spVis'], nt)
        await ev("()=>{window.__kgeu.PARIS.forceSparkle=true;}")
        await step(3)
        s1 = await ev("()=>{const P=window.__kgeu.PARIS;return {on:P.sparkle,vis:P.SP.pts.visible,inScene:!!P.SP.pts.parent,n:P.SP.count()}}")
        c('PARIS.forceSparkle=true: the sparkle layer visible (a few hundred lights)', s1['on'] and s1['vis'] and s1['inScene'] and 200 <= s1['n'] <= 800, s1)
        if SHOT: await pg.screenshot(path=f'{SHOTS}/final_night_sparkle.png')
        await ev("()=>{window.__kgeu.PARIS.forceSparkle=false;window.__mins=2;}")
        await step(3)
        s2 = await ev("()=>{const P=window.__kgeu.PARIS;return {on:P.sparkle,vis:P.SP.pts.visible}}")
        c('PARIS.forceSparkle=false hides it (even at :02)', not s2['on'] and not s2['vis'], s2)
        await ev("()=>{window.__kgeu.PARIS.forceSparkle=null;}")
        await step(3)
        s3 = await ev("()=>{const P=window.__kgeu.PARIS;return {on:P.sparkle,vis:P.SP.pts.visible,m:new Date().getMinutes()}}")
        c('night at :02 (mocked Date): the sparkle on by itself', s3['on'] and s3['vis'] and s3['m'] == 2, s3)
        await ev("()=>window.__kgeu.setTOD('day')")
        await step(2)
        dy = await ev("()=>{const P=window.__kgeu.PARIS,m=window.__kgeu.R3().scene.getObjectByName('eiffel_mesh').material;return {on:P.sparkle,gold:m.emissiveIntensity>0&&m.emissive.getHex()>0,fog:m.fog}}")
        c('day at :02: no sparkle, the tower bronze, drawn without fog', not dy['on'] and not dy['gold'] and dy['fog'] is False, dy)
        c('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(c.done('paris_check'))

asyncio.run(main())
