import os
# Verify the deployed site over https, as an iPhone-sized client would see it.
import asyncio,sys
from playwright.async_api import async_playwright
URL='https://rabahharchaoui-design.github.io/kgeu-flight/'
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    ctx=await b.new_context(viewport={'width':844,'height':390},has_touch=True,is_mobile=True,
        device_scale_factor=3,
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1')
    pg=await ctx.new_page(); errs=[]; reqfail=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('requestfailed',lambda r:reqfail.append(r.url+' '+str(r.failure)))
    await pg.goto(URL,wait_until='load'); await pg.wait_for_timeout(5000)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    chk('page loads over https',(await pg.title()).startswith('Pocket Flight Sim'),await pg.title())
    chk('no page errors',not errs,str(errs[:2]))
    chk('no failed requests',not reqfail,str(reqfail[:3]))
    # three.js came from the CDN and the scene is alive
    chk('three.js loaded from cdnjs',await pg.evaluate("()=>typeof THREE!=='undefined' && THREE.REVISION==='128'"),
        await pg.evaluate("()=>typeof THREE!=='undefined'?THREE.REVISION:'missing'"))
    chk('game booted',await pg.evaluate("()=>!!window.__kgeu"))
    # manifest is linked, fetchable and has the right fields
    m=await pg.evaluate("""async()=>{const l=document.querySelector('link[rel=manifest]');
      if(!l)return null;const r=await fetch(l.href);return await r.json();}""")
    chk('manifest is linked and fetchable',m is not None)
    if m:
        chk('manifest name is Pocket Flight Sim',m.get('name')=='Pocket Flight Sim' and m.get('short_name')=='Pocket Sim',str(m.get('name')))
        chk('display is fullscreen',m.get('display')=='fullscreen',str(m.get('display')))
        chk('orientation is landscape',m.get('orientation')=='landscape',str(m.get('orientation')))
        sizes=[i.get('sizes') for i in m.get('icons',[])]
        chk('manifest ships a 512 px icon','512x512' in sizes,str(sizes))
        # icons resolve relative to the project path, not the domain root
        ok=await pg.evaluate("""async(icons)=>{for(const i of icons){
            const r=await fetch(new URL(i.src,document.querySelector('link[rel=manifest]').href));
            if(!r.ok)return i.src+' -> '+r.status;}return 'ok';}""",m.get('icons',[]))
        chk('manifest icon paths resolve',ok=='ok',str(ok))
    # apple bits
    tags=await pg.evaluate("""()=>({cap:(document.querySelector('meta[name=apple-mobile-web-app-capable]')||{}).content,
      bar:(document.querySelector('meta[name=apple-mobile-web-app-status-bar-style]')||{}).content,
      title:(document.querySelector('meta[name=apple-mobile-web-app-title]')||{}).content,
      icon:(document.querySelector('link[rel=apple-touch-icon]')||{}).href,
      vp:(document.querySelector('meta[name=viewport]')||{}).content})""")
    chk('apple-mobile-web-app-capable is yes',tags['cap']=='yes',str(tags['cap']))
    chk('status bar is black-translucent',tags['bar']=='black-translucent',str(tags['bar']))
    chk('home screen title set',tags['title']=='Pocket Sim',str(tags['title']))
    chk('viewport-fit=cover for the notch','viewport-fit=cover' in (tags['vp'] or ''),str(tags['vp']))
    r=await pg.evaluate("async(u)=>{const r=await fetch(u);return r.status;}",tags['icon'])
    chk('apple-touch-icon resolves',r==200,str(r))
    # share card and install tip: these went missing once already because
    # nothing here checked for them
    og=await pg.evaluate("""()=>({img:(document.querySelector('meta[property="og:image"]')||{}).content,
      title:(document.querySelector('meta[property="og:title"]')||{}).content,
      card:(document.querySelector('meta[name="twitter:card"]')||{}).content})""")
    chk('og:image is present',bool(og['img']),str(og['img']))
    chk('og:title is present',og['title']=='Pocket Flight Sim',str(og['title']))
    chk('twitter card is the large image kind',og['card']=='summary_large_image',str(og['card']))
    if og['img']:
        r=await pg.evaluate("async(u)=>{const r=await fetch(u);return r.status;}",og['img'])
        chk('share card image resolves',r==200,str(r))
    chk('Add to Home Screen tip is in the page',
        await pg.evaluate("()=>!!document.getElementById('a2hs')"))
    chk('HD airframes are in the build',
        await pg.evaluate("()=>/makeHD/.test(document.documentElement.innerHTML)"))

    # offline mode (phone3 item 8): exactly one service worker, this build's (sw.js?v=APP_VER), so it holds no old copy
    sw=await pg.evaluate("""async()=>{if(!navigator.serviceWorker)return null;await navigator.serviceWorker.ready;const rs=await navigator.serviceWorker.getRegistrations();
      const v=document.documentElement.innerHTML.match(/APP_VER='([^']+)'/)[1];return {n:rs.length,url:rs.map(r=>(r.active||r.waiting||r.installing).scriptURL),v:v};}""")
    chk('one service worker, this build\'s',bool(sw) and sw['n']==1 and sw['url'][0].endswith('sw.js?v='+sw['v']),str(sw))
    # a fresh device: the leaderboard Worker answers and the callsign card is up after the splash
    await pg.wait_for_timeout(3000)
    cs=await pg.evaluate("()=>({on:document.getElementById('csOv').classList.contains('on'),lb:!!(window.__kgeu.LB&&window.__kgeu.LB.E.enabled),online:window.__kgeu.LB&&window.__kgeu.LB.E.online})")
    chk('leaderboards on, the Worker answers, the callsign card is up',cs=={'on':True,'lb':True,'online':True},str(cs))
    await pg.evaluate("()=>document.getElementById('csOv').classList.remove('on')")   # tests/live_scores_check.py signs up for real
    # actually play it
    # home -> FLY -> GO: two taps, by finger
    if await pg.is_visible('#funnel'): await pg.tap('#fPilot'); await pg.wait_for_timeout(300)
    await pg.evaluate("()=>{__kgeu.pick('reaper');__kgeu.pickPos('runway');}")
    await pg.tap('#hFly'); await pg.wait_for_timeout(800)
    await pg.tap('#bGo'); await pg.wait_for_timeout(1800)
    st=await pg.evaluate("()=>{const s=__kgeu.state();return {running:!!s,type:s.type,ias:Math.round(s.ias*1.944)};}")
    chk('a flight starts from the runway',st['type']=='reaper',str(st))
    await pg.tap('#bAuto'); await pg.wait_for_timeout(6000)
    ap=await pg.evaluate("()=>{const s=__kgeu.state();return {ap:s.ap?s.ap.mode:null,ias:Math.round(s.ias*1.944),alt:Math.round(s.pos.y*3.28084+1071)};}")
    chk('auto takeoff runs on the live site',ap['ap'] in ('to','hold'),str(ap))
    await pg.screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'live_iphone.png'))
    chk('no errors after play',not errs,str(errs[:2]))
    # ---- overnight build ----
    print('-- overnight build --')
    # the checks above leave a flight running, so bring the menu back up first
    await pg.evaluate("()=>window.__kgeu.openMenu()")
    await pg.wait_for_timeout(600)
    for t in ['cessna','alpha','f16','reaper','mq9b','c130']:
        ok = await pg.query_selector(f'#carMain .pick[data-t="{t}"]') is not None
        chk(f'{t} is offered in the carousel', ok)
    await pg.evaluate("()=>window.__kgeu.nav('sFly')")
    chk('spawn picker is there', await pg.is_visible('.pick[data-b="luke"]'))
    chk('time of day picker is there', await pg.is_visible('.pick[data-tod="night"]'))
    await pg.evaluate("()=>window.__kgeu.nav('sSet')")
    chk('radio controls are there', await pg.is_visible('#oRadio') and await pg.is_visible('#oRvol'))
    await pg.evaluate("()=>window.__kgeu.nav('sHome',true)")
    chk('records screen is reachable', await pg.is_visible('#hRec'))
    await pg.evaluate("()=>window.__kgeu.nav('sArc')")
    chk('C-130 short field is offered', await pg.is_visible('#arcCards [data-m="short"]'))
    await pg.evaluate("()=>window.__kgeu.nav('sArc')")
    chk('arcade hub has the landing challenge', await pg.is_visible('#arcCards [data-m="landing"]'))
    chk('creator credit links to the channel', await pg.evaluate("()=>document.querySelector('#sSet .credit').href")=='https://www.youtube.com/@OhRabah')
    chk('no tilt anywhere', await pg.evaluate("()=>!/tilt/i.test(document.body.innerText)&&!document.querySelector('[data-a=tilt]')"))
    n0=len(errs)
    for t in ['cessna','f16','reaper','mq9b','c130']:
        await pg.evaluate(f"()=>{{window.__kgeu.pick('{t}');window.__kgeu.start('runway');}}")
        await pg.wait_for_timeout(2000)
        s2=await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.type,s.crashed,s.base];}")
        chk(f'{t} spawns on the live site', s2[0]==t and not s2[1], str(s2))
        await pg.evaluate("()=>window.__kgeu.openMenu()")
        await pg.wait_for_timeout(300)
    chk('no console errors while spawning', len(errs)==n0, str(errs[n0:n0+2]))
    # the Red Flag Dogfight starts on the live site: card, briefing, FIGHT'S ON, a bandit, the dogfight song
    n1=len(errs)
    await pg.evaluate("()=>window.__kgeu.nav('sArc')")
    chk('arcade hub has the dogfight, not coming soon', await pg.is_visible('#arcCards [data-m="dogfight"]') and 'oming soon' not in await pg.inner_text('#arcCards [data-m="dogfight"]'))
    await pg.evaluate("()=>document.querySelector('#arcCards [data-m=\"dogfight\"]').click()")
    for _ in range(40):
        if await pg.is_visible('#dfbGo'): break
        await pg.wait_for_timeout(500)
    chk('dogfight briefing says Sound on', 'Sound on for the full experience' in await pg.evaluate("()=>document.body.innerText"))
    await pg.evaluate("()=>document.getElementById('dfbGo').click()")
    await pg.wait_for_timeout(4000)
    d=await pg.evaluate("()=>{const K=window.__kgeu,D=K.DF;return [!!D.on,D.wave,D.bandits.filter(b=>b.alive).length,K.MUSIC?K.MUSIC.forced:null,K.state().type];}")
    chk('dogfight runs on the live site', d[0] and d[2]>=1 and d[4]=='f16', str(d))
    chk('no console errors in the dogfight', len(errs)==n1, str(errs[n1:n1+2]))
    await pg.evaluate("()=>window.__kgeu.openMenu()")
    await pg.wait_for_timeout(300)
    # the radio clips must actually come down from the live host
    await pg.evaluate("()=>window.__kgeu.initAudio()")
    for _ in range(50):
        r=await pg.evaluate("()=>{const R=window.__kgeu.RADIO;return [R.want,R.got,R.err];}")
        if r[0] and r[1]+max(0,r[2])>=r[0]: break
        await pg.wait_for_timeout(500)
    chk('radio clips fetch and decode from the live host', r[0]>100 and r[1]>=r[0]-2, f'want {r[0]} got {r[1]} err {r[2]}')
    await pg.screenshot(path='overnight-screenshots/live_after_merge.png')

    await b.close()
asyncio.run(main())
print('\nlive check: '+('FAILED '+', '.join(fails) if fails else 'deployed site is good'))
sys.exit(1 if fails else 0)

# ---- overnight build: the new aircraft, fields and radio, on the live site ----
