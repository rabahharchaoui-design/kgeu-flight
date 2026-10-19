# fix2 item 11: the middle of the screen is the view. The clear zone is x W/3..2W/3 by y 26%..80% of the viewport;
# no HUD chrome (banners, pills, captions, toasts, prompts, CFI lines) may touch it, no two HUD pieces may overlap,
# and the top centre column shows two things at most. World markers (.anch: the sensor reticle and its readout, the
# dogfight boxes, the DZ marker and arrow, the flight director) are the view and are left out; the controls (buttons,
# the stick ring, the throttle, the look pad) are checked for overlaps but not for the zone (at 568 wide the dock's
# second column reaches into it by design), and so are the readouts and the mini map (fixed furniture, top left, which
# at 568 wide reach past W/3 below 26% of the height).
# Cases (--case, one per call keeps a run under two minutes):
#   airdrop   the C-130 airdrop flown to the ONE MINUTE call with the Loadmaster's line up, at 568x320, 844x390,
#             932x430 and 390x844 (--size), each with iPhone insets and an Android cutout and nav bar
#   call      844x390: on to the GREEN LIGHT (the pill reads GREEN LIGHT), the drop, the objective back in the pill,
#             the caption gone within 4.5 s of the radio going quiet (--shot DIR: hud_airdrop_844x390_call.png)
#   range     the strike range with Gila's call up        dogfight  the wave pill and a SENTRY line
#   tasking   Lifeline's brief accepted, its instruction   lesson    a lesson with Dana's line
#   free      free flight with a toast and the landing badge; Settings, Radio row: Captions Off hides the top caption
#             (--shot DIR: hud_settings_captions_844.png)
# lesson: the compact strip at the bottom (its top edge below 80% at 844 and 932, 72% at 568) keeps its instruction while
# Dana's line is the top caption (schoolhud item 3: captions at the top under pause, the task card at the bottom, every mode); free also checks the in flight +XP pill under pause and the bug banner heading the top column.
# Run: .venv/bin/python tests/hud_centre_check.py [--case NAME[,NAME]] [--size WxH] [--shot DIR]
# (one case and one size a call fits in two minutes; the tasking and the airdrop take about 50 s a size)
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks
ok = Checks()
K = 'window.__kgeu'
ARGV = sys.argv[1:]
def arg(k, d=None):
    return ARGV[ARGV.index(k) + 1] if k in ARGV else d
CASES = arg('--case', 'airdrop,call,range,dogfight,tasking,lesson,free').split(',')
SIZES = [(568, 320), (844, 390), (932, 430), (390, 844)]
SIZES2 = [(844, 390), (568, 320)]   # range, dogfight, tasking, lesson
if arg('--size'): SIZES = SIZES2 = [tuple(int(x) for x in arg('--size').split('x'))]
SHOT = arg('--shot')
STORE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
NOTE = ()   # round 2: the lesson panel is checked like the rest

def insets(w, h):
    if h > w: return [('iPhone', (47, 0, 0, 34)), ('Android', (24, 0, 0, 24))]
    return [('iPhone', (0, 47, 47, 21)), ('Android', (24, 0, 0, 24))]

SETSAFE = """([t,l,r,b])=>{const s=document.documentElement.style;s.setProperty('--saT',t+'px');s.setProperty('--saL',l+'px');s.setProperty('--saR',r+'px');s.setProperty('--saB',b+'px');
  if(window.layoutCtl)layoutCtl(true);const K=window.__kgeu;for(let i=0;i<3;i++)K.stepFrame(1/30);K.hudFit();}"""

