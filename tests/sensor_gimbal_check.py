# sensor item 2: the MTS-B gimbal. Continuous azimuth (straight behind), elevation +40 to -135 through straight down
# without a flip, the inertially held line of sight while the aircraft turns, the thumb rate scaled by the field of
# view and smoothed in and out, slew to nose, the airframe masking the view aft, the turret hidden in the sensor view.
# Usage: .venv/bin/python tests/sensor_gimbal_check.py [--type reaper|mq9b]
import asyncio, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

TYPE = sys.argv[sys.argv.index('--type') + 1] if '--type' in sys.argv else 'reaper'
K = 'window.__kgeu'
PLACE = """()=>{const K=window.__kgeu,s=K.state();const x=-7679-6000,z=-1855+4000,hdg=0.3,V=80;
  s.pos.set(x,4570+K.groundHeight(x,z),z);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);
  s.quat.setFromEuler(new THREE.Euler(0,-hdg,0,'YXZ'));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.snapCam();K.stepFrame(1/60,false,true);
  while(K.camMode()!==2)K.cycleCam();K.stepFrame(1/60,false,true);return K.sensorMode();}"""
# hold the aircraft still between frames (the orbit autopilot would turn it): the test turns it by hand
FREEZE = """()=>{const K=window.__kgeu,s=K.state();window.__q0=s.quat.clone();window.__p0=s.pos.clone();
  window.__slewPre=()=>{s.quat.copy(window.__q0);s.pos.copy(window.__p0);s.vel.set(0,0,0);s.w.set(0,0,0);};}"""
STEP = """(n)=>{const K=window.__kgeu,s=K.state();for(let i=0;i<n;i++){s.quat.copy(window.__q0);s.pos.copy(window.__p0);s.vel.set(0,0,0);s.w.set(0,0,0);K.stepFrame(1/60,false,true);}return K.sensor();}"""
SET = """([az,el])=>{const K=window.__kgeu,S=K.SENSOR;S.tgt=null;S.track=null;S.geo=null;S.slewTo=null;S.rx=S.ry=0;S.az=az*Math.PI/180;S.el=el*Math.PI/180;return true;}"""
CAMDIR = """()=>{const K=window.__kgeu,c=K.R3().camera,v=new THREE.Vector3();c.getWorldDirection(v);
  const f=new THREE.Vector3(0,0,-1).applyQuaternion(K.state().quat),u=new THREE.Vector3(0,1,0).applyQuaternion(K.state().quat);return {fwd:v.dot(f),up:v.dot(u)};}"""


