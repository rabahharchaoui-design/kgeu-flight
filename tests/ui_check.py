# Layout check at three iPhone landscape sizes. Fails if any two tappable controls
# overlap, a readout (HUD, map, radio, badges) sits on a control, a tap target is
# under 44 px, or anything is off screen. Run: .venv/bin/python tests/ui_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page

SIZES = [(667, 375)] if '-q' in sys.argv else [(667, 375), (844, 390), (932, 430)]
MIN_TAP = 44
failures = []

# "hit" marks what a thumb can press: those must never overlap each other.
GROUPS = [
    ('button',  'button',                          True),
    ('badge',   '.badge.on',                       True),
    ('stick',   '#stickZone, #stick.on',           True),
    ('slider',  '#thr, input[type=range]',         True),
    ('hudcard', '#hud .card',                      False),
    ('minimap', '#map',                            True),
    ('dest',    '#hDest:not([hidden])',            True),
    ('radio',   '#atc.on',                         False),
    ('mission', '#miss.on',                        False),
    ('lesson',  '#lesson.on',                      False),
    ('sixpack', '#sixpack.on',                     False),
    ('warn',    '#warn.on',                        False),
]
COVERS = ('hudcard', 'radio', 'mission', 'sixpack')

COLLECT = """(groups)=>{
  const out=[];
  for(const [kind,sel,hit] of groups){
    document.querySelectorAll(sel).forEach(el=>{
      if(el.closest('.overlay')) return;                 // modal sheets are not in play
      const cs=getComputedStyle(el);
      if(cs.display==='none'||cs.visibility==='hidden') return;
      if(parseFloat(cs.opacity)<0.05) return;
      for(let p=el.parentElement;p;p=p.parentElement){const c=getComputedStyle(p);if(c.display==='none'||parseFloat(c.opacity)<0.05)return;}
      const r=el.getBoundingClientRect();
      if(r.width<1||r.height<1) return;
      const id=el.id||el.dataset.a||(el.textContent||'').trim().slice(0,14)||el.tagName;
      out.push({kind:kind,hit:hit&&cs.pointerEvents!=='none',id:id,x:r.x,y:r.y,w:r.width,h:r.height});
    });
  }
  return out;
}"""

def overlap(a, b):
    return (min(a['x']+a['w'], b['x']+b['w']) - max(a['x'], b['x']),
            min(a['y']+a['h'], b['y']+b['h']) - max(a['y'], b['y']))

def contains(a, b):
    return (a['x'] <= b['x']+0.5 and a['y'] <= b['y']+0.5
            and a['x']+a['w'] >= b['x']+b['w']-0.5 and a['y']+a['h'] >= b['y']+b['h']-0.5)

async def audit(pg, label, w, h):
    els = await pg.evaluate(COLLECT, GROUPS)
    hits = [e for e in els if e['hit']]
    bad, cover = [], []
    for i in range(len(hits)):
        for j in range(i+1, len(hits)):
            a, b = hits[i], hits[j]
            if contains(a, b) or contains(b, a): continue    # nested, e.g. Skip inside the coach
            ox, oy = overlap(a, b)
            if ox > 0.5 and oy > 0.5:
                bad.append(f"{a['kind']}:{a['id']} x {b['kind']}:{b['id']} ({ox:.0f}x{oy:.0f}px)")
    for c in [e for e in els if e['kind'] in COVERS]:
        for t in hits:
            if contains(c, t) or contains(t, c): continue
            ox, oy = overlap(c, t)
            if ox > 0.5 and oy > 0.5:
                cover.append(f"{c['kind']}:{c['id']} over {t['kind']}:{t['id']} ({ox:.0f}x{oy:.0f}px)")
    small = [f"{e['kind']}:{e['id']} {e['w']:.0f}x{e['h']:.0f}"
             for e in hits if e['kind'] in ('button', 'badge') and (e['w'] < MIN_TAP-0.5 or e['h'] < MIN_TAP-0.5)]
    off = [f"{e['kind']}:{e['id']}" for e in els
           if e['x'] < -0.5 or e['y'] < -0.5 or e['x']+e['w'] > w+0.5 or e['y']+e['h'] > h+0.5]
    tag = f'{w}x{h} {label}'
    for name, lst in (('overlap', bad), ('covering', cover), ('small targets', small), ('offscreen', off)):
        if lst:
            failures.append(f'{tag}: {name} ' + '; '.join(lst))
            print(f'  FAIL {tag}: {name}: ' + '; '.join(lst))
    if not (bad or small or off or cover):
        print(f'  ok   {tag}  ({len(hits)} controls, {len(els)} boxes)' + (('  ' + ','.join(e['id'] for e in hits)) if '-v' in sys.argv else ''))

