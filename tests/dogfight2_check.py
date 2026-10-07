# Red Flag Dogfight round 2 (dogfight2): the F-16's turn (corner speed, roll rate, the G meter and CORNER cue), the bandits'
# energy fight, mistakes, overshoot, cool off, spawns never behind and the wave ramp, the BREAK button, CHECK 6, the rear
# threat pill, the padlock view, Easy's gun cross with its lead line and aim assist, and the button layout at two sizes.
# Run: .venv/bin/python tests/dogfight2_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,false);K.stepFrame(0,true);}"
# a held turn at an indicated speed: full back stick, wings to 84 degrees; the peak g and heading change over secs
TURN = """([kt,secs])=>{const K=window.__kgeu,s=K.state(),T=K.touchIn;K.DF.test.hold=true;
  const y=s.pos.y,V=kt/1.943844/Math.sqrt(1.097*Math.exp(-y/9200)/1.225);s.vel.set(0,0,-V);s.quat.setFromEuler(new THREE.Euler(0,0,0,'YXZ'));s.w.set(0,0,0);
  T.active=true;let gm=0;const e=new THREE.Euler();
  for(let i=0;i<secs*20;i++){e.setFromQuaternion(s.quat,'YXZ');T.ail=Math.max(-1,Math.min(1,(1.46-(-e.z))*2));T.elev=1;s.throttle=1;K.stepFrame(0.05,false,true);gm=Math.max(gm,s.gload);}
  e.setFromQuaternion(s.quat,'YXZ');T.active=false;T.ail=0;T.elev=0;return {gmax:+gm.toFixed(2),hdg:+(Math.abs(e.y)*57.3).toFixed(0),ias:+(s.ias*1.943844).toFixed(0)};}"""
ROLL = """()=>{const K=window.__kgeu,s=K.state(),T=K.touchIn;T.active=true;T.ail=1;T.elev=0;let mx=0;
  for(let i=0;i<60;i++){K.stepFrame(0.05,false,true);mx=Math.max(mx,Math.abs(s.w.z));}T.active=false;T.ail=0;return +(mx*57.3).toFixed(0);}"""
HUD = "()=>({g:document.getElementById('hG').textContent,bar:document.querySelector('#hG i b').style.transform,cn:document.getElementById('hCn').textContent,cls:document.getElementById('hCn').className,disp:getComputedStyle(document.getElementById('hCn')).display})"
# place bandit 0 relative to our nose: ahead metres (negative: behind), right metres, up metres, flying our heading at kt
PLACE = """([ahead,right,up,kt,state])=>{const K=window.__kgeu,s=K.state(),b=K.DF.bandits[0],e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ'),h=-e.y;
  const V=kt/1.943844,N=new THREE.Vector3(0,0,-1).applyQuaternion(s.quat),R=new THREE.Vector3(1,0,0).applyQuaternion(s.quat),U=new THREE.Vector3(0,1,0).applyQuaternion(s.quat);
  b.p.copy(s.pos).addScaledVector(N,ahead).addScaledVector(R,right).addScaledVector(U,up);
  b.hdg=h;b.gam=0;b.bank=0;b.spd=V;b.v.set(Math.sin(h)*V,0,-Math.cos(h)*V);b.state=state||'TURN';b.st=0;b.six=0;b.ovT=0;b.ovRoll=false;b.cool=0;b.alive=true;}"""
CAM = """()=>{const K=window.__kgeu,s=K.state(),c=K.camPos(),q=K.camQuat();const n=new THREE.Vector3(0,0,-1).applyQuaternion(s.quat);
  const f=new THREE.Vector3(0,0,-1).applyQuaternion(new THREE.Quaternion(q[0],q[1],q[2],q[3]));return {fwd:+f.dot(n).toFixed(2),mode:K.camMode(),k:+K.DF.sixK.toFixed(2)}}"""
PROJ = """()=>{const K=window.__kgeu,s=K.state(),b=K.DF.bandits[0],c=K.camPos(),q=K.camQuat(),Q=new THREE.Quaternion(q[0],q[1],q[2],q[3]).invert();
  const pr=(p)=>{const v=p.clone().sub(new THREE.Vector3(c[0],c[1],c[2])).applyQuaternion(Q);const t=Math.tan(34*Math.PI/180);return [Math.abs(v.x/(-v.z)/(t*844/390)),Math.abs(v.y/(-v.z)/t),-v.z>1];};
  return {b:pr(b.p),p:pr(s.pos)};}"""
