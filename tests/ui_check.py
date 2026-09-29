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
    ('lookpad', '#lookPad',                        True),   # C-130 airdrop free look pad
    ('hudcard', '#hud .card',                      False),
    ('minimap', '#map',                            True),
    ('dest',    '#hDest:not([hidden])',            True),
    ('radio',   '#atc.on',                         False),
    ('mission', '#miss.on',                        False),
    ('lesson',  '#lesson.on',                      False),
    ('sixpack', '#sixpack.on',                     False),
    ('warn',    '#warn.on',                        False),
    ('ticker',  '#tk.on .tkP',                     False),  # the now playing pill (its 44 pt button is in 'button')
]
COVERS = ('hudcard', 'radio', 'mission', 'sixpack', 'ticker')

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

async def audit(pg, label, w, h, only=None):
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
    if only:   # portrait: only what involves the given ids (the rest of portrait is not laid out for)
        keep = lambda t: any(k in t for k in only)
        bad, cover, small, off = [x for x in bad if keep(x)], [x for x in cover if keep(x)], [x for x in small if keep(x)], [x for x in off if keep(x)]
    tag = f'{w}x{h} {label}'
    for name, lst in (('overlap', bad), ('covering', cover), ('small targets', small), ('offscreen', off)):
        if lst:
            failures.append(f'{tag}: {name} ' + '; '.join(lst))
            print(f'  FAIL {tag}: {name}: ' + '; '.join(lst))
    if not (bad or small or off or cover):
        print(f'  ok   {tag}  ({len(hits)} controls, {len(els)} boxes)' + (('  ' + ','.join(e['id'] for e in hits)) if '-v' in sys.argv else ''))

TOP = """(m)=>{const K=window.__kgeu;K.tickerForce('A Much Longer Song Title That Will Not Fit In The Pill');
  const a=document.getElementById('atc');a.innerHTML='<b>Glendale Tower</b>Cessna 3 Kilo Echo, runway 1 clear to land, wind 050 at 5<span class="plain">Cleared to land runway 1</span>';
  a.classList.add('on','hasPlain');
  const e0=document.getElementById('miss');if(!window.__tkWas)window.__tkWas=[e0.classList.contains('on'),document.body.classList.contains('missOn'),document.getElementById('missT').textContent,document.getElementById('missS').textContent];
  if(m){const e=document.getElementById('miss');document.getElementById('missT').textContent='Drop the load on the red smoke';
    document.getElementById('missS').textContent='2.4 nm, 1,500 ft, 140 kt';e.classList.add('on');document.body.classList.add('missOn');}}"""