AUDIT = """()=>{const W=innerWidth,H=innerHeight,Z=[W/3,H*0.26,2*W/3,H*0.80];
  const vis=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.05)return false;}return true;};
  const painted=e=>{const s=getComputedStyle(e);if([...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))return true;
    const bg=s.backgroundColor;if(bg&&bg!=='transparent'&&!/rgba\\(.*,\\s*0\\)$/.test(bg))return true;if(s.backgroundImage&&s.backgroundImage!=='none')return true;
    return ['Top','Right','Bottom','Left'].some(k=>parseFloat(s['border'+k+'Width'])>0&&!/rgba\\(.*,\\s*0\\)$/.test(s['border'+k+'Color'])&&s['border'+k+'Style']!=='none');};
  const CTRL='button,#thr,#thrCol,#stickHint,#stick,#lookPad,#dock,#dfW,#flapInd,#hud,#map';
  const root=e=>{for(let n=e;n;n=n.parentElement){const p=n.parentElement;if(!p)return n;
    if(n.matches('button,.card,.badge,#thr,#lookPad,#stickHint,#stick,#flapInd')||p.id==='uiroot'||p.id==='topCol'||p.id==='cap'||p.id==='badges'||p.id==='hGrid')return n;}return e;};
  const els=[...document.querySelectorAll('#uiroot *, #badges .badge, #badges .badge *')].filter(e=>e.tagName!=='CANVAS'&&!e.closest('canvas,.anch,svg,#crash,#crashTop,#wasted,#bigFlash')&&vis(e)&&painted(e));
  const items=[];
  for(const e of els){let r=e.getBoundingClientRect(),x0=r.left,y0=r.top,x1=r.right,y1=r.bottom;
    for(let n=e.parentElement;n&&n!==document.body;n=n.parentElement){const s=getComputedStyle(n);
      if(s.overflow!=='visible'||s.overflowX!=='visible'||s.overflowY!=='visible'){const q=n.getBoundingClientRect();x0=Math.max(x0,q.left);y0=Math.max(y0,q.top);x1=Math.min(x1,q.right);y1=Math.min(y1,q.bottom);}}
    if(x1-x0<1||y1-y0<1)continue;
    const ro=root(e);items.push({e:e,ro:ro,ctl:!!e.closest(CTRL),r:[x0,y0,x1,y1],n:(e.closest('#lesson')?'[lesson] ':'')+(e.id?'#'+e.id:(ro.id?'#'+ro.id+' ':'')+e.tagName.toLowerCase()+(e.className&&typeof e.className==='string'?'.'+e.className.split(' ')[0]:''))});}
  const hit=(a,b,m)=>a[0]<b[2]-m&&b[0]<a[2]-m&&a[1]<b[3]-m&&b[1]<a[3]-m;
  const zone=items.filter(i=>!i.ctl&&!i.e.closest('#bugAsk')&&hit(i.r,Z,0))   // the bug banner: the one row while it is up (it may reach 108 px at 390 tall)
    .map(i=>i.n+' '+i.r.map(Math.round).join(','));
  const lap=[];
  for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){const a=items[i],b=items[j];
    if(a.ro===b.ro||a.e.contains(b.e)||b.e.contains(a.e)||a.ro.contains(b.ro)||b.ro.contains(a.ro))continue;
    if(hit(a.r,b.r,0.5))lap.push((a.e.closest('#hud')||b.e.closest('#hud')?'[hud] ':'')+a.n+' x '+b.n);}
  const tc=[...document.getElementById('topCol').children].filter(e=>vis(e)&&e.getBoundingClientRect().height>0).map(e=>e.id);
  const pill=document.getElementById('miss'),pr=pill.getBoundingClientRect();
  const hu=document.getElementById('hud').getBoundingClientRect(),pa=document.getElementById('bPause').getBoundingClientRect();
  const lr=document.getElementById('lesson').getBoundingClientRect();
  return {lesFrac:lr.height?lr.top/H:1,hudPause:hu.right>pa.left&&hu.top<pa.bottom,zone:zone,lap:[...new Set(lap)],top:tc,pill:vis(pill)?pill.innerText.replace(/\\s+/g,' ').trim():'',pillR:[pr.left,pr.top,pr.right,pr.bottom].map(Math.round),W:W,H:H};}"""

CAPINFO = """()=>{const a=document.getElementById('atc'),b=a.querySelector('b'),cs=getComputedStyle(a);
  return {on:a.classList.contains('on'),in:a.parentNode.id,who:b?b.textContent:'',col:b?getComputedStyle(b).color:'',txt:a.textContent,
    shown:cs.display!=='none'&&cs.visibility!=='hidden'&&parseFloat(cs.opacity)>0.05,col2:[...document.getElementById('topCol').children].map(k=>k.id+(k.classList.contains('on')?'+on':'')+(k.classList.contains('hold')?'+hold':'')).join(' '),op:cs.opacity,r:[...Object.values(a.getBoundingClientRect().toJSON())].map(Math.round)}}"""

