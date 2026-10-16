# sensor item 7: the thumb controls in the ball view. Real touch taps on every sensor button (ZOOM IN / OUT, MODE,
# TRACK, GEO, LASE, DCLT, NOSE); a double tap on the picture tracks, a single tap and a drag do not; the slew pad (the
# stick zone, labelled SLEW) drives the ball at a rate and stops when let go; then at iPhone and Android sizes every
# button is at least 44 px, on screen, clear of the readouts and clear of the HUD's centre zone (the middle third
# across, 26 to 80 percent down), the throttle out of the way.
# Usage: .venv/bin/python tests/sensor_controls_check.py [--sizes 844x390,...]
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, finger, IPHONE_15, Checks

K = 'window.__kgeu'
SIZES = sys.argv[sys.argv.index('--sizes') + 1].split(',') if '--sizes' in sys.argv else ['568x320', '667x375', '844x390', '932x430', '800x360', '915x412', '390x844']
S = f"()=>{K}.sensor()"
FREE = """()=>{const K=window.__kgeu,s=K.state(),L=K.LUKE;const x=L.x-6000,z=L.z+3000,V=75;
  s.pos.set(x,2100+K.groundHeight(x,z),z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.snapCam();K.stepFrame(1/60,false,true);
  document.querySelector('#bSensor').click();K.stepFrame(1/60,false,true);K.stepFrame(0,true);return K.sensorMode();}"""


async def tap_xy(pg, x, y):
    await pg.touchscreen.tap(x, y)