# place bandit 0 (as PLACE) and hold the gun for n tenths: the hit on him and the pipper's state after the first frame
SHOOT = PLACE.replace("([ahead,right,up,kt,state])", "([ahead,right,up,kt,n,state])").replace("b.alive=true;}", "b.alive=true;const D=K.DF;b.hp=1;D.gunHeld=true;K.stepFrame(0.1,false,false);const pip=document.querySelector('#dfHud .dfPip').className,ld=document.querySelector('#dfHud .dfLead');const lead=ld.className,tr=ld.style.transform,em=getComputedStyle(document.querySelector('#dfHud .dfPip em')).display;for(let i=1;i<n;i++)K.stepFrame(0.1,false,true);D.gunHeld=false;return {dhp:+(1-b.hp).toFixed(2),pip:pip,lead:lead,tr:tr,em:em};}")
RECTS = "()=>{const R=i=>{const r=document.getElementById(i).getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};return {fox:R('bFox'),gun:R('bGun'),brk:R('bBrk'),flr:R('bFlr'),six:R('bSix'),cam:R('bCam'),sub:R('dfSub'),stick:R('stickZone'),thr:R('thr')}}"

def overlaps(a, b, m=0):
    return a[0] < b[2] - m and b[0] < a[2] - m and a[1] < b[3] - m and b[1] < a[3] - m

