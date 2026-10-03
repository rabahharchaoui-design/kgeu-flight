# Red Flag Dogfight modes and scoring (5.5): FOX 2, GUN and FLARES 60 pt or larger, clear of each other, the throttle,
# VIEW, pause, the stick and the call strip, within thumb reach, at 844x390, 568x320, 667x375 and 932x430; Easy vs Hard
# DF_CFG; Hard's energy fight (a sustained hard turn bleeds speed below the burner, the burner holds it) and the 9 G
# limit (never over 9.05), the grey vision closing in over 7.5 g and clearing, none in Easy, the G readout; dfScore()
# arithmetic, stars and grades; the results card rows; the records per mode on the arcade card and the records screen
# (the old arc:dogfight key untouched); the four achievements at their events (DF.ach, the strip, Flare Save never from
# Easy's auto flares); the victory roll after a hit; "Good kill!" on a close gun kill; a simple bot in Easy and Hard
# with fixed seeds; no console errors.
# Run: .venv/bin/python tests/dogfight_modes_check.py
import asyncio, json, math, re, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = "window.__kgeu"
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);}"
UNTIL = """([cond,max])=>{const K=window.__kgeu,D=K.DF,s=K.state(),t0=s.time,f=new Function('K','D','return ('+cond+')');
  for(let i=0;i<max*10;i++){K.stepFrame(0.1,false,true);if(f(K,D))break;}return s.time-t0;}"""
PLACE = """([i,d,off])=>{const K=window.__kgeu,s=K.state(),D=K.DF,b=D.bandits[i];D.test.hold=true;
  const q=s.quat.clone();if(off)q.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),off));
  const n=new THREE.Vector3(0,0,-1).applyQuaternion(q);b.p.copy(s.pos).addScaledVector(n,d);
  const v=s.vel;b.hdg=Math.atan2(v.x,-v.z);b.gam=Math.asin(Math.max(-1,Math.min(1,v.y/v.length())));b.bank=0;b.spd=v.length();b.state='TURN';b.st=0;b.hp=1;
  b.v.set(Math.sin(b.hdg)*Math.cos(b.gam),Math.sin(b.gam),-Math.cos(b.hdg)*Math.cos(b.gam)).multiplyScalar(b.spd);b.g.position.copy(b.p);return true;}"""
# a held turn: the stick pulls for a g target (or full back), the wings held at the bank a level turn at that g needs
TURN = """([gT,thr,secs,kt0,full])=>{const K=window.__kgeu,s=K.state(),T=K.touchIn,D=K.DF;
  if(kt0)s.vel.multiplyScalar(kt0/(s.ias*1.943844));
  T.active=true;s.throttle=s.power=thr;const e=new THREE.Euler(0,0,0,'YXZ');let gmax=0,el=0.4,kt=[],gv=[],op=[];
  for(let i=0;i<secs*20;i++){e.setFromQuaternion(s.quat,'YXZ');const bank=-e.z,want=Math.acos(Math.min(0.995,1/gT));
    T.ail=Math.max(-1,Math.min(1,(want-bank)*2));if(full)el=1;else{el+=(gT-s.gload)*0.02;el=Math.max(-1,Math.min(1,el));}T.elev=el;s.throttle=thr;
    K.stepFrame(0.05,false,true);if(i>3)gmax=Math.max(gmax,s.gload);
    if(i%20===19){kt.push(+(s.ias*1.943844).toFixed(1));gv.push(+D.gv.toFixed(3));op.push(+getComputedStyle(document.querySelector('#dfGv .o')).opacity);}}
  return {gmax:gmax,kt:kt,gv:gv,op:op,g:s.gload};}"""
REL = "(secs)=>{const K=window.__kgeu,T=K.touchIn,D=K.DF,s=K.state();T.active=true;T.ail=0;T.elev=0;let r=[];for(let i=0;i<secs*20;i++){K.stepFrame(0.05,false,true);if(i%10===9)r.push([+s.gload.toFixed(2),+D.gv.toFixed(3),+getComputedStyle(document.querySelector('#dfGv .o')).opacity]);}T.active=false;return r;}"