async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('reaper');K.pickBase('luke');K.start('final');}}")
        await pg.wait_for_timeout(600)
        c('in the ball view', await pg.evaluate(FREE))
        await pg.wait_for_timeout(400)
        c('the pad reads SLEW in the ball view', await pg.inner_text('#stickHint') == 'SLEW')
        c('throttle and VIEW step out', not await pg.evaluate("()=>!!document.getElementById('thrCol').offsetParent") and not await pg.evaluate("()=>!!document.getElementById('bCam').offsetParent"))
        z0 = (await pg.evaluate(S))['zoomIdx']
        await finger(pg, '#bZoom'); await pg.wait_for_timeout(250); z1 = (await pg.evaluate(S))['zoomIdx']
        await finger(pg, '#bWide'); await pg.wait_for_timeout(250); z2 = (await pg.evaluate(S))['zoomIdx']
        c('ZOOM IN then ZOOM OUT by touch', (z0, z1, z2) == (0, 1, 0), (z0, z1, z2))
        await finger(pg, '#bMode'); await pg.wait_for_timeout(250)
        c('MODE by touch: DTV to NIR', (await pg.evaluate(S))['mode'] == 'nir')
        await pg.evaluate(f"()=>{K}.setSensorMode('tv')")
        await finger(pg, '#bLase'); await pg.wait_for_timeout(250)
        c('LASE by touch: ranging, the button lit', (await pg.evaluate(S))['lrf'] and await pg.evaluate("()=>document.getElementById('bLase').classList.contains('lit')"))
        await finger(pg, '#bGeo'); await pg.wait_for_timeout(250); s = await pg.evaluate(S)
        c('GEO by touch: a geo stare, GEO lit', s['kind'] == 'geo' and await pg.evaluate("()=>document.getElementById('bGeo').classList.contains('lit')"), s['kind'])
        await finger(pg, '#bLock'); await pg.wait_for_timeout(250); s = await pg.evaluate(S)
        c('TRACK in a geo stare: a video track', s['kind'] in ('ar', 'pt'), s['kind'])
        await finger(pg, '#bLock'); await pg.wait_for_timeout(250); s = await pg.evaluate(S)
        c('TRACK again: off', s['kind'] == '', s['kind'])
        await finger(pg, '#bDclt'); await pg.wait_for_timeout(250); s = await pg.evaluate(S)
        c('DCLT by touch: level 1, labelled DCLT 1', s['dclt'] == 1 and await pg.inner_text('#bDcltT') == 'DCLT 1')
        await finger(pg, '#bDclt'); await finger(pg, '#bDclt'); await pg.wait_for_timeout(250)
        c('DCLT round to off', (await pg.evaluate(S))['dclt'] == 0)
        await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.az=2.4;S.el=-0.3;}}"); await pg.wait_for_timeout(200)
        # the swing takes about a second of flight time; at the harness's few frames a second (dt capped at 0.1) that is
        # several seconds of wall time, so wait for it rather than a fixed 1.5 s
        await finger(pg, '#bNose')
        try: await pg.wait_for_function("()=>{const s=window.__kgeu.sensor();return Math.abs(s.az)<2&&Math.abs(s.el+15)<2;}", timeout=8000)
        except Exception: pass
        s = await pg.evaluate(S)
        c('NOSE by touch: back to the nose', abs(s['az']) < 2 and abs(s['el'] + 15) < 2, (s['az'], s['el']))
        # taps on the picture
        await pg.evaluate(f"()=>{K}.sensorLook(60,35)"); await pg.wait_for_timeout(200)
        await pg.evaluate(f"()=>{K}.stepFrame(1/60,false,true)")
        await tap_xy(pg, 520, 180); await pg.wait_for_timeout(500)
        await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);{K}.stepFrame(0,true);}}"); await pg.wait_for_timeout(200); s = await pg.evaluate(S)
        c('a single tap on the picture does not track', s['kind'] == '', s['kind'])
        # headless frames take ~300 ms and delay the touch events: hold the render loop while tapping (a phone draws at 60 fps)
        await pg.evaluate(f"()=>{K}.stepFrame(1/60,false,true)")
        await tap_xy(pg, 520, 180); await pg.wait_for_timeout(80); await tap_xy(pg, 522, 182); await pg.wait_for_timeout(100)
        await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);{K}.stepFrame(0,true);}}"); await pg.wait_for_timeout(200); s = await pg.evaluate(S)
        c('a double tap on the picture tracks there', s['kind'] in ('ar', 'pt'), s['kind'])
        await finger(pg, '#bLock'); await pg.wait_for_timeout(200)
        await pg.evaluate("""()=>{const g=document.getElementById('gl'),o={pointerId:41,pointerType:'touch',isPrimary:true,bubbles:true};
          g.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:500,clientY:200}));for(let i=1;i<=6;i++)g.dispatchEvent(new PointerEvent('pointermove',{...o,clientX:500+i*12,clientY:200}));
          g.dispatchEvent(new PointerEvent('pointerup',{...o,clientX:572,clientY:200}));g.dispatchEvent(new PointerEvent('pointerdown',{...o,pointerId:42,clientX:572,clientY:200}));
          g.dispatchEvent(new PointerEvent('pointerup',{...o,pointerId:42,clientX:572,clientY:200}));}""")
        await pg.wait_for_timeout(300); s = await pg.evaluate(S)
        c('a drag then a tap is not a double tap', s['kind'] == '', s['kind'])
        # the slew pad: hold right, the ball turns at a rate; let go, it stops
        box = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];}")
        a0 = (await pg.evaluate(S))['az']
        await pg.evaluate("""([x,y])=>{const z=document.getElementById('stickZone');z.dispatchEvent(new PointerEvent('pointerdown',{pointerId:9,pointerType:'touch',clientX:x,clientY:y,bubbles:true}));
          z.dispatchEvent(new PointerEvent('pointermove',{pointerId:9,pointerType:'touch',clientX:x+70,clientY:y,bubbles:true}));}""", box)
        await pg.wait_for_timeout(1500); a1 = (await pg.evaluate(S))['az']
        await pg.evaluate("""([x,y])=>{const z=document.getElementById('stickZone');z.dispatchEvent(new PointerEvent('pointerup',{pointerId:9,pointerType:'touch',clientX:x+70,clientY:y,bubbles:true}));}""", box)
        await pg.wait_for_timeout(800); a2 = (await pg.evaluate(S))['az']; await pg.wait_for_timeout(1000); a3 = (await pg.evaluate(S))['az']
        c('slew pad held right: the ball turns right', ((a1 - a0 + 540) % 360 - 180) > 3, (a0, a1))
        c('let go: it stops (inertial hold, no drift beyond the aircraft turning)', abs(((a3 - a2 + 540) % 360) - 180) < 3, (a2, a3))
        if pg.errs: c('no console errors', False, pg.errs[:3])
        await pg.close()
        # layout at every size, free flight and strike
        for sz in SIZES:
            w, h = [int(v) for v in sz.split('x')]
            for case in ('free', 'strike'):
                pg = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
                if h > w: await pg.evaluate("()=>document.body.classList.add('portraitok')")
                if case == 'free':
                    await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('mq9b');K.pickBase('luke');K.start('final');}}"); await pg.wait_for_timeout(600)
                    await pg.evaluate(FREE)
                else:
                    await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('reaper');K.mission('range');}}"); await pg.wait_for_timeout(1500)
                await pg.wait_for_timeout(500)
                r = await pg.evaluate("""()=>{const W=innerWidth,H=innerHeight,P=H>W,bad=[],small=[],off=[],cz=[],ovl=[];
                  const T=['shTL','shTR','shTgt','shDialW','map','bPause'].map(i=>document.getElementById(i)).filter(e=>e&&e.getBoundingClientRect().width>0);
                  const tb=e=>{if(e.tagName==='CANVAS'||e.tagName==='BUTTON'||e.id==='shDialW')return e.getBoundingClientRect();const rg=document.createRange();rg.selectNodeContents(e);const rs=[...rg.getClientRects()].filter(r=>r.width>1);
                    return rs.length?{left:Math.min(...rs.map(r=>r.left)),top:Math.min(...rs.map(r=>r.top)),right:Math.max(...rs.map(r=>r.right)),bottom:Math.max(...rs.map(r=>r.bottom))}:e.getBoundingClientRect();};
                  const TB=T.map(e=>[e.id,tb(e)]);let n=0;
                  for(const e of document.querySelectorAll('#dock button')){const r=e.getBoundingClientRect();if(!r.width||!e.offsetParent)continue;n++;
                    if(r.width<43.5||r.height<43.5)small.push(e.id+' '+Math.round(r.width)+'x'+Math.round(r.height));
                    if(r.left<0||r.top<0||r.right>W||r.bottom>H)off.push(e.id);
                    if(!P&&r.right>W/3&&r.left<2*W/3&&r.bottom>0.26*H&&r.top<0.80*H)cz.push(e.id+' '+[r.left,r.top].map(Math.round));
                    for(const [i,t] of TB)if(r.left<t.right-1&&t.left<r.right-1&&r.top<t.bottom-1&&t.top<r.bottom-1)ovl.push(e.id+' x '+i);}
                  return {n,small,off,cz,ovl};}""")
                c(f'{sz} {case}: {r["n"]} sensor buttons, all 44 px or more, on screen, clear of the readouts and the centre zone',
                  r['n'] >= 7 and not r['small'] and not r['off'] and not r['cz'] and not r['ovl'], r)
                if pg.errs: c(f'{sz} {case}: no console errors', False, pg.errs[:3])
                await pg.close()
        await b.close()
    srv.shutdown(); c.done('sensor_controls_check')

asyncio.run(main())
