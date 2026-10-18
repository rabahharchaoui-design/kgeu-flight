# Schoolhud item 1: Dana and Frank are recordings, never the speech engine.
# (a) radio/cfi/voice.json loads and every clip in it fetches and decodes (headless Chromium's AAC decoder);
# (b) coverage: the lines built at run time from numbers and names all find their clips (cfiClips, no miss): Dana's live
#     corrections (cfiCue) for every kind over a range of deviations, rounded to sensible values (nearest 10 ft under 100,
#     else 50; knots and degrees to the unit under 10, else 5); the debrief line (dbSay) for every lesson's tasks and every
#     letter; the pilotage checkpoint and course lines for every fix, heading and minutes; the emergency field line for every
#     clock position and distance; Frank's opening for every task draw, every task's line (rideTaskLine), his grades;
# (c) the pattern lesson flown with audio on and a spy on speechSynthesis: its sets decode at the start (cfiPrep), Dana's
#     lines play as clips (CFIV.plays), no speechSynthesis property is read, no line missed its clips, and the voice queue
#     still lets a safety call (Stall) cut her at once; (d) muted: no clip plays, the caption still shows; (e) no page errors.
# Run: .venv/bin/python tests/cfi_voice_check.py
import asyncio, json, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED, IPHONE_15, ROOT
ok = Checks()
K = 'window.__kgeu'
# every read of window.speechSynthesis counts (the game must never touch it)
SPY = """(()=>{window.__ssReads=0;const S={speak(){window.__ssReads++;},cancel(){window.__ssReads++;},getVoices(){window.__ssReads++;return [];},
  addEventListener(){window.__ssReads++;},get speaking(){window.__ssReads++;return false;},get pending(){return false;}};
  Object.defineProperty(window,'speechSynthesis',{configurable:true,get(){window.__ssReads++;return S;}});})()"""
DECODE = """async ()=>{const m=await (await fetch('radio/cfi/voice.json')).json();const ids=Object.values(m.d).concat(Object.values(m.f));
  const C=new (window.AudioContext||window.webkitAudioContext)();let ok=0,bad=[],dur=0;
  for(let i=0;i<ids.length;i+=8)await Promise.all(ids.slice(i,i+8).map(async id=>{try{const a=await (await fetch('radio/cfi/'+id+'.m4a')).arrayBuffer();
    const b=await C.decodeAudioData(a);if(b.duration>0.05){ok++;dur+=b.duration;}else bad.push(id);}catch(e){bad.push(id);}}));
  return {n:ids.length,ok:ok,bad:bad.slice(0,5),dur:dur,sets:Object.keys(m.sets).length,d:Object.keys(m.d).length,f:Object.keys(m.f).length};}"""