PLACE_DZ = f"""()=>{{const K={K},D=K.DZ,s=K.state(),f=D.f,x=D.rel.x-f.x*4828,z=D.rel.z-f.z*4828,gh=K.groundHeight?K.groundHeight(x,z):0;
  const V=140/1.94384;s.pos.set(x,(gh||0)+305+2,z);s.vel.set(f.x*V,0,f.z*V);s.quat.setFromEuler(new THREE.Euler(0.03,-Math.atan2(f.x,-f.z),0,'YXZ'));
  s.w.set(0,0,0);s.throttle=s.power=0.36;s.flapIdx=1;s.trim=0.5;s.airTime=30;s.onGround=false;s.gearDown=false;s.gearPos=0;s.ap=null;}}"""
# dz_check's steer: snap cross-track to zero, velocity on the run-in line, drop height held; n slices of 0.5 s
STEER = f"""([n,stop])=>{{const K={K},s=K.state(),D=K.DZ;for(let k=0;k<n;k++){{if(!K.MISS.dropped){{
    const f=D.f,dx=s.pos.x-D.rel.x,dz=s.pos.z-D.rel.z,c=-dx*f.z+dz*f.x,sp=Math.hypot(s.vel.x,s.vel.z);
    s.pos.x-=-f.z*c*0.5;s.pos.z-=f.x*c*0.5;s.vel.x=f.x*sp;s.vel.z=f.z*sp;
    s.quat.setFromEuler(new THREE.Euler(new THREE.Euler().setFromQuaternion(s.quat,'YXZ').x,-Math.atan2(f.x,-f.z),0,'YXZ'));}}
  for(let j=0;j<15;j++){{K.stepFrame(1/30,false,true);
    if(!K.MISS.dropped){{const gh=K.groundHeight(s.pos.x,s.pos.z);s.pos.y+=(gh+305-s.pos.y)*0.05;}}}}
  if(stop==='c1'&&D.c1)break;if(stop==='green'&&D.light==='green')break;}}
  return {{c1:D.c1,light:D.light,t:D.tRel}};}}"""
DRAW = f"(n)=>{{for(let i=0;i<n;i++){K}.stepFrame(1/30);{K}.hudFit();}}"

async def audit(pg, tag, expect_top=None):
    a = await pg.evaluate(AUDIT)
    zone = [z for z in a['zone'] if not any(('[%s]' % n) in z for n in NOTE)]
    if a['W'] < 600 and a['lesFrac'] >= 0.72:   # 568x320: the lesson strip may reach 72% of the height (round 3)
        zone = [z for z in zone if not z.startswith('[lesson]')]
    lap = [l for l in a['lap'] if not any(('[%s]' % n) in l for n in NOTE) and not (a['W'] < 600 and l.startswith('[hud] ') and a['hudPause'])]
    noted = [z for z in a['zone'] if z not in zone] + [l for l in a['lap'] if l not in lap]   # the lesson panel; at 568 with 47 px insets the readouts under pause (before item 11 too)
    ok(f'{tag}: nothing in the clear zone', not zone, zone[:6])
    ok(f'{tag}: no two HUD pieces overlap', not lap, lap[:6])
    ok(f'{tag}: two at most in the top column', len(a['top']) <= 2, a['top'])
    if noted: print('  note ', tag, 'not counted (the lesson panel; the readouts under pause at 568 with 47 px insets):', noted[:4])
    return a

async def new(b, url, w, h, store=STORE):
    pg = await page(b, url, vp={'width': w, 'height': h}, storage=store)
    await pg.evaluate("()=>document.body.classList.add('portraitok')")
    return pg

async def fly_to_call(pg):
    await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.radioLog(true);{K}.mission('drop')}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(PLACE_DZ)
    st = await pg.evaluate(STEER, [80, 'c1'])
    # drawing frames until the Loadmaster's line is on the caption
    for i in range(20):
        on = await pg.evaluate(f"()=>{{{K}.stepFrame(1/30);return document.getElementById('atc').classList.contains('on')}}")
        if on: break
    return st

