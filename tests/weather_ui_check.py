# Weather item 2: the WEATHER pill, the dice and the sheet (#wxOv), on the Fly tab and in the pause sheet.
# Opens the Fly tab, checks the pill's text and room (the longest names, Thunderstorm and Gusty winds, show their short
# names Storm and Gusty in the pills; the airports keep their width at 844 and up),
# taps the pill, measures the nine tiles (44 px or more, on screen, no scroll in landscape), picks every weather by
# touch (localStorage kgeuWX and the pill follow, the sheet closes), the dice (random on, the tag, the toast), the
# pause sheet's pill, and the migration (an old install's kgeuTOD 'haboob' reads as Day + Haboob, both saved).
# Weather regions item (regions(), once): the daily card shows the day's weather as a fact (icon and name); a lesson
# sets its fixed weather (clear; the crosswind lesson gusty under its own steady wind) without saving it and the
# player's comes back at the menu; a mission and a tasking do the same; Tokyo's first visit rolls from Tokyo's odds,
# seeded by the day (__kgeu.wxFirst), saved as kgeuWX_rjtt only.
# Measuring in the style of tests/ui1_break_check.py (not imported). Shots: /tmp/wx_ui/<size>_<screen>.png
#   .venv/bin/python tests/weather_ui_check.py                    (844x390 and 568x320, the full pass)
#   .venv/bin/python tests/weather_ui_check.py --size 568x320     (one size)
#   .venv/bin/python tests/weather_ui_check.py --sheet 390x844    (the sheet only, at a size: 667x375, 932x430, portrait)
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, finger

ok = Checks()
K = 'window.__kgeu'
SHOTS = '/tmp/wx_ui'
os.makedirs(SHOTS, exist_ok=True)
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuPlace': '{"level":"ride","hours":null}'}
IDS = ['clear', 'scattered', 'overcast', 'rain', 'storm', 'fog', 'gusty', 'haboob']
SHORT = {'storm': 'Storm', 'gusty': 'Gusty'}
NAMES = {'clear': 'Clear', 'scattered': 'Scattered', 'overcast': 'Overcast', 'rain': 'Rain', 'storm': 'Thunderstorm', 'fog': 'Fog', 'gusty': 'Gusty winds', 'haboob': 'Haboob'}

# the pill and the dice in their row: sizes, the name not cut (or ellipsed with room for the short name in the pause
# sheet at 568), no overlap with the neighbours, on screen
PILL = """([pid,rid])=>{const p=document.getElementById(pid),d=document.getElementById(rid),out=[];if(!p||!d)return {err:['missing']};
  const pr=p.getBoundingClientRect(),dr=d.getBoundingClientRect(),W=innerWidth,H=innerHeight;
  const shown=[...p.querySelectorAll('b > span')].find(s=>getComputedStyle(s).display!=='none');
  const b=p.querySelector('b');
  if(pr.height<43.5||pr.width<43.5)out.push('pill small '+Math.round(pr.width)+'x'+Math.round(pr.height));
  // the pause row up to 700 wide: the pill is the icon alone and the dice steps out (the sheet's Random tile)
  const diceOut=getComputedStyle(d).display==='none';if(diceOut&&!(pid==='wxPillP'&&W<=700))out.push('dice hidden');
  if(!diceOut&&(dr.height<43.5||dr.width<43.5))out.push('dice small '+Math.round(dr.width)+'x'+Math.round(dr.height));
  if(b.scrollWidth>b.clientWidth+1)out.push('name cut '+shown.textContent+' '+b.scrollWidth+'>'+b.clientWidth);
  if(!diceOut&&pr.right>dr.left+0.5)out.push('pill over dice');
  if(pr.left<0||pr.right>W+1||pr.bottom>H+1||!diceOut&&(dr.right>W+1||dr.bottom>H+1))out.push('off screen');
  const row=p.closest('.frow'),loc=row.querySelector('.locG').getBoundingClientRect();
  if(loc.right>pr.left-1)out.push('location group overlaps '+Math.round(loc.right)+'>'+Math.round(pr.left));
  row.querySelectorAll('.pick[data-tod]').forEach(c=>{const r=c.getBoundingClientRect();if(r.width<43.5||r.height<43.5)out.push('time chip small '+c.textContent+' '+Math.round(r.width));
    const cb=c.querySelector('b');if(cb.scrollWidth>cb.clientWidth+1)out.push('time chip cut '+c.textContent);if(r.right>pr.left+0.5&&r.left<pr.right)out.push('time chip under pill');});
  return {err:out,dice:!diceOut,text:shown?shown.textContent:'',icon:p.querySelector('i').textContent,tag:!p.querySelector('small').hidden,w:Math.round(pr.width),loc:Math.round(loc.width)};}"""

