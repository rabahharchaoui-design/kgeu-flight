# School1 break-ui pass: worst-case data into the Flight School screens, through the data boundary only: SCHOOL,
# LES, G (gBegin/gHold/gRange/gEvent/gEnd), lesBrief*, setPlace, LOGB/logbookAdd, endorsements, startLesson and
# localStorage (kgeuSchool, kgeuLogbook, kgeuPlace, kgeuEndorse, kgeuLB) -- never the DOM, never game code.
# Fixture: a 12 letter callsign throughout; the stage map at 0 of 15 and 15 of 15 passed, every placement level,
# hours 0/20000/empty, REFRESHER, the Standard and Easy chips, a summary of 999.9 h, 9,999 landings and 3
# endorsements; the briefing on the lesson with SCHOOL's longest card body and the one with its longest quiz
# answer, both quiz outcomes, Skip shown (a replay); the debrief on Power off and power on stalls (its own seven
# tasks, forced to worst-case long detail through gRange/gEvent/gEnd) and on the stage check and first solo (the
# Endorsement row), both carrying the device board line, the EASY TOLERANCES tag and the callsign; the logbook at
# 60 entries and every ring full, and separately at 0 entries with no endorsements; prior hours 20,000; the HUD
# lesson card with three cue rows out during slow flight; the hood layout.
# Audit (copied from tests/breakui_check.py, as every *_break_check.py does): cut, spilling, outside its box or
# off screen text, and sub-44 px buttons.
#   .venv/bin/python tests/school_break_check.py --size 568x320        (one size per run, each under 2 minutes)
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, finger, ROOT
from school_fly import fly

ok = Checks()
K = 'window.__kgeu'
W, H = 844, 390
if '--size' in sys.argv:
    w, h = sys.argv[sys.argv.index('--size') + 1].split('x'); W, H = int(w), int(h)
TAG = f'{W}x{H}'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'school', 'break'); os.makedirs(SHOTS, exist_ok=True)
PATHS = []

# the audit, copied verbatim from tests/breakui_check.py (as tasking_break_check.py and ui1_break_check.py do)
AUDIT = """([sel,boxSel])=>{const R=document.querySelector(sel);if(!R)return ['no '+sel];const out=[],W=innerWidth,H=innerHeight;
  const rr=(boxSel?R.querySelector(boxSel):R).getBoundingClientRect();
  const vis=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden')return false;}const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};
  const inScroll=e=>{for(let n=e.parentElement;n&&n!==R.parentElement;n=n.parentElement){const s=getComputedStyle(n);if(/(auto|scroll)/.test(s.overflowX+s.overflowY))return true;}return false;};
  for(const e of R.querySelectorAll('*')){if(!vis(e))continue;const sc=inScroll(e);const own=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());const r=e.getBoundingClientRect(),cs=getComputedStyle(e);
    const tag=(e.id?'#'+e.id:e.className&&typeof e.className==='string'?'.'+e.className.split(' ')[0]:e.tagName)+' "'+(e.textContent||'').trim().slice(0,24)+'"';
    if(own&&e.scrollWidth>e.clientWidth+1&&cs.textOverflow!=='ellipsis'&&cs.overflowX!=='visible')out.push('cut '+tag);
    if(own&&e.scrollWidth>e.clientWidth+1&&cs.overflowX==='visible'&&cs.display!=='inline')out.push('spills '+tag+' '+e.scrollWidth+'>'+e.clientWidth);
    if(own&&!sc&&(r.left<rr.left-1||r.right>rr.right+1))out.push('outside '+tag+' '+Math.round(r.left)+'..'+Math.round(r.right)+' of '+Math.round(rr.left)+'..'+Math.round(rr.right));
    if(!sc&&(r.right>W+1||r.bottom>H+1||r.left<-1||r.top<-1))out.push('off screen '+tag);
    if((e.tagName==='BUTTON')&&(r.width<43.5||r.height<43.5))out.push('small '+tag+' '+Math.round(r.width)+'x'+Math.round(r.height));}
  return out;}"""

async def audit(pg, sel, state):
    res = await pg.evaluate(AUDIT, [sel, None])
    for f in res: print(f'  FAIL {TAG} {sel} {state}: {f}')
    ok(f'{TAG} {sel} {state} audit clean', len(res) == 0, res[:6])

async def shot(pg, name):
    p = os.path.join(SHOTS, f'{name}_{TAG}.png')
    await pg.wait_for_timeout(90)
    await pg.screenshot(path=p)
    PATHS.append(p)

BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchoolEasy': '0', 'kgeuTOD': 'day'}
LESSON_IDS = ['first', 'climbs', 'pattern', 'slow', 'stall', 'ground', 'landings', 'engine', 'solo',
              'steep', 'short', 'soft', 'xwind', 'emerg', 'hood']   # the 15 flyable lessons (school1 items 6-7)
CS = 'WWWWWWWWWWWW'   # the server's longest callsign, all W (as the other break_check fixtures use)

def mk_logbook():
    ents = []
    for i in range(60):
        lid = LESSON_IDS[i % len(LESSON_IDS)]
        f = i % 11 == 0
        ents.append({'id': lid, 'at': 1700000000000 - i * 86400000, 'score': 0 if f else 93, 'letter': 'F' if f else 'A',
                     'dual': 0 if f else 5.5, 'solo': 0 if f else 2.3, 'xc': 0 if f else 4.1,
                     'night': 0 if f else 3.2, 'inst': 0 if f else 2.7, 'ldg': 0 if f else 12})
    return {'dual': 900.0, 'solo': 99.9, 'xc': 5, 'night': 5, 'inst': 5, 'ldg': 9999, 'entries': ents}

SEEDED = dict(BASE, **{
    'kgeuPlace': json.dumps({'level': 'cert', 'hours': 20000, 'at': 1700000000000}),
    'kgeuSchool': json.dumps({f'cessna:{lid}': 'A' for lid in LESSON_IDS}),
    'kgeuLogbook': json.dumps(mk_logbook()),
    'kgeuEndorse': json.dumps({'solo': {'at': 1700000000000, 'by': 'Dana Reyes, CFI', 'lesson': 'solo'},
                                'instrument': {'at': 1700000000000, 'by': 'Dana Reyes, CFI', 'lesson': 'hood'},
                                'checkride': {'at': 1700000000000, 'by': 'Dana Reyes, CFI', 'lesson': 'landings'}}),
    'kgeuLB': json.dumps({'cs': CS, 'key': 'k' * 48, 'xp': 16000, 'creator': False, 'renamed': 0, 'renameAt': 0, 'created': 1}),
})
PRISTINE = dict(BASE, kgeuLB=SEEDED['kgeuLB'])

LONGEST_CARD = "()=>{let b=null,bl=-1;for(const s of window.__kgeu.SCHOOL.stages)for(const l of s.lessons){if(!l.cards)continue;for(const c of l.cards)if(c.b.length>bl){bl=c.b.length;b=l.id;}}return b;}"
LONGEST_QUIZ = "()=>{let b=null,bl=-1;for(const s of window.__kgeu.SCHOOL.stages)for(const l of s.lessons){if(!l.quiz)continue;for(const a of l.quiz.a)if(a.length>bl){bl=a.length;b=l.id;}}return b;}"
QUIZ_OF = "(id)=>{const L=[...window.__kgeu.SCHOOL.stages.flatMap(s=>s.lessons)].find(l=>l.id===id);return {ok:L.quiz.ok,n:L.quiz.a.length}}"

STALL_FIX = f"""()=>{{const K={K};K.startLesson('stall',true,{{brief:false}});
  K.gRange('loss',480,'Four hundred eighty feet lost recovering from the power off stall, nose held low far longer than the standard allows before flying speed returned');
  K.gEvent('pwr',true,'Full power was in by just under two seconds after the stall broke, inside the standard for getting the engine working for you again');
  K.gRange('wings',55,'Wings were leveled only after fifty five degrees of bank developed in the recovery, well outside the twenty degree standard for a clean recovery');
  K.gEvent('sec',true,'No secondary stall: the nose came up smoothly once flying speed was solidly back, well clear of the critical angle of attack');
  K.gRange('loss2',90,'Ninety feet lost recovering from the power on stall, well inside standard thanks to a prompt nose down and a clean wings level recovery');
  K.gRange('wings2',47,'Wings were leveled only after forty seven degrees of bank developed in the power on recovery, nearly two and a half times the standard');
  K.gEvent('sec2',false,'A secondary stall followed the power on recovery immediately after the nose came up, before the airplane was solidly flying again');
  K.gEnd();}}"""