# the bot: steer at the nearest bandit (a little lead), Fox 2 on a lock (one missile on a bandit at a time), the gun
# when it sits on the nose inside 850 m, FLARES 1.5 s before a missile arrives; back toward the middle past 7 nm.
# Easy flies its bank and pitch commands, Hard rolls and pulls. Coarse 0.1 s steps.
BOT = """([secs,dt])=>{
 const K=window.__kgeu,s=K.state(),D=K.DF,T=K.touchIn,ez=K.skill()!=='pilot',cl=(x,a,b)=>Math.max(a,Math.min(b,x));
 const B=D.bot||(D.bot={iq:new THREE.Quaternion(),v:new THREE.Vector3(),w:new THREE.Vector3(),e:new THREE.Euler(0,0,0,'YXZ'),hit1:null,fl:0});
 T.active=true;
 for(let i=0;i<secs/dt;i++){
  if(!D.on||D.done)break;
  s.throttle=ez?0.8:1;
  let nb=null,nr=1e9;for(const b of D.bandits){if(!b.alive)continue;const r=b.p.distanceTo(s.pos);if(r<nr){nr=r;nb=b;}}
  const ft=(s.pos.y-1.5)*3.28084+1071,dcx=D.C.x-s.pos.x,dcz=D.C.z-s.pos.z,dc=Math.hypot(dcx,dcz);let off=9;
  if(nb){const v=B.v;v.copy(nb.p).addScaledVector(nb.v,Math.min(1.2,nr/800)).sub(s.pos);
    if(dc>D.R*0.6){const L=v.length();v.set(dcx/dc*L,v.y,dcz/dc*L);}
    if(ft<8000)v.y=Math.max(v.y,v.length()*0.35);
    B.iq.copy(s.quat).invert();v.applyQuaternion(B.iq);off=Math.atan2(Math.hypot(v.x,v.y),-v.z);
    if(ez){B.w.copy(v).applyQuaternion(s.quat);B.e.setFromQuaternion(s.quat,'YXZ');const hd=Math.atan2(B.w.x,-B.w.z),h0=-B.e.y,hx=Math.atan2(Math.sin(hd-h0),Math.cos(hd-h0));
      T.ail=cl(hx*6,-1,1);T.elev=cl((Math.atan2(B.w.y,Math.hypot(B.w.x,B.w.z))-B.e.x)*3,-1,1);}
    else if(off<0.12){T.ail=cl(v.x/-v.z*8,-1,1);T.elev=cl(v.y/-v.z*10,-0.5,1);}
    else{const roll=Math.atan2(v.x,v.y);T.ail=cl(roll*1.6,-1,1);T.elev=Math.abs(roll)<1.0?cl(off*3,0,1):0.15;}}
  else{T.ail=0;T.elev=ft<9000?0.3:0;}
  if(D.seek.state==='lock'&&D.seek.b&&!D.msl.some(m=>m.on&&!m.foe&&m.b===D.seek.b))K.dfFox();
  D.gunHeld=!!(nb&&nr<850&&off<0.05&&D.rounds>0);
  for(const m of D.msl){if(!m.on||!m.foe||m.dec||m.lost||m.pf)continue;
    const dx=s.pos.x-m.p.x,dy=s.pos.y-m.p.y,dz=s.pos.z-m.p.z,R=Math.hypot(dx,dy,dz),vc=-(dx*(s.vel.x-m.v.x)+dy*(s.vel.y-m.v.y)+dz*(s.vel.z-m.v.z))/R;
    if(vc>1&&R/vc<=1.5){K.dfPFlare(false);B.fl++;break;}}
  const h0=D.hits;K.stepFrame(dt,false,true);if(D.hits>h0&&B.hit1===null)B.hit1=+D.fightT.toFixed(1);
 }
 D.gunHeld=false;T.active=false;
 const r={done:!D.on||D.done,why:D.why,kills:D.kills,gun:D.gunKills,hits:D.hits,wave:D.wave,fightT:+D.fightT.toFixed(1),firstHit:B.hit1,flares:B.fl,score:D.sc?D.sc.score:null};
 if(r.done)D.bot=null;return r;}"""

