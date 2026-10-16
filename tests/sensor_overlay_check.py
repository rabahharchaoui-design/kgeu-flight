# sensor item 4: the symbology overlay. Every readout checked against the state it shows: sensor and field of view, the
# UTC clock, AZ/EL/DEP, the laser line (LSR SAFE, LRF ON with L on the range for 10 s), the point of interest's lat/long,
# MGRS (against the game's own converter, itself checked against the mgrs library) and elevation, the aircraft line,
# the track gate (point, area, geo, the lost blink and the cue), the declutter levels, the next field of view's
# corners, the azimuth dial, the north arrow, MASK, Easy's plain words; then at five phone sizes in free flight and on
# the strike range, no readout overlaps another, the map, pause or a button, and all sit on screen.
# Usage: .venv/bin/python tests/sensor_overlay_check.py [--sizes 844x390,...]
import asyncio, sys, re, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

K = 'window.__kgeu'
SIZES = sys.argv[sys.argv.index('--sizes') + 1].split(',') if '--sizes' in sys.argv else ['568x320', '667x375', '844x390', '932x430', '390x844']
PLACE = """(hdg)=>{const K=window.__kgeu,s=K.state(),L=K.LUKE;const x=L.x-6000,z=L.z+3000,V=75;hdg=hdg*Math.PI/180;
  s.pos.set(x,2100+K.groundHeight(x,z),z);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);
  s.quat.setFromEuler(new THREE.Euler(0,-hdg,0,'YXZ'));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.snapCam();K.stepFrame(1/60,false,true);
  while(K.camMode()!==2)K.cycleCam();K.stepFrame(1/60,false,true);
  window.__q0=s.quat.clone();window.__p0=s.pos.clone();window.__slewPre=()=>{s.quat.copy(window.__q0);s.pos.copy(window.__p0);};return K.sensorMode();}"""
STEP = """(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++){window.__slewPre();K.stepFrame(1/60,false,true);}window.__slewPre();K.stepFrame(1/60);return K.sensor();}"""
TXT = "()=>({TL:document.getElementById('shTL').innerText,TR:document.getElementById('shTR').innerText,TG:document.getElementById('shTgt').innerText,cue:document.getElementById('shCue').className.includes('on')?document.getElementById('shCue').textContent:''})"
VIS = "(id)=>{const e=document.getElementById(id);if(!e)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).display!=='none';}"
OVL = """()=>{const R=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'?r:null;};
  const W=innerWidth,H=innerHeight,txt=['shTL','shTR','shTgt','shDialW','shMid'].map(i=>[i,document.getElementById(i)]).filter(a=>a[1].textContent.trim()||a[0]==='shDialW');
  const other=[['map',document.getElementById('map')],['pause',document.getElementById('bPause')],...[...document.querySelectorAll('#dock button,#fovInd')].map(e=>[e.id||'btn',e])];
  const bad=[],out=[];const box=(r)=>[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)];
  // text boxes shrink to their glyphs: a range of each line's width, not the element's (pre text: use a Range)
  const tb=e=>{const rg=document.createRange();rg.selectNodeContents(e);const rs=[...rg.getClientRects()].filter(r=>r.width>1);if(!rs.length)return R(e);
    return {left:Math.min(...rs.map(r=>r.left)),top:Math.min(...rs.map(r=>r.top)),right:Math.max(...rs.map(r=>r.right)),bottom:Math.max(...rs.map(r=>r.bottom)),width:1,height:1};};
  const T=txt.map(([i,e])=>[i,i==='shDialW'?R(e):tb(e)]).filter(a=>a[1]),O=other.map(([i,e])=>[i,R(e)]).filter(a=>a[1]);
  const hit=(a,b)=>a.left<b.right-1&&b.left<a.right-1&&a.top<b.bottom-1&&b.top<a.bottom-1;
  for(let i=0;i<T.length;i++){const [n,a]=T[i];if(a.left<-1||a.top<-1||a.right>W+1||a.bottom>H+1)out.push(n+' '+box(a));
    for(let j=i+1;j<T.length;j++)if(hit(a,T[j][1]))bad.push(n+' x '+T[j][0]);
    for(const [m,b] of O)if(hit(a,b))bad.push(n+' x '+m+' '+box(a)+' '+box(b));}
  return {bad,out};}"""


