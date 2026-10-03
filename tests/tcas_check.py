# Item 4.1b: TCAS on top of the AI traffic. iPhone landscape, a Cessna at 3,000 ft over the desert
# west of KGEU, the sim stepped by hand (the test drives the vertical speed: level, or following the RA).
# (a) Hard: a scripted head on conflict gives a TA ("Traffic, traffic") then an RA with a sense, the
#     bands on the VS card and the intruder going the other way, then "Clear of conflict" within 60 s;
# (b) Easy: the same with the big CLIMB NOW / DESCEND NOW arrow and the plain English clips;
# (c) no TA or RA on a 2 nm final to KGEU runway 1 at 600 ft, nor on the ground; a crossing conflict;
# (d) the panel hides in the airdrop mission and is back in free flight;
# (e) the panel overlaps no control or card at 844x390 and 667x375, Easy and Hard, one and two button columns;
# (f) the full map draws traffic symbols, below every label; (g) no console errors.
# Usage: .venv/bin/python tests/tcas_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

K = 'window.__kgeu'
# free flight, then the player put at 3,000 ft MSL heading north, 100 kt, 12 km west of KGEU, no other traffic
PLACE = """([type,skill,x,z,ft])=>{const K=window.__kgeu;K.setSkill(skill);K.pick(type);K.pickBase('kgeu');K.start('final');
  K.TFC.auto=false;K.tfcClear();const s=K.state(),V=100/1.94384,y=(ft-1071)/3.28084+(K.TYPES[type].gear||1.5);
  s.pos.set(x,y,z);s.vel.set(0,0,-V);s.quat.setFromEuler(new THREE.Euler(0,0,0,'YXZ'));if(s.w)s.w.set(0,0,0);s.onGround=false;s.ap=null;
  K.tcasVoiceLog.length=0;for(let i=0;i<3;i++){K.stepFrame(0.1,false,true);s.vel.y=0;}return {agl:s.agl,y:s.pos.y};}"""
# n frames of 0.1 s. The test flies the aircraft: 100 kt north, level, or 1,800 fpm the way the RA says (follow).
# Returns a timeline of what TCAS did and what the intruder did.
FLY = """([n,follow,iid])=>{const K=window.__kgeu,s=K.state(),T=K.TCAS,out={ta:null,ra:null,sense:null,band:null,ivs:[],clear:null,arrow:null,maxLv:0,shown:0,frames:0};
  for(let i=0;i<n;i++){const S=T.state();
    s.vel.set(0,follow&&S.ra?(S.sense==='climb'?9.2:-9.2):0,-100/1.94384);   // held at 100 kt north
    K.stepFrame(0.1,false,true);out.frames++;const S2=T.state(),t=+(i*0.1).toFixed(1);
    if(S2.shown)out.shown++;
    for(const l of T.levels())out.maxLv=Math.max(out.maxLv,l.lv);
    if(S2.ta&&out.ta===null)out.ta=t;
    if(S2.ra){if(out.ra===null){out.ra=t;out.sense=S2.sense;}
      const e=document.getElementById('hVs');if(out.band===null&&S2.raT>3)out.band=[e.className,e.parentNode.className];
      const a=document.getElementById('tcasRA');if(out.arrow===null&&S2.raT>1)out.arrow={on:a.classList.contains('on'),vis:getComputedStyle(a).display!=='none',text:a.textContent.trim()};
      const o=K.tfcList().find(q=>q.id===iid);if(o&&S2.raT>6)out.ivs.push(o.vs);}
    if(out.ra!==null&&S2.clear&&!S2.ra&&out.clear===null){out.clear=t;out.levelsAtClear=T.levels();}
    if(out.clear!==null&&t>out.clear+1.5)break;}
  out.levels=T.levels();out.state=T.state();out.log=K.tcasVoiceLog.slice();out.agl=s.agl;
  const e=document.getElementById('hVs');out.bandAfter=e.className;return out;}"""