SOLO_FIX = f"""()=>{{const K={K};K.startLesson('solo',true,{{brief:false}});
  K.gEvent('three',true,'Three full stop landings completed alone with no coaching from the right seat, each one a complete stop before the next takeoff roll began');
  K.gRange('fpm',290,'Two hundred ninety feet per minute at touchdown on the third full stop landing, just inside the three hundred foot per minute standard for a normal arrival');
  K.gRange('tdz',380,'Touched down three hundred eighty feet past the aiming point on the worst of the three landings, just inside the four hundred foot standard measured from the point chosen before the approach began');
  K.gRange('cl',5,'Five meters left of the centerline on the worst of the three landings, inside the six meter standard the whole way down final and through the flare');
  K.gEnd();}}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        # ---------------- pristine: 0 of 15 passed, first-visit placement intake, empty logbook ----------------
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=PRISTINE)
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(130)
        await audit(pg, '#plOv', 'first visit, no placement, no Back')
        back_hidden = await pg.evaluate("()=>document.getElementById('plBack').hidden")
        ok(f'{TAG} first visit: no Back', back_hidden)
        opts = await pg.evaluate("()=>[...document.querySelectorAll('#plOv .plO')].map(b=>b.dataset.lv)")
        for lv in opts:
            await pg.evaluate("(lv)=>document.querySelector('#plOv .plO[data-lv=\"'+lv+'\"]').click()", lv)
            await pg.wait_for_timeout(60)
            await audit(pg, '#plOv', f'option {lv} selected')
        await shot(pg, 'placement_first_visit')
        for hrs in ('0', '20000', ''):
            await pg.fill('#plHrs', hrs)
            await pg.evaluate("()=>document.getElementById('plHrs').dispatchEvent(new Event('change',{bubbles:true}))")
            await audit(pg, '#plOv', f'hours {hrs or "empty"}')
        await pg.fill('#plHrs', '')
        await finger(pg, '#plDay'); await pg.wait_for_timeout(130)   # closes the sheet (plDone), unlike setPlace alone
        await audit(pg, '#sSchool', '0 of 15 passed, never flown')
        prog = await pg.evaluate("()=>document.getElementById('schProg').textContent")
        ok(f'{TAG} 0 of 15 passed', prog == '0 of 15 passed', prog)
        await shot(pg, 'stagemap_0of15')
        await pg.evaluate("()=>document.getElementById('schLog').scrollIntoView()")
        await finger(pg, '#schLog'); await pg.wait_for_timeout(150)
        await audit(pg, '#sLog', '0 entries, no endorsements')
        rows0 = await pg.evaluate("()=>document.querySelectorAll('#logList .lE').length")
        end0 = await pg.evaluate("()=>document.getElementById('logEnd').textContent")
        ok(f'{TAG} 0 entries, no endorsements', rows0 == 0 and 'None yet' in end0, (rows0, end0))
        await shot(pg, 'logbook_empty')
        ok(f'{TAG} no page errors (pristine)', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # ---------------- heavily seeded worst case ----------------
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=SEEDED)
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(130)
        await audit(pg, '#sSchool', '15 of 15 passed, REFRESHER, the 999.9 h summary')
        prog = await pg.evaluate("()=>document.getElementById('schProg').textContent")
        ref = await pg.evaluate("()=>!document.getElementById('schRef').hidden")
        summ = await pg.evaluate("()=>document.getElementById('schSum').textContent")
        ok(f'{TAG} 15 of 15 passed, REFRESHER shown', prog == '15 of 15 passed' and ref, (prog, ref))
        ok(f'{TAG} the summary: 999.9 h, 9999 landings, 3 endorsements', summ == '999.9 h logged, 9999 landings, 3 endorsements', summ)
        await shot(pg, 'stagemap_15of15')
        await pg.evaluate(f"()=>{K}.ezSet(0,true)"); await pg.wait_for_timeout(150)
        await audit(pg, '#sSchool', 'Standard tolerances'); await shot(pg, 'stagemap_standard')
        await pg.evaluate(f"()=>{K}.ezSet(1,true)"); await pg.wait_for_timeout(150)
        await audit(pg, '#sSchool', 'Easy, double tolerances'); await shot(pg, 'stagemap_easy')

        # the placement intake reopened from Settings: Back shown, 20000 prior hours
        await pg.evaluate(f"()=>{K}.openMenu('sSet')"); await pg.wait_for_timeout(120)
        await pg.evaluate("()=>document.getElementById('bPlace').scrollIntoView()")   # #sSet scrolls at short heights
        await finger(pg, '#bPlace'); await pg.wait_for_timeout(130)
        await audit(pg, '#plOv', 'reopened, Back shown, 20000 prior hours')
        back_shown = not await pg.evaluate("()=>document.getElementById('plBack').hidden")
        hrs_val = await pg.evaluate("()=>document.getElementById('plHrs').value")
        ok(f'{TAG} reopened: Back shown, the 20000 hours kept', back_shown and hrs_val == '20000', (back_shown, hrs_val))
        await shot(pg, 'placement_reopened')
        await pg.evaluate("()=>document.getElementById('plBack').click()"); await pg.wait_for_timeout(260)   # plClose's 180ms close animation

        # the logbook: 60 entries, every ring full, 3 endorsements, 20,000 prior hours
        await pg.evaluate("()=>document.getElementById('schLog').scrollIntoView()")
        await finger(pg, '#schLog'); await pg.wait_for_timeout(180)
        await audit(pg, '#sLog', '60 entries, every ring full, 3 endorsements, 20000 prior hours')
        rings = await pg.evaluate("()=>[...document.querySelectorAll('#logRings .lRing')].map(r=>r.classList.contains('full'))")
        full = len(rings) == 6 and all(rings)
        prior = await pg.evaluate("()=>document.getElementById('logPrior').textContent")
        n60 = await pg.evaluate("()=>document.querySelectorAll('#logList .lE').length")
        end3 = await pg.evaluate("()=>document.querySelectorAll('#logEnd p').length")
        ok(f'{TAG} every ring full', full, rings)
        ok(f'{TAG} prior hours reads 20,000', '20,000' in prior, prior)
        ok(f'{TAG} the entries list keeps 60', n60 == 60, n60)
        ok(f'{TAG} 3 endorsements listed', end3 == 3, end3)
        await shot(pg, 'logbook_full')
        await pg.evaluate(f"()=>{K}.nav('sSchool',true)"); await pg.wait_for_timeout(150)

        # the briefing: SCHOOL's longest card body, and its longest quiz answers, both outcomes, Skip shown
        longest_card = await pg.evaluate(LONGEST_CARD)
        await pg.evaluate(f"(id)=>{K}.startLesson(id)", longest_card); await pg.wait_for_timeout(150)
        await audit(pg, '#brOv', f'{longest_card}: longest card body, Skip shown (a replay)')
        skip = await pg.evaluate("()=>!document.getElementById('brSkip').hidden")
        ok(f'{TAG} Skip briefing shown (every lesson already passed)', skip)
        await shot(pg, f'brief_card_{longest_card}')
        await pg.evaluate(f"()=>{K}.lesBriefNext()"); await pg.wait_for_timeout(150)
        await audit(pg, '#brOv', f'{longest_card}: next card')
        await shot(pg, f'brief_card_{longest_card}_last')
        await pg.evaluate(f"()=>{K}.lesBriefBack()"); await pg.wait_for_timeout(130)

        longest_quiz = await pg.evaluate(LONGEST_QUIZ)
        qz = await pg.evaluate(QUIZ_OF, longest_quiz)
        wrong = (qz['ok'] + 1) % qz['n']
        await pg.evaluate(f"(id)=>{K}.startLesson(id)", longest_quiz); await pg.wait_for_timeout(130)
        for _ in range(3):
            await pg.evaluate(f"()=>{K}.lesBriefNext()"); await pg.wait_for_timeout(150)
        await audit(pg, '#brOv', f'{longest_quiz}: longest quiz answers, unanswered')
        await shot(pg, f'brief_quiz_{longest_quiz}_unanswered')
        await pg.evaluate(f"(k)=>{K}.lesBriefAnswer(k)", wrong); await pg.wait_for_timeout(150)
        await audit(pg, '#brOv', f'{longest_quiz}: wrong answer'); await shot(pg, f'brief_quiz_{longest_quiz}_wrong')
        await pg.evaluate(f"()=>{K}.lesBriefBack()"); await pg.wait_for_timeout(130)
        await pg.evaluate(f"(id)=>{K}.startLesson(id)", longest_quiz); await pg.wait_for_timeout(130)
        for _ in range(3):
            await pg.evaluate(f"()=>{K}.lesBriefNext()"); await pg.wait_for_timeout(150)
        await pg.evaluate(f"(k)=>{K}.lesBriefAnswer(k)", qz['ok']); await pg.wait_for_timeout(150)
        await audit(pg, '#brOv', f'{longest_quiz}: right answer'); await shot(pg, f'brief_quiz_{longest_quiz}_right')
        await pg.evaluate(f"()=>{K}.lesBriefBack()"); await pg.wait_for_timeout(130)

        # the debrief: Power off and power on stalls (seven tasks, worst-case long detail), EASY TOLERANCES (still
        # on from above), the device board line, the 12 letter callsign
        await pg.evaluate(STALL_FIX); await pg.wait_for_timeout(150)
        await audit(pg, '#gradeOv', 'stall debrief: seven task rows, long detail, EASY TOLERANCES, device board, callsign')
        rows7 = await pg.evaluate("()=>document.querySelectorAll('#gLines .gt').length")
        ez = await pg.evaluate("()=>!!document.querySelector('#gScore .ezTag')")
        board = await pg.evaluate("()=>!!document.querySelector('#gLines .lbLine')")
        cs = await pg.evaluate("()=>{const e=document.querySelector('.rWho .rCs');return e&&e.textContent}")
        ok(f'{TAG} the stall debrief shows all seven task rows', rows7 == 7, rows7)
        ok(f'{TAG} the EASY TOLERANCES tag shows', ez)
        ok(f'{TAG} the device board line shows', board)
        ok(f'{TAG} the 12 letter callsign shows', cs == CS, cs)
        await shot(pg, 'debrief_stall')

        # the debrief: the stage check and first solo (the Endorsement row), the device board line
        await pg.evaluate(SOLO_FIX); await pg.wait_for_timeout(150)
        await audit(pg, '#gradeOv', 'solo debrief: the Endorsement row, device board, callsign')
        en = await pg.evaluate("()=>!!document.querySelector('#gLines .gEnd')")
        board2 = await pg.evaluate("()=>!!document.querySelector('#gLines .lbLine')")
        ok(f'{TAG} the Endorsement row shows', en)
        ok(f'{TAG} the device board line shows (solo)', board2)
        await shot(pg, 'debrief_solo')

        # the HUD lesson card: three cue rows all out, during slow flight
        await pg.evaluate(f"()=>{K}.startLesson('slow',true,{{brief:false}})"); await pg.wait_for_timeout(150)
        await fly(pg, 400, kt=55, vs=0, hdg=0, alt=3500, until="K.LES.ph===1")   # the cue strip only shows from ph 1
        await fly(pg, 20, kt=95, vs=0, hdg=170, alt=4700)
        cue = await pg.evaluate("()=>[...document.querySelectorAll('#lesCue .cue')].map(e=>e.className)")
        ok(f'{TAG} three cue rows, all out of tolerance', len(cue) == 3 and all('out' in c for c in cue), cue)
        await audit(pg, '#lesson', 'three cue rows out, the live instruction')
        await shot(pg, 'hud_cue_out')

        # the hood layout
        await pg.evaluate(f"()=>{K}.startLesson('hood',true,{{brief:false}})"); await pg.wait_for_timeout(180)
        L = await pg.evaluate("""()=>{const r=s=>{const e=document.getElementById(s);const q=e.getBoundingClientRect();return [q.left,q.top,q.right,q.bottom];};
          const hood=document.getElementById('hood').getBoundingClientRect(),atc=document.getElementById('atc');
          return {hood:[hood.left,hood.top,hood.width,hood.height],card:r('lesson'),
            dock:[...document.querySelectorAll('#dock button')].map(b=>b.getBoundingClientRect()).filter(x=>x.width).map(x=>[x.left,x.top,x.right,x.bottom]),
            sixpack:r('sixpack'),atcText:atc.textContent.trim(),atcCut:[...atc.querySelectorAll('.tx')].some(e=>e.scrollHeight>e.clientHeight+1)}}""")
        ok(f'{TAG} the hood fills the viewport', L['hood'][0] == 0 and L['hood'][1] == 0 and abs(L['hood'][2] - W) < 1 and abs(L['hood'][3] - H) < 1, L['hood'])
        ok(f'{TAG} Dana\'s subtitle is not cut', L['atcText'] and not L['atcCut'], L)
        def ov(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
        hit = [d for d in L['dock'] if ov(L['card'], d)] + (['six pack'] if ov(L['card'], L['sixpack']) else [])
        ok(f'{TAG} the lesson card clears the dock and the six pack', not hit, hit)
        await audit(pg, '#lesson', 'the hood: the card and cue strip')
        await shot(pg, 'hood_layout')

        ok(f'{TAG} no page errors (seeded)', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    print('\nScreenshots:')
    for pth in PATHS: print(' ', pth)
    sys.exit(ok.done(f'school_break_check {TAG}'))

asyncio.run(main())
