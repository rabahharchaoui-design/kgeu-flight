# Desktop (Mac) smoke check: no touch, mouse yoke and sensor click-to-track.
import asyncio, os, sys
from playwright.async_api import async_playwright
THREE = open('node_modules/three/build/three.min.js').read()
URL = 'file://' + os.path.abspath('index.html')
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    ctx=await b.new_context(viewport={'width':1440,'height':900})
    pg=await ctx.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2200)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    if await pg.is_visible('#funnel'): await pg.click('#fPilot')
    chk('desktop is not in touch mode', not await pg.evaluate("()=>document.body.classList.contains('touch')"))
    chk('phone only controls stay hidden',
        not await pg.is_visible('#stickZone') and not await pg.is_visible('#thr'))
    await pg.evaluate("()=>window.__kgeu.start('runway')"); await pg.wait_for_timeout(1200)
    chk('desktop camera and Full screen are shown',
        await pg.is_visible('#bCam') and await pg.is_visible('#bFull'))
    # mouse yoke
    await pg.mouse.move(700,500); await pg.mouse.down()
    await pg.mouse.move(820,560, steps=6); await pg.wait_for_timeout(120)
    st=await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.ail,s.elev];}")
    chk('mouse drag works the yoke', abs(st[0])>0.1 and abs(st[1])>0.1, str([round(v,2) for v in st]))
    await pg.mouse.up(); await pg.wait_for_timeout(200)
    # keyboard flap change raises the big readout
    await pg.keyboard.press(']'); await pg.wait_for_timeout(250)
    big=await pg.inner_text('#bigcfg')
    chk('flap change shows the big readout', 'FLAPS' in big, repr(big))
    chk('flaps line under the altitude card updates',
        'FLAPS' in await pg.inner_text('#hFlap'), await pg.inner_text('#hFlap'))
    # strike mode on desktop: click to track, space to fire
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
    await pg.evaluate("()=>window.__kgeu.mission('range')"); await pg.wait_for_timeout(1500)
    chk('sensor mode active on desktop', await pg.evaluate("()=>window.__kgeu.sensorMode()"))
    i=await pg.evaluate("()=>window.__kgeu.STRIKE.targets.findIndex(t=>t.kind==='bunker')")
    await pg.evaluate("(i)=>window.__kgeu.pointAt(i)", i); await pg.wait_for_timeout(200)
    await pg.mouse.click(720,450); await pg.wait_for_timeout(250)
    trk=await pg.evaluate("()=>{const S=window.__kgeu.SENSOR;return !!(S.tgt||S.track);}")
    chk('click on the scene sets a track', trk)
    await pg.keyboard.press('Space'); await pg.wait_for_timeout(400)
    chk('space fires in sensor mode', await pg.evaluate("()=>window.__kgeu.STRIKE.shots")==1)
    await pg.screenshot(path='tests/shot_desktop.png')
    chk('no page errors', not errs, str(errs[:2]))
    await b.close()
asyncio.run(main())
print('\ndesktop_check: ' + ('FAILED ' + ', '.join(fails) if fails else 'all checks passed'))
sys.exit(1 if fails else 0)