GROUPS = [
    ('button', 'button'), ('badge', '.badge.on'), ('stick', '#stickZone, #stick.on'), ('slider', '#thr, input[type=range]'),
    ('lookpad', '#lookPad'), ('hudcard', '#hud .card'), ('minimap', '#map'), ('dest', '#hDest:not([hidden])'),
    ('radio', '#atc.on'), ('mission', '#miss.on'), ('lesson', '#lesson.on'), ('sixpack', '#sixpack.on'), ('warn', '#warn.on'),
    ('ticker', '#tk.on .tkP'), ('jump', '#jumpLt.on'), ('sidecfg', '#sideToast.on'), ('toast', '#toast.on'), ('pause', '#bPause'),
]
# the same visibility rules as tests/ui_check.py COLLECT
COLLECT = """(groups)=>{const out=[];
  for(const [kind,sel] of groups){document.querySelectorAll(sel).forEach(el=>{
    if(el.closest('.overlay'))return;const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'||parseFloat(cs.opacity)<0.05)return;
    for(let p=el.parentElement;p;p=p.parentElement){const c=getComputedStyle(p);if(c.display==='none'||parseFloat(c.opacity)<0.05)return;}
    const r=el.getBoundingClientRect();if(r.width<1||r.height<1)return;
    out.push({kind:kind,id:el.id||(el.textContent||'').trim().slice(0,14)||el.tagName,x:r.x,y:r.y,w:r.width,h:r.height});});}
  const t=document.getElementById('tcas'),r=t.getBoundingClientRect(),cs=getComputedStyle(t);
  return {els:out,tcas:cs.display==='none'?null:{x:r.x,y:r.y,w:r.width,h:r.height}};}"""
# everything that can be up beside the panel in free flight: a long tower line, the ticker, the side readout, a badge, a warning
BUSY = """()=>{const K=window.__kgeu;K.tickerForce('A Much Longer Song Title That Will Not Fit In The Pill');K.sideCfg('AUTOLAND COMPLETE','your airplane');
  const a=document.getElementById('atc');a.innerHTML='<span class="tx"><b>Glendale Tower</b>Cessna 3 Kilo Echo, Glendale Tower, wind 050 at 5, runway 1, cleared to land, traffic a Cherokee on the go</span><span class="plain">Tower says: you can land on runway 1, a Cherokee is going around</span>';
  a.classList.add('on','hasPlain');K.gradeBadge({letter:'B',line:'Firm, left of centerline, a long way off the touchdown zone'});
  K.toast('Now playing: Pocket Sim Original');}"""
SAFE = {(667, 375): (0, 0, 0, 0), (844, 390): (0, 47, 47, 21)}
SETSAFE = """([t,l,r,b])=>{const s=document.documentElement.style;s.setProperty('--saT',t+'px');s.setProperty('--saL',l+'px');s.setProperty('--saR',r+'px');s.setProperty('--saB',b+'px');}"""


def overlap(a, b):
    return (min(a['x']+a['w'], b['x']+b['w']) - max(a['x'], b['x']), min(a['y']+a['h'], b['y']+b['h']) - max(a['y'], b['y']))


def has(log, *ids):
    return all(i in log for i in ids)