async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('reaper');K.pickBase('luke');K.start('final');}}")
        await pg.wait_for_timeout(500)
        c('sensor view', await pg.evaluate(PLACE, 0))
        s = await pg.evaluate(f"()=>{K}.sensorLook(90,30)"); s = await pg.evaluate(STEP, 3); t = await pg.evaluate(TXT)
        tl = t['TL'].split('\n'); tr = t['TR'].split('\n'); tg = t['TG'].split('\n')
        c('TL: DTV and the field of view name, then its angle and INR (no track)', tl[0].startswith('DTV') and 'WFOV' in tl[0] and tl[1].startswith('34°') and 'INR' in tl[1], tl)
        c('TR line 1: UTC date and time (Arizona day: 18:30Z at the start)', re.fullmatch(r'\d\d[A-Z]{3}\d\d (\d\d):\d\d:\d\dZ', tr[0]) is not None and tr[0][8:10] == '18', tr[0])
        m = re.fullmatch(r'AZ ([LR])(\d{3}) EL (-?\d+) DEP (-?\d+)', tr[1])
        az = (-1 if m and m.group(1) == 'L' else 1) * int(m.group(2)) if m else None
        c('TR line 2: AZ / EL / DEP match the gimbal and the line of sight', m and abs(az - s['az']) <= 1 and abs(int(m.group(3)) - s['el']) <= 1 and abs(int(m.group(4)) - 30) <= 1, (tr[1], s['az'], s['el']))
        c('TR line 3: LSR SAFE  CODE 1688', tr[2] == 'LSR SAFE  CODE 1688', tr[2])
        want = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,[la,lo]=K.geoLL(S.spot.x,S.spot.z);return [la,lo,K.toMGRS(la,lo),Math.round(S.spot.y*3.28084+K.rwyFrame().field),S.slant];}}")
        la, lo = want[0], want[1]
        def dm(v, w): v = abs(v); d = int(v); return f"{d:0{w}d}°{(v - d) * 60:05.2f}′"
        c('point of interest: lat/long in degrees and decimal minutes', tg[0] == f"N{dm(la, 2)} W{dm(lo, 3)}", (tg[0], la, lo))
        c('point of interest: MGRS (zone 12S at Luke)', tg[1] == want[2] and tg[1].startswith('12S '), (tg[1], want[2]))
        c('point of interest: elevation in ft MSL', tg[2] == f"ELEV {want[3]:,} FT MSL", tg[2])
        c('slant range in NM, computed (C)', tg[3] == f"SLT {want[4] / 1852:.2f} NM C", tg[3])
        c('aircraft line: ALT, HDG and KIAS', re.fullmatch(r'ALT [\d,]+  HDG \d{3}  \d+ KIAS', tg[4]) is not None, tg[4])
        # the converter itself on fixed points (values from the mgrs library)
        mg = await pg.evaluate(f"()=>[{K}.toMGRS(33.5350,-112.3831),{K}.toMGRS(-22.910397,-43.16282),{K}.toMGRS(35.549678,139.786958),{K}.toMGRS(49.00896,2.554117),{K}.toMGRS(38.8977,-77.0365)]")
        c('MGRS converter matches the mgrs library at five points', mg == ['12S UC 71577 11456', '23K PQ 88423 65222', '54S UE 90050 34679', '31U DQ 67392 28547', '18S UJ 23394 07395'], mg)
        # laser
        await pg.evaluate(f"()=>{K}.sensorLase()"); await pg.evaluate(STEP, 2); t = await pg.evaluate(TXT)
        c('LASE: the range reads L and TR says LRF ON', t['TG'].split('\n')[3].endswith(' L') and t['TR'].split('\n')[2].startswith('LRF ON'), (t['TG'].split('\n')[3], t['TR'].split('\n')[2]))
        await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<110;i++){window.__slewPre();K.stepFrame(0.1,false,true);}}"); await pg.evaluate(STEP, 1); t = await pg.evaluate(TXT)
        c('10 s later: back to C and LSR SAFE', t['TG'].split('\n')[3].endswith(' C') and t['TR'].split('\n')[2].startswith('LSR SAFE'), t['TG'].split('\n')[3])
        # dial and north arrow
        dial = await pg.evaluate("()=>document.getElementById('shDialP').getAttribute('transform')")
        c('dial pointer at the ball azimuth', dial == f"rotate({round(s['az'])})", (dial, s['az']))
        for brg, wantN in ((0, 0), (180, 180), (90, -90)):
            await pg.evaluate(f"()=>{K}.sensorLook({brg},35)"); await pg.evaluate(STEP, 2)
            na = await pg.evaluate("()=>document.getElementById('shNA').getAttribute('transform')")
            v = int(re.search(r'-?\d+', na).group())
            c(f'north arrow: looking {brg}°, north points {wantN}° on screen', abs(((v - wantN) + 180) % 360 - 180) <= 12, na)
        # next field of view corners
        bk = await pg.evaluate("()=>{const h=document.getElementById('sensorHud');return [h.classList.contains('nobk'),parseFloat(h.style.getPropertyValue('--by')),h.clientHeight];}")
        k = math.tan(math.radians(17 / 2)) / math.tan(math.radians(34 / 2))
        c('WFOV: the corners frame MWFOV (half height from the angles)', not bk[0] and abs(bk[1] - bk[2] * k / 2) <= 2, bk)
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=7;}}"); await pg.evaluate(STEP, 1)
        c('narrowest step: no corners', await pg.evaluate("()=>document.getElementById('sensorHud').classList.contains('nobk')"))
        await pg.evaluate(f"()=>{{{K}.SENSOR.zoom=1;}}")
        # gates
        await pg.evaluate(f"()=>{K}.sensorLook(60,35)"); await pg.evaluate(STEP, 2)
        await pg.evaluate(f"()=>{K}.trackHere()"); await pg.evaluate(STEP, 3)
        g = await pg.evaluate(f"()=>{K}.gate()"); t = await pg.evaluate(TXT)
        c('area track: a dashed gate on the crosshair, AR TRK', g['c'] == 'on ar' and abs(g['x'] - 422) < 6 and abs(g['y'] - 195) < 6 and 'AR TRK' in t['TL'], (g, t['TL']))
        await pg.evaluate(f"()=>{K}.sensorLock()"); await pg.evaluate(STEP, 1)
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.geo=K.SENSOR.spot.clone();}}"); await pg.evaluate(STEP, 2)
        g = await pg.evaluate(f"()=>{K}.gate()"); t = await pg.evaluate(TXT)
        c('geo stare: the diamond and GEO', g['c'] == 'on geo' and 'GEO' in t['TL'], (g, t['TL']))
        await pg.evaluate("()=>{const S=window.__kgeu.SENSOR;S.geo=null;S.track=S.spot.clone();}"); await pg.evaluate(STEP, 2)
        await pg.evaluate("()=>{const S=window.__kgeu.SENSOR;S.cue='TRK LOST';S.cueT=2.5;S.track=null;}"); s2 = await pg.evaluate(STEP, 1)
        g = await pg.evaluate(f"()=>{K}.gate()"); t = await pg.evaluate(TXT)
        c('a lost track: the gate blinks amber where it was, TRK LOST cue', g['c'] == 'on lost' and t['cue'] == 'TRK LOST', (g, t['cue']))
        await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<40;i++){window.__slewPre();K.stepFrame(0.1,false,true);}}"); await pg.evaluate(STEP, 1)
        g = await pg.evaluate(f"()=>{K}.gate()"); t = await pg.evaluate(TXT)
        c('... both gone a few seconds later', g['c'] == '' and t['cue'] == '', (g, t['cue']))
        # mask
        await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.az=Math.PI;S.el=-0.02;}}"); await pg.evaluate(STEP, 8); t = await pg.evaluate(TXT)
        c('looking aft into the airframe: MASK on the track line', 'MASK' in t['TL'], t['TL'])
        # declutter
        await pg.evaluate(f"()=>{K}.sensorLook(60,35)"); await pg.evaluate(STEP, 2)
        await pg.evaluate(f"()=>{K}.sensorDclt()"); await pg.evaluate(STEP, 1)
        v1 = [await pg.evaluate(VIS, i) for i in ('shTL', 'shTR', 'shDialW')]; t = await pg.evaluate(TXT)
        c('DCLT 1: TL stays, TR and the dial go, the block keeps only the range', v1 == [True, False, False] and t['TG'].strip().startswith('SLT'), (v1, t['TG']))
        await pg.evaluate(f"()=>{K}.sensorDclt()"); await pg.evaluate(STEP, 1)
        v2 = [await pg.evaluate(VIS, i) for i in ('shTL', 'shTgt', 'shGate')]
        c('DCLT 2: crosshair only (TL and the block gone)', v2[:2] == [False, False] and await pg.evaluate(VIS, 'sensorHud'), v2)
        await pg.evaluate(f"()=>{K}.sensorDclt()"); await pg.evaluate(STEP, 1)
        c('DCLT again: everything back', all([await pg.evaluate(VIS, i) for i in ('shTL', 'shTR', 'shTgt', 'shDialW')]))
        # Easy
        await pg.evaluate(f"()=>{{{K}.setSkill('rookie');}}"); await pg.evaluate(STEP, 2); t = await pg.evaluate(TXT)
        c('Easy: plain words (camera, zoom n of 5, the spot in miles or metres, feet above sea level)', t['TL'].startswith('Day camera') and 'Zoom 2 of 5' in t['TL'] and 'away' in t['TG'] and 'ft above sea level' in t['TG'], (t['TL'], t['TG']))
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');}}")
        if pg.errs: c('no console errors', False, pg.errs[:3])
        await pg.close()
        # layout at every size, free flight and the strike range
        for sz in SIZES:
            w, h = [int(v) for v in sz.split('x')]
            for case in ('free', 'strike'):
                pg = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
                if h > w: await pg.evaluate("()=>document.body.classList.add('portraitok')")
                if case == 'free':
                    await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('mq9b');K.pickBase('luke');K.start('final');}}"); await pg.wait_for_timeout(500)
                    await pg.evaluate(PLACE, 30); await pg.evaluate(f"()=>{K}.sensorLook(120,30)"); await pg.evaluate(f"()=>{K}.trackHere()")
                else:
                    await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('reaper');K.mission('range');}}"); await pg.wait_for_timeout(1200)
                    await pg.evaluate(f"()=>{{const K={K},i=K.STRIKE.targets.findIndex(t=>t.kind==='truck');K.pointAt(i);K.trackHere();}}")
                    await pg.evaluate("()=>{window.__slewPre=()=>{};}")
                await pg.evaluate("()=>{const t=document.getElementById('toast');t&&t.classList.remove('on');}")
                await pg.evaluate(STEP, 20); await pg.wait_for_timeout(300)
                await pg.evaluate("()=>{const K=window.__kgeu;K.stepFrame(1/60);}")
                o = await pg.evaluate(OVL)
                c(f'{sz} {case}: no readout overlaps another, the map, pause or a button; all on screen', not o['bad'] and not o['out'], o)
                if pg.errs: c(f'{sz} {case}: no console errors', False, pg.errs[:3])
                await pg.close()
        await b.close()
    srv.shutdown(); c.done('sensor_overlay_check')

asyncio.run(main())
