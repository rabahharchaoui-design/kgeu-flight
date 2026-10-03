# Item 4.2: Tokyo Haneda (RJTT) landmarks, skyline, night, billboard. iPhone 15 landscape, Hard, Cessna.
# Landmarks by name with their heights (Tokyo Tower 333 m, Skytree 634, the Rainbow Bridge towers 120),
# Mount Fuji at 42 km on TKY.fujiBrg; the item's triangles under 60k; from the 3 nm final to 34R Tokyo
# Tower or the Skytree and the Rainbow Bridge inside the camera frustum; Fuji inside it 3 km past the
# departure end of 34R at 400 m on the runway heading; the @OhRabah board and CITYBB.setChamp; Tokyo
# Tower and the Skytree in OBST (and a crash into the tower); the 34R/34L final and climb out clear of
# both towers, and the airliners after 90 s too; at night the towers' and city windows' materials
# emissive and the neon glows on (off by day); no console errors.
# Screenshots to overnight-screenshots/tokyo/ unless --noshots.
# Usage: .venv/bin/python tests/tokyo_check.py [--noshots]
import asyncio, sys, os, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

SHOT = '--noshots' not in sys.argv
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'tokyo')
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'rjtt'}

# which of the named points are inside the camera's frustum right now
INVIEW = """(pts)=>{const K=window.__kgeu,c=K.R3().camera;c.updateMatrixWorld();
  const F=new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(c.projectionMatrix,c.matrixWorldInverse));
  const o={};for(const k in pts)o[k]=F.containsPoint(new THREE.Vector3(...pts[k]));return o;}"""
# landmark points: Tokyo Tower at 200 m, the Skytree at 400 m, both bridge tower tops, Fuji's summit
PTS = """()=>{const K=window.__kgeu,S=K.R3().scene,B=new THREE.Box3(),o={};
  for(const [k,n,f] of [['tower','tokyo_tower',0.6],['skytree','skytree',0.63],['bridgeN','rainbow_tower_n',0.9],['bridgeS','rainbow_tower_s',0.9],['fuji','fuji',0.97]]){
    const g=S.getObjectByName(n);B.setFromObject(g);o[k]=[(B.min.x+B.max.x)/2,B.min.y+(B.max.y-B.min.y)*f,(B.min.z+B.max.z)/2];}
  return o;}"""


