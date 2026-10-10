# Tasking item 6, break-ui on the mission UI: worst-case data, plausible or at its limit, through the data boundary only
# (the roll, via TASK.test.roll; a template's score; localStorage; the callsign the server allows), never the DOM.
# Fixture (mixed): each tasking's briefing at its longest (FINDER at night in Easy, SHEPHERD at 11,000 ft with a 22 kt wind
# and its longest corridor, LIFELINE at 18 km with 16 kt, OVERWATCH Hard); every reply set the game asks (WILCO/UNABLE,
# CONTACT/LOOKING, YELLOW/VIOLET smoke, REPORT vehicle departs, REPORT talk-on, MARK over the flash) in the plain bar, in
# the ball view and beside the C-130's LOOK pad; the stage card's longest lines; a results card with 100 of 100, a long
# title, every line long and "#60 of 60 +81 XP PERSONAL BEST"; a board with 60 runs (scores 100 to 0), a 12 letter
# callsign (the server's longest, all W), no callsign, one run, none; the Challenges cards with best scores.
#   .venv/bin/python tests/tasking_break_check.py --size 568x320   (one size per run)
import asyncio, os, sys, json
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT
ok = Checks()
K = 'window.__kgeu'
W, H = 844, 390
if '--size' in sys.argv:
    w, h = sys.argv[sys.argv.index('--size') + 1].split('x'); W, H = int(w), int(h)
TAG = f'{W}x{H}'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'tasking', 'break'); os.makedirs(SHOTS, exist_ok=True)
# the audit, copied from tests/ui1_break_check.py (importing it runs that test)
AUDIT = """([sel,boxSel])=>{const R=document.querySelector(sel);if(!R)return ['no '+sel];const out=[],W=innerWidth,H=innerHeight;
  const rr=(boxSel?R.querySelector(boxSel):R).getBoundingClientRect();
  const vis=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden')return false;}const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};
  // inside a scroller (a tab strip, the region chips, the stats list) being out of view is by design
  const inScroll=e=>{for(let n=e.parentElement;n&&n!==R.parentElement;n=n.parentElement){const s=getComputedStyle(n);if(/(auto|scroll)/.test(s.overflowX+s.overflowY))return true;}return false;};
  for(const e of R.querySelectorAll('*')){if(!vis(e))continue;const sc=inScroll(e);const own=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());const r=e.getBoundingClientRect(),cs=getComputedStyle(e);
    const tag=(e.id?'#'+e.id:e.className&&typeof e.className==='string'?'.'+e.className.split(' ')[0]:e.tagName)+' "'+(e.textContent||'').trim().slice(0,24)+'"';
    if(own&&e.scrollWidth>e.clientWidth+1&&cs.textOverflow!=='ellipsis'&&cs.overflowX!=='visible')out.push('cut '+tag);
    if(own&&e.scrollWidth>e.clientWidth+1&&cs.overflowX==='visible'&&cs.display!=='inline')out.push('spills '+tag+' '+e.scrollWidth+'>'+e.clientWidth);
    if(own&&!sc&&(r.left<rr.left-1||r.right>rr.right+1))out.push('outside '+tag+' '+Math.round(r.left)+'..'+Math.round(r.right)+' of '+Math.round(rr.left)+'..'+Math.round(rr.right));
    if(!sc&&(r.right>W+1||r.bottom>H+1||r.left<-1||r.top<-1))out.push('off screen '+tag);
    if((e.tagName==='BUTTON')&&(r.width<43.5||r.height<43.5))out.push('small '+tag+' '+Math.round(r.width)+'x'+Math.round(r.height));}
  return out;}"""
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def audit(pg, sel, state):
    res = await pg.evaluate(AUDIT, [sel, None])
    ok(f'{TAG} {sel} {state}: nothing cut, spilling or off screen, 44 px targets', not res, res[:5])
async def shot(pg, name):
    await pg.evaluate("()=>window.__kgeu.stepFrame(0.02,false,false)")
    await pg.screenshot(path=os.path.join(SHOTS, f'{TAG}_{name}.png'))
# a reply's label must show whole (an ellipsis on WILCO is a broken button)
LABELS = """()=>[...document.querySelectorAll('#tkReply button')].map(b=>{const l=b.querySelector('b'),s=b.querySelector('small'),r=b.getBoundingClientRect();
  return {k:b.dataset.k,cut:l.scrollWidth>l.clientWidth+1,subCut:!!s&&s.scrollWidth>s.clientWidth+1,w:Math.round(r.width),h:Math.round(r.height)}})"""