TK = ('ticker:', ':tk')   # failures that involve the ticker or its music controls
UNTOP = """()=>{window.__kgeu.tickerForce(null);document.getElementById('atc').classList.remove('on');
  const w=window.__tkWas,e=document.getElementById('miss');window.__tkWas=null;e.classList.toggle('on',w[0]);document.body.classList.toggle('missOn',w[1]);document.getElementById('missT').textContent=w[2];document.getElementById('missS').textContent=w[3];}"""

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
        await pg.evaluate(TOP, True); await pg.wait_for_timeout(500)
        await audit(pg, f'{skill}, C172, ticker + mission card + tower', w, h, only=TK)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{w}x{h}_ticker.png')
        await pg.evaluate("()=>window.__kgeu.tickerOpen()"); await pg.wait_for_timeout(300)
        await audit(pg, f'{skill}, C172, music controls open', w, h, only=TK)
        await pg.evaluate(UNTOP)
        # the full column: C-130 has gear and flaps
        await go(f"{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('final')", 1500)
        await audit(pg, f'{skill}, C-130 on final, button column', w, h)
        if skill == 'pilot': await pg.screenshot(path=f'tests/shot_{w}x{h}_column.png')

        box = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x,r.y,r.width,r.height];}")
        for fx, fy in [(0.5,0.5),(0.08,0.92),(0.92,0.08)]:
            x = box[0] + box[2]*fx; y = box[1] + box[3]*fy
            await pg.evaluate("""([x,y])=>{document.getElementById('stickZone').dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,clientX:x,clientY:y,bubbles:true}));}""", [x,y])
            await pg.wait_for_timeout(150)
            await audit(pg, f'{skill}, stick down at {fx:g},{fy:g}', w, h)
            if fx == 0.5 and skill == 'rookie': await pg.screenshot(path=f'tests/shot_{w}x{h}_stick.png')
            await pg.evaluate("""()=>document.getElementById('stickZone').dispatchEvent(new PointerEvent('pointerup',{pointerId:7,bubbles:true}))""")
            await pg.wait_for_timeout(250)

        # weapon buttons sit left of the column, only when a mission needs them
        await go(f"{K}.mission('range')", 2500)
        await go(f"{K}.state().ap||{K}.auto();for(let i=0;i<4;i++)if({K}.camMode()!==2){K}.cycleCam()", 1500)
        await audit(pg, f'{skill}, Reaper strike, sensor ball', w, h)
        if skill == 'pilot': await pg.screenshot(path=f'tests/shot_strike_{w}x{h}.png')
        await go(f"{K}.mission('drop')", 2000)
        await audit(pg, f'{skill}, C-130 airdrop', w, h)
        await pg.evaluate(TOP, True); await pg.wait_for_timeout(500)
        await audit(pg, f'{skill}, C-130 airdrop, ticker + mission card + tower', w, h, only=TK)
        await pg.evaluate("()=>window.__kgeu.tickerOpen()"); await pg.wait_for_timeout(300)
        await audit(pg, f'{skill}, C-130 airdrop, music controls open', w, h, only=TK)
        # a landing badge and a record badge up at the same time (they share the top row there)
        await pg.evaluate(f"()=>{{{K}.gradeBadge({{letter:'B',line:'Firm, left of centerline, a long way off the touchdown zone'}});document.getElementById('banner').innerHTML='<b>NEW RECORD</b><span>Smoothest landing 42 fpm</span>';document.getElementById('banner').classList.add('on')}}")
        await pg.wait_for_timeout(700)
        await audit(pg, f'{skill}, C-130 airdrop, music controls open + badges', w, h, only=TK)
        await pg.evaluate(TOP, True); await pg.wait_for_timeout(300)
        await audit(pg, f'{skill}, C-130 airdrop, ticker + badges', w, h, only=TK)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{w}x{h}_airdrop_ticker.png')
        await pg.evaluate("()=>{document.getElementById('banner').classList.remove('on');document.querySelectorAll('.badge.on').forEach(e=>e.classList.remove('on'))}")
        await pg.evaluate(UNTOP)
        # the crash card (3.9): RETRY and MENU at the bottom, the flight controls gone
        await go(f"{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('final')", 800)
        await go(f"{K}.crashNow('Hard impact at 1240 fpm. Keep the sink rate under 750 fpm.');for(let i=0;i<110;i++){K}.stepFrame(1/30,false,true);{K}.stepFrame(1/60);{K}.stepFrame(0,true)", 300)
        await pg.wait_for_function("()=>getComputedStyle(document.getElementById('crash')).opacity==='1'", timeout=10000)
        cc = await pg.evaluate("()=>['cRetry','cMenu'].map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&e.offsetParent!==null})")
        if not all(cc):
            failures.append(f'{w}x{h} {skill}: crash card RETRY/MENU missing or small'); print(f'  FAIL {w}x{h} {skill}: crash card buttons {cc}')
        await audit(pg, f'{skill}, crash card', w, h)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{w}x{h}_crash.png')

      await go(f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')", 1800)
      await go(f"{K}.setDest({K}.RWY_ENDS[3])", 600)
      await audit(pg, 'destination set', w, h)
      await go(f"{K}.setDest(null);{K}.gradeBadge({{letter:'B',line:'Firm, left of centerline'}})", 1500)
      await audit(pg, 'grade badge showing', w, h)
      await pg.screenshot(path=f'tests/shot_{w}x{h}_air.png')

      # portrait ("Play in portrait anyway"): the ticker must clear everything at the top
      await pg.set_viewport_size({'width': h, 'height': w}); await pg.wait_for_timeout(600)
      for skill in ('rookie', 'pilot'):
        await go(f"document.body.classList.add('portraitok');{K}.setSkill('{skill}');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')", 1500)
        await pg.evaluate(TOP, True); await pg.wait_for_timeout(500)
        await audit(pg, f'portrait {skill}, ticker + mission card + tower', h, w, only=TK)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{h}x{w}_portrait_ticker.png')
        await pg.evaluate(UNTOP)

      if pg.errs:
          failures.append(f'{w}x{h}: page errors ' + '; '.join(pg.errs[:3]))
          print(f'  FAIL {w}x{h} page errors: {pg.errs[:3]}')
      await pg.context.close()
    await b.close()

asyncio.run(main())
print('\nui_check: ' + ('FAILED\n  ' + '\n  '.join(failures) if failures else 'all layouts clear'))
sys.exit(1 if failures else 0)
