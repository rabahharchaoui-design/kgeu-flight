# Layout check at three iPhone landscape sizes. Fails if any two tappable controls
# overlap, a readout (HUD, map, radio, badges) sits on a control, a tap target is
# under 44 px, or anything is off screen. Run: .venv/bin/python tests/ui_check.py
#
# The top area (item 16): at every landscape size and in portrait 375x667, 390x844 and
# 430x932, Easy and Hard, with the mission card, a long two-line tower subtitle, a
# warning, a toast, the jump light, a lesson panel, the now playing ticker and a badge
# all up at once (also in the C-130 airdrop, where the look pad owns a corner), no two
# top elements overlap, none of them sits on the stick, throttle or buttons, and all of
# them are inside the safe area. The notch / Dynamic Island insets are stood in through
# --saT/--saL/--saR/--saB (index.html reads env() only there). Screenshots go to
# overnight-screenshots/phone0929/item16/.
import asyncio, sys, os
from playwright.async_api import async_playwright
from harness import serve, launch, page

SIZES = [(667, 375)] if '-q' in sys.argv else [(667, 375), (844, 390), (932, 430)]
if '--size' in sys.argv:   # one landscape size (and its portrait), e.g. --size 844x390
    SIZES = [tuple(int(v) for v in sys.argv[sys.argv.index('--size')+1].split('x'))]
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
    ('jump',    '#jumpLt.on',                      False),
]
COVERS = ('hudcard', 'radio', 'mission', 'sixpack', 'ticker', 'warn', 'jump')

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
  const a=document.getElementById('atc');a.innerHTML='<span class="tx"><b>Glendale Tower</b>Cessna 3 Kilo Echo, Glendale Tower, wind 050 at 5, runway 1, cleared to land, traffic a Cherokee on the go</span><span class="plain">Tower says: you can land on runway 1, a Cherokee is going around</span>';
  a.classList.add('on','hasPlain');
  const e0=document.getElementById('miss');if(!window.__tkWas)window.__tkWas=[e0.classList.contains('on'),document.body.classList.contains('missOn'),document.getElementById('missT').textContent,document.getElementById('missS').textContent];
  if(m&&!K.MISS.on){const e=document.getElementById('miss');document.getElementById('missT').textContent='AIRDROP  4.2 nm to the DZ, turn left to 040 and hold 1,500 ft';
    document.getElementById('missS').textContent='DROP is live. Put the bundle on the orange bullseye.';e.classList.add('on');}}"""
TK = ('ticker:', ':tk')   # failures that involve the ticker or its music controls
UNTOP = """()=>{window.__kgeu.tickerForce(null);document.getElementById('atc').classList.remove('on');
  const w=window.__tkWas,e=document.getElementById('miss');window.__tkWas=null;e.classList.toggle('on',w[0]);document.body.classList.toggle('missOn',w[1]);document.getElementById('missT').textContent=w[2];document.getElementById('missS').textContent=w[3];}"""

# ---- the top area (item 16) ----
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone0929', 'item16')
# raw safe-area insets (top, left, right, bottom) of the phone each size stands for
SAFE = {(667, 375): (0, 0, 0, 0),    (844, 390): (0, 47, 47, 21),   (932, 430): (0, 59, 59, 21),
        (375, 667): (20, 0, 0, 0),   (390, 844): (47, 0, 0, 34),    (430, 932): (59, 0, 0, 34)}
SETSAFE = """([t,l,r,b])=>{const s=document.documentElement.style;s.setProperty('--saT',t+'px');s.setProperty('--saL',l+'px');s.setProperty('--saR',r+'px');s.setProperty('--saB',b+'px');}"""
# (kind, selector, top element?) -- the controls are here so the column can be checked against them
TOPG = [
    ('pause',   '#bPause', 1), ('map', '#map', 1), ('hudcard', '#hud .card', 1), ('ap', '#hAp.on', 1),
    ('ticker',  '#tk.on', 1), ('music', '#tkCtl.on', 1), ('mission', '#miss.on', 1), ('jump', '#jumpLt.on', 1),
    ('warn',    '#warn.on', 1), ('toast', '#toast.on', 1), ('radio', '#atc.on', 1), ('badge', '.badge.on', 1), ('lesson', '#lesson.on', 1),
    ('lookpad', '#lookPad', 1), ('dest', '#hDest:not([hidden])', 1),
    ('stick',   '#stickZone', 0), ('throttle', '#thr', 0), ('button', '#dock button', 0),
]
# hold the sim for one frame, put up the warning, the jump light and a lesson on top of what
# TOP put up (the frame loop would clear them), and measure everything in the same breath
TOPSET = """([g,o])=>{const K=window.__kgeu,$=id=>document.getElementById(id);K.stepFrame(1/60,false,false);
  const u=window.__topUndo=[];const keep=e=>u.push([e,e.className,e.textContent]);
  const w=$('warn');keep(w);w.textContent='FLAP SPEED';w.classList.add('on');
  const ts=$('toast');keep(ts);ts.textContent='Now playing: Pocket Sim Original \u2014 Main Theme';ts.classList.add('on');
  const j=$('jumpLt');if(o.jump&&!j.classList.contains('on')){keep(j.lastChild);j.lastChild.textContent='ONE MINUTE';u.push([j,j.className,null]);j.classList.add('on');}
  if(o.lesson){const l=$('lesson');u.push([l,l.className,null]);for(const [id,t] of [['lesT','Lesson 4'],['lesI','Hold 70 kt down final, nose on the numbers'],['lesM','Speed 72 kt, on the glide path']]){keep($(id));$(id).textContent=t;}
    l.classList.add('on');}
  const out=[];
  for(const [kind,sel,top] of g){
    document.querySelectorAll(sel).forEach(el=>{
      if(el.closest('.overlay'))return;
      for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p);if(c.display==='none'||c.visibility==='hidden')return;}
      const r=el.getBoundingClientRect();if(r.width<1||r.height<1)return;
      out.push({kind:kind,top:!!top,id:el.id||(el.textContent||'').trim().slice(0,14)||el.tagName,x:r.x,y:r.y,w:r.width,h:r.height});
    });
  }
  return out;}"""
TOPUNDO = """()=>{const u=window.__topUndo||[];for(let i=u.length-1;i>=0;i--){const [e,c,t]=u[i];e.className=c;if(t!==null)e.textContent=t;}window.__topUndo=null;window.__kgeu.stepFrame(0,true);}"""

async def top_audit(pg, label, w, h, need, **o):
    """no overlap among the top elements or between them and the controls; all inside the safe area"""
    els = await pg.evaluate(TOPSET, [TOPG, o])
    t, l, r, b = SAFE[(w, h)]
    bad, out = [], []
    for i in range(len(els)):
        for j in range(i+1, len(els)):
            a, c = els[i], els[j]
            if not (a['top'] or c['top']): continue            # control vs control: audit() does those
            if contains(a, c) or contains(c, a): continue
            ox, oy = overlap(a, c)
            if ox > 0.5 and oy > 0.5:
                bad.append(f"{a['kind']}:{a['id']} x {c['kind']}:{c['id']} ({ox:.0f}x{oy:.0f}px)")
    for e in els:
        if e['kind'] == 'stick': continue                      # the invisible touch zone runs to the edges on purpose
        if e['x'] < l-0.5 or e['y'] < t-0.5 or e['x']+e['w'] > w-r+0.5 or e['y']+e['h'] > h-b+0.5:
            out.append(f"{e['kind']}:{e['id']} ({e['x']:.0f},{e['y']:.0f} {e['w']:.0f}x{e['h']:.0f})")
    missing = sorted(need - {e['kind'] for e in els})
    tag = f'{w}x{h} {label}'
    for name, lst in (('top overlap', bad), ('outside the safe area', out), ('not showing', missing)):
        if lst:
            failures.append(f'{tag}: {name} ' + '; '.join(lst))
            print(f'  FAIL {tag}: {name}: ' + '; '.join(lst))
    if not (bad or out or missing):
        print(f'  ok   {tag}  top area ({len(els)} boxes, {sum(e["top"] for e in els)} at the top)')

BASE = {'pause', 'map', 'hudcard', 'ticker', 'radio', 'warn', 'toast', 'badge'}

async def top_scene(pg, label, w, h, shot, lesson=True):
    """TOP + a landing badge and a record badge (they take turns), then the top audit, the full
    layout audit with the warning and jump light up, and a screenshot. Then the same without
    the mission card but with a school lesson panel (lessons and missions never run together)."""
    await pg.evaluate("()=>window.__kgeu.tickerClose()")
    await pg.evaluate(TOP, True)
    await pg.evaluate("()=>{const K=window.__kgeu;K.gradeBadge({letter:'B',line:'Firm, left of centerline, a long way off the touchdown zone'});K.bannerShow('NEW RECORD','Smoothest landing 42 fpm')}")
    await pg.wait_for_timeout(400)
    await pg.wait_for_function("()=>[...document.querySelectorAll('#badges .badge.on')].every(e=>getComputedStyle(e).transform==='none')", timeout=5000)   # slid in
    n = await pg.evaluate("()=>document.querySelectorAll('#badges .badge.on').length")
    if n != 1:
        failures.append(f'{w}x{h} {label}: {n} badges up at once (they take turns in one slot)'); print(f'  FAIL {w}x{h} {label}: {n} badges up at once')
    await top_audit(pg, label, w, h, BASE | {'mission', 'jump'}, jump=True)
    await audit(pg, label + ', full layout', w, h)
    os.makedirs(SHOTS, exist_ok=True)
    await pg.screenshot(path=os.path.join(SHOTS, shot))
    await pg.evaluate(TOPUNDO)
    if lesson:
        await pg.evaluate("()=>{if(!window.__kgeu.MISS.on)document.getElementById('miss').classList.remove('on')}")
        await top_audit(pg, label + ', lesson', w, h, BASE | {'lesson'}, lesson=True)
        await audit(pg, label + ', lesson, full layout', w, h)
        await pg.screenshot(path=os.path.join(SHOTS, shot.replace('.png', '_lesson.png')))
        await pg.evaluate(TOPUNDO)
    await pg.evaluate("()=>window.__kgeu.badgeHide()")
    await pg.evaluate(UNTOP)

async def main():
  srv, url = serve()
  async with async_playwright() as p:
    b = await launch(p)
    for w, h in SIZES:
      pg = await page(b, url, vp={'width': w, 'height': h},
                      storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
      await pg.evaluate(SETSAFE, list(SAFE[(w, h)]))
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
        await top_scene(pg, f'{skill}, C172 on final, top area', w, h, f'{w}x{h}_{skill}_c172.png')
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
        await pg.evaluate(f"()=>{{{K}.gradeBadge({{letter:'B',line:'Firm, left of centerline, a long way off the touchdown zone'}});{K}.bannerShow('NEW RECORD','Smoothest landing 42 fpm')}}")
        await pg.wait_for_timeout(700)
        await audit(pg, f'{skill}, C-130 airdrop, music controls open + badges', w, h, only=TK)
        await pg.evaluate(TOP, True); await pg.wait_for_timeout(300)
        await audit(pg, f'{skill}, C-130 airdrop, ticker + badges', w, h, only=TK)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{w}x{h}_airdrop_ticker.png')
        await pg.evaluate("()=>window.__kgeu.badgeHide()")
        await pg.evaluate(UNTOP)
        await top_scene(pg, f'{skill}, C-130 airdrop, top area', w, h, f'{w}x{h}_{skill}_airdrop.png', lesson=False)
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

      # portrait ("Play in portrait anyway"): the ticker must clear everything at the top,
      # and the whole top area stacks cleanly (item 16)
      await pg.set_viewport_size({'width': h, 'height': w}); await pg.evaluate(SETSAFE, list(SAFE[(h, w)])); await pg.wait_for_timeout(600)
      for skill in ('rookie', 'pilot'):
        await go(f"document.body.classList.add('portraitok');{K}.setSkill('{skill}');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')", 1500)
        await pg.evaluate(TOP, True); await pg.wait_for_timeout(500)
        await audit(pg, f'portrait {skill}, ticker + mission card + tower', h, w, only=TK)
        if skill == 'rookie': await pg.screenshot(path=f'tests/shot_{h}x{w}_portrait_ticker.png')
        await pg.evaluate(UNTOP)
        if (h, w) == (375, 667): continue      # the item 16 portrait sizes are 390x844 and 430x932
        await top_scene(pg, f'portrait {skill}, C172 on final, top area', h, w, f'{h}x{w}_{skill}_c172.png')
        await go(f"{K}.mission('drop')", 2000)
        await top_scene(pg, f'portrait {skill}, C-130 airdrop, top area', h, w, f'{h}x{w}_{skill}_airdrop.png', lesson=False)

      if pg.errs:
          failures.append(f'{w}x{h}: page errors ' + '; '.join(pg.errs[:3]))
          print(f'  FAIL {w}x{h} page errors: {pg.errs[:3]}')
      await pg.context.close()
    await b.close()

asyncio.run(main())
print('\nui_check: ' + ('FAILED\n  ' + '\n  '.join(failures) if failures else 'all layouts clear'))
sys.exit(1 if failures else 0)
