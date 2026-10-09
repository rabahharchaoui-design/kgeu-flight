# The Arsenal: the loadout card between the Red Flag Dogfight's briefing and FIGHT'S ON (item 1), and what each pick puts
# on the jet. More sections join as the items land (the MRM, the multipliers, the balance, the submission).
# Run: .venv/bin/python tests/arsenal_check.py            (writes screenshots to overnight-screenshots/arsenal/)
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
from ui1_mock import Mock
ok = Checks()
K = "window.__kgeu"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'arsenal'))
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,false);K.stepFrame(0,true);}"
STORES = f"()=>{{const D={K}.DF;return {{fox:D.fox,mrm:D.mrm|0,rounds:D.rounds,flares:D.flares,lo:D.lo&&D.lo.r,g:D.lo&&D.lo.g,t:D.t,on:D.on,brief:D.brief}}}}"
# every box on the card: in the viewport, no two interactive boxes overlapping, tap targets 44 px or more
FIT = """()=>{const o=document.getElementById('dfLo'),sh=o.querySelector('.sheet').getBoundingClientRect(),W=innerWidth,H=innerHeight;
  const R=e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};
  const btn=[...o.querySelectorAll('button')].map(R),go=R(document.getElementById('dfbGo'));
  let ov=0;for(let i=0;i<btn.length;i++)for(let j=i+1;j<btn.length;j++){const a=btn[i],b=btn[j];if(a[0]<b[2]-1&&b[0]<a[2]-1&&a[1]<b[3]-1&&b[1]<a[3]-1)ov++;}
  const small=btn.filter(b=>b[2]-b[0]<44||b[3]-b[1]<44).length,off=[...o.querySelectorAll('.sheet *')].map(R).filter(b=>b[2]-b[0]>0&&(b[0]<-0.5||b[1]<-0.5||b[2]>W+0.5||b[3]>H+0.5)).length;
  const clip=[...o.querySelectorAll('.loR .c,.loR .f,.loR b,.loSum,.loG b')].filter(e=>e.scrollWidth>e.clientWidth+1).length;
  return {on:o.classList.contains('on'),sheet:[sh.left,sh.top,sh.right,sh.bottom],ov:ov,small:small,off:off,clip:clip,go:go,scroll:o.scrollHeight>o.clientHeight+1,n:btn.length}}"""

async def open_brief(pg, mode):
    await pg.evaluate(f"()=>{{{K}.setSkill('{mode}');{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
    await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(600)
    await pg.evaluate(f"()=>{{{K}.DF.test.noBanditFire=true;{K}.DF.test.hold=true;}}")

async def shot(pg, name):
    os.makedirs(OUT, exist_ok=True)
    await pg.screenshot(path=os.path.join(OUT, name), timeout=120000)
    print('  wrote', os.path.join(OUT, name))

# bandit i at d metres along the nose (or off it by off radians, positive to the left), flying our way and speed (test.hold)
PLACE = """([i,d,off])=>{const K=window.__kgeu,s=K.state(),D=K.DF,b=D.bandits[i];D.test.hold=true;
  const q=s.quat.clone();if(off)q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),off));
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(q);b.p.copy(s.pos).addScaledVector(n,d);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;b.alive=true;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);return true;}"""
FAST = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);}"
DRAW = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}"
W = f"""()=>{{const D={K}.DF,S=D.seek,r=document.querySelector('#dfHud .dfRad'),c=document.querySelector('#dfHud .dfSeek'),f=document.getElementById('bFox');
  return {{wpn:D.wpn,fox:D.fox,mrm:D.mrm,st:S.state,min:!!S.min,rel:!!D.rel,ab:D.mAbort,ms:D.mShots,mk:D.mKills,kills:D.kills,
    msl:D.msl.filter(m=>m.on&&!m.foe).map(m=>m.kind),rad:r.className,radT:r.lastChild.textContent,seek:c.className,
    L:document.getElementById('bFoxL').textContent,N:document.getElementById('bFoxN').textContent,Wt:document.getElementById('bFoxW').textContent,cls:f.className,
    side:document.getElementById('sideToast').textContent,v:{K}.DFA.w.slice()}}}}"""

async def hold_fox(pg, ms):
    await pg.evaluate("(ms)=>{const f=document.getElementById('bFox');f.dispatchEvent(new PointerEvent('pointerdown',{pointerId:91,bubbles:true,pointerType:'touch'}));}", ms)
    await pg.wait_for_timeout(ms)
    await pg.evaluate("()=>{const f=document.getElementById('bFox');f.dispatchEvent(new PointerEvent('pointerup',{pointerId:91,bubbles:true,pointerType:'touch'}));}")

async def start_rack(pg, mode, rack, gun='full'):
    await open_brief(pg, mode); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
    await finger(pg, f'#loRacks [data-r="{rack}"]'); await finger(pg, f'#loGuns [data-g="{gun}"]'); await pg.wait_for_timeout(150)
    await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)
    await pg.evaluate(FAST, 2); await pg.evaluate(DRAW, 6)

