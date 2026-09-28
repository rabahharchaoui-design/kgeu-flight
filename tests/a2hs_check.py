import asyncio,os,sys
from playwright.async_api import async_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL='file://'+os.path.join(ROOT,'index.html')
THREE=open(os.path.join(ROOT,'node_modules/three/build/three.min.js')).read()
IOS='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
CHROME_IOS='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/126.0 Mobile/15E148 Safari/604.1'
MAC='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)
async def load(b,ua,standalone=False):
    ctx=await b.new_context(viewport={'width':844,'height':390},has_touch=True,is_mobile=True,user_agent=ua)
    pg=await ctx.new_page()
    if standalone:
        await pg.add_init_script("Object.defineProperty(navigator,'standalone',{get:()=>true});")
    await pg.route('**/three.min.js',lambda r:r.fulfill(body=THREE,content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2500)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    # the tip lives in Settings, and on the first launch screen
    await pg.evaluate("()=>{document.getElementById('funnel').classList.remove('on');window.__kgeu.nav('sSet',true)}")
    return pg
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    pg=await load(b,IOS)
    chk('tip shows on iPhone Safari, in Settings',await pg.is_visible('#a2hs'))
    chk('and on the first launch screen',await pg.evaluate("()=>getComputedStyle(document.getElementById('a2hsF')).display==='block'"))
    t=await pg.inner_text('#a2hs')
    chk('tip names Share and Add to Home Screen','Share' in t and 'Add to Home Screen' in t,repr(t[:70]))
    await pg.close()
    pg=await load(b,IOS,standalone=True)
    chk('tip hidden once installed',not await pg.is_visible('#a2hs'))
    await pg.close()
    pg=await load(b,CHROME_IOS)
    vis=await pg.is_visible('#a2hs'); t=await pg.inner_text('#a2hs') if vis else ''
    chk('in-app browser is told to open Safari first',vis and 'Safari' in t,repr(t[:60]))
    await pg.close()
    pg=await load(b,MAC)
    chk('tip hidden on desktop',not await pg.is_visible('#a2hs'))
    await pg.close()
    await b.close()
asyncio.run(main())
print('\na2hs: '+('FAILED '+', '.join(fails) if fails else 'all checks passed'))
sys.exit(1 if fails else 0)
