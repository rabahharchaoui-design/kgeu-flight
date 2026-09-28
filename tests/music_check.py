# 3.13 Music system. (a) With the real, empty assets/music/playlist.json: tapping
# through the menus, a flight, pause and resume makes no errors and no sound.
# (b) With generated tones swapped in through __kgeu.musicLoad: it starts on the home
# screen after a tap, deals every track before repeating, crossfades on Next song,
# dips under the tower, follows the free flight toggle, and the Settings and pause
# controls change and persist. Also a fit check of both at 667x375.
# Run: .venv/bin/python tests/music_check.py
import asyncio, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
from harness import serve, page, Checks, finger
ok = Checks()
M = "()=>window.__kgeu.music()"
SR = 8000

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    n = int(SR * secs)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(n)))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()

def tones(secs, tag):
    return [{'name': f'_test_{tag}{i}.wav', 'url': tone(f, secs)} for i, f in enumerate((330, 440, 550))]

FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight;const bad=[];
  if(s.scrollHeight>s.clientHeight+1||s.scrollWidth>s.clientWidth+1)bad.push('scrolls '+s.scrollWidth+'x'+s.scrollHeight);
  s.querySelectorAll('button,input').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width)return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off screen '+(e.id||e.textContent.trim().slice(0,16)));
    if(r.height<43.5||(e.matches('button')&&r.width<43.5))bad.push('small '+(e.id||e.textContent.trim().slice(0,16))+' '+Math.round(r.width)+'x'+Math.round(r.height));});
  const hits=[...s.querySelectorAll('button,input')].filter(e=>e.getBoundingClientRect().width).map(e=>[e,e.getBoundingClientRect()]);
  for(let i=0;i<hits.length;i++)for(let j=i+1;j<hits.length;j++){const a=hits[i][1],b=hits[j][1];
    if(hits[i][0].contains(hits[j][0])||hits[j][0].contains(hits[i][0]))continue;
    if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)bad.push('overlap '+(hits[i][0].id||'?')+' / '+(hits[j][0].id||'?'));}
  return bad;}"""

async def m(pg): return await pg.evaluate(M)

async def wait_for(pg, cond, limit=6000, every=100):
    t = 0
    while t < limit:
        s = await m(pg)
        if cond(s): return s
        await pg.wait_for_timeout(every); t += every
    return await m(pg)

async def slider(pg, sel, v):
    await pg.evaluate("([s,v])=>{const r=document.querySelector(s);r.value=String(v);r.dispatchEvent(new Event('input',{bubbles:true}))}", [sel, v])

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        seed = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}

        # (a) the real, empty playlist: silent and error free
        pg = await page(b, url, storage=seed)
        await pg.touchscreen.tap(330, 8); await pg.wait_for_timeout(600)
        await finger(pg, '#hFly'); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>window.__kgeu.nav('sHome',true)"); await finger(pg, '#hSch'); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>window.__kgeu.nav('sHome',true)"); await finger(pg, '#hSet'); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.start('runway')}"); await pg.wait_for_timeout(1200)
        await pg.evaluate("()=>window.__kgeu.togglePause()"); await pg.wait_for_timeout(500)
        await finger(pg, '#pResume'); await pg.wait_for_timeout(800)
        s = await m(pg)
        ok('(a) empty playlist: manifest read as an empty list', s['list'] == [], s['list'])
        ok('(a) empty playlist: nothing playing, no errors', s['playing'] is None and s['errors'] == 0 and s['played'] == 0, s)
        ok('(a) no page errors and no console errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # (b) three generated tones
        pg = await page(b, url, storage=seed)
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", tones(2.0, 's'))
        s0 = await m(pg)
        ok('(b) nothing plays before the first tap', s0['playing'] is None, s0['playing'])
        await pg.touchscreen.tap(330, 8)
        s = await wait_for(pg, lambda s: s['playing'])
        ok('(b) playing on the home screen after a tap', s['playing'] is not None and await pg.evaluate("()=>window.__kgeu.curScr()") == 'sHome', s['playing'])
        ok('(b) default on, 60 percent, free flight off', s['on'] and abs(s['vol'] - 0.6) < 1e-6 and not s['free'], (s['on'], s['vol'], s['free']))
        await pg.wait_for_timeout(8000)
        h = (await m(pg))['hist']
        rounds = [h[i:i + 3] for i in range(0, len(h) - 2, 3)]
        ok('(b) 8 s of 2 s tones: at least two full rounds', len(h) >= 6, h)
        ok('(b) every track once before any repeat, each round', all(len(set(r)) == 3 for r in rounds), h)
        ok('(b) never the same track twice in a row', all(h[i] != h[i + 1] for i in range(len(h) - 1)), h)

        # Next song: long tones so no natural change lands in the window
        await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", tones(12.0, 'L'))
        s = await wait_for(pg, lambda s: s['playing'])
        await pg.wait_for_timeout(1800)
        p0 = (await m(pg))['playing']
        await pg.evaluate("()=>window.__kgeu.musicNext()")
        samples = []
        for _ in range(17):
            await pg.wait_for_timeout(100); samples.append(await m(pg))
        p1 = samples[-1]['playing']
        ok('(b) Next song changes the track', p1 and p1 != p0, (p0, p1))
        def g(s, name):
            for x in s['xf']:
                if x and x['name'] == name: return x['g']
            return 0.0
        mid = [s for s in samples[5:11]]
        inc = [round(g(s, p1), 2) for s in samples]; out = [round(g(s, p0), 2) for s in samples]
        ok('(b) crossfade: incoming rises, outgoing falls through the 1.5 s', any(0.15 < g(s, p1) < 0.95 and 0.15 < g(s, p0) < 0.95 for s in mid)
           and inc[-1] > 0.95 and out[-1] < 0.05 and inc[1] < inc[8], (inc, out))
        ok('(b) equal power: the sum of squares stays near 1 mid fade', all(abs(g(s, p1) ** 2 + g(s, p0) ** 2 - 1) < 0.2 for s in mid), [round(g(s, p1) ** 2 + g(s, p0) ** 2, 2) for s in mid])

        # the tower dips the music, in a mission (music allowed)
        for _ in range(40):
            r = await pg.evaluate("()=>{const R=window.__kgeu.RADIO;return R.want&&R.got+Math.max(0,R.err)>=R.want}")
            if r: break
            await pg.wait_for_timeout(500)
        await pg.evaluate("()=>window.__kgeu.mission('drop')")
        await pg.wait_for_timeout(2500)
        base = (await m(pg))['gain']
        await pg.evaluate("()=>{const K=window.__kgeu,ids=Object.keys(K.RADIO.buf).filter(k=>k.indexOf('t_')===0).slice(0,6);K.say('Tower','Skyhawk eight four zero one lima, runway one, cleared for takeoff.',ids)}")
        gs, dk = [], []
        for _ in range(60):
            await pg.wait_for_timeout(80); s = await m(pg); gs.append(round(s['gain'], 3)); dk.append(s['ducked'])
        low = min(gs)
        ok('(b) tower line: music ducks below half', base > 0.3 and low < 0.5 * base and any(dk), (base, low))
        s = await wait_for(pg, lambda s: not s['ducked'] and s['gain'] > 0.9 * base, 4000)
        ok('(b) tower line: music comes back up after', s['gain'] > 0.9 * base, (base, s['gain']))

        # free flight: off by default, fades to 0; on, it plays
        await pg.evaluate("()=>{window.__kgeu.setMusicFree(false);window.__kgeu.start('runway')}")
        await pg.wait_for_timeout(1000)
        mid = (await m(pg))['gain']
        await pg.wait_for_timeout(1500)
        s = await m(pg)
        ok('(b) free flight, toggle off: fades (not cut) to 0 and stops', 0.005 < mid < base and s['gain'] < 0.02 and s['playing'] is None and not s['want'], (base, mid, s['gain'], s['playing']))
        await pg.evaluate("()=>window.__kgeu.setMusicFree(true)")
        s = await wait_for(pg, lambda s: s['playing'] and s['gain'] > 0.4, 5000)
        ok('(b) free flight, toggle on: plays', s['playing'] is not None and s['gain'] > 0.4, (s['playing'], s['gain']))

        # Settings controls
        await pg.evaluate("()=>window.__kgeu.openMenu('sSet')"); await pg.wait_for_timeout(1800)
        p0 = (await m(pg))['playing']
        await finger(pg, '#oMnext')
        s = await wait_for(pg, lambda s: s['playing'] != p0, 1500)
        ok('(b) Settings Next song changes the track', s['playing'] and s['playing'] != p0, (p0, s['playing']))
        await finger(pg, '#oMusic'); await slider(pg, '#oMvol', 3); await finger(pg, '#oMfree')
        s = await m(pg)
        ui = await pg.evaluate("()=>[document.getElementById('oMusic').textContent,document.getElementById('oMvolV').textContent,document.getElementById('oMfree').textContent]")
        ok('(b) Settings: music off, 30 percent, free flight off', not s['on'] and abs(s['vol'] - 0.3) < 1e-6 and not s['free'], (s['on'], s['vol'], s['free'], ui))
        ok('(b) Settings labels follow', ui == ['Music: Off', '30%', 'In free flight: Off'], ui)
        s = await wait_for(pg, lambda s: s['playing'] is None and s['gain'] < 0.02, 3000)
        ok('(b) music off: fades out and stops', s['playing'] is None and s['gain'] < 0.02, (s['playing'], s['gain']))
        bad = await pg.evaluate(FIT, '#sSet')
        ok('(b) Settings at 667x375: fits, 44 px targets, no overlaps', not bad, bad[:4])

        # pause menu controls, in a mission
        await pg.evaluate("()=>window.__kgeu.mission('drop')"); await pg.wait_for_timeout(600)
        await pg.evaluate("()=>window.__kgeu.togglePause()"); await pg.wait_for_timeout(400)
        await finger(pg, '#pMusic'); await slider(pg, '#pMvol', 8)
        s = await wait_for(pg, lambda s: s['playing'], 3000)
        ok('(b) pause: Music on and 80 percent', s['on'] and abs(s['vol'] - 0.8) < 1e-6 and s['playing'], (s['on'], s['vol'], s['playing']))
        await pg.wait_for_timeout(1700)
        p0 = (await m(pg))['playing']
        await finger(pg, '#pMnext')
        s = await wait_for(pg, lambda s: s['playing'] != p0, 1500)
        ok('(b) pause: Next song changes the track', s['playing'] and s['playing'] != p0, (p0, s['playing']))
        bad = await pg.evaluate(FIT, '#pauseOv .pz')
        ok('(b) pause sheet at 667x375: fits, 44 px targets, no overlaps', not bad, bad[:4])
        ok('(b) no page errors and no console errors', not pg.errs, pg.errs[:3])

        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await pg.wait_for_timeout(500)
        s = await m(pg)
        ls = await pg.evaluate("()=>[localStorage.getItem('kgeuMusicOn'),localStorage.getItem('kgeuMusicVol'),localStorage.getItem('kgeuMusicFree')]")
        ui = await pg.evaluate("()=>[document.getElementById('oMusic').textContent,document.getElementById('pMvol').value,document.getElementById('oMfree').textContent]")
        ok('(b) reload keeps on, volume and the free flight toggle', s['on'] and abs(s['vol'] - 0.8) < 1e-6 and not s['free'] and ls == ['1', '0.8', '0'], (ls, ui))
        ok('(b) controls show the saved values after reload', ui == ['Music: On', '8', 'In free flight: Off'], ui)
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('music_check'))

asyncio.run(main())
