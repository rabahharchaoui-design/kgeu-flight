# Item 9: nose wheel steering works whenever the wheels are on the ground and rolling.
# For each aircraft, in Hard and Easy: on runway 1 at idle, set the ground roll to about
# 2, 5 and 15 kt, hold full left then full right stick for a few seconds and check the
# heading swings the right way by a useful amount. At a standstill the nose must not
# pivot. Airborne and nearly stopped (Hard), the stick must not yaw the aircraft through
# the nose wheel (ground steering is a ground-only thing).
# Run: .venv/bin/python tests/steer_check.py [cessna f16 ...]
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()

TYPES = ['cessna', 'archer', 'alpha', 'reaper', 'mq9b', 'f16', 'c130']
if sys.argv[1:]: TYPES = sys.argv[1:]
SPEEDS = [(2, 2.0, 8), (5, 2.5, 15), (15, 2.5, 20)]    # kt, seconds held, minimum heading change in degrees
MODES = [('Hard', 'pilot'), ('Easy', 'rookie')]

# put the aircraft on runway 1 at idle rolling at kt, no wind, then hold the stick at ail for sec
ROLL = """([kt,ail,sec])=>{const K=window.__kgeu;K.start('runway');const s=K.state(),T=THREE;
  s.windKt=0;s.gustAmp=0;s.throttle=s.power=0;s.brake=false;s.ap=null;s.apW=null;s.w.set(0,0,0);
  const f=new T.Vector3(0,0,-1).applyQuaternion(s.quat);f.y=0;f.normalize();const V=kt/1.94384;
  s.vel.set(f.x*V,0,f.z*V);K.touchIn.active=true;K.touchIn.elev=0;K.touchIn.ail=ail;
  const e=new T.Euler(0,0,0,'YXZ'),hdg=()=>{e.setFromQuaternion(s.quat,'YXZ');return -e.y;};
  let h0=hdg(),tot=0;const n=Math.round(sec*60);
  for(let i=0;i<n;i++){K.stepFrame(1/60,false,true);const h=hdg();tot+=Math.atan2(Math.sin(h-h0),Math.cos(h-h0));h0=h;if(s.crashed)break;}
  K.touchIn.active=false;K.touchIn.ail=0;
  return {deg:tot*180/Math.PI,kt:Math.hypot(s.vel.x,s.vel.z)*1.94384,ground:s.onGround,crashed:s.crashed?s.crashReason:''};}"""

# airborne at 3000 m, barely moving: the nose wheel must do nothing
AIR = """([ail])=>{const K=window.__kgeu;K.start('runway');const s=K.state(),T=THREE;
  s.windKt=0;s.gustAmp=0;s.pos.y=3000+K.groundHeight(s.pos.x,s.pos.z);s.onGround=false;s.airTime=30;s.throttle=s.power=0;
  const f=new T.Vector3(0,0,-1).applyQuaternion(s.quat);s.vel.set(f.x*2,0,f.z*2);s.w.set(0,0,0);
  K.touchIn.active=true;K.touchIn.elev=0;K.touchIn.ail=ail;
  const e=new T.Euler(0,0,0,'YXZ'),hdg=()=>{e.setFromQuaternion(s.quat,'YXZ');return -e.y;};
  let h0=hdg(),tot=0;for(let i=0;i<30;i++){K.stepFrame(1/60,false,true);const h=hdg();tot+=Math.atan2(Math.sin(h-h0),Math.cos(h-h0));h0=h;}
  K.touchIn.active=false;K.touchIn.ail=0;return {deg:tot*180/Math.PI,ground:s.onGround};}"""

async def main():
    srv, url = serve()
    table = []
    async with async_playwright() as p:
        b = await launch(p)
        for mname, skill in MODES:
            for t in TYPES:
                pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuType': t, 'kgeuTut': '1', 'kgeuCoach': '3'})
                await pg.evaluate(f"()=>{{const K=window.__kgeu;K.pick('{t}');K.pickBase('kgeu');K.start('runway');}}")
                await pg.wait_for_timeout(400)
                row = [f'{mname:4} {t:6}']
                for kt, sec, need in SPEEDS:
                    L = await pg.evaluate(ROLL, [kt, -1.0, sec])
                    R = await pg.evaluate(ROLL, [kt, 1.0, sec])
                    # stick left turns the nose left: heading decreases
                    ok(f'{mname} {t} {kt} kt: left stick turns left', L['ground'] and not L['crashed'] and L['deg'] < -need,
                       f"{L['deg']:+.1f} deg, ends {L['kt']:.1f} kt {L['crashed']}")
                    ok(f'{mname} {t} {kt} kt: right stick turns right', R['ground'] and not R['crashed'] and R['deg'] > need,
                       f"{R['deg']:+.1f} deg, ends {R['kt']:.1f} kt {R['crashed']}")
                    row.append(f"{kt:>2}kt {L['deg']/sec:+6.1f}/{R['deg']/sec:+6.1f} deg/s")
                Z = await pg.evaluate(ROLL, [0, 1.0, 2.0])
                ok(f'{mname} {t} 0 kt: no pivot in place', abs(Z['deg']) < 0.5, f"{Z['deg']:+.2f} deg")
                # Hard only: in Easy the stick commands a bank and Easy Flight turns the aircraft itself
                if skill == 'pilot':
                    A = await pg.evaluate(AIR, [1.0])
                    ok(f'{mname} {t} airborne: no nose wheel yaw', not A['ground'] and abs(A['deg']) < 0.5, f"{A['deg']:+.2f} deg")
                table.append('  '.join(row))
                await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
                ok(f'{mname} {t} no console errors', not pg.errs, pg.errs[:3])
                await pg.context.close()
        await b.close()
    print('\nturn rate left/right (deg/s):')
    for r in table: print('  ' + r)
    srv.shutdown()
    sys.exit(ok.done('steer_check'))

asyncio.run(main())
