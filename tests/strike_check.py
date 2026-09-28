# Reaper strike checks. Run from project root: .venv/bin/python tests/strike_check.py
# Verifies where the range sits against the real terrain and city section map, then flies
# a full engagement: track, fire, impact, score.
import asyncio, os, sys, math
from playwright.async_api import async_playwright
THREE = open('node_modules/three/build/three.min.js').read()
URL = 'file://' + os.path.abspath('index.html')
fails = []
WALK_OFF = ('([x,z])=>{const S=window.__kgeu.SENSOR;const V=S.spot.constructor;'
            'S.tgt=null;S.track=new V(x+300,S.spot.y,z+180);}')
RES2 = ('()=>({hits:window.__kgeu.STRIKE.hits,shots:window.__kgeu.STRIKE.shots,'
        'dead:window.__kgeu.STRIKE.targets.filter(t=>t.dead).length})')

def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (('  ' + detail) if detail else ''))
    if not cond: fails.append(name)

async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    ctx = await b.new_context(viewport={'width':932,'height':430}, has_touch=True, is_mobile=True)
    pg = await ctx.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2200)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)

    # ---------- siting ----------
    site = await pg.evaluate("""()=>{
      const K=window.__kgeu,R=K.RANGE,out={r:R.r};
      // flat? sample the whole range footprint
      let hmin=1e9,hmax=-1e9;
      for(let i=0;i<24;i++)for(let j=0;j<8;j++){
        const a=i/24*Math.PI*2, d=j/7*R.r;
        const h=K.groundHeight(R.x+Math.cos(a)*d, R.z+Math.sin(a)*d);
        hmin=Math.min(hmin,h);hmax=Math.max(hmax,h);}
      out.relief=hmax-hmin;
      // nearest built-up section from the real section map, and nearest paved surface
      let nearCity=1e9, kinds={};
      for(let dx=-12000;dx<=12000;dx+=400)for(let dz=-12000;dz<=12000;dz+=400){
        const x=R.x+dx,z=R.z+dz,t=K.secAt(x,z);
        kinds[t]=1;
        if(t==='sub'||t==='near'||t==='farm'||t==='airport'||t==='luke'||t==='stadium'){
          nearCity=Math.min(nearCity,Math.hypot(dx,dz)-R.r);}
        if(K.isPaved(x,z))nearCity=Math.min(nearCity,Math.hypot(dx,dz)-R.r);}
      out.nearCity=nearCity;
      out.hereType=K.secAt(R.x,R.z);
      // freeways, river, airport, Luke
      out.fwy=Math.abs(R.x-K.FWY_X)-R.r;
      out.i10=Math.abs(R.z-K.I10_Z)-R.r;
      out.river=Math.abs(R.x-K.riverX(R.z))-R.r;
      out.apt=Math.hypot(R.x-K.APC.x,R.z-K.APC.z)-R.r;
      out.luke=Math.hypot(R.x-K.LUKE.x,R.z-K.LUKE.z)-R.r;
      out.sw=(R.x<K.APC.x)&&(R.z>K.APC.z);
      return out;}""")
    print('  range siting:', {k:(round(v,1) if isinstance(v,(int,float)) else v) for k,v in site.items()})
    chk('range is southwest of KGEU', site['sw'])
    chk('range ground is flat', site['relief'] < 3.0, f"{site['relief']:.2f} m of relief")
    chk('range sits on open desert', site['hereType'] in ('none','desert'), site['hereType'])
    chk('over 3 km from any city, houses or pavement', site['nearCity'] > 3000, f"{site['nearCity']:.0f} m")
    chk('over 3 km from the 101 freeway', site['fwy'] > 3000, f"{site['fwy']:.0f} m")
    chk('over 3 km from the I-10 freeway', site['i10'] > 3000, f"{site['i10']:.0f} m")
    chk('over 3 km from the river', site['river'] > 3000, f"{site['river']:.0f} m")
    chk('over 3 km from the airport', site['apt'] > 3000, f"{site['apt']:.0f} m")
    chk('over 3 km from Luke AFB', site['luke'] > 3000, f"{site['luke']:.0f} m")

    # ---------- start the mode ----------
    await pg.evaluate("()=>window.__kgeu.mission('range')"); await pg.wait_for_timeout(1500)
    info = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();
      return {active:K.STRIKE.active,n:K.STRIKE.targets.length,
        kinds:K.STRIKE.targets.map(t=>t.kind).sort().join(','),
        moving:K.STRIKE.targets.filter(t=>t.moving).length,
        ap:s.ap?s.ap.mode:null, cam:K.camMode(), sensor:K.sensorMode(),
        altFt:Math.round(s.pos.y*3.28084+1071), pylons:K.pylonsVisible()};}""")
    print('  start:', info)
    chk('strike mode active', info['active'])
    chk('seven targets: 3 trucks, 2 hulls, 1 bunker, 1 mover',
        info['n']==7 and info['kinds']=='bunker,hull,hull,truck,truck,truck,truck' and info['moving']==1,
        f"{info['n']} {info['kinds']} moving={info['moving']}")
    chk('starts in the orbit autopilot', info['ap']=='orbit', str(info['ap']))
    chk('starts in the sensor ball', info['cam']==2 and info['sensor'])
    chk('starts near 7,000 ft MSL', abs(info['altFt']-7000)<400, f"{info['altFt']} ft")
    chk('four stores on the pylons', info['pylons']==[True]*4, str(info['pylons']))

    # the moving truck actually drives the loop
    a0 = await pg.evaluate("()=>{const t=window.__kgeu.STRIKE.targets.find(t=>t.moving);return [t.x,t.z];}")
    await pg.wait_for_timeout(1500)
    a1 = await pg.evaluate("()=>{const t=window.__kgeu.STRIKE.targets.find(t=>t.moving);return [t.x,t.z];}")
    chk('the mover drives the loop road', math.hypot(a1[0]-a0[0], a1[1]-a0[1]) > 3,
        f"{math.hypot(a1[0]-a0[0], a1[1]-a0[1]):.1f} m")

    # ---------- track and shoot the bunker ----------
    idx = await pg.evaluate("()=>window.__kgeu.STRIKE.targets.findIndex(t=>t.kind==='bunker')")
    ok = await pg.evaluate("(i)=>window.__kgeu.pointAt(i)", idx)
    await pg.wait_for_timeout(120)
    await pg.evaluate("()=>window.__kgeu.trackHere()")
    lock = await pg.evaluate("""()=>{const S=window.__kgeu.SENSOR;
      return {tgt:S.tgt?S.tgt.kind:null, slant:Math.round(S.slant), valid:S.valid};}""")
    chk('locks the bunker under the crosshair', lock['tgt']=='bunker', str(lock))
    chk('slant range is in the firing window', 700 <= lock['slant'] <= 8200, f"{lock['slant']} m")
    await pg.wait_for_timeout(100)
    txt = await pg.inner_text('#sensorHud')
    chk('sensor display shows lock, slant and IN RANGE',
        'LOCK' in txt and 'SLANT' in txt and 'IN RANGE' in txt, repr(txt.replace('\n',' | ')[:110]))

    await pg.evaluate("()=>window.__kgeu.fire()")
    await pg.wait_for_timeout(400)
    fired = await pg.evaluate("""()=>({shots:window.__kgeu.STRIKE.shots,
      inflight:window.__kgeu.STRIKE.missiles.length,pylons:window.__kgeu.pylonsVisible()})""")
    chk('one missile away', fired['shots']==1 and fired['inflight']==1, str(fired))
    await pg.wait_for_timeout(900)
    chk('the fired pylon store is hidden',
        (await pg.evaluate("()=>window.__kgeu.pylonsVisible()")).count(False)==1,
        str(await pg.evaluate("()=>window.__kgeu.pylonsVisible()")))
    smax = await pg.evaluate("()=>window.__kgeu.smokeMax")
    chk('smoke pool is capped at 60', smax==60, str(smax))

    # hold the laser on until it hits
    for _ in range(140):
        if await pg.evaluate("()=>window.__kgeu.STRIKE.missiles.length")==0: break
        await pg.wait_for_timeout(250)
    res = await pg.evaluate("""()=>({hits:window.__kgeu.STRIKE.hits,
      dead:window.__kgeu.STRIKE.targets.filter(t=>t.dead).map(t=>t.kind),
      live:window.__kgeu.STRIKE.missiles.length,
      smoke:window.__kgeu.smokeCount()})""")
    chk('holding the laser scores a hit', res['hits']==1 and 'bunker' in res['dead'], str(res))
    chk('smoke never exceeds the pool', res['smoke'] <= 60, str(res['smoke']))
    tt = await pg.inner_text('#toast')
    chk('result is reported', 'hit' in tt.lower() or 'miss' in tt.lower(), repr(tt))

    # ---------- laser walks off, then the track breaks: missile follows the last spot ----------
    idx2 = await pg.evaluate("()=>window.__kgeu.STRIKE.targets.findIndex(t=>t.kind==='hull'&&!t.dead)")
    await pg.evaluate("(i)=>window.__kgeu.pointAt(i)", idx2)
    await pg.wait_for_timeout(120)
    await pg.evaluate("()=>window.__kgeu.trackHere()")
    tpos = await pg.evaluate("(i)=>{const t=window.__kgeu.STRIKE.targets[i];return [t.x,t.z];}", idx2)
    await pg.evaluate("()=>window.__kgeu.fire()")
    await pg.wait_for_timeout(1500)
    # walk the laser 300 m off the target, let the missile take that spot, then drop the track
    await pg.evaluate(WALK_OFF, tpos)
    await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>{const S=window.__kgeu.SENSOR;S.tgt=null;S.track=null;}")
    for _ in range(140):
        if await pg.evaluate("()=>window.__kgeu.STRIKE.missiles.length")==0: break
        await pg.wait_for_timeout(250)
    res2 = await pg.evaluate(RES2)
    chk('laser walked off before the break, so the shot misses',
        res2['hits']==1 and res2['shots']==2 and res2['dead']==1, str(res2))
    tt2 = await pg.inner_text('#toast')
    chk('the miss is reported with a distance', 'Miss by' in tt2, repr(tt2))

    # ---------- score after four shots ----------
    for _ in range(2):
        await pg.evaluate("""()=>{const K=window.__kgeu,S=K.SENSOR;
          const i=K.STRIKE.targets.findIndex(t=>!t.dead);K.pointAt(i);}""")
        await pg.wait_for_timeout(120)
        await pg.evaluate("()=>window.__kgeu.trackHere()")
        await pg.evaluate("()=>window.__kgeu.fire()")
        for _ in range(140):
            if await pg.evaluate("()=>window.__kgeu.STRIKE.missiles.length")==0: break
            await pg.wait_for_timeout(250)
    fin = await pg.evaluate("""()=>({shots:window.__kgeu.STRIKE.shots,hits:window.__kgeu.STRIKE.hits,
      cleared:window.__kgeu.STRIKE.cleared,
      best:JSON.parse(localStorage.getItem('kgeuStrikeBest')||'null'),
      pylons:window.__kgeu.pylonsVisible()})""")
    print('  final:', fin)
    chk('four shots empties the rails', fin['shots']==4 and fin['pylons']==[False]*4, str(fin['pylons']))
    chk('the engagement scores out', fin['cleared'])
    chk('best score is saved to localStorage',
        fin['best'] is not None and 'hits' in fin['best'] and 'avg' in fin['best'] and 't' in fin['best'],
        str(fin['best']))
    chk('firing with empty rails is refused',
        (await pg.evaluate("()=>{window.__kgeu.fire();return window.__kgeu.STRIKE.shots;}"))==4)

    # ZOOM sits with FIRE and LOCK in the button dock, only in sensor mode
    zvis = await pg.evaluate("()=>{const b=document.getElementById('bZoom');return !b.hidden&&b.offsetParent!==null}")
    chk('zoom button is offered in sensor mode', zvis)
    chk('FIRE is offered during the strike', await pg.evaluate("()=>document.getElementById('bFire').offsetParent!==null"))
    if zvis:
        z0 = await pg.evaluate("()=>window.__kgeu.SENSOR.zoom")
        await pg.evaluate("()=>document.getElementById('bZoom').click()"); await pg.wait_for_timeout(250)
        z1 = await pg.evaluate("()=>window.__kgeu.SENSOR.zoom")
        chk('zoom steps in', z0 != z1, f'{z0} -> {z1}')
        chk('the second field is selected', z1 == 1, str(z1))

    await pg.screenshot(path='tests/shot_strike.png')
    chk('no page errors', not errs, str(errs[:2]))
    await b.close()

asyncio.run(main())
print('\nstrike_check: ' + ('FAILED ' + ', '.join(fails) if fails else 'all checks passed'))
sys.exit(1 if fails else 0)