async def step(pg, secs):
    await pg.evaluate(STEP, int(round(secs * 10)))

async def until(pg, cond, mx):
    return await pg.evaluate(UNTIL, [cond, mx])

async def start(pg, skill='pilot', quiet=True):
    await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.setSkill('{skill}');D.test.seed=null;D.test.hold=false;D.test.noBanditFire={'true' if quiet else 'false'};D.test.decoy=0;D.test.noDecoy=false;D.test.noBrief=true;K.windSeed(7);K.dfStart();}}")
    await pg.wait_for_timeout(300); await step(pg, 0.2)

def ovl(a, b):
    return a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']

RECTS = """()=>{const R=s=>{const e=document.querySelector(s);if(!e)return null;const c=getComputedStyle(e);if(c.display==='none'||c.visibility==='hidden')return null;
    const r=e.getBoundingClientRect();return r.width<1?null:{x:r.x,y:r.y,w:r.width,h:r.height}};
  const sb=document.getElementById('dfSub').getBoundingClientRect(),sz=document.getElementById('stickZone').getBoundingClientRect();
  return {fox:R('#bFox'),gun:R('#bGun'),flr:R('#bFlr'),view:R('#bCam'),pause:R('#bPause'),hint:R('#stickHint'),thr:R('#thr'),
    strip:{x:sb.x,y:sb.bottom-32,w:sb.width,h:32},stickR:sz.right,W:innerWidth,H:innerHeight}}"""

async def layout(pg, vp):
    await pg.set_viewport_size({'width': vp[0], 'height': vp[1]}); await pg.wait_for_timeout(400)
    await pg.evaluate(f"()=>{K}.dfCall('launch')"); await step(pg, 0.2)
    r = await pg.evaluate(RECTS)
    lab = f'{vp[0]}x{vp[1]}'
    W = ('fox', 'gun', 'flr')
    hit = []
    for i, a in enumerate(W):
        for b in W[i + 1:] + ('view', 'pause', 'hint', 'thr', 'strip'):
            if r[a] and r[b] and ovl(r[a], r[b]): hit.append((a, b))
    size = {k: (round(r[k]['w']), round(r[k]['h'])) for k in W if r[k]}
    on = all(r[k] and r[k]['x'] >= 0 and r[k]['y'] >= 0 and r[k]['x'] + r[k]['w'] <= r['W'] and r[k]['y'] + r[k]['h'] <= r['H'] for k in W)
    ok(f'{lab}: FOX 2, GUN and FLARES on screen, each 60 pt or larger', on and len(size) == 3 and all(min(v) >= 60 for v in size.values()), size)
    ok(f'{lab}: they overlap nothing (each other, the throttle, VIEW, pause, the stick, the call strip) and sit right of the stick zone',
       not hit and all(r[k]['x'] >= r['stickR'] for k in W), (hit, r['stickR']))
    # reach: from where the right thumb rests, just left of the throttle at the bottom
    ax, ay = r['thr']['x'], r['thr']['y'] + r['thr']['h']
    d = {k: round(math.hypot(r[k]['x'] + r[k]['w'] / 2 - ax, r[k]['y'] + r[k]['h'] / 2 - ay)) for k in W}
    ok(f'{lab}: in thumb reach (centres from the thumb rest: FOX 2 and GUN under 190 pt, FLARES under 240)', d['fox'] < 190 and d['gun'] < 190 and d['flr'] < 240, d)
    print('     ', lab, 'rest', (round(ax), round(ay)), {k: {'w': size[k][0], 'cx': round(r[k]['x'] + r[k]['w'] / 2), 'cy': round(r[k]['y'] + r[k]['h'] / 2), 'reach': d[k]} for k in W})

async def kill_wave(pg, how):
    await pg.evaluate(f"(h)=>{{const D={K}.DF;D.bandits.slice().forEach((b,i)=>{{if(b.alive){K}.dfKill(b,Array.isArray(h)?h[i%h.length]:h);}});}}", how)

