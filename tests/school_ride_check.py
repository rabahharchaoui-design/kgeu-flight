# School2 item 6: Stage 4 lesson 2, the mock checkride. Frank Delgado, the DPE, draws five tasks from the flown lessons in ACS
# order plus the landings last; each is flown with its own lesson code and tasks, Easy off, no briefing, no debrief of its own.
# (a) rideSeed(42) draws steep, slow, stall, emerg, hood, landings (the easiest draw to drive: no ground reference, no
# diversion); started with the briefing skipped and kgeuSchoolEasy '1': RUNSTART is the ride, the card reads Checkride: Steep
# turns, Frank's opening is in the radio log as Frank, Easy is off for every task (G.easy false) and the toggle is untouched;
# (b) each task flown to a pass the way its own check does (the steep turn pinned round, slow flight held, the stall sequence of
# school_grade_check, the emergency descent and field of school_emerg_check, the hood of school_hood_check, the three circuits
# of school_landings_check with Frank's Go around); the pause between tasks reads Next: <task>; no Dana line in the ride;
# (c) the certificate: TEMPORARY AIRMAN CERTIFICATE, the callsign, today's date, Examiner: Frank Delgado, DPE, Checkride n of
# 100, six task rows, the board line, kgeuCert, the logbook entry (1.5 h dual, a landing), the XP burst (500 + taskXp: the big
# pop, on at once and 1.5 s later, over the sheet, topmost at its centre with the pointer events on for the probe), the
# fit at 844x390 with 44 px buttons; (d) the Boards screen lists Checkride under Flight school with the device row; the school
# header says Private pilot, certificated and Stage 4 shows done; (e) rideSeed(1) (slow flight first) stalled: the ride
# stops, the F card titled Notice of disapproval, slow flight red, the rest not flown, a Retrain row with a 44 px RETRAIN that
# opens Slow flight with its briefing; (f) no page errors. Prints every Frank line of the passed run.
# Run: .venv/bin/python tests/school_ride_check.py
import asyncio, sys, math, json, datetime
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15, finger
from school_fly import K, BASE, DEBRIEF, rwy, call, climbout, downwind, base, final, touchdown, stop
import school_fly
ok = Checks()
# school_fly's FLY, held to the task it starts in (the ride goes on to the next task under it)
FLY = school_fly.FLY.replace("let i=0;\n  for(;i<n&&K.LES.on;i++)", "let i=0;const tk=K.LES.on;\n  for(;i<n&&K.LES.on===tk;i++)")
assert FLY != school_fly.FLY
WAIT = "(id)=>{const K=window.__kgeu;let i=0;for(;i<900&&K.LES.on&&K.LES.on!==id;i++){const s=K.state();s.windKt=0;s.gustAmp=0;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return [K.LES.on,i,document.getElementById('lesT').textContent]}"
GAP = "()=>{const K=window.__kgeu;for(let i=0;i<40&&K.LES.on!=='ride';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);return [K.LES.on,document.getElementById('lesI').textContent,document.getElementById('lesT').textContent]}"
STALL = """(o)=>{const K=window.__kgeu,u=o.u?new Function('K','return '+o.u):null;let i=0;const tk=K.LES.on;
  for(;i<(o.n||400)&&K.LES.on===tk;i++){const s=K.state();s.windKt=0;s.gustAmp=0;s.throttle=s.power=o.thr;
    const V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225);s.vel.set(0,o.vy||0,-V);s.quat.setFromEuler(new THREE.Euler(o.p,0,0,'YXZ'));s.w.set(0,0,0);
    K.stepFrame(0.1,false,true);if(u&&u(K))break;}K.stepFrame(0,true);return {ph:K.LES.ph,on:K.LES.on,i:i}}"""