COVER = """async ()=>{const K=window.__kgeu;await K.CFIV&&0;const m=await (await fetch('radio/cfi/voice.json')).json();K.CFIV.man=m;
  const miss=[],D=t=>{const r=K.cfiClips('Dana',K.cfiSp(t));if(r.miss)miss.push(['Dana',t,r.miss]);},F=t=>{const r=K.cfiClips('Frank',K.cfiSp(t));if(r.miss)miss.push(['Frank',t,r.miss]);};
  const lines=[];
  for(const k of ['alt','spd','hdg','bank','trk','route','vs'])for(const v of [3,7,12,23,47,67,88,140,333,670,1234,2650])for(const s of [1,-1]){const t=K.cfiCue(k,s*v);if(t){lines.push(t);D(t);}}
  for(const L of K.SCHOOL.stages.flatMap(s=>s.lessons)){const T=(L.tasks||[]).map(t=>({ok:false,name:t.name,tip:t.tip,pts:0,w:t.w||1}));
    for(const letter of ['A','B','C','D','F'])for(let i=0;i<Math.max(1,T.length);i++){const r={letter:letter,lines:T.length?[T[i]]:[],failWhy:null};D(K.dbSay(r));}
    D(K.dbSay({letter:'F',lines:T.slice(0,1),failWhy:'stalled'}));}
  for(const e of ['solo','solo cross country'])D('Good flight. That is your '+e+' endorsement. I am signing your logbook.');
  const fx=['Glendale','Stadium','Tolleson','Downtown','Sky Harbor'],say=['Glendale','the stadium','Tolleson','downtown Phoenix','Sky Harbor'];
  for(const a of fx)for(const b of say)for(const h of [3,45,90,123,286,360])for(const m of [1,2,7,13]){const hs=String(h).padStart(3,'0').split('').map(d=>K.cfiSp(d)).join(' ');
    D(a+'. Next is '+b+', heading '+hs+', '+m+(m===1?' minute.':' minutes.'));}
  for(const b of say)for(const h of [90,286])D('On course to '+b+', heading '+String(h).padStart(3,'0').split('').map(d=>K.cfiSp(d)).join(' ')+'. Hold 3,500.');
  for(const c of [1,2,3,4,5,6,7,8,9,10,11,12])for(const n of [0.4,1.5,2.8])D('Engine failure. Best glide 68, pick a field, flow, declare. There is a field at your '+c+" o'clock, "+n.toFixed(1)+' miles.');
  for(const tn of ['left','right'])D('Turn '+tn+' on course after 700 feet.');
  for(const id of K.RIDE_POOL.concat(['landings'])){const q=K.rideTaskLine(id);F(q[1]||q[0]);
    const n=K.rideName?K.rideName(id):null;}
  for(const id of K.RIDE_POOL){const L=K.lessonDef(id),n=(L&&(L.short||L.name))||id,nm={stall:'Stalls',emerg:'Emergencies',hood:'Under the hood'}[id]||n;
    F('Skyhawk eight four zero one lima, this is your examiner, Frank Delgado. Six tasks today, to the ACS standards. I will not coach you. First, '+nm.charAt(0).toLowerCase()+nm.slice(1)+'.');}
  for(const t of ['That is within standard.','Noted.','That one was outside the standard. We will go on, and I will note it.','Go around.','Your controls.',
    'Congratulations. You are a private pilot. This is your temporary certificate; the plastic one comes in the mail.',
    'Notice of disapproval. Retrain the tasks below with your instructor and come back for those alone.'])F(t);
  return {n:lines.length,miss:miss.slice(0,30),nm:miss.length,ex:lines.filter(t=>/high|low/.test(t)).slice(0,6)};}"""


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=dict({'kgeuOnboard': 'pilot', 'kgeuTut': '1'}, **PLACED))
        d = await pg.evaluate(DECODE)
        ok('(a) voice.json: every clip decodes', d['ok'] == d['n'] and d['n'] > 300, d)
        c = await pg.evaluate(COVER)
        ok('(b) every run time line finds its clips', c['nm'] == 0, c['miss'][:12])
        print('  sample corrections:', c['ex'])
        await pg.context.close()

        pg = await page(b, url, vp=IPHONE_15, storage=dict({'kgeuOnboard': 'pilot', 'kgeuTut': '1'}, **PLACED))
        await pg.context.add_init_script(SPY)
        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
        await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
        await pg.evaluate(f"()=>{{const K={K};K.initAudio();K.vqLog(true);K.radioLog(true);window.__ssReads=0;K.cfiPrep('pattern');}}")
        # decoded on the menu first (headless, a flight's 300 ms frames starve the decode callbacks), then the lesson
        await pg.wait_for_function(f"()=>{K}.CFIV.want>0&&{K}.CFIV.got>={K}.CFIV.want", timeout=90000)
        await pg.evaluate(f"()=>{K}.startLesson('pattern',true)")
        cv = await pg.evaluate(f"()=>({{sets:{K}.CFIV.sets,want:{K}.CFIV.want,got:{K}.CFIV.got,err:{K}.CFIV.err}})")
        ok('(c) the pattern lesson decodes Dana common plus pattern at its start', cv['sets'] == ['d:common', 'd:pattern'] and cv['err'] == 0, cv)
        await pg.evaluate(f"()=>{{const K={K};K.lesBriefSkip();for(let i=0;i<40;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);}}")
        await pg.wait_for_timeout(1500)
        r = await pg.evaluate(f"""()=>{{const K={K},L=K.vqLog().filter(e=>e.who==='Dana');return {{plays:K.CFIV.plays,miss:K.CFIV.miss.slice(),n:L.length,
          voiced:L.filter(e=>e.speech).length,reads:window.__ssReads}}}}""")
        ok('(c) Dana voiced from clips', r['plays'] >= 1 and r['n'] >= 1, r)
        ok('(c) no speechSynthesis read at all', r['reads'] == 0, r['reads'])
        ok('(c) no Dana line missed its clips', not r['miss'], r['miss'])
        st = await pg.evaluate(f"""()=>{{const K={K};K.cfi('Turn crosswind now. Level off at 2,100.');for(let i=0;i<3;i++)K.stepFrame(0.1,false,true);
          const p0=K.CFIV.src.length;K.cfi('Go around. Full power, nose up, flaps up a notch.',null,{{urgent:1}});for(let i=0;i<2;i++)K.stepFrame(0.1,false,true);
          const c=K.VQ.cur;return {{p0:p0,cur:c&&c.line.text,pri:c&&c.pri,src:K.CFIV.src.length}}}}""")
        ok('(c) an urgent call (Go around) cuts her line at once and plays', st['p0'] > 0 and st['cur'] and st['cur'].startswith('Go around') and st['pri'] == 0 and st['src'] > 0, st)
        # (d) muted: set through the game's own toggle
        await pg.evaluate(f"()=>{{const K={K};if(K.setMuted)K.setMuted(true);}}")
        md = await pg.evaluate(f"""()=>{{const K={K};K.radioQ().length=0;if(K.VQ.cur)K.VQ.cur.end=K.VQ.cur.estEnd=0;K.stepFrame(0.1,false,true);const p=K.CFIV.plays;K.cfi('Turn base, then final. Aim for the numbers.');for(let i=0;i<4;i++)K.stepFrame(0.1,false,false);
          return {{d:K.CFIV.plays-p,cap:document.getElementById('atc').textContent,muted:K.muted?K.muted():null}}}}""")
        ok('(d) muted: no clip, the caption still shows', md['d'] == 0 and 'Turn base' in md['cap'], md)
        ok('(e) no page errors', not pg.errs, pg.errs[:4])
        await b.close()
    return ok.done('cfi_voice_check')

sys.exit(asyncio.run(main()))