async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('{TYPE}');K.pickBase('luke');K.start('final');}}")
        await pg.wait_for_timeout(500)
        c('sensor view up in flight', await pg.evaluate(PLACE))
        await pg.evaluate(FREEZE)
        # 1. straight behind
        await pg.evaluate(SET, [180, -5]); s = await pg.evaluate(STEP, 3); d = await pg.evaluate(CAMDIR)
        c('az 180: the ball holds straight behind', abs(abs(s['az']) - 180) < 0.5, s['az'])
        c('az 180: the camera looks aft', d['fwd'] < -0.95, d)
        await pg.evaluate(SET, [-150, -20]); s = await pg.evaluate(STEP, 3)
        c('az -150 held (no stop at the old 149 degree limit)', abs(s['az'] + 150) < 0.5, s['az'])
        # 2. elevation limits and through straight down
        await pg.evaluate(SET, [0, 60]); s = await pg.evaluate(STEP, 2)
        c('el above +40 holds at +40', abs(s['el'] - 40) < 0.2, s['el'])
        await pg.evaluate(SET, [30, -80]); await pg.evaluate(STEP, 1)
        els, azs = [], []
        for _ in range(12):
            s = await pg.evaluate(f"()=>{K}.slewHold(0,1,6,1/60)")   # thumb pulled back: down and on past straight down
            await pg.evaluate("()=>{const s=window.__kgeu.state();s.quat.copy(window.__q0);s.pos.copy(window.__p0);}")
            els.append(s['el']); azs.append(s['az'])
        mono = all(els[i + 1] <= els[i] + 0.05 for i in range(len(els) - 1))
        c('thumb down passes straight down without a flip', mono and min(els) < -95, [round(e, 1) for e in els])
        c('azimuth stays put through straight down', max(abs(((a - 30 + 180) % 360) - 180) for a in azs) < 2, [round(a, 1) for a in azs])
        await pg.evaluate(SET, [30, -130]); s = await pg.evaluate(f"()=>{K}.slewHold(0,1,60,1/60)")
        c('el stops at -135', abs(s['el'] + 135) < 0.3, s['el'])
        # 3. inertial hold: the aircraft yaws 10 degrees, the line of sight does not move
        await pg.evaluate(SET, [40, -30]); s0 = await pg.evaluate(STEP, 5)
        await pg.evaluate("()=>{const q=window.__q0;q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),0.1745));}")
        s1 = await pg.evaluate(STEP, 3)
        dot = sum(a * b2 for a, b2 in zip(s0['los'], s1['los']))
        c('aircraft turns 10 degrees: the line of sight holds', dot > 0.99999, dot)
        c('... and the gimbal azimuth takes the turn', abs((s1['az'] - s0['az']) - 10) < 0.6, (s0['az'], s1['az']))
        await pg.evaluate("()=>{const q=window.__q0;q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),0.35));}")
        s2 = await pg.evaluate(STEP, 3)
        dot = sum(a * b2 for a, b2 in zip(s1['los'], s2['los']))
        c('aircraft banks 20 degrees: the line of sight holds', dot > 0.99999, dot)
        await pg.evaluate("()=>{window.__q0.copy(window.__kgeu.state().quat);}")
        # 4. rate by field of view, smoothed
        rates = []
        for zi in (0, 2):
            await pg.evaluate(f"()=>{{{K}.SENSOR.zoom={zi};}}"); await pg.evaluate(SET, [0, -40]); await pg.evaluate(STEP, 2)
            a0 = await pg.evaluate(f"()=>{K}.sensor()")
            a1 = await pg.evaluate(f"()=>{K}.slewHold(1,0,60,1/60)")
            fov = a0['fov']; rates.append(((a1['az'] - a0['az'] + 540) % 360 - 180, fov))
        r0, r2 = rates[0][0] / rates[0][1], rates[1][0] / rates[1][1]
        c('full thumb for 1 s moves about the same number of fields of view wide and narrow', 0.8 < r2 / r0 < 1.25 and rates[0][0] > rates[1][0] * 2, rates)
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=0;}}"); await pg.evaluate(SET, [0, -40]); await pg.evaluate(STEP, 1)
        a = await pg.evaluate(f"()=>{K}.slewHold(1,0,2,1/60)")
        b2 = await pg.evaluate(f"()=>{K}.slewHold(1,0,30,1/60)")
        c('rate builds up (not a jump): 2 frames in under 40 percent', 0 < a['rx'] < 0.4 and b2['rx'] > 0.9, (a['rx'], b2['rx']))
        e1 = await pg.evaluate(STEP, 3); e2 = await pg.evaluate(STEP, 40)
        c('released: it settles (a short glide, then still)', 0 < e1['rx'] < 0.7 and e2['rx'] == 0, (e1['rx'], e2['rx']))
        e3 = await pg.evaluate(STEP, 20)
        c('still means still: no drift with the thumb off', abs(e3['az'] - e2['az']) < 0.01 and abs(e3['el'] - e2['el']) < 0.01, (e2['az'], e3['az']))
        a = await pg.evaluate(f"()=>{K}.slewHold(0.03,0,30,1/60)")
        c('a resting thumb (3 percent) does not creep', abs(a['az'] - e3['az']) < 0.01, a['az'])
        # 5. slew to nose
        await pg.evaluate(SET, [150, -60]); await pg.evaluate(STEP, 1)
        await pg.evaluate(f"()=>{K}.sensorNose()"); s = await pg.evaluate(STEP, 60)
        c('NOSE: back to az 0, el -15 in a second', abs(s['az']) < 0.3 and abs(s['el'] + 15) < 0.3, (s['az'], s['el']))
        # 6. masking
        await pg.evaluate(SET, [180, -2]); s = await pg.evaluate(STEP, 8)
        c('straight behind, level: the airframe masks', s['mask'], s['mask'])
        await pg.evaluate(SET, [20, -45]); s = await pg.evaluate(STEP, 8)
        c('ahead and down: clear', not s['mask'])
        await pg.evaluate(SET, [90, -40]); s = await pg.evaluate(STEP, 8)
        c('abeam and down: clear', not s['mask'])
        await pg.evaluate(SET, [120, 15]); s = await pg.evaluate(STEP, 8)
        c('aft and up under the wing: masked', s['mask'])
        vis = await pg.evaluate(f"()=>{{const g={K}.plane().g;let n=0,v=0;g.traverse(o=>{{if(o.userData.turret){{n++;if(o.visible)v++;}}}});return [n,v];}}")
        c('turret meshes tagged and hidden in the sensor view', vis[0] == 3 and vis[1] == 0, vis)
        # 7. a track breaks when the airframe masks it
        await pg.evaluate(SET, [60, -30]); await pg.evaluate(STEP, 2)
        await pg.evaluate(f"()=>{K}.trackHere()"); s0 = await pg.evaluate(f"()=>{K}.sensor()"); s = await pg.evaluate(STEP, 2)
        c('area track on', s['kind'] == 'ar', (s0['kind'], s['kind'], s['cue'], s0['valid'], s0['az'], s0['el']))
        await pg.evaluate("()=>{const q=window.__q0;q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),2.0));}")
        # the aircraft swings round so the spot sits aft and slightly up: masked (the nose pitched up hard too)
        await pg.evaluate("()=>{const q=window.__q0;q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),0.85));}")
        s = await pg.evaluate(STEP, 40)
        c('masked track breaks with the MASK cue', s['kind'] == '' and s['cue'] == 'MASK', (s['kind'], s['cue'], s['mask'], s['az'], s['el']))
        if pg.errs: c('no console errors', False, pg.errs[:3])
        await b.close()
    srv.shutdown(); c.done('sensor_gimbal_check')

asyncio.run(main())