async def case_airdrop(b, url):
    for (w, h) in SIZES:
        pg = await new(b, url, w, h)
        st = await fly_to_call(pg)
        ok(f'{w}x{h}: the one minute call came', st['c1'], st)
        for name, sa in insets(w, h):
            await pg.evaluate(SETSAFE, list(sa))
            try:   # the caption's 0.35 s fade in (the harness draws at a few frames a second under load)
                await pg.wait_for_function("()=>{const a=document.getElementById('atc');return !a.classList.contains('on')||parseFloat(getComputedStyle(a).opacity)>0.9}", timeout=8000)
            except Exception: pass
            tag = f'airdrop {w}x{h} {name}'
            a = await audit(pg, tag)
            ok(f'{tag}: the pill reads ONE MINUTE while the call is on', a['pill'] == 'ONE MINUTE', a['pill'])
            c = await pg.evaluate(CAPINFO)
            # schoolhud item 3: the caption at the top under pause, the task card (the pill) at the bottom (portrait: above the throttle)
            # the Loadmaster's line, or whatever replaced it on the air by now (a new line replaces the old one)
            lm = await pg.evaluate(f"()=>{K}.radioLog().some(l=>l.who==='Loadmaster')")
            ok(f'{tag}: the caption (the Loadmaster said one minute) is tinted, in the top column above 26% of the height', lm and c['shown'] and c['in'] == 'topCol' and c['col'] == 'rgb(127, 212, 255)' and c['r'][6] <= h * 0.26 + 0.5, c)
            side = await pg.evaluate("()=>document.getElementById('cap').classList.contains('side')")
            # where the bottom band is too narrow for it (568 wide, the C-130's three button columns) it sits under the readouts
            tc = await pg.evaluate("()=>document.getElementById('miss').parentNode.id==='topCol'")
            ok(f'{tag}: the pill is the bottom card (or under the readouts, or atop the column, where the bottom has no room)', (w < 600) if tc else (a['pillR'][2] <= w / 3 + 0.5 and w < 600) if side else
               (a['pillR'][0] >= w * 2 / 3 - 1 if h > w else a['pillR'][1] >= h * 0.8 - 1), (side, a['pillR']))
            if SHOT and name == 'iPhone':
                os.makedirs(SHOT, exist_ok=True); await pg.screenshot(path=os.path.join(SHOT, f'check_airdrop_{w}x{h}.png'))
        ok(f'airdrop {w}x{h}: no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

async def case_call(b, url):
    pg = await new(b, url, 844, 390)
    await pg.evaluate(SETSAFE, [0, 47, 47, 21])
    await fly_to_call(pg)
    st = await pg.evaluate(STEER, [160, 'green'])
    await pg.evaluate(DRAW, 2)
    a = await audit(pg, 'airdrop 844 green light')
    ok('green light: the pill reads GREEN LIGHT', st['light'] == 'green' and a['pill'] == 'GREEN LIGHT', (st, a['pill']))
    if SHOT:
        os.makedirs(SHOT, exist_ok=True); await pg.wait_for_timeout(450); await pg.screenshot(path=os.path.join(SHOT, 'hud_airdrop_844x390_call.png'))
    await pg.evaluate(f"()=>{K}.missDrop()")
    await pg.evaluate(DRAW, 4)
    a = await pg.evaluate(AUDIT)
    ok('after the drop the objective is back in the pill', a['pill'] and a['pill'] not in ('ONE MINUTE', 'GREEN LIGHT', 'RED LIGHT') and 'LIGHT' not in a['pill'], a['pill'])
    # the caption: down within 4.5 s of the radio going quiet (a new line restarts the clock)
    f = await pg.evaluate(f"""()=>{{const K={K},a=document.getElementById('atc');let t=0,q=null,lines=0;
      for(let i=0;i<30*40;i++){{K.stepFrame(1/30,false,true);t+=1/30;const busy=K.VQ.cur||K.radioQ().length;
        if(busy){{q=null;}}else if(q===null)q=t;
        if(!busy&&!a.classList.contains('on')&&q!==null)return {{gone:+(t-q).toFixed(2),t:+t.toFixed(1)}};}}
      return {{gone:null,t:t}};}}""")
    ok('the caption goes within 4.5 s after the radio goes quiet', f['gone'] is not None and f['gone'] <= 4.5, f)
    ok('call: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def case_range(b, url):
    for (w, h) in SIZES2:
        pg = await new(b, url, w, h)
        await pg.evaluate(SETSAFE, [0, 47, 47, 21])
        await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.mission('range')}}"); await pg.wait_for_timeout(300)
        for i in range(30):
            c = await pg.evaluate(f"()=>{{for(let j=0;j<4;j++){K}.stepFrame(1/30);{K}.hudFit();return document.getElementById('atc').textContent}}")
            if 'Gila' in c: break
        ok(f'range {w}x{h}: a Gila call on the caption', 'Gila' in c, c[:60])
        await audit(pg, f'range {w}x{h}')
        if SHOT and w == 844: await pg.screenshot(path=os.path.join(SHOT, 'check_range_844.png'))
        ok(f'range {w}x{h}: no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

async def case_dogfight(b, url):
    for (w, h) in SIZES2:
        pg = await new(b, url, w, h)
        await pg.evaluate(SETSAFE, [0, 47, 47, 21])
        await pg.evaluate(f"()=>{{{K}.DF.test.noBrief=true;{K}.DF.test.noBanditFire=true;{K}.dfStart();}}")
        sub = ''
        for i in range(25):
            sub = await pg.evaluate(f"()=>{{for(let j=0;j<4;j++){K}.stepFrame(1/30);{K}.hudFit();const s=document.querySelector('#dfSub span');return s&&document.getElementById('dfSub').classList.contains('on')?s.innerHTML:''}}")
            if 'SENTRY' in sub: break
        ok(f'dogfight {w}x{h}: a SENTRY line, the speaker tinted', '<b>SENTRY: </b>' in sub, sub[:80])
        a = await audit(pg, f'dogfight {w}x{h}')
        sr = await pg.evaluate("()=>{const r=document.querySelector('#dfSub span').getBoundingClientRect();return {p:document.getElementById('dfSub').parentNode.id,b:r.bottom,H:innerHeight}}")
        pl = await pg.evaluate("()=>({p:document.getElementById('miss').parentNode.id,side:document.getElementById('cap').classList.contains('side')})")
        ok(f'dogfight {w}x{h}: the SENTRY caption at the top, the wave pill at the bottom (568: under the readouts)', sr['p'] == 'topCol' and sr['b'] <= sr['H'] * 0.26 + 0.5
           and (a['pillR'][1] >= h * 0.8 - 1 or (w < 600 and (pl['side'] or pl['p'] == 'topCol'))), (sr, a['pillR'], pl))
        ok(f'dogfight {w}x{h}: the wave pill is one line', a['pill'].startswith('WAVE') and a['pillR'][3] - a['pillR'][1] <= 26, (a['pill'], a['pillR']))
        if SHOT and w == 844: await pg.screenshot(path=os.path.join(SHOT, 'check_dogfight_844.png'))
        ok(f'dogfight {w}x{h}: no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

async def case_tasking(b, url):
    for (w, h) in SIZES2:
        pg = await new(b, url, w, h)
        await pg.evaluate(SETSAFE, [0, 47, 47, 21])
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('lifeline',{{seed:7}})}}"); await pg.wait_for_timeout(400)
        await pg.evaluate(DRAW, 60)
        a = await audit(pg, f'tasking {w}x{h}')
        pl = await pg.evaluate("()=>({p:document.getElementById('miss').parentNode.id,side:document.getElementById('cap').classList.contains('side')})")
        # the bottom card; at 568 wide with the C-130's three button columns there is no room at the bottom: under the readouts,
        # or (a destination readout there too) heading the top column as before schoolhud
        ok(f'tasking {w}x{h}: the instruction is in the pill, the bottom card (568: under the readouts or atop the column)', a['pill'].startswith('1/') and
           (a['pillR'][1] >= h * 0.8 - 1 or (w < 600 and (pl['side'] or pl['p'] == 'topCol'))), (a['pill'], a['pillR'], pl))
        if SHOT and w == 844: await pg.screenshot(path=os.path.join(SHOT, 'check_tasking_844.png'))
        ok(f'tasking {w}x{h}: no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

async def case_lesson(b, url):
    for (w, h) in SIZES2:
        pg = await new(b, url, w, h)
        await pg.evaluate(SETSAFE, [0, 47, 47, 21])
        await pg.evaluate(f"()=>{{const K={K};K.startLesson('pattern',true);K.lesBriefSkip();}}"); await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{{{K}.coach2('Full power, rotate at 55 knots, then hold 70 knots in the climb.');}}")
        for i in range(10):
            c = await pg.evaluate(CAPINFO)
            if c['who'] == 'Dana' and c['on']: break
            await pg.evaluate(DRAW, 3)
        await pg.evaluate(DRAW, 2)
        L = await pg.evaluate("""()=>{const l=document.getElementById('lesson'),a=document.getElementById('atc'),b=a.querySelector('b'),i=document.getElementById('lesI'),r=l.getBoundingClientRect(),ar=a.getBoundingClientRect();
          return {lc:l.classList.contains('lc'),call:l.classList.contains('call'),who:b?b.textContent:'',col:b?getComputedStyle(b).color:'',in:a.parentNode.id,
            atcBottom:Math.round(ar.bottom),H:innerHeight,ins:i.textContent,insShown:i.getBoundingClientRect().height>0&&parseFloat(getComputedStyle(i).opacity)>0.5,
            top:Math.round(r.top),frac:+(r.top/innerHeight).toFixed(3),bottom:Math.round(r.bottom)}}""")
        print(f'  info lesson {w}x{h}: the panel spans y {L["top"]}..{L["bottom"]} (top at {L["frac"]} of the height)')
        ok(f'lesson {w}x{h}: Dana is the top caption (tinted sand, above 26%), the instruction stays on the card', L['lc'] and not L['call'] and L['who'] == 'Dana' and L['in'] == 'topCol'
           and L['col'] == 'rgb(246, 193, 119)' and L['atcBottom'] <= L['H'] * 0.26 + 0.5 and L['insShown'] and L['ins'], L)
        ok(f'lesson {w}x{h}: the panel top below {0.72 if w < 600 else 0.80} of the height', L['frac'] >= (0.72 if w < 600 else 0.80), L['frac'])
        L2 = await pg.evaluate(f"""()=>{{const K={K},a=document.getElementById('atc'),l=document.getElementById('lesson');
          for(let i=0;i<30*45;i++){{K.stepFrame(1/30,false,true);if(!a.classList.contains('on'))break;}}
          return {{off:!a.classList.contains('on'),call:l.classList.contains('call'),i:document.getElementById('lesI').getBoundingClientRect().height>0,txt:document.getElementById('lesI').textContent}}}}""")
        ok(f'lesson {w}x{h}: after the call the caption is gone and the instruction is still there', L2['off'] and not L2['call'] and L2['i'] and L2['txt'], L2)
        await audit(pg, f'lesson {w}x{h}')
        if SHOT and w == 844: await pg.screenshot(path=os.path.join(SHOT, 'check_lesson_844.png'))
        ok(f'lesson {w}x{h}: no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

async def case_free(b, url):
    pg = await new(b, url, 844, 390)
    # Settings, Radio row: the captions toggle
    await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(400)
    t = await pg.evaluate("()=>{const b=document.getElementById('oCap'),r=b.getBoundingClientRect(),row=b.closest('.srow');return {txt:b.innerText.trim(),row:row&&row.firstElementChild.textContent,top:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===b}}")
    ok('Settings: Captions: On (Cap: On under 900 px wide) in the Radio row, tappable', t['txt'] in ('Captions: On', 'Cap: On') and t['row'] == 'Radio' and t['top'], t)
    await pg.evaluate("()=>document.getElementById('oCap').click()")
    t2 = await pg.evaluate("()=>({txt:document.getElementById('oCap').innerText.trim(),ls:localStorage.getItem('kgeuCap'),aria:document.getElementById('oCap').getAttribute('aria-label')})")
    ok('Captions: Off is saved (kgeuCap 0)', t2['txt'] in ('Captions: Off', 'Cap: Off') and t2['ls'] == '0' and t2['aria'] == 'Radio captions: Off', t2)
    if SHOT:
        os.makedirs(SHOT, exist_ok=True); await pg.screenshot(path=os.path.join(SHOT, 'hud_settings_captions_844.png'))
    await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}"); await pg.wait_for_timeout(500)
    await pg.evaluate(DRAW, 30)
    await pg.evaluate(f"()=>{K}.say('Glendale Tower','Skyhawk 8401L, runway 1, cleared for takeoff.',['t_cleared_to'])")
    await pg.evaluate(DRAW, 10)
    c = await pg.evaluate(CAPINFO)
    ok('Captions Off: the tower line plays but the top caption is hidden', c['on'] and not c['shown'] and 'cleared for takeoff' in c['txt'], c)
    await pg.evaluate(f"()=>{K}.setCap(true)")
    await pg.evaluate(DRAW, 2)
    c = await pg.evaluate(CAPINFO)
    ok('Captions On again: the line shows', c['shown'], c)
    for name, sa in insets(844, 390):
        await pg.evaluate(SETSAFE, list(sa))
        await pg.evaluate(f"()=>{{const K={K};K.toast('Landing challenge: Glendale runway 1. Go!');K.gradeBadge({{letter:'A',line:'Greaser. 120 fpm, 2 ft off the centreline'}});}}")
        await pg.evaluate(DRAW, 3); await pg.wait_for_function("()=>parseFloat(getComputedStyle(document.getElementById('toast')).opacity)>0.9", timeout=8000)   # the toast's 0.3 s fade in
        a = await audit(pg, f'free 844x390 {name} toast, badge and caption')
        dbg = {'badge': await pg.evaluate("()=>document.getElementById('gBadge').classList.contains('on')")}
        ok(f'free {name}: the toast and the badge are up', 'toast' in a['top'] and dbg['badge'], (a['top'], dbg))
    if SHOT: await pg.screenshot(path=os.path.join(SHOT, 'check_free_844.png'))
    # the +XP pop in flight: a one line pill under pause, over the mission pill, out of the middle
    await pg.evaluate(f"()=>{K}.xpPop(50,'Greaser')"); await pg.wait_for_timeout(300)
    x = await pg.evaluate("()=>{const e=document.querySelector('#xpPops .xpPop .xpIn');if(!e)return null;const r=e.getBoundingClientRect(),p=document.getElementById('bPause').getBoundingClientRect();return {t:r.top,b:r.bottom,l:r.left,r:r.right,pb:p.bottom,H:innerHeight,fly:document.getElementById('xpPops').classList.contains('fly')}}")
    ok('in flight the +XP pop is a pill under pause, above 26% of the height', x and x['fly'] and x['t'] >= x['pb'] and x['b'] <= x['H'] * 0.26 + 0.5, x)
    # the bug banner heads the top column; under 430 px tall only the banner shows
    await pg.evaluate(f"()=>{{const K={K};K.toast('Landing challenge: Glendale runway 1. Go!');K.bugAsk('error');}}"); await pg.wait_for_timeout(600)
    await pg.evaluate(DRAW, 9)
    a = await audit(pg, 'free 844x390 bug banner')
    bb = await pg.evaluate("()=>{const b=document.getElementById('bugAsk'),r=b.getBoundingClientRect();return {on:b.classList.contains('on'),t:r.top,b:r.bottom}}")
    ok('the bug banner is up and the top column waits under it (nothing else at 390 tall)', bb['on'] and not a['top'], (bb, a['top']))
    await pg.evaluate("()=>document.getElementById('bugAskX').click()"); await pg.wait_for_timeout(300)
    await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(300)
    for name, sa in insets(568, 320):
        await pg.evaluate(SETSAFE, list(sa))
        await pg.evaluate(f"()=>{{const K={K};K.toast('Landing challenge: Glendale runway 1. Go!');const w=document.getElementById('warn');w.textContent='GEAR UP';w.classList.add('on');}}")
        await pg.evaluate(DRAW, 3); await pg.wait_for_timeout(400)
        await audit(pg, f'free 568x320 {name} warning, toast, badge')
    ok('free: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for c in CASES:
            print(f'-- {c}')
            await globals()['case_' + c](b, url)
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('hud_centre_check'))

asyncio.run(main())