async def main():
  srv, url = serve()
  async with async_playwright() as p:
    b = await launch(p)
    for w, h in SIZES:
      pg = await page(b, url, vp={'width': w, 'height': h},
                      storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
      K = "window.__kgeu"
      async def go(js, wait=1400):
          await pg.evaluate("()=>{" + js + "}"); await pg.wait_for_timeout(wait)
      for skill in ('rookie', 'pilot'):
        await go(f"{K}.setSkill&&{K}.setSkill('{skill}');{K}.pick('f16');{K}.pickBase('luke');{K}.start('runway')")
        await audit(pg, f'{skill}, F-16 on the ground', w, h)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{w}x{h}.png')
        await go(f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')", 1800)
        await audit(pg, f'{skill}, C172 on final, radio up', w, h)
        await go("document.getElementById('bFlaps').click()", 300)
        await audit(pg, f'{skill}, flap selector open', w, h)
        await go("document.getElementById('bFlaps').click()", 200)
      await go(f"{K}.setDest({K}.RWY_ENDS[3])", 600)
      await audit(pg, 'destination set', w, h)
      await go(f"{K}.setDest(null);{K}.gradeBadge({{letter:'B',line:'Firm, left of centerline'}})", 1500)
      await audit(pg, 'grade badge showing', w, h)
      await pg.screenshot(path=f'tests/shot_{w}x{h}_air.png')

      box = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x,r.y,r.width,r.height];}")
      for fx, fy in [(0.5,0.5),(0.08,0.92),(0.92,0.08)]:
          x = box[0] + box[2]*fx; y = box[1] + box[3]*fy
          await pg.evaluate("""([x,y])=>{document.getElementById('stickZone').dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,clientX:x,clientY:y,bubbles:true}));}""", [x,y])
          await pg.wait_for_timeout(150)
          await audit(pg, f'stick down at {fx:g},{fy:g}', w, h)
          if fx == 0.5: await pg.screenshot(path=f'tests/shot_{w}x{h}_stick.png')
          await pg.evaluate("""()=>document.getElementById('stickZone').dispatchEvent(new PointerEvent('pointerup',{pointerId:7,bubbles:true}))""")
          await pg.wait_for_timeout(250)

      # the lower right carries weapon buttons only when a mission needs them
      await go(f"{K}.mission('range')", 2500)
      await go(f"{K}.state().ap||{K}.auto();for(let i=0;i<4;i++)if({K}.camMode()!==2){K}.cycleCam()", 1500)
      await audit(pg, 'Reaper strike, sensor ball', w, h)
      await pg.screenshot(path=f'tests/shot_strike_{w}x{h}.png')
      await go(f"{K}.mission('drop')", 2000)
      await audit(pg, 'C-130 airdrop', w, h)

      if pg.errs:
          failures.append(f'{w}x{h}: page errors ' + '; '.join(pg.errs[:3]))
          print(f'  FAIL {w}x{h} page errors: {pg.errs[:3]}')
      await pg.context.close()
    await b.close()

asyncio.run(main())
print('\nui_check: ' + ('FAILED\n  ' + '\n  '.join(failures) if failures else 'all layouts clear'))
sys.exit(1 if failures else 0)