async def main():
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        c('hooks: TCAS.levels, state, tcasConflict, tcasVoiceLog', await pg.evaluate(
            f"()=>{{const T={K}.TCAS;return typeof T.levels==='function'&&typeof T.state==='function'&&typeof T.tcasConflict==='function'&&Array.isArray({K}.tcasVoiceLog)}}"))

        # --- (a) Hard: head on ---
        r = await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        c('placed at 3,000 ft over the desert, well above 1,000 ft AGL', r['agl'] > 400, round(r['agl']))
        iid = await pg.evaluate(f"()=>{K}.tcasConflict('headon')")
        c('tcasConflict(headon) spawns a scripted airliner', bool(iid))
        lv0 = await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<3;i++)K.stepFrame(0.1,false,true);return K.TCAS.levels()}}")
        c('the intruder is listed, 6 nm out, level within 100 ft', any(l['type'] == 'airliner' and 5.5 < l['range'] < 6.1 and abs(l['relAlt']) < 100 for l in lv0), lv0)
        t = await pg.evaluate(FLY, [700, True, iid])
        c('TA before RA', t['ta'] is not None and t['ra'] is not None and t['ta'] < t['ra'], (t['ta'], t['ra']))
        c('"Traffic, traffic" (c_tcas_traffic) logged', 'c_tcas_traffic' in t['log'], t['log'])
        c('RA with a sense', t['sense'] in ('climb', 'descend'), t['sense'])
        c('RA callout matches the sense', ('c_tcas_climb' if t['sense'] == 'climb' else 'c_tcas_descend') in t['log'], t['log'])
        band = t['band'] or ['', '']
        want = 'raClimb' if t['sense'] == 'climb' else 'raDesc'
        c('#hVs and its card carry the RA band class', 'raBand' in band[0] and want in band[0] and want in band[1], band)
        sgn = 1 if t['sense'] == 'climb' else -1
        c('the intruder maneuvers the other way at about 1,500 fpm', t['ivs'] and all(v * sgn < -3 for v in t['ivs'][-5:]) and abs(t['ivs'][-1]) > 6,
          [round(v, 1) for v in t['ivs'][-3:]])
        c('clear of conflict within 60 s of the RA', t['clear'] is not None and t['clear'] - t['ra'] <= 60, (t['ra'], t['clear']))
        c('"Clear of conflict" (c_tcas_clear) logged', 'c_tcas_clear' in t['log'], t['log'])
        lc = [l for l in (t.get('levelsAtClear') or []) if l['type'] == 'airliner']
        c('the intruder back to proximate or other at the clear', lc and all(l['level'] in ('PROXIMATE', 'OTHER') for l in lc), lc)
        c('bands gone after the clear', 'raBand' not in t['bandAfter'], t['bandAfter'])
        c('the panel showed in free flight', t['shown'] > 0, t['shown'])
        c('no Easy clips in Hard', not any('_e_' in x for x in t['log']), t['log'])

        # --- (f) full map: traffic symbols through the label pass, during a TA ---
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        iid = await pg.evaluate(f"()=>{K}.tcasConflict('headon')")
        await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();for(let i=0;i<400&&!K.TCAS.state().ta;i++){s.vel.set(0,0,-51.4);K.stepFrame(0.1,false,true);}}""")
        f = await pg.evaluate(f"""()=>{{const K={K};K.fmOpen();K.FM.cx=K.state().pos.x;K.FM.cz=K.state().pos.z;K.FM.scale=0.02;K.fmFlush();
          const L=K.LBL().placed,tf=L.filter(p=>p.kind==='tfc'),lab=L.filter(p=>p.kind!=='tfc');let bad=0;
          for(const a of tf)for(const q of lab){{const A=a.box,B=q.box;if(A[0]<B[2]&&A[2]>B[0]&&A[1]<B[3]&&A[3]>B[1])bad++;}}
          const r={{drawn:K.FM.tfcDrawn,placed:tf.length,bad:bad,ta:K.TCAS.state().ta}};K.fmClose();K.stepFrame(0,true);return r;}}""")
        c('full map: traffic symbols drawn (FM.tfcDrawn)', f['drawn'] >= 1 and f['placed'] >= 1, f)
        c('full map: no symbol overlaps a label', f['bad'] == 0, f)

        # --- (c) inhibit: 2 nm final to KGEU runway 1 at 600 ft AGL; on the ground; a crossing conflict TAs ---
        await pg.evaluate("""()=>{const K=window.__kgeu;K.setSkill('pilot');K.pick('cessna');K.pickBase('kgeu');K.start('final');K.TFC.auto=false;K.tfcClear();
          const e=K.RWY_ENDS.find(q=>q.rwy.code==='KGEU'&&q.num==='1'),s=K.state(),dx=Math.sin(e.h),dz=-Math.cos(e.h),x=e.x-dx*3704,z=e.z-dz*3704;
          s.pos.set(x,K.groundHeight(x,z)+183+(K.TYPES.cessna.gear||1.5),z);s.vel.set(dx*40,0,dz*40);s.quat.setFromEuler(new THREE.Euler(0,-e.h,0,'YXZ'));s.onGround=false;s.ap=null;
          K.tcasVoiceLog.length=0;K.stepFrame(0.1,false,true);}""")
        await pg.evaluate(f"()=>{K}.tcasConflict('headon')")
        t = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),T=K.TCAS;let ta=0,ra=0,inh={},minD=1e9;
          for(let i=0;i<500;i++){s.vel.y=0;K.stepFrame(0.1,false,true);const S=T.state();if(S.ta)ta++;if(S.ra)ra++;inh[S.inhibit]=1;
            for(const l of T.levels())minD=Math.min(minD,l.cpaD);if(s.agl<60)break;}
          return {ta:ta,ra:ra,inh:Object.keys(inh),log:K.tcasVoiceLog.slice(),agl:s.agl,minD:minD}}""")
        c('final at 600 ft: no TA, no RA, no callout', t['ta'] == 0 and t['ra'] == 0 and not t['log'], t)
        c('final at 600 ft: inhibited as an approach, and the conflict was real', 'approach' in t['inh'] and t['minD'] < 0.3, (t['inh'], t['minD']))
        await pg.evaluate(f"()=>{{const K={K};K.start('runway');K.TFC.auto=false;K.tfcClear();K.tcasVoiceLog.length=0;K.stepFrame(0.1,false,true);}}")
        await pg.evaluate(f"()=>{K}.tcasConflict('headon')")
        t = await pg.evaluate("""()=>{const K=window.__kgeu,T=K.TCAS;let ta=0,ra=0,inh={},shown=0;
          for(let i=0;i<500;i++){K.stepFrame(0.1,false,true);const S=T.state();if(S.ta)ta++;if(S.ra)ra++;if(S.shown)shown++;inh[S.inhibit]=1;}
          return {ta:ta,ra:ra,inh:Object.keys(inh),log:K.tcasVoiceLog.slice(),ground:K.state().onGround,shown:shown}}""")
        c('on the ground: no TA, no RA, no callout, no panel', t['ground'] and t['ta'] == 0 and t['ra'] == 0 and not t['log'] and t['shown'] == 0 and 'ground' in t['inh'] and set(t['inh']) <= {'ground', 'approach'}, t)
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        iid = await pg.evaluate(f"()=>{K}.tcasConflict('cross')")
        t = await pg.evaluate(FLY, [700, True, iid])
        c('crossing from the right: TA, RA and clear', t['ta'] is not None and t['ra'] is not None and t['clear'] is not None, (t['ta'], t['ra'], t['clear'], t['log']))

        # --- (b) Easy ---
        await pg.evaluate(PLACE, ['cessna', 'rookie', -12000, 0, 3000])
        iid = await pg.evaluate(f"()=>{K}.tcasConflict('headon')")
        t = await pg.evaluate(FLY, [700, True, iid])
        a = t['arrow'] or {}
        word = 'CLIMB NOW' if t['sense'] == 'climb' else 'DESCEND NOW'
        c('Easy: the big arrow shows CLIMB NOW / DESCEND NOW', a.get('on') and a.get('vis') and a.get('text') == word, a)
        c('Easy: plain English clips (traffic, RA, clear)', has(t['log'], 'c_tcas_e_traffic', 'c_tcas_e_' + str(t['sense']), 'c_tcas_e_clear'), t['log'])
        c('Easy: no Hard callouts', not any(x in t['log'] for x in ('c_tcas_traffic', 'c_tcas_climb', 'c_tcas_descend', 'c_tcas_clear')), t['log'])
        c('Easy: the arrow goes with the clear', not await pg.evaluate("()=>document.getElementById('tcasRA').classList.contains('on')"))

        # --- (d) hidden in a mission, back in free flight ---
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        s1 = await pg.evaluate(f"()=>{K}.TCAS.state().shown&&document.getElementById('tcas').classList.contains('on')")
        c('free flight: panel up', s1)
        s2 = await pg.evaluate(f"""()=>{{const K={K};K.pick('c130');K.start('drop');for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);
          return {{miss:K.MISS.on,shown:K.TCAS.state().shown,on:document.getElementById('tcas').classList.contains('on'),inh:K.TCAS.state().inhibit,lv:K.TCAS.levels().length}}}}""")
        c('airdrop mission: panel hidden, TCAS off', s2['miss'] and not s2['shown'] and not s2['on'] and s2['inh'] == 'off' and s2['lv'] == 0, s2)
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        s3 = await pg.evaluate(f"()=>{K}.TCAS.state().shown&&document.getElementById('tcas').classList.contains('on')")
        c('back in free flight: panel up', s3)
        # Settings toggle
        s4 = await pg.evaluate(f"""()=>{{const K={K};K.TCAS.setTcas(false);K.stepFrame(0.1,false,true);const off=!document.getElementById('tcas').classList.contains('on')&&localStorage.getItem('kgeuTcas')==='0'&&document.getElementById('oTcas').textContent==='TCAS: Off';
          K.TCAS.setTcas(true);K.stepFrame(0.1,false,true);return off&&document.getElementById('tcas').classList.contains('on')&&document.getElementById('oTcas').textContent==='TCAS: On'}}""")
        c('Settings TCAS toggle hides the panel and is stored', s4)
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        errs = list(pg.errs)
        await pg.context.close()

        # --- (e) layout: the panel against every control and card ---
        for w, h in [(844, 390), (667, 375)]:
            pg2 = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg2.evaluate(SETSAFE, list(SAFE[(w, h)]))
            for skill in ('rookie', 'pilot'):
                for typ in ('cessna', 'c130'):
                    await pg2.evaluate(PLACE, [typ, skill, -12000, 0, 3000])
                    await pg2.evaluate("()=>{const K=window.__kgeu;K.stepFrame(0,true);}")
                    await pg2.wait_for_timeout(250)
                    await pg2.evaluate(BUSY)
                    await pg2.wait_for_timeout(500)
                    r = await pg2.evaluate(COLLECT, GROUPS)
                    T = r['tcas']
                    bad = []
                    if T:
                        for e in r['els']:
                            ox, oy = overlap(T, e)
                            if ox > 0.5 and oy > 0.5:
                                bad.append(f"{e['kind']}:{e['id']} ({ox:.0f}x{oy:.0f})")
                        if T['x'] < 0 or T['y'] < 0 or T['x'] + T['w'] > w or T['y'] + T['h'] > h:
                            bad.append('off screen')
                    c(f'{w}x{h} {skill} {typ}: panel up and clear of every control and card', T is not None and not bad, bad or T)
                    if typ == 'c130' and skill == 'pilot':
                        await pg2.screenshot(path=f'overnight-screenshots/tcas_{w}x{h}.png')
                    await pg2.evaluate("()=>{const K=window.__kgeu;K.tickerForce(null);K.badgeHide();document.getElementById('atc').classList.remove('on');}")
            errs += pg2.errs
            await pg2.context.close()
        c('no console errors', not errs, errs[:5])
        await b.close()
    srv.shutdown()
    return c.done('tcas_check')


sys.exit(asyncio.run(main()))
