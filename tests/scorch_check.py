# Crash scorch z-fighting (phone notes 0929 item 4). The scorch used to be a flat disc laid
# 15 cm over groundHeight at its centre, with polygonOffset, which the log depth buffer
# ignores (it writes gl_FragDepth): on iPhone it flickered. Now it follows the terrain mesh
# vertex by vertex, lifts with range and pulls its depth toward the camera in the shader.
# Checks, after a real F-16 crash at Glendale (flat) and an explosion on a White Tank slope:
#  - every scorch vertex sits on or just above the terrain mesh (never under, never floating)
#  - rendered from a slowly moving camera close (chase, ~25 m) and far (1.2 km, 2.5 km), the
#    scorch darkens the ground by the same amount every frame (spread < 0.03) and no sample
#    inside it shows the bare terrain (speckle 0)
# Everything standing over 30 cm (wreck, buildings, trees), fire and smoke (the instanced quad
# layer and the instanced debris since item 15) is hidden for the pixel reads, so only the
# ground layers and the scorch are compared.
# Run: .venv/bin/python tests/scorch_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15

ok = Checks()
K = 'window.__kgeu'

async def step(pg, secs, dt=1/30):
    await pg.evaluate("([n,dt])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);}",
                      [max(1, round(secs/dt)), dt])

async def climb(pg, ft=150, limit=150):
    await pg.evaluate(f"()=>{K}.auto()")
    t = 0
    while t < limit:
        await step(pg, 1.0); t += 1
        if await pg.evaluate(f"()=>{K}.state().agl*3.28084") >= ft: return True
    return False

# vertices vs the terrain mesh under them
SIT = """(a)=>{const K=window.__kgeu,sc=K.fxScorch().find(m=>Math.hypot(m.position.x-a.x,m.position.z-a.z)<0.5);
  if(!sc)return null;const P=sc.geometry.attributes.position,lift=sc.position.y-sc.userData.base;let lo=1e9,hi=-1e9;
  for(let i=0;i<P.count;i++){const x=sc.position.x+P.getX(i)*sc.scale.x,z=sc.position.z+P.getZ(i)*sc.scale.z,
    d=sc.position.y+P.getY(i)-K.terrainMeshH(x,z);lo=Math.min(lo,d);hi=Math.max(hi,d);}
  return {lo:lo,hi:hi,lift:lift,r:sc.userData.r,n:P.count};}"""

# frames of a slowly moving camera; per frame the mean darkening inside the scorch and the
# share of samples where the terrain shows through
MEASURE = """(a)=>{const K=window.__kgeu,{scene,renderer,camera}=K.R3();
  const sc=K.fxScorch().find(m=>Math.hypot(m.position.x-a.x,m.position.z-a.z)<0.5);if(!sc)return null;
  const R=sc.userData.r,base=sc.userData.base,x=sc.position.x,z=sc.position.z,hid=[],bx=new THREE.Box3();
  scene.traverse(o=>{if(!o.visible||o===scene||o===sc)return;
    // fire, smoke, sparks and debris are one instanced quad layer and one instanced box mesh (item 15)
    if(o.isSprite||o.isPoints||o.isLine||o.isInstancedMesh||(o.geometry&&o.geometry.isInstancedBufferGeometry)){o.visible=false;hid.push(o);return;}
    if(!o.isMesh||(o.geometry.parameters&&o.geometry.parameters.width>=60000))return;
    bx.setFromObject(o);if(bx.max.y>base+0.3){o.visible=false;hid.push(o);}});
  const gl=renderer.getContext(),W=gl.drawingBufferWidth,H=gl.drawingBufferHeight,v=new THREE.Vector3(),fov0=camera.fov,out=[];
  // samples on rings inside the disc, each with the point at the disc's edge the same way out,
  // so a sample under 2 px from the edge on screen (grazing views far off) can be skipped
  const pts=[];for(const q of [0.15,0.3,0.45,0.6,0.75])for(let j=0;j<32;j++){const an=j/32*6.2832,c=Math.cos(an)*R,s=Math.sin(an)*R;
    pts.push([x+c*q,K.terrainMeshH(x+c*q,z+s*q),z+s*q,x+c*0.96,K.terrainMeshH(x+c*0.96,z+s*0.96),z+s*0.96]);}
  // a sample the scorch does not darken counts as speckle only if nothing stands in front of
  // it (a runway light box, a sign): the first thing the ray meets must be the ground or the scorch
  const rc=new THREE.Raycaster(),flat=o=>o===sc||(o.geometry.parameters&&o.geometry.parameters.width>=60000)||o.geometry.type==='PlaneGeometry';rc.camera=camera;
  const lum=(b,i)=>0.3*b[i]+0.59*b[i+1]+0.11*b[i+2];
  for(let f=0;f<a.frames;f++){
    const az=a.az+f*0.004,d=a.dist*(1+0.003*f),el=a.el+0.002*Math.sin(f*1.7);
    camera.position.set(x+Math.cos(az)*Math.cos(el)*d,base+Math.sin(el)*d,z+Math.sin(az)*Math.cos(el)*d);
    camera.up.set(0,1,0);camera.lookAt(x,base,z);camera.fov=a.fov;camera.updateProjectionMatrix();camera.updateMatrixWorld();
    sc.position.y=base+K.gdLift(x,base,z);
    const px=[];let x0=W,x1=0,y0=H,y1=0;
    for(const p of pts){v.set(p[3],p[4],p[5]).project(camera);const ex=(v.x+1)/2*W,ey=(v.y+1)/2*H;
      v.set(p[0],p[1],p[2]).project(camera);if(Math.abs(v.x)>0.98||Math.abs(v.y)>0.98||v.z>1)continue;
      const X=Math.round((v.x+1)/2*W),Y=Math.round((v.y+1)/2*H);if(Math.hypot(ex-X,ey-Y)<2)continue;px.push([X,Y]);x0=Math.min(x0,X);x1=Math.max(x1,X);y0=Math.min(y0,Y);y1=Math.max(y1,Y);}
    if(!px.length){out.push(null);continue;}
    const w=x1-x0+1,h=y1-y0+1,A=new Uint8Array(w*h*4),B=new Uint8Array(w*h*4);
    sc.visible=true;renderer.render(scene,camera);gl.readPixels(x0,y0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,A);
    sc.visible=false;renderer.render(scene,camera);gl.readPixels(x0,y0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,B);sc.visible=true;
    let sum=0,bad=0,n=0;for(const [X,Y] of px){const i=((Y-y0)*w+(X-x0))*4,off=lum(B,i),dk=(off-lum(A,i))/Math.max(off,1);
      if(dk<0.3){rc.setFromCamera({x:(X+0.5)/W*2-1,y:(Y+0.5)/H*2-1},camera);const h=rc.intersectObjects(scene.children,true).find(h=>h.object.visible);
        if(h&&!flat(h.object))continue;bad++;}
      sum+=dk;n++;}
    out.push({dark:sum/Math.max(n,1),speckle:bad/Math.max(n,1),n:n,pxR:(x1-x0)/2});}
  for(const o of hid)o.visible=true;camera.fov=fov0;camera.updateProjectionMatrix();
  return out;}"""