# the sheet: nine tiles, each 44 px or more, on screen and inside the sheet, names not cut, no scroll in landscape
SHEET = """()=>{const ov=document.getElementById('wxOv'),sh=ov.querySelector('.sheet'),out=[],W=innerWidth,H=innerHeight;
  if(!ov.classList.contains('on'))return {err:['not open']};const sr=sh.getBoundingClientRect(),T=[...ov.querySelectorAll('.wxT')];
  if(T.length!==9)out.push('tiles '+T.length);
  const scroll=sh.scrollHeight>sh.clientHeight+1||ov.scrollHeight>ov.clientHeight+1;
  let minH=1e9;for(const t of T){const r=t.getBoundingClientRect(),n=t.querySelector('b');minH=Math.min(minH,r.height);
    if(r.height<43.5||r.width<43.5)out.push('tile small '+t.dataset.wx+' '+Math.round(r.width)+'x'+Math.round(r.height));
    if(!scroll&&(r.top<sr.top-1||r.bottom>sr.bottom+1||r.left<sr.left-1||r.right>sr.right+1))out.push('tile outside sheet '+t.dataset.wx);
    if(!scroll&&(r.bottom>H+1||r.right>W+1||r.top<-1||r.left<-1))out.push('tile off screen '+t.dataset.wx);
    if(n.scrollWidth>n.clientWidth+1)out.push('name cut '+n.textContent);
    const hn=t.querySelector('span');if(hn&&getComputedStyle(hn).display!=='none'&&hn.scrollHeight>hn.clientHeight+1)out.push('hint cut '+hn.textContent);}
  const x=document.getElementById('wxX').getBoundingClientRect();if(x.width<43.5||x.height<43.5)out.push('close small');
  for(const t of T){const r=t.getBoundingClientRect();if(!(x.right<=r.left||x.left>=r.right||x.bottom<=r.top||x.top>=r.bottom))out.push('close over tile '+t.dataset.wx);}
  const sel=T.filter(t=>t.classList.contains('sel')).map(t=>t.dataset.wx);
  return {err:out,scroll:scroll,minH:Math.round(minH),sel:sel,h:Math.round(sr.height),w:Math.round(sr.width)};}"""


# the roll toast covers no visible button (taps go through it anyway) and stays on screen
TOAST = """(root)=>{const t=document.getElementById('wxToast'),r=t.getBoundingClientRect(),out=[];if(!t.classList.contains('on'))return ['not shown'];
  if(r.left<0||r.right>innerWidth+1||r.top<0||r.bottom>innerHeight+1)out.push('off screen');
  for(const b of document.querySelectorAll(root+' button')){const q=b.getBoundingClientRect();if(!q.width||!q.height||getComputedStyle(b).visibility==='hidden')continue;
    const x=Math.min(r.right,q.right)-Math.max(r.left,q.left),y=Math.min(r.bottom,q.bottom)-Math.max(r.top,q.top);if(x>1&&y>1)out.push('over '+(b.id||b.textContent.trim().slice(0,14)));}
  return out;}"""


async def ls(pg, k):
    return await pg.evaluate(f"()=>localStorage.getItem({k!r})")