GROUND = """([x,z,n])=>{const K=window.__kgeu,tk=K.LES.on;for(let i=0;i<n&&K.LES.on===tk;i++){const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;K.stepFrame(0.1,false,true);}K.stepFrame(0,true);return K.LES.on}"""
FIELD = """()=>{const K=window.__kgeu,O=K.lesObjs(),M=O.filter(o=>o.name==='fieldMk'),s=K.state();if(!M.length)return null;
  const cx=M.reduce((p,o)=>p+o.x,0)/M.length,cz=M.reduce((p,o)=>p+o.z,0)/M.length;
  return {cx:cx,cz:cz,brg:(Math.atan2(cx-s.pos.x,-(cz-s.pos.z))*180/Math.PI+360)%360,M:M.map(o=>[o.x,o.z])}}"""
POP = """()=>{const b=document.getElementById('xpPops'),e=b&&b.querySelector('.xpPop.big');if(!e)return {n:b?b.children.length:-1};
  const r=e.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,g=document.getElementById('gradeOv'),sh=g.querySelector('.sheet').getBoundingClientRect();
  const pe=[b.style.pointerEvents,e.style.pointerEvents];b.style.pointerEvents=e.style.pointerEvents='auto';const h=document.elementFromPoint(cx,cy);b.style.pointerEvents=pe[0];e.style.pointerEvents=pe[1];
  return {on:e.classList.contains('on'),txt:e.textContent,aria:e.getAttribute('aria-label'),op:getComputedStyle(e.firstChild).opacity,fs:parseFloat(getComputedStyle(e.querySelector('.xpN')).fontSize),
    top:!!h&&e.contains(h),overSheet:cx>sh.left&&cx<sh.right&&cy>sh.top&&cy<sh.bottom,z:+getComputedStyle(b).zIndex,gz:getComputedStyle(g).zIndex,card:g.classList.contains('on')}}"""
FRANK = "()=>window.__kgeu.radioLog().filter(l=>l.who==='Frank').map(l=>l.text)"
WHO = "()=>[...new Set(window.__kgeu.radioLog().map(l=>l.who))]"
CARD = """()=>{const g=document.getElementById('gradeOv'),q=s=>{const e=g.querySelector(s);return e?e.textContent:null};
  return {on:g.classList.contains('on'),cert:g.classList.contains('cert'),letter:q('#gLetter'),letterShown:getComputedStyle(document.getElementById('gLetter')).display!=='none',
    title:document.getElementById('gTitle').firstChild.textContent,kick:q('.cert .cK'),name:q('.cert .cN'),date:q('.cert .cD'),score:q('.cert .cS'),
    rows:[...g.querySelectorAll('#gLines .gt')].map(r=>[r.querySelector('span').textContent,r.className.replace('gl gt rr','').trim(),r.querySelector('b').textContent]),
    board:q('#gLines .lbLine'),rt:[...g.querySelectorAll('.rtGo')].map(b=>{const r=b.getBoundingClientRect();return [b.dataset.l,b.textContent,Math.round(r.width),Math.round(r.height)]}),
    tip:q('.rTip'),retry:q('#gRetry')}}"""
FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight,bad=[];
  s.querySelectorAll('button').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off '+e.textContent.trim().slice(0,14));
    if(r.width<43.5||r.height<43.5)bad.push('small '+e.textContent.trim().slice(0,14));});
  const c=s.querySelector('.cert');if(c){const r=c.getBoundingClientRect();if(r.bottom>H||r.top<0)bad.push('cert off screen');}
  const b=s.querySelector('.rLines');if(c&&b.scrollHeight>b.clientHeight+1)bad.push('lines scroll');return bad;}"""

async def fly(pg, n, **o):
    return await pg.evaluate(FLY, [n, o])

def vs(kt, deg):
    return kt * 101.27 * math.tan(math.radians(deg) - 0.04)

async def wait(pg, tid):
    return await pg.evaluate(WAIT, tid)

async def gap(pg):
    return await pg.evaluate(GAP)

async def t_steep(pg):
    kt = await pg.evaluate(f"()=>Math.round({K}.state().ias*1.943844)")
    await fly(pg, 10, kt=kt, vs=0, hdg=0, bank=45, until="K.LES.ph===1")
    r = await fly(pg, 600, kt=kt, vs=0, hdg=0, bank=45, rate=10, until="K.LES.d.turned>=340")
    await fly(pg, 20, kt=kt, vs=0, hdg=360, bank=0)

async def t_slow(pg):
    await fly(pg, 400, kt=58, vs=0, hdg=0, thr=0.5, until="K.LES.ph===1")
    await fly(pg, 600, kt=58, vs=0, hdg=0, thr=0.5)

async def t_stall(pg):
    for o in ({'kt': 48, 'p': 0.5, 'thr': 0, 'u': 'K.LES.ph===1'}, {'kt': 60, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===2'}, {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1, 'u': 'K.LES.ph===3'},
              {'kt': 58, 'p': 0.1, 'vy': 0, 'thr': 0.4, 'n': 20}, {'kt': 52, 'p': 0.55, 'thr': 1, 'u': 'K.LES.ph===4'}, {'kt': 62, 'p': -0.05, 'vy': 1.2, 'thr': 1, 'u': 'K.LES.ph===5'},
              {'kt': 74, 'p': 0.1, 'vy': 2, 'thr': 1}):
        await pg.evaluate(STALL, o)

async def t_emerg(pg):
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<60&&!K.LES.d.go;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}}")
    await fly(pg, 700, thr=0, bank=45, kt=130, vs=-2500, hdg=0, rate=8, until="K.LES.ph===1")
    await fly(pg, 80, alt=3500, thr=0.8, kt=100, vs=0, hdg=90, until="K.LES.ph===2")
    await fly(pg, 140, kt=100, vs=0, hdg=90, until="K.LES.ph===3")
    f = await pg.evaluate(FIELD)
    await fly(pg, 120, kt=68, vs=-650, hdg=f['brg'])
    ax, az = (f['M'][1][0] - f['M'][0][0]), (f['M'][1][1] - f['M'][0][1]); L = math.hypot(ax, az); ax, az = ax / L, az / L
    h = (math.degrees(math.atan2(ax, -az)) + 360) % 360
    await fly(pg, 10, x=f['cx'] - ax * 600, z=f['cz'] - az * 600, agl=250, kt=62, vs=-500, hdg=h)
    await pg.evaluate(f"([x,z])=>{{const K={K};K.events.push({{type:'touchdown',fpm:220,paved:K.isPaved(x,z),x:x,z:z,ias:30,bank:0}})}}", [f['cx'], f['cz']])
    await fly(pg, 2, agl=20, kt=50, vs=-100, hdg=h)
    await pg.evaluate(GROUND, [f['cx'], f['cz'], 30])

async def t_hood(pg):
    await fly(pg, 700, alt=3500, kt=90, vs=0, hdg=0, until="K.LES.ph===1")
    await fly(pg, 200, kt=90, vs=0, hdg=0, rate=4.5, bank=15)
    await fly(pg, 400, kt=90, vs=0, hdg=90, until="K.LES.ph===2")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on==='hood';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", 40)
    await fly(pg, 6, thr=0, bank=50, kt=118, vs=vs(118, -25), hdg=90)
    await fly(pg, 6, bank=0, kt=125, vs=vs(125, -25), hdg=90)
    await fly(pg, 30, bank=0, kt=125, vs=300, hdg=90, until="K.LES.ph===3")
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on==='hood';i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}", 40)
    await fly(pg, 6, thr=1, bank=-40, kt=68, vs=vs(68, 30), hdg=90)
    await fly(pg, 10, bank=-40, kt=70, vs=0, hdg=90)
    await fly(pg, 60, bank=0, kt=75, vs=0, hdg=90)

async def t_landings(pg):
    F = await rwy(pg)
    assert await call(pg), 'no CALL at the hold'
    await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);if(K.radioLog().some(l=>/^Cleared for takeoff/.test(l.text)))break;}K.stepFrame(0,true)}")
    for c in range(3):
        await climbout(pg, F); await downwind(pg, F)
        assert await call(pg), ('no readback', c)
        await downwind(pg, F, 80); await base(pg, F)
        if c == 1:
            await final(pg, F, to=320)
            await school_fly.fly(pg, 3, agl=295, kt=65, vs=-400, hdg=F['rh'])
            await school_fly.fly(pg, 120, thr=1, kt=70, vs=900, hdg=F['rh'], until="K.LES.d.c===2")
            continue
        await final(pg, F)
        await touchdown(pg, F, past=60)
        if c == 0:
            await school_fly.fly(pg, 30, agl=30, kt=60, vs=0, hdg=F['rh'])
            await school_fly.fly(pg, 10, agl=150, kt=70, vs=500, hdg=F['rh'], until="K.LES.d.c===1")
        else:
            await stop(pg, F)

DRIVE = {'steep': t_steep, 'slow': t_slow, 'stall': t_stall, 'emerg': t_emerg, 'hood': t_hood, 'landings': t_landings}

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuSchoolEasy='1', **PLACED))
        # (a) the draw, the start, Frank's opening
        seq = await pg.evaluate(f"()=>{{{K}.rideSeed(42);const s={K}.rideDraw();{K}.rideSeed(42);return s}}")
        ok('(a) rideSeed(42): steep, slow, stall, emerg, hood, landings', seq == ['steep', 'slow', 'stall', 'emerg', 'hood', 'landings'], seq)
        await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('ride');K.lesBriefSkip();const s=K.state();s.windKt=0;s.gustAmp=0;}}")
        await pg.wait_for_timeout(200)
        a = await pg.evaluate(f"()=>{{const K={K};return {{rs:K.RUNSTART(),t:document.getElementById('lesT').textContent,i:document.getElementById('lesI').textContent,seq:K.RIDE.seq,on:K.RIDE.on}}}}")
        ok('(a) RUNSTART is the ride, the card reads Checkride: Steep turns, Next: Steep turns', a['rs'].get('k') == 'les' and a['rs'].get('id') == 'ride' and a['t'] == 'Checkride: Steep turns'
           and a['i'] == 'Next: Steep turns' and a['seq'] == seq and a['on'], a)
        w = await wait(pg, 'steep')
        fr = await pg.evaluate(FRANK)
        ok("(a) Frank's opening in the radio log as Frank, before the first task", fr and fr[0].startswith('Skyhawk 8401L, this is your examiner, Frank Delgado.') and w[0] == 'steep', (fr, w))
        e = await pg.evaluate(f"()=>{{const K={K};return {{easy:K.G.easy,def:K.G.def.id,quiet:!!K.G.def.quiet,ls:localStorage.getItem('kgeuSchoolEasy'),rs:K.RUNSTART().id,t:document.getElementById('lesT').textContent,mode:K.runMode()}}}}")
        ok('(a) steep turns flying: G.easy false with the toggle on Easy (left as it is), quiet, RUNSTART still the ride, the title', e['easy'] is False and e['def'] == 'steep' and e['quiet'] and e['ls'] == '1' and e['rs'] == 'ride'
           and e['t'] == 'Checkride: Steep turns' and e['mode'] == 'hard', e)
        FITT = """()=>{const K=window.__kgeu,t=document.getElementById('lesT'),o=t.innerHTML,r=['steep','slow','stall','ground','short','soft','emerg','hood','divert','landings'].map(id=>K.rideName(id)).filter(n=>{t.innerHTML='<span class="rPre">Checkride: </span>'+n;return t.scrollWidth>t.clientWidth+0.5;});t.innerHTML=o;return r}"""
        fit = await pg.evaluate(FITT)
        await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(300)
        fit2 = await pg.evaluate(FITT)
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        ok('(a) every Checkride: <task> title fits the card at 844x390, the task alone at 568x320 (Ground reference is cut there as its own lesson is)', not fit and fit2 in ([], ['Ground reference']), (fit, fit2))
        # (b) every task driven
        gaps, easy = [], []
        for k, tid in enumerate(seq):
            if k:
                w = await wait(pg, tid)
                assert w[0] == tid, ('never started', tid, w)
            easy.append(await pg.evaluate(f"()=>{K}.G.easy"))
            await DRIVE[tid](pg)
            if k < 5: gaps.append(await gap(pg))
        pop = await pg.evaluate(POP)   # right after the certificate opens: the big burst over the card
        await pg.wait_for_timeout(1000)
        await pg.screenshot(path='/tmp/ride_pop.png')
        pop2 = await pg.evaluate(POP)   # 1.5 s on: counted up, fully shown, still there
        res = await pg.evaluate(f"()=>{K}.RIDE.res.map(r=>[r.id,r.score,r.ok,r.failWhy,r.lines.filter(l=>!l.ok).map(l=>l.name+': '+l.detail)])")
        ok('(b) every task passed (C or better, no fail)', len(res) == 6 and all(r[2] for r in res), res)
        ok('(b) Easy off on every task', easy == [False] * 6, easy)
        ok('(b) the pause between tasks reads Next: <task>', [g[1] for g in gaps] == ['Next: Slow flight', 'Next: Stalls', 'Next: Emergencies', 'Next: Under the hood', 'Next: Landings'], gaps)
        fr = await pg.evaluate(FRANK); who = await pg.evaluate(WHO)
        ok('(b) no Dana in the ride; Frank names every task and says Go around', 'Dana' not in who and any(t.startswith('Steep turns.') for t in fr) and any(t.startswith('Slow flight.') for t in fr)
           and any(t.startswith('Stalls.') for t in fr) and 'Go around.' in fr and any(t.startswith('Last task.') for t in fr), (who, fr))
        # (c) the certificate
        c = await pg.evaluate(CARD)
        cs = await pg.evaluate(f"()=>({K}.LB&&{K}.LB.E&&{K}.LB.E.P&&{K}.LB.E.P.cs)||'Skyhawk 8401L'")
        today = await pg.evaluate("()=>new Date().toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'})")
        ok('(c) the certificate card: no letter, the kicker, PRIVATE PILOT, the callsign, today, the examiner', c['on'] and c['cert'] and not c['letterShown'] and c['kick'] == 'TEMPORARY AIRMAN CERTIFICATE'
           and c['name'] == cs and c['date'].startswith(today) and 'Examiner: Frank Delgado, DPE' in c['date'], c)
        sc = round(sum(r[1] for r in res) / 6)
        ok('(c) Checkride <mean> of 100 and six task rows, all green', c['score'] == f'Checkride {sc} of 100' and len(c['rows']) == 6 and all(r[1] == 'ok' for r in c['rows'])
           and [r[0] for r in c['rows']] == ['Steep turns', 'Slow flight', 'Stalls', 'Emergencies', 'Under the hood', 'Landings'], c)
        x = await pg.evaluate(f"()=>{{const K={K},L=K.XPP.log;return {{x:L.length?L[L.length-1]:null,tx:K.taskXp({sc},'hard',true)}}}}")
        ok('(c) the board line: #1 of 1, +XP, FIRST RUN', c['board'] and c['board'].startswith('Board, this device#1 of 1') and f"+{500 + x['tx']} XP" in c['board'] and 'FIRST RUN' in c['board'], c['board'])
        amt = 500 + x['tx']
        ok('(c) at once: the big burst on (the on class) over the open certificate, its label the amount and the reason, topmost at its centre, z-index over #gradeOv, 1.6x type',
           pop.get('on') and pop.get('card') and pop.get('aria') == f'+{amt} XP, Private pilot certificate' and pop['top'] and pop['overSheet']
           and pop['z'] > (int(pop['gz']) if pop['gz'].lstrip('-').isdigit() else 0) and pop['fs'] >= 60, pop)
        ok('(c) 1.5 s on: still on and topmost, fully shown, reading +amount XP and the reason', pop2.get('on') and pop2['op'] == '1' and pop2['txt'] == f'+{amt:,}XPPrivate pilot certificate' and pop2['top'], pop2)
        ok('(c) the XP burst: 500 + taskXp, Private pilot certificate', x['x'] and x['x']['amount'] == 500 + x['tx'] and x['x']['reason'] == 'Private pilot certificate', x)
        st = await pg.evaluate("()=>({cert:JSON.parse(localStorage.getItem('kgeuCert')||'null'),log:JSON.parse(localStorage.getItem('kgeuLogbook')||'{}').entries.slice(-1)[0],best:JSON.parse(localStorage.getItem('kgeuSchool')||'{}')['cessna:ride']})")
        ok('(c) kgeuCert {at, cs, score, examiner}', st['cert'] and st['cert']['cs'] == cs and st['cert']['score'] == sc and st['cert']['examiner'] == 'Frank Delgado, DPE' and st['cert']['at'] > 0, st['cert'])
        ok('(c) the logbook: the ride, 1.5 h dual, one landing; the best letter', st['log']['id'] == 'ride' and st['log']['dual'] == 1.5 and st['log']['ldg'] == 1 and st['log']['letter'] != 'F' and st['best'] == st['log']['letter'], st)
        ok('(c) RETRY CHECKRIDE', c['retry'] == 'RETRY CHECKRIDE', c['retry'])
        bad = await pg.evaluate(FIT, '#gradeOv')
        ok('(c) 844x390: the certificate, six rows and the board line without scrolling, 44 px buttons', not bad, bad)
        await pg.screenshot(path='/tmp/ride_cert.png')
        await pg.set_viewport_size({'width': 568, 'height': 320}); await pg.wait_for_timeout(400)
        bad = await pg.evaluate(FIT.replace("if(r.bottom>H||r.top<0)bad.push('cert off screen');", '').replace("if(c&&b.scrollHeight>b.clientHeight+1)bad.push('lines scroll');", ''), '#gradeOv')
        ok('(c) 568x320: the card fits, 44 px buttons (the lines may scroll)', not bad, bad)
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        fr = await pg.evaluate(FRANK)
        print('\n  Frank, the passed ride, in order:')
        for t in fr: print('   - ' + t)
        print()
        # (d) the Boards screen and the school header
        await pg.evaluate(f"()=>{{{K}.openMenu('sLb');{K}.LB.lbOpen('lesson:ride')}}"); await pg.wait_for_timeout(500)
        lb = await pg.evaluate("""()=>{const g=[...document.querySelectorAll('#lbList h3')].map(h=>[h.textContent,[...h.nextElementSibling.querySelectorAll('[data-lbb]')].map(b=>[b.dataset.lbb,b.textContent])]);
          return {g:g,title:document.getElementById('lbTitle').textContent,rows:document.querySelectorAll('#lbRowsIn .lbRow').length,how:document.getElementById('lbHow').textContent}}""")
        fs = dict(lb['g']).get('Flight school', [])
        ok('(d) the Boards picker lists Checkride under Flight school', ['lesson:ride', 'Checkride'] in fs, lb['g'])
        ok('(d) the Checkride board shows the device row', lb['title'] == 'Checkride' and lb['rows'] >= 1 and 'passes only' in lb['how'], lb)
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
        await pg.evaluate("()=>{const b=document.querySelector('#schMap [data-st=s4]');if(b)b.click()}"); await pg.wait_for_timeout(300)
        h = await pg.evaluate("""()=>({c:document.getElementById('schCert').textContent,vis:!document.getElementById('schCert').hidden&&getComputedStyle(document.getElementById('schCert')).display!=='none',
          node:document.querySelector('#schMap [data-st=s4]').className,ring:document.querySelector('#schMap [data-st=s4] .ring').textContent,
          row:[...document.querySelectorAll('#school .lrow')].map(r=>[r.dataset.l,r.className.replace('lrow','').trim()])})""")
        ok('(d) the school header: Private pilot, certificated <date>; Stage 4 shows done with a tick', h['c'].startswith('Private pilot, certificated ') and h['vis'] and 'done' in h['node'] and h['ring'].strip().endswith('✓'), h)
        ok('(d) the Mock checkride row is a real row, passed', ['ride', 'done'] in [[r[0], r[1].split(' ')[0]] for r in h['row']], h['row'])
        ok('(f) no page errors (passed ride)', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (e) a fail: slow flight first, stalled: the ride stops, the notice of disapproval, RETRAIN
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, **PLACED))
        seq = await pg.evaluate(f"()=>{{{K}.rideSeed(1);const s={K}.rideDraw();{K}.rideSeed(1);return s}}")
        await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('ride');K.lesBriefSkip();}}")
        w = await wait(pg, seq[0])
        r = await pg.evaluate(STALL, {'kt': 40, 'p': 0.6, 'thr': 0, 'n': 200})
        await pg.wait_for_timeout(700)
        c = await pg.evaluate(CARD)
        ok('(e) rideSeed(1) starts with slow flight', seq[0] == 'slow' and w[0] == 'slow', (seq, w))
        ok('(e) the stall stops the ride: the F card, Notice of disapproval, no certificate', c['on'] and not c['cert'] and c['letter'] == 'F' and c['letterShown'] and c['title'] == 'Checkride: Notice of disapproval', c)
        ok('(e) slow flight red with the stall, the other five not flown', c['rows'][0][0] == 'Slow flight' and c['rows'][0][1] == 'no' and 'stalled' in c['rows'][0][2]
           and [x[2] for x in c['rows'][1:]] == ['not flown'] * 5 and len(c['rows']) == 6, c['rows'])
        ok("(e) Frank's notice as the tip, the Retrain row with a 44 px RETRAIN for slow flight", c['tip'].startswith('Notice of disapproval. Retrain the tasks below') and c['rt'] == [['slow', 'RETRAIN', c['rt'][0][2], c['rt'][0][3]]]
           and c['rt'][0][2] >= 44 and c['rt'][0][3] >= 44 and not c['board'], c)
        st = await pg.evaluate("()=>({cert:localStorage.getItem('kgeuCert'),log:JSON.parse(localStorage.getItem('kgeuLogbook')||'{}').entries.slice(-1)[0],xp:window.__kgeu.XPP.log.length,lb:(JSON.parse(localStorage.getItem('kgeuTaskLB')||'{}')['lesson:ride']||[]).length})")
        ok('(e) no certificate, no XP, no board entry; a logbook entry with the F and no time', not st['cert'] and st['xp'] == 0 and st['lb'] == 0 and st['log']['id'] == 'ride' and st['log']['letter'] == 'F' and st['log']['dual'] == 0, st)
        bad = await pg.evaluate(FIT, '#gradeOv')
        ok('(e) 844x390: the F card fits, 44 px buttons', not bad, bad)
        await pg.screenshot(path='/tmp/ride_fail.png')
        await finger(pg, '#gradeOv .rtGo'); await pg.wait_for_timeout(500)
        t = await pg.evaluate(f"()=>({{on:{K}.LES.on,brief:document.getElementById('brOv').classList.contains('on'),title:document.getElementById('brT').textContent,ride:{K}.RIDE.on,card:document.getElementById('gradeOv').classList.contains('on')}})")
        ok('(e) RETRAIN opens Slow flight with its briefing, the ride over', t == {'on': 'slow', 'brief': True, 'title': 'Slow flight', 'ride': False, 'card': False}, t)
        ok('(f) no page errors (failed ride)', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('school_ride_check'))
asyncio.run(main())
