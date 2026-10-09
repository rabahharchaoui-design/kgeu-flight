# ui1 break-ui pass: worst-case data into the new menu screens (the tab bar, the Home rank card, Challenges,
# Boards and the XP pop), the way break-ui always does it: only through the data boundary (the mocked Worker in
# tests/ui1_mock.py and the game's own test hooks), never by poking the DOM or editing game code.
# Fixture (one worst case, mixed across rows, all plausible: the server allows callsigns A-Z0-9 of 3 to 12 chars):
#   callsign WWWWWWWWWWWW (12 chars), xp 7999 (1 XP short of Weapons School at 8000), then 16000 (Top Gun) and
#   123456, and no callsign at all; board rows with 12-char names, a creator badge, ranks up to Top Gun, scores to
#   1,234,567, a b747 row, mixed easy/hard; my row pinned at #12,345 of 123,456; an empty board; offline; the
#   picker sheet; a long Arizona daily (landing, then dogfight) with a long dogfight star line and the daily
#   marked used; the Fly tab's callsign/rank tag; a long XP pop reason held on screen.
# Audit (copied from tests/breakui_check.py, not imported: that file runs its own worker mock on import): the
# same failure signatures, on every visible screen and on the XP pop layer.
#   .venv/bin/python tests/ui1_break_check.py --size 844x390        (one size per run, each under 2 minutes)
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT
from ui1_mock import Mock

ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'ui1', 'break')
os.makedirs(SHOTS, exist_ok=True)

W, H = 844, 390
if '--size' in sys.argv:
    w, h = sys.argv[sys.argv.index('--size') + 1].split('x')
    W, H = int(w), int(h)
TAG = f'{W}x{H}'
PATHS = []

# ---- AUDIT, copied verbatim from tests/breakui_check.py (lines 44-56): every text box inside root spilling out of
# itself without an ellipsis, out of root, or off screen; buttons under the 44px tap target ----
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

# the picker sheet: every [data-lbb] chip at least 44px tall, inside the sheet or the sheet scrolls
CHIPS = """()=>{const sh=document.getElementById('lbSheet');if(!sh)return ['no sheet'];const sr=sh.getBoundingClientRect();
  const scrollable=sh.scrollHeight>sh.clientHeight+1,out=[];
  document.querySelectorAll('[data-lbb]').forEach(e=>{const r=e.getBoundingClientRect(),t=e.textContent.trim();
    if(r.height<43.5)out.push('chip short '+t+' '+Math.round(r.height)+'px');
    if(!scrollable&&(r.top<sr.top-1||r.bottom>sr.bottom+1))out.push('chip outside sheet '+t);});
  return out;}"""


async def audit(pg, sel, state):
    res = await pg.evaluate(AUDIT, [sel, None])
    for f in res:
        print(f'  FAIL {TAG} {sel} {state}: {f}')
    ok(f'{TAG} {sel} {state} audit clean', len(res) == 0, res[:6])


async def shot(pg, screen, state):
    p = os.path.join(SHOTS, f'{screen}_{state}_{TAG}.png')
    await pg.wait_for_timeout(250)
    await pg.screenshot(path=p)
    PATHS.append(p)


# ---- the fixture: worst-case board rows, through the mock only ----
NAMES = ['WWWWWWWWWWWW', 'MMMMMMMMMMMM', 'OHRABAH', 'JOX', 'W0W0W0W0W0W0', 'ABC', 'QQQQQQQQQQQQ', 'MESQUITE7777', 'HABOOBHABOOB', 'ZZZZZZZZZZZZ']
RANKS_MIX = ['Instructor Pilot', 'Weapons School', 'Top Gun']
ME_ROW = {'r': 12345, 'cs': 'WWWWWWWWWWWW', 'score': 1234567, 'secs': 61.1, 'mode': 'hard', 'xp': 7999, 'rank': 'Weapons School', 'creator': False}


def mkrows(lower):
    rows = []
    for i, cs in enumerate(NAMES):
        sc = round(30.1 + i * 41.7, 1) if lower else max(1, 1234567 - i * 97531)
        rows.append({'r': i + 1, 'cs': cs, 'score': sc, 'secs': 90 + i, 'ac': 'b747' if i == 5 else ['f16', 'c130', 'reaper', 'mq9b', 'cessna', 'archer'][i % 6],
                     'mode': 'easy' if i % 2 else 'hard', 'xp': 99000 - i * 700, 'rank': RANKS_MIX[i % 3], 'creator': cs == 'OHRABAH', 'when': 1})
    return rows


