# Drop zone guidance for the C-130 airdrop (session "dz"). Easy and Hard, day, night and
# inside a haboob: the DZ icon, waypoint and route; "Head for the red smoke" on screen and
# once on the radio; the red smoke column leaning downwind (red flares with a glow at
# night); the orange letter; the run in line and gates (Easy only); the floating marker and
# edge chevron (Easy only); a flown run in with the one minute, ten seconds, red and green
# jump lights, a real drop on green and the distance in the result card.
# Run: .venv/bin/python tests/dz_check.py [--shots]
import asyncio, math, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15, ROOT
ok = Checks()
K = "window.__kgeu"
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'dz')
SAVE = '--shots' in sys.argv

async def shot(pg, name):
    if SAVE:
        os.makedirs(SHOTS, exist_ok=True)
        await pg.evaluate(f"()=>{K}.stepFrame(1/60)"); await pg.wait_for_timeout(250)
        await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))

STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/30,false,true)}"

async def state(pg):
    return await pg.evaluate(f"""()=>{{const D={K}.DZ,dz={K}.DROPZ,sm=D.smoke.filter(s=>s.visible&&s.material.opacity>0.05);
      const top=D.smoke.reduce((a,s)=>s.position.y>a.position.y?s:a,D.smoke[0]);
      const c=sm.length?sm[0].material.color:null,wd={K}.state().windDir*Math.PI/180;
      return {{dest:{K}.dest(),hint:document.getElementById('dzHint').classList.contains('on'),smoke:sm.length,
        red:c?c.r>c.g*3&&c.r>c.b*3:false,lean:(top.position.x-dz.x)*(-Math.sin(wd))+(top.position.z-dz.z)*Math.cos(wd),topY:top.position.y,
        flares:D.flares.filter(f=>f.visible).length,glow:D.glow.visible,line:D.runG.visible,gates:D.gates.filter(g=>g.visible).length,
        mark:document.getElementById('dzMark').classList.contains('on'),arrow:document.getElementById('dzArrow').classList.contains('on'),
        letter:D.letter.count,wind:{K}.state().windKt}}}}""")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('rookie', 'pilot'):
            M = 'Easy' if skill == 'rookie' else 'Hard'
            for tod in ('day', 'night', 'haboob'):
                pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuTut': '1'})
                await pg.evaluate(f"()=>{{{K}.setTOD('{tod}');{K}.radioLog(true);{K}.mission('drop')}}")
                await pg.evaluate(STEP, 60)
                if tod == 'haboob':   # put the dust over the run in
                    await pg.evaluate(f"()=>{K}.haboobJump(-1500)"); await pg.evaluate(STEP, 30)
                s = await state(pg)
                tag = f'{M} {tod}'
                if skill == 'rookie':
                    ok(f'{tag}: waypoint and route set to the drop zone', s['dest'] and s['dest'].get('name') == 'Drop zone', s['dest'])
                else:
                    ok(f'{tag}: no route in Hard, only the map marker', s['dest'] is None, s['dest'])
                ok(f'{tag}: "Head for the red smoke" on screen', s['hint'])
                log = await pg.evaluate(f"()=>{K}.radioLog().concat({K}.radioQ()).filter(l=>/red smoke/.test(l.text)).length")
                ok(f'{tag}: the radio says it once', log == 1, log)
                ok(f'{tag}: a tall red smoke column', s['smoke'] >= 15 and s['red'] and s['topY'] > 600, (s['smoke'], s['red'], round(s['topY'])))
                ok(f'{tag}: it leans downwind so it shows the wind', s['wind'] < 3 or s['lean'] > 20, round(s['lean']))
                ok(f'{tag}: orange letter panels on the DZ', s['letter'] >= 20, s['letter'])
                if tod == 'night':
                    ok(f'{tag}: red flares with a glow', s['flares'] == 6 and s['glow'], (s['flares'], s['glow']))
                else:
                    ok(f'{tag}: no flares by day', s['flares'] == 0 and not s['glow'])
                ok(f'{tag}: run in line and gates ' + ('shown' if skill == 'rookie' else 'hidden'),
                   (s['line'] and s['gates'] == 6) if skill == 'rookie' else (not s['line'] and s['gates'] == 0), (s['line'], s['gates']))
                ok(f'{tag}: floating marker or edge chevron ' + ('shown' if skill == 'rookie' else 'hidden'),
                   (s['mark'] or s['arrow']) if skill == 'rookie' else not (s['mark'] or s['arrow']), (s['mark'], s['arrow']))
                await shot(pg, f'{skill}_{tod}_start')
                # look away: Easy gets the edge chevron
                if skill == 'rookie' and tod == 'day':
                    await pg.evaluate(f"()=>{{const s={K}.state();s.quat.setFromEuler(new THREE.Euler(0,Math.PI,0,'YXZ'));s.vel.set(0,0,-60);}}")
                    await pg.evaluate(STEP, 60); s2 = await state(pg)   # the chase camera takes a moment to come round
                    ok('Easy: turned away, the edge chevron points to the DZ', s2['arrow'] and not s2['mark'], s2)
                    await shot(pg, 'rookie_chevron')
                # fly the ideal run in: 3 miles out on the line, into the wind, 1,000 ft, 140 kt
                PLACE = f"""()=>{{const K={K},D=K.DZ,s=K.state(),f=D.f,x=D.rel.x-f.x*4828,z=D.rel.z-f.z*4828,gh=K.groundHeight?K.groundHeight(x,z):0;
                  const V=140/1.94384;s.pos.set(x,(gh||0)+305+2,z);s.vel.set(f.x*V,0,f.z*V);s.quat.setFromEuler(new THREE.Euler(0.03,-Math.atan2(f.x,-f.z),0,'YXZ'));
                  s.w.set(0,0,0);s.throttle=s.power=0.36;s.flapIdx=1;s.trim=0.5;s.airTime=30;s.onGround=false;s.gearDown=false;s.gearPos=0;s.ap=null;}}"""
                await pg.evaluate(PLACE)
                seen, green_t, dropped = set(), None, False
                for i in range(320):   # up to 160 s in half second slices: the run in, then the bundle's fall
                    # the test flies like a pilot: holds drop height and keeps to the current run in line
                    # (it moves with the wind), since the guidance is under test, not the piloting
                    await pg.evaluate(f"""()=>{{const K={K},s=K.state(),D=K.DZ;if(!K.MISS.dropped){{
                        const f=D.f,dx=s.pos.x-D.rel.x,dz=s.pos.z-D.rel.z,c=-dx*f.z+dz*f.x,sp=Math.hypot(s.vel.x,s.vel.z);
                        s.pos.x-=-f.z*c*0.5;s.pos.z-=f.x*c*0.5;s.vel.x=f.x*sp;s.vel.z=f.z*sp;
                        s.quat.setFromEuler(new THREE.Euler(new THREE.Euler().setFromQuaternion(s.quat,'YXZ').x,-Math.atan2(f.x,-f.z),0,'YXZ'));}}
                      for(let j=0;j<15;j++){{K.stepFrame(1/30,false,true);
                        if(!K.MISS.dropped){{const gh=K.groundHeight(s.pos.x,s.pos.z);s.pos.y+=(gh+305-s.pos.y)*0.05;}}}}}}""")
                    # the wind swung (leaving the haboob's dust) and the run in moved behind us: fly a fresh pass
                    # (or it swung so far the release point is already well behind us)
                    if not dropped and await pg.evaluate(f"()=>{K}.DZ.tRel>90&&{K}.DZ.tRel<1e8||{K}.DZ.tRel<-15&&{K}.DZ.err>1500"):
                        await pg.evaluate(PLACE)
                    st = await pg.evaluate(f"()=>({{l:{K}.DZ.light,t:{K}.DZ.tRel,jl:document.getElementById('jumpLt').className,pulse:document.getElementById('bDrop').classList.contains('jgreen'),dz:{K}.MISS.dropped}})")
                    if st['l']: seen.add(st['l'])
                    if os.environ.get('DZDBG') and i % 4 == 0: print('   ', tag, i, await pg.evaluate(f"()=>{{const D={K}.DZ,s={K}.state();return [Math.round(D.tRel),Math.round(D.err),Math.round(D.cross),{K}.MISS.armed,D.light,Math.round(s.agl*3.28),Math.round(s.ias*1.94),+s.gload.toFixed(2),Math.round(s.windDir),Math.round(s.windKt),{K}.MISS.dropped]}}"))
                    if st['l'] == 'red' and 'red' not in seen: pass
                    if st['l'] == 'green' and not dropped:
                        ok(f'{tag}: green light on screen and the DROP button pulses', 'green' in st['jl'] and st['pulse'], st)
                        if tod == 'day': await shot(pg, f'{skill}_green')
                        await pg.evaluate(f"()=>{K}.missDrop()"); dropped = True
                    if dropped and await pg.evaluate(f"()=>{K}.MISS.result!==null"): break
                calls = await pg.evaluate(f"()=>{K}.radioLog().concat({K}.radioQ()).filter(l=>l.who==='Loadmaster').map(l=>l.text)")
                if tod == 'haboob':   # the wind re-plan can move the release point through the one minute window
                    ok(f'{tag}: ten seconds, then green light', calls[-2:] == ['Ten seconds.', 'Green light, green light.'], calls)
                else:
                    ok(f'{tag}: one minute and ten seconds calls, then green light', calls[-3:] == ['One minute.', 'Ten seconds.', 'Green light, green light.'], calls)
                ok(f'{tag}: red light before green', 'red' in seen and 'green' in seen, seen)
                ok(f'{tag}: the route clears after the drop', await pg.evaluate(f"()=>{K}.dest()") is None)
                await pg.evaluate(STEP, 200)
                res = await pg.evaluate(f"()=>({{r:{K}.MISS.result,title:document.getElementById('mTitle').textContent}})")
                d = res['r'] and res['r']['dist']
                if tod == 'haboob':   # the wind under the canopy changes as the dust moves: no accuracy promise in a haboob
                    ok(f'{tag}: the drop on green is scored ({d and round(d)} m)', d is not None, res)
                else:
                    ok(f'{tag}: the bundle lands on the DZ on the green light ({d and round(d)} m)', d is not None and d < 150, res)
                ok(f'{tag}: the result card gives the distance from the centre', 'm from the centre' in res['title'], res['title'])
                ok(f'{tag}: no page errors', not pg.errs, pg.errs[:3])
                if tod == 'day': await shot(pg, f'{skill}_result')
                await pg.context.close()
        await b.close()
    sys.exit(ok.done('dz_check'))
asyncio.run(main())