VIEWS = [('chase 25 m', 25, 0.2, 62), ('mid 300 m', 300, 0.12, 30), ('far 1.2 km', 1200, 0.1, 12), ('far 2.5 km', 2500, 0.08, 8)]

async def check_site(pg, label, c, azs=(0.6, 3.6)):
    s = await pg.evaluate(SIT, c)
    ok(f'{label}: scorch found', s is not None, s)
    if not s: return
    ok(f'{label}: no vertex under the terrain mesh', s['lo'] >= s['lift'] - 0.005, f"min {s['lo']:.3f} m, lift {s['lift']:.3f} m")
    ok(f'{label}: nothing floats (every vertex within 0.35 m of lift)', s['hi'] <= s['lift'] + 0.35, f"max {s['hi']:.3f} m, r {s['r']:.1f} m, {s['n']} verts")
    for name, dist, el, fov in VIEWS:
        for az in azs:
            r = await pg.evaluate(MEASURE, {**c, 'dist': dist, 'el': el, 'fov': fov, 'az': az, 'frames': 6})
            fr = [f for f in (r or []) if f]
            if not fr: ok(f'{label} {name} az {az}: scorch on screen', False, r); continue
            dk = [f['dark'] for f in fr]; sp = max(f['speckle'] for f in fr)
            ok(f'{label} {name} az {az}: dark and steady, no speckle', min(dk) > 0.3 and max(dk) - min(dk) < 0.03 and sp == 0,
               f"dark {min(dk):.3f}..{max(dk):.3f}, speckle {sp:.3f}, {fr[0]['n']} samples, r {fr[0]['pxR']:.0f} px")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);}}")
        await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('runway');}}")
        await step(pg, 0.2)
        ok('f16 climbed to ~150 ft', await climb(pg))
        ok('crash', await pg.evaluate(f"()=>{K}.crashNow('Scorch test crash.')"))
        await step(pg, 4.0)
        c = await pg.evaluate(f"()=>{{const s={K}.fxScorch();return s.length?{{x:s[0].position.x,z:s[0].position.z}}:null}}")
        ok('the crash left a scorch', c is not None)
        if c: await check_site(pg, 'crash (flat)', c)
        # a slope inside the terrain mesh: the steepest spot sampled on the White Tanks' east face
        sl = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();let best=null;
          for(let x=-19500;x<=-15500;x+=250)for(let z=-9000;z<=-3000;z+=250){if(Math.hypot(x-s.pos.x,z-s.pos.z)>28000)continue;
            const g=Math.hypot(K.terrainMeshH(x+5,z)-K.terrainMeshH(x-5,z),K.terrainMeshH(x,z+5)-K.terrainMeshH(x,z-5))/10;
            if(!best||g>best.g)best={x:x+37,z:z+53,g:g,az:Math.atan2(-(K.terrainMeshH(x,z+5)-K.terrainMeshH(x,z-5)),-(K.terrainMeshH(x+5,z)-K.terrainMeshH(x-5,z)))};}
          K.explode(best.x,K.groundHeight(best.x,best.z),best.z,{scale:1.6,smokeSec:20});return best;}""")
        ok('found a slope over 8%', sl['g'] > 0.08, f"{sl['g']*100:.0f}% at {sl['x']:.0f},{sl['z']:.0f}")
        await step(pg, 3.0)
        # the camera on the downhill side, looking up the face (uphill the ridge hides it)
        await check_site(pg, f"slope {sl['g']*100:.0f}%", sl, (round(sl['az'] - 0.5, 2), round(sl['az'] + 0.5, 2)))
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('scorch_check'))

if __name__ == '__main__':
    asyncio.run(main())