REPLIES = [('wilco', "[{k:'WILCO'},{k:'UNABLE'}]"), ('contact', "[{k:'CONTACT',say:''},{k:'LOOKING',say:''}]"),
           ('smoke', "[{k:'YELLOW',sub:'smoke'},{k:'VIOLET',sub:'smoke'}]"), ('report', "[{k:'REPORT',sub:'vehicle departs'}]"),
           ('talk', "[{k:'REPORT',sub:'talk-on'}]"), ('mark', "[{k:'MARK',sub:'over the flash'}]")]
EXTREME = {'finder': "d=>{d.box.W=2600;d.box.H=3200;}", 'shepherd': "d=>{d.alt=11000;d.wkt=22;d.wdir=360;d.len=34900;d.par=316;}",
           'lifeline': "d=>{d.wkt=16;d.wdir=360;d.runHdg=360;d.par=245;}", 'overwatch': "d=>{d.dist=8500;d.par=419;d.stPar=284;}"}

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('rookie', 'pilot'):
            pg = await page(b, url, vp={'width': W, 'height': H}, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTOD': 'night' if skill == 'rookie' else 'day'})
            for tid in ('overwatch', 'lifeline', 'shepherd', 'finder'):
                await pg.evaluate(f"()=>{{const K={K};K.TASK.test.roll={EXTREME[tid]};K.taskStop();K.taskStart('{tid}',{{seed:77}})}}"); await pg.wait_for_timeout(350)
                await audit(pg, '#tkBrief', f'{skill} {tid} briefing (longest roll)')
                if tid in ('finder', 'shepherd'): await shot(pg, f'brief_{tid}_{skill}')
                await pg.evaluate(f"()=>{{const K={K};K.TASK.test.roll=null;K.taskGo()}}")
                await pg.evaluate(STEP, 30)
                # every reply set, in this tasking's own context (the ball view for Overwatch, the LOOK pad for Lifeline)
                if tid == 'overwatch':
                    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;s.pos.set(d.c.x+2400,600,d.c.z);s.vel.set(0,0,-64);s.onGround=false;K.auto();let k=0;while(K.camMode()!==2&&k++<5)K.cycleCam();}}")
                    await pg.evaluate(STEP, 10)
                for name, opts in REPLIES:
                    await pg.evaluate(f"()=>{{const K={K};K.tkAsk({opts},{{keep:1}});}}"); await pg.evaluate(STEP, 2); await pg.wait_for_timeout(260)
                    lab = await pg.evaluate(LABELS)
                    ok(f'{TAG} {skill} {tid} replies {name}: every label whole, 44 tall, 56 wide', lab and all(not x['cut'] and not x['subCut'] and x['h'] >= 44 and x['w'] >= 56 for x in lab), lab)
                    await audit(pg, '#tkReply', f'{skill} {tid} replies {name}')
                    if name == 'contact': await shot(pg, f'reply_{tid}_{skill}')
                await pg.evaluate(f"()=>{{const K={K};K.TASK.ask=null;}}"); await pg.evaluate(STEP, 40)
                await audit(pg, '#topCol', f'{skill} {tid} stage card and radio line')
            # the results card at its worst, through a template's score and a full device board
            await pg.evaluate(f"""()=>{{const K={K};K.taskStop();const L=[];for(let i=0;i<59;i++)L.push({{s:Math.max(0,99-Math.floor(i*1.7)),secs:300,ac:'mq9b',mode:i%2?'easy':'hard',when:Date.now()-i*36e5}});
              localStorage.setItem('kgeuTaskLB',JSON.stringify({{'task:overwatch':L}}));
              K.TASKS.drillw={{name:'Overwatch',role:'Surveillance',ac:'mq9b',base:'luke',limit:600,roll:(R,d)=>{{d.wdir=360;d.wkt=22;d.par=419;}},
                brief:d=>({{ac:'x',sit:'x',facts:[]}}),spawn:d=>{{}},stages:[{{id:'a',name:'a',obj:d=>['a','b'],tick:d=>true}}],
                score:d=>({{score:100,title:'Eyes never left it',wait:0,lines:[['Time on target','100 %  (338 of 338 s)'],['Standoff in band','100 %  ·  9 overflights'],['Report after departure','39.9 s  ·  12 early'],['On station','4:44  (par 4:44)'],['Talk-on','the team found it']],
                  tip:'Lock the ball on the target (LOCK) and it stays on as you circle.'}})}};}}""")
            await pg.evaluate(f"()=>{{const K={K};K.TASK.test.noBrief=true;K.taskStart('drillw',{{seed:1}})}}"); await pg.evaluate(STEP, 3)
            # the device board is task:drillw's own: put the same 59 runs there so this run is #1 of 60, a best
            await pg.evaluate(f"()=>{{const A=JSON.parse(localStorage.getItem('kgeuTaskLB'));A['task:drillw']=A['task:overwatch'];localStorage.setItem('kgeuTaskLB',JSON.stringify(A));}}")
            await pg.wait_for_timeout(600); await pg.evaluate(STEP, 3)
            await audit(pg, '#missOv', f'{skill} results card, 100 of 100, every line long')
            await shot(pg, f'results_{skill}')
            await pg.evaluate(f"()=>{{const K={K};K.TASK.test.noBrief=false;K.taskStop();K.openMenu('sArc');delete K.TASKS.drillw;}}")
            await pg.evaluate("()=>localStorage.setItem('kgeuTaskBest',JSON.stringify({overwatch:{score:100,letter:'A'},lifeline:{score:0,letter:'F'},shepherd:{score:59,letter:'D'},finder:{score:100,letter:'A'}}))")
            await pg.evaluate(f"()=>{{const K={K};K.nav('sHome');K.nav('sArc');document.getElementById('arcCards').scrollTop=1e4;}}"); await pg.wait_for_timeout(300)
            await audit(pg, '#sArc', f'{skill} Challenges scrolled to the Taskings, best scores 0 and 100')
            await shot(pg, f'challenges_{skill}')
            # the boards: 60 runs with the longest callsign, then none, then one, then no callsign
            await pg.evaluate("()=>{const P=JSON.parse(localStorage.getItem('kgeuLB')||'null');}")
            for state, lb, cs in [('60 runs, 12 letter callsign', 'full', 'WWWWWWWWWWWW'), ('no runs', 'none', 'WWWWWWWWWWWW'), ('one run', 'one', 'WWWWWWWWWWWW'), ('no callsign', 'full', None)]:
                await pg.evaluate(f"""([lb,cs])=>{{const K={K},E=K.LB.E;E.P=cs?{{cs:cs,key:'k'.repeat(48),xp:16000,creator:false}}:null;
                  const L=[];for(let i=0;i<(lb==='full'?60:lb==='one'?1:0);i++)L.push({{s:Math.max(0,100-Math.floor(i*1.7)),secs:300,ac:i%3?'f16':'c130',mode:i%2?'easy':'hard',when:Date.now()-i*864e5}});
                  localStorage.setItem('kgeuTaskLB',JSON.stringify({{'task:shepherd':L}}));K.LB.lbOpen('task:shepherd');}}""", [lb, cs]); await pg.wait_for_timeout(400)
                await audit(pg, '#sLb', f'{skill} Shepherd board: {state}')
                if state.startswith('60'):
                    await pg.evaluate("()=>document.querySelector('[data-lbp=all]').click()"); await pg.wait_for_timeout(300)
                    n = await pg.evaluate("()=>document.querySelectorAll('#lbRowsIn .lbRow').length")
                    await audit(pg, '#sLb', f'{skill} Shepherd board: all time, {n} rows')
                    ok(f'{TAG} {skill} all time shows this device\'s 30 best of 60, the total 60', n == 30 and await pg.evaluate("()=>document.getElementById('lbTotal').textContent") == '60 runs', n)
                    await pg.evaluate("()=>document.querySelector('[data-lbp=today]').click()")
                t = await pg.evaluate("()=>({tot:document.getElementById('lbTotal').textContent,me:document.getElementById('lbMe').innerText,msg:document.getElementById('lbRowsIn').innerText.slice(0,40)})")
                if state == 'one run': ok(f'{TAG} {skill} one run reads "1 run"', t['tot'] == '1 run', t)
                if state == 'no runs': ok(f'{TAG} {skill} no runs: an empty state, not a blank list', 'No runs yet' in t['msg'] and t['tot'] == '0 runs', t)
                if state.startswith('60'): await shot(pg, f'board_{skill}')
            ok(f'{TAG} {skill}: no console errors', not pg.errs, pg.errs[:3])
            await pg.close()
        await b.close()
    return ok.done(f'tasking_break_check {TAG}')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