def mkboard(lower=False, empty=False):
    if empty:
        return {'rows': [], 'me': None, 'total': 0, 'ghost': None}
    return {'rows': mkrows(lower), 'me': dict(ME_ROW), 'total': 123456, 'ghost': None}


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        # ---------------- the main pilot: WWWWWWWWWWWW, xp 7999 (1 XP to Weapons School) ----------------
        m = Mock(cs='WWWWWWWWWWWW', xp=7999)
        m.extra['boards'] = {
            'daily': mkboard(),
            'df:clear:hard': mkboard(lower=True),
            'lesson:pattern': mkboard(),
            'free:landing': mkboard(),
            'arc:drop': mkboard(empty=True),
        }
        st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        st.update(m.storage())
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=st, pre=m.install)
        if H > W:
            await pg.evaluate("()=>{document.body.classList.add('portraitok');const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
        await pg.wait_for_timeout(500)

        # ---- Home: xp 7999 -> 16000 (Top Gun) -> 123456 ----
        await pg.evaluate(f"()=>{K}.openMenu('sHome')")
        await shot(pg, 'home', 'xp7999')
        await audit(pg, '#sHome', 'xp7999')
        await pg.evaluate(f"()=>{{const K={K};K.LB.P.xp=16000;K.LB.ui();}}")
        await pg.wait_for_timeout(300)
        await shot(pg, 'home', 'xp16000_topgun')
        await audit(pg, '#sHome', 'xp16000_topgun')
        await pg.evaluate(f"()=>{{const K={K};K.LB.P.xp=123456;K.LB.ui();}}")
        await pg.wait_for_timeout(300)
        await shot(pg, 'home', 'xp123456')
        await audit(pg, '#sHome', 'xp123456')
        await pg.evaluate(f"()=>{{const K={K};K.LB.P.xp=7999;K.LB.ui();}}")

        # ---- Fly tab: the tab bar extras with the 12-char callsign and Weapons School ----
        await pg.evaluate(f"()=>{K}.tabGo('sFly')")
        await shot(pg, 'fly', 'tabbar')
        await audit(pg, '#sFly', 'tabbar')
        await audit(pg, '#mTabs', 'tabbar')

        # ---- Boards ----
        await pg.evaluate(f"()=>{{const K={K};K.openMenu();K.LB.lbOpen('daily')}}")
        await shot(pg, 'lb', 'daily_today')
        await audit(pg, '#sLb', 'daily_today')

        await pg.evaluate(f"()=>{K}.LB.lbOpen('df:clear:hard')")
        await shot(pg, 'lb', 'df_clear_hard')
        await audit(pg, '#sLb', 'df_clear_hard')
        title = await pg.evaluate("()=>document.getElementById('lbTitle').textContent")
        ok(f'{TAG} df:clear:hard title reads clear time', title == 'Red Flag Dogfight, clear time', title)

        await pg.evaluate(f"()=>{K}.LB.lbOpen('lesson:pattern')")
        await pg.evaluate("()=>document.querySelector('[data-lbp=all]').click()")
        await shot(pg, 'lb', 'lesson_pattern_all')
        await audit(pg, '#sLb', 'lesson_pattern_all')

        await pg.evaluate(f"()=>{K}.LB.lbOpen('free:landing')")
        await pg.evaluate("()=>document.querySelector('[data-lbp=all]').click()")
        await pg.evaluate("()=>{document.getElementById('lbRows').scrollTop=1e4}")
        await pg.wait_for_timeout(200)
        await shot(pg, 'lb', 'free_landing_all_end')
        await audit(pg, '#sLb', 'free_landing_all_end')
        pin = await pg.evaluate("()=>{const e=document.querySelector('#lbMe .lbRow');return e?e.textContent:null}")
        ok(f'{TAG} the pinned row reads #12,345 of 123,456', pin and '12,345' in pin and '123,456' in pin, pin)

        await pg.evaluate("()=>document.getElementById('lbPick').click()")
        await shot(pg, 'lb', 'picker_sheet')
        chips = await pg.evaluate(CHIPS)
        for f in chips:
            print(f'  FAIL {TAG} picker sheet: {f}')
        ok(f'{TAG} every board chip is >=44px and inside the sheet (or it scrolls)', len(chips) == 0, chips[:6])
        await pg.evaluate("()=>document.getElementById('lbPick').click()")

        await pg.evaluate(f"()=>{K}.LB.lbOpen('arc:drop')")
        await shot(pg, 'lb', 'empty')
        await audit(pg, '#sLb', 'empty')
        msg = await pg.evaluate("()=>document.getElementById('lbRowsIn').textContent")
        ok(f'{TAG} an empty board reads No scores yet', 'No scores yet' in msg, msg)

        m.offline = True
        await pg.evaluate(f"()=>{K}.LB.lbFetch? {K}.LB.lbFetch(true):{K}.LB.lbOpen('daily')")
        await pg.wait_for_timeout(600)
        await shot(pg, 'lb', 'offline')
        await audit(pg, '#sLb', 'offline')
        off = await pg.evaluate("()=>document.getElementById('lbRowsIn').textContent")
        ok(f'{TAG} offline reads the Offline message', 'Offline' in off, off)
        m.offline = False

        # ---------------- Challenges: a long Arizona daily, then a dogfight day, then long star lines ----------------
        await pg.evaluate(f"()=>{{const K={K};K.dailyRegion('az');K.openMenu('sArc');}}")
        await shot(pg, 'arc', 'az_landing_daily')
        await audit(pg, '#sArc', 'az_landing_daily')

        await pg.evaluate(f"()=>{{const K={K};K.dailyKind('dogfight');K.nav('sArc');}}")
        await shot(pg, 'arc', 'az_dogfight_daily')
        await audit(pg, '#sArc', 'az_dogfight_daily')

        await pg.evaluate(f"()=>{{const K={K};K.SCORE.best['arc:dogfight:hard']={{pts:12345,kills:10,stars:3,clr:359.9}};K.nav('sArc');}}")
        await shot(pg, 'arc', 'dogfight_long_stars')
        await audit(pg, '#sArc', 'dogfight_long_stars')
        feat = await pg.evaluate("()=>document.querySelector('.mcard.feat .sc').textContent")
        ok(f'{TAG} the dogfight card shows the long best line', '12,345' in feat and '10' in feat, feat)

        day = await pg.evaluate(f"()=>{K}.dailySpec().day")
        await pg.evaluate("(d)=>localStorage.setItem('kgeuDaily',JSON.stringify({day:d,used:1}))", day)
        await pg.evaluate(f"()=>{K}.nav('sArc')")
        await shot(pg, 'arc', 'daily_used')
        await audit(pg, '#sArc', 'daily_used')
        used = await pg.evaluate("()=>document.querySelector('#arcCards .mcard[data-m=daily] .d').textContent")
        ok(f'{TAG} the used daily reads practice only', 'Official attempt flown, practice only' in used, used)

        # ---------------- the XP pop: a long reason, held on screen ----------------
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway');}}")
        await pg.wait_for_timeout(500)
        await pg.evaluate(f"()=>{K}.xpPop(1234,'Sent: Lesson: Pattern and touch and go  \\u00b7  Rank up: Instructor Pilot',{{hold:6000}})")
        await pg.wait_for_timeout(1200)
        await shot(pg, 'xppop', 'long_reason')
        await audit(pg, '#xpPops', 'long_reason')

        ok(f'{TAG} no page errors (main pilot)', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # ---------------- Home with no callsign ----------------
        m2 = Mock(cs=None)
        st2 = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        st2.update(m2.storage())
        pg2 = await page(b, url, vp={'width': W, 'height': H}, storage=st2, pre=m2.install)
        if H > W:
            await pg2.evaluate("()=>{document.body.classList.add('portraitok');const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            await pg2.wait_for_timeout(500)
        await pg2.evaluate("()=>{const o=document.getElementById('csOv');if(o)o.classList.remove('on')}")
        await pg2.evaluate(f"()=>{K}.openMenu('sHome')")
        await pg2.wait_for_timeout(400)
        await shot(pg2, 'home', 'no_callsign')
        await audit(pg2, '#sHome', 'no_callsign')
        nc = await pg2.evaluate("()=>document.getElementById('hRkCs').textContent")
        ok(f'{TAG} no callsign reads No callsign yet', nc == 'No callsign yet', nc)
        ok(f'{TAG} no page errors (no callsign)', not pg2.errs, pg2.errs[:3])
        await pg2.context.close()

        await b.close()
    print('\nScreenshots:')
    for pth in PATHS:
        print(' ', pth)
    sys.exit(ok.done(f'ui1_break_check {TAG}'))

asyncio.run(main())