async def main():
    if SHOT: os.makedirs(SHOTS, exist_ok=True)
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=30000)
        ev = lambda js, a=None: pg.evaluate(js, a)
        await ev("()=>{const K=window.__kgeu;K.setSkill('pilot');K.setTOD('day');}")
        r = await ev("""()=>{const K=window.__kgeu,S=K.R3().scene,B=new THREE.Box3(),o={region:K.REGION.id,built:K.TKY.built,tris:K.TKY.tris};
          for(const n of ['tokyo_tower','skytree','rainbow_bridge','rainbow_tower_n','rainbow_tower_s','fuji','tokyo_skyline','tokyo_neon','fujitv_sphere','city_billboard']){
            const g=S.getObjectByName(n);if(!g){o[n]=null;continue;}B.setFromObject(g);o[n]={h:B.max.y-B.min.y,top:B.max.y,x:(B.min.x+B.max.x)/2,z:(B.min.z+B.max.z)/2};}
          const fr=K.wframe(),ax=-fr.woff[0],az=-fr.woff[1];o.fuji.d=Math.hypot(o.fuji.x-ax,o.fuji.z-az);o.fuji.brg=((Math.atan2(o.fuji.x-ax,-(o.fuji.z-az))*180/Math.PI)+360)%360;
          o.fujiBrg=K.TKY.fujiBrg;o.fujiReal=K.TKY.fujiReal;return o;}""")
        c('rjtt: Tokyo built', r['region'] == 'rjtt' and r['built'])
        c('every landmark by name', all(r[n] for n in ['tokyo_tower', 'skytree', 'rainbow_bridge', 'rainbow_tower_n', 'rainbow_tower_s', 'fuji', 'tokyo_skyline', 'tokyo_neon', 'city_billboard']),
          [n for n in r if r[n] is None])
        c('Tokyo Tower about 333 m tall', abs(r['tokyo_tower']['h'] - 333) < 6, round(r['tokyo_tower']['h'], 1))
        c('Skytree about 634 m tall', abs(r['skytree']['h'] - 634) < 6, round(r['skytree']['h'], 1))
        c('Rainbow Bridge towers 120 m', abs(r['rainbow_tower_n']['h'] - 120) < 3 and abs(r['rainbow_tower_s']['h'] - 120) < 3,
          (r['rainbow_tower_n']['h'], r['rainbow_tower_s']['h']))
        f = r['fuji']
        c('Fuji 3,000 m high at 42 km on TKY.fujiBrg', abs(f['top'] - 3000) < 50 and abs(f['d'] - 42000) < 300 and abs((f['brg'] - r['fujiBrg'] + 540) % 360 - 180) < 1,
          {'top': round(f['top']), 'd': round(f['d']), 'brg': round(f['brg'], 1), 'real': round(r['fujiReal'], 1)})
        tot = sum(r['tris'].values())
        c('Tokyo item under 60k triangles', tot < 60000, (tot, r['tris']))
        # the 3 nm final to 34R, rendered: a tower and the bridge in the frustum
        await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');for(let i=0;i<4;i++)K.stepFrame(1/30);}")
        pts = await ev(PTS)
        v = await ev(INVIEW, pts)
        c('3 nm final: Tokyo Tower or the Skytree in view', v['tower'] or v['skytree'], v)
        c('3 nm final: the Rainbow Bridge in view', v['bridgeN'] or v['bridgeS'], v)
        c('3 nm final: Fuji in view', v['fuji'], v)
        if SHOT: await pg.screenshot(path=f'{SHOTS}/final_day.png')
        # 3 km past the departure end of 34R, 400 m, runway heading
        dep = await ev("""(pts)=>{const K=window.__kgeu,s=K.state(),fr=K.wframe(),u=fr.len+3000,x=Math.sin(fr.rh)*u,z=-Math.cos(fr.rh)*u;
          s.pos.set(x,400,z);s.vel.set(Math.sin(fr.rh)*55,0,-Math.cos(fr.rh)*55);s.quat.setFromEuler(new THREE.Euler(0,-fr.rh,0,'YXZ'));s.w.set(0,0,0);
          s.onGround=false;s.airTime=30;s.gearDown=false;s.gearPos=0;K.snapCam();for(let i=0;i<3;i++)K.stepFrame(1/30);
          const p=pts.fuji,b=((Math.atan2(p[0]-x,-(p[2]-z))*180/Math.PI)+360)%360,h=(fr.rh*180/Math.PI+360)%360;return {rel:((b-h+540)%360)-180};}""", pts)
        v = await ev(INVIEW, pts)
        c('after takeoff on 34R: Fuji in view, within 30 degrees of the nose', v['fuji'] and abs(dep['rel']) <= 30, (v['fuji'], round(dep['rel'], 1)))
        if SHOT: await pg.screenshot(path=f'{SHOTS}/departure_day.png')
        # the billboard and its champion line
        bb = await ev("""()=>{const K=window.__kgeu,B=K.CITYBB,o=B.list[0];if(!o)return null;const d0=o.tex.image.toDataURL(),v0=o.tex.version;
          B.setChamp('ABC');const r={n:B.list.length,champ:B.champ,changed:o.tex.image.toDataURL()!==d0&&o.tex.version>v0,city:o.city,x:o.x,z:o.z,hdg:o.hdg};B.setChamp(null);r.reset=B.champ===null;
          const fr=K.wframe(),u=o.x*Math.sin(fr.rh)-o.z*Math.cos(fr.rh),vv=o.x*Math.cos(fr.rh)+o.z*Math.sin(fr.rh);r.u=u-fr.thr01;r.v=vv;r.rh=fr.rh*180/Math.PI;
          r.obst=K.OBST.some(q=>q.name==='a billboard'&&Math.hypot(q.x-o.x,q.z-o.z)<1);r.water=K.isWater(o.x,o.z);return r;}""")
        c('one city billboard, Tokyo', bb and bb['n'] == 1 and bb['city'] == 'Tokyo', bb)
        c("CITYBB.setChamp('ABC') redraws the texture", bb and bb['champ'] == 'ABC' and bb['changed'] and bb['reset'], bb)
        c('billboard past the 34R threshold, left of the centreline, facing the approach, on land, in OBST',
          bb and 2000 < bb['u'] < 5500 and -400 < bb['v'] < 0 and abs(((bb['hdg'] - (bb['rh'] + 180)) + 540) % 360 - 180) < 2 and not bb['water'] and bb['obst'], bb)
        # OBST and a crash into Tokyo Tower
        cr = await ev("""()=>{const K=window.__kgeu,o=K.OBST.map(q=>q.name),S=K.R3().scene,B=new THREE.Box3().setFromObject(S.getObjectByName('tokyo_tower'));
          const x=(B.min.x+B.max.x)/2,z=(B.min.z+B.max.z)/2,s=K.state();s.pos.set(x+120,B.min.y+100,z);s.vel.set(-50,0,0);s.quat.setFromEuler(new THREE.Euler(0,Math.PI/2,0,'YXZ'));s.w.set(0,0,0);
          for(let i=0;i<120&&!s.crashed;i++)K.stepFrame(1/30,false,true);
          return {tower:o.includes('Tokyo Tower'),sky:o.includes('the Tokyo Skytree'),crashed:s.crashed,why:s.crashReason};}""")
        c('Tokyo Tower and the Skytree in OBST', cr['tower'] and cr['sky'], cr)
        c('flying into Tokyo Tower crashes', cr['crashed'] and 'Tokyo Tower' in (cr['why'] or ''), cr)
        # traffic: the 34R/34L finals (18.5 km) and climb outs (12 km) clear of both towers; airliners after 90 s
        tf = await ev("""()=>{const K=window.__kgeu,S=K.R3().scene,B=new THREE.Box3(),T=[];
          for(const n of ['tokyo_tower','skytree']){B.setFromObject(S.getObjectByName(n));T.push([(B.min.x+B.max.x)/2,(B.min.z+B.max.z)/2,B.max.y]);}
          const sd=(px,pz,ax,az,bx,bz)=>{const ex=bx-ax,ez=bz-az,L=ex*ex+ez*ez,t=Math.max(0,Math.min(1,((px-ax)*ex+(pz-az)*ez)/L));return Math.hypot(px-ax-ex*t,pz-az-ez*t);};
          let line=1e9;for(const r of K.RUNWAYS)for(const e of r.ends){if(!/^34/.test(e.num))continue;const o=r.ends.find(q=>q!==e);
            for(const p of T){line=Math.min(line,sd(p[0],p[1],e.x,e.z,e.x-e.dx*18520,e.z-e.dz*18520),sd(p[0],p[1],o.x,o.z,o.x+e.dx*12000,o.z+e.dz*12000));}}
          K.TFC.auto=true;K.pick('cessna');K.pickPos('ramp');K.start('ramp');let near=1e9,n=0;
          for(let i=0;i<900;i++){K.stepFrame(0.1,false,true);if(i%5)continue;for(const a of K.tfcList()){if(a.type!=='airliner')continue;n++;for(const p of T)if(a.y<p[2]+300)near=Math.min(near,Math.hypot(a.x-p[0],a.z-p[1]));}}
          return {line:Math.round(line),near:Math.round(near),n:n,crashed:K.state().crashed};}""")
        c('34L/34R finals and climb outs over 1.5 km from both towers', tf['line'] > 1500, tf)
        c('airliners never within 1 km of the towers below their tops + 300 m', tf['near'] > 1000 and tf['n'] > 0, tf)
        # night
        await ev("()=>window.__kgeu.setTOD('night')")
        nt = await ev("""()=>{const K=window.__kgeu,S=K.R3().scene,em=n=>{let e=false;S.getObjectByName(n).traverse(m=>{if(m.isMesh&&m.material.emissive&&m.material.emissive.getHex()>0&&m.material.emissiveIntensity>0)e=true;});return e;};
          const cm=S.getObjectByName('cityBoxes').material;
          return {tower:em('tokyo_tower'),sky:em('skytree'),bridge:em('rainbow_bridge'),city:!!cm.emissiveMap&&cm.emissiveIntensity>0,
            sky2:S.getObjectByName('tokyo_skyline').material===cm,neon:S.getObjectByName('tokyo_neon').visible,bb:K.CITYBB.list[0].mat.emissiveIntensity,L:K.TKY.L.pts.visible}}""")
        c('night: Tokyo Tower and the Skytree emissive', nt['tower'] and nt['sky'] and nt['bridge'], nt)
        c('night: city windows emissive on (one material with the skyline)', nt['city'] and nt['sky2'], nt)
        c('night: neon on, billboard lit, landmark lights on', nt['neon'] and nt['bb'] > 0.5 and nt['L'], nt)
        if SHOT:
            await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');for(let i=0;i<4;i++)K.stepFrame(1/30);}")
            await pg.screenshot(path=f'{SHOTS}/final_night.png')
            await ev("""()=>{const K=window.__kgeu,o=K.CITYBB.list[0],s=K.state();K.freeCam(null);}""")
        await ev("()=>window.__kgeu.setTOD('day')")
        dy = await ev("""()=>{const K=window.__kgeu,S=K.R3().scene,m=S.getObjectByName('tokyo_tower_mesh').material,cm=S.getObjectByName('cityBoxes').material;
          return {neon:S.getObjectByName('tokyo_neon').visible,tower:m.emissive.getHex()>0&&m.emissiveIntensity>0,city:cm.emissiveIntensity}}""")
        c('day: neon off, tower and windows not emissive', not dy['neon'] and not dy['tower'] and dy['city'] == 0, dy)
        c('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(c.done('tokyo_check'))

asyncio.run(main())
