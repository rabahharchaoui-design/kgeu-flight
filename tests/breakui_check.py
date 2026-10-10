# Phone3 item 10: break the UI (the break-ui method). Worst-case data goes in through the same doors the
# real data does: the results card's options (resOpen/resBoard), the leaderboard Worker's /board answer
# (stubbed), the callsign profile, the music title. The fixture: 12 character callsigns of the widest
# letters (the server allows A-Z0-9, 3 to 12), a 1 character-wide-ish short one, huge scores, the longest
# run names (Rio Santos Dumont, Pattern and touch and go), every aircraft, a creator badge, top ranks,
# five-digit ranks, a dogfight answer with personal bests, achievements and a rank up, and a long song
# title. Sizes: 844x390, 667x375, 568x320 landscape and 390x844, 375x667 portrait.
# Failure signatures checked on every text element: overflow out of its own box without an ellipsis,
# out of the card or row, under 44 px tap targets, off screen, a card that scrolls or does not fit, a
# score or rank cut (numbers are never truncated), captions that vanish, controls overlapping.
# Screenshots: overnight-screenshots/phone3/item10/. Run: .venv/bin/python tests/breakui_check.py
import asyncio, os, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, ROOT
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'phone3', 'item10')
WK = 'http://lb.test'
ME = 'WWWWWWWWWWWW'
TYPES = ['f16', 'c130', 'reaper', 'mq9b', 'cessna', 'alpha']
NAMES = [ME, 'MMMMMMMMMMMM', 'OHRABAH', 'JOX', 'W0W0W0W0W0W0', 'QQQQQQQQQQQQ', 'ABC', 'MESQUITE7777', 'HABOOBHABOOB', 'ZZZZZZZZZZZZ']
RANKS = ['Top Gun', 'Weapons School', 'Instructor Pilot', 'Flight Lead', 'Wingman', 'Nugget']
VIEWS = [(844, 390), (667, 375), (568, 320), (390, 844), (375, 667)]
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}

def board(b, big):
    rows = [{'r': i * 1111 + 1 if i > 6 else i + 1, 'cs': n, 'score': big - i * 137, 'secs': 3599 - i, 'ac': TYPES[i % 6], 'mode': 'easy' if i % 2 else 'hard',
             'xp': 99999 - i, 'rank': RANKS[min(5, i)], 'creator': n == 'OHRABAH' or i == 4, 'when': 0} for i, n in enumerate(NAMES)]
    me = dict(rows[0]); me['r'] = 12345
    return {'board': b, 'mode': 'all', 'period': 'all', 'dir': 1, 'total': 123456, 'rows': rows, 'me': me, 'ghost': {'score': big, 'ac': 'f16', 'cs': NAMES[1]}, 'now': 0, 'day': 20261006}

BIG = {'daily': 9999999, 'mission:dash': 3599.9, 'arc:drop': 999.9, 'df:score:hard': 9999999, 'lesson:pattern': 100}

async def worker(route):
    req = route.request; path = req.url[len(WK):].split('?')[0]
    if req.method == 'OPTIONS': return await route.fulfill(status=204, headers=CORS)
    q = dict(x.split('=', 1) for x in req.url.split('?', 1)[1].split('&')) if '?' in req.url else {}
    b = q.get('b', 'daily').replace('%3A', ':')
    body = {'/health': {'ok': True}, '/me': {'cs': ME, 'xp': 99999, 'creator': False}, '/pool': {'tokens': []},
            '/fame': {'day': 20261006, 'daily': None, 'top': []}, '/board': board(b, BIG.get(b, 9999999)), '/ghost': {'ghost': None}}.get(path, {})
    await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps(body))

