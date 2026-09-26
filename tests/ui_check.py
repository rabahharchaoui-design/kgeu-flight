# Playwright visual + layout check. Run from project root:
#   .venv/bin/python tests/ui_check.py
# Screenshots every phone size, and fails if any two interactive controls overlap.
import asyncio, os, sys
from playwright.async_api import async_playwright

THREE = open('node_modules/three/build/three.min.js').read()
URL = 'file://' + os.path.abspath('index.html')
SIZES = [(844, 390), (932, 430), (667, 375)]
MIN_TAP = 44          # css px; 48 pt targets, allowing for sub-pixel rounding
failures = []

# Everything the check collects. "hit" marks the ones a thumb can actually press:
# those are the ones that must never overlap each other.
GROUPS = [
    ('button',  'button',                 True),
    ('stick',   '#stickZone, #stick.on',  True),
    ('slider',  '#thr, input[type=range]',True),
    ('hudcard', '#hud .card',             False),
    ('minimap', '#map',                   False),
    ('radio',   '#atc',                   False),
    ('coach',   '#coach',                 False),
    ('warn',    '#warn',                  False),
    ('bigcfg',  '#bigcfg',                False),
]

COLLECT = """(groups)=>{
  const out=[];
  for(const [kind,sel,hit] of groups){
    document.querySelectorAll(sel).forEach(el=>{
      if(el.closest('.overlay')) return;                 // modal sheets are not in play
      const cs=getComputedStyle(el);
      if(cs.display==='none'||cs.visibility==='hidden') return;
      if(parseFloat(cs.opacity)<0.05) return;
      const r=el.getBoundingClientRect();
      if(r.width<1||r.height<1) return;
      const id=el.id||el.dataset.a||(el.textContent||'').trim().slice(0,14)||el.tagName;
      out.push({kind:kind,hit:hit&&cs.pointerEvents!=='none',id:id,
                x:r.x,y:r.y,w:r.width,h:r.height,
                path:(el.id?'#'+el.id:el.tagName.toLowerCase())});
    });
  }
  // drop entries fully contained in another of the same element set (parent/child pairs)
  return out;
}"""

def overlap(a, b):
    ox = min(a['x']+a['w'], b['x']+b['w']) - max(a['x'], b['x'])
    oy = min(a['y']+a['h'], b['y']+b['h']) - max(a['y'], b['y'])
    return ox, oy

def contains(a, b):
    return (a['x'] <= b['x']+0.5 and a['y'] <= b['y']+0.5
            and a['x']+a['w'] >= b['x']+b['w']-0.5 and a['y']+a['h'] >= b['y']+b['h']-0.5)

async def audit(pg, label, w, h):
    els = await pg.evaluate(COLLECT, GROUPS)
    hits = [e for e in els if e['hit']]
    bad = []
    for i in range(len(hits)):
        for j in range(i+1, len(hits)):
            a, b = hits[i], hits[j]
            if contains(a, b) or contains(b, a):
                continue                       # nested controls, e.g. Skip inside the coach
            ox, oy = overlap(a, b)
            if ox > 0.5 and oy > 0.5:
                bad.append(f"{a['kind']}:{a['id']} x {b['kind']}:{b['id']} ({ox:.0f}x{oy:.0f}px)")
    # the minimap and HUD cards are not tappable, but they must not sit on top of a control
    cover = []
    for c in [e for e in els if e['kind'] in ('minimap','hudcard')]:
        for t in hits:
            if contains(c, t) or contains(t, c):
                continue
            ox, oy = overlap(c, t)
            if ox > 0.5 and oy > 0.5:
                cover.append(f"{c['kind']}:{c['id']} over {t['kind']}:{t['id']} ({ox:.0f}x{oy:.0f}px)")
    small = [f"{e['kind']}:{e['id']} {e['w']:.0f}x{e['h']:.0f}"
             for e in hits if e['kind'] == 'button' and (e['w'] < MIN_TAP or e['h'] < MIN_TAP)]
    off = [f"{e['kind']}:{e['id']}" for e in hits
           if e['x'] < -0.5 or e['y'] < -0.5 or e['x']+e['w'] > w+0.5 or e['y']+e['h'] > h+0.5]
    tag = f'{w}x{h} {label}'
    if bad:
        failures.append(f'{tag}: overlap ' + '; '.join(bad))
        print(f'  FAIL {tag}: {len(bad)} overlap(s)')
        for m in bad: print('       ' + m)
    if small:
        failures.append(f'{tag}: small targets ' + '; '.join(small))
        print(f'  FAIL {tag}: tap targets under {MIN_TAP}px: ' + '; '.join(small))
    if off:
        failures.append(f'{tag}: offscreen ' + '; '.join(off))
        print(f'  FAIL {tag}: outside the viewport: ' + '; '.join(off))
    if cover:
        failures.append(f'{tag}: covering ' + '; '.join(cover))
        print(f'  FAIL {tag}: readout covers a control: ' + '; '.join(cover))
    if not (bad or small or off or cover):
        print(f'  ok   {tag}  ({len(hits)} controls, {len(els)} boxes)')