async def fight(pg, mode):
    await pg.evaluate(f"()=>{{{K}.setSkill('{mode}');{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
    await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(600)
    await pg.evaluate(f"()=>{{{K}.DF.test.noBanditFire=true;{K}.DF.test.hold=true;}}")
    await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
        await fight(pg, 'pilot')
        # ---- 1. the turn ----
        r = await pg.evaluate(ROLL)
        ok('Hard, in the fight: full stick rolls at over 200 deg/s', r > 200, r)
        await pg.evaluate(f"()=>{{const s={K}.state();s.pos.y=(15000-1071)/3.28084+1.5;}}")
        t = await pg.evaluate(TURN, [345, 3])
        ok('full back stick at 345 KIAS pulls over 7.5 g (near the 350 corner speed), the heading swings over 50 degrees in 3 s', t['gmax'] >= 7.5 and t['hdg'] > 50, t)
        t = await pg.evaluate(TURN, [250, 3])
        ok('at 250 KIAS the wing gives under 6 g and the jet does not stall (it keeps turning)', 3 < t['gmax'] < 6 and t['hdg'] > 25, t)
        t = await pg.evaluate(TURN, [500, 3])
        ok('at 500 KIAS the limiter holds 9 g (never past 9.1)', 8.6 < t['gmax'] <= 9.1, t)
        h = await pg.evaluate(HUD)
        ok('the G meter shows the g with its bar, the CORNER cue says slow down (down arrow 350) when fast', h['disp'] != 'none' and h['g'].endswith(' G') and 'scaleX' in h['bar'] and 'CORNER' in h['cn'] and '▼' in h['cn'] and h['cls'] == '', h)
        await pg.evaluate(TURN, [350, 0.1]); await pg.evaluate(STEP, 1); h = await pg.evaluate(HUD)
        ok('inside the band the cue reads CORNER with a tick, green', h['cn'].startswith('CORNER ✓') and h['cls'] == 'ok', h)
        await pg.evaluate(TURN, [250, 0.1]); await pg.evaluate(STEP, 1); h = await pg.evaluate(HUD)
        ok('slow: CORNER with an up arrow and 350', '\u25B2' in h['cn'] and '350' in h['cn'] and h['cls'] == '', h)
        # ---- 2. the bandits ----
        rp = await pg.evaluate(f"()=>{{const K={K},D=K.DF,o=[];for(const w of [1,2,3,4]){{D.wave=w;o.push([K.dfWv('g'),K.dfWv('react'),K.dfWv('mist'),K.dfWv('rLock')]);}}D.wave=1;return o;}}")
        ok('the wave ramp: g and mistakes rise, reaction and lock time fall from wave 1 to 4', all(rp[i][0] < rp[i+1][0] and rp[i][1] > rp[i+1][1] and rp[i][2] > rp[i+1][2] and rp[i][3] > rp[i+1][3] for i in range(3)) and rp[3] == [1, 1, 0.55, 0], rp)
        cfg = await pg.evaluate(f"()=>({{h:{K}.DF_CFG.hard,e:{K}.DF_CFG.easy}})")
        ok('the configs carry the energy and mistake tunables (bBleed, ovG, ovT, mist, cool, err, brkCd, brkT), Hard six 14 s, Easy assist', all(k in cfg['h'] for k in ('bBleed','ovG','ovT','mist','cool','err','brkCd','brkT')) and cfg['h']['six'] == 14 and cfg['e']['assist'] == 4 and not cfg['h'].get('assist'), cfg['h'])
        # energy: the player circles at 84 degrees for 15 s, the bandit in TURN chases; its speed falls, its g never past the wave's limit
        await pg.evaluate(TURN, [360, 0.1]); await pg.evaluate(PLACE, [-350, 0, 0, 440, 'TURN'])
        e = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),T=K.touchIn,D=K.DF,b=D.bandits[0];D.test.hold=false;D.test.noMiss=true;const e=new THREE.Euler();
          const ias=()=>b.spd*Math.sqrt(1.097*Math.exp(-b.p.y/9200)/1.225)*1.943844;const i0=ias();let gmax=0;T.active=true;
          for(let i=0;i<240;i++){e.setFromQuaternion(s.quat,'YXZ');T.ail=Math.max(-1,Math.min(1,(1.45-(-e.z))*2));T.elev=1;s.throttle=1;b.six=0;K.stepFrame(0.05,false,true);gmax=Math.max(gmax,b.gP);}
          T.active=false;T.ail=0;T.elev=0;D.test.noMiss=false;return {i0:+i0.toFixed(0),i1:+ias().toFixed(0),gmax:+gmax.toFixed(2),lim:+(7*K.dfWv('g')).toFixed(2),state:b.state};}""")
        ok('a bandit turning hard for 12 s bleeds over 15 kt and never pulls past the wave\'s g', e['i0'] - e['i1'] > 15 and e['gmax'] <= e['lim'] + 0.05, e)
        # the overshoot: a bandit 600 m behind, nose on, closing; we pull 8 g; forced to miss it flies on through
        await pg.evaluate(TURN, [400, 0.1]); await pg.evaluate(PLACE, [-600, 0, 0, 580, 'TURN'])
        o = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),T=K.touchIn,D=K.DF,b=D.bandits[0];D.test.hold=false;D.test.miss=true;D.test.noMiss=false;const e=new THREE.Euler();
          let t=null,ov0=D.ovs;const tr=[];T.active=true;for(let i=0;i<60;i++){e.setFromQuaternion(s.quat,'YXZ');T.ail=Math.max(-1,Math.min(1,(1.4-(-e.z))*2));T.elev=1;K.stepFrame(0.05,false,true);if(b.state==='OVERSHOOT'&&t===null)t=i*0.05;
            if(i%5===4){const d=s.pos.clone().sub(b.p),r=d.length(),fw=b.v.clone().normalize();tr.push([b.state,+b.ovT.toFixed(2),+(fw.dot(d)/r).toFixed(2),+(b.v.clone().sub(s.vel).dot(d)/r).toFixed(0),+r.toFixed(0),+s.gload.toFixed(1)]);}}
          T.active=false;T.ail=0;T.elev=0;D.test.miss=false;return {t:t,ovs:D.ovs-ov0,sub:document.getElementById('dfSub').textContent,state:b.state,tr:tr};}""")
        ok('a chasing bandit overshoots about 1.3 s into our 8 g break (wave 1 reaction), the wingman calls Overshoot! Reverse!', o['t'] is not None and 0.8 <= o['t'] <= 2.2 and o['ovs'] == 1 and 'Overshoot' in o['sub'], o)
        await pg.evaluate(TURN, [400, 0.1]); await pg.evaluate(PLACE, [-600, 0, 0, 580, 'TURN'])
        o = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),T=K.touchIn,D=K.DF,b=D.bandits[0];D.test.noMiss=true;const e=new THREE.Euler();let any=false;
          T.active=true;for(let i=0;i<60;i++){e.setFromQuaternion(s.quat,'YXZ');T.ail=Math.max(-1,Math.min(1,(1.4-(-e.z))*2));T.elev=1;K.stepFrame(0.05,false,true);if(b.state==='OVERSHOOT')any=true;}
          T.active=false;T.ail=0;T.elev=0;D.test.noMiss=false;return any;}""")
        ok('with the mistake switched off (test.noMiss) it never overshoots', not o, o)
        # spawns never behind: at the arena edge facing out, every bandit of a wave of 4 is within 70 degrees of the nose
        sp = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),D=K.DF;const out=[];D.test.hold=true;
          for(const h of [0,1.2,2.5,3.9,5.2]){const x=D.C.x+Math.sin(h)*D.R*0.9,z=D.C.z-Math.cos(h)*D.R*0.9;s.pos.set(x,s.pos.y,z);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));
            D.test.wave(4);for(const b of D.bandits){const br=Math.atan2(b.p.x-s.pos.x,-(b.p.z-s.pos.z)),d=Math.atan2(Math.sin(br-h),Math.cos(br-h));out.push(+(d*57.3).toFixed(0));}}
          return out;}""")
        ok('spawns at the arena edge, nose out: 20 bandits all inside 70 degrees of the nose, none behind', len(sp) == 20 and max(abs(x) for x in sp) <= 70, sp)
        # a hit on us: every bandit eases off, radar quiet, EXTEND
        c = await pg.evaluate("""()=>{const K=window.__kgeu,D=K.DF,s=K.state();s.pos.set(D.C.x,s.pos.y,D.C.z);D.test.hold=false;D.test.wave(3);for(const x of D.bandits){x.state='TURN';x.rw=1;}
          K.dfHit('msl',{p:s.pos.clone(),src:D.bandits[0]});for(let i=0;i<10;i++)K.stepFrame(0.1,false,true);
          D.test.hold=true;return {hits:D.hits,cool:D.bandits.map(x=>+x.cool.toFixed(1)),states:D.bandits.map(x=>x.state),rw:D.bandits.map(x=>x.rw),vr:D.bandits[0].vr>0};}""")
        ok('after a missile hit on us the three bandits cool off for 6 s (5 left after 1 s), the other two extend, radars quiet, the shooter rolls', c['hits'] == 1 and c['cool'] == [5, 5, 5] and c['states'][1:] == ['EXTEND'] * 2 and c['rw'] == [0, 0, 0] and c['vr'], c)
        # ---- 3. BREAK (Hard) ----
        await pg.evaluate(f"()=>{{const D={K}.DF;D.test.wave(1);D.hits=0;}}"); await pg.evaluate(TURN, [400, 0.1]); await pg.evaluate(PLACE, [-900, 300, 0, 400, 'TURN'])
        bk = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),D=K.DF,T=K.touchIn,b=D.bandits[0];const e=new THREE.Euler();T.active=false;
          D.test.noBanditFire=false;D.waveT=99;D.test.launchAt();const fl0=D.flares;D.test.noBanditFire=true;
          K.dfBreak();const brk0=D.brk,cd0=D.brkCd,x=D.brkX,pop=document.getElementById('bBrk').className,sub=document.getElementById('dfSub').textContent,body=document.body.classList.contains('dfBrk');
          let gmax=0,bmax=0;for(let i=0;i<32;i++){K.stepFrame(0.05,false,true);e.setFromQuaternion(s.quat,'YXZ');gmax=Math.max(gmax,s.gload);bmax=Math.max(bmax,Math.abs(-e.z));}
          const n=D.brks;K.dfBreak();
          return {brk0:brk0,cd0:cd0,x:x,pop:pop,sub:sub,body:body,fl:[fl0,D.flares],gmax:+gmax.toFixed(2),bmax:+(bmax*57.3).toFixed(0),second:D.brks===n,
            cls:document.getElementById('bBrk').className,cd:document.getElementById('bBrkN').textContent,cdv:document.getElementById('bBrk').style.getPropertyValue('--cd'),after:D.brk};}""")
        ok('BREAK (Hard): 1.6 s of break away from the missile (left, it came from the right), the button pops, BREAK LEFT on the strip, two flares out',
           bk['brk0'] == 1.6 and bk['cd0'] == 9.6 and bk['x'] == -1 and bk['pop'] == 'pop' and 'BREAK LEFT' in bk['sub'] and bk['body'] and bk['fl'][0] - bk['fl'][1] == 2, bk)
        ok('the break rolls to over 70 degrees and pulls over 8 g, then hands the stick back; a second tap is refused while recharging; the sweep and seconds show',
           bk['bmax'] > 70 and bk['gmax'] > 8 and bk['second'] and bk['after'] == 0 and bk['cls'] == 'cool' and bk['cd'].endswith(' s') and float(bk['cdv']) > 0.5, bk)
        hp = await pg.evaluate(f"()=>{K}.hapLog(true).filter(h=>h.name==='break'||h.pat==='break').length>0||JSON.stringify({K}.hapLog()).length>=0")
        # ---- 4. awareness ----
        await pg.evaluate(f"()=>{{const D={K}.DF;D.brkCd=0;D.test.wave(1);}}"); await pg.evaluate(TURN, [400, 0.1]); await pg.evaluate(PLACE, [-1300, -700, 0, 400, 'TURN'])
        await pg.evaluate(STEP, 2); await pg.wait_for_timeout(300)
        six = await pg.evaluate("()=>{const e=document.getElementById('dfSix');return {cls:e.className,t:e.textContent,disp:getComputedStyle(e).display,op:getComputedStyle(e).opacity}}")
        ok('a bandit at our left rear 0.8 nm: the pill reads 7 or 8 O\'CLOCK 0.8 nm with the left arrow', six['disp'] == 'flex' and six['cls'].startswith('on l') and six['t'].split(' ')[0] in ('7', '8') and '0.8 nm' in six['t'], six)
        await pg.evaluate(PLACE, [-500, 0, 0, 400, 'TURN']); await pg.evaluate(STEP, 2)
        six = await pg.evaluate("()=>{const e=document.getElementById('dfSix');return {cls:e.className,t:e.textContent}}")
        ok('dead astern inside 0.7 nm: 6 O\'CLOCK, the down arrow, pulsing (hot)', 'on b' in six['cls'] and 'hot' in six['cls'] and six['t'].startswith("6 O'CLOCK"), six)
        await pg.evaluate(PLACE, [1500, 0, 0, 400, 'TURN']); await pg.evaluate(STEP, 2)
        six = await pg.evaluate("()=>document.getElementById('dfSix').className")
        ok('a bandit ahead: no pill', six == '', six)
        c0 = await pg.evaluate(CAM)
        await pg.evaluate(f"()=>{{{K}.DF.six6=true;}}"); await pg.evaluate(STEP, 12); c1 = await pg.evaluate(CAM)
        await pg.evaluate(f"()=>{{{K}.DF.six6=false;}}"); await pg.evaluate(STEP, 12); c2 = await pg.evaluate(CAM)
        ok('CHECK 6 held: the chase camera looks back along the tail within a second; released: back to the chase view', c0['fwd'] > 0.9 and c1['fwd'] < -0.9 and c1['k'] == 1 and c2['fwd'] > 0.9 and c2['k'] == 0, (c0, c1, c2))
        await pg.evaluate(f"()=>{{{K}.cycleCam();}}"); await pg.evaluate(STEP, 2)
        pl = await pg.evaluate(f"()=>({{m:{K}.camMode(),t:document.getElementById('dfSub').textContent}})")
        ok('VIEW in the fight: chase to Padlock (camMode 3)', pl['m'] == 3 and 'Padlock' in pl['t'], pl)
        frames = []
        for off in ([1500, 0, 0], [900, 0, 600], [-1200, -900, -200], [0, 1200, 0], [-1300, 0, 0]):
            await pg.evaluate(PLACE, [off[0], off[1], off[2], 400, 'TURN']); await pg.evaluate(STEP, 15); frames.append(await pg.evaluate(PROJ))
        ok('the padlock keeps the bandit (centre) and our jet in frame wherever he is: ahead, beside, behind, above', all(f['b'][2] and f['b'][0] < 0.2 and f['b'][1] < 0.2 and f['p'][2] and f['p'][0] < 0.9 and f['p'][1] < 0.9 for f in frames), frames)
        await pg.evaluate(f"()=>{{{K}.cycleCam();}}"); m1 = await pg.evaluate(f"()=>{K}.camMode()")
        await pg.evaluate(f"()=>{{{K}.DF.six6=true;}}"); await pg.evaluate(STEP, 12); c3 = await pg.evaluate(CAM)
        await pg.evaluate(f"()=>{{{K}.DF.six6=false;{K}.cycleCam();}}"); m0 = await pg.evaluate(f"()=>{K}.camMode()")
        ok('then cockpit, where CHECK 6 turns the head round, then chase again', m1 == 1 and c3['fwd'] < -0.9 and m0 == 0, (m1, c3, m0))
        # layout at 844x390 and 568x320: the new buttons clear the others, the strip and the stick zone
        for vp in ((844, 390), (568, 320)):
            await pg.set_viewport_size({'width': vp[0], 'height': vp[1]}); await pg.wait_for_timeout(400); await pg.evaluate(STEP, 2)
            r = await pg.evaluate(RECTS)
            bad = [(a, b2) for a in ('brk', 'six') for b2 in r if b2 != a and overlaps(r[a], r[b2])]
            ok(f'{vp[0]}x{vp[1]}: BREAK and CHECK 6 clear FOX 2, GUN, FLARES, VIEW, the throttle, the call strip and the stick zone', not bad and r['brk'][3] <= vp[1] and r['six'][1] >= 0, (bad, {k: [round(x) for x in v] for k, v in r.items()}))
        await pg.set_viewport_size({'width': 844, 'height': 390}); await pg.wait_for_timeout(300)
        # ---- 5. Easy: the gun cross, the lead line, the aim assist ----
        await pg.evaluate(f"()=>{K}.cycleCam()") if await pg.evaluate(f"()=>{K}.camMode()") != 0 else None
        await pg.evaluate(f"()=>{{{K}.DF.test.hold=true;{K}.DF.test.wave(1);}}"); await pg.evaluate(TURN, [400, 0])   # level, no rotation left over
        hardHit = await pg.evaluate(SHOOT, [500, 25, 0, 380, 6])
        ok('Hard: a bandit 2.9 degrees off the nose at 500 m is not hit by the plain pipper (no cross, no lead line)', hardHit['dhp'] == 0 and hardHit['pip'] == 'dfPip on' and hardHit['lead'] == 'dfLead', hardHit)
        await pg.evaluate(f"()=>{K}.setSkill('rookie')"); await pg.evaluate(STEP, 40)
        ezHit = await pg.evaluate(SHOOT, [500, 15, 0, 380, 6])
        ok('Easy: a bandit 1.7 degrees off at 500 m is hit (the aim assist bends the stream onto him), the pipper is the gun cross (ez, hot), the lead line runs to his box',
           ezHit['dhp'] > 0.3 and 'ez' in ezHit['pip'] and 'hot' in ezHit['pip'] and ezHit['lead'] == 'dfLead on' and 'scaleX' in ezHit['tr'] and ezHit['em'] == 'block', ezHit)
        await pg.evaluate(STEP, 10); far = await pg.evaluate(SHOOT, [500, 90, 0, 380, 6])
        ok('Easy: 10 degrees off the nose is outside the assist cone: no hit, the cross not hot', far['dhp'] == 0 and 'hot' not in far['pip'], far)
        # Easy's BREAK
        await pg.evaluate(f"()=>{{const D={K}.DF;D.gap=0;D.test.wave(1);D.test.hold=true;D.brkCd=0;D.brk=0;D.subT=0;}}"); await pg.evaluate(TURN, [400, 0.1]); await pg.evaluate(STEP, 20); await pg.evaluate(PLACE, [-900, 300, 0, 400, 'TURN'])
        eb = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),D=K.DF;const e=new THREE.Euler();K.dfBreak();const b0=D.brk,sub=document.getElementById('dfSub').textContent;let bmax=0,gmax=0;
          for(let i=0;i<50;i++){K.stepFrame(0.05,false,true);e.setFromQuaternion(s.quat,'YXZ');bmax=Math.max(bmax,Math.abs(-e.z));gmax=Math.max(gmax,s.gload);}
          return {b0:b0,bmax:+(bmax*57.3).toFixed(0),gmax:+gmax.toFixed(1),sub:sub};}""")
        ok('Easy: BREAK lasts 2.4 s, the assist rolls to over 70 degrees and pulls over 3 g, "Break left!" or "Break right!" on the strip', eb['b0'] == 2.4 and eb['bmax'] > 70 and eb['gmax'] > 3 and 'Break ' in eb['sub'], eb)
        # the run ends cleanly: MAIN MENU drops the padlock, the pill, the break
        await pg.evaluate(f"()=>{{{K}.cycleCam();}}"); await finger(pg, '#bPause'); await pg.wait_for_timeout(300); await finger(pg, '#pMenu'); await pg.wait_for_timeout(500)
        end = await pg.evaluate(f"()=>({{m:{K}.camMode(),live:{K}.DF.live,six:document.getElementById('dfSix').className,brk:document.body.classList.contains('dfBrk'),menu:document.getElementById('menu').classList.contains('on')}})")
        ok('MAIN MENU: the camera back to chase, the pill and the break off, the fight over', end['m'] == 0 and not end['live'] and end['six'] == '' and not end['brk'] and end['menu'], end)
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('dogfight2_check'))
asyncio.run(main())
