# Phone2 item 10: haptics. One module (hapPattern, hapTick) over navigator.vibrate where it exists and,
# on iOS Safari, a hidden <input type="checkbox" switch> whose label is clicked. Every event in the
# spec fires its pattern: flaps, gear, throttle detents, trim, autopilot, touchdown by how hard,
# crash, Hellfire launch and impact, afterburner, stall, green light and pallet release, an A
# landing, a personal best, menu button presses. The rate is capped (never per frame, cooldowns,
# a 40 ms floor, 24 clicks in flight). A Haptics tile in Settings and on the pause sheet, on by
# default, saved. Run: .venv/bin/python tests/haptics_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
# a) record navigator.vibrate calls; b) no vibrate but the iOS switch (Chromium has neither the switch
# attribute nor haptics, so the switch is stood in for and the label clicks are counted)
VIB = "window.__vib=[];Object.defineProperty(Navigator.prototype,'vibrate',{configurable:true,value:function(a){window.__vib.push(Array.isArray(a)?a.slice():a);return true;}});"
SWITCH = """Object.defineProperty(Navigator.prototype,'vibrate',{configurable:true,value:undefined});
  Object.defineProperty(HTMLInputElement.prototype,'switch',{configurable:true,get(){return this.hasAttribute('switch');},set(v){}});
  window.__clicks=[];const oc=HTMLLabelElement.prototype.click;HTMLLabelElement.prototype.click=function(){window.__clicks.push(performance.now());return oc.call(this);};"""
S = "()=>{const s=window.__kgeu.state();return {g:s.onGround,v:Math.hypot(s.vel.x,s.vel.z),crash:s.crashed}}"