async def to_next_wave(pg):
    await until(pg, "D.gap<=0&&D.bandits.some(b=>b.alive)||!D.on", 8)

CARD = "()=>({on:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText,letter:document.getElementById('aLetter').textContent,score:document.getElementById('aScore').textContent,stars:(document.getElementById('aStars').textContent.match(/★/g)||[]).length-(document.querySelector('#aStars u')?document.querySelector('#aStars u').textContent.length:0)})"

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        old = json.dumps({'log': {'time': 0, 'landings': 0, 'streak': 0, 'bestStreak': 0}, 'best': {'arc:dogfight': {'pts': 300, 'kills': 3, 'stars': 1, 'mode': 'hard'}}, 'ach': {}})
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16', 'kgeuScores': old})
        # ---- 1. the weapon buttons at the four viewports ----
        await start(pg)
        for vp in ((844, 390), (568, 320), (667, 375), (932, 430)):
            await layout(pg, vp)
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        # ---- 2. Easy vs Hard tunables ----
        c = await pg.evaluate(f"()=>{K}.DF_CFG")
        e, h = c['easy'], c['hard']
        ok('Easy: bigger seeker, faster lock, bandits 0.8 speed and 0.75 g, bandit lock 5 s, auto flares 2 a wave, no grey vision, no energy bleed',
           e['seek'] > h['seek'] and e['lock'] < h['lock'] and e['spd'] == 0.8 and e['g'] == 0.75 and e['rLock'] == 5 and e['autoFlr'] == 2 and e['gv'] == 0 and e['eDrag'] == 0, e)
        ok('Hard: no auto flares, grey vision on, the energy bleed on, the 9 G limit (both modes)', h['autoFlr'] == 0 and h['gv'] == 1 and h['eDrag'] > 0 and h['gLim'] == 9 and e['gLim'] == 9, h)
        # ---- 3. Hard: the energy fight, the g limit, the grey vision ----
        await start(pg)
        mil = await pg.evaluate(TURN, [7, 0.8, 3, 400, 0])
        await start(pg)
        ab = await pg.evaluate(TURN, [7, 1, 3, 400, 0])
        bleed = (mil['kt'][0] - mil['kt'][-1]) / 2
        hold = (ab['kt'][0] - ab['kt'][-1]) / 2
        ok('Hard: a sustained 7 g turn at 400 kt below the burner bleeds 15 to 25 kt a second', 15 <= bleed <= 25, (round(bleed, 1), mil['kt']))
        ok('Hard: the same turn in full burner holds roughly level (under 4 kt a second either way)', abs(hold) < 4, (round(hold, 1), ab['kt']))
        await start(pg)
        lim = await pg.evaluate(TURN, [9, 1, 4.5, 600, 1])
        ok('Hard: full stick at 600 kt pulls to the 9 G limit and never past 9.05', 8.6 < lim['gmax'] <= 9.05, round(lim['gmax'], 3))
        ok('Hard: over 7.5 g the grey vision closes in (rising each second, nearly full after 4 s at 9 g)',
           all(lim['gv'][i] < lim['gv'][i + 1] for i in range(3)) and lim['gv'][3] >= 0.85 and lim['op'][0] > 0 and lim['op'][-1] >= 0.95, (lim['gv'], lim['op']))
        gr = await pg.evaluate("()=>{const g=document.getElementById('hG');return {t:g.textContent,vis:getComputedStyle(g).display!=='none',c:g.className,i:getComputedStyle(document.querySelector('#dfGv .i')).opacity,bg:getComputedStyle(document.querySelector('#dfGv .i')).backgroundImage}}")
        ok('the G readout by the gauges shows the g (red near the limit), the inner ring is in, its middle clear',
           gr['vis'] and re.match(r'^\d\.\d G$', gr['t']) and gr['c'] == 'r' and float(gr['i']) > 0.5 and 'rgba(70, 72, 76, 0) 20%' in gr['bg'], gr)
        rel = await pg.evaluate(REL, 3)
        ok('let go under 5 g: it clears within about 2 s', rel[-1][1] == 0 and rel[-1][2] == 0 and any(x[1] > 0 for x in rel[:2]), rel)
        # Easy: no grey vision, no g effects
        await start(pg, 'rookie')
        await pg.evaluate(f"()=>{{{K}.DF.gv=0.6;}}"); ez = await pg.evaluate(TURN, [9, 1, 2, 500, 1])
        ok('Easy: no grey vision (forced in, it is gone the next frame; a full pull shows none)', max(ez['gv']) == 0 and max(ez['op']) == 0, ez)
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        # ---- 4. dfScore arithmetic, stars, grades ----
        sc = await pg.evaluate(f"""()=>{{const K={K};return [K.dfScore({{kills:10,gunKills:3,hits:1,bank:[20,15,10,5],won:true,clearT:250.25,fightT:251.4,flareSaves:2,mode:'hard'}}),
          K.dfScore({{kills:4,gunKills:0,hits:2,bank:[30.2,12],won:false,fightT:200,mode:'easy'}}),K.dfScore({{kills:0,hits:3,bank:[],won:false,fightT:40,mode:'hard'}})]}}""")
        ok('dfScore: 10 kills, 3 by gun, 1 hit, 20+15+10+5 s banked, a win: 700 + 600 + 100 - 75 + 250 = 1,575 (with the run\'s fields)',
           sc[0]['score'] == 1575 and sc[0]['waves'] == 4 and sc[0]['won'] and sc[0]['clearT'] in (250.2, 250.3) and sc[0]['secs'] == 251 and sc[0]['flareSaves'] == 2 and sc[0]['mode'] == 'hard' and sc[0]['gunKills'] == 3, sc[0])
        ok('dfScore: 4 missile kills, 2 hits, 31 + 12 s banked (whole seconds up), no win: 400 + 86 - 150 = 336, 2 waves, no clear time',
           sc[1]['score'] == 336 and sc[1]['waves'] == 2 and sc[1]['clearT'] is None and sc[1]['mode'] == 'easy', sc[1])
        ok('dfScore: no kills, 3 hits: never under 0', sc[2]['score'] == 0, sc[2])
        th = await pg.evaluate(f"()=>{{const K={K};return [[299,300,899,900,1499,1500].map(K.dfStars),[299,300,699,700,1099,1100,1499,1500].map(K.dfGrade).join('')]}}")
        ok('stars at 300, 900, 1,500; grades A 1,500, B 1,100, C 700, D 300, F below', th[0] == [0, 1, 1, 2, 2, 3] and th[1] == 'FDDCCBBA', th)
        # ---- 5 to 7. a Hard win with gun kills and a hit: the card, the records, the achievements ----
        await pg.evaluate(f"()=>{{const A={K}.SCORE.ach;for(const k in A)delete A[k];}}")
        await start(pg)
        await kill_wave(pg, 'gun')
        g1 = await pg.evaluate(f"()=>({{ach:{K}.DF.ach.slice(),got:!!{K}.SCORE.ach.guns,sub:document.querySelector('#dfSub span').textContent,banner:document.getElementById('banner').classList.contains('on')}})")
        ok('Guns Kill: granted at the gun kill, listed in DF.ach, shown in the bottom strip (no banner over the fight)', g1['ach'] == ['guns'] and g1['got'] and 'Achievement: Guns Kill' in g1['sub'] and not g1['banner'], g1)
        await to_next_wave(pg); await kill_wave(pg, ['gun', 'gun'])
        await to_next_wave(pg)
        await pg.evaluate(f"()=>{K}.dfHit('msl',null)")
        await kill_wave(pg, ['fox2', 'gun', 'fox2'])
        a5 = await pg.evaluate(f"()=>({{ach:{K}.DF.ach.slice(),kills:{K}.DF.kills,got:!!{K}.SCORE.ach.ace}})")
        ok('Ace: granted at the 5th kill', a5['kills'] == 6 and a5['ach'][:2] == ['guns', 'ace'] and 'ace' in a5['ach'] and a5['got'], a5)
        await to_next_wave(pg); await kill_wave(pg, 'fox2')
        await until(pg, "document.getElementById('arcOv').classList.contains('on')", 12); await pg.wait_for_timeout(300)
        card = await pg.evaluate(CARD)
        r = await pg.evaluate(f"()=>{{const K={K},D=K.DF;return {{sc:D.sc,ach:D.ach.slice(),best:K.SCORE.best['arc:dogfight:hard'],old:K.SCORE.best['arc:dogfight'],run:K.runs()[0],bonus:D.bank.reduce((a,x)=>a+Math.ceil(x),0)*2}}}}")
        s = r['sc']
        want = 6 * 100 + 4 * 200 + r['bonus'] - 75 + 250
        ok('the run scores by the formula (6 missile kills, 4 by gun, 1 hit, the time bonus, the win)', s and s['score'] == want and s['kills'] == 10 and s['gunKills'] == 4 and s['hits'] == 1, (s, want))
        letter = await pg.evaluate(f"(p)=>{K}.dfGrade(p)", s['score']); st = await pg.evaluate(f"(p)=>{K}.dfStars(p)", s['score'])
        rows = card['lines']
        ok('results card: the grade, the score, All bandits down, the stars', card['on'] and card['letter'] == letter and card['score'].startswith(f"{s['score']:,} pts") and 'All bandits down' in card['title'] and card['stars'] == st, card)
        ok('results card rows: Kills 10 (4 by gun), Waves cleared 4/4, Hits taken 1, Time bonus, Clear time m:ss.s',
           'Kills\n10 (4 by gun)' in rows and 'Waves cleared\n4/4' in rows and 'Hits taken\n1 of 3' in rows and f"Time bonus\n+{r['bonus']:,}" in rows and re.search(r'Clear time\n\d+:\d\d\.\d', rows), rows)
        ok('not Untouchable (a hit was taken)', 'untouchable' not in r['ach'], r['ach'])
        ok('the Hard record: best score, stars and clear time; the old arc:dogfight key untouched', r['best'] and r['best']['pts'] == s['score'] and r['best']['stars'] == st and r['best']['clr'] == s['clearT'] and r['old'] == {'pts': 300, 'kills': 3, 'stars': 1, 'mode': 'hard'}, (r['best'], r['old']))
        ok('runLog dogfight with the stats', r['run']['kind'] == 'dogfight' and r['run']['score'] == s['score'] and r['run']['gunKills'] == 4 and r['run']['why'] == 'win' and r['run']['ach'] == r['ach'], r['run'])
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc');}}"); await pg.wait_for_timeout(300)
        ac = await pg.evaluate("()=>{const c=document.querySelector('#arcCards [data-m=dogfight] .sc');return {t:c.innerText,on:c.querySelectorAll('.stars').length?c.querySelector('.stars').getAttribute('aria-label'):''}}")
        ok('the ARCADE card (Hard): the stars and Best score · kills', f"Best {s['score']:,} · 10 kills" in ac['t'] and ac['on'] == f'{st} of 3 stars', ac)
        await pg.evaluate(f"()=>{{{K}.setSkill('rookie');{K}.nav('sArc');}}"); await pg.wait_for_timeout(300)
        ac2 = await pg.evaluate("()=>document.querySelector('#arcCards [data-m=dogfight] .sc').innerText")
        ok('the ARCADE card (Easy): its own record, not flown yet', 'Not flown yet' in ac2, ac2)
        # an Easy run: one kill, out of time; then the card shows Easy's best
        await start(pg, 'rookie')
        await kill_wave(pg, 'fox2'); await to_next_wave(pg)
        await pg.evaluate(f"()=>{{{K}.DF.t=0.5;}}"); await step(pg, 3); await pg.wait_for_timeout(300)
        ce = await pg.evaluate(CARD)
        eb = await pg.evaluate(f"()=>({{e:{K}.SCORE.best['arc:dogfight:easy'],h:{K}.SCORE.best['arc:dogfight:hard'].pts}})")
        ok('Easy run out of time: Out of time on the card, no clear time row, its record under Easy (Hard\'s kept)',
           'Out of time' in ce['title'] and 'Clear time' not in ce['lines'] and eb['e'] and eb['e']['mode'] == 'easy' and eb['e']['kills'] == 1 and eb['e']['clr'] is None and eb['h'] == s['score'], (ce['title'], eb))
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc');}}"); await pg.wait_for_timeout(300)
        ac3 = await pg.evaluate("()=>document.querySelector('#arcCards [data-m=dogfight] .sc').innerText")
        ok('the ARCADE card (Easy) now shows Easy\'s best', f"Best {eb['e']['pts']:,} · 1 kills" in ac3, ac3)
        await pg.evaluate(f"()=>{{{K}.recOpen();}}"); await pg.wait_for_timeout(200)
        rec = await pg.evaluate("()=>document.getElementById('recBody').innerText")
        await pg.evaluate("()=>document.getElementById('recOv').classList.remove('on')")
        ok('the records screen: Red Flag Dogfight, Hard and Easy rows; Ace, Guns Kill, Flare Save, Untouchable listed',
           'Red Flag Dogfight, Hard' in rec and 'Red Flag Dogfight, Easy' in rec and all(n in rec for n in ('Ace', 'Guns Kill', 'Flare Save', 'Untouchable')), rec[-400:])
        # Flare Save: never from Easy's auto flares; from our own tap at 1.5 s
        await pg.evaluate(f"()=>{{const A={K}.SCORE.ach;delete A.flaresave;}}")
        await start(pg, 'rookie')
        await pg.evaluate(f"()=>{{{K}.DF.test.decoy=1;}}"); await pg.evaluate(PLACE, [0, 2500, 3.14159]); await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
        await until(pg, "!D.msl.some(m=>m.on&&m.foe)", 9)
        fa = await pg.evaluate(f"()=>({{ach:{K}.DF.ach.slice(),got:!!{K}.SCORE.ach.flaresave,auto:{K}.DF.calls.filter(c=>c==='autoflare').length,hits:{K}.DF.hits}})")
        ok('Easy auto flares decoy the missile but do not grant Flare Save', fa['auto'] == 1 and fa['hits'] == 0 and 'flaresave' not in fa['ach'] and not fa['got'], fa)
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        await start(pg)
        await pg.evaluate(f"()=>{{{K}.DF.test.decoy=1;}}"); await pg.evaluate(PLACE, [0, 3500, 3.14159]); await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
        await until(pg, "(()=>{const m=D.msl.find(m=>m.on&&m.foe),s=K.state();if(!m)return true;const dx=s.pos.x-m.p.x,dy=s.pos.y-m.p.y,dz=s.pos.z-m.p.z,R=Math.hypot(dx,dy,dz),vc=-(dx*(s.vel.x-m.v.x)+dy*(s.vel.y-m.v.y)+dz*(s.vel.z-m.v.z))/R;return vc>1&&R/vc<=1.5;})()", 8)
        await pg.evaluate(f"()=>{K}.dfPFlare(false)")
        fs = await pg.evaluate(f"()=>({{ach:{K}.DF.ach.slice(),got:!!{K}.SCORE.ach.flaresave,saves:{K}.DF.flareSaves,sub:document.querySelector('#dfSub span').textContent}})")
        ok('Flare Save: our own FLARES tap 1.5 s out decoys the missile, granted at the decoy, in the strip', fs['ach'] == ['flaresave'] and fs['got'] and fs['saves'] == 1 and 'Flare Save' in fs['sub'], fs)
        # Untouchable: a win with no hits
        await start(pg)
        for w in range(4):
            await kill_wave(pg, 'fox2')
            if w < 3: await to_next_wave(pg)
        ut = await pg.evaluate(f"()=>({{ach:{K}.DF.ach.slice(),got:!!{K}.SCORE.ach.untouchable,won:{K}.DF.won,hits:{K}.DF.hits}})")
        ok('Untouchable: granted at a win with no hits', ut['won'] and ut['hits'] == 0 and 'untouchable' in ut['ach'] and ut['got'], ut)
        await step(pg, 4)
        # ---- 8a. the victory roll: a hit, and the bandit that shot rolls once, flying straight, holding fire ----
        await start(pg, quiet=False)
        await pg.evaluate(PLACE, [0, 1500, 3.14159]); await pg.evaluate(f"()=>{K}.DF.test.launchAt()")
        await until(pg, "D.hits>0||!D.msl.some(m=>m.on&&m.foe)", 8)
        vr = await pg.evaluate("""()=>{const K=window.__kgeu,D=K.DF,b=D.bandits[0],h0=b.hdg,s0=D.eShots,r={hits:D.hits,vr0:b.vr,n:b.vrN,bank:[],dh:0,shots:0};
          b.rw=2;b.rwT=99;b.rwD=0;b.cd=0;D.waveT=99;D.inv=0;const b0=b.bank;let mx=0;
          for(let i=0;i<22;i++){K.stepFrame(0.1,false,true);mx=Math.max(mx,b.bank-b0);if(i%5===0)r.bank.push(+(b.bank*57.3).toFixed(0));r.dh=Math.max(r.dh,Math.abs(b.hdg-h0));if(b.vr>0)r.shots=D.eShots-s0;}
          r.roll=+(mx*57.3).toFixed(0);r.vr1=b.vr;r.state=b.state;return r;}""")
        ok('after the hit the shooter does one full victory roll over about 2 s, flying straight, and cannot shoot during it',
           vr['hits'] == 1 and vr['vr0'] > 1.5 and vr['n'] == 1 and 340 <= vr['roll'] <= 361 and vr['dh'] < 0.02 and vr['shots'] == 0 and vr['vr1'] == 0 and vr['state'] == 'TURN', vr)
        # ---- 8b. a gun kill inside 300 m: "Good kill!" every time; Easy "Great shooting!" ----
        gk = []
        for skill in ('pilot', 'rookie'):
            await start(pg, skill)
            await pg.evaluate(f"()=>{K}.DF.test.wave(3)")
            for d in (250, 280, 600):
                await pg.evaluate(PLACE, [0 if d == 250 else 1 if d == 280 else 2, d, 0])
            for i in range(3):
                await pg.evaluate(f"(i)=>{{const D={K}.DF;D.calls.length=0;{K}.dfKill(D.bandits[i],'gun');}}", i)
                gk.append((skill, i, await pg.evaluate(f"()=>({{calls:{K}.DF.calls.slice(),last:{K}.DF.lastCall}})")))
        ok('gun kills at 250 and 280 m: the wingman says Good kill! each time (Easy: Great shooting!), not at 600 m',
           all('gunkill' in x[2]['calls'] for x in gk if x[1] < 2) and all('gunkill' not in x[2]['calls'] for x in gk if x[1] == 2) and
           gk[0][2]['last'] == 'Good kill!' and gk[3][2]['last'] == 'Great shooting!', gk)
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        # ---- 9. the bot, fixed seeds ----
        res = {}
        for skill, seeds in (('rookie', (2, 3)), ('pilot', (1, 3))):
            for seed in seeds:
                await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.setSkill('{skill}');K.windSeed({seed});D.test.seed={seed};D.test.noBrief=true;D.test.noBanditFire=false;D.test.hold=false;D.test.decoy=0;D.test.noDecoy=false;D.bot=null;K.dfStart();}}")
                await pg.wait_for_timeout(200)
                r = None
                for _ in range(30):
                    r = await pg.evaluate(BOT, [30, 0.1])
                    if r['done']: break
                res[(skill, seed)] = r
                print('      bot', 'Easy' if skill == 'rookie' else 'Hard', 'seed', seed, r)
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.DF.test.seed=null;}}")
        ez = [res[('rookie', s)] for s in (2, 3)]; hd = [res[('pilot', s)] for s in (1, 3)]
        ok('the Easy bot wins or reaches wave 3 with 4 or more kills (seeds 2 and 3)', all(x['why'] == 'win' or (x['wave'] >= 3 and x['kills'] >= 4) for x in ez), ez)
        ok('the Hard bot gets 2 or more kills and is not shot down in the first 60 s (seeds 1 and 3)', all(x['kills'] >= 2 and not (x['why'] == 'hits' and x['fightT'] < 60) for x in hd), hd)
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('dogfight_modes_check'))
asyncio.run(main())
