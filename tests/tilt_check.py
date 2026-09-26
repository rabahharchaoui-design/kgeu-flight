# Tilt steering check. Run from project root: .venv/bin/python tests/tilt_check.py
# Drives synthetic deviceorientation / devicemotion events and asserts the mapping,
# stubbing the iOS requestPermission result so the real iOS branch is exercised.
import asyncio, os, sys
from playwright.async_api import async_playwright
THREE = open('node_modules/three/build/three.min.js').read()
URL = 'file://' + os.path.abspath('index.html')
fails = []

def chk(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (('  ' + detail) if detail else ''))
    if not cond: fails.append(name)

PERM_STUB = """(res)=>{
  for(const n of ['DeviceOrientationEvent','DeviceMotionEvent']){
    if(!window[n]) continue;
    window[n].requestPermission = function(){ window.__permCalls=(window.__permCalls||0)+1; return Promise.resolve(res); };
  }
}"""

async def newpage(ctx, errs, perm='granted', start=True):
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.add_init_script("window.__permRes=%r;" % perm)
    await pg.add_init_script("(" + PERM_STUB + ")(window.__permRes)")
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(1800)
    if start:
        await pg.tap('#bRunway'); await pg.wait_for_timeout(500)
    return pg

async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    ctx = await b.new_context(viewport={'width':844,'height':390}, has_touch=True, is_mobile=True)
    errs = []

    # ---------- granted: orientation path ----------
    pg = await newpage(ctx, errs, 'granted')
    await pg.tap('#bMore'); await pg.wait_for_timeout(250)   # Tilt lives in the More drawer
    await pg.tap('[data-a="tilt"]')                          # a real tap, not a synthetic click
    await pg.wait_for_timeout(250)
    chk('tilt arms from a real tap on the button', await pg.evaluate("__kgeu.tilt.on"))
    chk('the drawer closes after the tap', not await pg.evaluate("document.getElementById('drawer').classList.contains('on')"))
    chk('both permissions requested in the gesture', await pg.evaluate("window.__permCalls") == 2,
        str(await pg.evaluate("window.__permCalls")))

    async def feed(beta, gamma, n=40):
        await pg.evaluate("""([b,g,n])=>{for(let i=0;i<n;i++)
            window.dispatchEvent(new DeviceOrientationEvent('deviceorientation',{beta:b,gamma:g,alpha:0}));}""",
            [beta, gamma, n])
        await pg.wait_for_timeout(60)

    await feed(0, -75)
    base = await pg.evaluate("[__kgeu.tilt.x,__kgeu.tilt.y]")
    chk('centred at the calibration pose', abs(base[0])<0.08 and abs(base[1])<0.08, f'{base}')
    chk('source is orientation', await pg.evaluate("__kgeu.tilt.src") == 'orientation')

    await feed(25, -75); r1 = await pg.evaluate("[__kgeu.tilt.x,__kgeu.tilt.y]")
    await feed(-25, -75); r2 = await pg.evaluate("[__kgeu.tilt.x,__kgeu.tilt.y]")
    chk('roll responds both ways', abs(r1[0])>0.25 and abs(r2[0])>0.25 and r1[0]*r2[0]<0,
        f'{r1[0]:+.2f} / {r2[0]:+.2f}')

    await feed(0, -75)
    await feed(0, -50); p1 = await pg.evaluate("__kgeu.tilt.y")
    await feed(0, -75)
    await feed(0, -100); p2 = await pg.evaluate("__kgeu.tilt.y")
    chk('pitch responds both ways', abs(p1)>0.15 and abs(p2)>0.15 and p1*p2<0, f'{p1:+.2f} / {p2:+.2f}')

    await feed(0, -75); await feed(1.2, -75)
    dz = await pg.evaluate("__kgeu.tilt.x")
    chk('dead zone holds centre', abs(dz) < 0.06, f'{dz:+.3f}')

    await feed(0, -75)
    await pg.evaluate("document.getElementById('oInv').click()")
    await feed(0, -50); inv = await pg.evaluate("__kgeu.tilt.y")
    chk('invert pitch flips the sign', inv * p1 < 0, f'{inv:+.2f} vs {p1:+.2f}')
    await pg.evaluate("document.getElementById('oInv').click()")

    async def sens(v):
        await pg.evaluate("""(v)=>{const s=document.getElementById('oSens');s.value=String(v);
            s.dispatchEvent(new Event('input',{bubbles:true}));}""", v)
    await sens(0); await feed(0,-75); await feed(20,-75); lo = abs(await pg.evaluate("__kgeu.tilt.x"))
    await sens(4); await feed(0,-75); await feed(20,-75); hi = abs(await pg.evaluate("__kgeu.tilt.x"))
    chk('sensitivity slider changes gain', hi > lo + 0.05, f'low {lo:.2f} high {hi:.2f}')
    await sens(2)

    await pg.evaluate("document.getElementById('bMenu').click()")
    await pg.wait_for_timeout(1200)
    d = await pg.inner_text('#tiltDiag')
    chk('diagnostics shows permission, rate and raw angles',
        'permission granted' in d and '/s' in d and 'roll' in d and 'pitch' in d, repr(d[:100]))
    await pg.close()

    # ---------- granted: devicemotion fallback ----------
    pg2 = await newpage(ctx, errs, 'granted')
    await pg2.evaluate("document.getElementById('bMore').click();document.querySelector('[data-a=\"tilt\"]').click()")
    await pg2.wait_for_timeout(150)
    async def feedM(x,y,z,n=40):
        await pg2.evaluate("""([x,y,z,n])=>{for(let i=0;i<n;i++)
            window.dispatchEvent(new DeviceMotionEvent('devicemotion',{accelerationIncludingGravity:{x:x,y:y,z:z}}));}""",
            [x,y,z,n])
        await pg2.wait_for_timeout(60)
    await feedM(0, 9.8, 0)
    chk('falls back to devicemotion when orientation never arrives',
        await pg2.evaluate("__kgeu.tilt.src") == 'motion')
    m0 = await pg2.evaluate("__kgeu.tilt.x")
    chk('motion centred at calibration', abs(m0)<0.08, f'{m0:+.3f}')
    await feedM(4.5, 8.7, 0); m1 = await pg2.evaluate("__kgeu.tilt.x")
    await feedM(-4.5, 8.7, 0); m2 = await pg2.evaluate("__kgeu.tilt.x")
    chk('motion roll responds both ways', abs(m1)>0.2 and abs(m2)>0.2 and m1*m2<0, f'{m1:+.2f} / {m2:+.2f}')
    # orientation must take over once it appears
    await pg2.evaluate("""()=>{for(let i=0;i<10;i++)
        window.dispatchEvent(new DeviceOrientationEvent('deviceorientation',{beta:0,gamma:-75,alpha:0}));}""")
    await pg2.wait_for_timeout(80)
    chk('orientation takes priority once present', await pg2.evaluate("__kgeu.tilt.src") == 'orientation')
    await pg2.close()

    # ---------- granted but no events at all: blocked viewer ----------
    pg3 = await newpage(ctx, errs, 'granted')
    await pg3.evaluate("document.getElementById('bMore').click();document.querySelector('[data-a=\"tilt\"]').click()")
    await pg3.wait_for_timeout(2400)
    msg = await pg3.inner_text('#toast')
    chk('warns when no motion data arrives', 'Safari' in msg or 'No motion data' in msg, repr(msg))
    await pg3.close()

    # ---------- denied ----------
    pg4 = await newpage(ctx, errs, 'denied')
    await pg4.evaluate("document.getElementById('bMore').click();document.querySelector('[data-a=\"tilt\"]').click()")
    await pg4.wait_for_timeout(500)
    chk('denied leaves tilt off', not await pg4.evaluate("__kgeu.tilt.on"))
    msg4 = await pg4.inner_text('#toast')
    chk('denied explains how to fix it', 'denied' in msg4.lower(), repr(msg4))
    await pg4.close()

    chk('no page errors', not errs, str(errs[:2]))
    await b.close()

asyncio.run(main())
print('\ntilt_check: ' + ('FAILED ' + ', '.join(fails) if fails else 'all checks passed'))
sys.exit(1 if fails else 0)
