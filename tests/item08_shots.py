# One-off screenshot script for phone notes 0929, item 8 (the single voice priority
# queue: vq*, coachSpeak, radioSpeak share one queue across the instructor, tower
# readbacks, drop zone / range calls and traffic chatter). Shows a flight school
# lesson with the instructor's text on screen while a tower call is queued behind it,
# to confirm the tower subtitle does not cover the lesson panel.
# Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item08_shots.py
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, THREE, IGNORE, splash_gone

SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'overnight-screenshots', 'phone0929', 'item08')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'
VP = {'width': 844, 'height': 390}

# speechSynthesis stub so the instructor line has a known, controllable duration
# (60 ms/char), same technique as tests/voice_queue_check.py
FAKE_SPEECH = """(()=>{const S={speaking:false,cur:null,tm:0,
  speak(u){this.cancel();this.cur=u;this.speaking=true;const r={text:u.text,t0:performance.now()/1000};window.__spk.push(r);
    this.tm=setTimeout(()=>{if(this.cur!==u)return;this.cur=null;this.speaking=false;r.t1=performance.now()/1000;u.onend&&u.onend({});},u.text.length*60+300);},
  cancel(){const u=this.cur;if(!u)return;clearTimeout(this.tm);this.cur=null;this.speaking=false;const r=window.__spk[window.__spk.length-1];r.t1=performance.now()/1000;r.cut=true;u.onerror&&u.onerror({error:'interrupted'});},
  getVoices(){return [];},addEventListener(){},removeEventListener(){},pause(){},resume(){}};
  window.__spk=[];Object.defineProperty(window,'speechSynthesis',{value:S,configurable:true});})()"""
DRIVE = """()=>{const K=window.__kgeu;let last=performance.now();clearInterval(window.__iv);
  window.__iv=setInterval(()=>{const n=performance.now(),d=Math.min(0.1,(n-last)/1000);last=n;K.stepFrame(d,false,true);},50);}"""
STOP = "()=>{clearInterval(window.__iv);window.__kgeu.stepFrame(0,true);}"

async def shot(pg, name, note=''):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f'wrote {path}' + (f'  {note}' if note else ''))

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        ctx = await b.new_context(viewport=VP, has_touch=True, is_mobile=True, device_scale_factor=2)
        await ctx.add_init_script("(()=>{if(sessionStorage.getItem('__seeded'))return;sessionStorage.setItem('__seeded','1');localStorage.clear();"
            "localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');})()")
        await ctx.add_init_script(FAKE_SPEECH)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
        await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        await pg.goto(url); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await splash_gone(pg)
        await pg.evaluate(f"()=>{K}.initAudio()")

        # flight school pattern lesson: a long instructor line, then queue a tower
        # clearance behind it while the instructor is still talking
        await pg.evaluate(f"()=>{{const K={K};K.stepFrame(0,false,true);K.startLesson('pattern',true);}}")
        await pg.evaluate(f"()=>{{const K={K};K.coach2('Pattern work. Take off, climb to 700 above the ground, then fly the circuit at 2,100 feet and bring it back to runway 1.');"
                           "K.vqAdd('Glendale Tower 121.0','tower','Skyhawk 31G, runway 1, cleared for takeoff.',['t_cleared_to'],{pri:2});}")
        await pg.evaluate(DRIVE)
        await pg.wait_for_timeout(1200)
        state = await pg.evaluate(f"()=>{{const a=document.getElementById('atc'),l=document.getElementById('lesson');const A=a.getBoundingClientRect(),B=l.getBoundingClientRect();"
                                   "return {who:a.querySelector('b')&&a.querySelector('b').textContent,atcOn:a.classList.contains('on'),lesT:document.getElementById('lesT').textContent,"
                                   "lesI:document.getElementById('lesI').textContent,q:window.__kgeu.radioQ().map(x=>x.who+': '+x.text),"
                                   "hit:!(A.right<B.left||B.right<A.left||A.bottom<B.top||B.bottom<A.top)};}")
        print('state:', state)
        await shot(pg, 'item08_lesson_with_queued_tower_call.png', state)
        await pg.evaluate(STOP)
        print('errs:', errs[:5])
        await b.close()
    srv.shutdown()

asyncio.run(main())