async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl',
                                      '--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
    for w, h in SIZES:
      ctx = await b.new_context(viewport={'width':w,'height':h}, has_touch=True,
                                is_mobile=True, device_scale_factor=2)
      pg = await ctx.new_page(); errs=[]
      pg.on('pageerror', lambda e: errs.append(str(e)))
      await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
      await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
      await pg.goto(URL); await pg.wait_for_timeout(2200)

      await pg.tap('#bRunway'); await pg.wait_for_timeout(1400)
      await audit(pg, 'on the ground', w, h)
      await pg.screenshot(path=f'tests/shot_{w}x{h}.png')

      # the More drawer open, easy flight (View / Tilt / Brake only)
      await pg.tap('#bMore'); await pg.wait_for_timeout(350)
      await audit(pg, 'drawer, easy', w, h)
      await pg.screenshot(path=f'tests/shot_{w}x{h}_drawer.png')
      await pg.tap('#bMore'); await pg.wait_for_timeout(250)

      # realistic mode drawer: gear, flaps and trim appear too
      await pg.tap('#bMenu'); await pg.wait_for_timeout(300)
      await pg.tap('#oEasy'); await pg.wait_for_timeout(150)
      await pg.tap('#bRunway'); await pg.wait_for_timeout(900)
      await pg.tap('#bMore'); await pg.wait_for_timeout(350)
      await audit(pg, 'drawer, realistic', w, h)
      await pg.screenshot(path=f'tests/shot_{w}x{h}_drawer_real.png')
      await pg.tap('#bMore'); await pg.wait_for_timeout(250)
      await pg.tap('#bMenu'); await pg.wait_for_timeout(250)
      await pg.tap('#oEasy'); await pg.wait_for_timeout(150)

      # airborne: the context button becomes View, and the radio call is up
      await pg.tap('#bFinal'); await pg.wait_for_timeout(1600)
      await audit(pg, 'airborne', w, h)
      await pg.screenshot(path=f'tests/shot_{w}x{h}_air.png')

      # thumb down in the left zone: the floating stick must clear everything
      box = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x,r.y,r.width,r.height];}")
      for fx, fy in [(0.5,0.5),(0.08,0.92),(0.92,0.08)]:
          x = box[0] + box[2]*fx; y = box[1] + box[3]*fy
          await pg.evaluate("""([x,y])=>{const z=document.getElementById('stickZone');
             z.dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,clientX:x,clientY:y,bubbles:true}));}""", [x,y])
          await pg.wait_for_timeout(120)
          await audit(pg, f'stick down at {fx:g},{fy:g}', w, h)
          if fx == 0.5:
              await pg.screenshot(path=f'tests/shot_{w}x{h}_stick.png')
          await pg.evaluate("""()=>{const z=document.getElementById('stickZone');
             z.dispatchEvent(new PointerEvent('pointerup',{pointerId:7,bubbles:true}));}""")
          await pg.wait_for_timeout(80)

      if errs:
          failures.append(f'{w}x{h}: page errors ' + '; '.join(errs[:3]))
          print(f'  FAIL {w}x{h} page errors: {errs[:3]}')
      await ctx.close()
    await b.close()

asyncio.run(main())
print('\nui_check: ' + ('FAILED\n  ' + '\n  '.join(failures) if failures else 'all layouts clear'))
sys.exit(1 if failures else 0)