# every text box inside root: does it spill out of itself (without an ellipsis), out of root, or off screen
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
# numbers are never truncated: scores, ranks, totals
NUMS = """(sel)=>[...document.querySelectorAll(sel)].filter(e=>e.offsetParent&&(e.scrollWidth>e.clientWidth+1)).map(e=>e.textContent.trim().slice(0,20))"""
CARD_FIT = """(id)=>{const o=document.getElementById(id),s=o.querySelector('.sheet').getBoundingClientRect(),bad=[];
  if(s.bottom>innerHeight+0.5||s.top<-0.5)bad.push('sheet off screen '+Math.round(s.top)+'..'+Math.round(s.bottom));
  if(o.scrollHeight>o.clientHeight+1)bad.push('card scrolls');
  const btns=[...o.querySelectorAll('.rBtns button')].map(b=>b.getBoundingClientRect());
  for(let i=0;i<btns.length;i++)for(let j=i+1;j<btns.length;j++){const a=btns[i],b=btns[j];if(a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1)bad.push('buttons overlap');}
  const who=o.querySelector('.rWho');if(who){const a=who.querySelector('.acTag'),c=who.querySelector('.rCs');if(a&&a.getBoundingClientRect().width<40)bad.push('aircraft chip squished');
    if(c&&c.textContent&&c.getBoundingClientRect().width<30)bad.push('callsign squeezed out');}
  return bad;}"""

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    try:
        async with async_playwright() as p:
            b = await launch(p)
            for (w, h) in VIEWS:
                tag = f'{w}x{h}'
                pg = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuLBUrl': WK, 'kgeuLB': json.dumps({'cs': ME, 'key': 'a' * 48, 'xp': 99999}), 'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
                await pg.context.route(WK + '/**', worker)
                if h > w: await pg.evaluate("()=>document.body.classList.add('portraitok')")
                await pg.evaluate(f"()=>{{const K={K};if(K.LB&&K.LB.E)K.LB.E.P={{cs:'{ME}',key:'a'.repeat(48),xp:99999}};}}")
                # ---- results cards: every aircraft, the longest names, huge scores, the dogfight answer
                for i, t in enumerate(TYPES):
                    await pg.evaluate(f"()=>{{const K={K};K.pick('{t}');K.start('runway');}}"); await pg.wait_for_timeout(150)
                    o = {'letter': 'A', 'title': 'Rio Santos Dumont landing: new best, 1,500 points', 'score': '9,999,999 pts', 'stars': 3,
                         'stats': [['Time', '59:59  (par 59:59)'], ['Landing', 'A  Butter, on centerline'], ['Touchdown', '1,234 fpm, 155 kt'], ['Aim point', '1,234 m long'], ['Centreline', '12.3 m'], ['Best', '9,999,999 pts, 59:59']],
                         'retry': 'RIO SANTOS DUMONT LANDING', 'tip': 'MQ-9B: start down sooner, that long wing floats, aim at the white blocks', 'board': 'daily'}
                    await pg.evaluate(f"(o)=>{{const K={K},ov=document.getElementById('arcOv');K.resOpen(ov,o);}}", o)
                    await pg.evaluate(f"""()=>{{const K={K};try{{K.resBoardHook&&K.resBoardHook({{b:'daily',rank:12345,total:123456,gain:250,pb:1,
                      df:{{kills:{{pb:1,rank:12345}},clear:{{pb:1,rank:3,top10:1}},guns:{{pb:1,rank:99999}}}},ach:[{{id:'greaser',xp:250}},{{id:'night',xp:100}}],rankUp:'Weapons School'}});}}catch(e){{}}}}""")
                    await pg.wait_for_timeout(350)
                    a = await pg.evaluate(AUDIT, ['#arcOv', '.sheet'])
                    f = await pg.evaluate(CARD_FIT, 'arcOv')
                    n = await pg.evaluate(NUMS, '#arcOv .rScore, #arcOv .lbLine b, #arcOv .rLines .gl b')
                    ok(f'{tag} results card, {t}: nothing cut, spilt or off screen, fits, numbers whole', not a and not f and not n, (a[:4], f, n))
                    if i == 0 or t == 'alpha': await pg.screenshot(path=os.path.join(SHOTS, f'results_{tag}_{t}.png'))
                    await pg.evaluate(f"()=>{K}.resClose(document.getElementById('arcOv'))")
                # the landing card (brief, free flight) and the lesson card
                await pg.evaluate(f"""()=>{{const K={K};K.resOpen(document.getElementById('landOv'),{{letter:'B',title:'Free flight landing, Rio Santos Dumont runway 20L  (14 kt crosswind)',score:'100 pts',sub:'Firm, left of centerline',
                  lines:'<div class="gl"><span>Sink rate</span><b>1,234 fpm<i class="pt bad">12</i></b></div><div class="gl"><span>Off centreline</span><b>12.3 m<i class="pt">55</i></b></div><div class="gl"><span>From the aim point</span><b>1,234 m long<i class="pt bad">0</i></b></div><div class="gl"><span>Airspeed</span><b>155 kt vs 130<i class="pt bad">3</i></b></div><div class="gl"><span>Flight time</span><b>59:59</b></div>',
                  board:'free:landing',retry:'RUNWAY START',tip:'C-130: about 700 fpm down final, power back at 50 ft, small flare, under 150 fpm at touchdown'}},true)}}""")
                await pg.wait_for_timeout(350)
                # school1: the card slides up 28 px over 340 ms; a late headless frame can land the measure mid animation
                await pg.evaluate("()=>Promise.all(document.getElementById('landOv').getAnimations({subtree:true}).map(a=>a.finished.catch(()=>{})))")
                a = await pg.evaluate(AUDIT, ['#landOv', '.sheet']); f = await pg.evaluate(CARD_FIT, 'landOv')
                ok(f'{tag} landing card (brief): nothing cut, fits', not a and not f, (a[:4], f))
                await pg.screenshot(path=os.path.join(SHOTS, f'landing_{tag}.png'))
                await pg.evaluate(f"()=>{K}.resClose(document.getElementById('landOv'))")
                await pg.evaluate(f"""()=>{{const K={K};K.resOpen(document.getElementById('gradeOv'),{{letter:'F',title:'Flight school: Pattern and touch and go: crashed on the go around',score:'',
                  lines:'<div class="no">Climbed to 700 ft AGL before turning crosswind (you turned at 312 ft)</div><div class="ok">Held 2,100 ft on downwind</div><div class="no">Touchdown 1,234 ft past the zone</div>',board:''}})}}""")
                await pg.wait_for_timeout(350)
                a = await pg.evaluate(AUDIT, ['#gradeOv', '.sheet']); f = await pg.evaluate(CARD_FIT, 'gradeOv')
                ok(f'{tag} lesson card: nothing cut, fits', not a and not f, (a[:4], f))
                await pg.evaluate(f"()=>{K}.resClose(document.getElementById('gradeOv'))")
                # ---- leaderboards: every board kind
                for bd in ('daily', 'mission:dash', 'arc:drop', 'df:score:hard'):
                    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen('{bd}')}}")
                    try: await pg.wait_for_function("()=>document.querySelectorAll('#lbRowsIn .lbRow').length>=10", timeout=8000)
                    except Exception: pass
                    await pg.wait_for_timeout(400)
                    rows = await pg.evaluate("""()=>[...document.querySelectorAll('#lbRowsIn .lbRow, #lbMe .lbRow')].map(r=>{const R=r.getBoundingClientRect(),q=s=>r.querySelector(s),box=e=>e?e.getBoundingClientRect():null;
                      const n=q('.n'),c=q('.c span'),s=q('.s'),a=q('.a'),m=q('.modeTag'),cr=q('.creator');
                      const bad=[];const B=[['n',n],['s',s],['a',a],['mode',m],['creator',cr]];
                      for(const [k,e] of B){if(!e)continue;const b=e.getBoundingClientRect();if(b.right>R.right+1||b.left<R.left-1)bad.push(k+' outside row');if(e.scrollWidth>e.clientWidth+1&&k!=='a')bad.push(k+' cut');}
                      if(c){const cb=c.getBoundingClientRect();if(cb.width<36&&c.scrollWidth>c.clientWidth+1)bad.push('callsign squeezed to '+Math.round(cb.width));if(c.scrollWidth>c.clientWidth+1&&getComputedStyle(c).textOverflow!=='ellipsis')bad.push('callsign cut');
                        if(c.scrollWidth>c.clientWidth+1&&!r.dataset.full)bad.push('callsign truncated with no way to read it');}
                      if(a&&a.querySelector('b')&&a.querySelector('b').getBoundingClientRect().width<20)bad.push('aircraft name squeezed');
                      if(r.scrollWidth>r.clientWidth+1)bad.push('row spills');if(R.height>58)bad.push('row wraps '+Math.round(R.height));
                      return {t:r.innerText.replace(/\\s+/g,' ').slice(0,60),bad:bad};}).filter(x=>x.bad.length)""")
                    hdr = await pg.evaluate(AUDIT, ['#sLb', None])
                    hdr = [x for x in hdr if 'lbRow' not in x and '.c ' not in x and not x.startswith('cut .creator')]
                    ok(f'{tag} board {bd}: every row fits, numbers whole, aircraft readable', not rows, rows[:3])
                    ok(f'{tag} board {bd}: header, tabs and totals fit', not hdr, hdr[:4])
                    if bd == 'daily': await pg.screenshot(path=os.path.join(SHOTS, f'board_{tag}.png'))
                # ---- the pause sheet: a long song title, every aircraft chip, all region chips
                await pg.evaluate(f"()=>{{const K={K};K.menuClose&&K.menuClose();K.pick('mq9b');K.start('runway');}}"); await pg.wait_for_timeout(300)
                await pg.evaluate(f"()=>{{const K={K};K.tickerForce&&K.tickerForce('Teenage Bottlerocket \\u2014 Skate or Die (Live at the Whisky a Go Go, 2008)');if(!K.paused())K.togglePause();}}"); await pg.wait_for_timeout(500)
                a = await pg.evaluate(AUDIT, ['#pauseOv', None])
                a = [x for x in a if not x.startswith('cut #pMusTitle')]   # the song title scrolls as a marquee by design
                cap = await pg.evaluate("()=>[...document.querySelectorAll('#pauseOv .qs')].filter(b=>b.offsetParent).map(b=>{const i=b.querySelector('i');const vis=i&&[...i.querySelectorAll('*')].concat([i]).some(e=>e.getBoundingClientRect().width>4&&getComputedStyle(e).display!=='none'&&e.textContent.trim());return vis?null:b.id}).filter(Boolean)")
                ok(f'{tag} pause sheet: nothing cut, spilt or off screen, 44 px targets', not a, a[:5])
                ok(f'{tag} pause sheet: every quick tile keeps its caption', not cap, cap)
                await pg.screenshot(path=os.path.join(SHOTS, f'pause_{tag}.png'))
                ok(f'{tag}: no page errors', not pg.errs, pg.errs[:3])
                await pg.context.close()
            await b.close()
    finally:
        srv.shutdown()
    return ok.done('breakui_check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