async def shot(pg, tag, screen):
    await pg.wait_for_timeout(260)
    p = f'{SHOTS}/{tag}_{screen}.png'
    await pg.screenshot(path=p)
    print('  shot', p)


async def open_sheet(pg, pill):
    await finger(pg, '#' + pill)
    await pg.wait_for_timeout(300)


async def sheet_only(b, url, W, H):
    tag = f'{W}x{H}'
    pg = await page(b, url, vp={'width': W, 'height': H}, storage=BASE)
    await pg.evaluate(f"()=>{{{K}.setWX('storm');{K}.openFly();}}")
    await pg.wait_for_timeout(400)
    await pg.evaluate(f"()=>{K}.wxOpen()")
    await pg.wait_for_timeout(400)
    s = await pg.evaluate(SHEET)
    land = W > H
    ok(f'{tag} sheet: nine tiles, 44 px or more, nothing cut' + (', no scroll' if land else ''), not s['err'] and (not land or not s['scroll']), s)
    await shot(pg, tag, 'sheet')
    ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()


async def full(b, url, W, H):
    tag = f'{W}x{H}'
    vp = {'width': W, 'height': H}
    pg = await page(b, url, vp=vp, storage=BASE)
    await pg.evaluate(f"()=>{K}.openFly()")
    await pg.wait_for_timeout(500)
    r = await pg.evaluate(PILL, ['wxPill', 'wxRnd'])
    pr = await pg.evaluate(f"()=>{K}.prefs()")
    ok(f'{tag} Fly tab: pill shows the default weather, row fits', not r['err'] and not r['tag'] and r['text'] == SHORT.get(pr['wx'], NAMES[pr['wx']]), [r, pr['wx']])
    await shot(pg, tag, 'fly')
    # the longest names in the pill
    for wid in ('storm', 'gusty'):
        await pg.evaluate(f"()=>{K}.setWX({wid!r})")
        r = await pg.evaluate(PILL, ['wxPill', 'wxRnd'])
        ok(f'{tag} Fly tab pill: {NAMES[wid]} fits (its short name, the sheet has the full one), nothing overlaps', not r['err'] and r['text'] == SHORT.get(wid, NAMES[wid]), r)
    await shot(pg, tag, 'fly_gusty')
    # the sheet by touch
    await open_sheet(pg, 'wxPill')
    s = await pg.evaluate(SHEET)
    ok(f'{tag} sheet opens from the pill: nine tiles, 44 px or more, no scroll, Gusty winds ringed', not s['err'] and not s['scroll'] and s['sel'] == ['gusty'], s)
    await shot(pg, tag, 'sheet')
    # pick every weather by touch
    for wid in IDS:
        if not await pg.evaluate("()=>document.getElementById('wxOv').classList.contains('on')"):
            await open_sheet(pg, 'wxPill')
        await finger(pg, f'#wxOv .wxT[data-wx="{wid}"]')
        await pg.wait_for_timeout(350)
        st = await pg.evaluate("()=>[localStorage.getItem('kgeuWX'),localStorage.getItem('kgeuWXR'),document.getElementById('wxOv').classList.contains('on'),"
                               "document.querySelector('#wxPill .lg').textContent,window.__kgeu.WX().clouds]")
        ok(f'{tag} tile {NAMES[wid]}: saved, pill follows, sheet closed', st[0] == wid and st[1] == '0' and not st[2] and st[3] == NAMES[wid], st)
    # a tap on the backdrop closes it; the close button too
    await open_sheet(pg, 'wxPill')
    await pg.touchscreen.tap(4, H - 4)
    await pg.wait_for_timeout(350)
    ok(f'{tag} backdrop tap closes the sheet', not await pg.evaluate("()=>document.getElementById('wxOv').classList.contains('on')"))
    await open_sheet(pg, 'wxPill')
    await finger(pg, '#wxX')
    await pg.wait_for_timeout(350)
    ok(f'{tag} the X closes the sheet', not await pg.evaluate("()=>document.getElementById('wxOv').classList.contains('on')"))
    # the dice
    await finger(pg, '#wxRnd')
    await pg.wait_for_timeout(250)
    d = await pg.evaluate("()=>{const t=document.getElementById('wxToast'),r=t.getBoundingClientRect();return [localStorage.getItem('kgeuWXR'),t.classList.contains('on'),t.textContent,"
                          "!document.querySelector('#wxPill small').hidden,window.__kgeu.WX(),r.left>=0&&r.right<=innerWidth]}")
    ok(f'{tag} dice: random on, the tag on the pill, a toast with what it rolled', d[0] == '1' and d[1] and d[2] == 'Rolled: ' + d[4]['icon'] + ' ' + d[4]['name'] and d[3] and d[4]['random'] and d[5], d)
    tt = await pg.evaluate(TOAST, '#menu')
    ok(f'{tag} the roll toast covers no control on the Fly tab', not tt, tt)
    r = await pg.evaluate(PILL, ['wxPill', 'wxRnd'])
    ok(f'{tag} Fly tab pill on Random fits', not r['err'] and r['tag'], r)
    await shot(pg, tag, 'fly_random')
    # random rolls: Arizona never rolls fog by day; Tokyo odds never hold the haboob
    rolls = await pg.evaluate(f"()=>{{const o={K}.wxOdds('rjtt','day'),a={K}.wxOdds('az','night');return [Object.keys(o),Object.keys(a)]}}")
    ok(f'{tag} odds: no haboob in Tokyo or an Arizona night', 'haboob' not in rolls[0] and 'haboob' not in rolls[1], rolls)
    # the pause sheet
    await pg.evaluate(f"()=>{{{K}.setWX('storm');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway');}}")
    await pg.wait_for_timeout(600)
    await pg.evaluate(f"()=>{K}.togglePause()")
    await pg.wait_for_timeout(500)
    for wid in ('storm', 'gusty'):
        await pg.evaluate(f"()=>{K}.setWX({wid!r})")
        r = await pg.evaluate(PILL, ['wxPillP', 'wxRndP'])
        ok(f'{tag} pause pill: {NAMES[wid]} fits (short name, or the icon alone up to 700 wide), nothing overlaps, the airports keep 90 px', not r['err'] and r['loc'] >= 90, r)
        await shot(pg, tag, 'pause_' + wid)
    au = await pg.evaluate("""()=>{const ov=document.getElementById('pauseOv'),W=innerWidth,H=innerHeight,bad=[];
      const inScroll=e=>{for(let n=e.parentElement;n&&n!==ov;n=n.parentElement){const s=getComputedStyle(n);if(/(auto|scroll)/.test(s.overflowX+s.overflowY))return true;}return false;};
      ov.querySelectorAll('button').forEach(b=>{const r=b.getBoundingClientRect();if(r.width&&r.height&&!inScroll(b)&&(r.right>W+1||r.bottom>H+1))bad.push('off '+b.id+' '+b.textContent.slice(0,12));});return bad;}""")
    ok(f'{tag} pause sheet: every button on screen', not au, au)
    if W > 700:
        await finger(pg, '#wxRndP')
        await pg.wait_for_timeout(250)
        tt = await pg.evaluate(TOAST, '#pauseOv')
        ok(f'{tag} the roll toast in the pause sheet covers no control', not tt, tt)
        await shot(pg, tag, 'pause_toast')
        await pg.wait_for_timeout(2100)
    else:   # no dice in the pause row up to 700 wide: the sheet's Random tile, its roll shown in the sheet's title
        await open_sheet(pg, 'wxPillP')
        await finger(pg, '#wxOv .wxT[data-wx="random"]')
        await pg.wait_for_timeout(200)
        rt = await pg.evaluate(f"()=>[document.getElementById('wxT').textContent,{K}.WX(),[...document.querySelectorAll('#wxOv .wxT.sel')].map(t=>t.dataset.wx),document.getElementById('wxToast').classList.contains('on')]")
        ok(f'{tag} pause: the Random tile shows its roll in the sheet title, rings it, no toast', rt[0] == 'Rolled: ' + rt[1]['icon'] + ' ' + rt[1]['name'] and rt[1]['random'] and sorted(rt[2]) == sorted([rt[1]['id'], 'random']) and not rt[3], rt)
        await shot(pg, tag, 'pause_rolled')
        await pg.wait_for_timeout(1100)
        ok(f'{tag} pause: the sheet closes after the roll', not await pg.evaluate("()=>document.getElementById('wxOv').classList.contains('on')"))
    await open_sheet(pg, 'wxPillP')
    s = await pg.evaluate(SHEET)
    top = await pg.evaluate("()=>{const t=document.querySelector('#wxOv .wxT[data-wx=haboob]'),r=t.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('.wxT')===t}")
    ok(f'{tag} sheet over the pause sheet, on top, nothing cut', not s['err'] and not s['scroll'] and top, s)
    await shot(pg, tag, 'pause_sheet')
    await finger(pg, '#wxOv .wxT[data-wx="haboob"]')
    await pg.wait_for_timeout(350)
    h = await pg.evaluate(f"()=>{{const s={K}.state();return [{K}.haboob().on,{K}.TOD().id,{K}.paused()]}}")
    ok(f'{tag} Haboob from the pause sheet: the wall comes, time still day, still paused', h[0] and h[1] == 'day' and h[2], h)
    await finger(pg, '#wxPillP'); await pg.wait_for_timeout(300)
    await finger(pg, '#wxOv .wxT[data-wx="clear"]'); await pg.wait_for_timeout(350)
    h = await pg.evaluate(f"()=>[{K}.haboob().on,{K}.paused()]")
    ok(f'{tag} Clear from the pause sheet: the wall goes', not h[0] and h[1], h)
    ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()
    # the migration: an old install's Haboob time
    pg = await page(b, url, vp=vp, storage=dict(BASE, kgeuTOD='haboob'))
    await pg.evaluate(f"()=>{K}.openFly()")
    await pg.wait_for_timeout(400)
    m = await pg.evaluate(f"()=>[{K}.prefs(),localStorage.getItem('kgeuTOD'),localStorage.getItem('kgeuWX'),document.querySelector('#wxPill .lg').textContent,"
                          "document.querySelector('#sFly .pick[data-tod=day]').classList.contains('sel'),!!document.querySelector('.pick[data-tod=haboob]')]")
    ok(f'{tag} migration: kgeuTOD haboob -> Day + Haboob, both saved, pill Haboob, Day lit, no Haboob time chip',
       m[0]['tod'] == 'day' and m[0]['wx'] == 'haboob' and m[1] == 'day' and m[2] == 'haboob' and m[3] == 'Haboob' and m[4] and not m[5], m)
    await shot(pg, tag, 'migrated')
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway');}}")
    await pg.wait_for_timeout(500)
    h = await pg.evaluate(f"()=>[{K}.haboob().on,{K}.TOD().hb===true]")
    ok(f'{tag} migrated haboob flies: the wall on, the dusty day light', h[0] and h[1], h)
    ok(f'{tag} migration: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()


async def regions(b, url):
    tag = 'regions'
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=BASE)
    await pg.evaluate(f"()=>{{{K}.openMenu('sArc');}}")
    await pg.wait_for_timeout(500)
    d = await pg.evaluate(f"()=>{{const s={K}.dailySpec(),W={K}.WX_SET[s.wx],c=document.querySelector('#arcCards .mcard[data-m=daily] .d');"
                          "return [s.wx,s.kind,W&&W.icon,W&&W.name,c?c.textContent:null]}")
    ok(f'{tag} daily card: the weather fact (icon and name), never the haboob or fog', d[4] is not None and (d[1] == 'dogfight' or (d[2] + '\u00a0' + d[3]) in d[4]) and d[0] not in ('haboob', 'fog'), d)
    await pg.evaluate(f"()=>{{{K}.setWX('storm');}}")
    await pg.evaluate(f"()=>{K}.startLesson('pattern',true)")
    await pg.wait_for_timeout(500)
    a = await pg.evaluate(f"()=>[{K}.WX().id,localStorage.getItem('kgeuWX'),{K}.wxOf('les:pattern')]")
    ok(f'{tag} lesson: its fixed weather (clear), the player\'s choice kept in storage', a[0] == 'clear' and a[1] == 'storm' and a[2] == 'clear', a)
    await pg.evaluate(f"()=>{K}.openMenu('sFly')")
    await pg.wait_for_timeout(400)
    a = await pg.evaluate(f"()=>[{K}.WX().id,document.querySelector('#wxPill .lg').textContent]")
    ok(f'{tag} lesson: the player\'s weather back at the menu, the pill shows it', a == ['storm', 'Thunderstorm'], a)
    await pg.evaluate(f"()=>{K}.startLesson('xwind',true)")
    await pg.wait_for_timeout(500)
    a = await pg.evaluate(f"()=>{{const s={K}.state();return [{K}.WX().id,s.windKt,s.windHold,s.wxW,s.gustAmp]}}")
    ok(f'{tag} crosswind lesson: the gusty look, lesWind\'s steady wind (12 kt, held), no weather gusts', a[0] == 'gusty' and a[1] in (8, 12) and a[2] == 1 and not a[3] and a[4] <= 0.15, a)
    await pg.evaluate(f"()=>{K}.mission('drop')")
    await pg.wait_for_timeout(500)
    a = await pg.evaluate(f"()=>[{K}.WX().id,localStorage.getItem('kgeuWX')]")
    ok(f'{tag} airdrop: scattered for the run, storm still saved', a == ['scattered', 'storm'], a)
    await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway');}}")
    await pg.wait_for_timeout(400)
    a = await pg.evaluate(f"()=>{K}.WX().id")
    ok(f'{tag} the next free flight flies the player\'s weather', a == 'storm', a)
    ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()
    # Tokyo's first visit: no kgeuWX_rjtt, an Arizona choice saved
    pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=dict(BASE, kgeuRegion='rjtt', kgeuWX='haboob', kgeuTOD='day'))
    await pg.wait_for_function(f"()=>{K}.boot&&{K}.boot().pre.done", timeout=120000)
    t = await pg.evaluate(f"()=>{{const d=new Date(),k=d.getUTCFullYear()*10000+(d.getUTCMonth()+1)*100+d.getUTCDate();"
                          f"return [{K}.WX().id,{K}.wxFirst('rjtt','day',k),Object.keys({K}.wxOdds('rjtt','day')),localStorage.getItem('kgeuWX_rjtt'),localStorage.getItem('kgeuWX'),"
                          f"document.querySelector('#wxPill .lg').textContent,{K}.WX().name]}}")
    ok(f'{tag} Tokyo first visit: rolled from Tokyo\'s odds (seeded by the day), saved as kgeuWX_rjtt only, the pill shows it',
       t[0] == t[1] and t[0] in t[2] and t[3] == t[0] and t[4] == 'haboob' and t[5] == t[6], t)
    ok(f'{tag} Tokyo: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if '--sheet' in sys.argv:
            w, h = sys.argv[sys.argv.index('--sheet') + 1].split('x')
            await sheet_only(b, url, int(w), int(h))
        else:
            sizes = [(844, 390), (568, 320)]
            if '--size' in sys.argv:
                w, h = sys.argv[sys.argv.index('--size') + 1].split('x')
                sizes = [(int(w), int(h))]
            for W, H in sizes:
                await full(b, url, W, H)
            if '--size' not in sys.argv or '--regions' in sys.argv:
                await regions(b, url)
        await b.close()
    srv.shutdown()
    return ok.done('weather_ui_check')

sys.exit(asyncio.run(main()))