async def log(pg, clear=True): return [e['n'] for e in await pg.evaluate(f"(c)=>{K}.hapLog(c)", clear)]

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        # ---- vibrate path: every hook fires its pattern
        ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
        await ctx.add_init_script(VIB)
        pg = await ctx.new_page(); pg.errs = []
        pg.on('pageerror', lambda e: pg.errs.append(str(e)))
        from harness import THREE, splash_gone
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await ctx.add_init_script("(()=>{if(sessionStorage.getItem('__seeded'))return;sessionStorage.setItem('__seeded','1');localStorage.clear();localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');})()")
        await pg.goto(url); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await splash_gone(pg); await pg.wait_for_timeout(300)
        h = await pg.evaluate(f"()=>({{sup:{K}.HAP.sup,on:{K}.HAP.on}})")
        ok('with navigator.vibrate: the module uses it, on by default', h == {'sup': 'vibrate', 'on': True}, h)
        # a menu button press: a very light tick
        await finger(pg, '#hFly'); await pg.wait_for_timeout(200)
        ok('menu button press: a light tick', 'button' in await log(pg))
        n0 = await pg.evaluate("()=>window.__vib.length")
        ok('it reached navigator.vibrate', n0 >= 1, n0)
        # flaps, throttle detent, trim, autopilot on the Cessna; gear and the afterburner on the F-16
        await pg.evaluate(f"()=>{{const K={K};K.nav('sHome',true);K.pick('cessna');K.pickBase('kgeu');K.start('final');}}"); await pg.wait_for_timeout(500)
        await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await log(pg)
        await finger(pg, '#bFlapUp'); await pg.wait_for_timeout(150); await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await pg.wait_for_timeout(200)
        ok('flaps: one tick per detent', 'detent' in await log(pg))
        await finger(pg, '#thr .det[data-p="1"]'); await pg.wait_for_timeout(250)
        ok('throttle FULL detent: a tick', 'detent' in await log(pg))
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        await pg.keyboard.down('y'); await pg.wait_for_timeout(500); await pg.keyboard.up('y'); await pg.wait_for_timeout(150)
        ok('trim: a light tick', 'trim' in await log(pg))
        await pg.evaluate(f"()=>{K}.auto()"); await pg.wait_for_timeout(300)
        ok('autopilot toggle: a tick', 'ap' in await log(pg))
        await pg.evaluate(f"()=>{{const K={K};K.pick('f16');K.pickBase('kgeu');K.start('final');}}"); await pg.wait_for_timeout(500)
        await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await log(pg)
        await finger(pg, '#bGear'); await pg.wait_for_timeout(150); await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)"); await pg.wait_for_timeout(200)
        ok('gear: one tick per change', 'detent' in await log(pg))
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        await pg.evaluate(f"()=>{{const K={K};K.state().ap=null;K.state().apW=null;K.state().throttle=1;}}")
        for _ in range(12): await pg.evaluate(f"()=>{K}.ff(1)"); await pg.wait_for_timeout(120)
        ok('afterburner lights: the rolling rumble', 'ab' in await log(pg))
        # Hellfire launch and impact, the strike range (the bunker under the crosshair, as strike_check does it)
        await pg.evaluate(f"()=>{K}.mission('range')"); await pg.wait_for_timeout(800)
        await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<30;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);}}"); await pg.wait_for_timeout(300)
        idx = await pg.evaluate(f"()=>{K}.STRIKE.targets.findIndex(t=>t.kind==='bunker')")
        await pg.evaluate(f"(i)=>{K}.pointAt(i)", idx); await pg.wait_for_timeout(150)
        await pg.evaluate(f"()=>{K}.trackHere()"); await pg.wait_for_timeout(150); await log(pg)
        await pg.evaluate(f"()=>{K}.fire()"); await pg.wait_for_timeout(200)
        L = await log(pg, False)
        ok('Hellfire launch: the sharp double', 'launch' in L, L)
        for _ in range(40):
            await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<10;i++)K.stepFrame(0.1,false,true);}}")
            if await pg.evaluate(f"()=>{K}.STRIKE.missiles.length===0"): break
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)"); await pg.wait_for_timeout(100)
        ok('Hellfire impact: the heavy thump, after the flight', 'impact' in await log(pg))
        # touchdown (and an A landing), then a crash
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('final');}}"); await pg.wait_for_timeout(400); await log(pg)
        await pg.evaluate(f"()=>{K}.auto()")
        for _ in range(90):
            await pg.evaluate(f"()=>{K}.ff(3)"); await pg.wait_for_timeout(100)
            st = await pg.evaluate(S)
            if st['g'] or st['crash']: break
        await pg.wait_for_timeout(300)
        L = await log(pg)
        ok('touchdown: a tick scaled by how hard', any(x in L for x in ('tdLight', 'tdFirm', 'tdHard')), L)
        ok('an A landing: the celebratory triple (if it was an A)', 'gradeA' in L or await pg.evaluate("()=>document.getElementById('gbL').textContent") != 'A', L)
        await pg.evaluate(f"()=>{K}.crashNow('Test crash')"); await pg.wait_for_timeout(200)
        ok('crash: the long heavy burst', 'crash' in await log(pg))
        # the airdrop: green light and pallet release
        await pg.evaluate(f"()=>{{const K={K};K.pick('c130',1);K.start('drop');}}"); await pg.wait_for_timeout(600); await log(pg)
        await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z;}}")
        await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<40;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);}}"); await pg.wait_for_timeout(200)
        await pg.evaluate(f"()=>{K}.missDrop()"); await pg.wait_for_timeout(200)
        L = await log(pg)
        ok('pallet release: the double', 'release' in L, L)
        ok('green light: the double (when the window was open)', 'green' in L or not await pg.evaluate(f"()=>{K}.DZ.cg"), L)
        # a stall warning repeats on a cooldown, never per frame
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('final');}}"); await pg.wait_for_timeout(400); await log(pg)
        await pg.evaluate(f"()=>{{const s={K}.state();s.ap=null;s.apW=null;s.aoaWarn=true;}}")
        for _ in range(12): await pg.evaluate(f"()=>{{const s={K}.state();s.aoaWarn=true;{K}.stepFrame(0,false,true);}}")   # dt 0: the flag survives the frame
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        L = await log(pg)
        ok('stall warning: a pulse, at most one per 0.7 s over 12 frames', L.count('stall') == 1, L)
        # rate cap: 30 gun calls in a burst are one pattern every 40 ms at most
        await pg.evaluate("()=>window.__vib.length=0")
        n = await pg.evaluate(f"()=>{{let n=0;for(let i=0;i<30;i++)if({K}.hap('gun'))n++;return n;}}")
        ok('30 gun calls in one frame: one pattern (the 40 ms cooldown)', n == 1, n)
        # the Settings tile turns it off, saved; the pause tile turns it back on
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sSet');}}"); await pg.wait_for_timeout(300)
        await finger(pg, '#oHap'); await pg.wait_for_timeout(200)
        h = await pg.evaluate(f"()=>({{on:{K}.HAP.on,ls:localStorage.getItem('kgeuHaptics'),txt:document.getElementById('oHap').textContent}})")
        ok('Settings: Haptics tile turns it off and saves it', h == {'on': False, 'ls': '0', 'txt': 'Haptics: Off'}, h)
        await log(pg); fired = await pg.evaluate(f"()=>{K}.hap('crash')")
        ok('off: patterns do nothing', fired is False and not await log(pg))
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('runway');K.togglePause();}}"); await pg.wait_for_timeout(500)
        await finger(pg, '#pHap'); await pg.wait_for_timeout(200)
        h = await pg.evaluate(f"()=>({{on:{K}.HAP.on,ls:localStorage.getItem('kgeuHaptics'),txt:document.querySelector('#pHap b').textContent,set:document.getElementById('oHap').textContent}})")
        ok('pause sheet: the Haptics tile turns it back on, both tiles agree', h == {'on': True, 'ls': '1', 'txt': 'On', 'set': 'Haptics: On'}, h)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await ctx.close()

        # ---- the iOS path: no vibrate, a switch input whose label is clicked
        ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
        await ctx.add_init_script(SWITCH)
        pg = await ctx.new_page(); pg.errs = []
        pg.on('pageerror', lambda e: pg.errs.append(str(e)))
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await ctx.add_init_script("(()=>{if(sessionStorage.getItem('__seeded'))return;sessionStorage.setItem('__seeded','1');localStorage.clear();localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');})()")
        await pg.goto(url); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await splash_gone(pg); await pg.wait_for_timeout(300)
        h = await pg.evaluate(f"()=>({{sup:{K}.HAP.sup,sw:!!document.querySelector('#hapWrap input[type=checkbox][switch]'),lab:!!document.querySelector('#hapWrap label[for=hapSw]'),hidden:(()=>{{const w=document.getElementById('hapWrap'),r=w.getBoundingClientRect();return r.right<=0&&r.bottom<=0}})()}})")
        ok('iOS: a hidden switch input and its label stand in for vibrate', h == {'sup': 'switch', 'sw': True, 'lab': True, 'hidden': True}, h)
        await pg.evaluate(f"()=>{{{K}.HAP.plan.length=0;{K}.hap('crash');}}"); await pg.wait_for_timeout(1500)
        c = await pg.evaluate("()=>window.__clicks.length")
        plan = await pg.evaluate(f"()=>{K}.HAP.plan.slice()")
        gaps = [plan[i + 1] - plan[i] for i in range(len(plan) - 1)]
        ok('crash: a burst of label clicks (3 per heavy tick), planned no closer than 40 ms', 12 <= c <= 18 and len(plan) == c and all(g >= 39 for g in gaps), (c, gaps))
        await pg.evaluate("()=>window.__clicks.length=0")
        await pg.evaluate(f"()=>{K}.hap('button')"); await pg.wait_for_timeout(200)
        ok('button: exactly one light click', await pg.evaluate("()=>window.__clicks.length") == 1)
        await pg.evaluate("()=>window.__clicks.length=0")
        await pg.evaluate(f"()=>{{for(let i=0;i<20;i++){K}.hapTick('h',0);}}"); await pg.wait_for_timeout(1500)
        n = await pg.evaluate("()=>window.__clicks.length")
        ok('20 heavy ticks at once: capped at 24 clicks in flight, never buzzy', n <= 24, n)
        # a flight does not throw without vibrate
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway');}}"); await pg.wait_for_timeout(800)
        await pg.evaluate(f"()=>{{for(let i=0;i<30;i++){K}.stepFrame(0.1,false,true);{K}.stepFrame(0,true);}}")
        ok('iOS path: no page errors', not pg.errs, pg.errs[:3])
        await ctx.close()
        await b.close()
    sys.exit(ok.done('haptics_check'))

asyncio.run(main())