async def mrm_section(b, url):
    """item 2: the MRM (FOX 3): the swap, the radar box and its tones, the lock held until it is away, min range, the kill"""
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
    await start_rack(pg, 'pilot', 'mixed')
    await pg.evaluate(f"()=>{{{K}.DF.test.mSee=0;}}")   # item 4's bandit reaction off here (balance_section covers it)
    w = await pg.evaluate(W)
    ok('MIXED (Hard): 2 SRM + 2 MRM, SRM selected first; FOX reads FOX 2, SRM x2, and the swap line MRM 2', w['fox'] == 2 and w['mrm'] == 2 and w['wpn'] == 'srm' and w['L'] == 'FOX 2' and w['N'] == 'SRM x2' and 'MRM 2' in w['Wt'], w)
    await pg.evaluate(PLACE, [0, 3 * 1852, 1.6]); await pg.evaluate(FAST, 6)   # the wave's bandit off to the side: no lock (a press with a lock fires)
    await pg.evaluate(f"()=>{K}.hapLog(true)")
    await hold_fox(pg, 650); await pg.evaluate(DRAW, 4)
    w = await pg.evaluate(W); hl = [h['n'] for h in await pg.evaluate(f"()=>{K}.hapLog(true)")]
    ok('holding FOX 0.65 s swaps to the MRM: FOX 3, MRM x2, swap line SRM 2, cyan (mrm), a detent tick, nothing fired', w['wpn'] == 'mrm' and w['L'] == 'FOX 3' and w['N'] == 'MRM x2' and 'SRM 2' in w['Wt'] and 'mrm' in w['cls'] and not w['msl'] and 'detent' in hl and 'MRM' in w['side'], (w, hl))
    ok('the MRM shows its radar box on the boresight (the SRM circle is off)', ' on' in w['rad'] and ' on' not in w['seek'] and w['radT'] == 'MRM', w)
    # a bandit 6 nm ahead: past the SRM's 5 nm, inside the MRM's 10
    await pg.evaluate(PLACE, [0, 6 * 1852, 0]); await pg.evaluate(FAST, 3); await pg.evaluate(DRAW, 3)
    w = await pg.evaluate(W)
    ok('a bandit 6 nm ahead: the radar searches (box lit, MRM 6.0 nm), the MRM search chirp (no SRM growl)', w['st'] == 'search' and 'sr' in w['rad'] and w['radT'].startswith('MRM 6') and w['v'][0] == 0, w)
    await pg.evaluate(FAST, 18); await pg.evaluate(DRAW, 3)
    w = await pg.evaluate(W)
    ok('held in the box 2 s: lock (red box, LOCK), the MRM lock tone on, the SRM lock tone off', w['st'] == 'lock' and 'lk' in w['rad'] and w['radT'].startswith('LOCK') and w['v'][5] > 0 and w['v'][1] == 0 and 'lock' in w['cls'], w)
    await shot(pg, 'a2_mrm_lock_844.png')
    await pg.evaluate(f"()=>{K}.hapLog(true)")
    await finger(pg, '#bFox'); await pg.evaluate(FAST, 4); await pg.evaluate(DRAW, 2)
    w = await pg.evaluate(W)
    ok('FOX 3 with the lock: the release starts (HOLD, the button pulses), no missile yet 0.4 s in', w['rel'] and not w['msl'] and 'rel' in w['cls'] and w['radT'].startswith('HOLD'), w)
    await shot(pg, 'a2_mrm_hold_844.png')
    await pg.evaluate(FAST, 5)
    w = await pg.evaluate(W); hl = [h['n'] for h in await pg.evaluate(f"()=>{K}.hapLog(true)")]
    calls = await pg.evaluate(f"()=>{K}.DF.calls.slice(-4)")
    ok('the lock held 0.8 s: the MRM is away (one MRM left), the FOX 3 haptic (launch3) and the Fox three call', w['msl'] == ['mrm'] and w['mrm'] == 1 and w['ms'] == 1 and not w['rel'] and 'launch3' in hl and 'fox3' in calls, (w, hl, calls))
    for _ in range(30):
        await pg.evaluate(FAST, 10)
        w = await pg.evaluate(W)
        if w['kills'] >= 1 or not w['msl']: break
    ok('the MRM reaches the bandit 6 nm out and kills it (counted as a FOX 3 kill)', w['kills'] == 1 and w['mk'] == 1, w)
    # the abort: lock, FOX 3, then the bandit leaves the box before the missile is away
    await pg.evaluate(f"()=>{{const D={K}.DF;D.gap=0;D.kc=0;D.kcB=null;document.body.classList.remove('dfKc');D.test.wave(1);}}")   # past the wave's breather and kill cam
    await pg.evaluate(PLACE, [0, 4 * 1852, 0]); await pg.evaluate(FAST, 25)
    w = await pg.evaluate(W)
    ok('a second bandit at 4 nm: locked again', w['st'] == 'lock', w)
    await finger(pg, '#bFox'); await pg.evaluate(FAST, 2)
    await pg.evaluate(PLACE, [0, 4 * 1852, 0.6]); await pg.evaluate(FAST, 8); await pg.evaluate(DRAW, 2)
    w = await pg.evaluate(W)
    ok('the bandit leaves the box during the release: SHOT ABORTED, the missile stays on the rail', not w['rel'] and w['ab'] == 1 and w['mrm'] == 1 and not w['msl'] and 'SHOT ABORTED' in w['side'], w)
    # minimum range
    await pg.evaluate(PLACE, [0, 1100, 0]); await pg.evaluate(FAST, 4); await pg.evaluate(DRAW, 3)
    w = await pg.evaluate(W)
    ok('a bandit 0.6 nm ahead: inside the MRM minimum, the box says MIN RNG and never locks', w['min'] and w['st'] == 'none' and w['radT'] == 'MIN RNG' and 'min' in w['rad'], w)
    await finger(pg, '#bFox'); await pg.wait_for_timeout(100)
    w = await pg.evaluate(W)
    ok('FOX 3 inside the minimum: MIN RANGE, nothing fired', 'MIN RANGE' in w['side'] and not w['msl'] and w['mrm'] == 1, w)
    await shot(pg, 'a2_mrm_min_844.png')
    # the last MRM: the SRM comes up by itself
    await pg.evaluate(PLACE, [0, 3 * 1852, 0]); await pg.evaluate(FAST, 25)
    await finger(pg, '#bFox'); await pg.evaluate(FAST, 10); await pg.evaluate(DRAW, 3)
    w = await pg.evaluate(W)
    ok('the last MRM away: the SRM is selected by itself (FOX 2, SRM x2, no swap line)', w['mrm'] == 0 and w['wpn'] == 'srm' and w['L'] == 'FOX 2' and w['N'] == 'SRM x2' and w['Wt'] == '', w)
    await pg.evaluate(PLACE, [0, 1500, 0]); await pg.evaluate(FAST, 18); await pg.evaluate(DRAW, 3)
    w = await pg.evaluate(W)
    ok('the SRM: its circle again, locks with the SRM tone (not the MRM one)', ' on' in w['seek'] and ' on' not in w['rad'] and w['st'] == 'lock' and w['v'][1] > 0 and w['v'][5] == 0, w)
    await hold_fox(pg, 650)
    w = await pg.evaluate(W)
    ok('no MRM left: holding FOX does not swap', w['wpn'] == 'srm', w)
    ok('no console errors (MRM)', not pg.errs, pg.errs[:3])
    await pg.context.close()
    # a one type rack reads exactly as before: FOX 2, x6, no swap line; holding does nothing
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16', 'kgeuLoadout': '{"r":"std","g":"full"}'})
    await start_rack(pg, 'pilot', 'std')
    await hold_fox(pg, 650)
    w = await pg.evaluate(W)
    ok('STANDARD: FOX 2, x6, no swap line, the hold does not swap', w['L'] == 'FOX 2' and w['N'] == 'x6' and w['Wt'] == '' and w['wpn'] == 'srm' and w['mrm'] == 0, w)
    await pg.context.close()
    # the small phone: the button's three lines fit, the box on the boresight
    pg = await page(b, url, vp={'width': 568, 'height': 320}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
    await start_rack(pg, 'pilot', 'mixed')
    await pg.evaluate(PLACE, [0, 3 * 1852, 1.6]); await pg.evaluate(FAST, 6)
    await hold_fox(pg, 650)
    ok('568x320: the hold swaps to the MRM', await pg.evaluate(f"()=>{K}.DF.wpn") == 'mrm')
    await pg.evaluate(PLACE, [0, 5 * 1852, 0]); await pg.evaluate(FAST, 25); await pg.evaluate(DRAW, 6)
    fit = await pg.evaluate("()=>{const f=document.getElementById('bFox').getBoundingClientRect();return [...document.querySelectorAll('#bFox b,#bFox i,#bFox u')].every(e=>{const r=e.getBoundingClientRect();return r.left>=f.left-1&&r.right<=f.right+1&&r.top>=f.top&&r.bottom<=f.bottom})}")
    ok('568x320: FOX 3, MRM x2 and the swap line fit inside the button', fit)
    await shot(pg, 'a2_mrm_lock_568.png')
    ok('no console errors (568 MRM)', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def end_run(pg, kills):
    """kill `kills` bandits of wave 1 (test kills count as missile kills), then let the round clock run out; the card"""
    await pg.evaluate(f"(n)=>{{const D={K}.DF;D.test.noBanditFire=true;for(let i=0;i<n;i++){{D.gap=0;D.kc=0;D.test.wave(1);{K}.dfKill(D.bandits[0],'test');}}D.gap=0;D.kc=0;D.test.wave(1);D.t=1.5;}}", kills)
    await pg.evaluate(FAST, 40); await pg.wait_for_timeout(400)
    return await pg.evaluate(f"()=>({{sc:{K}.DF.sc,card:document.getElementById('arcOv').classList.contains('on'),lines:document.getElementById('aLines').innerText,score:document.getElementById('aScore').textContent,best:{K}.SCORE.best['arc:dogfight:hard']}})")

async def mult_section(b, url):
    """item 3: the multipliers on the card, the score they make, the base the boards get"""
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
    await open_brief(pg, 'pilot'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
    em = await pg.evaluate("()=>Object.fromEntries([...document.querySelectorAll('#dfLo .loR,#dfLo .loG')].map(e=>[e.dataset.r||e.dataset.g,e.querySelector('em').textContent]))")
    ok('Hard: each rack shows its multiplier (STANDARD x1.00, LIGHT x1.10, MIXED x1.05, LOW FLARES x1.10), the HALF gun +0.05', em == {'std': 'x1.00', 'light': 'x1.10', 'mixed': 'x1.05', 'bold': 'x1.10', 'full': '', 'half': '+0.05'}, em)
    x = await pg.evaluate("()=>{const e=document.getElementById('loX');return [e.firstChild.textContent,e.className]}")
    ok('the card total reads x1.00 for STANDARD with the full gun (not highlighted)', x[0] == 'x1.00' and 'up' not in x[1], x)
    await finger(pg, '#loRacks [data-r="light"]'); await finger(pg, '#loGuns [data-g="half"]'); await pg.wait_for_timeout(250)
    x = await pg.evaluate("()=>{const e=document.getElementById('loX');return [e.firstChild.textContent,e.className]}")
    ok('LIGHT with the HALF gun: x1.15, highlighted', x[0] == 'x1.15' and 'up' in x[1], x)
    f = await pg.evaluate(FIT)
    ok('844x390: still fits with the multipliers', not f['off'] and not f['scroll'] and not f['ov'] and not f['small'] and not f['clip'], f)
    await shot(pg, 'a3_card_mult_844.png')
    await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(FAST, 3)
    r = await end_run(pg, 3)
    sc = r['sc']
    want = round(sc['base'] * 1.15)
    ok('a run with LIGHT + HALF: score = base x 1.15 (3 kills and the wave bank), base kept for the boards', sc['base'] >= 300 and sc['score'] == want and sc['mult'] == 1.15 and sc['lo'] == 'light/half', sc)
    ok('the results card shows the multiplied score and the Multiplier row (x1.15, board points = base)', r['card'] and r['score'].startswith(format(want, ',')) and 'Multiplier' in r['lines'] and 'x1.15' in r['lines'] and ('board points ' + format(sc['base'], ',')) in r['lines'], (r['score'], r['lines']))
    ok('the local best keeps the card score', r['best'] and r['best']['pts'] == want, r['best'])
    await shot(pg, 'a3_results_844.png')
    # the default: no multiplier row, the score is the base
    await pg.evaluate(f"()=>{{{K}.arsPick('std','full');}}")
    await open_brief(pg, 'pilot'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300); await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(FAST, 3)
    r = await end_run(pg, 2)
    ok("STANDARD + FULL: the score is the base, no Multiplier row (today's card)", r['sc']['score'] == r['sc']['base'] >= 200 and r['sc']['mult'] == 1 and 'Multiplier' not in r['lines'], (r['sc'], r['lines']))
    # Easy's LOW FLARES is x1.05 (the auto flares soften it)
    await open_brief(pg, 'rookie'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
    em = await pg.evaluate("()=>document.querySelector('#dfLo .loR[data-r=bold] em').textContent")
    ok('Easy: LOW FLARES is x1.05 (Easy flares by itself twice a wave)', em == 'x1.05', em)
    ok('no console errors (multipliers)', not pg.errs, pg.errs[:3])
    await pg.context.close()

FIRE = f"""(kind)=>{{const K={K},D=K.DF,b=D.bandits[0];return K.dfShoot(b,kind);}}"""
MS = f"""()=>{{const D={K}.DF;return {{kills:D.kills,mk:D.mKills,def:D.mDef,masks:D.masks,lr:D.lrShots,hits:D.hits,rwr:D.rwr,
  msl:D.msl.filter(m=>m.on).map(m=>({{k:m.kind,dec:m.dec,lost:m.lost,foe:m.foe}})),calls:D.calls.slice(-6),st:D.bandits[0]&&D.bandits[0].state,flN:D.bandits[0]&&D.bandits[0].flN}}}}"""
FRESH = f"(n)=>{{const D={K}.DF;D.gap=0;D.kc=0;D.kcB=null;document.body.classList.remove('dfKc');for(const m of D.msl)if(m.on){{m.on=false;m.mesh.g.visible=false;}}D.test.wave(n||1);}}"

async def until(pg, cond_js, secs):
    for _ in range(int(secs * 2)):
        await pg.evaluate(FAST, 5)
        if await pg.evaluate(cond_js): return True
    return False

async def balance_section(b, url):
    """item 4: flares and radar missiles, the bandit's break against our MRM, terrain, the Hard long shot and its counterplay"""
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
    await start_rack(pg, 'pilot', 'mixed')
    await pg.evaluate(f"()=>{{const T={K}.DF.test;T.noBanditFire=true;T.mSee=0;}}")
    # flares: an SRM with the decoy forced goes for the flare, an MRM ignores it
    await pg.evaluate(FRESH); await pg.evaluate(PLACE, [0, 2500, 0]); await pg.evaluate(f"()=>{{{K}.DF.test.decoy=1;}}")
    await pg.evaluate(FIRE, 'srm'); await pg.evaluate(FAST, 7)
    m = await pg.evaluate(MS)
    ok('control: an SRM with the flare decoy forced rolls on the bandit\'s flares (decoyed)', any(x['k'] == 'srm' and x['dec'] for x in m['msl']), m)
    await pg.evaluate(FRESH); await pg.evaluate(PLACE, [0, 3 * 1852, 0])
    await pg.evaluate(FIRE, 'mrm'); await pg.evaluate(FAST, 15)
    await pg.evaluate(f"()=>{{const D={K}.DF,b=D.bandits[0];b.flN=2;b.flT=0;}}")   # the bandit pops two flares at it
    k0 = await pg.evaluate(f"()=>{K}.DF.kills")
    hit = await until(pg, f"()=>{K}.DF.kills>{k0}", 20)
    m = await pg.evaluate(MS)
    ok('flares do not spoof the MRM (decoy forced, the bandit flared): it kills', hit and m['mk'] == 1, m)
    # the bandit sees it go active and breaks: with the beat forced, it defeats the MRM
    await pg.evaluate(f"()=>{{const T={K}.DF.test;T.decoy=0;T.mSee=1;T.mBeat=1;T.hold=false;}}")
    await pg.evaluate(FRESH); await pg.evaluate(PLACE, [0, 5 * 1852, 0]); await pg.evaluate(f"()=>{{{K}.DF.test.hold=false;}}")
    await pg.evaluate(FIRE, 'mrm')
    ev = await until(pg, f"()=>{{const D={K}.DF;return D.bandits[0].state==='EVADE'}}", 15)
    ok('our MRM goes active 5 s out: the bandit (notice forced) breaks hard (EVADE)', ev, await pg.evaluate(MS))
    k0 = await pg.evaluate(f"()=>{K}.DF.kills")
    await until(pg, f"()=>{{const D={K}.DF;return D.mDef>=1||D.kills>{k0}||!D.msl.some(m=>m.on&&!m.foe)}}", 20)
    m = await pg.evaluate(MS)
    ok('in the last 2 s the hard break beats it (beat forced): no kill, the missile flies on, "He beat it"', m['def'] == 1 and m['kills'] == k0 and 'mrmMiss' in m['calls'], m)
    # the same with the beat refused: the hard break alone does not save him
    await pg.evaluate(f"()=>{{const T={K}.DF.test;T.mBeat=0;}}")
    await pg.evaluate(FRESH); await pg.evaluate(PLACE, [0, 5 * 1852, 0]); await pg.evaluate(f"()=>{{{K}.DF.test.hold=false;}}")
    k0 = await pg.evaluate(f"()=>{K}.DF.kills")
    await pg.evaluate(FIRE, 'mrm')
    await until(pg, f"()=>{{const D={K}.DF;return D.kills>{k0}||!D.msl.some(m=>m.on&&!m.foe)}}", 25)
    m = await pg.evaluate(MS)
    ok('beat refused: the MRM gets him through his break', m['kills'] == k0 + 1, m)
    # terrain: a target under the ridge line breaks the radar missile's track
    ok('dfMask: a line through the ground is masked, one high above is not', await pg.evaluate(f"""()=>{{const K={K},s=K.state(),V=THREE.Vector3;
      const a=new V(s.pos.x,s.pos.y,s.pos.z),lo=new V(s.pos.x+3000,-3000,s.pos.z),hi=new V(s.pos.x+3000,s.pos.y,s.pos.z);return K.dfMask(a,lo)&&!K.dfMask(a,hi)}}"""))
    await pg.evaluate(f"()=>{{const T={K}.DF.test;T.mSee=0;T.mBeat=0;T.hold=true;}}")
    await pg.evaluate(FRESH); await pg.evaluate(PLACE, [0, 4 * 1852, 0])
    k0 = await pg.evaluate(f"()=>{K}.DF.kills")
    await pg.evaluate(FIRE, 'mrm'); await pg.evaluate(FAST, 2)
    await pg.evaluate(f"()=>{{const D={K}.DF,b=D.bandits[0];b.p.y=-2500;}}")   # the target behind (under) the terrain
    await pg.evaluate(FAST, 5)
    m = await pg.evaluate(MS)
    ok('terrain between the MRM and its target: the track is lost (masks 1), no kill', m['masks'] >= 1 and m['kills'] == k0, m)
    ok('no console errors (balance, ours)', not pg.errs, pg.errs[:3])
    await pg.context.close()
    # ---- the bandits' long shot (Hard) ----
    pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16', 'kgeuLoadout': '{"r":"std","g":"full"}'})
    await start_rack(pg, 'pilot', 'std')
    HEAD_ON = f"""(d)=>{{const K={K},s=K.state(),D=K.DF,b=D.bandits[0],n=new THREE.Vector3(0,0,-1).applyQuaternion(s.quat);D.test.hold=true;
      b.p.copy(s.pos).addScaledVector(n,d);b.hdg=Math.atan2(-n.x,n.z);b.gam=0;b.bank=0;b.spd=230;b.state='TURN';b.st=0;b.alive=true;b.cool=0;
      b.v.set(Math.sin(b.hdg),0,-Math.cos(b.hdg)).multiplyScalar(b.spd);}}"""
    await pg.evaluate(f"()=>{{const D={K}.DF;D.test.noBanditFire=false;D.test.lr=1;D.wave=2;D.gap=0;D.test.wave(1);D.waveT=10;}}")
    lr = await pg.evaluate(f"()=>{K}.DF.bandits[0].lr")
    ok('Hard, wave 2 (long shot forced): the bandit carries the long shot', lr == 1, lr)
    await pg.evaluate(HEAD_ON, 7 * 1852)
    await pg.evaluate(FAST, 10)
    m = await pg.evaluate(MS)
    ok('7 nm head on: its long range radar is on us (our warning reads search)', m['rwr'] == 'search', m)
    await pg.evaluate(FAST, 22)
    m = await pg.evaluate(MS)
    ok('7 nm head on, us in its nose: its radar locks (our warning reads lock), out past the normal 4 nm', m['rwr'] in ('lock', 'launch'), m)
    fired = await until(pg, f"()=>{K}.DF.lrShots>=1", 6)
    m = await pg.evaluate(MS)
    ok('after its wait: the long shot (a radar missile, emrm), the launch warning and the radar call', fired and any(x['k'] == 'emrm' for x in m['msl']) and m['rwr'] == 'launch' and 'launchLr' in m['calls'], m)
    await pg.evaluate(f"()=>{{const D={K}.DF;D.test.decoy=1;{K}.dfPFlare(false);}}")
    m = await pg.evaluate(MS)
    ok('FLARES (decoy forced) do not fool it', any(x['k'] == 'emrm' and not x['dec'] for x in m['msl']), m)
    await shot(pg, 'a4_longshot_844.png')
    # BREAK when it is close: the hard turn beats its 20 g in the end game
    near = await until(pg, f"""()=>{{const K={K},D=K.DF,s=K.state();const m=D.msl.find(m=>m.on&&m.kind==='emrm');if(!m)return true;
      const R=m.p.distanceTo(s.pos);return R<2600}}""", 30)
    await pg.evaluate(f"()=>{{const D={K}.DF;D.brkCd=0;D.brk=0;{K}.dfBreak();}}")
    await until(pg, f"()=>{{const D={K}.DF;return !D.msl.some(m=>m.on&&m.kind==='emrm'&&!m.lost)}}", 12)
    m = await pg.evaluate(MS)
    ok('BREAK as it closes: the long shot overshoots (lost), no hit', near and m['hits'] == 0, m)
    ok('no console errors (long shot)', not pg.errs, pg.errs[:3])
    # Easy never sees one
    await pg.evaluate(f"()=>{{const K={K};K.setSkill('rookie');}}")
    n = await pg.evaluate(f"()=>{{const D={K}.DF;D.test.lr=null;let n=0;for(let i=0;i<40;i++){{D.wave=2+(i%3);D.test.wave(2);n+=D.bandits.filter(b=>b.lr).length;}}return n}}")
    ok('Easy: 40 waves from wave 2 on, never a long shot', n == 0, n)
    await pg.evaluate(f"()=>{{const K={K};K.setSkill('pilot');}}")
    n = await pg.evaluate(f"()=>{{const D={K}.DF;D.test.lr=null;let n=0;for(let i=0;i<200;i++){{D.wave=2+(i%3);D.test.wave(2);n+=D.bandits.filter(b=>b.lr).length;}}return n}}")
    ok('Hard: about 6 waves in 10 from wave 2 carry one (200 waves: 90 to 150)', 90 <= n <= 150, n)
    n = await pg.evaluate(f"()=>{{const D={K}.DF;let n=0;for(let i=0;i<50;i++){{D.wave=1;D.test.wave(1);n+=D.bandits.filter(b=>b.lr).length;}}return n}}")
    ok('Hard wave 1: never', n == 0, n)
    await pg.context.close()

async def submit_section(b, url):
    """item 5: the run submission carries the loadout and multiplier with the base score; the card shows the loadout; the XP burst"""
    m = Mock(gain=37)
    st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'}; st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await start_rack(pg, 'pilot', 'light', 'half')
    r = await end_run(pg, 3)
    for _ in range(20):
        if m.subs: break
        await pg.wait_for_timeout(300)
    sub = m.subs[-1] if m.subs else {}
    df = sub.get('df') or {}
    sc = r['sc']
    ok('the submission: df:score:hard, the BASE score (what the Worker can check), the stats as before', sub.get('board') == 'df:score:hard' and sub.get('score') == sc['base'] and df.get('kills') == 3 and 'bank' in df, {k: sub.get(k) for k in ('board', 'score', 'mode')})
    ok('the df block carries the loadout (light/half), the multiplier (1.15) and the card points', df.get('lo') == 'light/half' and df.get('mult') == 1.15 and df.get('pts') == sc['score'] and df.get('srm') == 4 and df.get('mrm') == 0, df)
    await pg.wait_for_timeout(2500)
    card = await pg.evaluate("()=>{const x=document.querySelector('#arcOv .rXp');return {lines:document.getElementById('aLines').innerText,xp:x&&x.textContent,done:!!(x&&x.classList.contains('done'))}}")
    ok('the results card shows the loadout used (LIGHT · 4 SRM · 250 rds) and the Multiplier row', 'Loadout' in card['lines'] and 'LIGHT · 4 SRM · 250 rds' in card['lines'] and 'x1.15' in card['lines'], card['lines'])
    ok('the XP count up from ui1 still plays on the card (+37 XP, done)', card['xp'] and '+37' in card['xp'] and card['done'], card)
    await shot(pg, 'a5_results_xp_844.png')
    # an MRM run: the card counts the radar missiles
    await pg.evaluate(f"()=>{{{K}.arsPick('mixed','full');}}")
    await start_rack(pg, 'pilot', 'mixed')
    await pg.evaluate(f"()=>{{const D={K}.DF;D.test.mSee=0;D.test.noBanditFire=true;}}")
    await pg.evaluate(f"()=>{{const D={K}.DF;D.gap=0;D.kc=0;D.test.wave(1);}}"); await pg.evaluate(PLACE, [0, 4 * 1852, 0])
    await pg.evaluate(FIRE, 'mrm')
    await until(pg, f"()=>{K}.DF.kills>=1", 25)
    n0 = len(m.subs)
    r = await end_run(pg, 0)
    for _ in range(20):
        if len(m.subs) > n0: break
        await pg.wait_for_timeout(300)
    df = (m.subs[-1] if len(m.subs) > n0 else {}).get('df') or {}
    ok('an MRM kill: the df block counts it (msh 1, mk 1, lo mixed/full, mult 1.05)', df.get('msh') == 1 and df.get('mk') == 1 and df.get('lo') == 'mixed/full' and df.get('mult') == 1.05, df)
    lines = await pg.evaluate("()=>document.getElementById('aLines').innerText")
    ok('the card: Loadout MIXED · 2 SRM + 2 MRM · 510 rds and Radar missiles 1 of 1 hit', 'MIXED · 2 SRM + 2 MRM · 510 rds' in lines and 'Radar missiles' in lines and '1 of 1 hit' in lines, lines)
    ok('no console errors (submission)', not pg.errs, pg.errs[:3])
    await pg.context.close()
    # the small phone: the results card with the extra rows still fits
    m = Mock(gain=37)
    st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'}; st.update(m.storage())
    pg = await page(b, url, vp={'width': 568, 'height': 320}, storage=st, pre=m.install)
    await start_rack(pg, 'pilot', 'light', 'half')
    await end_run(pg, 3); await pg.wait_for_timeout(2500)
    fit = await pg.evaluate("""()=>{const o=document.getElementById('arcOv'),sh=o.querySelector('.sheet').getBoundingClientRect(),L=document.getElementById('aLines');
      const btn=[...o.querySelectorAll('.rBtns button')].map(e=>e.getBoundingClientRect());
      return {inView:sh.top>=-0.5&&sh.bottom<=innerHeight+0.5,btns:btn.every(r=>r.bottom<=innerHeight&&r.height>=44),scroll:L.scrollHeight>L.clientHeight+1,clip:[...L.querySelectorAll('*')].filter(e=>e.children.length===0&&e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)}}""")
    ok('568x320: the results card with Loadout and Multiplier fits (sheet in view, buttons reachable; the rows may scroll inside)', fit['inView'] and fit['btns'], fit)
    await shot(pg, 'a5_results_568.png')
    ok('no console errors (568 results)', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
        # ---- 1. the card between the briefing and FIGHT'S ON ----
        await open_brief(pg, 'pilot')
        br = await pg.evaluate("()=>{const r=document.getElementById('dfbNext').getBoundingClientRect();return {brief:document.getElementById('dfBrief').classList.contains('on'),lo:document.getElementById('dfLo').classList.contains('on'),txt:document.getElementById('dfbNext').textContent,c:[r.left+r.width/2,r.top+r.height/2]}}")
        ok('the briefing ends in LOADOUT (the card is not up yet)', br['brief'] and not br['lo'] and br['txt'] == 'LOADOUT', br)
        await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        f = await pg.evaluate(FIT)
        s = await pg.evaluate(STORES)
        ok('LOADOUT: the briefing gives way to the loadout card, the sim still held (clock 90)', f['on'] and s['brief'] and s['t'] == 90 and not await pg.evaluate("()=>document.getElementById('dfBrief').classList.contains('on')"), (f['on'], s))
        txt = await pg.inner_text('#dfLo')
        ok('the card: LOADOUT, HARD, the racks (STANDARD, LIGHT, LOW FLARES), the gun (510 and 250 rds), FIGHT\'S ON', all(t in txt for t in ('LOADOUT', 'HARD', 'STANDARD', 'LIGHT', 'LOW FLARES', '510 rds', '250 rds', "FIGHT'S ON")), txt)
        ck = await pg.evaluate("()=>[...document.querySelectorAll('#dfLo [aria-checked=true]')].map(e=>e.dataset.r||e.dataset.g)")
        ok('a new install picks STANDARD and the FULL gun', ck == ['std', 'full'], ck)
        ok('the summary under the jet says today\'s stores: 6 SRM, 30 flares, 510 rds', (await pg.inner_text('#loSum')) == '6 SRM · 30 flares · 510 rds', (await pg.inner_text('#loSum')))
        ok('the jet drawing shows six missiles on the stations', await pg.evaluate("()=>document.querySelectorAll('#loJet g').length") == 6)
        ok('844x390: the card fits (nothing off screen, no scroll, no overlap, every target 44 px, no clipped text)', not f['off'] and not f['scroll'] and not f['ov'] and not f['small'] and not f['clip'], f)
        gc = [(f['go'][0] + f['go'][2]) / 2, (f['go'][1] + f['go'][3]) / 2]
        ok("FIGHT'S ON sits where LOADOUT was (two taps in one place fly today's fight): within 60 px", abs(gc[0] - br['c'][0]) < 60 and abs(gc[1] - br['c'][1]) < 60, (gc, br['c']))
        await shot(pg, 'a1_card_844.png')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)
        await pg.evaluate(STEP, 10)
        s = await pg.evaluate(STORES)
        ok("FIGHT'S ON with the defaults: today's fight (6 FOX 2, 510 rounds, 30 flares), the clock runs", s['on'] and not s['brief'] and s['fox'] == 6 and s['rounds'] == 510 and s['flares'] == 30 and s['mrm'] == 0 and s['t'] < 90, s)
        ok('the buttons show the stores', await pg.inner_text('#bFoxN') == 'x6' and await pg.inner_text('#bGunN') == '510' and await pg.inner_text('#bFlrN') == '30')
        # ---- the picks: LIGHT and the HALF gun, kept for the next run ----
        await open_brief(pg, 'pilot'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        await finger(pg, '#loRacks [data-r="light"]'); await pg.wait_for_timeout(150)
        await finger(pg, '#loGuns [data-g="half"]'); await pg.wait_for_timeout(150)
        ck = await pg.evaluate("()=>[...document.querySelectorAll('#dfLo [aria-checked=true]')].map(e=>e.dataset.r||e.dataset.g)")
        ok('a tap picks a rack and a gun (one each)', ck == ['light', 'half'], ck)
        ok('the summary and the drawing follow the pick: 4 SRM, 250 rds, four missiles', (await pg.inner_text('#loSum')) == '4 SRM · 30 flares · 250 rds' and await pg.evaluate("()=>document.querySelectorAll('#loJet g').length") == 4, (await pg.inner_text('#loSum')))
        await shot(pg, 'a1_light_844.png')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(STEP, 5)
        s = await pg.evaluate(STORES)
        ok('LIGHT with the HALF gun: 4 FOX 2, 250 rounds, 30 flares', s['fox'] == 4 and s['rounds'] == 250 and s['flares'] == 30 and s['lo'] == 'light' and s['g'] == 'half', s)
        kept = await pg.evaluate("()=>localStorage.getItem('kgeuLoadout')")
        ok('the pick is kept (kgeuLoadout)', kept == '{"r":"light","g":"half"}', kept)
        await open_brief(pg, 'pilot'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        ck = await pg.evaluate("()=>[...document.querySelectorAll('#dfLo [aria-checked=true]')].map(e=>e.dataset.r||e.dataset.g)")
        ok('the next run opens on the kept pick', ck == ['light', 'half'], ck)
        await finger(pg, '#loRacks [data-r="bold"]'); await finger(pg, '#loGuns [data-g="full"]'); await pg.wait_for_timeout(150)
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(STEP, 5)
        s = await pg.evaluate(STORES)
        ok('LOW FLARES: 6 FOX 2 and only 12 flares', s['fox'] == 6 and s['flares'] == 12 and s['rounds'] == 510, s)
        # ---- Easy: the same racks with Easy's counts ----
        await open_brief(pg, 'rookie'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        await finger(pg, '#loRacks [data-r="std"]'); await pg.wait_for_timeout(150)
        txt = await pg.inner_text('#dfLo')
        ok('Easy: the EASY chip, STANDARD is 10 SRM, LIGHT 6 SRM', 'EASY' in txt and '10 SRM' in txt and '6 SRM' in txt, txt)
        await shot(pg, 'a1_card_easy_844.png')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(STEP, 5)
        s = await pg.evaluate(STORES)
        ok("Easy STANDARD with the full gun: today's Easy fight (10 FOX 2, 510 rounds, 30 flares)", s['fox'] == 10 and s['rounds'] == 510 and s['flares'] == 30, s)
        ok('no console errors (844x390)', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await mrm_section(b, url)
        await mult_section(b, url)
        await balance_section(b, url)
        await submit_section(b, url)
        # ---- the small phones ----
        for vp, nm in (({'width': 667, 'height': 375}, '667'), ({'width': 568, 'height': 320}, '568'), ({'width': 932, 'height': 430}, '932')):
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
            await open_brief(pg, 'pilot')
            c0 = await pg.evaluate("()=>{const r=document.getElementById('dfbNext').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,r.bottom<=innerHeight]}")
            await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
            f = await pg.evaluate(FIT)
            ok(f'{nm}: the card fits (nothing off screen, no scroll, no overlap, every target 44 px, no clipped text)', f['on'] and not f['off'] and not f['scroll'] and not f['ov'] and not f['small'] and not f['clip'], f)
            gc = [(f['go'][0] + f['go'][2]) / 2, (f['go'][1] + f['go'][3]) / 2]
            ok(f"{nm}: FIGHT'S ON within 60 px of LOADOUT, 60 px tall or more", c0[2] and abs(gc[0] - c0[0]) < 60 and abs(gc[1] - c0[1]) < 60 and f['go'][3] - f['go'][1] >= 60, (gc, c0, f['go']))
            await shot(pg, f'a1_card_{nm}.png')
            ok(f'no console errors ({nm})', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    srv.shutdown()
    return ok.done('arsenal_check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
