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
    chk('page loads over https',(await pg.title()).startswith('KGEU'),await pg.title())
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
        chk('manifest name is KGEU Flight',m.get('name')=='KGEU Flight',str(m.get('name')))
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
    chk('home screen title set',tags['title']=='KGEU Flight',str(tags['title']))
    chk('viewport-fit=cover for the notch','viewport-fit=cover' in (tags['vp'] or ''),str(tags['vp']))
    r=await pg.evaluate("async(u)=>{const r=await fetch(u);return r.status;}",tags['icon'])
    chk('apple-touch-icon resolves',r==200,str(r))
    # share card and install tip: these went missing once already because
    # nothing here checked for them
    og=await pg.evaluate("""()=>({img:(document.querySelector('meta[property="og:image"]')||{}).content,
      title:(document.querySelector('meta[property="og:title"]')||{}).content,
      card:(document.querySelector('meta[name="twitter:card"]')||{}).content})""")
    chk('og:image is present',bool(og['img']),str(og['img']))
    chk('og:title is present',og['title']=='KGEU Flight',str(og['title']))
    chk('twitter card is the large image kind',og['card']=='summary_large_image',str(og['card']))
    if og['img']:
        r=await pg.evaluate("async(u)=>{const r=await fetch(u);return r.status;}",og['img'])
        chk('share card image resolves',r==200,str(r))
    chk('Add to Home Screen tip is in the page',
        await pg.evaluate("()=>!!document.getElementById('a2hs')"))
    chk('HD airframes are in the build',
        await pg.evaluate("()=>/makeHD/.test(document.documentElement.innerHTML)"))

    # no service worker registered, so updates are instant
    sw=await pg.evaluate("async()=>{if(!navigator.serviceWorker)return 0;const rs=await navigator.serviceWorker.getRegistrations();return rs.length;}")
    chk('no service worker registered',sw==0,str(sw)+' registrations')
    # actually play it
    await pg.tap('#bRunway'); await pg.wait_for_timeout(1800)
    st=await pg.evaluate("()=>{const s=__kgeu.state();return {running:!!s,type:s.type,ias:Math.round(s.ias*1.944)};}")
    chk('a flight starts from the runway',st['type']=='reaper',str(st))
    await pg.tap('#bAuto'); await pg.wait_for_timeout(6000)
    ap=await pg.evaluate("()=>{const s=__kgeu.state();return {ap:s.ap?s.ap.mode:null,ias:Math.round(s.ias*1.944),alt:Math.round(s.pos.y*3.28084+1071)};}")
    chk('auto takeoff runs on the live site',ap['ap'] in ('to','hold'),str(ap))
    await pg.screenshot(path='/Users/rabahharchaoui/Desktop/cc-test/kgeu/tests/live_iphone.png')
    chk('no errors after play',not errs,str(errs[:2]))
    # ---- overnight build ----
    print('-- overnight build --')
    # the checks above leave a flight running, so bring the menu back up first
    await pg.evaluate("()=>window.__kgeu.openMenu()")
    await pg.wait_for_timeout(600)
    for t in ['cessna','alpha','f16','reaper','mq9b','c130']:
        ok = await pg.is_visible(f'.pick[data-t="{t}"]')
        chk(f'{t} is offered in the menu', ok)
    chk('spawn picker is there', await pg.is_visible('.pick[data-b="luke"]'))
    chk('time of day picker is there', await pg.is_visible('.pick[data-tod="night"]'))
    chk('radio controls are there', await pg.is_visible('#oRadio') and await pg.is_visible('#oRvol'))
    chk('records screen is reachable', await pg.is_visible('#bRecords'))
    chk('C-130 missions are offered', await pg.is_visible('#bDrop') and await pg.is_visible('#bShort'))
    n0=len(errs)
    for t in ['cessna','f16','reaper','mq9b','c130']:
        await pg.evaluate(f"()=>{{window.__kgeu.pick('{t}');window.__kgeu.start('runway');}}")
        await pg.wait_for_timeout(2000)
        s2=await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.type,s.crashed,s.base];}")
        chk(f'{t} spawns on the live site', s2[0]==t and not s2[1], str(s2))
        await pg.evaluate("()=>window.__kgeu.openMenu()")
        await pg.wait_for_timeout(300)
    chk('no console errors while spawning', len(errs)==n0, str(errs[n0:n0+2]))
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
